# -*- coding: utf-8 -*-
"""
ArcFlow publisher — records real cross-chain USDC spread observations on Arc mainnet.

What it does
------------
1. Reads the *actual* USDC/USDT price on each chain from the deepest DEX pool
   (public DexScreener API, no key required).
2. Computes the spread between chains in basis points.
3. Signs and broadcasts `record(fromChain, toChain, spreadBps)` to the ArcFlow
   contract on Arc mainnet, paying gas in native USDC.

Why the spreads are meaningful
------------------------------
USDC is meant to be worth exactly $1 everywhere, but it is not: local supply and
demand push it a few basis points off parity on each chain, and that deviation is
precisely the cost a wallet, bot or agent pays when it moves USDC. That deviation
is what this ledger records.

Arc's own reference price is taken as the $1.000 peg, because on Arc USDC *is* the
native gas asset rather than a bridged representation.

Economics
---------
One `record()` costs roughly 0.001 USDC in gas. This script therefore does NOT
write on every run: before writing, it asks the contract what it last recorded
for each pair (`latestPair`) and only writes when the spread has moved at least
ARCFLOW_MIN_DELTA_BPS. It also refuses to spend more than ARCFLOW_MAX_RECORDS per
run, and aborts entirely below ARCFLOW_MIN_BALANCE. Because the previous value is
read from chain, the change detection needs no local state file and works
identically on a laptop, a server or a GitHub Actions runner.

Configuration (environment)
---------------------------
  ARCFLOW_PK            hex private key, no 0x. If unset -> dry run, nothing sent.
  ARCFLOW_CONTRACT      contract address (defaults to the deployed one)
  ARCFLOW_RPC           RPC endpoint (defaults to Arc mainnet)
  ARCFLOW_MIN_DELTA_BPS minimum change to re-publish a pair (default 1)
  ARCFLOW_MAX_RECORDS   hard cap on writes per run (default 3)
  ARCFLOW_MIN_BALANCE   abort if native balance drops below this (default 0.05)
  ARCFLOW_DRY_RUN       set to 1 to force a dry run

Dependencies: Python standard library only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from arcflow_signer import (  # noqa: E402
    encode_record_calldata,
    private_key_to_address,
    sign_eip1559_tx,
)

# ── Configuration ─────────────────────────────────────────────────────────────

CONTRACT = os.environ.get('ARCFLOW_CONTRACT', '0xf004c40f0b8204c21991309A808dA2ee4895B9Eb')
RPC = os.environ.get('ARCFLOW_RPC', 'https://rpc.mainnet.arc.io')
PK_HEX = os.environ.get('ARCFLOW_PK', '').strip().removeprefix('0x')
CHAIN_ID = 5042

MIN_DELTA_BPS = int(os.environ.get('ARCFLOW_MIN_DELTA_BPS', '1'))
MAX_RECORDS = int(os.environ.get('ARCFLOW_MAX_RECORDS', '3'))
MIN_BALANCE = float(os.environ.get('ARCFLOW_MIN_BALANCE', '0.05'))
DRY_RUN = os.environ.get('ARCFLOW_DRY_RUN', '') == '1' or not PK_HEX

# Arc gas: the base fee floor is 20 Gwei.
GAS_FLOOR = 20 * 10 ** 9
GAS_LIMIT_FALLBACK = 120000

# ── Chain registry ────────────────────────────────────────────────────────────
# `dex` is the DexScreener chain slug; None means the chain has no public DEX
# data source here (Arc is priced at the native peg instead).

CHAINS = {
    'arc':       {'id': 5042,  'dex': None,         'ref': 1.0},
    'ethereum':  {'id': 1,     'dex': 'ethereum',   'usdc': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'},
    'base':      {'id': 8453,  'dex': 'base',       'usdc': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'},
    'optimism':  {'id': 10,    'dex': 'optimism',   'usdc': '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'},
    'arbitrum':  {'id': 42161, 'dex': 'arbitrum',   'usdc': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831'},
    'polygon':   {'id': 137,   'dex': 'polygon',    'usdc': '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359'},
    'avalanche': {'id': 43114, 'dex': 'avalanche',  'usdc': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E'},
    'bnb':       {'id': 56,    'dex': 'bsc',        'usdc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d'},
    'linea':     {'id': 59144, 'dex': 'linea',      'usdc': '0x176211869cA2b568f2A7D4EE941E073a821EE1ff'},
}

PAIRS = [
    ('arc', 'ethereum'),
    ('arc', 'base'),
    ('arc', 'arbitrum'),
    ('arc', 'polygon'),
    ('arc', 'optimism'),
    ('ethereum', 'base'),
    ('ethereum', 'arbitrum'),
]

# ── HTTP helpers ──────────────────────────────────────────────────────────────


# Public APIs reject generic client strings, so identify ourselves properly.
USER_AGENT = 'ArcFlow/1.0 (+https://github.com/ooii166/Lightning)'


def http_json(url, payload=None, timeout=25):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'user-agent': USER_AGENT, 'accept': 'application/json'}
    if data:
        headers['content-type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def rpc(method, params=None):
    d = http_json(RPC, {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or []})
    if 'error' in d:
        raise RuntimeError('%s -> %s' % (method, d['error']))
    return d.get('result')


LATEST_PAIR_SELECTOR = '0x25f18eb6'  # latestPair(uint16,uint16)


def read_latest_bps(from_id, to_id):
    """
    Ask the contract what it last recorded for this pair.

    Reading this from chain (rather than keeping a local state file) means the
    change-detection works across CI runs, machines and clones with no state to
    persist. Returns None when the pair has never been recorded.
    """
    data = LATEST_PAIR_SELECTOR + ('%064x' % from_id) + ('%064x' % to_id)
    try:
        res = rpc('eth_call', [{'to': CONTRACT, 'data': data}, 'latest'])
    except Exception as e:
        print('  [warn] latestPair(%d,%d) read failed: %s' % (from_id, to_id, e), file=sys.stderr)
        return None
    if not res or res == '0x' or len(res) < 2 + 64 * 4:
        return None
    body = res[2:]
    spread = int(body[0:64], 16)
    if spread >= 2 ** 255:
        spread -= 2 ** 256
    ts = int(body[64:128], 16)
    if ts == 0:
        return None
    return spread


# ── Price discovery ───────────────────────────────────────────────────────────


def chain_usdc_price(chain_key, min_liquidity=250000):
    """
    Deepest trustworthy USDC pool on this chain -> price of USDC in USD.

    DexScreener reports `priceUsd` for the *base* token of a pair, so we handle
    both orientations:
      * USDC is the base   -> priceUsd is already USDC's price
      * USDC is the quote  -> priceUsd / priceNative gives the quote token's price
    Returns None when nothing passes the liquidity and plausibility filters.
    """
    spec = CHAINS[chain_key]
    if spec.get('ref') is not None:
        return spec['ref']

    url = 'https://api.dexscreener.com/latest/dex/tokens/%s' % spec['usdc']
    try:
        d = http_json(url)
    except Exception as e:
        print('  [warn] %s price fetch failed: %s' % (chain_key, e), file=sys.stderr)
        return None

    want = spec['usdc'].lower()
    best = None
    for p in (d.get('pairs') or []):
        if p.get('chainId') != spec['dex']:
            continue
        liq = ((p.get('liquidity') or {}).get('usd') or 0)
        if liq < min_liquidity:
            continue
        try:
            price_usd = float(p['priceUsd'])
        except (KeyError, TypeError, ValueError):
            continue

        base = (p.get('baseToken') or {}).get('address', '').lower()
        quote = (p.get('quoteToken') or {}).get('address', '').lower()
        price = None
        if base == want:
            price = price_usd
        elif quote == want:
            try:
                pn = float(p['priceNative'])
            except (KeyError, TypeError, ValueError):
                continue
            if pn > 0:
                price = price_usd / pn
        if price is None:
            continue

        # A dollar stablecoin should be near a dollar. This rejects mispriced or
        # manipulated pools (e.g. a "USDC/USDT" pool quoting 1.72) that would
        # otherwise poison the ledger with junk.
        if not (0.90 <= price <= 1.10):
            continue

        if best is None or liq > best[0]:
            best = (liq, price)

    return best[1] if best else None


def fetch_prices():
    out = {}
    for key in CHAINS:
        if key == 'arc':
            out[key] = CHAINS[key]['ref']
            continue
        p = chain_usdc_price(key)
        if p is not None:
            out[key] = p
        time.sleep(0.25)  # be polite to the public API
    return out


def spread_bps(p_from, p_to):
    """Signed basis points: how much more USDC costs on `to` vs `from`."""
    if not p_from:
        return 0
    diff = (p_to - p_from) / p_from * 10000.0
    return max(min(int(round(diff)), 32767), -32768)


# ── Publishing ────────────────────────────────────────────────────────────────


def send_record(priv, from_chain, to_chain, bps, gas_limit, max_fee, priority_fee, nonce=None):
    """
    Sign and broadcast one `record()` call.

    `nonce` may be supplied by the caller. That matters because several writes can
    happen in a single run and a freshly broadcast transaction may not yet be
    reflected in `eth_getTransactionCount(..., 'pending')`; reusing the same nonce
    would make the later writes replace the earlier ones.
    """
    if nonce is None:
        nonce = int(rpc('eth_getTransactionCount', ['0x%040x' % priv_addr_int(priv), 'pending']), 16)
    raw = sign_eip1559_tx(
        priv, CHAIN_ID, nonce, CONTRACT,
        encode_record_calldata(from_chain, to_chain, bps),
        gas_limit, max_fee, priority_fee,
    )
    return rpc('eth_sendRawTransaction', ['0x' + raw.hex()])


_ADDR_CACHE = {}


def priv_addr_int(priv):
    a = _ADDR_CACHE.get(priv)
    if a is None:
        a = int(private_key_to_address(priv), 16)
        _ADDR_CACHE[priv] = a
    return a


def main():
    if CONTRACT.startswith('0xREPLACE'):
        print('[abort] ARCFLOW_CONTRACT is not set to a real address', file=sys.stderr)
        return 2

    priv = int(PK_HEX, 16) if PK_HEX else None
    if priv is not None:
        addr = private_key_to_address(priv)
        print('signer   : %s' % addr)
    print('contract : %s' % CONTRACT)
    print('mode     : %s' % ('DRY RUN (no transactions will be sent)' if DRY_RUN else 'LIVE'))
    print()

    # Balance guard — never let a runaway schedule drain the wallet.
    if not DRY_RUN:
        bal_wei = int(rpc('eth_getBalance', [private_key_to_address(priv), 'latest']), 16)
        bal = bal_wei / 1e18
        print('balance  : %.6f USDC' % bal)
        if bal < MIN_BALANCE:
            print('[abort] balance %.6f below ARCFLOW_MIN_BALANCE %.6f' % (bal, MIN_BALANCE),
                  file=sys.stderr)
            return 3
        gas_price = int(rpc('eth_gasPrice', []), 16)
        max_fee = max(gas_price * 2, GAS_FLOOR + 5 * 10 ** 9)
        priority = 10 ** 9
        gas_limit = GAS_LIMIT_FALLBACK
        print('gas price: %.2f Gwei -> maxFee %.2f Gwei' % (gas_price / 1e9, max_fee / 1e9))
    else:
        max_fee = priority = gas_limit = 0

    print()
    print('fetching per-chain USDC prices…')
    prices = fetch_prices()
    for k, v in sorted(prices.items()):
        print('  %-10s %s' % (k, ('%.6f' % v) if v else 'unavailable'))

    pending = []
    for frm, to in PAIRS:
        pf, pt = prices.get(frm), prices.get(to)
        if pf is None or pt is None:
            print('  skip %s -> %s (missing price)' % (frm, to))
            continue
        bps = spread_bps(pf, pt)
        prev = read_latest_bps(CHAINS[frm]['id'], CHAINS[to]['id'])
        if prev is not None and abs(bps - prev) < MIN_DELTA_BPS:
            print('  keep %s -> %s (now %+d bps, on-chain %+d bps — unchanged)'
                  % (frm, to, bps, prev))
            continue
        pending.append((frm, to, bps, prev))

    pending.sort(key=lambda x: -abs(x[2] - (x[3] or 0)))
    if len(pending) > MAX_RECORDS:
        print('  %d pairs moved; writing the top %d (ARCFLOW_MAX_RECORDS)'
              % (len(pending), MAX_RECORDS))
        pending = pending[:MAX_RECORDS]

    print()
    if not pending:
        print('nothing moved by >= %d bps — no write needed this run.' % MIN_DELTA_BPS)
        return 0

    written = 0
    failed = 0
    next_nonce = None
    for frm, to, bps, prev in pending:
        f_id, t_id = CHAINS[frm]['id'], CHAINS[to]['id']
        label = '%s -> %s' % (frm, to)
        if DRY_RUN:
            print('  [dry-run] %-24s bps=%+6d (was %s)' % (label, bps, prev))
            written += 1
            continue
        try:
            # Read the nonce ONCE, before the first broadcast, then advance it
            # locally. Reading it *after* a broadcast and incrementing counts the
            # transaction we just sent a second time, which opens a nonce gap and
            # makes every later write in the same run fail with "nonce too high".
            if next_nonce is None:
                next_nonce = int(rpc('eth_getTransactionCount',
                                     ['0x%040x' % priv_addr_int(priv), 'pending']), 16)
            txh = send_record(priv, f_id, t_id, bps, gas_limit, max_fee, priority, next_nonce)
            print('  %-24s bps=%+6d  tx=%s' % (label, bps, txh))
            written += 1
            next_nonce += 1
        except Exception as e:
            failed += 1
            print('  %-24s bps=%+6d  ERROR: %s' % (label, bps, e), file=sys.stderr)

    print()
    print('[done] %d observation(s) %s%s'
          % (written, 'previewed' if DRY_RUN else 'written',
             (', %d FAILED' % failed) if failed else ''))
    # A run that silently drops writes would report success while the ledger stays
    # behind, so surface it as a real failure. Nothing is lost: a pair whose write
    # failed still has no on-chain value, so the next run picks it up again.
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
