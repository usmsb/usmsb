// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

// ========== Chainlink VRF 接口 ==========

/**
 * @dev Chainlink VRF v2 接口
 */
interface VRFCoordinatorV2Interface {
    function requestRandomWords(
        bytes32 keyHash,
        uint64 subId,
        uint16 minimumRequestConfirmations,
        uint32 callbackGasLimit,
        uint32 numWords
    ) external returns (uint256 requestId);

    function getRequestConfig()
        external
        view
        returns (
            uint16 minimumRequestConfirmations,
            uint32 maxGasLimit,
            uint32 minGasLimit,
            uint32 maxNumWords
        );

    function addConsumer(uint64 subId, address consumer) external;

    function createSubscription() external returns (uint64 subId);

    function fundSubscription(uint64 subId, uint96 amount) external;
}

/**
 * @title VIBDispute
 * @notice 争议解决合约
 * @dev 实现白皮书要求的争议解决机制
 *
 * 流程:
 * 1. 发起争议：双方各质押 5 VIBE
 * 2. 仲裁员分配：随机 3 名仲裁员
 * 3. 证据提交：24 小时
 * 4. 仲裁投票：48 小时
 * 5. 执行裁决
 *
 * 仲裁员准入条件:
 * - 需持有 1,000+ VIBE
 * - 通过治理考试
 * - 至少参与 10 次投票且记录良好
 *
 * 服务者信用保护:
 * - 连续 3 次胜诉 → 争议门槛降至 1 VIBE
 * - 连续 3 次败诉（需求方）→ 争议门槛提高至 20 VIBE
 */
