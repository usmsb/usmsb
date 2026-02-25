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

    uint256 public totalPoolsCreated;
    uint256 public totalPoolsCompleted;
    uint256 public totalVolume;

    address public arbitrator;
    address public feeCollector;

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

    event PoolCancelled(
        bytes32 indexed poolId,
        string reason
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
        payable 
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

        // 验证信誉签名 (简化版，实际应该验证签名)
        // _verifyReputationSignature(msg.sender, reputationScore, reputationSignature);

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

        pool.status = PoolStatus.AWARDED;
        pool.winningProvider = winningBid.provider;
        pool.winningBid = winningBid.price;
        pool.platformFee = (winningBid.price * PLATFORM_FEE_RATE) / 10000;

        winningBid.isWinner = true;

        emit PoolAwarded(poolId, bidId, winningBid.provider, winningBid.price);

        // 自动进入执行中状态
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

        // 退还所有参与者的资金
        for (uint256 i = 0; i < pool.participantCount; i++) {
            address participantAddr = poolParticipants[poolId][i];
            Participant storage p = participants[poolId][participantAddr];
            if (p.hasDeposited && !p.hasWithdrawn) {
                p.hasWithdrawn = true;
                vibeToken.safeTransfer(participantAddr, p.budget);
                emit RefundWithdrawn(poolId, participantAddr, p.budget);
            }
        }

        emit PoolCancelled(poolId, reason);
    }

    /**
     * @notice 发起争议
     * @param poolId 池ID
     * @param reason 争议原因
     */
    function raiseDispute(
        bytes32 poolId,
        string calldata reason
    ) 
        external 
        poolExists(poolId) 
        whenNotPaused
    {
        OrderPool storage pool = pools[poolId];
        Participant storage participant = participants[poolId][msg.sender];

        require(
            pool.status == PoolStatus.IN_PROGRESS || 
            pool.status == PoolStatus.AWARDED ||
            pool.status == PoolStatus.DELIVERED,
            "JointOrder: invalid status"
        );
        require(
            participant.hasDeposited || msg.sender == pool.winningProvider,
            "JointOrder: not authorized"
        );

        pool.status = PoolStatus.DISPUTED;

        emit DisputeRaised(poolId, msg.sender, reason);
    }

    /**
     * @notice 解决争议 (仅仲裁员)
     * @param poolId 池ID
     * @param refundBuyers 是否退款给买方
     * @param resolution 解决方案
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

        uint256 buyerRefund = 0;
        uint256 providerPayout = 0;

        if (refundBuyers) {
            // 退款给所有参与者
            for (uint256 i = 0; i < pool.participantCount; i++) {
                address participantAddr = poolParticipants[poolId][i];
                Participant storage p = participants[poolId][participantAddr];
                if (p.hasDeposited && !p.hasWithdrawn) {
                    p.hasWithdrawn = true;
                    vibeToken.safeTransfer(participantAddr, p.budget);
                    buyerRefund += p.budget;
                }
            }
            pool.status = PoolStatus.CANCELLED;
        } else {
            // 支付给服务商
            providerPayout = pool.winningBid - pool.platformFee;
            vibeToken.safeTransfer(pool.winningProvider, providerPayout);
            vibeToken.safeTransfer(feeCollector, pool.platformFee);
            pool.status = PoolStatus.COMPLETED;
            totalPoolsCompleted++;
            totalVolume += pool.winningBid;
        }

        emit DisputeResolved(poolId, refundBuyers, buyerRefund, providerPayout);
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

    function _completePool(bytes32 poolId) internal {
        OrderPool storage pool = pools[poolId];

        pool.status = PoolStatus.COMPLETED;
        totalPoolsCompleted++;
        totalVolume += pool.winningBid;

        // 支付平台费用
        vibeToken.safeTransfer(feeCollector, pool.platformFee);

        emit PoolCompleted(poolId, pool.winningBid, pool.platformFee);
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

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function emergencyWithdraw(address token, address to, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(to, amount);
    }
}
