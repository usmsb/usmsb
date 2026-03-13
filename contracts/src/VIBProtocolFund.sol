// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBProtocolFund
 * @notice 协议基金管理合约 - 治理奖励 + 协议维护
 * @dev 接收交易手续费的15%协议基金
 *      混合模式：小额自动批准，大额需治理投票
 *
 * 资金用途:
 * - 治理奖励: 投票奖励、提案奖励
 * - 协议维护: 安全审计、bug bounty、开发任务
 *
 * 分发规则:
 * - 小额支出 (<1000 VIBE): 自动批准
 * - 大额支出 (>=1000 VIBE): 需要治理投票 (>67%通过)
 */
contract VIBProtocolFund is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    /// @notice 小额阈值 (自动批准)
    uint256 public constant SMALL_AMOUNT_THRESHOLD = 1000 * 10**18; // 1000 VIBE

    /// @notice 治理投票通过阈值 (67%)
    uint256 public constant GOVERNANCE_PASS_THRESHOLD = 6700;

    /// @notice 投票奖励 (每票)
    uint256 public constant VOTE_REWARD = 0.01 * 10**18; // 0.01 VIBE

    /// @notice 提案奖励范围
    uint256 public constant PROPOSAL_REWARD_MIN = 50 * 10**18;   // 50 VIBE
    uint256 public constant PROPOSAL_REWARD_MAX = 500 * 10**18;  // 500 VIBE

    // 支出类别
    enum ExpenseCategory {
        GOVERNANCE_VOTE,      // 治理投票奖励
        GOVERNANCE_PROPOSAL,  // 治理提案奖励
        SECURITY_AUDIT,       // 安全审计
        BUG_BOUNTY,           // Bug赏金
        DEVELOPMENT,          // 开发任务
        MAINTENANCE           // 维护费用
    }

    // 支出状态
    enum ExpenseStatus {
        PENDING,              // 待处理
        AUTO_APPROVED,        // 自动批准
        GOVERNANCE_PENDING,   // 等待治理投票
        APPROVED,             // 已批准
        REJECTED,             // 已拒绝
        EXECUTED              // 已执行
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 治理合约地址
    address public governanceContract;

    /// @notice 已授权的支出发起者
    mapping(address => bool) public authorizedSpenders;

    /// @notice 治理奖励接收者待领取金额
    mapping(address => uint256) public pendingGovernanceRewards;

    /// @notice 支出请求
    mapping(bytes32 => ExpenseRequest) public expenseRequests;

    /// @notice 支出请求数量
    uint256 public expenseCount;

    /// @notice 类别支出限制
    mapping(ExpenseCategory => uint256) public categoryLimits;

    /// @notice 类别已支出金额
    mapping(ExpenseCategory => uint256) public categorySpent;

    /// @notice 总接收资金
    uint256 public totalFundsReceived;

    /// @notice 总治理奖励发放
    uint256 public totalGovernanceRewards;

    /// @notice 总协议维护支出
    uint256 public totalMaintenanceSpent;

    // ========== 结构体 ==========

    struct ExpenseRequest {
        bytes32 requestId;          // 请求ID
        ExpenseCategory category;   // 支出类别
        uint256 amount;             // 金额
        address recipient;          // 接收者
        string description;         // 描述
        uint256 requestedAt;        // 请求时间
        ExpenseStatus status;       // 状态
        uint256 governanceVoteId;   // 关联的治理投票ID
        uint256 approveCount;       // 批准票数
        uint256 rejectCount;        // 拒绝票数
        uint256 totalVotingPower;   // 总投票权
        bool executed;              // 是否已执行
    }

    // ========== 事件 ==========

    event FundsReceived(uint256 amount, address from);

    event GovernanceRewardAdded(
        address indexed recipient,
        uint256 amount,
        bool isVoteReward
    );

    event GovernanceRewardClaimed(
        address indexed recipient,
        uint256 amount
    );

    event ExpenseRequested(
        bytes32 indexed requestId,
        ExpenseCategory category,
        uint256 amount,
        address recipient,
        bool autoApproved
    );

    event ExpenseVoted(
        bytes32 indexed requestId,
        address indexed voter,
        bool approve,
        uint256 votingPower
    );

    event ExpenseExecuted(
        bytes32 indexed requestId,
        address recipient,
        uint256 amount
    );

    event ExpenseRejected(bytes32 indexed requestId);

    event CategoryLimitUpdated(ExpenseCategory category, uint256 limit);

    event GovernanceContractUpdated(address governanceContract);

    event SpenderUpdated(address indexed spender, bool authorized);

    // ========== 修饰符 ==========

    modifier onlyGovernance() {
        require(msg.sender == governanceContract, "VIBProtocolFund: only governance");
        _;
    }

    modifier onlyAuthorizedSpender() {
        require(authorizedSpenders[msg.sender], "VIBProtocolFund: not authorized spender");
        _;
    }

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBProtocolFund: invalid token");
        vibeToken = IERC20(_vibeToken);

        // 设置默认类别限制
        categoryLimits[ExpenseCategory.SECURITY_AUDIT] = 50000 * 10**18;  // 50000 VIBE
        categoryLimits[ExpenseCategory.BUG_BOUNTY] = 10000 * 10**18;      // 10000 VIBE
        categoryLimits[ExpenseCategory.DEVELOPMENT] = 30000 * 10**18;     // 30000 VIBE
        categoryLimits[ExpenseCategory.MAINTENANCE] = 20000 * 10**18;     // 20000 VIBE
    }

    // ========== 外部函数 ==========

    /**
     * @notice 接收资金（从VIBEToken的protocolFundContract）
     */
    function receiveFunds(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        totalFundsReceived += amount;
        emit FundsReceived(amount, msg.sender);
    }

    // ========== 治理奖励功能 ==========

    /**
     * @notice 添加投票奖励（仅治理合约调用）
     * @param voter 投票者地址
     * @param voteCount 投票数量
     */
    function addVoteReward(address voter, uint256 voteCount) external onlyGovernance {
        uint256 reward = VOTE_REWARD * voteCount;

        // 检查余额
        uint256 balance = vibeToken.balanceOf(address(this));
        if (reward > balance) {
            reward = balance;
        }

        if (reward > 0) {
            pendingGovernanceRewards[voter] += reward;
            totalGovernanceRewards += reward;
            emit GovernanceRewardAdded(voter, reward, true);
        }
    }

    /**
     * @notice 添加提案奖励（仅治理合约调用）
     * @param proposer 提案者地址
     * @param proposalValue 提案价值评分 (5000-20000)
     */
    function addProposalReward(address proposer, uint256 proposalValue) external onlyGovernance {
        require(proposalValue >= 5000 && proposalValue <= 20000, "VIBProtocolFund: invalid value");

        // 计算奖励: 50-500 VIBE 基于提案价值
        uint256 reward = PROPOSAL_REWARD_MIN +
            ((PROPOSAL_REWARD_MAX - PROPOSAL_REWARD_MIN) * (proposalValue - 5000)) / 15000;

        // 检查余额
        uint256 balance = vibeToken.balanceOf(address(this));
        if (reward > balance) {
            reward = balance;
        }

        if (reward > 0) {
            pendingGovernanceRewards[proposer] += reward;
            totalGovernanceRewards += reward;
            emit GovernanceRewardAdded(proposer, reward, false);
        }
    }

    /**
     * @notice 领取治理奖励
     */
    function claimGovernanceRewards() external nonReentrant whenNotPaused {
        uint256 reward = pendingGovernanceRewards[msg.sender];
        require(reward > 0, "VIBProtocolFund: no rewards");

        pendingGovernanceRewards[msg.sender] = 0;
        vibeToken.safeTransfer(msg.sender, reward);

        emit GovernanceRewardClaimed(msg.sender, reward);
    }

    // ========== 协议维护支出功能 ==========

    /**
     * @notice 请求支出
     * @param category 支出类别
     * @param amount 金额
     * @param recipient 接收者
     * @param description 描述
     * @return requestId 请求ID
     */
    function requestExpense(
        ExpenseCategory category,
        uint256 amount,
        address recipient,
        string calldata description
    ) external onlyAuthorizedSpender whenNotPaused returns (bytes32 requestId) {
        require(recipient != address(0), "VIBProtocolFund: invalid recipient");
        require(amount > 0, "VIBProtocolFund: invalid amount");

        // 检查类别限制
        require(
            categorySpent[category] + amount <= categoryLimits[category],
            "VIBProtocolFund: exceeds category limit"
        );

        // 检查余额
        uint256 balance = vibeToken.balanceOf(address(this));
        require(amount <= balance, "VIBProtocolFund: insufficient balance");

        expenseCount++;
        requestId = keccak256(abi.encodePacked(
            category,
            amount,
            recipient,
            block.timestamp,
            expenseCount
        ));

        ExpenseStatus status;
        bool autoApproved = false;

        if (amount < SMALL_AMOUNT_THRESHOLD) {
            // 小额自动批准
            status = ExpenseStatus.AUTO_APPROVED;
            autoApproved = true;
        } else {
            // 大额需要治理投票
            status = ExpenseStatus.GOVERNANCE_PENDING;
        }

        expenseRequests[requestId] = ExpenseRequest({
            requestId: requestId,
            category: category,
            amount: amount,
            recipient: recipient,
            description: description,
            requestedAt: block.timestamp,
            status: status,
            governanceVoteId: 0,
            approveCount: 0,
            rejectCount: 0,
            totalVotingPower: 0,
            executed: false
        });

        emit ExpenseRequested(requestId, category, amount, recipient, autoApproved);

        // 如果是自动批准，直接执行
        if (autoApproved) {
            _executeExpense(requestId);
        }
    }

    /**
     * @notice 治理投票（仅治理合约调用）
     * @param requestId 请求ID
     * @param approve 是否批准
     * @param votingPower 投票权
     */
    function voteOnExpense(
        bytes32 requestId,
        bool approve,
        uint256 votingPower
    ) external onlyGovernance {
        ExpenseRequest storage request = expenseRequests[requestId];

        require(request.status == ExpenseStatus.GOVERNANCE_PENDING, "VIBProtocolFund: invalid status");
        require(!request.executed, "VIBProtocolFund: already executed");

        if (approve) {
            request.approveCount += votingPower;
        } else {
            request.rejectCount += votingPower;
        }
        request.totalVotingPower += votingPower;

        emit ExpenseVoted(requestId, msg.sender, approve, votingPower);

        // 检查是否达到通过阈值
        if (request.approveCount * PRECISION >= request.totalVotingPower * GOVERNANCE_PASS_THRESHOLD) {
            request.status = ExpenseStatus.APPROVED;
            _executeExpense(requestId);
        } else if (request.rejectCount * PRECISION > request.totalVotingPower * (PRECISION - GOVERNANCE_PASS_THRESHOLD)) {
            request.status = ExpenseStatus.REJECTED;
            emit ExpenseRejected(requestId);
        }
    }

    /**
     * @notice 执行已批准的支出
     */
    function executeApprovedExpense(bytes32 requestId) external nonReentrant whenNotPaused {
        ExpenseRequest storage request = expenseRequests[requestId];

        require(request.status == ExpenseStatus.APPROVED, "VIBProtocolFund: not approved");
        require(!request.executed, "VIBProtocolFund: already executed");

        _executeExpense(requestId);
    }

    // ========== 内部函数 ==========

    /**
     * @notice 执行支出
     */
    function _executeExpense(bytes32 requestId) internal {
        ExpenseRequest storage request = expenseRequests[requestId];

        request.executed = true;
        request.status = ExpenseStatus.EXECUTED;

        categorySpent[request.category] += request.amount;
        totalMaintenanceSpent += request.amount;

        vibeToken.safeTransfer(request.recipient, request.amount);

        emit ExpenseExecuted(requestId, request.recipient, request.amount);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取支出请求
     */
    function getExpenseRequest(bytes32 requestId) external view returns (ExpenseRequest memory) {
        return expenseRequests[requestId];
    }

    /**
     * @notice 获取待领取治理奖励
     */
    function getPendingGovernanceReward(address user) external view returns (uint256) {
        return pendingGovernanceRewards[user];
    }

    /**
     * @notice 获取合约余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    /**
     * @notice 获取可用余额（扣除待领取奖励）
     */
    function getAvailableBalance() external view returns (uint256) {
        uint256 balance = vibeToken.balanceOf(address(this));
        // 这里简化处理，实际可能需要追踪所有待领取金额
        return balance;
    }

    /**
     * @notice 检查支出请求是否可执行
     */
    function canExecuteExpense(bytes32 requestId) external view returns (bool) {
        ExpenseRequest storage request = expenseRequests[requestId];
        return (request.status == ExpenseStatus.APPROVED ||
                request.status == ExpenseStatus.AUTO_APPROVED) &&
               !request.executed &&
               request.amount <= vibeToken.balanceOf(address(this));
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置治理合约
     */
    function setGovernanceContract(address _governanceContract) external onlyOwner {
        governanceContract = _governanceContract;
        emit GovernanceContractUpdated(_governanceContract);
    }

    /**
     * @notice 设置授权支出者
     */
    function setAuthorizedSpender(address spender, bool authorized) external onlyOwner {
        authorizedSpenders[spender] = authorized;
        emit SpenderUpdated(spender, authorized);
    }

    /**
     * @notice 设置类别限制
     */
    function setCategoryLimit(ExpenseCategory category, uint256 limit) external onlyOwner {
        categoryLimits[category] = limit;
        emit CategoryLimitUpdated(category, limit);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 紧急提取（仅owner，有2天时间锁）
     */
    uint256 public emergencyWithdrawEffectiveTime;

    function initiateEmergencyWithdraw() external onlyOwner {
        emergencyWithdrawEffectiveTime = block.timestamp + 2 days;
    }

    function executeEmergencyWithdraw() external onlyOwner {
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBProtocolFund: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBProtocolFund: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }
}
