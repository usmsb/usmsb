// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./interfaces/IAgentRegistry.sol";

/**
 * @title IVIBStaking
 * @notice VIBStaking 接口
 */
interface IVIBStaking {
    enum StakeTier { BRONZE, SILVER, GOLD, PLATINUM }

    struct StakeInfo {
        uint256 amount;
        uint256 startTime;
        uint256 unlockTime;
        uint256 lockPeriodIndex;
        StakeTier tier;
        uint256 pendingReward;
        uint256 rewardDebt;
        bool isActive;
    }

    function stake(uint256 amount, uint256 lockPeriod) external;
    function unstake() external;
    function claimReward() external;
    function getStakeInfo(address user) external view returns (StakeInfo memory);
    function getStakingTier(address user) external view returns (StakeTier);
}

/**
 * @title AgentWallet
 * @notice Agent 智能合约钱包
 * @dev 支持：
 * - 限额控制（单笔、每日）
 * - 注册表验证（自动信任系统内 Agent）
 * - 主人授权大额交易
 * - VIBStaking 集成（质押等级与权限挂钩）
 *
 * 质押等级与 Agent 权限映射:
 * | 等级 | 质押量 | Agent数量限制 | 折扣 | 特权 |
 * |------|--------|--------------|------|------|
 * | Bronze | 100-999 | 1个 | 0% | 无 |
 * | Silver | 1000-4999 | 3个 | 5% | 无 |
 * | Gold | 5000-9999 | 10个 | 10% | 优先队列 |
 * | Platinum | 10000+ | 50个 | 20% | VIP支持 |
 */
