// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title EmissionController
 * @notice 激励池释放控制器
 * @dev 功能：
 *      - 5年线性释放 6.3亿 VIBE
 *      - 自动分配到各奖励池（质押45%/生态30%/治理15%/储备10%）
 *      - 混合触发机制（7天周期 + 紧急补充）
 *      - 触发者获得 Gas 补贴 + 时间累积奖励
 */
contract EmissionController is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 总释放量 (6.3亿)
    uint256 public constant TOTAL_EMISSION = 630_000_000 * 10**18;

    /// @notice 释放持续时间 (5年)
    uint256 public constant EMISSION_DURATION = 5 * 365 days;

    /// @notice 周期时长 (7天)
    uint256 public constant EPOCH_DURATION = 7 days;

    /// @notice 分配比例
    uint256 public constant STAKING_RATIO = 4500;    // 45%
    uint256 public constant ECOSYSTEM_RATIO = 3000;  // 30%
    uint256 public constant GOVERNANCE_RATIO = 1500; // 15%
    uint256 public constant RESERVE_RATIO = 1000;    // 10%

    /// @notice 触发奖励参数
    uint256 public constant BASE_REWARD = 0.0005 ether;
    uint256 public constant GAS_BONUS_PERCENT = 20;
    uint256 public constant ACCUMULATION_RATE = 0.0001 ether; // 每小时
    uint256 public constant MAX_ACCUMULATED_HOURS = 24;

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币
    IERC20 public vibeToken;

    /// @notice 价格预言机
    address public priceOracle;

    /// @notice 各奖励池地址
    address public stakingPool;
    address public ecosystemPool;
    address public governancePool;
    address public reservePool;

    /// @notice 释放开始时间
    uint256 public startTime;

    /// @notice 已释放总量
    uint256 public totalReleased;

    /// @notice 上次周期释放时间
    uint256 public lastEpochTime;

    /// @notice 上次触发时间
    uint256 public lastTriggerTime;

    /// @notice 紧急补充最小阈值
    uint256 public minPoolBalance = 100_000 * 10**18; // 10万 VIBE

    /// @notice 释放记录
    ReleaseRecord[] public releaseRecords;

    // ========== 结构体 ==========

    struct ReleaseRecord {
        uint256 amount;
        uint256 timestamp;
        address trigger;
        bool isEmergency;
        uint256 stakingAmount;
        uint256 ecosystemAmount;
        uint256 governanceAmount;
        uint256 reserveAmount;
    }

    // ========== 事件 ==========

    event EmissionReleased(
        uint256 amount,
        address indexed trigger,
        bool isEmergency,
        uint256 timestamp
    );

    event PoolUpdated(string poolName, address newAddress);
    event MinPoolBalanceUpdated(uint256 newBalance);
    event GovernanceFundsRequested(uint256 amount, address governancePool);

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _stakingPool,
        address _ecosystemPool,
        address _governancePool,
        address _reservePool
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "Invalid token");

        vibeToken = IERC20(_vibeToken);
        stakingPool = _stakingPool;
        ecosystemPool = _ecosystemPool;
        governancePool = _governancePool;
        reservePool = _reservePool;

        startTime = block.timestamp;
        lastEpochTime = block.timestamp;
        lastTriggerTime = block.timestamp;
    }

    // ========== 接收 ETH ==========

    receive() external payable {}

    // ========== 外部函数 ==========

    /**
     * @notice 周期释放（每7天触发一次）
     * @dev 任何人都可以调用
     */
    function epochDistribute() external nonReentrant whenNotPaused {
        require(block.timestamp >= lastEpochTime + EPOCH_DURATION, "Epoch not yet");

        uint256 releasable = getReleasableAmount();
        require(releasable > 0, "Nothing to release");

        _distribute(releasable, false);

        lastEpochTime = block.timestamp;
        lastTriggerTime = block.timestamp;
    }

    /**
     * @notice 紧急补充（池子余额低于阈值时）
     * @dev 任何人都可以调用，只补充质押池
     */
    function emergencyRefill() external nonReentrant whenNotPaused {
        require(stakingPool != address(0), "Staking pool not set");

        // 检查质押池余额
        uint256 poolBalance = vibeToken.balanceOf(stakingPool);
        require(poolBalance < minPoolBalance, "Pool has enough balance");

        uint256 releasable = getReleasableAmount();
        require(releasable > 0, "Nothing to release");

        // 计算需要的补充量
        uint256 needed = minPoolBalance - poolBalance;
        uint256 amount = needed < releasable ? needed : releasable;

        // 紧急补充只给质押池
        vibeToken.safeTransfer(stakingPool, amount);

        // 更新状态
        totalReleased += amount;
        lastTriggerTime = block.timestamp;

        // 记录释放
        releaseRecords.push(ReleaseRecord({
            amount: amount,
            timestamp: block.timestamp,
            trigger: msg.sender,
            isEmergency: true,
            stakingAmount: amount,
            ecosystemAmount: 0,
            governanceAmount: 0,
            reserveAmount: 0
        }));

        // 支付触发者奖励（如果有 ETH）
        _payTriggerReward();

        emit EmissionReleased(amount, msg.sender, true, block.timestamp);
    }

    /**
     * @notice 获取可释放数量
     */
    function getReleasableAmount() public view returns (uint256) {
        uint256 elapsed = block.timestamp - startTime;

        // 如果还没开始或已过释放期
        if (elapsed == 0) return 0;

        // 计算已归属数量
        uint256 vested;
        if (elapsed >= EMISSION_DURATION) {
            vested = TOTAL_EMISSION;
        } else {
            vested = (TOTAL_EMISSION * elapsed) / EMISSION_DURATION;
        }

        // 减去已释放数量
        if (vested <= totalReleased) return 0;

        return vested - totalReleased;
    }

    /**
     * @notice 计算触发者奖励
     */
    function getTriggerReward() public view returns (uint256) {
        uint256 hoursSinceLastTrigger = (block.timestamp - lastTriggerTime) / 1 hours;

        if (hoursSinceLastTrigger > MAX_ACCUMULATED_HOURS) {
            hoursSinceLastTrigger = MAX_ACCUMULATED_HOURS;
        }

        uint256 timeBonus = hoursSinceLastTrigger * ACCUMULATION_RATE;

        return BASE_REWARD + timeBonus;
    }

    /**
     * @notice 获取当前释放进度
     */
    function getEmissionProgress() external view returns (
        uint256 released,
        uint256 releasable,
        uint256 remaining,
        uint256 progressPercent
    ) {
        released = totalReleased;
        releasable = getReleasableAmount();
        remaining = TOTAL_EMISSION - totalReleased - releasable;
        progressPercent = (totalReleased * 100) / TOTAL_EMISSION;
    }

    // ========== 管理员函数 ==========

    function setStakingPool(address _pool) external onlyOwner {
        stakingPool = _pool;
        emit PoolUpdated("staking", _pool);
    }

    function setEcosystemPool(address _pool) external onlyOwner {
        ecosystemPool = _pool;
        emit PoolUpdated("ecosystem", _pool);
    }

    function setGovernancePool(address _pool) external onlyOwner {
        governancePool = _pool;
        emit PoolUpdated("governance", _pool);
    }

    function setReservePool(address _pool) external onlyOwner {
        reservePool = _pool;
        emit PoolUpdated("reserve", _pool);
    }

    function setMinPoolBalance(uint256 _balance) external onlyOwner {
        minPoolBalance = _balance;
        emit MinPoolBalanceUpdated(_balance);
    }

    function setPriceOracle(address _oracle) external onlyOwner {
        priceOracle = _oracle;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // ========== 治理池集成 ==========

    /**
     * @notice 治理池请求奖励资金
     * @dev 只有治理池合约可以调用，用于投票奖励等
     * @param amount 请求的金额
     */
    function requestGovernanceFunds(uint256 amount) external nonReentrant {
        require(msg.sender == governancePool, "Only governance pool");
        require(amount > 0, "Invalid amount");

        uint256 balance = vibeToken.balanceOf(address(this));
        require(balance >= amount, "Insufficient balance");

        vibeToken.safeTransfer(governancePool, amount);

        emit GovernanceFundsRequested(amount, governancePool);
    }

    /**
     * @notice 检查治理池是否可以请求指定金额
     * @param amount 请求的金额
     */
    function canRequestGovernanceFunds(uint256 amount) external view returns (bool) {
        return vibeToken.balanceOf(address(this)) >= amount;
    }

    /**
     * @notice 紧急提取（仅限紧急情况）
     */
    function emergencyWithdraw(address to) external onlyOwner {
        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(to, balance);
        }
        uint256 ethBalance = address(this).balance;
        if (ethBalance > 0) {
            payable(to).transfer(ethBalance);
        }
    }

    // ========== 内部函数 ==========

    /**
     * @notice 分配释放的代币
     */
    function _distribute(uint256 amount, bool isEmergency) internal {
        // 计算各池分配量
        uint256 stakingAmount = (amount * STAKING_RATIO) / PRECISION;
        uint256 ecosystemAmount = (amount * ECOSYSTEM_RATIO) / PRECISION;
        uint256 governanceAmount = (amount * GOVERNANCE_RATIO) / PRECISION;
        uint256 reserveAmount = (amount * RESERVE_RATIO) / PRECISION;

        // 计算实际分配总量（避免整数除法丢失）
        uint256 totalDistributed;

        // 转账到各池
        if (stakingPool != address(0) && stakingAmount > 0) {
            vibeToken.safeTransfer(stakingPool, stakingAmount);
            totalDistributed += stakingAmount;
        }
        if (ecosystemPool != address(0) && ecosystemAmount > 0) {
            vibeToken.safeTransfer(ecosystemPool, ecosystemAmount);
            totalDistributed += ecosystemAmount;
        }
        if (governancePool != address(0) && governanceAmount > 0) {
            vibeToken.safeTransfer(governancePool, governanceAmount);
            totalDistributed += governanceAmount;
        }
        if (reservePool != address(0) && reserveAmount > 0) {
            vibeToken.safeTransfer(reservePool, reserveAmount);
            totalDistributed += reserveAmount;
        }

        // 更新状态 - 使用实际分配量
        totalReleased += totalDistributed;

        // 记录释放
        releaseRecords.push(ReleaseRecord({
            amount: totalDistributed,
            timestamp: block.timestamp,
            trigger: msg.sender,
            isEmergency: isEmergency,
            stakingAmount: stakingAmount,
            ecosystemAmount: ecosystemAmount,
            governanceAmount: governanceAmount,
            reserveAmount: reserveAmount
        }));

        // 支付触发者奖励（如果有 ETH）
        _payTriggerReward();

        emit EmissionReleased(totalDistributed, msg.sender, isEmergency, block.timestamp);
    }

    /**
     * @notice 支付触发者奖励
     */
    function _payTriggerReward() internal {
        uint256 reward = getTriggerReward();
        uint256 ethBalance = address(this).balance;

        if (reward > 0 && ethBalance >= reward) {
            payable(msg.sender).transfer(reward);
        } else if (ethBalance > 0) {
            payable(msg.sender).transfer(ethBalance);
        }
    }

    // ========== 视图函数 ==========

    function getReleaseRecordCount() external view returns (uint256) {
        return releaseRecords.length;
    }

    function getReleaseRecord(uint256 index) external view returns (ReleaseRecord memory) {
        require(index < releaseRecords.length, "Index out of bounds");
        return releaseRecords[index];
    }

    function getNextEpochTime() external view returns (uint256) {
        return lastEpochTime + EPOCH_DURATION;
    }

    function getContractBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }
}
