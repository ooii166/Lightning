# `deploy/` — historical deploy helpers

These scripts are the scratch tooling I used while getting ArcFlow onto Arc. They are kept
for transparency, not because you need them.

**You do not need any of this to use or verify ArcFlow.** The contract is already deployed
on Arc mainnet and the source in `../contracts/ArcFlow.sol` compiles with Solidity 0.8.20 and
no external dependencies. To deploy your own copy, follow
[`../README.md` → How to deploy yourself](../README.md#how-to-deploy-yourself) — Remix is
enough.

What is in here:

| File | What it was for |
| --- | --- |
| `compile.js` | Compiles `ArcFlow.sol` with solc-js and writes `../build/{abi,bytecode}.json`. Still useful. |
| `arcflow_artifact.js`, `arcflow_artifact.json` | Compiled artifact dumps (ABI + bytecode). |
| `arcflow_mainnet_deploy.py`, `arcflow_connect_deploy.py`, `arcflow_deploy_only.py` | Wallet-connect deploy attempts against Arc mainnet. Superseded by the deploy recorded in the main README. |
| `arcflow_prepare.py`, `arcflow_run.py`, `arcflow_one_shot.py`, `arcflow_drive.py`, `deployctl.py`, `check_mm.py` | Ad-hoc orchestration and browser-automation experiments from the testnet phase. Dead ends — they never produced the final signed deploy. |
| `deploy.html` | A throwaway local page used to drive a wallet-connect deploy. |

The lesson worth recording: driving a wallet through browser automation to sign a deploy is
fragile, and it is why the publisher in `../agent/` signs transactions directly instead of
depending on a browser. That signer is verified against ethers.js byte-for-byte in
`../agent/verify_signer.py`.

If you are reading this as part of a grant review: the live artifact is the contract address
and deploy transaction in the main README, and everything the ledger claims can be checked by
calling `total()` and `latestPair(...)` on it.