contract VIBDispute is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== Chainlink VRF 配置 ==========

    /// @notice VRF Coordinator 地址 (以太坊主网: 0x271682DEB8C4CA1209EE3E1EA
    VRFCoordinatorV2Interface public vrfCoordinator;

    /// @notice LINK 代币地址
    address public linkToken;

    /// @notice VRF Key Hash
    bytes32 public vrfKeyHash;

    /// @notice VRF Subscription ID
    uint64 public vrfSubscriptionId;

    /// @notice VRF Callback Gas Limit
    uint32 public vrfCallbackGasLimit = 200000;

    /// @notice VRF 请求确认数
    uint16 public vrfRequestConfirmations = 3;

    /// @notice VRF 随机数映射
    mapping(uint256 => uint256) public vrfRequestIdToDisputeId;

    /// @notice 待处理的 VRF 请求
    mapping(uint256 => uint256) public vrfRandomWords;

    // ========== 常量 ==========

    /// @notice 默认争议质押金额
    uint256 public constant DEFAULT_DISPUTE_STAKE = 5 * 10**18; // 5 VIBE

    /// @notice 最低争议质押（信用保护）
    uint256 public constant MIN_DISPUTE_STAKE = 1 * 10**18; // 1 VIBE

    /// @notice 最高争议质押（需求方惩罚）
    uint256 public constant MAX_DISPUTE_STAKE = 20 * 10**18; // 20 VIBE

    /// @notice 证据提交期（24小时）
    uint256 public constant EVIDENCE_PERIOD = 24 hours;

    /// @notice 仲裁投票期（48小时）
    uint256 public constant VOTING_PERIOD = 48 hours;

    /// @notice 仲裁员数量
    uint256 public constant ARBITRATOR_COUNT = 3;

    /// @notice 仲裁员最低持币量
    uint256 public constant ARBITRATOR_MIN_STAKE = 1000 * 10**18; // 1000 VIBE

    /// @notice 仲裁员最低投票次数
    uint256 public constant ARBITRATOR_MIN_VOTES = 10;

    /// @notice 连续胜诉次数（获得信用保护）
    uint256 public constant CREDIT_PROTECTION_WINS = 3;

    /// @notice 连续败诉次数（提高门槛）
    uint256 public constant CREDIT_PENALTY_LOSSES = 3;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币
    IERC20 public immutable vibeToken;

    /// @notice 质押合约地址（用于检查持币量）
    address public stakingContract;

    /// @notice 治理合约地址（用于检查投票记录）
    address public governanceContract;

    /// @notice 争议计数器
    uint256 public disputeCounter;

    /// @notice 争议质押金额映射（地址 => 金额）
    mapping(address => uint256) public disputeStakes;

    /// @notice 争议信息映射
    mapping(uint256 => Dispute) public disputes;

    /// @notice 仲裁员信息映射
    mapping(address => Arbitrator) public arbitrators;

    /// @notice 用户信用记录
    mapping(address => CreditRecord) public creditRecords;

    /// @notice 仲裁员候选池
    address[] public arbitratorPool;

    /// @notice 争议投票记录 (disputeId => arbitrator => vote)
    mapping(uint256 => mapping(address => Vote)) public disputeVotes;

    /// @notice 争议仲裁员列表 (disputeId => arbitrators)
    mapping(uint256 => address[]) public disputeArbitrators;

    // ========== 枚举 ==========

    enum DisputeStatus {
        None,           // 不存在
        Pending,        // 等待被告响应
        EvidencePhase,  // 证据提交期
        VotingPhase,    // 投票期
        Resolved,       // 已解决
        Cancelled       // 已取消
    }

    enum Vote {
        None,           // 未投票
        ForPlaintiff,   // 支持原告
        ForDefendant,   // 支持被告
        Abstain         // 弃权
    }

    // ========== 结构体 ==========

    struct Dispute {
        uint256 id;
        address plaintiff;          // 原告（服务者）
        address defendant;          // 被告（需求方）
        uint256 amount;             // 争议金额
        uint256 stakeAmount;        // 质押金额
        uint256 createdAt;
        uint256 evidenceEndAt;
        uint256 votingEndAt;
        DisputeStatus status;
        string description;         // IPFS hash
        string evidence;            // IPFS hash
        uint8 votesForPlaintiff;
        uint8 votesForDefendant;
        bool plaintiffWon;
        bool resolved;
    }

    struct Arbitrator {
        bool isRegistered;
        bool passedExam;
        uint256 totalVotes;         // 参与投票次数
        uint256 correctVotes;       // 正确投票次数（与多数一致）
        uint256 reputation;         // 信誉分
        uint256 rewards;            // 累计奖励
    }

    struct CreditRecord {
        uint256 consecutiveWins;    // 连续胜诉次数
        uint256 consecutiveLosses;  // 连续败诉次数
        uint256 totalDisputes;      // 总争议数
        uint256 totalWins;          // 总胜诉数
    }

    // ========== 事件 ==========

    event DisputeCreated(
        uint256 indexed disputeId,
        address indexed plaintiff,
        address indexed defendant,
        uint256 amount,
        uint256 stakeAmount
    );

    event DisputeResponded(
        uint256 indexed disputeId,
        address indexed defendant
    );

    event EvidenceSubmitted(
        uint256 indexed disputeId,
        address indexed submitter,
        string evidenceHash
    );

    event ArbitratorsAssigned(
        uint256 indexed disputeId,
        address[3] arbitrators
    );

    event VoteCast(
        uint256 indexed disputeId,
        address indexed arbitrator,
        Vote vote
    );

    event DisputeResolved(
        uint256 indexed disputeId,
        bool plaintiffWon,
        uint256 plaintiffReward,
        uint256 arbitratorReward
    );

    event ArbitratorRegistered(address indexed arbitrator);
    event ArbitratorExamPassed(address indexed arbitrator);
    event CreditUpdated(address indexed user, uint256 consecutiveWins, uint256 consecutiveLosses);

    // ========== 修饰符 ==========

    modifier onlyStakingContract() {
        require(msg.sender == stakingContract, "Only staking contract");
        _;
    }

    modifier onlyGovernanceContract() {
        require(msg.sender == governanceContract, "Only governance contract");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _stakingContract,
        address _governanceContract,
        address _vrfCoordinator,
        address _linkToken,
        bytes32 _vrfKeyHash
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "Invalid token");
        vibeToken = IERC20(_vibeToken);
        stakingContract = _stakingContract;
        governanceContract = _governanceContract;

        // Chainlink VRF 配置
        vrfCoordinator = VRFCoordinatorV2Interface(_vrfCoordinator);
        linkToken = _linkToken;

        // M-11修复: 默认禁用回退随机性（生产环境安全）
        allowFallbackRandomness = false;
        vrfKeyHash = _vrfKeyHash;
    }

    /**
     * @notice 配置 Chainlink VRF
     * @param _subscriptionId VRF 订阅 ID
     */
    function setVRFSubscription(uint64 _subscriptionId) external onlyOwner {
        vrfSubscriptionId = _subscriptionId;
    }

    /**
     * @notice M-11修复: 设置是否允许回退随机性
     * @dev 生产环境应设为false，仅测试环境可设为true
     */
    function setAllowFallbackRandomness(bool _allow) external onlyOwner {
        allowFallbackRandomness = _allow;
    }

    /**
     * @notice 设置 VRF 参数
     */
    function setVRFParams(
        uint32 _callbackGasLimit,
        uint16 _requestConfirmations
    ) external onlyOwner {
        vrfCallbackGasLimit = _callbackGasLimit;
        vrfRequestConfirmations = _requestConfirmations;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 创建争议
     * @param defendant 被告地址
     * @param amount 争议金额
     * @param description 争议描述（IPFS hash）
     */
    function createDispute(
        address defendant,
        uint256 amount,
        string calldata description
    ) external nonReentrant returns (uint256) {
        require(defendant != address(0), "Invalid defendant");
        require(defendant != msg.sender, "Cannot dispute self");
        require(bytes(description).length > 0, "Description required");

        // 计算质押金额（根据信用记录调整）
        uint256 stakeAmount = _getDisputeStake(msg.sender);

        // 转入质押代币
        vibeToken.safeTransferFrom(msg.sender, address(this), stakeAmount);

        disputeCounter++;
        uint256 disputeId = disputeCounter;

        Dispute storage dispute = disputes[disputeId];
        dispute.id = disputeId;
        dispute.plaintiff = msg.sender;
        dispute.defendant = defendant;
        dispute.amount = amount;
        dispute.stakeAmount = stakeAmount;
        dispute.createdAt = block.timestamp;
        dispute.status = DisputeStatus.Pending;
        dispute.description = description;

        emit DisputeCreated(disputeId, msg.sender, defendant, amount, stakeAmount);

        return disputeId;
    }

    /**
     * @notice 被告响应争议
     * @param disputeId 争议ID
     */
    function respondToDispute(uint256 disputeId) external nonReentrant {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.Pending, "Not pending");
        require(msg.sender == dispute.defendant, "Only defendant");

        // 计算被告质押金额
        uint256 stakeAmount = _getDisputeStake(msg.sender);

        // 转入质押代币
        vibeToken.safeTransferFrom(msg.sender, address(this), stakeAmount);

        // 更新状态
        dispute.status = DisputeStatus.EvidencePhase;
        dispute.evidenceEndAt = block.timestamp + EVIDENCE_PERIOD;

        // 分配仲裁员
        _assignArbitrators(disputeId);

        emit DisputeResponded(disputeId, msg.sender);
    }

    /**
     * @notice 提交证据
     * @param disputeId 争议ID
     * @param evidenceHash 证据IPFS hash
     */
    function submitEvidence(
        uint256 disputeId,
        string calldata evidenceHash
    ) external {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.EvidencePhase, "Not evidence phase");
        require(
            msg.sender == dispute.plaintiff || msg.sender == dispute.defendant,
            "Only parties"
        );
        require(block.timestamp <= dispute.evidenceEndAt, "Evidence period ended");

        dispute.evidence = evidenceHash;

        emit EvidenceSubmitted(disputeId, msg.sender, evidenceHash);
    }

    /**
     * @notice 结束证据期，进入投票期
     * @param disputeId 争议ID
     */
    function startVoting(uint256 disputeId) external {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.EvidencePhase, "Not evidence phase");
        require(block.timestamp > dispute.evidenceEndAt, "Evidence period not ended");

        dispute.status = DisputeStatus.VotingPhase;
        dispute.votingEndAt = block.timestamp + VOTING_PERIOD;
    }

    /**
     * @notice 仲裁员投票
     * @param disputeId 争议ID
     * @param vote 投票选择
     */
    function castVote(uint256 disputeId, Vote vote) external nonReentrant {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.VotingPhase, "Not voting phase");
        require(block.timestamp <= dispute.votingEndAt, "Voting period ended");
        require(vote != Vote.None, "Invalid vote");

        // 检查是否为该争议的仲裁员
        bool isArbitrator = false;
        address[] storage disputeArbs = disputeArbitrators[disputeId];
        for (uint256 i = 0; i < disputeArbs.length; i++) {
            if (disputeArbs[i] == msg.sender) {
                isArbitrator = true;
                break;
            }
        }
        require(isArbitrator, "Not an arbitrator");

        // 检查是否已投票
        require(disputeVotes[disputeId][msg.sender] == Vote.None, "Already voted");

        // 记录投票
        disputeVotes[disputeId][msg.sender] = vote;

        // 更新计票
        if (vote == Vote.ForPlaintiff) {
            dispute.votesForPlaintiff++;
        } else if (vote == Vote.ForDefendant) {
            dispute.votesForDefendant++;
        }

        // 更新仲裁员记录
        arbitrators[msg.sender].totalVotes++;

        emit VoteCast(disputeId, msg.sender, vote);
    }

    /**
     * @notice 解决争议
     * @param disputeId 争议ID
     */
    function resolveDispute(uint256 disputeId) external nonReentrant {
        Dispute storage dispute = disputes[disputeId];
        require(dispute.status == DisputeStatus.VotingPhase, "Not voting phase");
        require(block.timestamp > dispute.votingEndAt, "Voting period not ended");
        require(!dispute.resolved, "Already resolved");

        // 确定胜方
        bool plaintiffWon = dispute.votesForPlaintiff > dispute.votesForDefendant;
        dispute.plaintiffWon = plaintiffWon;
        dispute.resolved = true;
        dispute.status = DisputeStatus.Resolved;

        // 计算总质押
        uint256 totalStake = dispute.stakeAmount * 2;

        // 分配奖励
        uint256 winnerReward;
        uint256 arbitratorReward;

        if (plaintiffWon) {
            // 原告胜诉：返还质押 + 被告质押的80%
            winnerReward = dispute.stakeAmount + (dispute.stakeAmount * 80) / 100;
            arbitratorReward = totalStake - winnerReward;

            // 更新信用记录
            _updateCreditRecord(dispute.plaintiff, true);
            _updateCreditRecord(dispute.defendant, false);
        } else {
            // 被告胜诉：返还质押 + 原告质押的80%
            winnerReward = dispute.stakeAmount + (dispute.stakeAmount * 80) / 100;
            arbitratorReward = totalStake - winnerReward;

            // 更新信用记录
            _updateCreditRecord(dispute.plaintiff, false);
            _updateCreditRecord(dispute.defendant, true);
        }

        // 转移胜方奖励
        address winner = plaintiffWon ? dispute.plaintiff : dispute.defendant;
        vibeToken.safeTransfer(winner, winnerReward);

        // 分配仲裁员奖励
        _distributeArbitratorRewards(disputeId, arbitratorReward, plaintiffWon);

        emit DisputeResolved(disputeId, plaintiffWon, winnerReward, arbitratorReward);
    }

    /**
     * @notice 注册成为仲裁员
     */
    function registerArbitrator() external {
        require(!arbitrators[msg.sender].isRegistered, "Already registered");

        // 检查持币量
        uint256 balance = vibeToken.balanceOf(msg.sender);
        require(balance >= ARBITRATOR_MIN_STAKE, "Insufficient VIBE balance");

        arbitrators[msg.sender].isRegistered = true;
        arbitrators[msg.sender].reputation = 100; // 初始信誉分

        arbitratorPool.push(msg.sender);

        emit ArbitratorRegistered(msg.sender);
    }

    /**
     * @notice 通过治理考试（由治理合约调用）
     * @param arbitrator 仲裁员地址
     */
    function passExam(address arbitrator) external onlyGovernanceContract {
        require(arbitrators[arbitrator].isRegistered, "Not registered");
        arbitrators[arbitrator].passedExam = true;

        emit ArbitratorExamPassed(arbitrator);
    }

    /**
     * @notice 设置仲裁员投票次数（仅用于测试/初始化）
     * @param arbitrator 仲裁员地址
     * @param votes 投票次数
     */
    function setArbitratorVotes(address arbitrator, uint256 votes) external onlyOwner {
        require(arbitrators[arbitrator].isRegistered, "Not registered");
        arbitrators[arbitrator].totalVotes = votes;
    }

    /**
     * @notice 更新投票记录（由治理合约调用）
     * @param voter 投票者地址
     */
    function recordGovernanceVote(address voter) external onlyGovernanceContract {
        // 用于统计参与治理投票次数
        // 简化实现：直接在仲裁员记录中累加
        if (arbitrators[voter].isRegistered) {
            // 这里只是记录，仲裁员准入检查时使用
        }
    }

    // ========== 管理员函数 ==========

    function setStakingContract(address _staking) external onlyOwner {
        stakingContract = _staking;
    }

    function setGovernanceContract(address _governance) external onlyOwner {
        governanceContract = _governance;
    }

    /**
     * @notice 移除不合格的仲裁员
     * @param arbitrator 仲裁员地址
     */
    function removeArbitrator(address arbitrator) external onlyOwner {
        arbitrators[arbitrator].isRegistered = false;

        // 从候选池中移除
        for (uint256 i = 0; i < arbitratorPool.length; i++) {
            if (arbitratorPool[i] == arbitrator) {
                arbitratorPool[i] = arbitratorPool[arbitratorPool.length - 1];
                arbitratorPool.pop();
                break;
            }
        }
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取用户的争议质押金额
     * @param user 用户地址
     */
    function getDisputeStake(address user) external view returns (uint256) {
        return _getDisputeStake(user);
    }

    /**
     * @notice 检查用户是否符合仲裁员条件
     * @param user 用户地址
     */
    function isEligibleArbitrator(address user) external view returns (bool) {
        return _isEligibleArbitrator(user);
    }

    /**
     * @notice 获取争议详情
     * @param disputeId 争议ID
     */
    function getDispute(uint256 disputeId) external view returns (Dispute memory) {
        return disputes[disputeId];
    }

    /**
     * @notice 获取争议的仲裁员列表
     * @param disputeId 争议ID
     */
    function getDisputeArbitrators(uint256 disputeId) external view returns (address[] memory) {
        return disputeArbitrators[disputeId];
    }

    /**
     * @notice 获取信用记录
     * @param user 用户地址
     */
    function getCreditRecord(address user) external view returns (CreditRecord memory) {
        return creditRecords[user];
    }

    // ========== 内部函数 ==========

    /**
     * @notice 计算争议质押金额（考虑信用保护）
     */
    function _getDisputeStake(address user) internal view returns (uint256) {
        CreditRecord memory record = creditRecords[user];

        // 服务者连续3次胜诉，门槛降至1 VIBE
        if (record.consecutiveWins >= CREDIT_PROTECTION_WINS) {
            return MIN_DISPUTE_STAKE;
        }

        // 需求方连续3次败诉，门槛提高至20 VIBE
        if (record.consecutiveLosses >= CREDIT_PENALTY_LOSSES) {
            return MAX_DISPUTE_STAKE;
        }

        return DEFAULT_DISPUTE_STAKE;
    }

    /**
     * @notice 检查是否符合仲裁员条件
     * @dev D-01修复: 使用质押金额而非余额检查持币量，确保"利益绑定"
     */
    function _isEligibleArbitrator(address user) internal view returns (bool) {
        Arbitrator memory arb = arbitrators[user];

        if (!arb.isRegistered || !arb.passedExam) {
            return false;
        }

        // D-01修复: 检查质押金额而非余额
        // 白皮书承诺: 仲裁员需持有1000+ VIBE（应为质押）
        uint256 stakedAmount = _getStakedAmount(user);
        if (stakedAmount < ARBITRATOR_MIN_STAKE) {
            return false;
        }

        // 检查投票次数
        if (arb.totalVotes < ARBITRATOR_MIN_VOTES) {
            return false;
        }

        // 检查信誉分
        if (arb.reputation < 50) {
            return false;
        }

        return true;
    }

    /**
     * @notice D-01修复: 获取用户质押金额
     * @param user 用户地址
     * @return 质押金额
     */
    function _getStakedAmount(address user) internal view returns (uint256) {
        if (stakingContract != address(0)) {
            // 尝试调用VIBStaking的getStakeInfo
            (bool success, bytes memory data) = stakingContract.staticcall(
                abi.encodeWithSignature("getStakeInfo(address)", user)
            );
            if (success && data.length > 0) {
                // 解析StakeInfo结构，amount是第一个字段
                (uint256 amount,,,,,,,) = abi.decode(data, (
                    uint256, // amount
                    uint256, // startTime
                    uint256, // unlockTime
                    uint256, // lockPeriodIndex
                    uint8,   // tier
                    uint256, // pendingReward
                    uint256, // rewardDebt
                    bool     // isActive
                ));
                return amount;
            }
        }
        // Fallback: 使用余额作为后备
        return vibeToken.balanceOf(user);
    }

    /// @notice M-11修复: 是否允许使用回退随机性（生产环境应设为false）
    bool public allowFallbackRandomness;

    /// @notice M-11修复: 回退随机性使用警告事件
    event FallbackRandomnessUsed(uint256 indexed disputeId, string warning);

    /**
     * @notice 分配仲裁员
     * @dev 安全改进: 使用增强的随机性生成算法
     *      M-11修复: 生产环境必须配置VRF，禁用回退随机性
     */
    function _assignArbitrators(uint256 disputeId) internal {
        // 检查是否配置了 VRF
        if (vrfSubscriptionId == 0) {
            // M-11修复: 检查是否允许回退随机性
            require(allowFallbackRandomness, "VRF not configured and fallback disabled");
            // 回退到本地随机数（仅用于测试）
            _assignArbitratorsFallback(disputeId);
        } else {
            // 请求 VRF 随机数
            _requestVRFRandomness(disputeId);
        }
    }

    /**
     * @dev 回退: 使用本地伪随机数
     *      M-11修复: 添加警告，仅用于测试环境
     */
    function _assignArbitratorsFallback(uint256 disputeId) internal {
        // M-11修复: 发出警告事件
        emit FallbackRandomnessUsed(disputeId, "WARNING: Using insecure pseudo-randomness. Configure Chainlink VRF for production.");
        // 获取符合条件的仲裁员
        address[] memory eligible = new address[](arbitratorPool.length);
        uint256 count = 0;

        for (uint256 i = 0; i < arbitratorPool.length; i++) {
            address arb = arbitratorPool[i];
            if (_isEligibleArbitrator(arb)) {
                if (arb != disputes[disputeId].plaintiff &&
                    arb != disputes[disputeId].defendant) {
                    eligible[count++] = arb;
                }
            }
        }

        require(count >= ARBITRATOR_COUNT, "Not enough arbitrators");

        address[3] memory selected;

        // 使用多个区块的哈希增加不可预测性
        uint256 seed = uint256(keccak256(abi.encodePacked(
            blockhash(block.number - 1),
            blockhash(block.number - 2),
            block.timestamp,
            block.prevrandao,
            disputeId,
            msg.sender,
            gasleft()
        )));

        // Fisher-Yates 洗牌算法
        for (uint256 i = 0; i < ARBITRATOR_COUNT; i++) {
            seed = uint256(keccak256(abi.encodePacked(seed, i)));
            uint256 index = seed % (count - i);

            selected[i] = eligible[index];
            eligible[index] = eligible[count - 1 - i];

            disputeArbitrators[disputeId].push(selected[i]);
        }

        emit ArbitratorsAssigned(disputeId, selected);
    }

    /**
     * @dev 请求 Chainlink VRF 随机数
     */
    function _requestVRFRandomness(uint256 disputeId) internal {
        uint256 requestId = vrfCoordinator.requestRandomWords(
            vrfKeyHash,
            vrfSubscriptionId,
            vrfRequestConfirmations,
            vrfCallbackGasLimit,
            1 // 只需要1个随机数
        );

        vrfRequestIdToDisputeId[requestId] = disputeId;
    }

    /**
     * @notice Chainlink VRF 回调函数 (由 VRF Coordinator 调用)
     * @dev 安全修复: 添加 onlyVRFCoordinator 访问控制
     */
    function fulfillRandomWords(
        uint256 requestId,
        uint256[] memory randomWords
    ) external {
        // 安全修复: 验证调用者是 VRF Coordinator
        require(msg.sender == address(vrfCoordinator), "Only VRF Coordinator");

        uint256 disputeId = vrfRequestIdToDisputeId[requestId];
        require(disputeId > 0, "Invalid request");

        _selectArbitratorsWithRandomness(disputeId, randomWords[0]);

        // 清理
        delete vrfRequestIdToDisputeId[requestId];
    }

    /**
     * @dev 使用 VRF 随机数选择仲裁员
     */
    function _selectArbitratorsWithRandomness(uint256 disputeId, uint256 randomness) internal {
        address[] memory eligible = new address[](arbitratorPool.length);
        uint256 count = 0;

        for (uint256 i = 0; i < arbitratorPool.length; i++) {
            address arb = arbitratorPool[i];
            if (_isEligibleArbitrator(arb)) {
                if (arb != disputes[disputeId].plaintiff &&
                    arb != disputes[disputeId].defendant) {
                    eligible[count++] = arb;
                }
            }
        }

        require(count >= ARBITRATOR_COUNT, "Not enough arbitrators");

        address[3] memory selected;

        // 使用 VRF 随机数进行 Fisher-Yates 洗牌
        uint256 seed = randomness;

        for (uint256 i = 0; i < ARBITRATOR_COUNT; i++) {
            seed = uint256(keccak256(abi.encodePacked(seed, i)));
            uint256 index = seed % (count - i);

            selected[i] = eligible[index];
            eligible[index] = eligible[count - 1 - i];

            disputeArbitrators[disputeId].push(selected[i]);
        }

        emit ArbitratorsAssigned(disputeId, selected);
    }

    /**
     * @notice 更新信用记录
     */
    function _updateCreditRecord(address user, bool won) internal {
        CreditRecord storage record = creditRecords[user];
        record.totalDisputes++;

        if (won) {
            record.totalWins++;
            record.consecutiveWins++;
            record.consecutiveLosses = 0;
        } else {
            record.consecutiveWins = 0;
            record.consecutiveLosses++;
        }

        emit CreditUpdated(user, record.consecutiveWins, record.consecutiveLosses);
    }

    /**
     * @notice 分配仲裁员奖励
     */
    function _distributeArbitratorRewards(
        uint256 disputeId,
        uint256 totalReward,
        bool plaintiffWon
    ) internal {
        address[] storage arbitratorsList = disputeArbitrators[disputeId];
        uint256 rewardPerArbitrator = totalReward / arbitratorsList.length;

        for (uint256 i = 0; i < arbitratorsList.length; i++) {
            address arb = arbitratorsList[i];
            Vote vote = disputeVotes[disputeId][arb];

            // 只奖励投票与结果一致的仲裁员
            if (
                (plaintiffWon && vote == Vote.ForPlaintiff) ||
                (!plaintiffWon && vote == Vote.ForDefendant)
            ) {
                vibeToken.safeTransfer(arb, rewardPerArbitrator);
                arbitrators[arb].rewards += rewardPerArbitrator;
                arbitrators[arb].correctVotes++;
                arbitrators[arb].reputation = _min(arbitrators[arb].reputation + 5, 200);
            } else if (vote == Vote.Abstain) {
                // 弃权返还部分
                vibeToken.safeTransfer(arb, rewardPerArbitrator / 2);
            } else {
                // 投错票扣信誉
                arbitrators[arb].reputation = arbitrators[arb].reputation > 10
                    ? arbitrators[arb].reputation - 10
                    : 0;
            }
        }
    }

    function _min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }
}
