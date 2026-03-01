// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBInfrastructurePool
 * @notice 基础设施节点激励池 - 硅基文明平台节点收入来源
 * @dev 接收交易手续费的15%生态基金，分发给IPFS/基础设施节点
 *      采用服务证明模式（Proof of Service）
 *
 * 节点类型:
 * - IPFS存储节点: 提供去中心化存储服务
 * - 数据中继节点: 提供数据传输服务
 * - 验证节点: 提供数据完整性验证
 *
 * 完全去中心化：由授权评估者（预言机）记录服务并触发奖励
 */
contract VIBInfrastructurePool is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 服务类型奖励范围（单位：VIBE，精度10^18）
    uint256 public constant IPFS_STORAGE_MIN = 0.1 * 10**18;    // 0.1 VIBE/GB/天
    uint256 public constant IPFS_STORAGE_MAX = 1 * 10**18;      // 1 VIBE/GB/天
    uint256 public constant RELAY_MIN = 0.01 * 10**18;          // 0.01 VIBE/GB
    uint256 public constant RELAY_MAX = 0.1 * 10**18;           // 0.1 VIBE/GB
    uint256 public constant VERIFICATION_MIN = 0.05 * 10**18;   // 0.05 VIBE/次
    uint256 public constant VERIFICATION_MAX = 0.5 * 10**18;    // 0.5 VIBE/次

    // 节点服务类型
    enum ServiceType {
        IPFS_STORAGE,      // IPFS存储
        DATA_RELAY,        // 数据中继
        VERIFICATION       // 验证服务
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 已授权的评估者（预言机/自动化系统）
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

    /// @notice 总接收资金
    uint256 public totalFundsReceived;

    // ========== 结构体 ==========

    struct NodeInfo {
        address owner;              // 节点所有者
        ServiceType primaryService; // 主要服务类型
        uint256 capacity;           // 容量 (GB)
        uint256 registeredAt;       // 注册时间
        bool isActive;              // 是否活跃
        uint256 totalServices;      // 总服务次数
        uint256 totalReward;        // 总奖励
        string endpoint;            // 节点端点（如IPFS节点ID）
    }

    struct ServiceRecord {
        address node;               // 节点地址
        ServiceType serviceType;    // 服务类型
        uint256 dataAmount;         // 数据量（GB）或次数
        uint256 duration;           // 服务时长（秒，仅存储用）
        uint256 qualityScore;       // 质量评分 (5000-20000)
        uint256 baseReward;         // 基础奖励
        uint256 finalReward;        // 最终奖励
        uint256 timestamp;          // 时间戳
        bool claimed;               // 是否已领取
        bytes32 serviceHash;        // 服务哈希（链下内容引用）
    }

    // ========== 事件 ==========

    event NodeRegistered(
        address indexed node,
        ServiceType serviceType,
        uint256 capacity,
        string endpoint
    );

    event NodeDeactivated(address indexed node);

    event ServiceRecorded(
        bytes32 indexed serviceId,
        address indexed node,
        ServiceType serviceType,
        uint256 dataAmount,
        uint256 finalReward
    );

    event RewardClaimed(
        bytes32 indexed serviceId,
        address indexed node,
        uint256 amount
    );

    event AssessorUpdated(address indexed assessor, bool authorized);

    event FundsReceived(uint256 amount, address from);

    // ========== 修饰符 ==========

    modifier onlyAuthorizedAssessor() {
        require(authorizedAssessors[msg.sender], "VIBInfrastructurePool: not authorized assessor");
        _;
    }

    modifier onlyRegisteredNode() {
        require(nodes[msg.sender].owner != address(0), "VIBInfrastructurePool: node not registered");
        _;
    }

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBInfrastructurePool: invalid token");
        vibeToken = IERC20(_vibeToken);
    }

    // ========== 外部函数 ==========

    /**
     * @notice 接收资金（从VIBEToken的ecosystemFundContract）
     */
    function receiveFunds(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        totalFundsReceived += amount;
        emit FundsReceived(amount, msg.sender);
    }

    /**
     * @notice 注册节点
     * @param serviceType 主要服务类型
     * @param capacity 容量 (GB)
     * @param endpoint 节点端点
     */
    function registerNode(
        ServiceType serviceType,
        uint256 capacity,
        string calldata endpoint
    ) external whenNotPaused returns (bool) {
        require(capacity > 0, "VIBInfrastructurePool: invalid capacity");
        require(nodes[msg.sender].owner == address(0), "VIBInfrastructurePool: already registered");
        require(bytes(endpoint).length > 0, "VIBInfrastructurePool: invalid endpoint");

        nodes[msg.sender] = NodeInfo({
            owner: msg.sender,
            primaryService: serviceType,
            capacity: capacity,
            registeredAt: block.timestamp,
            isActive: true,
            totalServices: 0,
            totalReward: 0,
            endpoint: endpoint
        });

        nodeCount++;

        emit NodeRegistered(msg.sender, serviceType, capacity, endpoint);
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
     * @param dataAmount 数据量（GB）或次数
     * @param duration 服务时长（秒，仅存储用）
     * @param qualityScore 质量评分 (5000-20000)
     * @param serviceHash 服务哈希
     * @return serviceId 服务ID
     */
    function recordService(
        address node,
        ServiceType serviceType,
        uint256 dataAmount,
        uint256 duration,
        uint256 qualityScore,
        bytes32 serviceHash
    ) external onlyAuthorizedAssessor whenNotPaused returns (bytes32 serviceId) {
        require(nodes[node].owner != address(0), "VIBInfrastructurePool: node not registered");
        require(nodes[node].isActive, "VIBInfrastructurePool: node not active");
        require(dataAmount > 0, "VIBInfrastructurePool: invalid data amount");

        // 验证因子范围
        require(qualityScore >= 5000 && qualityScore <= 20000, "VIBInfrastructurePool: invalid quality");

        serviceCount++;
        serviceId = keccak256(abi.encodePacked(
            node,
            serviceType,
            dataAmount,
            block.timestamp,
            serviceCount
        ));

        // 计算基础奖励
        uint256 baseReward = _calculateBaseReward(serviceType, dataAmount, duration);

        // 计算最终奖励（质量因子）
        uint256 finalReward = (baseReward * qualityScore) / PRECISION;

        // 确保在范围内
        (uint256 minReward, uint256 maxReward) = _getRewardRange(serviceType, dataAmount, duration);
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

        // 检查合约余额
        uint256 balance = vibeToken.balanceOf(address(this));
        if (finalReward > balance) {
            finalReward = balance; // 限制为可用余额
        }

        // 存储服务记录
        serviceRecords[serviceId] = ServiceRecord({
            node: node,
            serviceType: serviceType,
            dataAmount: dataAmount,
            duration: duration,
            qualityScore: qualityScore,
            baseReward: baseReward,
            finalReward: finalReward,
            timestamp: block.timestamp,
            claimed: false,
            serviceHash: serviceHash
        });

        // 更新节点统计
        nodes[node].totalServices++;

        emit ServiceRecorded(serviceId, node, serviceType, dataAmount, finalReward);
    }

    /**
     * @notice 领取奖励
     */
    function claimReward(bytes32 serviceId) external nonReentrant whenNotPaused {
        ServiceRecord storage record = serviceRecords[serviceId];

        require(record.node == msg.sender, "VIBInfrastructurePool: not service provider");
        require(record.finalReward > 0, "VIBInfrastructurePool: no reward");
        require(!record.claimed, "VIBInfrastructurePool: already claimed");

        record.claimed = true;
        uint256 reward = record.finalReward;

        nodeTotalRewards[msg.sender] += reward;
        nodes[msg.sender].totalReward += reward;
        totalRewardsDistributed += reward;

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

        require(totalReward > 0, "VIBInfrastructurePool: no rewards to claim");

        nodeTotalRewards[msg.sender] += totalReward;
        nodes[msg.sender].totalReward += totalReward;
        totalRewardsDistributed += totalReward;

        vibeToken.safeTransfer(msg.sender, totalReward);
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
        ServiceType serviceType,
        uint256 dataAmount,
        uint256 duration,
        uint256 qualityScore
    ) external pure returns (uint256) {
        uint256 baseReward = _calculateBaseReward(serviceType, dataAmount, duration);
        uint256 finalReward = (baseReward * qualityScore) / PRECISION;

        (uint256 minReward, uint256 maxReward) = _getRewardRange(serviceType, dataAmount, duration);
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

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

    // ========== 管理函数 ==========

    /**
     * @notice 设置授权评估者
     */
    function setAuthorizedAssessor(address assessor, bool authorized) external onlyOwner {
        authorizedAssessors[assessor] = authorized;
        emit AssessorUpdated(assessor, authorized);
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBInfrastructurePool: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBInfrastructurePool: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 计算基础奖励
     */
    function _calculateBaseReward(
        ServiceType serviceType,
        uint256 dataAmount,
        uint256 duration
    ) internal pure returns (uint256) {
        if (serviceType == ServiceType.IPFS_STORAGE) {
            // IPFS存储: 0.1 VIBE/GB/天
            uint256 days_ = duration / 86400;
            if (days_ == 0) days_ = 1;
            return (IPFS_STORAGE_MIN * dataAmount * days_);
        } else if (serviceType == ServiceType.DATA_RELAY) {
            // 数据中继: 0.01 VIBE/GB
            return (RELAY_MIN * dataAmount);
        } else {
            // 验证服务: 0.05 VIBE/次
            return (VERIFICATION_MIN * dataAmount);
        }
    }

    /**
     * @notice 获取奖励范围
     */
    function _getRewardRange(
        ServiceType serviceType,
        uint256 dataAmount,
        uint256 duration
    ) internal pure returns (uint256 minReward, uint256 maxReward) {
        if (serviceType == ServiceType.IPFS_STORAGE) {
            uint256 days_ = duration / 86400;
            if (days_ == 0) days_ = 1;
            return (IPFS_STORAGE_MIN * dataAmount * days_, IPFS_STORAGE_MAX * dataAmount * days_);
        } else if (serviceType == ServiceType.DATA_RELAY) {
            return (RELAY_MIN * dataAmount, RELAY_MAX * dataAmount);
        } else {
            return (VERIFICATION_MIN * dataAmount, VERIFICATION_MAX * dataAmount);
        }
    }
}
