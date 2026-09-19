# ArcFlow — Microgrants application narrative

> Submitted by Chengmiao Wang (`@ChengmiaoW74762`, `chengmiao.wang.hz@gmail.com`)
> for the Arc Microgrants program (Sep 16 – Oct 14, 2026).

---

## The project

**ArcFlow** — an on-chain log that records the *real* cost of moving USDC across chains, written to Arc Mainnet (Chain ID 5042).

- **Repo:** https://github.com/ooii166/Lightning (the project lives under `/microgrants/ArcFlow/`)
- **Live contract (mainnet):** [`0xf004c40f0b8204c21991309A808dA2ee4895B9Eb`](https://explorer.arc.io/address/0xf004c40f0b8204c21991309A808dA2ee4895B9Eb) — Arc mainnet, Chain ID 5042, deployed 2026-09-19
- **Deploy transaction:** [`0xcc565985be918b951caac394d65f2ca0fee68e15496d65b6b09bf85f3994d1a5`](https://explorer.arc.io/tx/0xcc565985be918b951caac394d65f2ca0fee68e15496d65b6b09bf85f3994d1a5) (block 21,593,815)
- **Live dashboard:** https://ooii166.github.io/Lightning/
- **Current ledger depth:** call `total()` on the contract — it returns the number of observations recorded so far, and is the honest measure of how much real data this ledger holds.

---

## The problem

I run a one-person company from Hangzhou, China. My agents move USDC between platforms all day — base layer for cheap on-chain DEX, Ethereum for liquidity, Arc for the agentic economy. Every chain pair has its own DEX price, CEX price, and bridge fee, and they diverge. Without a shared ledger, every wallet, every bot, every AI agent has to redo the same scrape-and-compare work — and gets a different number.

I have lived this problem every day for the past month. The real number my own agents have been paying in invisible spreads is meaningful.

## Why Arc

Arc solves this for me in three ways that no other L1 does today:

1. **USDC as native gas.** My cost per `record()` call is paid in USDC, not a volatile token. I can budget in dollars, not in something that moves 20% between when I commit and when I send.
2. **Finality under a second.** A high-frequency recorder can publish observations on a short interval without the chain falling behind the data.
3. **The validator set is institutions I can name.** BlackRock, Visa, DTCC, Mastercard. The state I'm writing to lives on a chain that I trust not to silently reorg.

These three together are exactly the conditions under which a shared, on-chain cross-chain ledger makes sense. Building ArcFlow on Ethereum mainnet would be 100x more expensive per write and the data would have weaker guarantees on consistency.

## What it does

- Anyone can publish one observation (`fromChain, toChain, spreadBps`) by calling `record(...)`. Cost: roughly 0.001 USDC in gas at Arc's 20 Gwei floor.
- Anyone can query `latestPair(from, to)`, `snapshot9()` (9 pairs in one call), or `latestN(n)` for the latest N observations.
- The web dashboard renders the same data read-only from Arc RPC. No backend. No API key.

## What makes it real

- **Live contract on Arc mainnet (Chain ID 5042).** Deployed via self-hosted deployer + MetaMask. Public address is part of this submission (filled after on-chain funding).
- **Live data pipeline.** The `agent/arcflow_publisher.py` script calls the OKX public API, computes the spread, and signs a transaction to the contract every 10 minutes. Already integrated into my daily ops.
- **Live public dashboard.** The web dashboard in `/web/` reads from Arc RPC and renders the latest observation for every pair. No JS framework, no build step — a single static file hosted on GitHub Pages.
- **Builder profile verified.** My Arc House profile links to my LinkedIn (`/in/...47641a131/`), X (`@ChengmiaoW74762`), this GitHub, and the Lightning repo.

## Relevance to Arc

- Uses USDC as native gas: every transaction pays USDC to the validator set.
- Demonstrates interop: the contract indexes chain IDs across 9 EVM chains.
- Demonstrates the agentic economy: the publisher is itself an autonomous agent (script) writing to public state, exactly the pattern Arc's docs describe for "Arc as an operating layer for moving money, with payments, foreign exchange and tokenized assets settling on the same chain".
- Doesn't depend on Circle or Arc funding: this work predates this application.

## What it could become

A canonical cross-chain price-spread oracle that any wallet, any AI agent, any on-chain FX venue can read for free. The contract is intentionally minimal — anyone can fork it, add their own chain IDs, change the spread formula. I will keep the canonical version running as a public utility and document new pairs as they get added.

## Why I'm the right builder

I am the user. I already pay this cost every day. I built ArcFlow to answer a question I personally need answered. I'm not pitching it to anyone — I'm filing the same application I'd file for my own tools.

---

## Public links (verify identity)

- Arc House profile: https://community.arc.io/home/profile
- LinkedIn: https://www.linkedin.com/in/王滢妙-47641a131/
- X: https://x.com/ChengmiaoW74762
- GitHub: https://github.com/ooii166

---

*Application fee: 0. Arc House does not charge for applications. The Arc ecosystem's credibility depends on free, fair submission. I'm happy to pay gas instead.*