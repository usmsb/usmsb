// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IVIBIdentity for NodeReward
 */
interface IVIBIdentityForNode {
    enum IdentityType { AI_AGENT, HUMAN_PROVIDER, NODE_OPERATOR, GOVERNANCE }
    function isRegistered(address) external view returns (bool);
    function getIdentityType(uint256 tokenId) external view returns (IdentityType);
    function getTokenIdByAddress(address owner) external view returns (uint256);
}

/**
 * @title IPriceOracle for USD锚定定价
 */
interface IPriceOracle {
    function getVibePrice() external view returns (uint256);
}

/**
 * @title VIBNodeReward
 * @notice 节点激励合约 - 完全去中心化自动分配
 * @dev 实现白皮书承诺的节点收益模型：
 *      节点总收益 = 基础服务收入 + 生产力加成 + 可靠性奖励
 *
 * 服务类型定价（USD锚定）:
 * - GPU算力: $0.5-5.0/GPU小时
 * - CPU算力: $0.05-0.5/CPU小时
 * - 存储: $0.005/GB/天
 * 支付时按VIBE实时价格折算
 *
 * 完全去中心化：奖励由预言机或自动化系统触发，不需要人工干预
 */
contract VIBNodeReward is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 基础服务定价（单位：USD，精度10^18）
    // 白皮书修复: 改为USD锚定定价
    uint256 public constant GPU_BASE_RATE_USD = 0.5 * 10**18;     // $0.5/GPU小时
    uint256 public constant GPU_MAX_RATE_USD = 5.0 * 10**18;      // $5.0/GPU小时
    uint256 public constant CPU_BASE_RATE_USD = 0.05 * 10**18;    // $0.05/CPU小时
    uint256 public constant CPU_MAX_RATE_USD = 0.5 * 10**18;      // $0.5/CPU小时
    uint256 public constant STORAGE_RATE_USD = 0.005 * 10**18;    // $0.005/GB/天

    // 奖励因子范围（精度10000）
    uint256 public constant MIN_QUALITY = 5000;       // 0.5x
    uint256 public constant MAX_QUALITY = 20000;      // 2.0x
    uint256 public constant MIN_PRODUCTIVITY = 10000; // 1.0x
    uint256 public constant MAX_PRODUCTIVITY = 13000; // 1.3x (最高+30%)
    uint256 public constant MIN_RELIABILITY = 10000;  // 1.0x
    uint256 public constant MAX_RELIABILITY = 12000;  // 1.2x (最高+20%)

    // 节点服务类型
    enum NodeType {
        GPU_COMPUTE,    // GPU算力
        CPU_COMPUTE,    // CPU算力
        STORAGE         // 存储
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice VIBIdentity合约（验证节点身份）
    address public identityContract;

    /// @notice 价格预言机地址（白皮书修复: USD锚定定价）
    address public priceOracle;

    /// @notice 已授权的服务质量评估者（预言机/自动化系统）
    mapping(address => bool) public authorizedAssessors;

    /// @notice 注册的节点
    mapping(address => NodeInfo) public nodes;

    /// @notice 节点数量
    uint256 public nodeCount;

    /// @notice 服务记录
    mapping(bytes32 => ServiceRecord) public serviceRecords;

    /// @notice 服务数量
    uint256 public serviceCount;

    /// @notice 节点总奖励
    mapping(address => uint256) public nodeTotalRewards;

    /// @notice 已发放总奖励
    uint256 public totalRewardsDistributed;

    /// @notice 算力信用（白皮书4.7.2）
    mapping(address => uint256) public computeCredits;

    /// @notice 节点在线时间（小时）
    mapping(address => uint256) public nodeOnlineHours;

    /// @notice 节点服务次数
    mapping(address => uint256) public nodeServiceCount;

    // ========== 结构体 ==========

    struct NodeInfo {
        address owner;              // 节点所有者
        NodeType nodeType;          // 节点类型
        uint256 capacity;           // 容量 (GPU数/CPU核心数/GB)
        uint256 registeredAt;       // 注册时间
        bool isActive;              // 是否活跃
        uint256 totalServices;      // 总服务次数
        uint256 totalReward;        // 总奖励
        uint256 reliabilityScore;   // 可靠性评分 (0-10000)
    }

    struct ServiceRecord {
        address node;               // 节点地址
        NodeType serviceType;       // 服务类型
        uint256 duration;           // 服务时长（秒）/存储天数
        uint256 capacity;           // 使用容量
        uint256 qualityScore;       // 质量评分
        uint256 baseReward;         // 基础奖励
        uint256 productivityBonus;  // 生产力加成
        uint256 reliabilityBonus;   // 可靠性加成
        uint256 finalReward;        // 最终奖励
        uint256 timestamp;          // 时间戳
        bool claimed;               // 是否已领取
        bytes32 serviceHash;        // 服务哈希（链下内容引用）
    }

    // ========== 事件 ==========

    event NodeRegistered(
        address indexed node,
        NodeType nodeType,
        uint256 capacity
    );

    event NodeDeactivated(address indexed node);

    event ServiceRecorded(
        bytes32 indexed serviceId,
        address indexed node,
        NodeType serviceType,
        uint256 duration,
        uint256 finalReward
    );

    event RewardClaimed(
        bytes32 indexed serviceId,
        address indexed node,
        uint256 amount
    );

    event ComputeCreditsEarned(
        address indexed node,
        uint256 amount,
        uint256 total
    );

    event AssessorUpdated(address indexed assessor, bool authorized);

    // ========== 修饰符 ==========

    modifier onlyAuthorizedAssessor() {
        require(authorizedAssessors[msg.sender], "VIBNodeReward: not authorized assessor");
        _;
    }

    modifier onlyRegisteredNode() {
        require(nodes[msg.sender].owner != address(0), "VIBNodeReward: node not registered");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _identityContract
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBNodeReward: invalid token");
        vibeToken = IERC20(_vibeToken);
        identityContract = _identityContract;
    }

    /**
     * @notice 设置价格预言机（白皮书修复: USD锚定）
     * @param _priceOracle 新预言机地址
     */
    function setPriceOracle(address _priceOracle) external onlyOwner {
        priceOracle = _priceOracle;
    }

    /**
     * @notice USD转换为VIBE数量（白皮书修复: USD锚定定价）
     * @param usdAmount USD数量
     * @return VIBE数量
     */
    function usdToVibe(uint256 usdAmount) public view returns (uint256) {
        if (priceOracle == address(0) || usdAmount == 0) {
            return usdAmount; // Fallback: 1:1
        }
        // 获取VIBE价格（假设预言机返回USD价格，乘以10^18）
        uint256 vibePrice = IPriceOracle(priceOracle).getVibePrice();
        // USD金额 / VIBE价格 = VIBE数量
        return (usdAmount * 10**18) / vibePrice;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 注册节点
     * @param nodeType 节点类型
     * @param capacity 容量 (GPU数/CPU核心数/GB)
     * @dev 需要先在VIBIdentity注册为NODE_OPERATOR
     */
    function registerNode(
        NodeType nodeType,
        uint256 capacity
    ) external whenNotPaused returns (bool) {
        require(capacity > 0, "VIBNodeReward: invalid capacity");
        require(nodes[msg.sender].owner == address(0), "VIBNodeReward: already registered");

        // 验证节点身份（可选）
        _verifyNodeIdentity(msg.sender);

        nodes[msg.sender] = NodeInfo({
            owner: msg.sender,
            nodeType: nodeType,
            capacity: capacity,
            registeredAt: block.timestamp,
            isActive: true,
            totalServices: 0,
            totalReward: 0,
            reliabilityScore: PRECISION // 初始可靠性100%
        });

        nodeCount++;

        emit NodeRegistered(msg.sender, nodeType, capacity);
        return true;
    }

    /**
     * @notice 停用/激活节点
     */
    function setNodeActive(bool isActive) external onlyRegisteredNode {
        nodes[msg.sender].isActive = isActive;
        if (!isActive) {
            emit NodeDeactivated(msg.sender);
        }
    }

    /**
     * @notice 记录服务并计算奖励（由授权评估者调用）
     * @param node 节点地址
     * @param serviceType 服务类型
     * @param duration 服务时长（秒）或存储天数
     * @param capacityUsed 使用容量
     * @param qualityScore 质量评分 (5000-20000)
     * @param productivityFactor 生产力因子 (10000-13000)
     * @param reliabilityFactor 可靠性因子 (10000-12000)
     * @param serviceHash 服务哈希
     * @return serviceId 服务ID
     */
    function recordService(
        address node,
        NodeType serviceType,
        uint256 duration,
        uint256 capacityUsed,
        uint256 qualityScore,
        uint256 productivityFactor,
        uint256 reliabilityFactor,
        bytes32 serviceHash
    ) external onlyAuthorizedAssessor whenNotPaused returns (bytes32 serviceId) {
        require(nodes[node].owner != address(0), "VIBNodeReward: node not registered");
        require(nodes[node].isActive, "VIBNodeReward: node not active");
        require(duration > 0, "VIBNodeReward: invalid duration");
        require(capacityUsed > 0, "VIBNodeReward: invalid capacity");

        // 验证因子范围
        require(qualityScore >= MIN_QUALITY && qualityScore <= MAX_QUALITY, "VIBNodeReward: invalid quality");
        require(productivityFactor >= MIN_PRODUCTIVITY && productivityFactor <= MAX_PRODUCTIVITY, "VIBNodeReward: invalid productivity");
        require(reliabilityFactor >= MIN_RELIABILITY && reliabilityFactor <= MAX_RELIABILITY, "VIBNodeReward: invalid reliability");

        serviceCount++;
        serviceId = keccak256(abi.encodePacked(
            node,
            serviceType,
            duration,
            capacityUsed,
            block.timestamp,
            serviceCount
        ));

        // 计算基础奖励
        uint256 baseReward = _calculateBaseReward(serviceType, duration, capacityUsed);

        // 计算最终奖励
        // Reward = BaseReward × Quality × Productivity × Reliability / PRECISION^3
        uint256 finalReward = baseReward;
        finalReward = (finalReward * qualityScore) / PRECISION;
        finalReward = (finalReward * productivityFactor) / PRECISION;
        finalReward = (finalReward * reliabilityFactor) / PRECISION;

        // 计算各加成部分
        uint256 productivityBonus = (baseReward * (productivityFactor - PRECISION)) / PRECISION;
        uint256 reliabilityBonus = (baseReward * (reliabilityFactor - PRECISION)) / PRECISION;

        // 存储服务记录
        serviceRecords[serviceId] = ServiceRecord({
            node: node,
            serviceType: serviceType,
            duration: duration,
            capacity: capacityUsed,
            qualityScore: qualityScore,
            baseReward: baseReward,
            productivityBonus: productivityBonus,
            reliabilityBonus: reliabilityBonus,
            finalReward: finalReward,
            timestamp: block.timestamp,
            claimed: false,
            serviceHash: serviceHash
        });

        // 更新节点统计
        nodes[node].totalServices++;
        nodes[node].totalReward += finalReward;

        // 更新在线时间（如果是计算服务）
        if (serviceType != NodeType.STORAGE) {
            nodeOnlineHours[node] += duration / 3600;
        }
        nodeServiceCount[node]++;

        // 累计算力信用（白皮书4.7.2）
        uint256 credits = finalReward / 10**18; // 1 VIBE = 1 信用
        computeCredits[node] += credits;
        emit ComputeCreditsEarned(node, credits, computeCredits[node]);

        emit ServiceRecorded(serviceId, node, serviceType, duration, finalReward);
    }

    /**
     * @notice 领取奖励
     * @param serviceId 服务ID
     */
    function claimReward(bytes32 serviceId) external nonReentrant whenNotPaused {
        ServiceRecord storage record = serviceRecords[serviceId];

        require(record.node == msg.sender, "VIBNodeReward: not service provider");
        require(record.finalReward > 0, "VIBNodeReward: no reward");
        require(!record.claimed, "VIBNodeReward: already claimed");

        record.claimed = true;
        uint256 reward = record.finalReward;

        nodeTotalRewards[msg.sender] += reward;
        totalRewardsDistributed += reward;

        // 从合约余额转账
        vibeToken.safeTransfer(msg.sender, reward);

        emit RewardClaimed(serviceId, msg.sender, reward);
    }

    /**
     * @notice 批量领取奖励
     */
    function batchClaimRewards(bytes32[] calldata serviceIds) external nonReentrant whenNotPaused {
        uint256 totalReward = 0;

        for (uint256 i = 0; i < serviceIds.length; i++) {
            ServiceRecord storage record = serviceRecords[serviceIds[i]];

            if (record.node == msg.sender &&
                record.finalReward > 0 &&
                !record.claimed) {
                record.claimed = true;
                totalReward += record.finalReward;
                emit RewardClaimed(serviceIds[i], msg.sender, record.finalReward);
            }
        }

        require(totalReward > 0, "VIBNodeReward: no rewards to claim");

        nodeTotalRewards[msg.sender] += totalReward;
        totalRewardsDistributed += totalReward;

        vibeToken.safeTransfer(msg.sender, totalReward);
    }

    /**
     * @notice 从EcosystemPool接收资金
     */
    function receiveFunds(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取节点信息
     */
    function getNodeInfo(address node) external view returns (NodeInfo memory) {
        return nodes[node];
    }

    /**
     * @notice 获取服务记录
     */
    function getServiceRecord(bytes32 serviceId) external view returns (ServiceRecord memory) {
        return serviceRecords[serviceId];
    }

    /**
     * @notice 计算预估奖励
     */
    function estimateReward(
        NodeType serviceType,
        uint256 duration,
        uint256 capacity,
        uint256 qualityScore,
        uint256 productivityFactor,
        uint256 reliabilityFactor
    ) external view returns (uint256) {
        uint256 baseReward = _calculateBaseReward(serviceType, duration, capacity);

        uint256 finalReward = baseReward;
        finalReward = (finalReward * qualityScore) / PRECISION;
        finalReward = (finalReward * productivityFactor) / PRECISION;
        finalReward = (finalReward * reliabilityFactor) / PRECISION;

        return finalReward;
    }

    /**
     * @notice 获取合约余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    /**
     * @notice 获取节点总奖励
     */
    function getNodeTotalRewards(address node) external view returns (uint256) {
        return nodeTotalRewards[node];
    }

    /**
     * @notice 获取节点算力信用
     */
    function getComputeCredits(address node) external view returns (uint256) {
        return computeCredits[node];
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置授权评估者
     */
    function setAuthorizedAssessor(address assessor, bool authorized) external onlyOwner {
        authorizedAssessors[assessor] = authorized;
        emit AssessorUpdated(assessor, authorized);
    }

    /**
     * @notice 设置身份合约
     */
    function setIdentityContract(address _identityContract) external onlyOwner {
        identityContract = _identityContract;
    }

    /**
     * @notice 更新节点可靠性评分
     */
    function updateReliabilityScore(address node, uint256 score) external onlyOwner {
        require(nodes[node].owner != address(0), "VIBNodeReward: node not registered");
        require(score <= PRECISION, "VIBNodeReward: score exceeds max");
        nodes[node].reliabilityScore = score;
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBNodeReward: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBNodeReward: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 计算基础奖励（白皮书修复: USD锚定定价）
     */
    function _calculateBaseReward(
        NodeType serviceType,
        uint256 duration,
        uint256 capacity
    ) internal view returns (uint256) {
        uint256 usdReward;
        if (serviceType == NodeType.GPU_COMPUTE) {
            // GPU: $0.5-5.0/GPU小时
            uint256 hrs = duration / 3600;
            usdReward = (GPU_BASE_RATE_USD * capacity * hrs);
        } else if (serviceType == NodeType.CPU_COMPUTE) {
            // CPU: $0.05-0.5/CPU小时
            uint256 hrs = duration / 3600;
            usdReward = (CPU_BASE_RATE_USD * capacity * hrs);
        } else {
            // Storage: $0.005/GB/天
            uint256 days_ = duration / 86400;
            usdReward = (STORAGE_RATE_USD * capacity * days_);
        }
        // 转换为VIBE
        return usdToVibe(usdReward);
    }

    /**
     * @notice 验证节点身份
     */
    function _verifyNodeIdentity(address node) internal view {
        if (identityContract != address(0)) {
            IVIBIdentityForNode identity = IVIBIdentityForNode(identityContract);
            if (identity.isRegistered(node)) {
                uint256 tokenId = identity.getTokenIdByAddress(node);
                IVIBIdentityForNode.IdentityType idType = identity.getIdentityType(tokenId);
                require(
                    idType == IVIBIdentityForNode.IdentityType.NODE_OPERATOR,
                    "VIBNodeReward: not a node operator"
                );
            }
        }
    }
}
