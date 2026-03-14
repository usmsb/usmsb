// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBReserve
 * @notice 储备基金管理合约 - 极端情况下的紧急补充
 * @dev 接收释放池的10%储备基金
 *
 * 功能:
 * - 自动补充: 当激励池余额低于阈值时自动补充
 * - 治理批准: 其他用途需治理投票 (>67%通过)
 * - 时间锁: 大额提取需要7天时间锁
 * - 透明度: 所有使用记录链上可查
 *
 * 激励池类型:
 * - 质押奖励池 (VIBStaking)
 * - 生态激励池 (VIBEcosystemPool)
 * - 治理奖励池 (待确认)
 */
contract VIBReserve is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    /// @notice 治理投票通过阈值 (67%)
    uint256 public constant GOVERNANCE_PASS_THRESHOLD = 6700;

    /// @notice 最小储备比例 (保留20%作为最后防线)
    uint256 public constant MIN_RESERVE_RATIO = 2000;

    /// @notice 大额提取时间锁 (7天)
    uint256 public constant LARGE_WITHDRAW_DELAY = 7 days;

    /// @notice 单次补充最大比例 (10%)
    uint256 public constant MAX_REFILL_RATIO = 1000;

    /// @notice 单次提取最大比例 (10%) - 白皮书修复
    uint256 public constant MAX_WITHDRAW_RATIO = 1000;

    // 池类型
    enum PoolType {
        STAKING,      // 质押奖励池
        ECOSYSTEM,    // 生态激励池
        GOVERNANCE,   // 治理奖励池
        OTHER         // 其他
    }

    // 补充请求状态
    enum RefillStatus {
        PENDING,      // 待处理
        APPROVED,     // 已批准
        EXECUTED,     // 已执行
        CANCELLED     // 已取消
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 治理合约地址
    address public governanceContract;

    /// @notice 池地址映射
    mapping(PoolType => address) public poolAddresses;

    /// @notice 池最低余额阈值
    mapping(PoolType => uint256) public poolMinThresholds;

    /// @notice 补充请求
    mapping(bytes32 => RefillRequest) public refillRequests;

    /// @notice 补充请求数量
    uint256 public refillCount;

    /// @notice 总接收资金
    uint256 public totalFundsReceived;

    /// @notice 总补充支出
    uint256 public totalRefilled;

    /// @notice 按池类型的补充记录
    mapping(PoolType => uint256) public totalRefilledByPool;

    /// @notice 补充历史
    RefillHistory[] public refillHistory;

    // ========== 结构体 ==========

    struct RefillRequest {
        bytes32 requestId;        // 请求ID
        PoolType poolType;        // 池类型
        uint256 amount;           // 金额
        uint256 thresholdAtRequest; // 请求时的阈值
        uint256 requestedAt;      // 请求时间
        RefillStatus status;      // 状态
        bool isAutomatic;         // 是否自动触发
        uint256 approveCount;     // 批准票数
        uint256 rejectCount;      // 拒绝票数
        uint256 totalVotingPower; // 总投票权
    }

    struct RefillHistory {
        bytes32 requestId;
        PoolType poolType;
        address poolAddress;
        uint256 amount;
        uint256 timestamp;
        bool isAutomatic;
    }

    // ========== 事件 ==========

    event FundsReceived(uint256 amount, address from);

    event PoolAddressUpdated(PoolType poolType, address poolAddress);

    event PoolThresholdUpdated(PoolType poolType, uint256 threshold);

    event RefillRequested(
        bytes32 indexed requestId,
        PoolType poolType,
        uint256 amount,
        bool isAutomatic
    );

    event RefillVoted(
        bytes32 indexed requestId,
        address indexed voter,
        bool approve,
        uint256 votingPower
    );

    event RefillExecuted(
        bytes32 indexed requestId,
        PoolType poolType,
        address poolAddress,
        uint256 amount
    );

    event RefillCancelled(bytes32 indexed requestId);

    event EmergencyWithdrawInitiated(uint256 effectiveTime);

    event EmergencyWithdrawExecuted(uint256 amount);

    // ========== 修饰符 ==========

    modifier onlyGovernance() {
        require(msg.sender == governanceContract, "VIBReserve: only governance");
        _;
    }

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBReserve: invalid token");
        vibeToken = IERC20(_vibeToken);

        // 设置默认最低阈值
        poolMinThresholds[PoolType.STAKING] = 100_000 * 10**18;   // 10万 VIBE
        poolMinThresholds[PoolType.ECOSYSTEM] = 50_000 * 10**18;  // 5万 VIBE
        poolMinThresholds[PoolType.GOVERNANCE] = 10_000 * 10**18; // 1万 VIBE
    }

    // ========== 外部函数 ==========

    /**
     * @notice 接收资金（从EmissionController的reservePool）
     */
    function receiveFunds(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        totalFundsReceived += amount;
        emit FundsReceived(amount, msg.sender);
    }

    /**
     * @notice 检查并触发自动补充
     * @dev 任何人都可以调用，自动检测池余额并触发补充
     */
    function checkAndRefill() external whenNotPaused returns (bool) {
        bool anyRefilled = false;

        for (uint256 i = 0; i <= uint256(PoolType.OTHER); i++) {
            PoolType poolType = PoolType(i);
            address poolAddress = poolAddresses[poolType];

            if (poolAddress == address(0)) continue;

            uint256 balance = vibeToken.balanceOf(poolAddress);
            uint256 threshold = poolMinThresholds[poolType];

            if (balance < threshold) {
                // 计算需要补充的金额
                uint256 needed = threshold - balance;

                // 限制最大补充比例
                uint256 maxRefill = (vibeToken.balanceOf(address(this)) * MAX_REFILL_RATIO) / PRECISION;
                uint256 refillAmount = needed > maxRefill ? maxRefill : needed;

                if (refillAmount > 0) {
                    _executeRefill(poolType, poolAddress, refillAmount, true);
                    anyRefilled = true;
                }
            }
        }

        return anyRefilled;
    }

    /**
     * @notice 手动请求补充（需要治理批准）
     * @param poolType 池类型
     * @param amount 金额
     */
    function requestRefill(
        PoolType poolType,
        uint256 amount
    ) external whenNotPaused returns (bytes32 requestId) {
        address poolAddress = poolAddresses[poolType];
        require(poolAddress != address(0), "VIBReserve: pool not set");
        require(amount > 0, "VIBReserve: invalid amount");

        // 检查储备余额是否足够
        uint256 reserveBalance = vibeToken.balanceOf(address(this));
        uint256 minReserve = (totalFundsReceived * MIN_RESERVE_RATIO) / PRECISION;

        require(
            reserveBalance - amount >= minReserve || reserveBalance >= amount,
            "VIBReserve: would breach min reserve"
        );

        refillCount++;
        requestId = keccak256(abi.encodePacked(
            poolType,
            amount,
            block.timestamp,
            refillCount
        ));

        refillRequests[requestId] = RefillRequest({
            requestId: requestId,
            poolType: poolType,
            amount: amount,
            thresholdAtRequest: poolMinThresholds[poolType],
            requestedAt: block.timestamp,
            status: RefillStatus.PENDING,
            isAutomatic: false,
            approveCount: 0,
            rejectCount: 0,
            totalVotingPower: 0
        });

        emit RefillRequested(requestId, poolType, amount, false);
    }

    /**
     * @notice 治理投票（仅治理合约调用）
     * @param requestId 请求ID
     * @param approve 是否批准
     * @param votingPower 投票权
     */
    function voteOnRefill(
        bytes32 requestId,
        bool approve,
        uint256 votingPower
    ) external onlyGovernance {
        RefillRequest storage request = refillRequests[requestId];

        require(request.status == RefillStatus.PENDING, "VIBReserve: invalid status");

        if (approve) {
            request.approveCount += votingPower;
        } else {
            request.rejectCount += votingPower;
        }
        request.totalVotingPower += votingPower;

        emit RefillVoted(requestId, msg.sender, approve, votingPower);

        // 检查是否达到通过阈值
        if (request.approveCount * PRECISION >= request.totalVotingPower * GOVERNANCE_PASS_THRESHOLD) {
            request.status = RefillStatus.APPROVED;
        } else if (request.rejectCount * PRECISION > request.totalVotingPower * (PRECISION - GOVERNANCE_PASS_THRESHOLD)) {
            request.status = RefillStatus.CANCELLED;
            emit RefillCancelled(requestId);
        }
    }

    /**
     * @notice 执行已批准的补充
     */
    function executeRefill(bytes32 requestId) external nonReentrant whenNotPaused {
        RefillRequest storage request = refillRequests[requestId];

        require(request.status == RefillStatus.APPROVED, "VIBReserve: not approved");

        address poolAddress = poolAddresses[request.poolType];
        require(poolAddress != address(0), "VIBReserve: pool not set");

        // 检查余额
        uint256 balance = vibeToken.balanceOf(address(this));
        require(request.amount <= balance, "VIBReserve: insufficient balance");

        request.status = RefillStatus.EXECUTED;

        _executeRefill(request.poolType, poolAddress, request.amount, false);
    }

    // ========== 内部函数 ==========

    /**
     * @notice 执行补充
     * @dev Medium #8 修复: 添加最小储备检查，防止储备耗尽
     */
    function _executeRefill(
        PoolType poolType,
        address poolAddress,
        uint256 amount,
        bool isAutomatic
    ) internal {
        // Medium #8 修复: 检查补充后是否低于最小储备
        uint256 currentBalance = vibeToken.balanceOf(address(this));
        uint256 minReserve = (totalFundsReceived * MIN_RESERVE_RATIO) / PRECISION;
        uint256 balanceAfterRefill = currentBalance - amount;
        
        require(balanceAfterRefill >= minReserve, "VIBReserve: would breach minimum reserve");
        
        vibeToken.safeTransfer(poolAddress, amount);

        totalRefilled += amount;
        totalRefilledByPool[poolType] += amount;

        refillHistory.push(RefillHistory({
            requestId: bytes32(0), // 自动补充没有requestId
            poolType: poolType,
            poolAddress: poolAddress,
            amount: amount,
            timestamp: block.timestamp,
            isAutomatic: isAutomatic
        }));

        emit RefillExecuted(
            isAutomatic ? bytes32(0) : refillRequests[bytes32(0)].requestId,
            poolType,
            poolAddress,
            amount
        );
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取补充请求
     */
    function getRefillRequest(bytes32 requestId) external view returns (RefillRequest memory) {
        return refillRequests[requestId];
    }

    /**
     * @notice 获取合约余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    /**
     * @notice 获取可用余额（扣除最小储备）
     */
    function getAvailableBalance() external view returns (uint256) {
        uint256 balance = vibeToken.balanceOf(address(this));
        uint256 minReserve = (totalFundsReceived * MIN_RESERVE_RATIO) / PRECISION;

        if (balance <= minReserve) return 0;
        return balance - minReserve;
    }

    /**
     * @notice 检查池是否需要补充
     */
    function checkPoolNeedsRefill(PoolType poolType) external view returns (bool, uint256) {
        address poolAddress = poolAddresses[poolType];
        if (poolAddress == address(0)) return (false, 0);

        uint256 balance = vibeToken.balanceOf(poolAddress);
        uint256 threshold = poolMinThresholds[poolType];

        if (balance < threshold) {
            return (true, threshold - balance);
        }
        return (false, 0);
    }

    /**
     * @notice 获取补充历史数量
     */
    function getRefillHistoryCount() external view returns (uint256) {
        return refillHistory.length;
    }

    /**
     * @notice 获取补充历史
     */
    function getRefillHistory(uint256 index) external view returns (RefillHistory memory) {
        require(index < refillHistory.length, "VIBReserve: index out of bounds");
        return refillHistory[index];
    }

    /**
     * @notice 获取储备状态
     */
    function getReserveStatus() external view returns (
        uint256 balance,
        uint256 available,
        uint256 minReserve,
        uint256 totalReceived,
        uint256 totalSpent
    ) {
        balance = vibeToken.balanceOf(address(this));
        minReserve = (totalFundsReceived * MIN_RESERVE_RATIO) / PRECISION;
        available = balance > minReserve ? balance - minReserve : 0;
        totalReceived = totalFundsReceived;
        totalSpent = totalRefilled;
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置治理合约
     */
    function setGovernanceContract(address _governanceContract) external onlyOwner {
        governanceContract = _governanceContract;
    }

    /**
     * @notice 设置池地址
     */
    function setPoolAddress(PoolType poolType, address poolAddress) external onlyOwner {
        poolAddresses[poolType] = poolAddress;
        emit PoolAddressUpdated(poolType, poolAddress);
    }

    /**
     * @notice 设置池最低阈值
     */
    function setPoolThreshold(PoolType poolType, uint256 threshold) external onlyOwner {
        poolMinThresholds[poolType] = threshold;
        emit PoolThresholdUpdated(poolType, threshold);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 紧急提取（仅owner，有7天时间锁）
     */
    uint256 public emergencyWithdrawEffectiveTime;
    uint256 public pendingEmergencyAmount;
    address public pendingEmergencyRecipient;

    function initiateEmergencyWithdraw(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "VIBReserve: invalid recipient");
        require(amount > 0, "VIBReserve: invalid amount");

        // 白皮书修复: 单次提取不超过余额的10%
        uint256 balance = vibeToken.balanceOf(address(this));
        require(amount <= (balance * MAX_WITHDRAW_RATIO) / PRECISION, 
            "VIBReserve: exceed 10% withdraw limit");

        // 保留最小储备
        uint256 minReserve = (totalFundsReceived * MIN_RESERVE_RATIO) / PRECISION;
        require(
            vibeToken.balanceOf(address(this)) - amount >= minReserve,
            "VIBReserve: would breach min reserve"
        );

        emergencyWithdrawEffectiveTime = block.timestamp + LARGE_WITHDRAW_DELAY;
        pendingEmergencyAmount = amount;
        pendingEmergencyRecipient = to;

        emit EmergencyWithdrawInitiated(emergencyWithdrawEffectiveTime);
    }

    function executeEmergencyWithdraw() external onlyOwner {
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBReserve: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBReserve: not initiated");
        require(pendingEmergencyAmount > 0, "VIBReserve: no pending withdraw");

        uint256 amount = pendingEmergencyAmount;
        address recipient = pendingEmergencyRecipient;

        // 清除待处理状态
        emergencyWithdrawEffectiveTime = 0;
        pendingEmergencyAmount = 0;
        pendingEmergencyRecipient = address(0);

        vibeToken.safeTransfer(recipient, amount);

        emit EmergencyWithdrawExecuted(amount);
    }

    function cancelEmergencyWithdraw() external onlyOwner {
        emergencyWithdrawEffectiveTime = 0;
        pendingEmergencyAmount = 0;
        pendingEmergencyRecipient = address(0);
    }
}
