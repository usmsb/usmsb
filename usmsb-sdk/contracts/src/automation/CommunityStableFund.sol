// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title CommunityStableFund
 * @notice 社区稳定基金合约
 * @dev 功能：
 *      - 护盘回购：价格下跌20%自动触发回购销毁
 *      - 流动性注入：DEX流动性低于阈值时自动注入
 *      - 完全自动化，无人为干预
 */
contract CommunityStableFund is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 回购触发阈值 (价格下跌20%)
    uint256 public constant DEFAULT_BUYBACK_THRESHOLD = 2000; // 20% = 2000/10000

    /// @notice 最小触发间隔 (24小时)
    uint256 public constant MIN_TRIGGER_INTERVAL = 24 hours;

    /// @notice 触发奖励参数
    uint256 public constant BASE_REWARD = 0.0005 ether;
    uint256 public constant GAS_BONUS_PERCENT = 20;
    uint256 public constant ACCUMULATION_RATE = 0.0001 ether;
    uint256 public constant MAX_ACCUMULATED_HOURS = 24;

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币
    IERC20 public vibeToken;

    /// @notice WETH
    IERC20 public weth;

    /// @notice 价格预言机
    address public priceOracle;

    /// @notice DEX 路由器
    address public dexRouter;

    /// @notice 回购触发阈值 (可治理调整)
    uint256 public buybackThreshold;

    /// @notice 最小流动性阈值
    uint256 public minLiquidityThreshold;

    /// @notice 上次触发时间
    uint256 public lastTriggerTime;

    /// @notice 总回购量
    uint256 public totalBuyback;

    /// @notice 总销毁量
    uint256 public totalBurned;

    /// @notice 总注入流动性量
    uint256 public totalLiquidityAdded;

    /// @notice 操作记录
    OperationRecord[] public operationRecords;

    // ========== 结构体 ==========

    struct OperationRecord {
        uint8 operationType; // 0=buyback, 1=liquidity
        uint256 amount;
        uint256 timestamp;
        address trigger;
        uint256 priceBefore;
        uint256 priceAfter;
    }

    // ========== 事件 ==========

    event BuybackExecuted(
        uint256 ethSpent,
        uint256 vibeBought,
        uint256 vibeBurned,
        address indexed trigger
    );

    event LiquidityAdded(
        uint256 vibeAmount,
        uint256 ethAmount,
        uint256 lpReceived,
        address indexed trigger
    );

    event ThresholdUpdated(string thresholdType, uint256 newValue);

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _weth,
        address _priceOracle,
        address _dexRouter,
        uint256 _minLiquidityThreshold
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "Invalid token");
        require(_weth != address(0), "Invalid WETH");
        require(_priceOracle != address(0), "Invalid oracle");
        require(_dexRouter != address(0), "Invalid router");

        vibeToken = IERC20(_vibeToken);
        weth = IERC20(_weth);
        priceOracle = _priceOracle;
        dexRouter = _dexRouter;
        buybackThreshold = DEFAULT_BUYBACK_THRESHOLD;
        minLiquidityThreshold = _minLiquidityThreshold;
    }

    // ========== 接收 ETH ==========

    receive() external payable {}

    // ========== 外部函数 ==========

    /**
     * @notice 自动回购
     * @dev 价格下跌超过阈值时，任何人都可以触发
     */
    function autoBuyback() external nonReentrant whenNotPaused {
        require(address(this).balance > 0, "No ETH balance");

        // 检查触发间隔
        require(
            block.timestamp >= lastTriggerTime + MIN_TRIGGER_INTERVAL,
            "Too frequent"
        );

        // 获取价格数据
        (uint256 currentPrice, uint256 avgPrice) = _getPriceData();

        // 检查是否满足回购条件
        require(
            currentPrice < (avgPrice * (PRECISION - buybackThreshold)) / PRECISION,
            "Price not low enough"
        );

        // 计算回购金额（使用50%的ETH余额）
        uint256 ethToSpend = address(this).balance / 2;

        // 执行回购
        uint256 vibeBought = _executeBuyback(ethToSpend);

        // 销毁回购的 VIBE
        IBurnable(address(vibeToken)).burn(vibeBought);

        // 记录操作
        uint256 newPrice = _getCurrentPrice();
        operationRecords.push(OperationRecord({
            operationType: 0,
            amount: vibeBought,
            timestamp: block.timestamp,
            trigger: msg.sender,
            priceBefore: currentPrice,
            priceAfter: newPrice
        }));

        // 支付触发者奖励（在更新 lastTriggerTime 之前）
        _payTriggerReward();

        // 更新状态
        totalBuyback += ethToSpend;
        totalBurned += vibeBought;
        lastTriggerTime = block.timestamp;

        emit BuybackExecuted(ethToSpend, vibeBought, vibeBought, msg.sender);
    }

    /**
     * @notice 自动注入流动性
     * @dev DEX流动性低于阈值时，任何人都可以触发
     */
    function autoInjectLiquidity() external nonReentrant whenNotPaused {
        // 检查当前流动性
        uint256 currentLiquidity = _getDEXLiquidity();
        require(currentLiquidity < minLiquidityThreshold, "Liquidity sufficient");

        // 计算注入量（使用33%的余额）
        uint256 ethAmount = address(this).balance / 3;
        uint256 vibeAmount = _calculateVibeAmount(ethAmount);

        // 检查 VIBE 余额
        uint256 vibeBalance = vibeToken.balanceOf(address(this));
        if (vibeAmount > vibeBalance) {
            vibeAmount = vibeBalance;
        }

        require(vibeAmount > 0 && ethAmount > 0, "Insufficient balance");

        // 执行添加流动性
        uint256 lpReceived = _addLiquidity(vibeAmount, ethAmount);

        // 记录操作
        operationRecords.push(OperationRecord({
            operationType: 1,
            amount: vibeAmount,
            timestamp: block.timestamp,
            trigger: msg.sender,
            priceBefore: 0,
            priceAfter: 0
        }));

        // 支付触发者奖励（在更新 lastTriggerTime 之前）
        _payTriggerReward();

        // 更新状态
        totalLiquidityAdded += vibeAmount;
        lastTriggerTime = block.timestamp;

        emit LiquidityAdded(vibeAmount, ethAmount, lpReceived, msg.sender);
    }

    /**
     * @notice 检查是否可以触发回购
     */
    function canTriggerBuyback() external view returns (bool, string memory) {
        if (address(this).balance == 0) {
            return (false, "No ETH balance");
        }
        if (block.timestamp < lastTriggerTime + MIN_TRIGGER_INTERVAL) {
            return (false, "Too frequent");
        }

        (uint256 currentPrice, uint256 avgPrice) = _getPriceData();
        uint256 threshold = (avgPrice * (PRECISION - buybackThreshold)) / PRECISION;

        if (currentPrice >= threshold) {
            return (false, "Price not low enough");
        }

        return (true, "Can trigger");
    }

    /**
     * @notice 检查是否可以注入流动性
     */
    function canInjectLiquidity() external view returns (bool, string memory) {
        uint256 currentLiquidity = _getDEXLiquidity();
        if (currentLiquidity >= minLiquidityThreshold) {
            return (false, "Liquidity sufficient");
        }
        if (address(this).balance == 0) {
            return (false, "No ETH balance");
        }
        return (true, "Can trigger");
    }

    // ========== 管理员函数 ==========

    function setBuybackThreshold(uint256 _threshold) external onlyOwner {
        require(_threshold >= 1000 && _threshold <= 3000, "Invalid threshold"); // 10%-30%
        buybackThreshold = _threshold;
        emit ThresholdUpdated("buyback", _threshold);
    }

    function setMinLiquidityThreshold(uint256 _threshold) external onlyOwner {
        minLiquidityThreshold = _threshold;
        emit ThresholdUpdated("liquidity", _threshold);
    }

    function setPriceOracle(address _oracle) external onlyOwner {
        priceOracle = _oracle;
    }

    function setDexRouter(address _router) external onlyOwner {
        dexRouter = _router;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 接收 VIBE 代币
     */
    function receiveVIBE(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /**
     * @notice 接收 ETH
     */
    function receiveETH() external payable {}

    // ========== 内部函数 ==========

    /**
     * @notice 获取价格数据
     */
    function _getPriceData() internal view returns (uint256 currentPrice, uint256 avgPrice) {
        IPriceOracle oracle = IPriceOracle(priceOracle);
        currentPrice = oracle.getPrice();
        avgPrice = oracle.get7DayAverage();
    }

    /**
     * @notice 获取当前价格
     */
    function _getCurrentPrice() internal view returns (uint256) {
        return IPriceOracle(priceOracle).getPrice();
    }

    /**
     * @notice 获取 DEX 流动性
     * @dev 通过工厂合约查询 VIBE-WETH 配对地址，获取实际流动性储备
     * @return totalLiquidity USD价值估算的流动性总额
     */
    function _getDEXLiquidity() internal view returns (uint256) {
        // 获取工厂地址
        address factory = IDEXRouter(dexRouter).factory();

        // 获取 VIBE-WETH 配对地址
        address pair = IDEXFactory(factory).getPair(address(vibeToken), address(weth));

        // 如果配对不存在，返回0
        if (pair == address(0)) {
            return 0;
        }

        // 获取储备量
        (uint112 reserve0, uint112 reserve1, ) = IDEXPair(pair).getReserves();

        // 确定哪个是VIBE，哪个是WETH
        address token0 = IDEXPair(pair).token0();
        uint256 vibeReserve;
        uint256 wethReserve;

        if (token0 == address(vibeToken)) {
            vibeReserve = reserve0;
            wethReserve = reserve1;
        } else {
            vibeReserve = reserve1;
            wethReserve = reserve0;
        }

        // 获取当前价格计算流动性USD价值
        uint256 currentPrice = _getCurrentPrice();
        if (currentPrice == 0) {
            // 如果价格查询失败，返回VIBE储备量作为近似值
            return vibeReserve;
        }

        // 流动性 = VIBE储备 + WETH储备 × 价格
        // 假设价格是 VIBE/ETH，即 1 VIBE = price ETH
        // 将WETH转换为VIBE等价物: wethReserve / (10^decimals) * price
        uint256 wethValueInVibe = (wethReserve * 1e18) / currentPrice;
        uint256 totalLiquidity = vibeReserve + wethValueInVibe;

        return totalLiquidity;
    }

    /**
     * @notice 执行回购
     */
    function _executeBuyback(uint256 ethAmount) internal returns (uint256) {
        uint256 vibeBalanceBefore = vibeToken.balanceOf(address(this));

        // 通过 DEX 买入 VIBE
        address[] memory path = new address[](2);
        path[0] = address(weth);
        path[1] = address(vibeToken);

        IDEXRouter(dexRouter).swapExactETHForTokens{value: ethAmount}(
            0, // 接受任何数量
            path,
            address(this),
            block.timestamp + 300
        );

        uint256 vibeBalanceAfter = vibeToken.balanceOf(address(this));
        return vibeBalanceAfter - vibeBalanceBefore;
    }

    /**
     * @notice 计算 VIBE 金额
     */
    function _calculateVibeAmount(uint256 ethAmount) internal view returns (uint256) {
        uint256 price = _getCurrentPrice();
        if (price == 0) return 0;
        // VIBE 数量 = ETH 数量 / 价格
        return (ethAmount * 1e18) / price;
    }

    /**
     * @notice 添加流动性
     */
    function _addLiquidity(uint256 vibeAmount, uint256 ethAmount) internal returns (uint256) {
        // 批准 DEX
        vibeToken.forceApprove(dexRouter, vibeAmount);

        // 添加流动性
        (uint256 vibeUsed, uint256 ethUsed, uint256 liquidity) =
            IDEXRouter(dexRouter).addLiquidityETH{value: ethAmount}(
                address(vibeToken),
                vibeAmount,
                vibeAmount * 90 / 100, // 最小90%
                ethAmount * 90 / 100,
                address(this), // LP 发送到本合约（永久锁定）
                block.timestamp + 300
            );

        // 清除批准
        vibeToken.forceApprove(dexRouter, 0);

        // LP 代币永久锁定在本合约，无法提取

        return liquidity;
    }

    /**
     * @notice 支付触发者奖励
     * @dev 奖励 = 基础奖励 + Gas补贴 + 时间累积奖励
     *      Gas补贴 = 估算Gas成本 × 120%
     */
    function _payTriggerReward() internal {
        uint256 hoursSinceLastTrigger = (block.timestamp - lastTriggerTime) / 1 hours;
        if (hoursSinceLastTrigger > MAX_ACCUMULATED_HOURS) {
            hoursSinceLastTrigger = MAX_ACCUMULATED_HOURS;
        }

        // 时间累积奖励
        uint256 timeBonus = hoursSinceLastTrigger * ACCUMULATION_RATE;

        // Gas补贴：估算约21000 Gas × 120%
        uint256 estimatedGasCost = 21000 * 30 gwei;
        uint256 gasBonus = (estimatedGasCost * (100 + GAS_BONUS_PERCENT)) / 100;

        uint256 reward = BASE_REWARD + gasBonus + timeBonus;

        if (address(this).balance >= reward) {
            payable(msg.sender).transfer(reward);
        }
    }

    // ========== 视图函数 ==========

    function getStats() external view returns (
        uint256 _totalBuyback,
        uint256 _totalBurned,
        uint256 _totalLiquidityAdded,
        uint256 _ethBalance,
        uint256 _vibeBalance
    ) {
        _totalBuyback = totalBuyback;
        _totalBurned = totalBurned;
        _totalLiquidityAdded = totalLiquidityAdded;
        _ethBalance = address(this).balance;
        _vibeBalance = vibeToken.balanceOf(address(this));
    }

    function getOperationCount() external view returns (uint256) {
        return operationRecords.length;
    }

    function getOperation(uint256 index) external view returns (OperationRecord memory) {
        require(index < operationRecords.length, "Index out of bounds");
        return operationRecords[index];
    }
}

// ========== 接口 ==========

interface IPriceOracle {
    function getPrice() external view returns (uint256);
    function get7DayAverage() external view returns (uint256);
}

interface IDEXRouter {
    function swapExactETHForTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable returns (uint256[] memory amounts);

    function addLiquidityETH(
        address token,
        uint256 amountTokenDesired,
        uint256 amountTokenMin,
        uint256 amountETHMin,
        address to,
        uint256 deadline
    ) external payable returns (
        uint256 amountToken,
        uint256 amountETH,
        uint256 liquidity
    );

    function factory() external view returns (address);
}

interface IDEXFactory {
    function getPair(address tokenA, address tokenB) external view returns (address);
}

interface IDEXPair {
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
    function token0() external view returns (address);
}

// VIBE Token 需要有 burn 函数
interface IBurnable {
    function burn(uint256 amount) external;
}
