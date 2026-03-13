// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBDevReward
 * @notice 开发者激励合约 - 完全去中心化自动分配
 * @dev 实现白皮书承诺的开发者激励模型：
 *      触发条件：DApp被使用/代码贡献
 *
 * 激励类型:
 * - 代码贡献: 按PR合并/代码量评估
 * - DApp使用: 按交易量/用户数评估
 * - 生态贡献: 按贡献积分评估
 *
 * 完全去中心化：奖励由预言机或自动化系统触发，不需要人工干预
 */
contract VIBDevReward is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 贡献类型奖励范围（单位：VIBE，精度10^18）
    uint256 public constant CODE_CONTRIBUTION_MIN = 5 * 10**18;     // 5 VIBE
    uint256 public constant CODE_CONTRIBUTION_MAX = 500 * 10**18;   // 500 VIBE
    uint256 public constant DAPP_USAGE_MIN = 1 * 10**18;            // 1 VIBE
    uint256 public constant DAPP_USAGE_MAX = 100 * 10**18;          // 100 VIBE
    uint256 public constant ECOSYSTEM_MIN = 10 * 10**18;            // 10 VIBE
    uint256 public constant ECOSYSTEM_MAX = 200 * 10**18;           // 200 VIBE

    // 贡献类型
    enum ContributionType {
        CODE_CONTRIBUTION,   // 代码贡献
        DAPP_USAGE,          // DApp使用奖励
        ECOSYSTEM_BUILDING   // 生态建设
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 已授权的评估者（预言机/自动化系统）
    mapping(address => bool) public authorizedAssessors;

    /// @notice 贡献记录
    mapping(bytes32 => ContributionRecord) public contributionRecords;

    /// @notice 贡献数量
    uint256 public contributionCount;

    /// @notice 开发者总奖励
    mapping(address => uint256) public developerTotalRewards;

    /// @notice 开发者贡献积分
    mapping(address => uint256) public developerPoints;

    /// @notice 已发放总奖励
    uint256 public totalRewardsDistributed;

    /// @notice 开发者数量
    uint256 public developerCount;

    /// @notice 是否为已注册开发者
    mapping(address => bool) public isDeveloper;

    // ========== 结构体 ==========

    struct ContributionRecord {
        address developer;          // 开发者地址
        ContributionType contribType; // 贡献类型
        uint256 baseReward;         // 基础奖励
        uint256 qualityFactor;      // 质量因子
        uint256 impactFactor;       // 影响力因子
        uint256 finalReward;        // 最终奖励
        uint256 timestamp;          // 时间戳
        bool claimed;               // 是否已领取
        bytes32 contribHash;        // 贡献哈希（PR链接/IPFS等）
        string metadata;            // 元数据
    }

    // ========== 事件 ==========

    event DeveloperRegistered(address indexed developer);
    event ContributionRecorded(
        bytes32 indexed contribId,
        address indexed developer,
        ContributionType contribType,
        uint256 finalReward
    );
    event RewardClaimed(
        bytes32 indexed contribId,
        address indexed developer,
        uint256 amount
    );
    event AssessorUpdated(address indexed assessor, bool authorized);

    // ========== 修饰符 ==========

    modifier onlyAuthorizedAssessor() {
        require(authorizedAssessors[msg.sender], "VIBDevReward: not authorized assessor");
        _;
    }

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBDevReward: invalid token");
        vibeToken = IERC20(_vibeToken);
    }

    // ========== 外部函数 ==========

    /**
     * @notice 注册为开发者
     */
    function registerDeveloper() external whenNotPaused {
        require(!isDeveloper[msg.sender], "VIBDevReward: already registered");
        isDeveloper[msg.sender] = true;
        developerCount++;
        emit DeveloperRegistered(msg.sender);
    }

    /**
     * @notice 记录贡献并计算奖励（由授权评估者调用）
     * @param developer 开发者地址
     * @param contribType 贡献类型
     * @param baseReward 基础奖励
     * @param qualityFactor 质量因子 (5000-30000)
     * @param impactFactor 影响力因子 (5000-20000)
     * @param contribHash 贡献哈希
     * @param metadata 元数据
     * @return contribId 贡献ID
     */
    function recordContribution(
        address developer,
        ContributionType contribType,
        uint256 baseReward,
        uint256 qualityFactor,
        uint256 impactFactor,
        bytes32 contribHash,
        string calldata metadata
    ) external onlyAuthorizedAssessor whenNotPaused returns (bytes32 contribId) {
        require(developer != address(0), "VIBDevReward: invalid developer");
        require(isDeveloper[developer], "VIBDevReward: not a registered developer");

        // 验证基础奖励范围
        (uint256 minReward, uint256 maxReward) = _getRewardRange(contribType);
        require(baseReward >= minReward && baseReward <= maxReward, "VIBDevReward: reward out of range");

        // 验证因子范围
        require(qualityFactor >= 5000 && qualityFactor <= 30000, "VIBDevReward: invalid quality");
        require(impactFactor >= 5000 && impactFactor <= 20000, "VIBDevReward: invalid impact");

        contributionCount++;
        contribId = keccak256(abi.encodePacked(
            developer,
            contribType,
            contribHash,
            block.timestamp,
            contributionCount
        ));

        // 计算最终奖励
        // Reward = BaseReward × Quality × Impact / PRECISION^2
        uint256 finalReward = baseReward;
        finalReward = (finalReward * qualityFactor) / PRECISION;
        finalReward = (finalReward * impactFactor) / PRECISION;

        // 确保在范围内
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

        // 存储贡献记录
        contributionRecords[contribId] = ContributionRecord({
            developer: developer,
            contribType: contribType,
            baseReward: baseReward,
            qualityFactor: qualityFactor,
            impactFactor: impactFactor,
            finalReward: finalReward,
            timestamp: block.timestamp,
            claimed: false,
            contribHash: contribHash,
            metadata: metadata
        });

        // 更新开发者积分
        developerPoints[developer] += finalReward / 10**18;

        emit ContributionRecorded(contribId, developer, contribType, finalReward);
    }

    /**
     * @notice 领取奖励
     */
    function claimReward(bytes32 contribId) external nonReentrant whenNotPaused {
        ContributionRecord storage record = contributionRecords[contribId];

        require(record.developer == msg.sender, "VIBDevReward: not contributor");
        require(record.finalReward > 0, "VIBDevReward: no reward");
        require(!record.claimed, "VIBDevReward: already claimed");

        record.claimed = true;
        uint256 reward = record.finalReward;

        developerTotalRewards[msg.sender] += reward;
        totalRewardsDistributed += reward;

        vibeToken.safeTransfer(msg.sender, reward);

        emit RewardClaimed(contribId, msg.sender, reward);
    }

    /**
     * @notice 批量领取奖励
     */
    function batchClaimRewards(bytes32[] calldata contribIds) external nonReentrant whenNotPaused {
        uint256 totalReward = 0;

        for (uint256 i = 0; i < contribIds.length; i++) {
            ContributionRecord storage record = contributionRecords[contribIds[i]];

            if (record.developer == msg.sender &&
                record.finalReward > 0 &&
                !record.claimed) {
                record.claimed = true;
                totalReward += record.finalReward;
                emit RewardClaimed(contribIds[i], msg.sender, record.finalReward);
            }
        }

        require(totalReward > 0, "VIBDevReward: no rewards to claim");

        developerTotalRewards[msg.sender] += totalReward;
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
     * @notice 获取贡献记录
     */
    function getContributionRecord(bytes32 contribId) external view returns (ContributionRecord memory) {
        return contributionRecords[contribId];
    }

    /**
     * @notice 获取开发者统计
     */
    function getDeveloperStats(address developer) external view returns (
        uint256 totalRewards,
        uint256 points,
        bool registered
    ) {
        return (
            developerTotalRewards[developer],
            developerPoints[developer],
            isDeveloper[developer]
        );
    }

    /**
     * @notice 计算预估奖励
     */
    function estimateReward(
        ContributionType contribType,
        uint256 baseReward,
        uint256 qualityFactor,
        uint256 impactFactor
    ) external pure returns (uint256) {
        uint256 finalReward = baseReward;
        finalReward = (finalReward * qualityFactor) / PRECISION;
        finalReward = (finalReward * impactFactor) / PRECISION;

        (uint256 minReward, uint256 maxReward) = _getRewardRange(contribType);
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBDevReward: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBDevReward: not initiated");

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
    function _getRewardRange(ContributionType contribType) internal pure returns (uint256 minReward, uint256 maxReward) {
        if (contribType == ContributionType.CODE_CONTRIBUTION) {
            return (CODE_CONTRIBUTION_MIN, CODE_CONTRIBUTION_MAX);
        } else if (contribType == ContributionType.DAPP_USAGE) {
            return (DAPP_USAGE_MIN, DAPP_USAGE_MAX);
        } else {
            return (ECOSYSTEM_MIN, ECOSYSTEM_MAX);
        }
    }
}
