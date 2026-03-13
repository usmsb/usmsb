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

    /// @notice 投资人最小ETH贡献 (0.1 ETH)
    uint256 public constant MIN_ETH_CONTRIBUTION = 0.1 ether;

    /// @notice 投资人最大ETH贡献 (10 ETH)
    uint256 public constant MAX_ETH_CONTRIBUTION = 10 ether;

    /// @notice 滑点保护阈值 (95%) - L-06修复: 实际使用
    uint256 public constant MIN_SLIPPAGE = 9500;

    /// @notice 紧急提取时间锁延迟 (2天)
    uint256 public constant EMERGENCY_WITHDRAW_DELAY = 2 days;

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
    ReinvestRecord[] public reinvestRecords;

    // ========== 紧急提取时间锁 ==========

    /// @notice 待提取的代币
    address public pendingWithdrawToken;

    /// @notice 待提取金额
    uint256 public pendingWithdrawAmount;

    /// @notice 提取生效时间
    uint256 public withdrawEffectiveTime;

    /// @notice 待提取ETH金额
    uint256 public pendingEthWithdrawAmount;

    /// @notice ETH提取生效时间
    uint256 public ethWithdrawEffectiveTime;

    // ========== 结构体 ==========

    struct ReinvestRecord {
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

    event EmergencyWithdrawInitiated(
        address indexed token,
        uint256 amount,
        uint256 effectiveTime
    );

    event EmergencyWithdrawConfirmed(
        address indexed token,
        uint256 amount
    );

    event EmergencyWithdrawCancelled();

    event EmergencyEthWithdrawInitiated(
        uint256 amount,
        uint256 effectiveTime
    );

    event EmergencyEthWithdrawConfirmed(
        uint256 amount
    );

    event EmergencyEthWithdrawCancelled();

    // L-08修复: 添加管理员函数事件
    event DexRouterUpdated(address indexed oldRouter, address indexed newRouter);
    event DexFactoryUpdated(address indexed oldFactory, address indexed newFactory);
    event ContractPaused(address indexed by);
    event ContractUnpaused(address indexed by);

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
     *      使用合约中已有的VIBE余额（来自distributeToPools）
     *      通过msg.value发送ETH
     */
    function initializeLiquidity() external payable onlyOwner nonReentrant {
        require(!initialized, "Already initialized");
        require(msg.value > 0, "Need ETH");

        // 使用 msg.value
        uint256 ethToUse = msg.value;

        // 使用合约中已有的VIBE余额（来自distributeToPools铸造的1.2亿）
        uint256 vibeAmount = vibeToken.balanceOf(address(this));
        require(vibeAmount >= 120_000_000 * 10**18, "Insufficient VIBE in contract");

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
                vibeAmount * MIN_SLIPPAGE / PRECISION, // L-06修复: 使用常量
                ethToUse * MIN_SLIPPAGE / PRECISION,
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
                vibeAmount * MIN_SLIPPAGE / PRECISION,
                msg.value * MIN_SLIPPAGE / PRECISION,
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
     * @notice 投资人添加流动性并获得LP代币
     * @dev 完全去中心化，任何人（包括AI/机器人）都可以参与
     *      流程：ETH → 换VIBE → 添加流动性 → LP归投资人
     *      安全修复 H-02: 添加deadline参数防止抢跑/三明治攻击
     * @param minVibeOut 最小VIBE输出量（滑点保护）
     * @param minLPOut 最小LP输出量（滑点保护）
     * @param deadline 交易截止时间戳（防止抢跑攻击）
     */
    function addLiquidityAndGetLP(
        uint256 minVibeOut,
        uint256 minLPOut,
        uint256 deadline
    ) external payable nonReentrant whenNotPaused {
        // H-02 修复: 检查deadline防止抢跑攻击
        require(block.timestamp <= deadline, "Transaction expired");
        require(initialized, "Not initialized");
        require(msg.value >= MIN_ETH_CONTRIBUTION, "Below minimum 0.1 ETH");
        require(msg.value <= MAX_ETH_CONTRIBUTION, "Above maximum 10 ETH");

        // 将ETH分成两部分：一半用于换VIBE，一半用于添加流动性
        uint256 ethForSwap = msg.value / 2;
        uint256 ethForLiquidity = msg.value - ethForSwap;

        // 安全检查：确保用于swap的ETH足够
        require(ethForSwap > 0, "ETH amount too small");

        // 第一步：用ETH换VIBE
        address[] memory path = new address[](2);
        path[0] = address(weth);
        path[1] = address(vibeToken);

        // 用swap获取VIBE
        uint256 vibeReceived = _swapETHForVIBE(ethForSwap, minVibeOut, path);

        // 安全检查：确保获得了VIBE
        require(vibeReceived >= minVibeOut, "Slippage: VIBE output too low");
        require(vibeReceived > 0, "No VIBE received");

        // 第二步：添加流动性
        // 使用换来的VIBE + 剩余ETH添加流动性
        vibeToken.forceApprove(dexRouter, vibeReceived);

        (uint256 vibeUsed, uint256 ethUsed, uint256 lpReceived) =
            IDEXRouter(dexRouter).addLiquidityETH{value: ethForLiquidity}(
                address(vibeToken),
                vibeReceived,
                vibeReceived * MIN_SLIPPAGE / PRECISION,
                ethForLiquidity * MIN_SLIPPAGE / PRECISION,
                msg.sender, // LP直接给投资人
                block.timestamp + 300
            );

        vibeToken.forceApprove(dexRouter, 0);

        // 安全检查：确保获得了LP
        require(lpReceived >= minLPOut, "Slippage: LP output too low");
        require(lpReceived > 0, "No LP received");

        // 更新统计
        totalVibeAdded += vibeUsed;
        totalEthAdded += ethUsed;
        totalManualLP += lpReceived;

        emit LiquidityAdded(vibeUsed, ethUsed, lpReceived, false);
        emit InvestorLPIssued(msg.sender, lpReceived, vibeUsed, ethUsed);
    }

    /**
     * @notice 用ETH交换VIBE
     */
    function _swapETHForVIBE(
        uint256 ethAmount,
        uint256 minVibeOut,
        address[] memory path
    ) internal returns (uint256) {
        if (ethAmount == 0) return 0;

        // 如果weth不是eth，先wrap
        // Uniswap V2需要先approve或使用ETH

        uint256[] memory amounts = IDEXRouter(dexRouter).swapExactETHForTokens{
            value: ethAmount
        }(
            minVibeOut,
            path,
            address(this),
            block.timestamp + 300
        );

        return amounts[amounts.length - 1];
    }

    /**
     * @notice 事件：投资人获得LP
     */
    event InvestorLPIssued(
        address indexed investor,
        uint256 lpReceived,
        uint256 vibeUsed,
        uint256 ethUsed
    );

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
        emit DexRouterUpdated(dexRouter, _router); // L-08修复
        dexRouter = _router;
    }

    function setDexFactory(address _factory) external onlyOwner {
        require(_factory != address(0), "Invalid factory");
        emit DexFactoryUpdated(dexFactory, _factory); // L-08修复
        dexFactory = _factory;
    }

    function pause() external onlyOwner {
        _pause();
        emit ContractPaused(msg.sender); // L-08修复
    }

    function unpause() external onlyOwner {
        _unpause();
        emit ContractUnpaused(msg.sender); // L-08修复
    }

    /**
     * @notice 发起紧急提取代币（需要时间锁）
     * @dev LP 代币永远不能提取
     * @param token 代币地址
     */
    function emergencyWithdraw(address token) external onlyOwner {
        require(token != address(lpToken), "Cannot withdraw LP");
        require(token != address(vibeToken) || !initialized, "Cannot withdraw VIBE after init");

        // 如果有待生效的提取，先取消
        if (pendingWithdrawToken != address(0)) {
            delete pendingWithdrawToken;
            delete pendingWithdrawAmount;
            delete withdrawEffectiveTime;
            emit EmergencyWithdrawCancelled();
        }

        uint256 balance = IERC20(token).balanceOf(address(this));
        require(balance > 0, "No balance to withdraw");

        pendingWithdrawToken = token;
        pendingWithdrawAmount = balance;
        withdrawEffectiveTime = block.timestamp + EMERGENCY_WITHDRAW_DELAY;

        emit EmergencyWithdrawInitiated(token, balance, withdrawEffectiveTime);
    }

    /**
     * @notice 确认紧急提取代币（时间锁到期后）
     */
    function confirmEmergencyWithdraw() external onlyOwner nonReentrant {
        require(pendingWithdrawToken != address(0), "No pending withdraw");
        require(block.timestamp >= withdrawEffectiveTime, "Timelock not expired");

        address token = pendingWithdrawToken;
        uint256 amount = pendingWithdrawAmount;

        // 清除状态
        delete pendingWithdrawToken;
        delete pendingWithdrawAmount;
        delete withdrawEffectiveTime;

        // 执行提取
        IERC20(token).safeTransfer(owner(), amount);

        emit EmergencyWithdrawConfirmed(token, amount);
    }

    /**
     * @notice 取消紧急提取代币
     */
    function cancelEmergencyWithdraw() external onlyOwner {
        require(pendingWithdrawToken != address(0), "No pending withdraw");

        delete pendingWithdrawToken;
        delete pendingWithdrawAmount;
        delete withdrawEffectiveTime;

        emit EmergencyWithdrawCancelled();
    }

    /**
     * @notice 发起紧急提取ETH（需要时间锁）
     */
    function emergencyWithdrawETH() external onlyOwner {
        // 如果有待生效的提取，先取消
        if (pendingEthWithdrawAmount > 0) {
            delete pendingEthWithdrawAmount;
            delete ethWithdrawEffectiveTime;
            emit EmergencyEthWithdrawCancelled();
        }

        uint256 balance = address(this).balance;
        require(balance > 0, "No ETH balance to withdraw");

        pendingEthWithdrawAmount = balance;
        ethWithdrawEffectiveTime = block.timestamp + EMERGENCY_WITHDRAW_DELAY;

        emit EmergencyEthWithdrawInitiated(balance, ethWithdrawEffectiveTime);
    }

    /**
     * @notice 确认紧急提取ETH（时间锁到期后）
     */
    function confirmEmergencyWithdrawETH() external onlyOwner nonReentrant {
        require(pendingEthWithdrawAmount > 0, "No pending ETH withdraw");
        require(block.timestamp >= ethWithdrawEffectiveTime, "Timelock not expired");

        uint256 amount = pendingEthWithdrawAmount;

        // 清除状态
        delete pendingEthWithdrawAmount;
        delete ethWithdrawEffectiveTime;

        // 执行提取
        payable(owner()).transfer(amount);

        emit EmergencyEthWithdrawConfirmed(amount);
    }

    /**
     * @notice 取消紧急提取ETH
     */
    function cancelEmergencyWithdrawETH() external onlyOwner {
        require(pendingEthWithdrawAmount > 0, "No pending ETH withdraw");

        delete pendingEthWithdrawAmount;
        delete ethWithdrawEffectiveTime;

        emit EmergencyEthWithdrawCancelled();
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

            // 获取token0地址来确定储备顺序
            address token0Addr = ISushiPair(address(lpToken)).token0();

            // Uniswap按地址排序：token0 < token1
            // 如果token0是WETH，则reserve0是ETH；否则reserve1是ETH
            if (token0Addr == address(weth)) {
                // reserve0 = ETH, reserve1 = VIBE
                // vibeAmount = ethAmount * reserve1 / reserve0
                return (ethAmount * uint256(reserve1)) / uint256(reserve0);
            } else {
                // reserve0 = VIBE, reserve1 = ETH
                // vibeAmount = ethAmount * reserve0 / reserve1
                return (ethAmount * uint256(reserve0)) / uint256(reserve1);
            }
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
                vibeAmount * MIN_SLIPPAGE / PRECISION,
                ethAmount * MIN_SLIPPAGE / PRECISION,
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
        reinvestRecords.push(ReinvestRecord({
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

    function getReinvestRecord(uint256 index) external view returns (ReinvestRecord memory) {
        require(index < reinvestRecords.length, "Index out of bounds");
        return reinvestRecords[index];
    }

    /**
     * @notice 获取 LP 价值（以 ETH 计）
     * @dev LQ-01修复: 正确识别ETH储备，不假设reserve0一定是ETH
     */
    function getLPValueInETH() external view returns (uint256) {
        uint256 lpBalance = lpToken.balanceOf(address(this));
        uint256 totalLPSupply = lpToken.totalSupply();

        if (totalLPSupply == 0 || lpBalance == 0) {
            return 0;
        }

        // 获取池子储备
        (uint112 reserve0, uint112 reserve1,) = ISushiPair(address(lpToken)).getReserves();

        // LQ-01修复: 检查token0是否为WETH
        address token0 = ISushiPair(address(lpToken)).token0();
        uint256 ethReserve;

        if (token0 == address(weth)) {
            ethReserve = uint256(reserve0);
        } else {
            ethReserve = uint256(reserve1);
        }

        // LP 价值 ≈ 2 * (ETH 储备 * LP 份额 / 总 LP)
        return (ethReserve * 2 * lpBalance) / totalLPSupply;
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

    // 用于ETH换VIBE的swap函数
    function swapExactETHForTokens(
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external payable returns (uint256[] memory amounts);

    function swapExactTokensForETH(
        uint256 amountIn,
        uint256 amountOutMin,
        address[] calldata path,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
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

    function token0() external view returns (address);

    function token1() external view returns (address);
}
