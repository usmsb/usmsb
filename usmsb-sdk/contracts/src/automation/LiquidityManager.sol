// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title LiquidityManager
 * @notice DEX流动性管理合约
 * @dev 功能：
 *      - 初始添加流动性 1.2亿 VIBE
 *      - LP代币永久锁定（不可提取）
 *      - 交易费收益自动复投
 *      - 完全去中心化，无人为干预
 */
contract LiquidityManager is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 最小复投间隔 (7天)
    uint256 public constant MIN_REINVEST_INTERVAL = 7 days;

    /// @notice 复投触发奖励
    uint256 public constant REINVEST_REWARD = 0.001 ether;

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币
    IERC20 public vibeToken;

    /// @notice WETH
    IERC20 public weth;

    /// @notice DEX 路由器
    address public dexRouter;

    /// @notice DEX 工厂
    address public dexFactory;

    /// @notice LP 代币
    IERC20 public lpToken;

    /// @notice 是否已初始化
    bool public initialized;

    /// @notice 上次复投时间
    uint256 public lastReinvestTime;

    /// @notice 总添加的 VIBE 数量
    uint256 public totalVibeAdded;

    /// @notice 总添加的 ETH 数量
    uint256 public totalEthAdded;

    /// @notice 总复投次数
    uint256 public reinvestCount;

    /// @notice 累计复投的 LP 数量
    uint256 public totalReinvestedLP;

    /// @notice 累计手动添加流动性获得的 LP 数量
    uint256 public totalManualLP;

    /// @notice 复投记录
    ReinvesrRecord[] public reinvestRecords;

    // ========== 结构体 ==========

    struct ReinvesrRecord {
        uint256 vibeAmount;
        uint256 ethAmount;
        uint256 lpReceived;
        uint256 timestamp;
        address trigger;
    }

    // ========== 事件 ==========

    event LiquidityAdded(
        uint256 vibeAmount,
        uint256 ethAmount,
        uint256 lpReceived,
        bool isInitial
    );

    event Reinvested(
        uint256 vibeAmount,
        uint256 ethAmount,
        uint256 lpReceived,
        address indexed trigger
    );

    event FeesCollected(
        uint256 vibeFees,
        uint256 ethFees
    );

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _weth,
        address _dexRouter,
        address _dexFactory
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "Invalid token");
        require(_weth != address(0), "Invalid WETH");
        require(_dexRouter != address(0), "Invalid router");
        require(_dexFactory != address(0), "Invalid factory");

        vibeToken = IERC20(_vibeToken);
        weth = IERC20(_weth);
        dexRouter = _dexRouter;
        dexFactory = _dexFactory;
    }

    // ========== 接收 ETH ==========

    receive() external payable {}

    // ========== 外部函数 ==========

    /**
     * @notice 初始化添加流动性
     * @dev 只能调用一次，创建新的交易对
     * @param vibeAmount VIBE 数量
     * @param ethAmount ETH 数量
     */
    function initializeLiquidity(
        uint256 vibeAmount,
        uint256 ethAmount
    ) external payable onlyOwner nonReentrant {
        require(!initialized, "Already initialized");
        require(vibeAmount > 0, "Invalid VIBE amount");
        require(ethAmount > 0 || msg.value > 0, "Invalid ETH amount");

        // 使用 msg.value 或传入的 ethAmount
        uint256 ethToUse = msg.value > 0 ? msg.value : ethAmount;

        // 转入 VIBE
        vibeToken.safeTransferFrom(msg.sender, address(this), vibeAmount);

        // 获取或创建 LP 代币地址
        address lpTokenAddress = _getOrCreatePair();
        lpToken = IERC20(lpTokenAddress);

        // 批准路由器
        vibeToken.forceApprove(dexRouter, vibeAmount);

        // 添加流动性
        (uint256 vibeUsed, uint256 ethUsed, uint256 lpReceived) =
            IDEXRouter(dexRouter).addLiquidityETH{value: ethToUse}(
                address(vibeToken),
                vibeAmount,
                vibeAmount * 95 / 100, // 最小95%
                ethToUse * 95 / 100,
                address(this), // LP 发送到本合约（永久锁定）
                block.timestamp + 300
            );

        // 清除批准
        vibeToken.forceApprove(dexRouter, 0);

        // 更新状态
        initialized = true;
        totalVibeAdded = vibeUsed;
        totalEthAdded = ethUsed;
        lastReinvestTime = block.timestamp;

        // LP 代币永久锁定在本合约，无法提取

        emit LiquidityAdded(vibeUsed, ethUsed, lpReceived, true);
    }

    /**
     * @notice 自动复投收益
     * @dev 使用合约中积累的 VIBE 和 ETH 添加流动性，不移除 LP
     */
    function autoReinvest() external nonReentrant whenNotPaused {
        require(initialized, "Not initialized");
        require(
            block.timestamp >= lastReinvestTime + MIN_REINVEST_INTERVAL,
            "Too frequent"
        );

        // 获取合约中可用于复投的余额
        uint256 vibeBalance = vibeToken.balanceOf(address(this));
        uint256 ethBalance = address(this).balance;

        // 如果余额太少，跳过
        if (vibeBalance < 1000 * 10**18 || ethBalance < 0.001 ether) {
            emit FeesCollected(vibeBalance, ethBalance);
            return;
        }

        // 使用部分余额添加流动性（保留一些 ETH 用于奖励）
        uint256 ethToUse = ethBalance > REINVEST_REWARD ? ethBalance - REINVEST_REWARD : ethBalance;
        uint256 vibeToUse = _calculateVibeAmount(ethToUse);

        // 确保 VIBE 余额足够
        if (vibeToUse > vibeBalance) {
            vibeToUse = vibeBalance;
        }

        if (vibeToUse == 0 || ethToUse == 0) {
            emit FeesCollected(vibeBalance, ethBalance);
            return;
        }

        // 复投
        _reinvest(vibeToUse, ethToUse);

        // 更新状态
        lastReinvestTime = block.timestamp;
        reinvestCount++;

        // 支付触发者奖励
        _payReward();
    }

    /**
     * @notice 手动添加更多流动性（仅 owner）
     * @param vibeAmount VIBE 数量
     */
    function addMoreLiquidity(uint256 vibeAmount) external payable onlyOwner nonReentrant {
        require(initialized, "Not initialized");
        require(vibeAmount > 0, "Invalid amount");
        require(msg.value > 0, "No ETH provided");

        // 转入 VIBE
        vibeToken.safeTransferFrom(msg.sender, address(this), vibeAmount);

        // 批准路由器
        vibeToken.forceApprove(dexRouter, vibeAmount);

        // 添加流动性
        (uint256 vibeUsed, uint256 ethUsed, uint256 lpReceived) =
            IDEXRouter(dexRouter).addLiquidityETH{value: msg.value}(
                address(vibeToken),
                vibeAmount,
                vibeAmount * 95 / 100,
                msg.value * 95 / 100,
                address(this),
                block.timestamp + 300
            );

        // 清除批准
        vibeToken.forceApprove(dexRouter, 0);

        // 更新状态
        totalVibeAdded += vibeUsed;
        totalEthAdded += ethUsed;
        totalManualLP += lpReceived;

        emit LiquidityAdded(vibeUsed, ethUsed, lpReceived, false);
    }

    /**
     * @notice 检查是否可以复投
     */
    function canReinvest() external view returns (bool, string memory) {
        if (!initialized) {
            return (false, "Not initialized");
        }
        if (block.timestamp < lastReinvestTime + MIN_REINVEST_INTERVAL) {
            return (false, "Too frequent");
        }

        // 检查合约余额
        uint256 vibeBalance = vibeToken.balanceOf(address(this));
        uint256 ethBalance = address(this).balance;

        if (vibeBalance < 1000 * 10**18 || ethBalance < 0.001 ether) {
            return (false, "Balance too low");
        }

        return (true, "Can reinvest");
    }

    // ========== 管理员函数 ==========

    function setDexRouter(address _router) external onlyOwner {
        require(_router != address(0), "Invalid router");
        dexRouter = _router;
    }

    function setDexFactory(address _factory) external onlyOwner {
        require(_factory != address(0), "Invalid factory");
        dexFactory = _factory;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 紧急提取错误发送的代币（非 LP 代币）
     * @dev LP 代币永远不能提取
     */
    function emergencyWithdraw(address token) external onlyOwner {
        require(token != address(lpToken), "Cannot withdraw LP");
        require(token != address(vibeToken) || !initialized, "Cannot withdraw VIBE after init");

        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20(token).safeTransfer(owner(), balance);
        }
    }

    /**
     * @notice 紧急提取 ETH
     */
    function emergencyWithdrawETH() external onlyOwner {
        uint256 balance = address(this).balance;
        if (balance > 0) {
            payable(owner()).transfer(balance);
        }
    }

    // ========== 内部函数 ==========

    /**
     * @notice 获取或创建交易对
     */
    function _getOrCreatePair() internal returns (address) {
        address pair = IDEXFactory(dexFactory).getPair(address(vibeToken), address(weth));

        if (pair == address(0)) {
            pair = IDEXFactory(dexFactory).createPair(address(vibeToken), address(weth));
        }

        return pair;
    }

    /**
     * @notice 根据 ETH 数量计算需要的 VIBE 数量
     * @dev 基于当前池子储备比例
     */
    function _calculateVibeAmount(uint256 ethAmount) internal view returns (uint256) {
        if (address(lpToken) == address(0)) {
            return 0;
        }

        try ISushiPair(address(lpToken)).getReserves() returns (
            uint112 reserve0,
            uint112 reserve1,
            uint32
        ) {
            if (reserve0 == 0 || reserve1 == 0) {
                return 0;
            }
            // reserve0 = ETH, reserve1 = VIBE
            // vibeAmount = ethAmount * reserve1 / reserve0
            return (ethAmount * uint256(reserve1)) / uint256(reserve0);
        } catch {
            return 0;
        }
    }

    /**
     * @notice 复投收益
     */
    function _reinvest(uint256 vibeAmount, uint256 ethAmount) internal {
        // 批准路由器
        vibeToken.forceApprove(dexRouter, vibeAmount);

        // 添加流动性
        (uint256 vibeUsed, uint256 ethUsed, uint256 lpReceived) =
            IDEXRouter(dexRouter).addLiquidityETH{value: ethAmount}(
                address(vibeToken),
                vibeAmount,
                vibeAmount * 95 / 100,
                ethAmount * 95 / 100,
                address(this), // LP 继续锁定
                block.timestamp + 300
            );

        // 清除批准
        vibeToken.forceApprove(dexRouter, 0);

        // 更新统计
        totalVibeAdded += vibeUsed;
        totalEthAdded += ethUsed;
        totalReinvestedLP += lpReceived;

        // 记录复投
        reinvestRecords.push(ReinvesrRecord({
            vibeAmount: vibeUsed,
            ethAmount: ethUsed,
            lpReceived: lpReceived,
            timestamp: block.timestamp,
            trigger: msg.sender
        }));

        emit Reinvested(vibeUsed, ethUsed, lpReceived, msg.sender);
    }

    /**
     * @notice 支付触发者奖励
     */
    function _payReward() internal {
        if (address(this).balance >= REINVEST_REWARD) {
            payable(msg.sender).transfer(REINVEST_REWARD);
        }
    }

    // ========== 视图函数 ==========

    function getStats() external view returns (
        uint256 _totalVibeAdded,
        uint256 _totalEthAdded,
        uint256 _lpBalance,
        uint256 _totalReinvestedLP,
        uint256 _totalManualLP,
        uint256 _reinvestCount,
        uint256 _lastReinvestTime
    ) {
        _totalVibeAdded = totalVibeAdded;
        _totalEthAdded = totalEthAdded;
        _lpBalance = initialized ? lpToken.balanceOf(address(this)) : 0;
        _totalReinvestedLP = totalReinvestedLP;
        _totalManualLP = totalManualLP;
        _reinvestCount = reinvestCount;
        _lastReinvestTime = lastReinvestTime;
    }

    function getReinvestRecordCount() external view returns (uint256) {
        return reinvestRecords.length;
    }

    function getReinvestRecord(uint256 index) external view returns (ReinvesrRecord memory) {
        require(index < reinvestRecords.length, "Index out of bounds");
        return reinvestRecords[index];
    }

    /**
     * @notice 获取 LP 价值（以 ETH 计）
     */
    function getLPValueInETH() external view returns (uint256) {
        uint256 lpBalance = lpToken.balanceOf(address(this));
        uint256 totalLPSupply = lpToken.totalSupply();

        if (totalLPSupply == 0 || lpBalance == 0) {
            return 0;
        }

        // 获取池子中的 ETH 储备
        (uint112 reserve0,,) = ISushiPair(address(lpToken)).getReserves();

        // LP 价值 ≈ 2 * (ETH 储备 * LP 份额 / 总 LP)
        return (uint256(reserve0) * 2 * lpBalance) / totalLPSupply;
    }

    /**
     * @notice 获取下次可复投时间
     */
    function getNextReinvestTime() external view returns (uint256) {
        return lastReinvestTime + MIN_REINVEST_INTERVAL;
    }
}

// ========== 接口 ==========

interface IDEXRouter {
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

    function removeLiquidityETH(
        address token,
        uint256 liquidity,
        uint256 amountTokenMin,
        uint256 amountETHMin,
        address to,
        uint256 deadline
    ) external returns (
        uint256 amountToken,
        uint256 amountETH
    );
}

interface IDEXFactory {
    function getPair(address tokenA, address tokenB) external view returns (address);
    function createPair(address tokenA, address tokenB) external returns (address);
}

interface ISushiPair {
    function getReserves() external view returns (
        uint112 reserve0,
        uint112 reserve1,
        uint32 blockTimestampLast
    );
}
