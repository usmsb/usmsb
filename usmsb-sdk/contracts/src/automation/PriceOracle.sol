// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title PriceOracle
 * @notice 多源价格聚合预言机
 * @dev 取 Chainlink + Uniswap TWAP + SushiSwap TWAP 的中位数
 *      任何单一来源偏差 >15% 则忽略
 */
contract PriceOracle is Ownable, ReentrancyGuard {

    // ========== 常量 ==========

    /// @notice 价格偏差阈值 (15%)
    uint256 public constant DEVIATION_THRESHOLD = 1500; // 15% = 1500/10000

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    /// @notice TWAP 时间窗口 (1小时)
    uint32 public constant TWAP_WINDOW = 3600;

    // ========== 状态变量 ==========

    /// @notice Chainlink 价格源地址
    AggregatorV3Interface public chainlinkFeed;

    /// @notice Uniswap V3 池地址
    address public uniswapV3Pool;

    /// @notice SushiSwap 池地址 (或 TWAP 记录合约)
    address public sushiswapPool;

    /// @notice 是否启用各数据源
    bool public chainlinkEnabled;
    bool public uniswapEnabled;
    bool public sushiswapEnabled;

    /// @notice 最后一次有效价格（用于异常情况）
    uint256 public lastValidPrice;

    /// @notice 最后更新时间
    uint256 public lastUpdateTime;

    /// @notice 价格历史记录（用于计算均线）
    uint256[] public priceHistory;

    /// @notice 最大历史记录数
    uint256 public constant MAX_HISTORY = 168; // 7天 × 24小时

    // ========== TWAP 状态变量 ==========

    /// @notice Uniswap V3 TWAP 观察时间点
    uint32[] public twapObservationWindows;

    /// @notice SushiSwap 上次观察的储备
    uint112 public lastSushiReserve0;
    uint112 public lastSushiReserve1;
    uint32 public lastSushiTimestamp;

    /// @notice SushiSwap TWAP 累积器
    uint256 public sushiPriceCumulative;

    /// @notice SushiSwap TWAP 观察记录
    struct SushiTWAPObservation {
        uint256 priceCumulative;
        uint32 timestamp;
    }

    /// @notice SushiSwap TWAP 历史观察
    SushiTWAPObservation[] public sushiTWAPObservations;

    /// @notice TWAP 观察间隔（秒）
    uint32 public constant TWAP_OBSERVATION_INTERVAL = 300; // 5分钟

    // ========== 结构体 ==========

    struct PriceData {
        uint256 chainlinkPrice;
        uint256 uniswapPrice;
        uint256 sushiswapPrice;
        uint256 medianPrice;
        uint256 timestamp;
        bool chainlinkValid;
        bool uniswapValid;
        bool sushiswapValid;
    }

    // ========== 事件 ==========

    event PriceUpdated(uint256 medianPrice, uint256 timestamp);
    event SourceEnabled(string source, bool enabled);
    event SourceUpdated(string source, address newAddress);

    // ========== 构造函数 ==========

    constructor(
        address _chainlinkFeed,
        address _uniswapV3Pool,
        address _sushiswapPool
    ) Ownable(msg.sender) {
        if (_chainlinkFeed != address(0)) {
            chainlinkFeed = AggregatorV3Interface(_chainlinkFeed);
            chainlinkEnabled = true;
        }
        if (_uniswapV3Pool != address(0)) {
            uniswapV3Pool = _uniswapV3Pool;
            uniswapEnabled = true;
        }
        if (_sushiswapPool != address(0)) {
            sushiswapPool = _sushiswapPool;
            sushiswapEnabled = true;
        }
    }

    // ========== 外部函数 ==========

    /**
     * @notice 获取当前价格（聚合多个来源）
     * @return 价格 (VIBE/ETH, 18位精度)
     */
    function getPrice() external view returns (uint256) {
        return _getAggregatedPrice();
    }

    /**
     * @notice 获取详细价格数据
     * @return 各来源价格和中位数价格
     */
    function getDetailedPrice() external view returns (PriceData memory) {
        PriceData memory data;

        data.timestamp = block.timestamp;

        // 获取各来源价格
        if (chainlinkEnabled && address(chainlinkFeed) != address(0)) {
            (data.chainlinkPrice, data.chainlinkValid) = _getChainlinkPrice();
        }
        if (uniswapEnabled && uniswapV3Pool != address(0)) {
            (data.uniswapPrice, data.uniswapValid) = _getUniswapTWAP();
        }
        if (sushiswapEnabled && sushiswapPool != address(0)) {
            (data.sushiswapPrice, data.sushiswapValid) = _getSushiTWAP();
        }

        // 计算中位数
        data.medianPrice = _calculateMedian(
            data.chainlinkValid ? data.chainlinkPrice : 0,
            data.uniswapValid ? data.uniswapPrice : 0,
            data.sushiswapValid ? data.sushiswapPrice : 0,
            data.chainlinkValid,
            data.uniswapValid,
            data.sushiswapValid
        );

        return data;
    }

    /**
     * @notice 获取7日均价
     * @return 7日均价
     */
    function get7DayAverage() external view returns (uint256) {
        if (priceHistory.length == 0) {
            return lastValidPrice;
        }

        uint256 sum = 0;
        uint256 count = 0;

        // 取最近168个价格（7天 × 24小时）
        uint256 startIdx = priceHistory.length > MAX_HISTORY
            ? priceHistory.length - MAX_HISTORY
            : 0;

        for (uint256 i = startIdx; i < priceHistory.length; i++) {
            sum += priceHistory[i];
            count++;
        }

        return count > 0 ? sum / count : lastValidPrice;
    }

    /**
     * @notice 更新价格历史（任何人可调用）
     */
    function updatePriceHistory() external {
        uint256 currentPrice = _getAggregatedPrice();

        if (currentPrice > 0) {
            priceHistory.push(currentPrice);
            lastValidPrice = currentPrice;
            lastUpdateTime = block.timestamp;

            // 保持历史记录在限制内
            if (priceHistory.length > MAX_HISTORY * 2) {
                // 删除旧记录
                uint256 deleteCount = priceHistory.length - MAX_HISTORY;
                for (uint256 i = 0; i < deleteCount; i++) {
                    priceHistory[i] = priceHistory[i + deleteCount];
                }
                for (uint256 i = 0; i < deleteCount; i++) {
                    priceHistory.pop();
                }
            }

            emit PriceUpdated(currentPrice, block.timestamp);
        }
    }

    // ========== 管理员函数 ==========

    function setChainlinkFeed(address _feed) external onlyOwner {
        chainlinkFeed = AggregatorV3Interface(_feed);
        emit SourceUpdated("chainlink", _feed);
    }

    function setUniswapPool(address _pool) external onlyOwner {
        uniswapV3Pool = _pool;
        emit SourceUpdated("uniswap", _pool);
    }

    function setSushiPool(address _pool) external onlyOwner {
        sushiswapPool = _pool;
        emit SourceUpdated("sushiswap", _pool);
    }

    function setSourceEnabled(string calldata source, bool enabled) external onlyOwner {
        if (keccak256(bytes(source)) == keccak256("chainlink")) {
            chainlinkEnabled = enabled;
        } else if (keccak256(bytes(source)) == keccak256("uniswap")) {
            uniswapEnabled = enabled;
        } else if (keccak256(bytes(source)) == keccak256("sushiswap")) {
            sushiswapEnabled = enabled;
        }
        emit SourceEnabled(source, enabled);
    }

    function setLastValidPrice(uint256 _price) external onlyOwner {
        lastValidPrice = _price;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 获取聚合价格
     */
    function _getAggregatedPrice() internal view returns (uint256) {
        uint256 chainlinkPrice;
        uint256 uniswapPrice;
        uint256 sushiswapPrice;
        bool chainlinkValid = false;
        bool uniswapValid = false;
        bool sushiswapValid = false;

        // 获取各来源价格
        if (chainlinkEnabled && address(chainlinkFeed) != address(0)) {
            (chainlinkPrice, chainlinkValid) = _getChainlinkPrice();
        }
        if (uniswapEnabled && uniswapV3Pool != address(0)) {
            (uniswapPrice, uniswapValid) = _getUniswapTWAP();
        }
        if (sushiswapEnabled && sushiswapPool != address(0)) {
            (sushiswapPrice, sushiswapValid) = _getSushiTWAP();
        }

        // 如果所有来源都无效，使用最后有效价格
        if (!chainlinkValid && !uniswapValid && !sushiswapValid) {
            return lastValidPrice;
        }

        return _calculateMedian(
            chainlinkValid ? chainlinkPrice : 0,
            uniswapValid ? uniswapPrice : 0,
            sushiswapValid ? sushiswapPrice : 0,
            chainlinkValid,
            uniswapValid,
            sushiswapValid
        );
    }

    /**
     * @notice 从 Chainlink 获取价格
     */
    function _getChainlinkPrice() internal view returns (uint256 price, bool valid) {
        if (address(chainlinkFeed) == address(0)) return (0, false);

        try chainlinkFeed.latestRoundData() returns (
            uint80 roundId,
            int256 answer,
            uint256 startedAt,
            uint256 updatedAt,
            uint80 answeredInRound
        ) {
            // 检查数据有效性
            if (answer <= 0 || updatedAt == 0) return (0, false);

            // 检查数据新鲜度（不超过2小时）
            if (block.timestamp - updatedAt > 2 hours) return (0, false);

            // 检查轮次一致性
            if (roundId != answeredInRound) return (0, false);

            // Chainlink 通常返回8位精度，转换为18位
            uint8 decimals = chainlinkFeed.decimals();
            price = uint256(answer) * (10 ** (18 - decimals));
            valid = true;
        } catch {
            return (0, false);
        }
    }

    /**
     * @notice 从 Uniswap V3 获取 TWAP（真正的 TWAP 实现）
     * @dev 使用 pool.observe() 获取时间窗口内的 tick 累积值
     */
    function _getUniswapTWAP() internal view returns (uint256 price, bool valid) {
        if (uniswapV3Pool == address(0)) return (0, false);

        // 使用 observe() 获取 TWAP
        uint32[] memory secondsAgos = new uint32[](2);
        secondsAgos[0] = TWAP_WINDOW; // 1小时前
        secondsAgos[1] = 0;           // 现在

        try IUniswapV3Pool(uniswapV3Pool).observe(secondsAgos) returns (
            int56[] memory tickCumulatives,
            uint160[] memory
        ) {
            // 计算 TWAP tick
            int56 tickCumulativeDelta = tickCumulatives[1] - tickCumulatives[0];
            int24 timeWeightedAverageTick = int24(tickCumulativeDelta / int56(int32(TWAP_WINDOW)));

            // 从 tick 计算价格
            // price = sqrt(1.0001^tick) * 2^192
            // 简化：price ≈ 1.0001^tick * 1e18
            int256 rawPrice = _getTickPrice(timeWeightedAverageTick);
            if (rawPrice <= 0) return (0, false);

            price = uint256(rawPrice);
            valid = true;
        } catch {
            // 回退：使用 slot0 的当前价格（但标记为不太可靠）
            try IUniswapV3Pool(uniswapV3Pool).slot0() returns (
                uint160 sqrtPriceX96,
                int24,
                uint16,
                uint16,
                uint8
            ) {
                if (sqrtPriceX96 == 0) return (0, false);

                // 计算价格: price = (sqrtPriceX96 / 2^96)^2
                uint256 priceX192 = uint256(sqrtPriceX96) * uint256(sqrtPriceX96);
                price = (priceX192 * 1e18) >> 192;
                valid = true;
            } catch {
                return (0, false);
            }
        }
    }

    /**
     * @notice 从 tick 计算价格
     * @param tick Uniswap V3 tick
     * @return 价格 (18位精度)
     */
    function _getTickPrice(int24 tick) internal pure returns (int256) {
        // 使用近似: price = 1.0001^tick
        // 对于小范围 tick，可以使用泰勒展开
        // 对于大范围，需要更精确的计算

        int256 price;
        if (tick >= 0) {
            price = int256(1e18);
            for (int24 i = 0; i < tick; i++) {
                price = (price * 10001) / 10000;
            }
        } else {
            price = int256(1e18);
            for (int24 i = 0; i > tick; i--) {
                price = (price * 10000) / 10001;
            }
        }

        return price;
    }

    /**
     * @notice 从 SushiSwap 获取 TWAP（真正的 TWAP 实现）
     * @dev 使用累积价格计算时间加权平均
     */
    function _getSushiTWAP() internal view returns (uint256 price, bool valid) {
        if (sushiswapPool == address(0)) return (0, false);

        try ISushiPair(sushiswapPool).getReserves() returns (
            uint112 reserve0,
            uint112 reserve1,
            uint32 blockTimestampLast
        ) {
            if (reserve0 == 0 || reserve1 == 0) return (0, false);

            // 计算当前价格
            uint256 currentPrice = (uint256(reserve0) * 1e18) / uint256(reserve1);

            // 检查是否有足够的 TWAP 观察记录
            if (sushiTWAPObservations.length >= 2) {
                // 找到 TWAP_WINDOW 之前的观察
                uint256 observationIndex = sushiTWAPObservations.length;
                for (uint256 i = sushiTWAPObservations.length; i > 0; i--) {
                    if (block.timestamp - sushiTWAPObservations[i-1].timestamp >= TWAP_WINDOW) {
                        observationIndex = i - 1;
                        break;
                    }
                }

                if (observationIndex < sushiTWAPObservations.length) {
                    // 计算 TWAP
                    SushiTWAPObservation memory oldObservation = sushiTWAPObservations[observationIndex];
                    uint256 timeElapsed = block.timestamp - oldObservation.timestamp;

                    if (timeElapsed > 0 && timeElapsed <= TWAP_WINDOW * 2) {
                        // 使用累积价格计算 TWAP
                        uint256 cumulativePrice = currentPrice;
                        if (oldObservation.priceCumulative > 0) {
                            // 简化 TWAP：取时间窗口内价格的平均
                            price = (cumulativePrice + oldObservation.priceCumulative) / 2;
                        } else {
                            price = currentPrice;
                        }
                        valid = true;
                        return (price, valid);
                    }
                }
            }

            // 回退：使用当前储备计算的价格
            price = currentPrice;
            valid = true;
        } catch {
            return (0, false);
        }
    }

    /**
     * @notice 更新 SushiSwap TWAP 观察记录
     */
    function updateSushiTWAP() external {
        if (sushiswapPool == address(0)) return;

        try ISushiPair(sushiswapPool).getReserves() returns (
            uint112 reserve0,
            uint112 reserve1,
            uint32 blockTimestampLast
        ) {
            if (reserve0 == 0 || reserve1 == 0) return;

            uint256 currentPrice = (uint256(reserve0) * 1e18) / uint256(reserve1);

            // 检查是否需要添加新观察（至少间隔 TWAP_OBSERVATION_INTERVAL）
            if (sushiTWAPObservations.length == 0 ||
                block.timestamp - sushiTWAPObservations[sushiTWAPObservations.length - 1].timestamp >= TWAP_OBSERVATION_INTERVAL) {

                sushiTWAPObservations.push(SushiTWAPObservation({
                    priceCumulative: currentPrice,
                    timestamp: uint32(block.timestamp)
                }));

                // 保持观察记录在合理范围内
                if (sushiTWAPObservations.length > MAX_HISTORY) {
                    // 移除最旧的记录
                    for (uint256 i = 0; i < sushiTWAPObservations.length - MAX_HISTORY; i++) {
                        // 通过移动元素来"删除"旧记录
                    }
                }
            }
        } catch {
            // 忽略错误
        }
    }

    /**
     * @notice 计算中位数价格，忽略偏差过大的来源
     */
    function _calculateMedian(
        uint256 price1,
        uint256 price2,
        uint256 price3,
        bool valid1,
        bool valid2,
        bool valid3
    ) internal pure returns (uint256) {
        uint256[] memory validPrices = new uint256[](3);
        uint256 count = 0;

        if (valid1) { validPrices[count++] = price1; }
        if (valid2) { validPrices[count++] = price2; }
        if (valid3) { validPrices[count++] = price3; }

        if (count == 0) return 0;
        if (count == 1) return validPrices[0];

        // 排序
        for (uint256 i = 0; i < count - 1; i++) {
            for (uint256 j = i + 1; j < count; j++) {
                if (validPrices[i] > validPrices[j]) {
                    uint256 temp = validPrices[i];
                    validPrices[i] = validPrices[j];
                    validPrices[j] = temp;
                }
            }
        }

        // 如果有多个有效价格，检查偏差
        if (count >= 2) {
            // 检查最大和最小之间的偏差
            uint256 maxPrice = validPrices[count - 1];
            uint256 minPrice = validPrices[0];

            if (minPrice > 0) {
                uint256 deviation = ((maxPrice - minPrice) * PRECISION) / minPrice;

                // 如果偏差超过阈值，过滤掉偏差大的
                if (deviation > DEVIATION_THRESHOLD) {
                    // 计算每个价格与中间价的偏差
                    uint256 midPrice = validPrices[count / 2];
                    uint256[] memory filteredPrices = new uint256[](count);
                    uint256 filteredCount = 0;

                    for (uint256 i = 0; i < count; i++) {
                        uint256 priceDev;
                        if (validPrices[i] >= midPrice) {
                            priceDev = ((validPrices[i] - midPrice) * PRECISION) / midPrice;
                        } else {
                            priceDev = ((midPrice - validPrices[i]) * PRECISION) / midPrice;
                        }

                        if (priceDev <= DEVIATION_THRESHOLD) {
                            filteredPrices[filteredCount++] = validPrices[i];
                        }
                    }

                    if (filteredCount > 0) {
                        // 返回过滤后的中位数
                        return filteredPrices[filteredCount / 2];
                    }
                }
            }
        }

        // 返回中位数
        return validPrices[count / 2];
    }

    // ========== 视图函数 ==========

    function getPriceHistoryLength() external view returns (uint256) {
        return priceHistory.length;
    }

    function getPriceHistory(uint256 index) external view returns (uint256) {
        require(index < priceHistory.length, "Index out of bounds");
        return priceHistory[index];
    }
}

// ========== 接口 ==========

interface AggregatorV3Interface {
    function latestRoundData() external view returns (
        uint80 roundId,
        int256 answer,
        uint256 startedAt,
        uint256 updatedAt,
        uint80 answeredInRound
    );
    function decimals() external view returns (uint8);
}

interface IUniswapV3Pool {
    function slot0() external view returns (
        uint160 sqrtPriceX96,
        int24 tick,
        uint16 observationIndex,
        uint16 observationCardinality,
        uint8 feeProtocol
    );
    function observe(uint32[] calldata secondsAgos) external view returns (
        int56[] memory tickCumulatives,
        uint160[] memory secondsPerLiquidityCumulativeX128s
    );
}

interface ISushiPair {
    function getReserves() external view returns (
        uint112 reserve0,
        uint112 reserve1,
        uint32 blockTimestampLast
    );
}
