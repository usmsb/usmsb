// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";
import "@openzeppelin/contracts-upgradeable/security/PausableUpgradeable.sol";

/**
 * @title VIBContributionPoints
 * @notice 贡献积分管理合约（从VIBGovernance提取以减小大小）
 * @dev 修复#1: 拆分合约以符合EVM 24KB限制
 */
contract VIBContributionPoints is Initializable, OwnableUpgradeable, PausableUpgradeable {
    // ========== 常量 ==========

    uint256 public constant MAX_SINGLE_CONTRIBUTION_POINTS = 1000 * 10**18;
    uint256 public constant MAX_MONTHLY_POINTS = 5000 * 10**18;
    uint256 public constant PRODUCTION_WINDOW = 90 days;

    // ========== 贡献类型枚举 ==========

    enum ContributionType {
        CODE_CONTRIBUTION,
        COMMUNITY_BUILDING,
        GOVERNANCE_PARTICIPATION,
        CONTENT_CREATION,
        BUG_REPORTING,
        SECURITY_AUDIT,
        ECOSYSTEM_DEVELOPMENT
    }

    // ========== 结构体 ==========

    struct TimedPoints {
        uint256 points;
        uint256 timestamp;
    }

    struct ContributionRecord {
        address contributor;
        ContributionType contributionType;
        uint256 points;
        uint256 timestamp;
        string evidence;
        bool verified;
        address verifier;
    }

    // ========== 状态变量 ==========

    mapping(address => uint256) public contributionPoints;
    uint256 public totalContributionPoints;

    mapping(address => TimedPoints[]) public userPointsHistory;
    mapping(address => uint256) public lastCleanupTime;

    mapping(ContributionType => uint256) public contributionTypePoints;
    ContributionRecord[] public contributionRecords;
    mapping(address => uint256[]) public userContributionIndices;
    uint256 public pendingContributionsCount;
    mapping(address => bool) public contributionVerifiers;
    mapping(address => mapping(uint256 => uint256)) public monthlyPointsEarned;

    address public governanceContract;

    // ========== 事件 ==========

    event ContributionPointsUpdated(
        address indexed user,
        uint256 oldPoints,
        uint256 newPoints
    );

    event ContributionSubmitted(
        uint256 indexed recordId,
        address indexed contributor,
        ContributionType contributionType,
        uint256 points,
        string evidence
    );

    event ContributionVerified(
        uint256 indexed recordId,
        address indexed contributor,
        uint256 points,
        address indexed verifier
    );

    event ContributionTypePointsUpdated(
        ContributionType indexed contributionType,
        uint256 oldPoints,
        uint256 newPoints
    );

    event ContributionVerifierSet(
        address indexed verifier,
        bool isVerifier
    );

    event GovernanceContractUpdated(address indexed oldAddress, address indexed newAddress);

    // ========== 修饰符 ==========

    modifier onlyGovernance() {
        require(msg.sender == governanceContract || msg.sender == owner(), "Not authorized");
        _;
    }

    // ========== 初始化 ==========

    function initialize() public initializer {
        __Ownable_init();
        __Pausable_init();
    }

    function setGovernanceContract(address _governanceContract) external onlyOwner {
        emit GovernanceContractUpdated(governanceContract, _governanceContract);
        governanceContract = _governanceContract;
    }

    // ========== 核心函数 ==========

    /**
     * @notice 更新用户贡献积分
     */
    function updateContributionPoints(address user, uint256 points) external onlyGovernance {
        require(user != address(0), "Invalid address");
        uint256 oldPoints = contributionPoints[user];
        contributionPoints[user] = points;

        if (points > oldPoints) {
            uint256 addedPoints = points - oldPoints;
            totalContributionPoints += addedPoints;
            _addTimedPoints(user, addedPoints);
        } else if (oldPoints > points) {
            totalContributionPoints -= (oldPoints - points);
        }

        emit ContributionPointsUpdated(user, oldPoints, points);
    }

    /**
     * @notice 获取用户有效贡献积分（90天滚动窗口）
     */
    function getEffectiveContributionPoints(address user) external view returns (uint256) {
        return _getEffectiveContributionPoints(user);
    }

    function _getEffectiveContributionPoints(address user) internal view returns (uint256) {
        TimedPoints[] storage history = userPointsHistory[user];
        uint256 effectivePoints = 0;
        uint256 currentTime = block.timestamp;
        uint256 windowStart = currentTime > PRODUCTION_WINDOW ? currentTime - PRODUCTION_WINDOW : 0;

        for (uint256 i = 0; i < history.length; i++) {
            TimedPoints storage entry = history[i];
            if (entry.timestamp >= windowStart) {
                effectivePoints += entry.points;
            } else if (entry.timestamp > 0) {
                uint256 age = windowStart - entry.timestamp;
                if (age < PRODUCTION_WINDOW * 2) {
                    uint256 decayRate = (age * 100) / (PRODUCTION_WINDOW * 2);
                    // Medium #12 修复: 确保衰减率不超过100，避免负数
                    if (decayRate >= 100) {
                        // 超过100%衰减，不计入
                        continue;
                    }
                    uint256 remainingPoints = (entry.points * (100 - decayRate)) / 100;
                    effectivePoints += remainingPoints;
                }
            }
        }

        uint256 currentPoints = contributionPoints[user];
        if (effectivePoints > currentPoints) {
            effectivePoints = currentPoints;
        }

        return effectivePoints;
    }

    function _addTimedPoints(address user, uint256 points) internal {
        userPointsHistory[user].push(TimedPoints({
            points: points,
            timestamp: block.timestamp
        }));
    }

    /**
     * @notice 清理过期积分记录
     */
    function cleanupExpiredPoints(address user) external {
        TimedPoints[] storage history = userPointsHistory[user];
        uint256 currentTime = block.timestamp;
        uint256 cutoffTime = currentTime > (PRODUCTION_WINDOW * 2) ? currentTime - (PRODUCTION_WINDOW * 2) : 0;

        uint256 writeIndex = 0;
        for (uint256 i = 0; i < history.length; i++) {
            if (history[i].timestamp >= cutoffTime) {
                if (writeIndex != i) {
                    history[writeIndex] = history[i];
                }
                writeIndex++;
            }
        }

        while (history.length > writeIndex) {
            history.pop();
        }

        lastCleanupTime[user] = currentTime;
    }

    // ========== 贡献管理函数 ==========

    function initializeContributionTypes() external onlyOwner {
        contributionTypePoints[ContributionType.CODE_CONTRIBUTION] = 100 * 10**18;
        contributionTypePoints[ContributionType.COMMUNITY_BUILDING] = 50 * 10**18;
        contributionTypePoints[ContributionType.GOVERNANCE_PARTICIPATION] = 20 * 10**18;
        contributionTypePoints[ContributionType.CONTENT_CREATION] = 30 * 10**18;
        contributionTypePoints[ContributionType.BUG_REPORTING] = 80 * 10**18;
        contributionTypePoints[ContributionType.SECURITY_AUDIT] = 200 * 10**18;
        contributionTypePoints[ContributionType.ECOSYSTEM_DEVELOPMENT] = 150 * 10**18;
    }

    function setContributionTypePoints(ContributionType contributionType, uint256 points) external onlyOwner {
        require(points <= MAX_SINGLE_CONTRIBUTION_POINTS, "Points exceed max");
        uint256 oldPoints = contributionTypePoints[contributionType];
        contributionTypePoints[contributionType] = points;
        emit ContributionTypePointsUpdated(contributionType, oldPoints, points);
    }

    function setContributionVerifier(address verifier, bool isVerifier) external onlyOwner {
        require(verifier != address(0), "Invalid address");
        contributionVerifiers[verifier] = isVerifier;
        emit ContributionVerifierSet(verifier, isVerifier);
    }

    function submitContribution(
        ContributionType contributionType,
        uint256 points,
        string calldata evidence
    ) external whenNotPaused returns (uint256) {
        require(points > 0 && points <= MAX_SINGLE_CONTRIBUTION_POINTS, "Invalid points");
        require(bytes(evidence).length > 0, "Evidence required");

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

    function verifyContribution(
        uint256 recordId,
        bool approved,
        uint256 adjustedPoints
    ) external whenNotPaused {
        require(contributionVerifiers[msg.sender], "Not a verifier");
        _verifyContributionInternal(recordId, approved, adjustedPoints);
    }

    function batchVerifyContributions(
        uint256[] calldata recordIds,
        bool[] calldata approvedList,
        uint256[] calldata adjustedPointsList
    ) external whenNotPaused {
        require(contributionVerifiers[msg.sender], "Not a verifier");
        require(
            recordIds.length == approvedList.length && recordIds.length == adjustedPointsList.length,
            "Length mismatch"
        );

        for (uint256 i = 0; i < recordIds.length; i++) {
            _verifyContributionInternal(recordIds[i], approvedList[i], adjustedPointsList[i]);
        }
    }

    function _verifyContributionInternal(
        uint256 recordId,
        bool approved,
        uint256 adjustedPoints
    ) internal {
        require(recordId < contributionRecords.length, "Invalid record id");

        ContributionRecord storage record = contributionRecords[recordId];
        require(!record.verified, "Already verified");

        record.verified = true;
        record.verifier = msg.sender;
        pendingContributionsCount--;

        if (approved) {
            uint256 finalPoints = adjustedPoints > 0 ? adjustedPoints : record.points;
            require(finalPoints <= MAX_SINGLE_CONTRIBUTION_POINTS, "Points exceed max");

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
                totalContributionPoints += allowedPoints;
                _addTimedPoints(record.contributor, allowedPoints);

                emit ContributionPointsUpdated(record.contributor, oldPoints, contributionPoints[record.contributor]);
            }
        }

        emit ContributionVerified(recordId, record.contributor, approved ? record.points : 0, msg.sender);
    }

    // ========== 视图函数 ==========

    function getContributionRecord(uint256 recordId) external view returns (ContributionRecord memory) {
        require(recordId < contributionRecords.length, "Invalid record id");
        return contributionRecords[recordId];
    }

    function getUserContributionCount(address user) external view returns (uint256) {
        return userContributionIndices[user].length;
    }

    function getUserContributionIds(
        address user,
        uint256 offset,
        uint256 limit
    ) external view returns (uint256[] memory) {
        uint256[] storage indices = userContributionIndices[user];
        require(offset < indices.length, "Offset out of bounds");

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

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
