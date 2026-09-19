# ArcFlow — Cross-chain USDC price-spread ledger on Arc

A small on-chain log that records the *real* cost of moving USDC across chains, written by anyone, read by anyone.

Built as the public deliverable for the **Arc Microgrants** program (open call Sep 16 – Oct 14, 2026).

---

## Why this exists

I run a one-person company. My agents move USDC between platforms all day. The problem: every chain pair has its own on-chain DEX price, CEX price, and bridge fee, and they diverge. Without a shared ledger, every wallet, every bot, every AI agent has to redo the same scrape-and-compare work — and gets a different number.

**ArcFlow is that ledger.** Anyone — me, my agent, you — can publish a single observation (`fromChain → toChain, spreadBps, ts`). Everyone else reads it. The data is verifiable end-to-end because it lives on Arc mainnet, not on some private API.

The motivation is exactly what I wrote in my Arc House application:
> "I run a one-person company, and settlement across platforms and currencies is my slowest and most expensive step. I want to test whether USDC-as-native-gas plus the built-in FX engine actually removes that cost for a solo operator, at small amounts and high frequency, including payments between my own agents."

This is the tool I built to answer that question for myself.

---

## What it does

- `record(fromChain, toChain, spreadBps)` — publish one observation. Paid in native USDC on Arc (~50k gas, ~0.001 USDC at today's gas price).
- `latestPair(fromChain, toChain)` — most recent observation for a given pair.
- `latestN(n)` — newest N observations (max 50).
- `snapshot9()` — batched latest spread for the 9 most common pairs in one call (saves RPC round-trips).
- `total()` / `get(i)` — append-only log of every observation.

**Chain IDs** are first-class constants in the contract:
`ARC (5042) · ETHEREUM (1) · BASE (8453) · OPTIMISM (10) · ARBITRUM (42161) · POLYGON (137) · AVALANCHE (43114) · BNB (56) · LINEA (59144)`

---

## Repository layout

```
ArcFlow/
├── contracts/ArcFlow.sol          # Solidity 0.8.20, no external deps
├── web/index.html                 # public read-only dashboard
├── agent/arcflow_publisher.py     # recorder: reads real DEX prices, writes to Arc
├── agent/arcflow_signer.py        # dependency-free EIP-1559 signer
├── agent/verify_signer.py         # asserts the signer matches ethers.js byte-for-byte
├── agent/test_publisher.py        # offline tests for the write path (no network, no key)
├── build/                         # abi.json + bytecode.json
└── docs/microgrants.md            # application narrative
```

---

## Live deployment

> **Status:** deployed and running on **Arc Mainnet** (Chain ID 5042).

- **Contract (mainnet):** [`0xf004c40f0b8204c21991309A808dA2ee4895B9Eb`](https://explorer.arc.io/address/0xf004c40f0b8204c21991309A808dA2ee4895B9Eb) — deployed 2026-09-19, tx `0xcc565985be918b951caac394d65f2ca0fee68e15496d65b6b09bf85f3994d1a5`, block 21,593,815, gasUsed 781,224
- **Dashboard:** **https://ooii166.github.io/Lightning/** — reads the contract above straight from Arc RPC
- **RPC (mainnet):** `https://rpc.mainnet.arc.io`
- **Verifiable state:** call `total()` on the contract to see how many observations the ledger holds.

---

## How to deploy yourself

ArcFlow has no constructor arguments. Deploy straight from Remix, Arc Studio, or Hardhat:

1. **Open Remix** at https://remix.ethereum.org
2. Paste `contracts/ArcFlow.sol` into a new file
3. In the **Solidity Compiler** tab, set `compiler` to `0.8.20` and click *Compile*
4. In the **Deploy & Run Transactions** tab:
   - **Environment:** `Injected Provider — MetaMask`
   - **Network:** Add Arc mainnet manually if not present (RPC `https://rpc.mainnet.arc.io`, Chain ID `5042`, symbol `USDC`, explorer `https://explorer.arc.io`)
   - **Contract:** pick `ArcFlow.sol · ArcFlow`
   - Click **Deploy**, confirm in MetaMask
5. Copy the deployed contract address → that's your public artifact for Microgrants

If you want a one-shot script (Hardhat):
```bash
npm i hardhat @nomicfoundation/hardhat-toolbox
# hardhat.config.ts → networks.arc = { url: "https://rpc.mainnet.arc.io", chainId: 5042, accounts: [process.env.PRIVATE_KEY] }
npx hardhat ignition deploy ignition/modules/ArcFlow.ts --network arc
```

---

## Cost and how it is automated

One `record(...)` call is roughly 50k gas, which on Arc is about **0.001 USDC** in
native gas.

The publisher therefore does not write on every run. Before writing, it asks the
contract what it last recorded for each pair (`latestPair`) and only writes when
the spread has moved by at least `ARCFLOW_MIN_DELTA_BPS`. It also caps writes per
run (`ARCFLOW_MAX_RECORDS`, default 3) and aborts if the wallet balance falls below
`ARCFLOW_MIN_BALANCE`.

[`.github/workflows/arcflow-publish.yml`](../../.github/workflows/arcflow-publish.yml)
runs the publisher hourly against Arc mainnet. Because the previous value is read
from the chain rather than a local file, the change detection works identically on
a laptop and on a CI runner — there is no state to persist.

Run it yourself:

```bash
cd agent
ARCFLOW_DRY_RUN=1 python arcflow_publisher.py      # preview, writes nothing
ARCFLOW_PK=<hex> python arcflow_publisher.py       # publish
```

Every run prints the per-chain prices it observed and the basis-point spread it
computed, so the numbers in the ledger can be reproduced from the same public
sources.

### Writes are confirmed, not assumed

A node returns a transaction hash as soon as it accepts a transaction into its
mempool, which is not a promise that the transaction will ever be included. The
publisher therefore waits for each write to appear in a block before counting it,
and only then builds the next one — so a record that silently failed to land is
reported as a failure (non-zero exit) rather than as a success the ledger does not
contain. The hourly job turns red in that case, which is the honest signal.

Because consecutive records share a wallet, the nonce is read from the chain
immediately before each broadcast rather than tracked locally. `pending` returns
the first *unused* nonce, which is also the correct choice when an earlier run left
a gap behind — filling that gap is what releases anything queued behind it. If a
nonce is already held by a transaction from an earlier run, the write is retried
once at the **same** nonce with a fee 35% higher: nodes only replace a pooled
transaction when the new fee clears a threshold (10% by default), so the retry has
to jump rather than nudge. Retrying at the same nonce can never open a gap, since
only one transaction can be included per nonce.

These paths are covered by `agent/test_publisher.py`, which runs offline in CI
before the publisher does.

---

## License

MIT — see [LICENSE](../../LICENSE).

---

## Credits

Built by Chengmiao Wang (`@ChengmiaoW74762` · LinkedIn `/in/...47641a131/`) — a one-person company in Hangzhou, China.

Public links to verify identity:
- Arc House profile: https://community.arc.io/home/profile
- GitHub: https://github.com/ooii166
- Project repo: https://github.com/ooii166/Lightning