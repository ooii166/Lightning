# Lightning

Monorepo for my on-chain projects. The active project is **ArcFlow**.

## ArcFlow — cross-chain USDC spread ledger on Arc

An on-chain log that records the **real cost of moving USDC across chains**. Anyone can write an
observation, anyone can read it. Deployed and running on **Arc mainnet (Chain ID 5042)**.

**Project folder: [`microgrants/ArcFlow/`](./microgrants/ArcFlow/)** · built for the
[Arc Microgrants](https://dorahacks.io/hackathon/arc-microgrants) program.

### Live on Arc mainnet

| | |
|---|---|
| **Contract** | [`0xf004c40f0b8204c21991309A808dA2ee4895B9Eb`](https://explorer.arc.io/address/0xf004c40f0b8204c21991309A808dA2ee4895B9Eb) |
| **Deploy tx** | [`0xcc5659…d1a5`](https://explorer.arc.io/tx/0xcc565985be918b951caac394d65f2ca0fee68e15496d65b6b09bf85f3994d1a5) |
| **Block** | 21,593,815 |
| **Chain ID** | 5042 |
| **RPC** | `https://rpc.mainnet.arc.io` |
| **Explorer** | https://explorer.arc.io |
| **Runtime bytecode** | 3,368 bytes. `eth_getCode` returns a 6,736-character hex string — that is 6,736 hex *characters*, and 2 characters are 1 byte, so the code is 3,368 bytes. The compiled creation bytecode in `build/bytecode.json` is 3,397 bytes (creation is always larger than runtime; it carries the constructor). |

### Live dashboard

**https://ooii166.github.io/Lightning/microgrants/ArcFlow/web/index.html** — reads the contract above directly from Arc RPC.
(The Pages root https://ooii166.github.io/Lightning/ is a short landing page that links here.)
No backend, no API key.

### What it does

- `record(fromChain, toChain, spreadBps)` — publish one observation. Paid in native USDC on Arc.
- `latestPair(from, to)` — the most recent observation for a pair.
- `latestN(n)` — newest N observations (max 50).
- `snapshot9()` — batched latest spread for the 9 most common pairs in a single call.
- `total()` / `get(i)` — the append-only log of every observation.

Chain IDs are first-class constants in the contract:
`ARC (5042) · ETHEREUM (1) · BASE (8453) · OPTIMISM (10) · ARBITRUM (42161) · POLYGON (137) · AVALANCHE (43114) · BNB (56) · LINEA (59144)`

### Repository layout

```
microgrants/ArcFlow/
├── contracts/ArcFlow.sol          # Solidity 0.8.20, no external deps
├── web/index.html                 # public read-only dashboard
├── agent/arcflow_publisher.py     # automated recorder (public price APIs -> Arc)
├── agent/arcflow_signer.py        # dependency-free EIP-1559 signer
├── agent/verify_signer.py         # signer checked against ethers.js, byte for byte
├── agent/test_publisher.py        # offline tests for the write path
├── deploy/                        # compile + deploy helpers
├── build/                         # abi.json + bytecode.json
└── docs/microgrants.md            # application narrative
```

### Why Arc

1. **USDC as native gas** — the cost per `record()` is paid in USDC, so it can be budgeted in
   dollars rather than in an asset that moves 20% between commitment and settlement.
2. **Sub-second finality** — a high-frequency recorder can publish every 10 minutes without the
   chain falling behind the data.
3. **A validator set that can be named** — the state being written to lives on a chain operated by
   institutions, not an anonymous set.

### Deploy it yourself

ArcFlow has no constructor arguments. See
[`microgrants/ArcFlow/README.md`](./microgrants/ArcFlow/README.md) for the full walkthrough
(Remix or Hardhat).

### License

MIT — see [LICENSE](./LICENSE).

### Author

Chengmiao Wang — one-person company, Hangzhou, China.

- GitHub: https://github.com/ooii166
- X: https://x.com/ChengmiaoW74762
- Arc House: https://community.arc.io/home/profile
