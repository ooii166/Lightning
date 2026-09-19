// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ArcFlow
 * @notice Cross-chain USDC price-spread and payment-cost ledger for Arc mainnet.
 * @dev Anyone can call `record(...)` to publish one observation; anyone can query.
 *      Stored as an append-only on-chain log so the data is verifiable end-to-end.
 *      Cost: a single SSTORE (~50k gas) paid in native USDC on Arc.
 *
 * Chain ID: Arc mainnet = 5042. Native gas: USDC (18 decimals on Arc).
 */
contract ArcFlow {
    /* ---------- Types ---------- */
    struct Observation {
        uint16  fromChain;      // see CHAIN_*
        uint16  toChain;        // see CHAIN_*
        int16   spreadBps;      // basis points (0.01%) signed: +ve = to is more expensive
        uint64  timestamp;      // block.timestamp at record()
        address reporter;       // who submitted (an agent, a wallet, a script)
    }

    /* ---------- Constants ---------- */
    // Indexed chain IDs (EVM-compatible). Match Arc Portal / Gateway list.
    uint16 public constant CHAIN_ARC        = 5042;
    uint16 public constant CHAIN_ETHEREUM   = 1;
    uint16 public constant CHAIN_BASE       = 8453;
    uint16 public constant CHAIN_OPTIMISM   = 10;
    uint16 public constant CHAIN_ARBITRUM   = 42161;
    uint16 public constant CHAIN_POLYGON    = 137;
    uint16 public constant CHAIN_AVALANCHE  = 43114;
    uint16 public constant CHAIN_BNB        = 56;
    uint16 public constant CHAIN_LINEA      = 59144;

    /* ---------- Storage ---------- */
    Observation[] public history;          // append-only log
    mapping(address => uint256) public reporterCount;  // total submissions per address

    /* ---------- Events ---------- */
    event ObservationRecorded(
        uint256 indexed idx,
        uint16  fromChain,
        uint16  toChain,
        int16   spreadBps,
        uint64  timestamp,
        address indexed reporter
    );

    /* ---------- Write ---------- */
    /// @notice Publish one observation. No fee — gas is the only cost (USDC).
    function record(uint16 fromChain, uint16 toChain, int16 spreadBps) external {
        require(fromChain != toChain, "ArcFlow: same chain");
        require(spreadBps >= -10000 && spreadBps <= 10000, "ArcFlow: spread out of range");
        history.push(Observation({
            fromChain: fromChain,
            toChain:   toChain,
            spreadBps: spreadBps,
            timestamp: uint64(block.timestamp),
            reporter:  msg.sender
        }));
        reporterCount[msg.sender] += 1;
        emit ObservationRecorded(
            history.length - 1,
            fromChain, toChain, spreadBps,
            uint64(block.timestamp),
            msg.sender
        );
    }

    /* ---------- Read ---------- */
    function total() external view returns (uint256) { return history.length; }

    function get(uint256 i) external view returns (Observation memory) { return history[i]; }

    /// @notice Most recent observation matching a given chain pair.
    function latestPair(uint16 fromChain, uint16 toChain)
        public
        view
        returns (int16 spreadBps, uint64 timestamp, address reporter, uint256 idx)
    {
        for (uint256 i = history.length; i > 0; i--) {
            Observation storage o = history[i - 1];
            if (o.fromChain == fromChain && o.toChain == toChain) {
                return (o.spreadBps, o.timestamp, o.reporter, i - 1);
            }
        }
        return (0, 0, address(0), type(uint256).max);
    }

    /// @notice Latest N observations as an array (newest first, max 50).
    function latestN(uint256 n) external view returns (Observation[] memory out) {
        require(n <= 50, "ArcFlow: max 50");
        uint256 total_ = history.length;
        uint256 take = n > total_ ? total_ : n;
        out = new Observation[](take);
        for (uint256 i = 0; i < take; i++) {
            out[i] = history[total_ - 1 - i];
        }
    }

    /// @notice Quick stats: latest spread for all 9 most common chain pairs.
    /// Returns two fixed arrays (spreads + timestamps) to stay under the
    /// Solidity stack limit that a flat 18-value return would hit.
    function snapshot9()
        external
        view
        returns (int16[9] memory spreads, uint64[9] memory timestamps)
    {
        (spreads[0], timestamps[0], , ) = _pair(CHAIN_ARC,      CHAIN_ETHEREUM);
        (spreads[1], timestamps[1], , ) = _pair(CHAIN_ARC,      CHAIN_BASE);
        (spreads[2], timestamps[2], , ) = _pair(CHAIN_ARC,      CHAIN_OPTIMISM);
        (spreads[3], timestamps[3], , ) = _pair(CHAIN_ARC,      CHAIN_ARBITRUM);
        (spreads[4], timestamps[4], , ) = _pair(CHAIN_ARC,      CHAIN_POLYGON);
        (spreads[5], timestamps[5], , ) = _pair(CHAIN_ARC,      CHAIN_AVALANCHE);
        (spreads[6], timestamps[6], , ) = _pair(CHAIN_ARC,      CHAIN_BNB);
        (spreads[7], timestamps[7], , ) = _pair(CHAIN_ARC,      CHAIN_LINEA);
        (spreads[8], timestamps[8], , ) = _pair(CHAIN_ETHEREUM, CHAIN_BASE);
    }

    function _pair(uint16 a, uint16 b) internal view returns (int16, uint64, address, uint256) {
        return latestPair(a, b);
    }
}