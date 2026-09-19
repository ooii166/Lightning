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

- `record(fromChain, toChain, spreadBps)` — publish one observation. Paid in native USDC on Arc (~50k gas, ~0.0001 USDC at today's gas price).
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
├── web/index.html                 # public read-only dashboard (GitHub Pages)
├── agent/arcflow_publisher.py     # automated recorder (OKX public API → Arc)
└── docs/microgrants.md            # application narrative
```

---

## Live deployment

> **Status:** code switched to **Arc Mainnet** (Chain ID 5042). Mainnet deployment is pending on-chain funding of the deployer address — the same bytecode deploys unchanged.

- **Contract (mainnet):** pending — will be filled after deployment
- **Web:** `https://ooii166.github.io/Lightning/microgrants/ArcFlow/web/` — points at the mainnet contract once deployed
- **RPC (mainnet):** `https://rpc.mainnet.arc.io`

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

## Cost

One `record(...)` call ≈ 50k gas × Arc gas price. At realistic Arc gas prices this is sub-cent in USDC. The agent publisher runs every 10 minutes, so daily cost ≈ a few cents.

---

## License

MIT.

---

## Credits

Built by Chengmiao Wang (`@ChengmiaoW74762` · LinkedIn `/in/...47641a131/`) — a one-person company in Hangzhou, China.

Public links to verify identity:
- Arc House profile: https://community.arc.io/home/profile
- GitHub: https://github.com/ooii166
- Project repo: https://github.com/ooii166/Lightning