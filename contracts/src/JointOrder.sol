// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title JointOrder
 * @notice 联合订单合约 - 实现需求聚合、反向竞价、资金托管、分批结算
 * @dev 支持多方需求聚合，服务商反向竞价，智能合约托管资金
 */
contract JointOrder is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    uint256 public constant MIN_POOL_BUDGET = 100 * 10**18;      // 最低池预算 100 VIBE
    uint256 public constant MAX_PARTICIPANTS = 50;               // 最大参与者数量
    uint256 public constant MAX_BIDS = 20;                       // 最大报价数量
    uint256 public constant PLATFORM_FEE_RATE = 300;             // 平台费率 3% (基点)
    uint256 public constant MIN_BIDDING_DURATION = 1 hours;      // 最短竞价时间
    uint256 public constant MAX_BIDDING_DURATION = 7 days;       // 最长竞价时间
    
    /// @notice Medium #14 修复: 订单超时处理时间
    uint256 public constant ORDER_TIMEOUT_DURATION = 30 days;

    /// @notice H3修复: 争议发起押金比例 (1% = 100 bps)
    uint256 public constant DISPUTE_PENALTY_RATE = 100;

    // ========== 状态枚举 ==========

    enum PoolStatus {
        CREATED,       // 已创建
        FUNDED,        // 已托管资金
        BIDDING,       // 竞价中
        AWARDED,       // 已授标
        IN_PROGRESS,   // 执行中
        DELIVERED,     // 已交付
        COMPLETED,     // 已完成
        DISPUTED,      // 争议中
        CANCELLED,     // 已取消
        EXPIRED        // 已过期
    }

    // ========== 数据结构 ==========

    struct OrderPool {
        bytes32 poolId;                    // 池ID
        address creator;                   // 创建者
        string serviceType;                // 服务类型
        uint256 totalBudget;               // 总预算
        uint256 minBudget;                 // 最低预算
        uint256 participantCount;          // 参与者数量
        uint256 bidCount;                  // 报价数量
        uint256 createdAt;                 // 创建时间
        uint256 fundingDeadline;           // 托管截止时间
        uint256 biddingEndsAt;             // 竞价截止时间
        uint256 deliveryDeadline;          // 交付截止
        PoolStatus status;                 // 状态
        address winningProvider;           // 中标服务商
        uint256 winningBid;                // 中标价格
        uint256 platformFee;               // 平台费用
        bytes32 metadataHash;              // 元数据哈希
    }

    struct Participant {
        address user;                      // 参与者地址
        uint256 budget;                    // 预算
        bytes32 demandId;                  // 需求ID
        bool hasDeposited;                 // 是否已托管
        bool hasConfirmed;                 // 是否已确认
        bool hasWithdrawn;                 // 是否已提取退款
        uint8 rating;                      // 评分 (1-5)
    }

    struct Bid {
        bytes32 bidId;                     // 报价ID
        bytes32 poolId;                    // 池ID
        address provider;                  // 服务商
        uint256 price;                     // 报价
        uint256 deliveryTime;              // 承诺交付时间(小时)
        uint256 reputationScore;           // 信誉分 (链下签名验证)
        uint256 computedScore;             // 综合评分
        bool isWinner;                     // 是否中标
        string proposal;                   // 方案描述
    }

    // ========== 状态变量 ==========

    IERC20 public vibeToken;

    mapping(bytes32 => OrderPool) public pools;
    mapping(bytes32 => mapping(address => Participant)) public participants;
    mapping(bytes32 => address[]) public poolParticipants;
    mapping(bytes32 => mapping(bytes32 => Bid)) public bids;
    mapping(bytes32 => bytes32[]) public poolBids;
    mapping(address => bytes32[]) public userPools;

    /// @notice 争议退款标记 (poolId => 是否处于退款模式)
    mapping(bytes32 => bool) public refundPendingPools;

    /// @notice 退款领取记录 (poolId => user => 已领取)
    mapping(bytes32 => mapping(address => bool)) public refundClaimed;

    /// @notice H3修复: 争议押金信息 (poolId => DisputePenalty)
    struct DisputePenalty {
        address raiser;
        uint256 penaltyAmount;
        bool resolved;
    }
    mapping(bytes32 => DisputePenalty) public disputePenalties;

    uint256 public totalPoolsCreated;
    uint256 public totalPoolsCompleted;
    uint256 public totalVolume;

    address public arbitrator;
    address public feeCollector;

    /// @notice 信誉系统合约地址
    address public reputationSystem;

    /// @notice 信誉系统管理员（可签名信誉数据）
    address public reputationSigner;

    /// @notice 已验证的信誉记录 (user => reputationScore => timestamp)
    mapping(address => mapping(uint256 => uint256)) public verifiedReputation;

    // ========== 事件 ==========

    event PoolCreated(
        bytes32 indexed poolId,
        address indexed creator,
        string serviceType,
        uint256 minBudget,
        uint256 biddingDuration,
        uint256 deliveryDeadline
    );

    event ParticipantJoined(
        bytes32 indexed poolId,
        address indexed user,
        uint256 budget,
        bytes32 demandId
    );

    event FundsDeposited(
        bytes32 indexed poolId,
        address indexed user,
        uint256 amount
    );

    event PoolFunded(
        bytes32 indexed poolId,
        uint256 totalBudget,
        uint256 participantCount
    );

    event BidSubmitted(
        bytes32 indexed poolId,
        bytes32 indexed bidId,
        address provider,
        uint256 price,
        uint256 deliveryTime,
        uint256 reputationScore
    );

    event PoolAwarded(
        bytes32 indexed poolId,
        bytes32 indexed bidId,
        address winner,
        uint256 winningBid
    );

    event DeliveryConfirmed(
        bytes32 indexed poolId,
        address indexed user,
        uint8 rating
    );

    event PoolCompleted(
        bytes32 indexed poolId,
        uint256 totalPayout,
        uint256 platformFee
    );

    /// @notice Medium #14 修复: 订单过期事件
    event PoolExpired(
        bytes32 indexed poolId,
        uint256 timestamp
    );

    event EarningsWithdrawn(
        bytes32 indexed poolId,
        address provider,
        uint256 amount
    );

    event RefundWithdrawn(
        bytes32 indexed poolId,
        address user,
        uint256 amount
    );

    event DisputeRaised(
        bytes32 indexed poolId,
        address indexed raiser,
        string reason
    );

    event DisputeResolved(
        bytes32 indexed poolId,
        bool refundBuyers,
        uint256 buyerRefund,
        uint256 providerPayout
    );

    /// @notice 退款领取事件
    event RefundClaimed(
        bytes32 indexed poolId,
        address indexed user,
        uint256 amount
    );

    event PoolCancelled(
        bytes32 indexed poolId,
        string reason
    );

    event ReputationVerified(
        address indexed user,
        uint256 reputationScore,
        uint256 timestamp
    );

    event ReputationSystemUpdated(
        address indexed reputationSystem,
        address indexed reputationSigner
    );

    // ========== 修饰符 ==========

    modifier poolExists(bytes32 poolId) {
        require(pools[poolId].createdAt > 0, "JointOrder: pool not exists");
        _;
    }

    modifier poolInStatus(bytes32 poolId, PoolStatus status) {
        require(pools[poolId].status == status, "JointOrder: invalid status");
        _;
    }

    modifier onlyArbitrator() {
        require(msg.sender == arbitrator, "JointOrder: not arbitrator");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _arbitrator,
        address _feeCollector
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "JointOrder: invalid token");
        require(_arbitrator != address(0), "JointOrder: invalid arbitrator");
        require(_feeCollector != address(0), "JointOrder: invalid fee collector");

        vibeToken = IERC20(_vibeToken);
        arbitrator = _arbitrator;
        feeCollector = _feeCollector;
    }

    // ========== 外部函数 - 池管理 ==========

    /**
     * @notice 创建需求池
     * @param serviceType 服务类型
     * @param minBudget 最低预算
     * @param fundingDuration 托管期限
     * @param biddingDuration 竞价期限
     * @param deliveryDeadline 交付截止
     * @param metadataHash 元数据哈希
     * @return poolId 池ID
     */
    function createPool(
        string calldata serviceType,
        uint256 minBudget,
        uint256 fundingDuration,
        uint256 biddingDuration,
        uint256 deliveryDeadline,
        bytes32 metadataHash
    ) external whenNotPaused returns (bytes32) {
        require(bytes(serviceType).length > 0, "JointOrder: empty service type");
        require(minBudget >= MIN_POOL_BUDGET, "JointOrder: budget too low");
        require(biddingDuration >= MIN_BIDDING_DURATION, "JointOrder: bidding too short");
        require(biddingDuration <= MAX_BIDDING_DURATION, "JointOrder: bidding too long");
        require(deliveryDeadline > block.timestamp + biddingDuration, "JointOrder: invalid deadline");

        bytes32 poolId = keccak256(
            abi.encodePacked(
                msg.sender,
                serviceType,
                block.timestamp,
                totalPoolsCreated
            )
        );

        uint256 fundingDeadline = block.timestamp + fundingDuration;

        pools[poolId] = OrderPool({
            poolId: poolId,
            creator: msg.sender,
            serviceType: serviceType,
            totalBudget: 0,
            minBudget: minBudget,
            participantCount: 0,
            bidCount: 0,
            createdAt: block.timestamp,
            fundingDeadline: fundingDeadline,
            biddingEndsAt: fundingDeadline + biddingDuration,
            deliveryDeadline: deliveryDeadline,
            status: PoolStatus.CREATED,
            winningProvider: address(0),
            winningBid: 0,
            platformFee: 0,
            metadataHash: metadataHash
        });

        userPools[msg.sender].push(poolId);
        totalPoolsCreated++;

        emit PoolCreated(
            poolId,
            msg.sender,
            serviceType,
            minBudget,
            biddingDuration,
            deliveryDeadline
        );

        return poolId;
    }

    /**
     * @notice 参与者加入池
     * @param poolId 池ID
     * @param budget 预算
     * @param demandId 需求ID
     * @param requirementsHash 需求哈希
     */
    function joinPool(
        bytes32 poolId,
        uint256 budget,
        bytes32 demandId,
        bytes32 requirementsHash
    )
        external
        nonReentrant
        poolExists(poolId)
        poolInStatus(poolId, PoolStatus.CREATED)
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];

        require(block.timestamp < pool.fundingDeadline, "JointOrder: funding ended");
        require(budget > 0, "JointOrder: zero budget");
        require(pool.participantCount < MAX_PARTICIPANTS, "JointOrder: pool full");
        require(participants[poolId][msg.sender].user == address(0), "JointOrder: already joined");

        // 转入资金
        vibeToken.safeTransferFrom(msg.sender, address(this), budget);

        // 记录参与者
        participants[poolId][msg.sender] = Participant({
            user: msg.sender,
            budget: budget,
            demandId: demandId,
            hasDeposited: true,
            hasConfirmed: false,
            hasWithdrawn: false,
            rating: 0
        });

        poolParticipants[poolId].push(msg.sender);
        pool.participantCount++;
        pool.totalBudget += budget;

        userPools[msg.sender].push(poolId);

        emit ParticipantJoined(poolId, msg.sender, budget, demandId);
        emit FundsDeposited(poolId, msg.sender, budget);

        // 检查是否达到最低预算
        if (pool.totalBudget >= pool.minBudget) {
            pool.status = PoolStatus.FUNDED;
            emit PoolFunded(poolId, pool.totalBudget, pool.participantCount);
        }
    }

    /**
     * @notice 提交报价
     * @param poolId 池ID
     * @param price 报价
     * @param deliveryTime 承诺交付时间(小时)
     * @param reputationScore 信誉分
     * @param proposal 方案描述
     * @param reputationSignature 信誉签名
     */
    function submitBid(
        bytes32 poolId,
        uint256 price,
        uint256 deliveryTime,
        uint256 reputationScore,
        string calldata proposal,
        bytes calldata reputationSignature
    ) 
        external 
        poolExists(poolId) 
        poolInStatus(poolId, PoolStatus.FUNDED)
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];

        require(block.timestamp < pool.biddingEndsAt, "JointOrder: bidding ended");
        require(price > 0 && price <= pool.totalBudget, "JointOrder: invalid price");
        require(pool.bidCount < MAX_BIDS, "JointOrder: too many bids");
        require(reputationScore <= 100, "JointOrder: invalid reputation");

        // 验证信誉分数 (完整验证)
        _verifyReputationScore(msg.sender, reputationScore, reputationSignature);

        bytes32 bidId = keccak256(
            abi.encodePacked(poolId, msg.sender, price, block.timestamp)
        );

        // 计算综合评分: 价格40% + 交付时间20% + 信誉40%
        uint256 priceScore = (pool.totalBudget * 100) / price;
        uint256 timeScore = deliveryTime > 0 ? (168 * 100) / deliveryTime : 50; // 相对于7天
        uint256 computedScore = (priceScore * 40 + timeScore * 20 + reputationScore * 40) / 100;

        bids[poolId][bidId] = Bid({
            bidId: bidId,
            poolId: poolId,
            provider: msg.sender,
            price: price,
            deliveryTime: deliveryTime,
            reputationScore: reputationScore,
            computedScore: computedScore,
            isWinner: false,
            proposal: proposal
        });

        poolBids[poolId].push(bidId);
        pool.bidCount++;

        emit BidSubmitted(
            poolId,
            bidId,
            msg.sender,
            price,
            deliveryTime,
            reputationScore
        );
    }

    /**
     * @notice 选择中标者
     * @param poolId 池ID
     * @param bidId 中标报价ID
     */
    function awardPool(
        bytes32 poolId,
        bytes32 bidId
    ) 
        external 
        poolExists(poolId) 
        poolInStatus(poolId, PoolStatus.FUNDED)
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];
        Bid storage winningBid = bids[poolId][bidId];

        require(msg.sender == pool.creator, "JointOrder: not creator");
        require(block.timestamp >= pool.biddingEndsAt, "JointOrder: bidding not ended");
        require(winningBid.poolId == poolId, "JointOrder: bid not in pool");

        pool.winningProvider = winningBid.provider;
        pool.winningBid = winningBid.price;
        pool.platformFee = (winningBid.price * PLATFORM_FEE_RATE) / 10000;

        winningBid.isWinner = true;

        emit PoolAwarded(poolId, bidId, winningBid.provider, winningBid.price);

        // 直接进入执行中状态（AWARDED 状态被立即覆盖，无实际意义）
        pool.status = PoolStatus.IN_PROGRESS;
    }

    /**
     * @notice 确认交付
     * @param poolId 池ID
     * @param rating 评分 (1-5)
     */
    function confirmDelivery(
        bytes32 poolId,
        uint8 rating
    )
        external
        nonReentrant
        poolExists(poolId) 
        poolInStatus(poolId, PoolStatus.IN_PROGRESS)
        whenNotPaused
    {
        require(rating >= 1 && rating <= 5, "JointOrder: invalid rating");

        Participant storage participant = participants[poolId][msg.sender];
        require(participant.hasDeposited, "JointOrder: not a participant");
        require(!participant.hasConfirmed, "JointOrder: already confirmed");

        participant.hasConfirmed = true;
        participant.rating = rating;

        emit DeliveryConfirmed(poolId, msg.sender, rating);

        // 检查是否所有参与者都已确认
        OrderPool storage pool = pools[poolId];
        uint256 confirmedCount = 0;
        for (uint256 i = 0; i < pool.participantCount; i++) {
            if (participants[poolId][poolParticipants[poolId][i]].hasConfirmed) {
                confirmedCount++;
            }
        }

        if (confirmedCount == pool.participantCount) {
            _completePool(poolId);
        }
    }

    /**
     * @notice 提取收益
     * @param poolId 池ID
     */
    function withdrawEarnings(bytes32 poolId) 
        external 
        poolExists(poolId) 
        poolInStatus(poolId, PoolStatus.COMPLETED)
        nonReentrant
    {
        OrderPool storage pool = pools[poolId];

        require(msg.sender == pool.winningProvider, "JointOrder: not winner");

        uint256 payout = pool.winningBid - pool.platformFee;
        pool.winningBid = 0; // 防止重复提取

        vibeToken.safeTransfer(msg.sender, payout);

        emit EarningsWithdrawn(poolId, msg.sender, payout);
    }

    /**
     * @notice 取消池并退款
     * @param poolId 池ID
     * @param reason 取消原因
     */
    function cancelPool(
        bytes32 poolId,
        string calldata reason
    )
        external
        nonReentrant
        poolExists(poolId) 
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];

        require(
            msg.sender == pool.creator || msg.sender == owner(),
            "JointOrder: not authorized"
        );
        require(
            pool.status == PoolStatus.CREATED || 
            pool.status == PoolStatus.FUNDED,
            "JointOrder: cannot cancel"
        );

        pool.status = PoolStatus.CANCELLED;

        // 安全修复: 使用拉取模式而非推送模式
        // 参与者需要调用 claimRefund() 来取回资金
        // 这避免了大量参与者导致 gas 超限的 DoS 攻击

        emit PoolCancelled(poolId, reason);
    }

    /**
     * @notice 领取退款（池取消后）
     * @param poolId 池ID
     * @dev 安全改进: 使用拉取模式防止 DoS
     */
    function claimRefund(bytes32 poolId)
        external
        nonReentrant
        poolExists(poolId)
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];

        require(pool.status == PoolStatus.CANCELLED, "JointOrder: pool not cancelled");

        Participant storage p = participants[poolId][msg.sender];
        require(p.hasDeposited, "JointOrder: not a participant");
        require(!p.hasWithdrawn, "JointOrder: already withdrawn");

        p.hasWithdrawn = true;
        uint256 amount = p.budget;

        vibeToken.safeTransfer(msg.sender, amount);

        emit RefundWithdrawn(poolId, msg.sender, amount);
    }

    /**
     * @notice 发起争议
     * @param poolId 池ID
     * @param reason 争议原因
     * @dev H3修复: 发起争议需要抵押押金，如果败诉则押金赔给对方
     */
    function raiseDispute(
        bytes32 poolId,
        string calldata reason
    )
        external
        poolExists(poolId)
        whenNotPaused
        nonReentrant
    {
        OrderPool storage pool = pools[poolId];
        Participant storage participant = participants[poolId][msg.sender];

        require(
            pool.status == PoolStatus.IN_PROGRESS ||
            pool.status == PoolStatus.DELIVERED,
            "JointOrder: invalid status"
        );
        require(
            participant.hasDeposited || msg.sender == pool.winningProvider,
            "JointOrder: not authorized"
        );

        // H3修复: 计算并扣除争议押金 (1% of winning bid)
        uint256 penaltyAmount = (pool.winningBid * DISPUTE_PENALTY_RATE) / 10000;
        require(
            vibeToken.balanceOf(msg.sender) >= penaltyAmount,
            "JointOrder: insufficient balance for dispute penalty"
        );

        // 转账押金到合约持有
        if (penaltyAmount > 0) {
            vibeToken.safeTransferFrom(msg.sender, address(this), penaltyAmount);
        }

        // 记录押金信息
        disputePenalties[poolId] = DisputePenalty({
            raiser: msg.sender,
            penaltyAmount: penaltyAmount,
            resolved: false
        });

        pool.status = PoolStatus.DISPUTED;

        emit DisputeRaised(poolId, msg.sender, reason);
    }

    /**
     * @notice 解决争议 (仅仲裁员)
     * @param poolId 池ID
     * @param refundBuyers 是否退款给买方
     * @param resolution 解决方案
     * @dev H3修复: 处理争议押金 - 败诉方押金赔给胜诉方
     */
    function resolveDispute(
        bytes32 poolId,
        bool refundBuyers,
        string calldata resolution
    )
        external
        onlyArbitrator
        poolExists(poolId)
        poolInStatus(poolId, PoolStatus.DISPUTED)
        nonReentrant
    {
        OrderPool storage pool = pools[poolId];
        DisputePenalty storage penalty = disputePenalties[poolId];

        uint256 buyerRefund = 0;
        uint256 providerPayout = 0;

        if (refundBuyers) {
            // 买家胜诉: 提供商的押金赔给买家，provider输
            // 修复: 使用拉取模式，避免 Gas 溢出
            // 标记池为待退款状态，用户自行领取
            refundPendingPools[poolId] = true;

            // 计算总退款金额
            for (uint256 i = 0; i < pool.participantCount; i++) {
                address participantAddr = poolParticipants[poolId][i];
                Participant storage p = participants[poolId][participantAddr];
                if (p.hasDeposited && !p.hasWithdrawn) {
                    buyerRefund += p.budget;
                }
            }

            // H3修复: 提供商输，押金不退（已被没收）
            // 押金留在合约，最终由参与者按比例分享
            // 如果有罚金，加入退款池
            if (penalty.penaltyAmount > 0) {
                buyerRefund += penalty.penaltyAmount;
            }

            pool.status = PoolStatus.CANCELLED;
        } else {
            // 提供商胜诉: 买家/参与者的押金赔给提供商
            if (penalty.penaltyAmount > 0) {
                // 将押金转给提供商
                vibeToken.safeTransfer(pool.winningProvider, penalty.penaltyAmount);
            }

            // 支付给服务商
            providerPayout = pool.winningBid - pool.platformFee;
            vibeToken.safeTransfer(pool.winningProvider, providerPayout);
            vibeToken.safeTransfer(feeCollector, pool.platformFee);
            pool.status = PoolStatus.COMPLETED;
            totalPoolsCompleted++;
            totalVolume += pool.winningBid;
        }

        // 标记押金已处理
        penalty.resolved = true;

        emit DisputeResolved(poolId, refundBuyers, buyerRefund, providerPayout);
    }

    /**
     * @notice 领取争议退款（拉取模式，避免 Gas 溢出）
     * @param poolId 池ID
     */
    function claimDisputeRefund(bytes32 poolId)
        external
        nonReentrant
    {
        require(refundPendingPools[poolId], "JointOrder: not a refund pool");
        require(!refundClaimed[poolId][msg.sender], "JointOrder: already claimed");

        Participant storage p = participants[poolId][msg.sender];
        require(p.hasDeposited && !p.hasWithdrawn, "JointOrder: no refund available");

        uint256 refundAmount = p.budget;

        // 标记已领取
        refundClaimed[poolId][msg.sender] = true;
        p.hasWithdrawn = true;

        // 转账
        vibeToken.safeTransfer(msg.sender, refundAmount);

        emit RefundClaimed(poolId, msg.sender, refundAmount);
    }

    // ========== 公共视图函数 ==========

    function getPool(bytes32 poolId) external view returns (OrderPool memory) {
        return pools[poolId];
    }

    function getParticipant(bytes32 poolId, address user) external view returns (Participant memory) {
        return participants[poolId][user];
    }

    function getBid(bytes32 poolId, bytes32 bidId) external view returns (Bid memory) {
        return bids[poolId][bidId];
    }

    function getPoolParticipants(bytes32 poolId) external view returns (address[] memory) {
        return poolParticipants[poolId];
    }

    function getPoolBids(bytes32 poolId) external view returns (bytes32[] memory) {
        return poolBids[poolId];
    }

    function getUserPools(address user) external view returns (bytes32[] memory) {
        return userPools[user];
    }

    function getStats() external view returns (
        uint256 _totalPoolsCreated,
        uint256 _totalPoolsCompleted,
        uint256 _totalVolume
    ) {
        return (totalPoolsCreated, totalPoolsCompleted, totalVolume);
    }

    // ========== 内部函数 ==========

    /**
     * @dev 验证信誉分数 (完整版)
     * 支持三种验证模式:
     * 1. 签名验证: 验证信誉签名的有效性
     * 2. 链上验证: 查询信誉系统合约
     * 3. 缓存验证: 使用已验证的信誉记录
     *
     * @param user 用户地址
     * @param reputationScore 信誉分数
     * @param signature 信誉签名数据
     */
    function _verifyReputationScore(
        address user,
        uint256 reputationScore,
        bytes calldata signature
    ) internal {
        // 基本范围检查
        require(reputationScore <= 100, "JointOrder: invalid reputation score");

        // 如果未设置签名者，只接受范围检查（向后兼容）
        if (reputationSigner == address(0)) {
            return;
        }

        // 验证签名长度 (64字节 = r + s, 可选 + v)
        // 或者尝试解析内嵌在signature中的数据
        if (signature.length >= 64) {
            // 尝试恢复签名者
            _verifySignature(user, reputationScore, signature);
        } else if (reputationSystem != address(0)) {
            // 使用链上信誉系统验证
            _verifyViaReputationSystem(user, reputationScore);
        } else {
            // 使用缓存的已验证信誉记录
            _verifyViaCache(user, reputationScore);
        }
    }

    /**
     * @dev 通过签名验证信誉
     */
    function _verifySignature(
        address user,
        uint256 reputationScore,
        bytes calldata signature
    ) internal {
        // 构建签名消息
        bytes32 message = keccak256(abi.encodePacked(
            user,
            reputationScore,
            block.chainid,
            "JOINT_ORDER_REPUTATION"
        ));

        // 转换为 EIP-191 格式
        bytes32 ethSignedMessage = keccak256(abi.encodePacked(
            "\x19Ethereum Signed Message:\n32",
            message
        ));

        // 从签名中提取 r, s, v
        require(signature.length >= 64, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }

        // 如果 v < 27，调整为 27 或 28
        if (v < 27) {
            v += 27;
        }

        // 恢复签名者地址
        address signer = ecrecover(ethSignedMessage, v, r, s);

        // 验证签名者是否是授权的信誉签名者
        require(signer == reputationSigner, "Invalid reputation signature");

        // 记录验证时间和分数
        verifiedReputation[user][reputationScore] = block.timestamp;

        emit ReputationVerified(user, reputationScore, block.timestamp);
    }

    /**
     * @dev 通过链上信誉系统验证
     */
    function _verifyViaReputationSystem(address user, uint256 reputationScore) internal {
        // 调用信誉系统合约
        IReputationSystem reputation = IReputationSystem(reputationSystem);
        uint256 storedScore = reputation.getReputationScore(user);

        // 验证分数匹配
        require(storedScore == reputationScore, "Reputation mismatch");

        // 验证信誉有效性
        require(reputation.isReputationValid(user), "Invalid reputation");

        emit ReputationVerified(user, reputationScore, block.timestamp);
    }

    /**
     * @dev 通过缓存验证信誉
     */
    function _verifyViaCache(address user, uint256 reputationScore) internal {
        // 检查是否有缓存的信誉记录
        uint256 cachedTimestamp = verifiedReputation[user][reputationScore];

        // 信誉记录必须在过去24小时内
        require(cachedTimestamp > 0 && block.timestamp - cachedTimestamp < 24 hours, "No valid reputation");

        emit ReputationVerified(user, reputationScore, cachedTimestamp);
    }

    function _completePool(bytes32 poolId) internal {
        OrderPool storage pool = pools[poolId];

        pool.status = PoolStatus.COMPLETED;
        totalPoolsCompleted++;
        totalVolume += pool.winningBid;

        // 支付平台费用
        vibeToken.safeTransfer(feeCollector, pool.platformFee);

        emit PoolCompleted(poolId, pool.winningBid, pool.platformFee);
    }

    /**
     * @notice Medium #14 修复: 处理订单超时
     * @param poolId 池ID
     * @dev 超时后允许参与者取回资金
     */
    function handleOrderTimeout(bytes32 poolId) 
        external 
        nonReentrant 
        poolExists(poolId) 
    {
        OrderPool storage pool = pools[poolId];
        
        // 检查是否已超时
        require(
            block.timestamp > pool.deliveryDeadline + ORDER_TIMEOUT_DURATION,
            "JointOrder: order not timed out yet"
        );
        
        // 只允许在特定状态下处理超时
        require(
            pool.status == PoolStatus.IN_PROGRESS,
            "JointOrder: invalid status for timeout"
        );
        
        // 标记为过期
        pool.status = PoolStatus.EXPIRED;
        
        // 启用退款模式
        refundPendingPools[poolId] = true;
        
        emit PoolExpired(poolId, block.timestamp);
    }

    // ========== 管理函数 ==========

    function setArbitrator(address _arbitrator) external onlyOwner {
        require(_arbitrator != address(0), "JointOrder: invalid address");
        arbitrator = _arbitrator;
    }

    function setFeeCollector(address _feeCollector) external onlyOwner {
        require(_feeCollector != address(0), "JointOrder: invalid address");
        feeCollector = _feeCollector;
    }

    /**
     * @notice 设置信誉系统合约
     * @param _reputationSystem 信誉系统合约地址
     * @param _reputationSigner 信誉签名管理员地址
     */
    function setReputationSystem(address _reputationSystem, address _reputationSigner) external onlyOwner {
        require(_reputationSystem != address(0), "JointOrder: invalid reputation system");
        require(_reputationSigner != address(0), "JointOrder: invalid signer");
        reputationSystem = _reputationSystem;
        reputationSigner = _reputationSigner;
        emit ReputationSystemUpdated(_reputationSystem, _reputationSigner);
    }

    /**
     * @notice 直接设置可信签名者（用于离线签名验证）
     * @param _signer 签名者地址
     */
    function setReputationSigner(address _signer) external onlyOwner {
        require(_signer != address(0), "JointOrder: invalid signer");
        reputationSigner = _signer;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 紧急提取代币
     * @dev 安全增强: 添加 nonReentrant 和零地址检查
     */
    function emergencyWithdraw(address token, address to, uint256 amount) external nonReentrant onlyOwner {
        require(to != address(0), "JointOrder: invalid recipient");
        require(amount > 0, "JointOrder: amount must be greater than 0");
        IERC20(token).safeTransfer(to, amount);
    }
}

// ========== 接口 ==========

/**
 * @title IReputationSystem
 * @notice 链上信誉系统接口
 */
interface IReputationSystem {
    /**
     * @notice 获取用户信誉分数
     * @param user 用户地址
     * @return 信誉分数 (0-100)
     */
    function getReputationScore(address user) external view returns (uint256);

    /**
     * @notice 验证信誉是否有效
     * @param user 用户地址
     * @return 是否有效
     */
    function isReputationValid(address user) external view returns (bool);
}
