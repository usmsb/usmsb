// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBBuilderReward
 * @notice 建设者激励合约 - 完全去中心化自动分配
 * @dev 实现白皮书承诺的生态建设激励：
 *      触发条件：社区贡献/任务完成/活动参与
 *
 * 激励类型:
 * - 社区贡献: 按贡献积分评估
 * - 任务完成: 按任务难度评估
 * - 活动参与: 按参与度评估
 *
 * 完全去中心化：奖励由预言机或自动化系统触发，不需要人工干预
 */
contract VIBBuilderReward is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 建设类型奖励范围（单位：VIBE，精度10^18）
    uint256 public constant COMMUNITY_MIN = 1 * 10**18;      // 1 VIBE
    uint256 public constant COMMUNITY_MAX = 50 * 10**18;     // 50 VIBE
    uint256 public constant TASK_MIN = 5 * 10**18;           // 5 VIBE
    uint256 public constant TASK_MAX = 100 * 10**18;         // 100 VIBE
    uint256 public constant EVENT_MIN = 1 * 10**18;          // 1 VIBE
    uint256 public constant EVENT_MAX = 30 * 10**18;         // 30 VIBE

    // 建设类型
    enum BuilderType {
        COMMUNITY_CONTRIBUTION,  // 社区贡献
        TASK_COMPLETION,         // 任务完成
        EVENT_PARTICIPATION      // 活动参与
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 已授权的评估者（预言机/自动化系统）
    mapping(address => bool) public authorizedAssessors;

    /// @notice 建设计录
    mapping(bytes32 => BuilderRecord) public builderRecords;

    /// @notice 建设数量
    uint256 public builderCount;

    /// @notice 建设者总奖励
    mapping(address => uint256) public builderTotalRewards;

    /// @notice 建设者贡献积分
    mapping(address => uint256) public builderPoints;

    /// @notice 已发放总奖励
    uint256 public totalRewardsDistributed;

    /// @notice 建设者数量
    uint256 public builderCountUnique;

    /// @notice 是否为已注册建设者
    mapping(address => bool) public isBuilder;

    // ========== 结构体 ==========

    struct BuilderRecord {
        address builder;            // 建设者地址
        BuilderType builderType;    // 建设类型
        uint256 baseReward;         // 基础奖励
        uint256 qualityFactor;      // 质量因子
        uint256 finalReward;        // 最终奖励
        uint256 timestamp;          // 时间戳
        bool claimed;               // 是否已领取
        bytes32 recordHash;         // 记录哈希
        string metadata;            // 元数据
    }

    // ========== 事件 ==========

    event BuilderRegistered(address indexed builder);
    event BuilderRecorded(
        bytes32 indexed recordId,
        address indexed builder,
        BuilderType builderType,
        uint256 finalReward
    );
    event RewardClaimed(
        bytes32 indexed recordId,
        address indexed builder,
        uint256 amount
    );
    event AssessorUpdated(address indexed assessor, bool authorized);

    // ========== 修饰符 ==========

    modifier onlyAuthorizedAssessor() {
        require(authorizedAssessors[msg.sender], "VIBBuilderReward: not authorized assessor");
        _;
    }

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBBuilderReward: invalid token");
        vibeToken = IERC20(_vibeToken);
    }

    // ========== 外部函数 ==========

    /**
     * @notice 注册为建设者
     */
    function registerBuilder() external whenNotPaused {
        require(!isBuilder[msg.sender], "VIBBuilderReward: already registered");
        isBuilder[msg.sender] = true;
        builderCountUnique++;
        emit BuilderRegistered(msg.sender);
    }

    /**
     * @notice 记录建设活动并计算奖励（由授权评估者调用）
     * @param builder 建设者地址
     * @param builderType 建设类型
     * @param baseReward 基础奖励
     * @param qualityFactor 质量因子 (5000-20000)
     * @param recordHash 记录哈希
     * @param metadata 元数据
     * @return recordId 记录ID
     */
    function recordBuilderActivity(
        address builder,
        BuilderType builderType,
        uint256 baseReward,
        uint256 qualityFactor,
        bytes32 recordHash,
        string calldata metadata
    ) external onlyAuthorizedAssessor whenNotPaused returns (bytes32 recordId) {
        require(builder != address(0), "VIBBuilderReward: invalid builder");
        require(isBuilder[builder], "VIBBuilderReward: not a registered builder");

        // 验证基础奖励范围
        (uint256 minReward, uint256 maxReward) = _getRewardRange(builderType);
        require(baseReward >= minReward && baseReward <= maxReward, "VIBBuilderReward: reward out of range");

        // 验证因子范围
        require(qualityFactor >= 5000 && qualityFactor <= 20000, "VIBBuilderReward: invalid quality");

        builderCount++;
        recordId = keccak256(abi.encodePacked(
            builder,
            builderType,
            recordHash,
            block.timestamp,
            builderCount
        ));

        // 计算最终奖励
        uint256 finalReward = (baseReward * qualityFactor) / PRECISION;

        // 确保在范围内
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

        // 存储建设记录
        builderRecords[recordId] = BuilderRecord({
            builder: builder,
            builderType: builderType,
            baseReward: baseReward,
            qualityFactor: qualityFactor,
            finalReward: finalReward,
            timestamp: block.timestamp,
            claimed: false,
            recordHash: recordHash,
            metadata: metadata
        });

        // 更新建设者积分
        builderPoints[builder] += finalReward / 10**18;

        emit BuilderRecorded(recordId, builder, builderType, finalReward);
    }

    /**
     * @notice 领取奖励
     */
    function claimReward(bytes32 recordId) external nonReentrant whenNotPaused {
        BuilderRecord storage record = builderRecords[recordId];

        require(record.builder == msg.sender, "VIBBuilderReward: not builder");
        require(record.finalReward > 0, "VIBBuilderReward: no reward");
        require(!record.claimed, "VIBBuilderReward: already claimed");

        record.claimed = true;
        uint256 reward = record.finalReward;

        builderTotalRewards[msg.sender] += reward;
        totalRewardsDistributed += reward;

        vibeToken.safeTransfer(msg.sender, reward);

        emit RewardClaimed(recordId, msg.sender, reward);
    }

    /**
     * @notice 批量领取奖励
     */
    function batchClaimRewards(bytes32[] calldata recordIds) external nonReentrant whenNotPaused {
        uint256 totalReward = 0;

        for (uint256 i = 0; i < recordIds.length; i++) {
            BuilderRecord storage record = builderRecords[recordIds[i]];

            if (record.builder == msg.sender &&
                record.finalReward > 0 &&
                !record.claimed) {
                record.claimed = true;
                totalReward += record.finalReward;
                emit RewardClaimed(recordIds[i], msg.sender, record.finalReward);
            }
        }

        require(totalReward > 0, "VIBBuilderReward: no rewards to claim");

        builderTotalRewards[msg.sender] += totalReward;
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
     * @notice 获取建设记录
     */
    function getBuilderRecord(bytes32 recordId) external view returns (BuilderRecord memory) {
        return builderRecords[recordId];
    }

    /**
     * @notice 获取建设者统计
     */
    function getBuilderStats(address builder) external view returns (
        uint256 totalRewards,
        uint256 points,
        bool registered
    ) {
        return (
            builderTotalRewards[builder],
            builderPoints[builder],
            isBuilder[builder]
        );
    }

    /**
     * @notice 计算预估奖励
     */
    function estimateReward(
        BuilderType builderType,
        uint256 baseReward,
        uint256 qualityFactor
    ) external pure returns (uint256) {
        uint256 finalReward = (baseReward * qualityFactor) / PRECISION;

        (uint256 minReward, uint256 maxReward) = _getRewardRange(builderType);
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBBuilderReward: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBBuilderReward: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 获取奖励范围
     */
    function _getRewardRange(BuilderType builderType) internal pure returns (uint256 minReward, uint256 maxReward) {
        if (builderType == BuilderType.COMMUNITY_CONTRIBUTION) {
            return (COMMUNITY_MIN, COMMUNITY_MAX);
        } else if (builderType == BuilderType.TASK_COMPLETION) {
            return (TASK_MIN, TASK_MAX);
        } else {
            return (EVENT_MIN, EVENT_MAX);
        }
    }
}
