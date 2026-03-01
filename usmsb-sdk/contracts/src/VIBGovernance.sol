// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IEmissionController
 * @notice EmissionController 接口（用于治理池集成）
 */
interface IEmissionController {
    function requestGovernanceFunds(uint256 amount) external;
    function canRequestGovernanceFunds(uint256 amount) external view returns (bool);
}

/**
 * @title IVIBStaking
 * @notice VIBStaking 接口（用于获取真实质押信息和投票权）
 */
interface IVIBStaking {
    struct StakeDetails {
        uint256 amount;
        uint256 tier;
        uint256 timeMultiplier;
        uint256 votingPower;
    }

    function getVotingPower(address user) external view returns (uint256);
    function getStakeDetails(address user) external view returns (
        uint256 amount,
        uint256 tier,
        uint256 timeMultiplier,
        uint256 votingPower
    );
    function getStakedDuration(address user) external view returns (uint256);
    function getTimeMultiplier(address user) external view returns (uint256);
    function totalStaked() external view returns (uint256);
}

/**
 * @title VIBGovernance
 * @notice VIBE 生态系统治理合约
 * @dev 支持三层治理结构：
 * - Layer 1: 资本权重 (质押量 × 时长系数)
 * - Layer 2: 生产权重 (贡献积分，不可转让)
 * - Layer 3: 社区共识 (KYC 验证后一人一票)
 */