contract AgentWallet is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 默认单笔最大限额 (500 VIBE)
    uint256 public constant DEFAULT_MAX_PER_TX = 500 * 10**18;

    /// @notice 默认每日最大限额 (1000 VIBE)
    uint256 public constant DEFAULT_DAILY_LIMIT = 1000 * 10**18;

    /// @notice 最小质押要求 (100 VIBE)
    uint256 public constant MIN_STAKE_REQUIREMENT = 100 * 10**18;

    /// @notice 各等级对应的 Agent 数量限制
    uint256 public constant BRONZE_AGENT_LIMIT = 1;
    uint256 public constant SILVER_AGENT_LIMIT = 3;
    uint256 public constant GOLD_AGENT_LIMIT = 10;
    uint256 public constant PLATINUM_AGENT_LIMIT = 50;

    /// @notice 各等级对应的折扣 (百分比)
    uint256 public constant BRONZE_DISCOUNT = 0;
    uint256 public constant SILVER_DISCOUNT = 5;
    uint256 public constant GOLD_DISCOUNT = 10;
    uint256 public constant PLATINUM_DISCOUNT = 20;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 注册表合约地址
    IAgentRegistry public registry;

    /// @notice 质押合约地址
    IVIBStaking public stakingContract;

    /// @notice Agent 地址 (后端服务地址)
    address public agent;

    /// @notice 单笔最大限额
    uint256 public maxPerTx;

    /// @notice 每日最大限额
    uint256 public dailyLimit;

    /// @notice 今日已转账金额
    uint256 public dailySpent;

    /// @notice 上次重置时间
    uint256 public lastResetTime;

    /// @notice 本地质押金额（用于未设置质押合约时的回退）
    uint256 public stakedAmount;

    /// @notice 白名单映射
    mapping(address => bool) public whitelist;

    /// @notice 待审批的转账请求
    mapping(bytes32 => PendingTransfer) public pendingTransfers;

    /// @notice 待审批转账计数
    uint256 public pendingTransferCount;

    // ========== 结构体 ==========

    struct PendingTransfer {
        address to;
        uint256 amount;
        address requester;
        uint256 timestamp;
        bool approved;
        bool executed;
    }

    // ========== 事件 ==========

    /// @notice 转账事件
    event TransferExecuted(address indexed to, uint256 amount, address indexed from);

    /// @notice 转账请求事件 (需要审批)
    event TransferRequested(
        bytes32 indexed requestId,
        address indexed to,
        uint256 amount,
        address indexed requester
    );

    /// @notice 转账批准事件
    event TransferApproved(bytes32 indexed requestId, address indexed approver);

    /// @notice 转账拒绝事件
    event TransferRejected(bytes32 indexed requestId, address indexed rejector);

    /// @notice 转账完成事件
    event TransferCompleted(bytes32 indexed requestId);

    /// @notice 充值事件
    event Deposited(address indexed from, uint256 amount);

    /// @notice 质押事件
    event Staked(uint256 amount, uint8 tier);

    /// @notice 取消质押事件
    event Unstaked(uint256 amount);

    /// @notice 质押合约更新事件
    event StakingContractUpdated(address indexed stakingContract);

    /// @notice 等级权限更新事件
    event TierPermissionsUpdated(uint8 tier, uint256 agentLimit, uint256 discount);

    /// @notice 限额更新事件
    event LimitsUpdated(uint256 maxPerTx, uint256 dailyLimit);

    /// @notice 白名单更新事件
    event WhitelistUpdated(address indexed addr, bool allowed);

    // ========== 修饰符 ==========

    /// @notice 只允许 Agent 或主人调用
    modifier onlyAgentOrOwner() {
        require(
            msg.sender == agent || msg.sender == owner(),
            "AgentWallet: caller is not agent or owner"
        );
        _;
    }

    /// @notice 只允许 Agent 调用
    modifier onlyAgent() {
        require(msg.sender == agent, "AgentWallet: caller is not agent");
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _owner 主人地址
     * @param _agent Agent 地址
     * @param _vibeToken VIBE 代币地址
     * @param _registry 注册表合约地址
     * @param _stakingContract 质押合约地址（可为零地址）
     */
    constructor(
        address _owner,
        address _agent,
        address _vibeToken,
        address _registry,
        address _stakingContract
    ) Ownable(_owner) {
        require(_owner != address(0), "AgentWallet: invalid owner");
        require(_agent != address(0), "AgentWallet: invalid agent");

        agent = _agent;
        vibeToken = IERC20(_vibeToken);
        registry = IAgentRegistry(_registry);

        if (_stakingContract != address(0)) {
            stakingContract = IVIBStaking(_stakingContract);
        }

        maxPerTx = DEFAULT_MAX_PER_TX;
        dailyLimit = DEFAULT_DAILY_LIMIT;
        lastResetTime = block.timestamp;

        whitelist[_owner] = true;
    }

    // ========== 外部函数 ==========

    /**
     * @notice Agent 发起转账
     * @param to 目标地址
     * @param amount 金额
     */
    function executeTransfer(address to, uint256 amount)
        external
        onlyAgent
        nonReentrant
        whenNotPaused
        returns (bool)
    {
        require(to != address(0), "AgentWallet: invalid recipient");
        require(amount > 0, "AgentWallet: amount must be greater than 0");

        // 检查目标地址是否允许
        require(_canTransfer(to), "AgentWallet: recipient not allowed");

        // 检查限额
        _checkAndUpdateDailyLimit(amount);

        // 检查单笔限额
        require(amount <= maxPerTx, "AgentWallet: exceeds max per tx");

        // 执行转账
        _executeTransfer(to, amount, msg.sender);

        return true;
    }

    /**
     * @notice 请求大额转账（需要主人审批）
     * @param to 目标地址
     * @param amount 金额
     * @return bytes32 请求 ID
     */
    function requestTransfer(address to, uint256 amount)
        external
        onlyAgent
        nonReentrant
        whenNotPaused
        returns (bytes32)
    {
        require(to != address(0), "AgentWallet: invalid recipient");
        require(amount > 0, "AgentWallet: amount must be greater than 0");

        // 检查目标地址是否允许
        require(_canTransfer(to), "AgentWallet: recipient not allowed");

        // 生成请求 ID
        bytes32 requestId = keccak256(
            abi.encodePacked(to, amount, msg.sender, block.timestamp, pendingTransferCount)
        );

        // 创建待审批请求
        pendingTransfers[requestId] = PendingTransfer({
            to: to,
            amount: amount,
            requester: msg.sender,
            timestamp: block.timestamp,
            approved: false,
            executed: false
        });
        pendingTransferCount++;

        emit TransferRequested(requestId, to, amount, msg.sender);

        return requestId;
    }

    /**
     * @notice 主人批准并执行转账
     * @param requestId 请求 ID
     */
    function approveTransfer(bytes32 requestId)
        external
        nonReentrant
        returns (bool)
    {
        require(msg.sender == owner(), "AgentWallet: only owner can approve");

        PendingTransfer storage request = pendingTransfers[requestId];
        require(request.amount > 0, "AgentWallet: invalid request");
        require(!request.executed, "AgentWallet: already executed");

        // 检查并更新限额
        _checkAndUpdateDailyLimit(request.amount);

        // 标记为已批准
        request.approved = true;

        // 执行转账
        _executeTransfer(request.to, request.amount, request.requester);
        request.executed = true;

        emit TransferApproved(requestId, msg.sender);
        emit TransferCompleted(requestId);

        return true;
    }

    /**
     * @notice 主人拒绝转账
     * @param requestId 请求 ID
     */
    function rejectTransfer(bytes32 requestId) external nonReentrant {
        require(msg.sender == owner(), "AgentWallet: only owner can reject");

        PendingTransfer storage request = pendingTransfers[requestId];
        require(request.amount > 0, "AgentWallet: invalid request");
        require(!request.executed, "AgentWallet: already executed");

        request.executed = true; // 标记为已处理（拒绝）

        emit TransferRejected(requestId, msg.sender);
    }

    /**
     * @notice 充值到钱包
     * @param amount 金额
     */
    function deposit(uint256 amount) external nonReentrant {
        require(amount > 0, "AgentWallet: amount must be greater than 0");

        // 从调用者转账到合约
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        emit Deposited(msg.sender, amount);
    }

    /**
     * @notice 质押代币到 VIBStaking 合约
     * @param amount 金额
     * @param lockPeriod 锁仓期索引 (0=无锁仓, 1=1月, 2=3月, 3=6月, 4=1年)
     */
    function stake(uint256 amount, uint256 lockPeriod) external onlyAgentOrOwner nonReentrant {
        require(amount > 0, "AgentWallet: amount must be greater than 0");
        require(lockPeriod < 5, "AgentWallet: invalid lock period");

        if (address(stakingContract) != address(0)) {
            // 先将代币从合约批准给质押合约
            vibeToken.forceApprove(address(stakingContract), amount);

            // 调用 VIBStaking 合约进行质押
            stakingContract.stake(amount, lockPeriod);

            // 获取质押等级
            IVIBStaking.StakeTier tier = stakingContract.getStakingTier(address(this));
            uint8 tierIndex = uint8(tier);

            // 根据等级更新权限
            _updateTierPermissions(tierIndex);

            emit Staked(amount, tierIndex);
        } else {
            // 回退：本地记录质押（不推荐，仅用于测试或未设置质押合约时）
            stakedAmount += amount;
            emit Staked(amount, 0);
        }
    }

    /**
     * @notice 从 VIBStaking 合约取消质押
     */
    function unstake() external onlyAgentOrOwner nonReentrant {
        if (address(stakingContract) != address(0)) {
            IVIBStaking.StakeInfo memory info = stakingContract.getStakeInfo(address(this));
            require(info.isActive, "AgentWallet: no active stake");
            require(block.timestamp >= info.unlockTime, "AgentWallet: lock not expired");

            uint256 amount = info.amount;

            // 调用 VIBStaking 合约取消质押
            stakingContract.unstake();

            // 重置权限到默认
            maxPerTx = DEFAULT_MAX_PER_TX;
            dailyLimit = DEFAULT_DAILY_LIMIT;

            emit Unstaked(amount);
        } else {
            require(stakedAmount > 0, "AgentWallet: no stake");
            uint256 amount = stakedAmount;
            stakedAmount = 0;
            emit Unstaked(amount);
        }
    }

    /**
     * @notice 领取质押奖励
     */
    function claimStakingReward() external onlyAgentOrOwner nonReentrant {
        if (address(stakingContract) != address(0)) {
            stakingContract.claimReward();
        }
    }

    /**
     * @notice 根据质押等级更新权限
     * @param tierIndex 等级索引 (0=Bronze, 1=Silver, 2=Gold, 3=Platinum)
     */
    function _updateTierPermissions(uint8 tierIndex) internal {
        // 根据等级设置不同的限额
        if (tierIndex == 0) {
            // Bronze: 默认限额
            maxPerTx = DEFAULT_MAX_PER_TX;
            dailyLimit = DEFAULT_DAILY_LIMIT;
        } else if (tierIndex == 1) {
            // Silver: 2x限额
            maxPerTx = DEFAULT_MAX_PER_TX * 2;
            dailyLimit = DEFAULT_DAILY_LIMIT * 2;
        } else if (tierIndex == 2) {
            // Gold: 5x限额
            maxPerTx = DEFAULT_MAX_PER_TX * 5;
            dailyLimit = DEFAULT_DAILY_LIMIT * 5;
        } else if (tierIndex == 3) {
            // Platinum: 10x限额
            maxPerTx = DEFAULT_MAX_PER_TX * 10;
            dailyLimit = DEFAULT_DAILY_LIMIT * 10;
        }

        emit TierPermissionsUpdated(tierIndex, maxPerTx, dailyLimit);
    }

    /**
     * @notice 更新限额 (仅主人)
     * @param _maxPerTx 新单笔限额
     * @param _dailyLimit 新每日限额
     */
    function updateLimits(uint256 _maxPerTx, uint256 _dailyLimit) external onlyOwner {
        require(_maxPerTx > 0, "AgentWallet: invalid max per tx");
        require(_dailyLimit >= _maxPerTx, "AgentWallet: daily limit must >= max per tx");

        maxPerTx = _maxPerTx;
        dailyLimit = _dailyLimit;

        emit LimitsUpdated(_maxPerTx, _dailyLimit);
    }

    /**
     * @notice 更新白名单 (仅主人)
     * @param addr 地址
     * @param allowed 是否允许
     */
    function updateWhitelist(address addr, bool allowed) external onlyOwner {
        require(addr != address(0), "AgentWallet: invalid address");

        whitelist[addr] = allowed;

        emit WhitelistUpdated(addr, allowed);
    }

    /**
     * @notice 设置质押合约地址 (仅主人)
     * @param _stakingContract 质押合约地址
     */
    function setStakingContract(address _stakingContract) external onlyOwner {
        stakingContract = IVIBStaking(_stakingContract);
        emit StakingContractUpdated(_stakingContract);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    /**
     * @notice 获取质押金额（从 VIBStaking 合约获取或本地）
     */
    function getStakedAmount() external view returns (uint256) {
        if (address(stakingContract) != address(0)) {
            IVIBStaking.StakeInfo memory info = stakingContract.getStakeInfo(address(this));
            return info.isActive ? info.amount : 0;
        }
        return stakedAmount;
    }

    /**
     * @notice 获取质押等级
     */
    function getStakingTier() external view returns (uint8) {
        if (address(stakingContract) != address(0)) {
            IVIBStaking.StakeTier tier = stakingContract.getStakingTier(address(this));
            return uint8(tier);
        }
        // 本地质押根据金额计算等级
        if (stakedAmount >= 10000 * 10**18) return 3; // Platinum
        if (stakedAmount >= 5000 * 10**18) return 2;  // Gold
        if (stakedAmount >= 1000 * 10**18) return 1;  // Silver
        return 0; // Bronze
    }

    /**
     * @notice 获取 Agent 数量限制（根据质押等级）
     */
    function getAgentLimit() external view returns (uint256) {
        uint8 tier = this.getStakingTier();
        if (tier == 3) return PLATINUM_AGENT_LIMIT;
        if (tier == 2) return GOLD_AGENT_LIMIT;
        if (tier == 1) return SILVER_AGENT_LIMIT;
        return BRONZE_AGENT_LIMIT;
    }

    /**
     * @notice 获取折扣百分比（根据质押等级）
     */
    function getDiscount() external view returns (uint256) {
        uint8 tier = this.getStakingTier();
        if (tier == 3) return PLATINUM_DISCOUNT;
        if (tier == 2) return GOLD_DISCOUNT;
        if (tier == 1) return SILVER_DISCOUNT;
        return BRONZE_DISCOUNT;
    }

    /**
     * @notice 获取今日已花费
     */
    function getDailySpent() external view returns (uint256) {
        return dailySpent;
    }

    /**
     * @notice 获取剩余可用限额
     */
    function getRemainingDailyLimit() external view returns (uint256) {
        uint256 spent = dailySpent;
        if (block.timestamp - lastResetTime >= 1 days) {
            spent = 0;
        }
        return dailyLimit > spent ? dailyLimit - spent : 0;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 检查是否可以转账到目标地址
     */
    function _canTransfer(address to) internal view returns (bool) {
        // 1. 白名单检查
        if (whitelist[to]) return true;

        // 2. 主人自己
        if (to == owner()) return true;

        // 3. 通过注册表验证是否为有效 Agent
        if (address(registry) != address(0)) {
            if (registry.isValidAgent(to)) return true;
        }

        return false;
    }

    /**
     * @notice 检查并更新每日限额
     */
    function _checkAndUpdateDailyLimit(uint256 amount) internal {
        _resetDailyIfNeeded();

        require(dailySpent + amount <= dailyLimit, "AgentWallet: exceeds daily limit");

        dailySpent += amount;
    }

    /**
     * @notice 重置每日限额（如果新的一天）
     */
    function _resetDailyIfNeeded() internal {
        if (block.timestamp - lastResetTime >= 1 days) {
            dailySpent = 0;
            lastResetTime = block.timestamp;
        }
    }

    /**
     * @notice 执行转账
     */
    function _executeTransfer(address to, uint256 amount, address from) internal {
        vibeToken.safeTransfer(to, amount);

        emit TransferExecuted(to, amount, from);
    }

    // ========== 紧急函数 ==========

    /// @notice 紧急暂停
    function pause() external onlyOwner {
        _pause();
    }

    /// @notice 恢复
    function unpause() external onlyOwner {
        _unpause();
    }

    /// @notice 紧急提取代币
    function emergencyWithdraw(address token, address to, uint256 amount)
        external
        onlyOwner
        nonReentrant
    {
        require(to != address(0), "AgentWallet: invalid recipient");

        if (token == address(0)) {
            // 提取 ETH
            payable(to).transfer(amount);
        } else {
            // 提取 ERC20
            IERC20(token).safeTransfer(to, amount);
        }
    }

    // 接收 ETH
    receive() external payable {}
}