contract VIBGovernance is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 提案类型
    enum ProposalType {
        GENERAL,      // 一般提案
        PARAMETER,    // 参数调整
        UPGRADE,      // 协议升级
        EMERGENCY     // 紧急提案
    }

    /// @notice 提案状态
    enum ProposalState {
        PENDING,
        ACTIVE,
        CANCELLED,
        DEFEATED,
        SUCCEEDED,
        EXECUTED,
        EXPIRED,
        PENDING_FINALIZATION  // 待完成最终化 (Gas优化)
    }

    /// @notice Layer 1: 资本权重上限 (10%)
    uint256 public constant CAPITAL_WEIGHT_MAX = 10; // 10%

    /// @notice Layer 2: 生产权重上限 (15%)
    uint256 public constant PRODUCTION_WEIGHT_MAX = 15; // 15%

    /// @notice Layer 3: 社区共识权重占比 (10%)
    uint256 public constant COMMUNITY_WEIGHT_RATIO = 10; // 10%

    /// @notice 最小质押要求
    uint256 public constant MIN_STAKE_REQUIREMENT = 100 * 10**18;

    /// @notice 一年秒数
    uint256 public constant SECONDS_PER_YEAR = 365 days;

    // ========== 委托机制常量 ==========

    /// @notice 最长委托期限 (90天)
    uint256 public constant MAX_DELEGATION_DURATION = 90 days;

    /// @notice 单一接受者最多接受委托比例 (5%)
    uint256 public constant MAX_DELEGATION_ACCEPT_RATIO = 500; // 5% = 500/10000

    /// @notice 大额投票权变动生效延迟 (7天)
    uint256 public constant LARGE_VOTE_CHANGE_DELAY = 7 days;

    /// @notice 大额变动阈值 (总投票权的 1%)
    uint256 public constant LARGE_VOTE_CHANGE_THRESHOLD = 100; // 1% = 100/10000

    // ========== 提案门槛 ==========

    /// @notice 一般提案门槛 (500 VIBE)
    uint256 public generalProposalThreshold = 500 * 10**18;

    // ========== GOV-06修复: 三层治理互相否决机制 ==========

    /// @notice 否决类型
    enum VetoType {
        INVESTOR_VETO,    // 投资者否决权：生产权重>50%的提案
        PRODUCER_VETO,    // 生产者否决权：纯资本权重提案
        COMMUNITY_VETO    // 社区否决权：社区反对率>60%
    }

    /// @notice 否决记录
    struct VetoRecord {
        uint256 proposalId;       // 被否决的提案ID
        VetoType vetoType;        // 否决类型
        address initiator;        // 发起人
        uint256 initiatedTime;    // 发起时间
        uint256 vetoVotes;        // 支持否决的票数
        uint256 opposeVotes;      // 反对否决的票数
        uint256 votingEndTime;    // 投票结束时间
        bool executed;            // 是否已执行
        bool passed;              // 是否通过
    }

    /// @notice 否决记录列表
    VetoRecord[] public vetoRecords;

    /// @notice 提案到否决记录的映射 (proposalId => vetoRecordIndex)
    mapping(uint256 => uint256) public proposalVetoIndex;

    /// @notice 用户是否已在否决中投票
    mapping(uint256 => mapping(address => bool)) public vetoVoted;

    /// @notice 否决投票期 (3天)
    uint256 public constant VETO_VOTING_PERIOD = 3 days;

    /// @notice 否决通过阈值 (50%)
    uint256 public constant VETO_PASS_THRESHOLD = 5000; // 50%

    /// @notice 生产权重阈值：超过此比例的提案可被投资者否决 (50%)
    uint256 public constant PRODUCTION_WEIGHT_VETO_THRESHOLD = 5000; // 50%

    /// @notice 社区反对率阈值：超过此比例自动触发社区否决 (60%)
    uint256 public constant COMMUNITY_OPPOSITION_THRESHOLD = 6000; // 60%

    /// @notice 参数调整门槛 (5,000 VIBE)
    uint256 public parameterProposalThreshold = 5000 * 10**18;

    /// @notice 协议升级门槛 (50,000 VIBE)
    uint256 public upgradeProposalThreshold = 50000 * 10**18;

    /// @notice 紧急提案门槛 (1,000 VIBE) - 安全增强
    uint256 public emergencyProposalThreshold = 1000 * 10**18;

    // ========== 通过率要求 ==========

    /// @notice 一般提案通过率 (>50%)
    uint256 public constant GENERAL_PASS_RATE = 5000; // 50%

    /// @notice 参数调整通过率 (>60%)
    uint256 public constant PARAMETER_PASS_RATE = 6000; // 60%

    /// @notice 协议升级通过率 (>75%)
    uint256 public constant UPGRADE_PASS_RATE = 7500; // 75%

    /// @notice 紧急提案通过率 (>90%)
    uint256 public constant EMERGENCY_PASS_RATE = 9000; // 90%

    // ========== 时间锁 ==========

    /// @notice 一般提案时间锁 (14天)
    uint256 public generalTimelock = 14 days;

    /// @notice 参数调整时间锁 (30天)
    uint256 public parameterTimelock = 30 days;

    /// @notice 协议升级时间锁 (60天)
    uint256 public upgradeTimelock = 60 days;

    /// @notice 紧急提案时间锁 (1天) - 安全增强
    uint256 public constant EMERGENCY_TIMELOCK = 1 days;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 质押合约地址
    address public stakingContract;

    /// @notice 时间锁合约地址
    address public timelockContract;

    /// @notice 贡献积分合约地址
    address public reputationContract;

    /// @notice KYC 验证合约地址
    address public kycContract;

    /// @notice 提案列表
    Proposal[] public proposals;

    /// @notice 用户投票映射
    mapping(uint256 => mapping(address => Vote)) public votes;

    /// @notice 用户是否已投票
    mapping(uint256 => mapping(address => bool)) public hasVoted;

    /// @notice 提议者提案计数
    mapping(address => uint256) public proposalCount;

    /// @notice KYC 验证通过的用户
    mapping(address => bool) public kycVerified;

    /// @notice KYC 验证通过的用户数量
    uint256 public kycUserCount;

    /// @notice 贡献积分
    mapping(address => uint256) public contributionPoints;

    // ========== GOV-03修复: 生产权重90天滚动窗口 ==========

    /// @notice 滚动窗口期 (90天)
    uint256 public constant PRODUCTION_WINDOW = 90 days;

    /// @notice 用户带时间戳的积分记录
    struct TimedPoints {
        uint256 points;
        uint256 timestamp;
    }

    /// @notice 用户积分历史记录
    mapping(address => TimedPoints[]) public userPointsHistory;

    /// @notice 用户最后清理时间
    mapping(address => uint256) public lastCleanupTime;

    // ========== 贡献积分系统 ==========

    /// @notice 贡献类型枚举
    enum ContributionType {
        CODE_CONTRIBUTION,      // 代码贡献
        COMMUNITY_BUILDING,     // 社区建设
        GOVERNANCE_PARTICIPATION, // 治理参与
        CONTENT_CREATION,       // 内容创作
        BUG_REPORTING,          // Bug 报告
        SECURITY_AUDIT,         // 安全审计
        ECOSYSTEM_DEVELOPMENT   // 生态发展
    }

    /// @notice 贡献类型对应的积分值
    mapping(ContributionType => uint256) public contributionTypePoints;

    /// @notice 贡献记录
    struct ContributionRecord {
        address contributor;
        ContributionType contributionType;
        uint256 points;
        uint256 timestamp;
        string evidence;     // IPFS hash 或其他证明
        bool verified;
        address verifier;
    }

    /// @notice 贡献记录列表
    ContributionRecord[] public contributionRecords;

    /// @notice 用户贡献记录索引
    mapping(address => uint256[]) public userContributionIndices;

    /// @notice 待验证的贡献数量
    uint256 public pendingContributionsCount;

    /// @notice 贡献验证者列表
    mapping(address => bool) public contributionVerifiers;

    /// @notice 最大单次贡献积分
    uint256 public constant MAX_SINGLE_CONTRIBUTION_POINTS = 1000 * 10**18;

    /// @notice 每月最大获得积分
    uint256 public constant MAX_MONTHLY_POINTS = 5000 * 10**18;

    /// @notice 用户本月已获得积分
    mapping(address => mapping(uint256 => uint256)) public monthlyPointsEarned; // user => month => points

    /// @notice 生产权重转换比例（贡献积分 -> 投票权）
    uint256 public constant PRODUCTION_WEIGHT_RATIO = 100; // 1 贡献积分 = 0.01 投票权

    /// @notice 社区基金地址
    address public communityFund;

    /// @notice 释放控制器地址
    address public emissionController;

    /// @notice VIBStaking 合约接口
    IVIBStaking public vibStaking;

    /// @notice 治理奖励余额
    uint256 public governanceRewardBalance;

    /// @notice 每票奖励（基础）- 已弃用，使用具体奖励值
    uint256 public voteReward = 1 * 10**18; // 1 VIBE

    /// @notice 每提案奖励 - 已弃用，使用具体奖励值
    uint256 public proposalReward = 10 * 10**18; // 10 VIBE

    // ========== 白皮书规定的投票奖励常量 ==========

    /// @notice 对通过提案投赞成票的奖励 (0.01 VIBE/票)
    uint256 public constant FOR_VOTE_REWARD_PER_POWER = 1 * 10**16; // 0.01 VIBE

    /// @notice 对否决提案投反对票的奖励 (0.005 VIBE/票)
    uint256 public constant AGAINST_VOTE_REWARD_PER_POWER = 5 * 10**15; // 0.005 VIBE

    /// @notice 提案发起人最小奖励 (50 VIBE)
    uint256 public constant PROPOSER_MIN_REWARD = 50 * 10**18;

    /// @notice 提案发起人最大奖励 (500 VIBE)
    uint256 public constant PROPOSER_MAX_REWARD = 500 * 10**18;

    /// @notice 用户已领取的治理奖励
    mapping(address => uint256) public claimedGovernanceRewards;

    /// @notice 用户待领取的治理奖励
    mapping(address => uint256) public pendingGovernanceRewards;

    /// @notice 总待领取奖励（用于防止超发）
    uint256 public totalPendingRewards;

    /// @notice 每个提案的投票奖励记录 (proposalId => voter => reward)
    mapping(uint256 => mapping(address => uint256)) public voteRewards;

    /// @notice 提案发起人奖励是否已发放
    mapping(uint256 => bool) public proposerRewardClaimed;

    // ========== 委托机制状态变量 ==========

    /// @notice 用户委托给谁 (address(0) 表示未委托)
    mapping(address => address) public delegates;

    /// @notice 用户被委托的投票权
    mapping(address => uint256) public delegatedVotes;

    /// @notice 用户委托出去的投票权
    mapping(address => uint256) public delegatedOut;

    /// @notice 委托开始时间
    mapping(address => uint256) public delegationStartTime;

    /// @notice 委托到期时间
    mapping(address => uint256) public delegationExpiryTime;

    /// @notice 用户收到的委托数量（用于检查 5% 限制）
    mapping(address => uint256) public receivedDelegationCount;

    /// @notice 某个地址收到的所有委托来源
    mapping(address => address[]) public delegationSources;

    /// @notice 委托是否存在
    mapping(address => mapping(address => bool)) public isDelegationSource;

    /// @notice 总委托投票权
    uint256 public totalDelegatedVotes;

    /// @notice 待生效的委托变动（大额延迟）
    mapping(address => PendingDelegation) public pendingDelegations;

    // ========== 委托弃权恢复机制 ==========

    /// @notice 受托人连续弃权次数
    mapping(address => uint256) public consecutiveAbstentions;

    /// @notice 最大允许连续弃权次数（超过后自动解除委托）
    uint256 public constant MAX_CONSECUTIVE_ABSTENTIONS = 3;

    /// @notice 委托人申请恢复委托的时间
    mapping(address => uint256) public delegationRecoveryRequestTime;

    /// @notice 恢复等待期（7天）
    uint256 public constant DELEGATION_RECOVERY_DELAY = 7 days;

    /// @notice 待恢复的委托
    mapping(address => bool) public pendingRecovery;

    /// @notice 提案中受托人是否投票的记录
    mapping(uint256 => mapping(address => bool)) public delegateeVotedInProposal;

    /// @notice 活跃受托人列表（收到委托的地址）
    address[] internal activeDelegatees;

    /// @notice 地址是否在活跃受托人列表中
    mapping(address => bool) public isActiveDelegatee;

    // ========== 闪电贷防护 ==========

    /// @notice 用户投票权最后更新的区块号
    mapping(address => uint256) public votingPowerLastUpdateBlock;

    /// @notice 用户投票时记录的区块号
    mapping(uint256 => mapping(address => uint256)) public voteCastBlock;

    /// @notice 闪电贷防护：同一区块内投票权变动不计入
    bool public flashLoanProtectionEnabled = true;

    /// @notice 闪电贷防护变更待生效时间
    uint256 public flashLoanProtectionChangeTime;

    /// @notice 最小投票权持有期（1天）
    /// @dev 防止闪电贷攻击：用户必须持有投票权至少1天才能投票
    uint256 public constant MIN_VOTING_HOLD_PERIOD = 1 days;

    /// @notice 用户投票权首次获取时间
    mapping(address => uint256) public votingPowerAcquireTime;

    // ========== 治理执行白名单（安全修复：CRITICAL-SEC-03）==========

    /// @notice 允许被治理调用的目标合约
    mapping(address => bool) public allowedExecutionTargets;

    /// @notice 允许被治理调用的函数选择器
    mapping(bytes4 => bool) public allowedExecutionFunctions;

    /// @notice 是否启用执行白名单（默认启用）
    bool public executionWhitelistEnabled = true;

    /// @notice 待生效的白名单变更
    bool public pendingWhitelistChange;
    uint256 public pendingWhitelistChangeTime;
    uint256 public constant WHITELIST_CHANGE_DELAY = 7 days;

    /// @notice 允许所有函数的目标合约（仅对可信合约）
    mapping(address => bool) public allowAllFunctionsForTarget;

    // ========== 委托结构体 ==========

    struct PendingDelegation {
        address from;
        address to;
        uint256 amount;
        uint256 effectiveTime;
        bool isActive;
    }

    // ========== 结构体 ==========

    /**
     * @notice 提案结构
     */
    struct Proposal {
        uint256 id;                    // 提案 ID
        address proposer;               // 提议者
        ProposalType proposalType;     // 提案类型
        ProposalState state;           // 提案状态
        string title;                  // 标题
        string description;            // 描述
        address target;                // 目标合约
        bytes data;                    // 调用数据
        uint256 threshold;             // 门槛
        uint256 startTime;             // 开始时间
        uint256 endTime;               // 结束时间
        uint256 executeTime;           // 执行时间
        uint256 forVotes;              // 赞成票 (加权)
        uint256 againstVotes;          // 反对票 (加权)
        uint256 abstainVotes;          // 弃权票 (加权)
        uint256 totalVoters;           // 总投票人数
        bool executed;                 // 是否已执行
        bool cancelled;                // 是否已取消
        uint256 lastProcessedDelegateIndex; // 最后处理的受托人索引 (Gas优化)
    }

    /**
     * @notice 投票结构
     */
    struct Vote {
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool hasVoted;
    }

    // ========== 事件 ==========

    /// @notice 提案创建事件
    event ProposalCreated(
        uint256 indexed id,
        address indexed proposer,
        ProposalType proposalType,
        string title,
        uint256 startTime,
        uint256 endTime
    );

    /// @notice 投票事件
    event VoteCast(
        uint256 indexed proposalId,
        address indexed voter,
        uint256 forVotes,
        uint256 againstVotes,
        uint256 abstainVotes
    );

    /// @notice 提案执行事件
    event ProposalExecuted(uint256 indexed id, address executor);

    /// @notice 投票奖励领取事件
    event VoteRewardClaimed(
        uint256 indexed proposalId,
        address indexed voter,
        uint256 reward
    );

    /// @notice 提案发起人奖励领取事件
    event ProposerRewardClaimed(
        uint256 indexed proposalId,
        address indexed proposer,
        uint256 reward
    );

    /// @notice 从 EmissionController 接收治理资金事件
    event GovernanceFundsReceived(uint256 amount);

    /// @notice 提案取消事件
    event ProposalCancelled(uint256 indexed id, address canceller);

    /// @notice 门槛更新事件
    event ThresholdUpdated(
        ProposalType proposalType,
        uint256 oldThreshold,
        uint256 newThreshold
    );

    /// @notice KYC 验证状态更新
    event KYCUpdated(address indexed user, bool isVerified);

    // ========== GOV-06修复: 否决机制事件 ==========

    /// @notice 否决发起事件
    event VetoInitiated(
        uint256 indexed vetoId,
        uint256 indexed proposalId,
        VetoType vetoType,
        address indexed initiator
    );

    /// @notice 否决投票事件
    event VetoVoteCast(
        uint256 indexed vetoId,
        address indexed voter,
        bool support,
        uint256 weight
    );

    /// @notice 否决执行事件
    event VetoExecuted(
        uint256 indexed vetoId,
        uint256 indexed proposalId,
        bool passed
    );

    /// @notice 贡献积分更新
    event ContributionPointsUpdated(
        address indexed user,
        uint256 oldPoints,
        uint256 newPoints
    );

    // ========== 委托事件 ==========

    /// @notice 委托事件
    event Delegated(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 expiryTime
    );

    /// @notice 取消委托事件
    event Undelegated(
        address indexed from,
        address indexed to,
        uint256 amount
    );

    /// @notice 待生效委托事件
    event PendingDelegationCreated(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 effectiveTime
    );

    /// @notice 委托过期事件
    event DelegationExpired(
        address indexed from,
        address indexed to
    );

    /// @notice 治理奖励事件
    event GovernanceRewardClaimed(
        address indexed user,
        uint256 amount
    );

    /// @notice 治理奖励参数更新
    event GovernanceRewardParamsUpdated(
        uint256 voteReward,
        uint256 proposalReward
    );

    /// @notice 释放控制器更新
    event EmissionControllerUpdated(
        address indexed oldAddress,
        address indexed newAddress
    );

    /// @notice 治理奖励接收
    event GovernanceRewardsReceived(
        uint256 amount,
        address indexed from
    );

    // ========== 贡献积分事件 ==========

    /// @notice 贡献提交事件
    event ContributionSubmitted(
        uint256 indexed recordId,
        address indexed contributor,
        ContributionType contributionType,
        uint256 points,
        string evidence
    );

    /// @notice 贡献验证事件
    event ContributionVerified(
        uint256 indexed recordId,
        address indexed contributor,
        uint256 points,
        address indexed verifier
    );

    /// @notice 贡献类型积分更新事件
    event ContributionTypePointsUpdated(
        ContributionType indexed contributionType,
        uint256 oldPoints,
        uint256 newPoints
    );

    /// @notice 验证者设置事件
    event ContributionVerifierSet(
        address indexed verifier,
        bool isVerifier
    );

    // ========== 委托恢复事件 ==========

    /// @notice 委托恢复请求事件
    event DelegationRecoveryRequested(
        address indexed delegator,
        address indexed delegatee,
        uint256 requestTime
    );

    /// @notice 委托恢复执行事件
    event DelegationRecovered(
        address indexed delegator,
        address indexed delegatee,
        uint256 amount
    );

    /// @notice 连续弃权记录事件
    event ConsecutiveAbstentionRecorded(
        address indexed delegatee,
        uint256 consecutiveCount
    );

    // ========== 治理执行白名单事件 ==========

    /// @notice 执行目标白名单更新事件
    event ExecutionTargetUpdated(
        address indexed target,
        bool isAllowed
    );

    /// @notice 执行函数白名单更新事件
    event ExecutionFunctionUpdated(
        bytes4 indexed functionSelector,
        bool isAllowed
    );

    /// @notice 执行白名单开关事件
    event ExecutionWhitelistToggled(bool enabled);

    /// @notice 白名单禁用发起事件
    event WhitelistDisableInitiated(uint256 effectiveTime);

    /// @notice 白名单变更取消事件
    event WhitelistChangeCancelled();

    /// @notice 目标合约允许所有函数事件
    event TargetAllowAllFunctionsUpdated(
        address indexed target,
        bool allowAll
    );

    // ========== 修饰符 ==========

    /// @notice 检查提案是否存在
    modifier proposalExists(uint256 proposalId) {
        require(proposalId < proposals.length, "VIBGovernance: proposal does not exist");
        _;
    }

    /// @notice 检查提案状态
    modifier proposalActive(uint256 proposalId) {
        require(
            proposals[proposalId].state == ProposalState.ACTIVE,
            "VIBGovernance: proposal not active"
        );
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _vibeToken VIBE 代币地址
     */
    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBGovernance: invalid token address");
        vibeToken = IERC20(_vibeToken);
    }

    // ========== 外部函数 ==========

    /**
     * @notice 创建提案
     * @param proposalType 提案类型
     * @param title 标题
     * @param description 描述
     * @param target 目标合约
     * @param data 调用数据
     * @return 提案 ID
     */
    function createProposal(
        ProposalType proposalType,
        string memory title,
        string memory description,
        address target,
        bytes memory data
    ) external nonReentrant whenNotPaused returns (uint256) {
        // 检查投票权（使用投票权而非代币余额，更安全）
        uint256 votingPower = getVotingPower(msg.sender);
        require(votingPower > 0, "VIBGovernance: no voting power");

        // 检查门槛（使用投票权）
        uint256 threshold = _getThreshold(proposalType);
        require(
            votingPower >= threshold,
            "VIBGovernance: below proposal threshold"
        );

        // 创建提案
        uint256 proposalId = proposals.length;
        uint256 duration = _getDuration(proposalType);
        uint256 startTime = block.timestamp;
        uint256 endTime = startTime + duration;
        uint256 executeTime = endTime + _getTimelock(proposalType);

        proposals.push(Proposal({
            id: proposalId,
            proposer: msg.sender,
            proposalType: proposalType,
            state: ProposalState.ACTIVE,
            title: title,
            description: description,
            target: target,
            data: data,
            threshold: threshold,
            startTime: startTime,
            endTime: endTime,
            executeTime: executeTime,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            totalVoters: 0,
            executed: false,
            cancelled: false,
            lastProcessedDelegateIndex: 0
        }));

        proposalCount[msg.sender]++;

        // 累计提案奖励（检查是否有足够余额预留）
        if (governanceRewardBalance >= totalPendingRewards + proposalReward) {
            pendingGovernanceRewards[msg.sender] += proposalReward;
            totalPendingRewards += proposalReward;
        }

        emit ProposalCreated(proposalId, msg.sender, proposalType, title, startTime, endTime);

        return proposalId;
    }

    /**
     * @notice 投票
     * @param proposalId 提案 ID
     * @param support 支持 (1=赞成, 0=反对, 2=弃权)
     */
    function castVote(uint256 proposalId, uint8 support)
        external
        nonReentrant
        proposalExists(proposalId)
        proposalActive(proposalId)
    {
        require(support <= 2, "VIBGovernance: invalid support value");
        require(!hasVoted[proposalId][msg.sender], "VIBGovernance: already voted");

        // 自动检查并处理过期委托
        _autoCheckDelegationExpiry(msg.sender);

        Proposal storage proposal = proposals[proposalId];

        // 检查投票时间
        require(
            block.timestamp >= proposal.startTime && block.timestamp <= proposal.endTime,
            "VIBGovernance: voting not within period"
        );

        // ========== 闪电贷防护 ==========
        // 检查投票权是否在当前区块内发生变化
        if (flashLoanProtectionEnabled) {
            require(
                votingPowerLastUpdateBlock[msg.sender] < block.number,
                "VIBGovernance: voting power changed in this block (flash loan protection)"
            );

            // 检查最小持有期：用户必须持有投票权至少1天
            uint256 acquireTime = votingPowerAcquireTime[msg.sender];
            if (acquireTime > 0) {
                require(
                    block.timestamp >= acquireTime + MIN_VOTING_HOLD_PERIOD,
                    "VIBGovernance: must hold voting power for minimum period"
                );
            }
        }

        // 获取投票权
        uint256 votingPower = getVotingPower(msg.sender);
        require(votingPower > 0, "VIBGovernance: no voting power");

        // 记录投票区块
        voteCastBlock[proposalId][msg.sender] = block.number;

        // 记录投票
        hasVoted[proposalId][msg.sender] = true;
        proposal.totalVoters++;

        if (support == 1) {
            proposal.forVotes += votingPower;
            votes[proposalId][msg.sender].forVotes = votingPower;
        } else if (support == 0) {
            proposal.againstVotes += votingPower;
            votes[proposalId][msg.sender].againstVotes = votingPower;
        } else {
            proposal.abstainVotes += votingPower;
            votes[proposalId][msg.sender].abstainVotes = votingPower;
        }

        votes[proposalId][msg.sender].hasVoted = true;

        // ========== 记录受托人投票（用于弃权恢复机制）==========
        _recordDelegateeVote(proposalId, msg.sender);

        // ========== 白皮书规定的投票奖励 ==========
        // 奖励将在提案执行后根据结果发放
        // 这里只记录投票信息，不立即发放奖励

        emit VoteCast(proposalId, msg.sender, votes[proposalId][msg.sender].forVotes,
            votes[proposalId][msg.sender].againstVotes, votes[proposalId][msg.sender].abstainVotes);
    }

    /**
     * @notice 计算投票奖励（提案执行后调用）
     * @param proposalId 提案 ID
     * @param voter 投票者地址
     * @return reward 奖励金额
     */
    function calculateVoteReward(uint256 proposalId, address voter) public view returns (uint256) {
        if (!hasVoted[proposalId][voter]) return 0;

        Proposal storage proposal = proposals[proposalId];
        Vote storage voterVote = votes[proposalId][voter];

        // 只有通过的提案才给赞成票奖励
        if (proposal.state == ProposalState.EXECUTED || proposal.state == ProposalState.SUCCEEDED) {
            // 对通过提案投赞成票: 0.01 VIBE/票
            if (voterVote.forVotes > 0 && proposal.forVotes > proposal.againstVotes) {
                return voterVote.forVotes * FOR_VOTE_REWARD_PER_POWER / 10**18;
            }
        }

        // 只有被否决的提案才给反对票奖励
        if (proposal.state == ProposalState.DEFEATED) {
            // 对否决提案投反对票: 0.005 VIBE/票
            if (voterVote.againstVotes > 0) {
                return voterVote.againstVotes * AGAINST_VOTE_REWARD_PER_POWER / 10**18;
            }
        }

        return 0;
    }

    /**
     * @notice 执行提案
     * @param proposalId 提案 ID
     * @dev 安全修复: 添加了目标合约和函数白名单验证，防止任意调用漏洞
     */
    function executeProposal(uint256 proposalId)
        external
        nonReentrant
        proposalExists(proposalId)
    {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.state == ProposalState.SUCCEEDED, "VIBGovernance: proposal not succeeded");
        require(!proposal.executed, "VIBGovernance: already executed");
        require(block.timestamp >= proposal.executeTime, "VIBGovernance: timelock not expired");

        // 执行提案
        proposal.executed = true;
        proposal.state = ProposalState.EXECUTED;

        // 如果有目标合约和调用数据，执行调用
        if (proposal.target != address(0) && proposal.data.length > 0) {
            // 安全修复: 检查目标合约是否在白名单中
            if (executionWhitelistEnabled) {
                require(
                    allowedExecutionTargets[proposal.target],
                    "VIBGovernance: target not allowed"
                );

                // 如果目标合约未被标记为"允许所有函数"，则需要检查函数选择器
                if (!allowAllFunctionsForTarget[proposal.target]) {
                    require(proposal.data.length >= 4, "VIBGovernance: invalid data length");
                    // 从 bytes 中提取前 4 字节作为函数选择器
                    bytes4 functionSelector = _extractFunctionSelector(proposal.data);
                    require(
                        allowedExecutionFunctions[functionSelector],
                        "VIBGovernance: function not allowed"
                    );
                }
            }

            (bool success, ) = proposal.target.call(proposal.data);
            require(success, "VIBGovernance: execution failed");
        }

        // ========== 白皮书规定的提案发起人奖励 ==========
        // 对通过提案的发起人: 50-500 VIBE
        if (!proposerRewardClaimed[proposalId]) {
            proposerRewardClaimed[proposalId] = true;

            // 根据提案类型计算奖励
            uint256 proposerReward = _calculateProposerReward(proposal);

            if (proposerReward > 0 && governanceRewardBalance >= totalPendingRewards + proposerReward) {
                pendingGovernanceRewards[proposal.proposer] += proposerReward;
                totalPendingRewards += proposerReward;
            }
        }

        emit ProposalExecuted(proposalId, msg.sender);
    }

    /**
     * @notice 结束提案并更新状态
     * @dev 在投票期结束后调用，更新提案状态并检查受托人弃权情况
     * @param proposalId 提案 ID
     */
    function finalizeProposal(uint256 proposalId)
        external
        nonReentrant
        proposalExists(proposalId)
    {
        Proposal storage proposal = proposals[proposalId];

        require(
            proposal.state == ProposalState.ACTIVE || proposal.state == ProposalState.PENDING_FINALIZATION,
            "VIBGovernance: proposal not active"
        );

        // 如果是第一次调用（ACTIVE状态），计算投票结果
        if (proposal.state == ProposalState.ACTIVE) {
            require(block.timestamp > proposal.endTime, "VIBGovernance: voting still ongoing");

            // 计算投票结果
            uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
            uint256 requiredRate = _getRequiredPassRate(proposal.proposalType);

            if (totalVotes == 0) {
                proposal.state = ProposalState.DEFEATED;
            } else {
                uint256 passRate = (proposal.forVotes * 10000) / totalVotes;
                if (passRate >= requiredRate) {
                    proposal.state = ProposalState.SUCCEEDED;
                } else {
                    proposal.state = ProposalState.DEFEATED;
                }
            }
        }

        // ========== 检查受托人弃权情况 ==========
        // 遍历所有受托人（有收到委托的地址）
        // 使用分批处理避免 gas 溢出，每次最多处理 100 个
        address[] memory allDelegates = _getAllActiveDelegates();
        uint256 batchSize = 100;
        uint256 processed = 0;

        // 记录当前提案检查到的位置
        uint256 lastProcessedKey = proposal.lastProcessedDelegateIndex;

        for (uint256 i = lastProcessedKey; i < allDelegates.length && processed < batchSize; i++) {
            _checkDelegateeAbstention(proposalId, allDelegates[i]);
            proposal.lastProcessedDelegateIndex = i + 1;
            processed++;
        }

        // 如果还有未处理的受托人，标记提案需要继续处理
        if (proposal.lastProcessedDelegateIndex < allDelegates.length) {
            proposal.state = ProposalState.PENDING_FINALIZATION;
        }
    }

    /**
     * @notice 获取所有活跃的受托人地址
     * @return 受托人地址列表
     */
    function _getAllActiveDelegates() internal view returns (address[] memory) {
        return activeDelegatees;
    }

    /**
     * @notice 清理不活跃的受托人（gas 优化）
     * @param limit 处理数量限制
     */
    function cleanupInactiveDelegatees(uint256 limit) external {
        uint256 cleaned = 0;
        uint256 i = 0;

        while (i < activeDelegatees.length && cleaned < limit) {
            address delegatee = activeDelegatees[i];

            // 检查是否仍然活跃（还有委托）
            if (delegatedVotes[delegatee] == 0) {
                // 移除：将最后一个元素移到当前位置
                activeDelegatees[i] = activeDelegatees[activeDelegatees.length - 1];
                activeDelegatees.pop();
                isActiveDelegatee[delegatee] = false;
                cleaned++;
                // 不增加 i，因为新元素在当前位置
            } else {
                i++;
            }
        }
    }

    /**
     * @notice 获取活跃受托人数量
     * @return 受托人数量
     */
    function getActiveDelegateeCount() external view returns (uint256) {
        return activeDelegatees.length;
    }

    /**
     * @notice 计算提案发起人奖励
     * @param proposal 提案信息
     * @return reward 奖励金额 (50-500 VIBE)
     */
    function _calculateProposerReward(Proposal storage proposal) internal view returns (uint256) {
        // 只有成功执行的提案才有奖励
        if (proposal.state != ProposalState.EXECUTED) return 0;

        // 基础奖励 50 VIBE
        uint256 baseReward = PROPOSER_MIN_REWARD;

        // 根据提案类型增加奖励
        if (proposal.proposalType == ProposalType.PARAMETER) {
            // 参数调整提案: 100 VIBE
            baseReward = 100 * 10**18;
        } else if (proposal.proposalType == ProposalType.UPGRADE) {
            // 协议升级提案: 500 VIBE
            baseReward = PROPOSER_MAX_REWARD;
        }

        // 根据参与度增加奖励
        uint256 participationBonus = 0;
        if (proposal.totalVoters >= 100) {
            participationBonus = 50 * 10**18;
        } else if (proposal.totalVoters >= 50) {
            participationBonus = 25 * 10**18;
        }

        uint256 totalReward = baseReward + participationBonus;

        // 确保不超过最大奖励
        if (totalReward > PROPOSER_MAX_REWARD) {
            totalReward = PROPOSER_MAX_REWARD;
        }

        return totalReward;
    }

    /**
     * @notice 领取投票奖励
     * @param proposalId 提案 ID
     */
    function claimVoteReward(uint256 proposalId) external nonReentrant {
        require(hasVoted[proposalId][msg.sender], "VIBGovernance: not voted");

        Proposal storage proposal = proposals[proposalId];
        require(
            proposal.state == ProposalState.EXECUTED ||
            proposal.state == ProposalState.DEFEATED,
            "VIBGovernance: proposal not finalized"
        );

        // 检查是否已领取
        require(voteRewards[proposalId][msg.sender] == 0, "VIBGovernance: reward already claimed");

        // 计算奖励
        uint256 reward = calculateVoteReward(proposalId, msg.sender);

        if (reward > 0) {
            // 如果余额不足，尝试从 EmissionController 请求资金
            if (governanceRewardBalance < reward && emissionController != address(0)) {
                uint256 needed = reward - governanceRewardBalance;
                // 请求更多一些以减少请求频率
                uint256 requestAmount = needed + 100 * 10**18; // 额外100 VIBE

                if (IEmissionController(emissionController).canRequestGovernanceFunds(requestAmount)) {
                    IEmissionController(emissionController).requestGovernanceFunds(requestAmount);
                    governanceRewardBalance += requestAmount;
                }
            }

            if (governanceRewardBalance >= reward) {
                voteRewards[proposalId][msg.sender] = reward;
                governanceRewardBalance -= reward;

                // 直接转账
                vibeToken.transfer(msg.sender, reward);

                emit VoteRewardClaimed(proposalId, msg.sender, reward);
            }
        }
    }

    /**
     * @notice 手动请求治理资金（管理员调用）
     * @param amount 请求金额
     */
    function requestGovernanceFundsFromEmission(uint256 amount) external onlyOwner {
        require(emissionController != address(0), "VIBGovernance: no emission controller");
        require(IEmissionController(emissionController).canRequestGovernanceFunds(amount), "VIBGovernance: cannot request amount");

        IEmissionController(emissionController).requestGovernanceFunds(amount);
        governanceRewardBalance += amount;

        emit GovernanceFundsReceived(amount);
    }

    /**
     * @notice 取消提案
     * @param proposalId 提案 ID
     */
    function cancelProposal(uint256 proposalId)
        external
        nonReentrant
        proposalExists(proposalId)
    {
        Proposal storage proposal = proposals[proposalId];

        require(
            msg.sender == proposal.proposer || msg.sender == owner(),
            "VIBGovernance: not authorized"
        );
        require(
            proposal.state == ProposalState.ACTIVE || proposal.state == ProposalState.PENDING,
            "VIBGovernance: cannot cancel"
        );

        proposal.cancelled = true;
        proposal.state = ProposalState.CANCELLED;

        emit ProposalCancelled(proposalId, msg.sender);
    }

    // ========== GOV-06修复: 三层治理互相否决机制 ==========

    /**
     * @notice 发起否决
     * @param proposalId 被否决的提案ID
     * @param vetoType 否决类型
     * @dev 投资者可否决生产权重>50%的提案，生产者可否决纯资本权重提案
     */
    function initiateVeto(
        uint256 proposalId,
        VetoType vetoType
    ) external nonReentrant whenNotPaused proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        // 验证提案状态
        require(proposal.state == ProposalState.SUCCEEDED, "VIBGovernance: proposal not succeeded");
        require(!proposal.executed, "VIBGovernance: proposal already executed");

        // 验证没有已存在的否决
        require(proposalVetoIndex[proposalId] == 0, "VIBGovernance: veto already exists");

        // 验证否决条件
        _validateVetoCondition(proposalId, vetoType);

        // 创建否决记录
        uint256 vetoId = vetoRecords.length;
        vetoRecords.push(VetoRecord({
            proposalId: proposalId,
            vetoType: vetoType,
            initiator: msg.sender,
            initiatedTime: block.timestamp,
            vetoVotes: 0,
            opposeVotes: 0,
            votingEndTime: block.timestamp + VETO_VOTING_PERIOD,
            executed: false,
            passed: false
        }));

        // 记录提案到否决的映射（+1 因为0表示不存在）
        proposalVetoIndex[proposalId] = vetoId + 1;

        emit VetoInitiated(vetoId, proposalId, vetoType, msg.sender);
    }

    /**
     * @notice 对否决投票
     * @param vetoId 否决记录ID
     * @param support 是否支持否决
     */
    function voteOnVeto(
        uint256 vetoId,
        bool support
    ) external nonReentrant whenNotPaused {
        require(vetoId < vetoRecords.length, "VIBGovernance: invalid veto id");

        VetoRecord storage vetoRecord = vetoRecords[vetoId];
        require(!vetoRecord.executed, "VIBGovernance: veto already executed");
        require(block.timestamp < vetoRecord.votingEndTime, "VIBGovernance: voting ended");
        require(!vetoVoted[vetoId][msg.sender], "VIBGovernance: already voted");

        // 根据否决类型获取投票权重
        uint256 weight = _getVetoVotingWeight(vetoRecord.vetoType, msg.sender);
        require(weight > 0, "VIBGovernance: no voting weight for this veto type");

        vetoVoted[vetoId][msg.sender] = true;

        if (support) {
            vetoRecord.vetoVotes += weight;
        } else {
            vetoRecord.opposeVotes += weight;
        }

        emit VetoVoteCast(vetoId, msg.sender, support, weight);
    }

    /**
     * @notice 执行否决结果
     * @param vetoId 否决记录ID
     */
    function executeVeto(uint256 vetoId) external nonReentrant {
        require(vetoId < vetoRecords.length, "VIBGovernance: invalid veto id");

        VetoRecord storage vetoRecord = vetoRecords[vetoId];
        require(!vetoRecord.executed, "VIBGovernance: veto already executed");
        require(block.timestamp >= vetoRecord.votingEndTime, "VIBGovernance: voting not ended");

        vetoRecord.executed = true;

        // 计算否决是否通过
        uint256 totalVotes = vetoRecord.vetoVotes + vetoRecord.opposeVotes;
        if (totalVotes > 0) {
            vetoRecord.passed = (vetoRecord.vetoVotes * 10000) / totalVotes >= VETO_PASS_THRESHOLD;
        }

        // 如果否决通过，取消提案
        if (vetoRecord.passed) {
            Proposal storage proposal = proposals[vetoRecord.proposalId];
            proposal.state = ProposalState.CANCELLED;
            proposal.cancelled = true;
        }

        emit VetoExecuted(vetoId, vetoRecord.proposalId, vetoRecord.passed);
    }

    /**
     * @notice 检查社区否决条件（自动触发）
     * @param proposalId 提案ID
     * @return 是否应触发社区否决
     * @dev GOV-06修复: 简化实现，使用整体反对率作为社区反对率的代理
     */
    function checkCommunityVetoCondition(uint256 proposalId) public view proposalExists(proposalId) returns (bool) {
        Proposal storage proposal = proposals[proposalId];

        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        if (totalVotes == 0) return false;

        uint256 oppositionRate = (proposal.againstVotes * 10000) / totalVotes;
        return oppositionRate >= COMMUNITY_OPPOSITION_THRESHOLD;
    }

    /**
     * @notice 验证否决条件
     * @dev GOV-06修复: 简化实现，基于提案投票统计估算权重比例
     */
    function _validateVetoCondition(uint256 proposalId, VetoType vetoType) internal view {
        Proposal storage proposal = proposals[proposalId];

        // 获取总投票权
        uint256 totalVP = _getTotalVotingPower();
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;

        require(totalVotes > 0, "VIBGovernance: no votes cast");

        if (vetoType == VetoType.INVESTOR_VETO) {
            // 投资者否决权：生产权重>50%的提案
            // 估算：如果投票参与度高且生产权重层参与，认为生产权重高
            // 简化实现：检查提案支持率是否异常高（可能被生产权重主导）
            uint256 supportRatio = (proposal.forVotes * 10000) / totalVotes;

            // 如果支持率>70%且总投票>总投票权的5%，可能需要投资者否决
            require(
                supportRatio > 7000 && totalVotes > (totalVP * 500) / 10000,
                "VIBGovernance: investor veto conditions not met"
            );

        } else if (vetoType == VetoType.PRODUCER_VETO) {
            // 生产者否决权：纯资本权重提案
            // 检查是否有足够的投票参与（如果参与度极低，可能只有资本方参与）
            // 简化实现：检查投票人数是否少于KYC用户数的10%
            uint256 minVoters = kycUserCount > 0 ? (kycUserCount * 10) / 100 : 1;

            require(
                proposal.totalVoters < minVoters && totalVotes > 0,
                "VIBGovernance: not a pure capital weight proposal"
            );

        } else if (vetoType == VetoType.COMMUNITY_VETO) {
            // 社区否决权：社区反对率>60%
            uint256 oppositionRate = (proposal.againstVotes * 10000) / totalVotes;

            require(
                oppositionRate >= COMMUNITY_OPPOSITION_THRESHOLD,
                "VIBGovernance: community opposition not exceeding threshold"
            );
        }
    }

    /**
     * @notice 根据否决类型获取投票权重
     */
    function _getVetoVotingWeight(VetoType vetoType, address voter) internal view returns (uint256) {
        if (vetoType == VetoType.INVESTOR_VETO) {
            // 投资者否决：只有资本权重有效
            return _getCapitalWeight(voter);
        } else if (vetoType == VetoType.PRODUCER_VETO) {
            // 生产者否决：只有生产权重有效
            return _getProductionWeight(voter);
        } else {
            // 社区否决：只有社区权重有效
            return _getCommunityWeight(voter);
        }
    }

    /**
     * @notice 获取否决记录数量
     */
    function getVetoCount() external view returns (uint256) {
        return vetoRecords.length;
    }

    /**
     * @notice 获取否决记录
     */
    function getVetoRecord(uint256 vetoId) external view returns (VetoRecord memory) {
        require(vetoId < vetoRecords.length, "VIBGovernance: invalid veto id");
        return vetoRecords[vetoId];
    }

    // ========== 委托函数 ==========

    /**
     * @notice 委托投票权给他人
     * @param to 委托目标地址
     * @param duration 委托时长（秒），最长90天
     */
    function delegate(address to, uint256 duration)
        external
        nonReentrant
        whenNotPaused
    {
        require(to != address(0), "VIBGovernance: invalid delegate");
        require(to != msg.sender, "VIBGovernance: cannot delegate to self");
        require(duration > 0 && duration <= MAX_DELEGATION_DURATION, "VIBGovernance: invalid duration");

        // 自动检查并处理过期委托（允许重新委托）
        _autoCheckDelegationExpiry(msg.sender);

        // 检查是否已委托
        require(delegates[msg.sender] == address(0), "VIBGovernance: already delegated");

        // 检查目标是否已委托给别人（不允许转委托）
        require(delegates[to] == address(0), "VIBGovernance: target has delegated");

        // 获取用户投票权
        uint256 votingPower = _getOwnVotingPower(msg.sender);
        require(votingPower > 0, "VIBGovernance: no voting power to delegate");

        // 检查目标地址是否超过 5% 限制
        uint256 newDelegatedVotes = delegatedVotes[to] + votingPower;
        uint256 totalVotes = _getTotalVotingPower();
        uint256 maxAllowed = (totalVotes * MAX_DELEGATION_ACCEPT_RATIO) / 10000;

        // 如果总票数为0或很小，用当前票数作为基准（避免小规模场景下的过度限制）
        // 最小总投票权阈值：10000 VIBE
        uint256 MIN_TOTAL_FOR_DELEGATION_LIMIT = 10000 * 10**18;
        if (totalVotes == 0 || totalVotes < MIN_TOTAL_FOR_DELEGATION_LIMIT) {
            maxAllowed = votingPower; // 允许委托
        }

        require(newDelegatedVotes <= maxAllowed, "VIBGovernance: exceeds 5% delegation limit");

        // 检查是否需要延迟生效（大额变动）
        // 只有当总投票权足够大时才应用延迟，避免小规模场景下的过度限制
        if (votingPower > (totalVotes * LARGE_VOTE_CHANGE_THRESHOLD) / 10000 &&
            totalVotes > 0 &&
            totalVotes >= MIN_TOTAL_FOR_DELEGATION_LIMIT) {
            // 创建待生效委托
            pendingDelegations[msg.sender] = PendingDelegation({
                from: msg.sender,
                to: to,
                amount: votingPower,
                effectiveTime: block.timestamp + LARGE_VOTE_CHANGE_DELAY,
                isActive: true
            });

            emit PendingDelegationCreated(msg.sender, to, votingPower, block.timestamp + LARGE_VOTE_CHANGE_DELAY);
        } else {
            // 立即生效
            _executeDelegation(msg.sender, to, votingPower, duration);
        }
    }

    /**
     * @notice 执行待生效的委托
     */
    function executePendingDelegation() external nonReentrant whenNotPaused {
        PendingDelegation storage pending = pendingDelegations[msg.sender];
        require(pending.isActive, "VIBGovernance: no pending delegation");
        require(block.timestamp >= pending.effectiveTime, "VIBGovernance: not yet effective");

        // 执行委托
        _executeDelegation(pending.from, pending.to, pending.amount, MAX_DELEGATION_DURATION);

        // 清除待生效记录
        pending.isActive = false;
    }

    /**
     * @notice 取消委托
     */
    function undelegate() external nonReentrant whenNotPaused {
        address delegateAddr = delegates[msg.sender];
        require(delegateAddr != address(0), "VIBGovernance: not delegated");

        // 检查是否有待生效的委托
        if (pendingDelegations[msg.sender].isActive) {
            pendingDelegations[msg.sender].isActive = false;
            emit Undelegated(msg.sender, pendingDelegations[msg.sender].to, pendingDelegations[msg.sender].amount);
            return;
        }

        uint256 amount = delegatedOut[msg.sender];

        // 更新状态
        delegates[msg.sender] = address(0);
        delegatedVotes[delegateAddr] -= amount;
        delegatedOut[msg.sender] = 0;
        delegationStartTime[msg.sender] = 0;
        delegationExpiryTime[msg.sender] = 0;
        totalDelegatedVotes -= amount;

        // 移除委托来源记录
        isDelegationSource[delegateAddr][msg.sender] = false;
        receivedDelegationCount[delegateAddr]--;

        emit Undelegated(msg.sender, delegateAddr, amount);
    }

    /**
     * @notice 取消收到的委托（委托目标可以拒绝）
     * @param from 委托来源地址
     */
    function revokeDelegation(address from) external nonReentrant whenNotPaused {
        require(delegates[from] == msg.sender, "VIBGovernance: not your delegator");

        uint256 amount = delegatedOut[from];

        // 更新状态
        delegates[from] = address(0);
        delegatedVotes[msg.sender] -= amount;
        delegatedOut[from] = 0;
        delegationStartTime[from] = 0;
        delegationExpiryTime[from] = 0;
        totalDelegatedVotes -= amount;

        // 移除委托来源记录
        isDelegationSource[msg.sender][from] = false;
        receivedDelegationCount[msg.sender]--;

        emit Undelegated(from, msg.sender, amount);
    }

    /**
     * @notice 检查并处理过期委托
     * @param user 用户地址
     */
    function checkDelegationExpiry(address user) external {
        if (delegates[user] != address(0) && block.timestamp >= delegationExpiryTime[user]) {
            address delegateAddr = delegates[user];
            uint256 amount = delegatedOut[user];

            // 更新状态
            delegates[user] = address(0);
            delegatedVotes[delegateAddr] -= amount;
            delegatedOut[user] = 0;
            delegationStartTime[user] = 0;
            delegationExpiryTime[user] = 0;
            totalDelegatedVotes -= amount;

            // 移除委托来源记录
            isDelegationSource[delegateAddr][user] = false;
            receivedDelegationCount[delegateAddr]--;

            emit DelegationExpired(user, delegateAddr);
        }
    }

    // ========== 委托内部函数 ==========

    /**
     * @notice 自动检查并处理过期委托（内部函数）
     * @dev 在关键操作（如投票）前自动调用
     * @param user 用户地址
     */
    function _autoCheckDelegationExpiry(address user) internal {
        if (delegates[user] != address(0) && block.timestamp >= delegationExpiryTime[user]) {
            address delegateAddr = delegates[user];
            uint256 amount = delegatedOut[user];

            // 更新状态
            delegates[user] = address(0);
            delegatedVotes[delegateAddr] -= amount;
            delegatedOut[user] = 0;
            delegationStartTime[user] = 0;
            delegationExpiryTime[user] = 0;
            totalDelegatedVotes -= amount;

            // 移除委托来源记录
            isDelegationSource[delegateAddr][user] = false;
            receivedDelegationCount[delegateAddr]--;

            emit DelegationExpired(user, delegateAddr);
        }
    }

    /**
     * @notice 执行委托
     */
    function _executeDelegation(address from, address to, uint256 amount, uint256 duration) internal {
        // 更新状态
        delegates[from] = to;
        delegatedVotes[to] += amount;
        delegatedOut[from] = amount;
        delegationStartTime[from] = block.timestamp;
        delegationExpiryTime[from] = block.timestamp + duration;
        totalDelegatedVotes += amount;

        // ========== 闪电贷防护：记录区块号 ==========
        votingPowerLastUpdateBlock[from] = block.number;
        votingPowerLastUpdateBlock[to] = block.number;

        // 添加委托来源记录
        if (!isDelegationSource[to][from]) {
            delegationSources[to].push(from);
            isDelegationSource[to][from] = true;
            receivedDelegationCount[to]++;
        }

        // 添加到活跃受托人列表
        if (!isActiveDelegatee[to]) {
            activeDelegatees.push(to);
            isActiveDelegatee[to] = true;
        }

        emit Delegated(from, to, amount, block.timestamp + duration);
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置闪电贷防护开关
     * @param enabled 是否启用
     * @dev 安全增强: 禁用需要7天时间锁
     */
    function setFlashLoanProtection(bool enabled) external onlyOwner {
        if (enabled) {
            // 启用立即生效
            flashLoanProtectionEnabled = true;
            flashLoanProtectionChangeTime = 0;
        } else {
            // 禁用需要时间锁
            flashLoanProtectionChangeTime = block.timestamp + 7 days;
        }
    }

    /**
     * @notice 确认禁用闪电贷防护
     */
    function confirmFlashLoanProtectionDisable() external onlyOwner {
        require(flashLoanProtectionChangeTime > 0, "No pending change");
        require(block.timestamp >= flashLoanProtectionChangeTime, "Timelock not elapsed");

        flashLoanProtectionEnabled = false;
        flashLoanProtectionChangeTime = 0;
    }

    /**
     * @notice 更新投票权变更区块号（供外部合约调用）
     * @param user 用户地址
     */
    function updateVotingPowerBlock(address user) external {
        // 只有质押合约或管理员可以调用
        require(
            msg.sender == stakingContract || msg.sender == owner(),
            "VIBGovernance: unauthorized"
        );
        votingPowerLastUpdateBlock[user] = block.number;

        // 如果用户之前没有投票权，记录获取时间（用于最小持有期检查）
        if (votingPowerAcquireTime[user] == 0) {
            votingPowerAcquireTime[user] = block.timestamp;
        }
    }

    /**
     * @notice 更新质押合约地址
     * @param _stakingContract 质押合约地址
     */
    function setStakingContract(address _stakingContract) external onlyOwner {
        require(_stakingContract != address(0), "VIBGovernance: invalid address");
        stakingContract = _stakingContract;
        // 同时更新 VIBStaking 接口
        vibStaking = IVIBStaking(_stakingContract);
    }

    /**
     * @notice 单独设置 VIBStaking 接口合约
     * @param _vibStaking VIBStaking 合约地址
     */
    function setVIBStaking(address _vibStaking) external onlyOwner {
        require(_vibStaking != address(0), "VIBGovernance: invalid address");
        vibStaking = IVIBStaking(_vibStaking);
    }

    /**
     * @notice 更新时间锁合约地址
     * @param _timelockContract 时间锁合约地址
     */
    function setTimelockContract(address _timelockContract) external onlyOwner {
        require(_timelockContract != address(0), "VIBGovernance: invalid address");
        timelockContract = _timelockContract;
    }

    /**
     * @notice 更新贡献积分合约地址
     * @param _reputationContract 贡献积分合约地址
     */
    function setReputationContract(address _reputationContract) external onlyOwner {
        require(_reputationContract != address(0), "VIBGovernance: invalid address");
        reputationContract = _reputationContract;
    }

    /**
     * @notice 更新 KYC 合约地址
     * @param _kycContract KYC 合约地址
     */
    function setKycContract(address _kycContract) external onlyOwner {
        require(_kycContract != address(0), "VIBGovernance: invalid address");
        kycContract = _kycContract;
    }

    /**
     * @notice 更新社区基金地址
     * @param _communityFund 社区基金地址
     */
    function setCommunityFund(address _communityFund) external onlyOwner {
        require(_communityFund != address(0), "VIBGovernance: invalid address");
        communityFund = _communityFund;
    }

    /// @notice 批量更新最大数量
    uint256 public constant MAX_BATCH_SIZE = 100;

    /**
     * @notice 批量更新 KYC 状态
     * @param users 用户地址列表
     * @param statuses 状态列表
     */
    function batchUpdateKYC(address[] calldata users, bool[] calldata statuses) external onlyOwner {
        require(users.length == statuses.length, "VIBGovernance: length mismatch");
        require(users.length <= MAX_BATCH_SIZE, "VIBGovernance: batch size too large");

        for (uint256 i = 0; i < users.length; i++) {
            bool wasVerified = kycVerified[users[i]];
            kycVerified[users[i]] = statuses[i];

            // 更新计数器
            if (statuses[i] && !wasVerified) {
                kycUserCount++;
            } else if (!statuses[i] && wasVerified) {
                if (kycUserCount > 0) {
                    kycUserCount--;
                }
            }

            emit KYCUpdated(users[i], statuses[i]);
        }
    }

    // ========== 治理执行白名单管理 ==========

    /**
     * @notice 设置执行目标合约白名单
     * @param target 目标合约地址
     * @param isAllowed 是否允许
     */
    function setExecutionTarget(address target, bool isAllowed) external onlyOwner {
        require(target != address(0), "VIBGovernance: invalid target");
        allowedExecutionTargets[target] = isAllowed;
        emit ExecutionTargetUpdated(target, isAllowed);
    }

    /**
     * @notice 批量设置执行目标合约白名单
     * @param targets 目标合约地址列表
     * @param isAllowed 是否允许
     */
    function batchSetExecutionTargets(address[] calldata targets, bool isAllowed) external onlyOwner {
        for (uint256 i = 0; i < targets.length; i++) {
            require(targets[i] != address(0), "VIBGovernance: invalid target");
            allowedExecutionTargets[targets[i]] = isAllowed;
            emit ExecutionTargetUpdated(targets[i], isAllowed);
        }
    }

    /**
     * @notice 设置执行函数选择器白名单
     * @param functionSelector 函数选择器 (bytes4)
     * @param isAllowed 是否允许
     */
    function setExecutionFunction(bytes4 functionSelector, bool isAllowed) external onlyOwner {
        allowedExecutionFunctions[functionSelector] = isAllowed;
        emit ExecutionFunctionUpdated(functionSelector, isAllowed);
    }

    /**
     * @notice 批量设置执行函数选择器白名单
     * @param functionSelectors 函数选择器列表
     * @param isAllowed 是否允许
     */
    function batchSetExecutionFunctions(bytes4[] calldata functionSelectors, bool isAllowed) external onlyOwner {
        for (uint256 i = 0; i < functionSelectors.length; i++) {
            allowedExecutionFunctions[functionSelectors[i]] = isAllowed;
            emit ExecutionFunctionUpdated(functionSelectors[i], isAllowed);
        }
    }

    /**
     * @notice 设置目标合约允许所有函数（仅对高度可信的合约）
     * @param target 目标合约地址
     * @param allowAll 是否允许所有函数
     * @dev 谨慎使用，仅对经过严格审计的可信合约启用
     */
    function setTargetAllowAllFunctions(address target, bool allowAll) external onlyOwner {
        require(target != address(0), "VIBGovernance: invalid target");
        require(allowedExecutionTargets[target], "VIBGovernance: target not in whitelist");
        allowAllFunctionsForTarget[target] = allowAll;
        emit TargetAllowAllFunctionsUpdated(target, allowAll);
    }

    /**
     * @notice 发起切换执行白名单开关（需要时间锁）
     * @param enabled 是否启用
     * @dev 警告：禁用白名单会降低安全性，仅用于紧急情况
     *      变更需要7天时间锁才能生效
     */
    function setExecutionWhitelistEnabled(bool enabled) external onlyOwner {
        // 安全修复: 如果是要禁用白名单，记录变更等待生效
        // 如果是要启用白名单，立即生效
        if (enabled) {
            // 启用白名单立即生效
            executionWhitelistEnabled = true;
            pendingWhitelistChange = false;
            pendingWhitelistChangeTime = 0;
            emit ExecutionWhitelistToggled(true);
        } else {
            // 禁用白名单需要时间锁
            pendingWhitelistChange = false;
            pendingWhitelistChangeTime = block.timestamp + WHITELIST_CHANGE_DELAY;
            emit WhitelistDisableInitiated(pendingWhitelistChangeTime);
        }
    }

    /**
     * @notice 确认禁用白名单（时间锁到期后）
     */
    function confirmWhitelistDisable() external onlyOwner {
        require(pendingWhitelistChangeTime > 0, "No pending change");
        require(block.timestamp >= pendingWhitelistChangeTime, "Timelock not elapsed");

        executionWhitelistEnabled = false;
        pendingWhitelistChangeTime = 0;
        emit ExecutionWhitelistToggled(false);
    }

    /**
     * @notice 取消待生效的白名单变更
     */
    function cancelWhitelistChange() external onlyOwner {
        require(pendingWhitelistChangeTime > 0, "No pending change");
        pendingWhitelistChangeTime = 0;
        emit WhitelistChangeCancelled();
    }

    /**
     * @notice 检查提案是否可以执行（白名单检查）
     * @param target 目标合约
     * @param data 调用数据
     * @return 是否可以通过白名单检查
     */
    function canExecuteProposal(address target, bytes calldata data) external view returns (bool) {
        if (!executionWhitelistEnabled) {
            return true;
        }
        if (!allowedExecutionTargets[target]) {
            return false;
        }
        if (allowAllFunctionsForTarget[target]) {
            return true;
        }
        if (data.length < 4) {
            return false;
        }
        bytes4 functionSelector = bytes4(data[:4]);
        return allowedExecutionFunctions[functionSelector];
    }

    /**
     * @notice 更新用户贡献积分
     * @param user 用户地址
     * @param points 贡献积分
     * @dev GOV-03修复: 同时添加带时间戳的积分记录
     */
    function updateContributionPoints(address user, uint256 points) external onlyOwner {
        require(user != address(0), "VIBGovernance: invalid address");
        uint256 oldPoints = contributionPoints[user];
        contributionPoints[user] = points;

        // 更新总贡献积分
        if (points > oldPoints) {
            totalContributionPoints += (points - oldPoints);
            // GOV-03修复: 如果是增加积分，添加时间记录
            _addTimedPoints(user, points - oldPoints);
        } else if (oldPoints > points) {
            totalContributionPoints -= (oldPoints - points);
        }

        emit ContributionPointsUpdated(user, oldPoints, points);
    }

    // ========== 贡献积分系统函数 ==========

    /**
     * @notice 初始化贡献类型积分值
     * @dev 只能由 owner 调用
     */
    function initializeContributionTypes() external onlyOwner {
        // 设置各类贡献的默认积分值
        contributionTypePoints[ContributionType.CODE_CONTRIBUTION] = 100 * 10**18;      // 100 积分
        contributionTypePoints[ContributionType.COMMUNITY_BUILDING] = 50 * 10**18;      // 50 积分
        contributionTypePoints[ContributionType.GOVERNANCE_PARTICIPATION] = 20 * 10**18; // 20 积分
        contributionTypePoints[ContributionType.CONTENT_CREATION] = 30 * 10**18;        // 30 积分
        contributionTypePoints[ContributionType.BUG_REPORTING] = 80 * 10**18;           // 80 积分
        contributionTypePoints[ContributionType.SECURITY_AUDIT] = 200 * 10**18;         // 200 积分
        contributionTypePoints[ContributionType.ECOSYSTEM_DEVELOPMENT] = 150 * 10**18;  // 150 积分
    }

    /**
     * @notice 设置贡献类型积分值
     * @param contributionType 贡献类型
     * @param points 积分值
     */
    function setContributionTypePoints(ContributionType contributionType, uint256 points) external onlyOwner {
        require(points <= MAX_SINGLE_CONTRIBUTION_POINTS, "VIBGovernance: points exceed max");
        uint256 oldPoints = contributionTypePoints[contributionType];
        contributionTypePoints[contributionType] = points;
        emit ContributionTypePointsUpdated(contributionType, oldPoints, points);
    }

    /**
     * @notice 设置贡献验证者
     * @param verifier 验证者地址
     * @param isVerifier 是否为验证者
     */
    function setContributionVerifier(address verifier, bool isVerifier) external onlyOwner {
        require(verifier != address(0), "VIBGovernance: invalid address");
        contributionVerifiers[verifier] = isVerifier;
        emit ContributionVerifierSet(verifier, isVerifier);
    }

    /**
     * @notice 提交贡献记录
     * @param contributionType 贡献类型
     * @param points 申请积分（可自定义，由验证者审核）
     * @param evidence 证明材料（IPFS hash 等）
     * @return recordId 贡献记录 ID
     */
    function submitContribution(
        ContributionType contributionType,
        uint256 points,
        string calldata evidence
    ) external whenNotPaused returns (uint256) {
        require(points > 0 && points <= MAX_SINGLE_CONTRIBUTION_POINTS, "VIBGovernance: invalid points");
        require(bytes(evidence).length > 0, "VIBGovernance: evidence required");

        uint256 recordId = contributionRecords.length;

        contributionRecords.push(ContributionRecord({
            contributor: msg.sender,
            contributionType: contributionType,
            points: points,
            timestamp: block.timestamp,
            evidence: evidence,
            verified: false,
            verifier: address(0)
        }));

        userContributionIndices[msg.sender].push(recordId);
        pendingContributionsCount++;

        emit ContributionSubmitted(recordId, msg.sender, contributionType, points, evidence);

        return recordId;
    }

    /**
     * @notice 验证贡献记录
     * @param recordId 贡献记录 ID
     * @param approved 是否批准
     * @param adjustedPoints 调整后的积分（如果批准）
     */
    function verifyContribution(
        uint256 recordId,
        bool approved,
        uint256 adjustedPoints
    ) external whenNotPaused {
        require(contributionVerifiers[msg.sender], "VIBGovernance: not a verifier");
        _verifyContributionInternal(recordId, approved, adjustedPoints);
    }

    /**
     * @notice 批量验证贡献记录
     * @param recordIds 贡献记录 ID 列表
     * @param approvedList 是否批准列表
     * @param adjustedPointsList 调整后积分列表
     */
    function batchVerifyContributions(
        uint256[] calldata recordIds,
        bool[] calldata approvedList,
        uint256[] calldata adjustedPointsList
    ) external whenNotPaused {
        require(contributionVerifiers[msg.sender], "VIBGovernance: not a verifier");
        require(recordIds.length == approvedList.length && recordIds.length == adjustedPointsList.length,
            "VIBGovernance: length mismatch");

        for (uint256 i = 0; i < recordIds.length; i++) {
            _verifyContributionInternal(recordIds[i], approvedList[i], adjustedPointsList[i]);
        }
    }

    /**
     * @notice 内部验证贡献记录函数
     */
    function _verifyContributionInternal(
        uint256 recordId,
        bool approved,
        uint256 adjustedPoints
    ) internal {
        require(recordId < contributionRecords.length, "VIBGovernance: invalid record id");

        ContributionRecord storage record = contributionRecords[recordId];
        require(!record.verified, "VIBGovernance: already verified");

        record.verified = true;
        record.verifier = msg.sender;
        pendingContributionsCount--;

        if (approved) {
            uint256 finalPoints = adjustedPoints > 0 ? adjustedPoints : record.points;
            require(finalPoints <= MAX_SINGLE_CONTRIBUTION_POINTS, "VIBGovernance: points exceed max");

            // 检查月度积分限制
            uint256 currentMonth = block.timestamp / 30 days;
            uint256 monthlyEarned = monthlyPointsEarned[record.contributor][currentMonth];
            uint256 allowedPoints = finalPoints;

            if (monthlyEarned + finalPoints > MAX_MONTHLY_POINTS) {
                allowedPoints = MAX_MONTHLY_POINTS - monthlyEarned;
            }

            if (allowedPoints > 0) {
                uint256 oldPoints = contributionPoints[record.contributor];
                contributionPoints[record.contributor] += allowedPoints;
                monthlyPointsEarned[record.contributor][currentMonth] += allowedPoints;

                // 更新总贡献积分
                totalContributionPoints += allowedPoints;

                // GOV-03修复: 添加带时间戳的积分记录
                _addTimedPoints(record.contributor, allowedPoints);

                emit ContributionPointsUpdated(record.contributor, oldPoints, contributionPoints[record.contributor]);
            }
        }

        emit ContributionVerified(recordId, record.contributor, approved ? record.points : 0, msg.sender);
    }

    /**
     * @notice 获取贡献记录
     * @param recordId 贡献记录 ID
     * @return 贡献记录
     */
    function getContributionRecord(uint256 recordId) external view returns (ContributionRecord memory) {
        require(recordId < contributionRecords.length, "VIBGovernance: invalid record id");
        return contributionRecords[recordId];
    }

    /**
     * @notice 获取用户贡献记录数量
     * @param user 用户地址
     * @return 记录数量
     */
    function getUserContributionCount(address user) external view returns (uint256) {
        return userContributionIndices[user].length;
    }

    /**
     * @notice 获取用户贡献记录 ID 列表
     * @param user 用户地址
     * @param offset 偏移量
     * @param limit 数量限制
     * @return 记录 ID 列表
     */
    function getUserContributionIds(
        address user,
        uint256 offset,
        uint256 limit
    ) external view returns (uint256[] memory) {
        uint256[] storage indices = userContributionIndices[user];
        require(offset < indices.length, "VIBGovernance: offset out of bounds");

        uint256 end = offset + limit;
        if (end > indices.length) {
            end = indices.length;
        }

        uint256[] memory result = new uint256[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = indices[i];
        }

        return result;
    }

    // ========== 委托恢复机制 ==========

    /**
     * @notice 申请恢复委托（当受托人连续弃权时）
     * @dev 委托人可以在等待期后收回委托权
     */
    function requestDelegationRecovery() external whenNotPaused {
        address delegateAddr = delegates[msg.sender];
        require(delegateAddr != address(0), "VIBGovernance: not delegated");
        require(!pendingRecovery[msg.sender], "VIBGovernance: recovery already pending");
        require(consecutiveAbstentions[delegateAddr] >= MAX_CONSECUTIVE_ABSTENTIONS,
            "VIBGovernance: delegatee has not abstained enough");

        delegationRecoveryRequestTime[msg.sender] = block.timestamp;
        pendingRecovery[msg.sender] = true;

        emit DelegationRecoveryRequested(msg.sender, delegateAddr, block.timestamp);
    }

    /**
     * @notice 执行委托恢复
     * @dev 需要等待 7 天后才能执行
     */
    function executeDelegationRecovery() external nonReentrant whenNotPaused {
        require(pendingRecovery[msg.sender], "VIBGovernance: no pending recovery");
        require(
            block.timestamp >= delegationRecoveryRequestTime[msg.sender] + DELEGATION_RECOVERY_DELAY,
            "VIBGovernance: recovery delay not passed"
        );

        address delegateAddr = delegates[msg.sender];
        uint256 amount = delegatedOut[msg.sender];

        // 清除委托状态
        delegates[msg.sender] = address(0);
        delegatedVotes[delegateAddr] -= amount;
        delegatedOut[msg.sender] = 0;
        delegationStartTime[msg.sender] = 0;
        delegationExpiryTime[msg.sender] = 0;
        totalDelegatedVotes -= amount;
        pendingRecovery[msg.sender] = false;
        delegationRecoveryRequestTime[msg.sender] = 0;

        // 移除委托来源记录
        isDelegationSource[delegateAddr][msg.sender] = false;
        receivedDelegationCount[delegateAddr]--;

        // 重置受托人的连续弃权计数
        consecutiveAbstentions[delegateAddr] = 0;

        // 更新投票权区块
        votingPowerLastUpdateBlock[msg.sender] = block.number;
        votingPowerLastUpdateBlock[delegateAddr] = block.number;

        emit DelegationRecovered(msg.sender, delegateAddr, amount);
    }

    /**
     * @notice 记录受托人在提案中的投票情况
     * @dev 在 castVote 中调用，跟踪受托人是否投票
     * @param proposalId 提案 ID
     * @param delegatee 受托人地址
     */
    function _recordDelegateeVote(uint256 proposalId, address delegatee) internal {
        delegateeVotedInProposal[proposalId][delegatee] = true;

        // 重置连续弃权计数
        if (consecutiveAbstentions[delegatee] > 0) {
            consecutiveAbstentions[delegatee] = 0;
        }
    }

    /**
     * @notice 在提案结束时检查受托人是否弃权
     * @param proposalId 提案 ID
     * @param delegatee 受托人地址
     */
    function _checkDelegateeAbstention(uint256 proposalId, address delegatee) internal {
        if (!delegateeVotedInProposal[proposalId][delegatee]) {
            consecutiveAbstentions[delegatee]++;
            emit ConsecutiveAbstentionRecorded(delegatee, consecutiveAbstentions[delegatee]);
        }
    }

    /**
     * @notice 检查委托人是否有资格申请恢复
     * @param delegator 委托人地址
     * @return 是否有资格
     */
    function canRequestRecovery(address delegator) external view returns (bool) {
        address delegateAddr = delegates[delegator];
        if (delegateAddr == address(0)) return false;
        if (pendingRecovery[delegator]) return false;
        return consecutiveAbstentions[delegateAddr] >= MAX_CONSECUTIVE_ABSTENTIONS;
    }

    /**
     * @notice 检查恢复是否可以执行
     * @param delegator 委托人地址
     * @return 是否可以执行
     */
    function canExecuteRecovery(address delegator) external view returns (bool) {
        if (!pendingRecovery[delegator]) return false;
        return block.timestamp >= delegationRecoveryRequestTime[delegator] + DELEGATION_RECOVERY_DELAY;
    }

    /**
     * @notice 获取委托恢复状态
     * @param delegator 委托人地址
     * @return isPending 是否有待恢复
     * @return requestTime 申请时间
     * @return canExecute 是否可以执行
     * @return remainingTime 剩余等待时间
     */
    function getDelegationRecoveryStatus(address delegator) external view returns (
        bool isPending,
        uint256 requestTime,
        bool canExecute,
        uint256 remainingTime
    ) {
        isPending = pendingRecovery[delegator];
        requestTime = delegationRecoveryRequestTime[delegator];

        if (isPending) {
            uint256 executeTime = requestTime + DELEGATION_RECOVERY_DELAY;
            if (block.timestamp >= executeTime) {
                canExecute = true;
                remainingTime = 0;
            } else {
                canExecute = false;
                remainingTime = executeTime - block.timestamp;
            }
        } else {
            canExecute = false;
            remainingTime = 0;
        }
    }

    /**
     * @notice 暂停合约
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice 恢复合约
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 设置释放控制器地址
     * @param _emissionController 释放控制器地址
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        require(_emissionController != address(0), "VIBGovernance: invalid address");
        emit EmissionControllerUpdated(emissionController, _emissionController);
        emissionController = _emissionController;
    }

    /**
     * @notice 设置治理奖励参数
     * @param _voteReward 每票奖励
     * @param _proposalReward 每提案奖励
     */
    function setGovernanceRewardParams(uint256 _voteReward, uint256 _proposalReward) external onlyOwner {
        voteReward = _voteReward;
        proposalReward = _proposalReward;
        emit GovernanceRewardParamsUpdated(_voteReward, _proposalReward);
    }

    /**
     * @notice 接收来自释放控制器的奖励
     * @dev 只有释放控制器可以调用
     * @param amount 奖励数量
     */
    function receiveRewards(uint256 amount) external {
        require(
            msg.sender == emissionController || msg.sender == owner(),
            "VIBGovernance: not authorized"
        );
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        governanceRewardBalance += amount;
        emit GovernanceRewardsReceived(amount, msg.sender);
    }

    /**
     * @notice 领取治理奖励
     */
    function claimGovernanceReward() external nonReentrant whenNotPaused {
        uint256 reward = pendingGovernanceRewards[msg.sender];
        require(reward > 0, "VIBGovernance: no pending rewards");
        require(governanceRewardBalance >= reward, "VIBGovernance: insufficient balance");

        pendingGovernanceRewards[msg.sender] = 0;
        totalPendingRewards -= reward;
        governanceRewardBalance -= reward;
        claimedGovernanceRewards[msg.sender] += reward;

        vibeToken.safeTransfer(msg.sender, reward);

        emit GovernanceRewardClaimed(msg.sender, reward);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取用户投票权（包含委托）
     * @param user 用户地址
     * @return 总投票权
     */
    function getVotingPower(address user) public view returns (uint256) {
        // 如果用户已委托给别人，则没有直接投票权
        if (delegates[user] != address(0)) {
            return 0;
        }

        // 自身投票权
        uint256 ownPower = _getOwnVotingPower(user);

        // 加上收到的委托投票权
        uint256 delegatedPower = delegatedVotes[user];

        return ownPower + delegatedPower;
    }

    /**
     * @notice 获取用户自身投票权（不含委托）
     * @param user 用户地址
     * @return 自身投票权
     */
    function _getOwnVotingPower(address user) internal view returns (uint256) {
        // Layer 1: 资本权重
        uint256 capitalPower = _getCapitalWeight(user);

        // Layer 2: 生产权重
        uint256 productionPower = _getProductionWeight(user);

        // Layer 3: 社区共识
        uint256 communityPower = _getCommunityWeight(user);

        // GOV-01修复: 使用实际总投票权计算上限，而非代币总供应量
        uint256 totalVotingPower = _getTotalVotingPower();

        // 只有当总投票权足够大时才应用上限（避免小规模治理场景下的过度限制）
        // 最小总投票权阈值：10000 VIBE
        uint256 MIN_TOTAL_FOR_CAPS = 10000 * 10**18;

        if (totalVotingPower >= MIN_TOTAL_FOR_CAPS) {
            // 资本权重上限：最多占总投票权的 10%
            uint256 capitalCap = (totalVotingPower * CAPITAL_WEIGHT_MAX) / 100;
            if (capitalPower > capitalCap) {
                capitalPower = capitalCap;
            }

            // 生产权重上限：最多占总投票权的 15%
            uint256 productionCap = (totalVotingPower * PRODUCTION_WEIGHT_MAX) / 100;
            if (productionPower > productionCap) {
                productionPower = productionCap;
            }
        }

        return capitalPower + productionPower + communityPower;
    }

    /**
     * @notice GOV-04修复: 获取实际总投票权
     * @return 总投票权 = 质押总额 + 估计生产权重 + 社区权重
     * @dev 使用缓存机制避免每次调用都重新计算
     */
    function _getTotalVotingPower() internal view returns (uint256) {
        // 如果有缓存的值且未过期（1小时内），使用缓存
        if (cachedTotalVotingPower > 0 &&
            block.timestamp < totalVotingPowerCacheTime + 1 hours) {
            return cachedTotalVotingPower;
        }

        // 基础: 质押总额（资本权重）
        uint256 basePower = _getTotalStakedAmount();

        // 估计生产权重：使用总贡献积分
        uint256 estimatedProduction = (totalContributionPoints * PRODUCTION_WEIGHT_RATIO) / 100;

        // 社区权重固定为基础+生产的10%
        uint256 communityWeight = ((basePower + estimatedProduction) * 10) / 100;

        return basePower + estimatedProduction + communityWeight;
    }

    /// @notice 缓存的总投票权
    uint256 public cachedTotalVotingPower;

    /// @notice 缓存时间
    uint256 public totalVotingPowerCacheTime;

    /// @notice 总贡献积分
    uint256 public totalContributionPoints;

    /**
     * @notice 更新总投票权缓存
     */
    function updateTotalVotingPowerCache() external {
        uint256 basePower = _getTotalStakedAmount();
        uint256 estimatedProduction = (totalContributionPoints * PRODUCTION_WEIGHT_RATIO) / 100;
        uint256 communityWeight = ((basePower + estimatedProduction) * 10) / 100;

        cachedTotalVotingPower = basePower + estimatedProduction + communityWeight;
        totalVotingPowerCacheTime = block.timestamp;
    }

    /**
     * @notice 获取总质押金额
     */
    function _getTotalStakedAmount() internal view returns (uint256) {
        if (address(vibStaking) != address(0)) {
            try vibStaking.totalStaked() returns (uint256 total) {
                return total;
            } catch {}
        }
        // Fallback: 使用代币总供应量的80%作为估计
        return (vibeToken.totalSupply() * 80) / 100;
    }

    /**
     * @notice 获取资本权重（深度集成 VIBStaking）
     * @param user 用户地址
     * @return 资本权重
     * @dev 资本权重 = 质押量 × 时长系数（来自 VIBStaking 合约）
     */
    function _getCapitalWeight(address user) internal view returns (uint256) {
        // 如果已设置 VIBStaking 合约，使用真实的质押信息
        if (address(vibStaking) != address(0)) {
            try vibStaking.getVotingPower(user) returns (uint256 votingPower) {
                if (votingPower > 0) {
                    return votingPower;
                }
            } catch {
                // 如果调用失败，继续使用 fallback 逻辑
            }
        }

        // Fallback: 使用简单的代币余额检查
        uint256 balance = vibeToken.balanceOf(user);
        if (balance < MIN_STAKE_REQUIREMENT) return 0;

        // 简化处理：没有质押合约时使用基础 1x 系数
        return balance;
    }

    /**
     * @notice 获取生产权重（基于贡献积分）
     * @param user 用户地址
     * @return 生产权重
     * @dev GOV-03修复: 使用90天滚动窗口计算有效积分
     *      生产权重 = 有效积分 × 转换比例
     *      有效积分 = 过去90天内的积分总和（按时间线性衰减）
     */
    function _getProductionWeight(address user) internal view returns (uint256) {
        uint256 effectivePoints = _getEffectiveContributionPoints(user);
        // 贡献积分转换为投票权：1 积分 = 0.01 投票权
        return (effectivePoints * PRODUCTION_WEIGHT_RATIO) / 100;
    }

    /**
     * @notice 获取用户有效贡献积分（90天滚动窗口）
     * @param user 用户地址
     * @return 有效积分
     * @dev GOV-03修复: 只计算90天内的积分，超过90天的积分按线性衰减
     */
    function _getEffectiveContributionPoints(address user) internal view returns (uint256) {
        TimedPoints[] storage history = userPointsHistory[user];
        uint256 effectivePoints = 0;
        uint256 currentTime = block.timestamp;
        uint256 windowStart = currentTime > PRODUCTION_WINDOW ? currentTime - PRODUCTION_WINDOW : 0;

        for (uint256 i = 0; i < history.length; i++) {
            TimedPoints storage entry = history[i];
            if (entry.timestamp >= windowStart) {
                // 在窗口期内，全额计入
                effectivePoints += entry.points;
            } else if (entry.timestamp > 0) {
                // 超出窗口期但未清理，按距离窗口的时间线性衰减
                uint256 age = windowStart - entry.timestamp;
                // 衰减率 = age / PRODUCTION_WINDOW，最大100%
                if (age < PRODUCTION_WINDOW * 2) {
                    uint256 decayRate = (age * 100) / (PRODUCTION_WINDOW * 2);
                    uint256 remainingPoints = (entry.points * (100 - decayRate)) / 100;
                    effectivePoints += remainingPoints;
                }
                // 超过180天的完全衰减，不计入
            }
        }

        return effectivePoints;
    }

    /**
     * @notice 清理用户过期的积分记录（节省存储）
     * @param user 用户地址
     * @dev GOV-03修复: 删除超过180天的记录
     */
    function cleanupExpiredPoints(address user) external {
        TimedPoints[] storage history = userPointsHistory[user];
        uint256 currentTime = block.timestamp;
        uint256 cutoffTime = currentTime > (PRODUCTION_WINDOW * 2) ? currentTime - (PRODUCTION_WINDOW * 2) : 0;

        // 从后向前遍历，删除过期记录
        uint256 writeIndex = 0;
        for (uint256 i = 0; i < history.length; i++) {
            if (history[i].timestamp >= cutoffTime) {
                if (writeIndex != i) {
                    history[writeIndex] = history[i];
                }
                writeIndex++;
            }
        }

        // 删除多余的元素
        while (history.length > writeIndex) {
            history.pop();
        }

        lastCleanupTime[user] = currentTime;
    }

    /**
     * @notice 添加带时间戳的积分记录
     * @param user 用户地址
     * @param points 积分数量
     * @dev GOV-03修复: 内部函数，由贡献积分系统调用
     */
    function _addTimedPoints(address user, uint256 points) internal {
        userPointsHistory[user].push(TimedPoints({
            points: points,
            timestamp: block.timestamp
        }));
    }

    /**
     * @notice 获取用户有效贡献积分（外部视图）
     * @param user 用户地址
     * @return 有效积分
     */
    function getEffectiveContributionPoints(address user) external view returns (uint256) {
        return _getEffectiveContributionPoints(user);
    }

    /**
     * @notice 获取社区共识权重
     * @param user 用户地址
     * @return 社区共识权重
     * @dev GOV-02修复: 社区权重 = 总投票权的10% / KYC用户数，使用实际总投票权
     */
    function _getCommunityWeight(address user) internal view returns (uint256) {
        if (!kycVerified[user]) return 0;
        if (kycUserCount == 0) return 0;

        // GOV-02修复: 使用实际总投票权
        uint256 totalVotingPower = _getTotalVotingPower();
        uint256 totalCommunityWeight = (totalVotingPower * 10) / 100;

        // 每个KYC用户获得均等的权重
        return totalCommunityWeight / kycUserCount;
    }

    /**
     * @notice 从字节数组中提取函数选择器
     * @param data 字节数组
     * @return 函数选择器 (bytes4)
     */
    function _extractFunctionSelector(bytes memory data) internal pure returns (bytes4) {
        require(data.length >= 4, "VIBGovernance: data too short");
        return bytes4(data[0]) | (bytes4(data[1]) >> 8) | (bytes4(data[2]) >> 16) | (bytes4(data[3]) >> 24);
    }

    /**
     * @notice 获取提案门槛
     * @param proposalType 提案类型
     * @return 门槛金额
     */
    function _getThreshold(ProposalType proposalType) internal view returns (uint256) {
        if (proposalType == ProposalType.GENERAL) {
            return generalProposalThreshold;
        } else if (proposalType == ProposalType.PARAMETER) {
            return parameterProposalThreshold;
        } else if (proposalType == ProposalType.UPGRADE) {
            return upgradeProposalThreshold;
        }
        return emergencyProposalThreshold; // 紧急提案有门槛 - 安全增强
    }

    /**
     * @notice 获取投票时长
     * @param proposalType 提案类型
     * @return 时长（秒）
     */
    function _getDuration(ProposalType proposalType) internal pure returns (uint256) {
        if (proposalType == ProposalType.GENERAL) {
            return 7 days;
        } else if (proposalType == ProposalType.PARAMETER) {
            return 14 days;
        } else if (proposalType == ProposalType.UPGRADE) {
            return 21 days;
        }
        return 3 days; // 紧急提案
    }

    /**
     * @notice 获取时间锁时长
     * @param proposalType 提案类型
     * @return 时长（秒）
     */
    function _getTimelock(ProposalType proposalType) internal view returns (uint256) {
        if (proposalType == ProposalType.GENERAL) {
            return generalTimelock;
        } else if (proposalType == ProposalType.PARAMETER) {
            return parameterTimelock;
        } else if (proposalType == ProposalType.UPGRADE) {
            return upgradeTimelock;
        }
        return EMERGENCY_TIMELOCK; // 紧急提案有1天时间锁 - 安全增强
    }

    /**
     * @notice 检查提案是否通过
     * @param proposalId 提案 ID
     * @return 是否通过
     */
    function checkProposalPassed(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (bool)
    {
        Proposal storage proposal = proposals[proposalId];

        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        require(totalVotes > 0, "VIBGovernance: no votes");

        uint256 passRate = (proposal.forVotes * 10000) / totalVotes;
        uint256 requiredRate = _getRequiredPassRate(proposal.proposalType);

        return passRate >= requiredRate;
    }

    /**
     * @notice 获取需要的通过率
     * @param proposalType 提案类型
     * @return 通过率 (x10000)
     */
    function _getRequiredPassRate(ProposalType proposalType) internal pure returns (uint256) {
        if (proposalType == ProposalType.GENERAL) {
            return GENERAL_PASS_RATE;
        } else if (proposalType == ProposalType.PARAMETER) {
            return PARAMETER_PASS_RATE;
        } else if (proposalType == ProposalType.UPGRADE) {
            return UPGRADE_PASS_RATE;
        }
        return EMERGENCY_PASS_RATE;
    }

    /**
     * @notice 获取提案数量
     * @return 提案数量
     */
    function getProposalCount() external view returns (uint256) {
        return proposals.length;
    }

    /**
     * @notice 获取提案详情
     * @param proposalId 提案 ID
     * @return 提案详情
     */
    function getProposal(uint256 proposalId)
        external
        view
        proposalExists(proposalId)
        returns (Proposal memory)
    {
        return proposals[proposalId];
    }

    /**
     * @notice 获取用户投票信息
     * @param proposalId 提案 ID
     * @param user 用户地址
     * @return 投票信息
     */
    function getVote(uint256 proposalId, address user)
        external
        view
        returns (Vote memory)
    {
        return votes[proposalId][user];
    }

    // ========== 委托视图函数 ==========

    /**
     * @notice 获取用户委托信息
     * @param user 用户地址
     * @return delegateAddr 委托目标
     * @return delegatedOutAmount 委托出去的票数
     * @return delegatedInAmount 收到的委托票数
     * @return expiryTime 委托到期时间
     */
    function getDelegationInfo(address user)
        external
        view
        returns (
            address delegateAddr,
            uint256 delegatedOutAmount,
            uint256 delegatedInAmount,
            uint256 expiryTime
        )
    {
        delegateAddr = delegates[user];
        delegatedOutAmount = delegatedOut[user];
        delegatedInAmount = delegatedVotes[user];
        expiryTime = delegationExpiryTime[user];
    }

    /**
     * @notice 获取用户收到的委托来源列表
     * @param user 用户地址
     * @return 委托来源地址列表
     */
    function getDelegationSources(address user) external view returns (address[] memory) {
        return delegationSources[user];
    }

    /**
     * @notice 获取用户自身投票权（不含委托）
     * @param user 用户地址
     * @return 自身投票权
     */
    function getOwnVotingPower(address user) external view returns (uint256) {
        return _getOwnVotingPower(user);
    }

    /**
     * @notice 获取用户有效投票权（包含委托，用于投票）
     * @param user 用户地址
     * @return 有效投票权
     */
    function getEffectiveVotingPower(address user) external view returns (uint256) {
        return getVotingPower(user);
    }

    /**
     * @notice 检查委托是否有效
     * @param user 用户地址
     * @return 是否有效
     */
    function isDelegationValid(address user) external view returns (bool) {
        if (delegates[user] == address(0)) return false;
        return block.timestamp < delegationExpiryTime[user];
    }

    /**
     * @notice 获取剩余委托时间
     * @param user 用户地址
     * @return 剩余时间（秒），0表示未委托或已过期
     */
    function getRemainingDelegationTime(address user) external view returns (uint256) {
        if (delegates[user] == address(0)) return 0;
        if (block.timestamp >= delegationExpiryTime[user]) return 0;
        return delegationExpiryTime[user] - block.timestamp;
    }

    /**
     * @notice 获取总委托投票权
     * @return 总委托投票权
     */
    function getTotalDelegatedVotes() external view returns (uint256) {
        return totalDelegatedVotes;
    }

    /**
     * @notice 检查是否可以委托给目标地址
     * @param delegateAddr 目标地址
     * @param amount 委托数量
     * @return 是否可以委托
     */
    function canDelegate(address delegateAddr, uint256 amount) external view returns (bool) {
        if (delegateAddr == address(0)) return false;
        if (delegates[delegateAddr] != address(0)) return false; // 目标已委托给别人

        uint256 newDelegatedVotes = delegatedVotes[delegateAddr] + amount;
        uint256 totalVotes = _getTotalVotingPower();
        uint256 maxAllowed = (totalVotes * MAX_DELEGATION_ACCEPT_RATIO) / 10000;

        if (totalVotes == 0) {
            maxAllowed = amount; // 允许第一笔委托
        }

        return newDelegatedVotes <= maxAllowed;
    }

    /**
     * @notice 获取用户待领取的治理奖励
     * @param user 用户地址
     * @return 待领取奖励数量
     */
    function getPendingGovernanceReward(address user) external view returns (uint256) {
        return pendingGovernanceRewards[user];
    }

    /**
     * @notice 获取用户已领取的治理奖励
     * @param user 用户地址
     * @return 已领取奖励数量
     */
    function getClaimedGovernanceReward(address user) external view returns (uint256) {
        return claimedGovernanceRewards[user];
    }

    /**
     * @notice 获取治理奖励统计
     * @return balance 当前余额
     * @return pending 总待领取
     * @return available 可用余额（当前余额 - 待领取）
     */
    function getGovernanceRewardStats() external view returns (
        uint256 balance,
        uint256 pending,
        uint256 available
    ) {
        balance = governanceRewardBalance;
        pending = totalPendingRewards;
        available = governanceRewardBalance >= totalPendingRewards
            ? governanceRewardBalance - totalPendingRewards
            : 0;
    }
}


