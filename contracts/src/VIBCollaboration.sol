// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBCollaboration
 * @notice 协作分成合约 - AI-002修复
 * @dev 实现白皮书承诺的协作分成比例：
 *      - 最终产出者: 70%
 *      - 协作贡献者: 20%（按贡献度分配）
 *      - 协作协调者: 10%
 *
 * 完全去中心化：分成由合约自动执行，不需要人工干预
 */
contract VIBCollaboration is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 分成比例（精度10000）
    uint256 public constant PRODUCER_RATIO = 7000;      // 70%
    uint256 public constant CONTRIBUTORS_RATIO = 2000;  // 20%
    uint256 public constant COORDINATOR_RATIO = 1000;   // 10%

    // 协作角色
    enum CollaborationRole {
        FINAL_PRODUCER,   // 最终产出者 - 70%
        CONTRIBUTOR,       // 协作贡献者 - 共享20%
        COORDINATOR        // 协作协调者 - 10%
    }

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice VIBIdentity合约（验证身份）
    address public identityContract;

    /// @notice 协作项目
    mapping(bytes32 => CollaborationProject) public projects;

    /// @notice 项目贡献者列表
    mapping(bytes32 => address[]) public projectContributors;

    /// @notice 项目贡献者权重
    mapping(bytes32 => mapping(address => uint256)) public contributorWeights;

    /// @notice 用户总收入
    mapping(address => uint256) public userTotalIncome;

    /// @notice 项目数量
    uint256 public projectCount;

    // ========== 结构体 ==========

    struct CollaborationProject {
        bytes32 projectId;          // 项目ID
        address finalProducer;      // 最终产出者
        address coordinator;        // 协调者
        uint256 totalRevenue;       // 总收入
        uint256 producerShare;      // 产出者份额
        uint256 contributorsShare;  // 贡献者总份额
        uint256 coordinatorShare;   // 协调者份额
        uint256 createdAt;          // 创建时间
        uint256 distributedAt;      // 分发时间
        bool distributed;           // 是否已分发
        bool finalized;             // 是否已结算
    }

    // ========== 事件 ==========

    event ProjectCreated(
        bytes32 indexed projectId,
        address indexed finalProducer,
        address indexed coordinator
    );

    event ContributorAdded(
        bytes32 indexed projectId,
        address indexed contributor,
        uint256 weight
    );

    event RevenueReceived(
        bytes32 indexed projectId,
        uint256 amount
    );

    event RevenueDistributed(
        bytes32 indexed projectId,
        uint256 producerAmount,
        uint256 contributorsAmount,
        uint256 coordinatorAmount
    );

    event IncomeClaimed(
        bytes32 indexed projectId,
        address indexed user,
        uint256 amount
    );

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _identityContract
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBCollaboration: invalid token");
        vibeToken = IERC20(_vibeToken);
        identityContract = _identityContract;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 创建协作项目
     * @param finalProducer 最终产出者地址
     * @param coordinator 协调者地址
     * @return projectId 项目ID
     */
    function createProject(
        address finalProducer,
        address coordinator
    ) external whenNotPaused returns (bytes32 projectId) {
        require(finalProducer != address(0), "VIBCollaboration: invalid producer");
        require(coordinator != address(0), "VIBCollaboration: invalid coordinator");

        projectCount++;
        projectId = keccak256(abi.encodePacked(
            finalProducer,
            coordinator,
            block.timestamp,
            projectCount
        ));

        projects[projectId] = CollaborationProject({
            projectId: projectId,
            finalProducer: finalProducer,
            coordinator: coordinator,
            totalRevenue: 0,
            producerShare: 0,
            contributorsShare: 0,
            coordinatorShare: 0,
            createdAt: block.timestamp,
            distributedAt: 0,
            distributed: false,
            finalized: false
        });

        emit ProjectCreated(projectId, finalProducer, coordinator);
    }

    /**
     * @notice 添加贡献者
     * @param projectId 项目ID
     * @param contributors 贡献者地址数组
     * @param weights 贡献权重数组（精度10000，总和应为10000）
     */
    function addContributors(
        bytes32 projectId,
        address[] calldata contributors,
        uint256[] calldata weights
    ) external whenNotPaused {
        require(contributors.length == weights.length, "VIBCollaboration: length mismatch");
        require(contributors.length > 0, "VIBCollaboration: empty arrays");

        CollaborationProject storage project = projects[projectId];
        require(project.finalProducer != address(0), "VIBCollaboration: project not found");
        require(!project.distributed, "VIBCollaboration: already distributed");

        // 只有产出者或协调者可以添加贡献者
        require(
            msg.sender == project.finalProducer || msg.sender == project.coordinator || msg.sender == owner(),
            "VIBCollaboration: unauthorized"
        );

        // 验证权重总和
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < weights.length; i++) {
            require(contributors[i] != address(0), "VIBCollaboration: invalid contributor");
            require(weights[i] > 0, "VIBCollaboration: weight must be positive");
            totalWeight += weights[i];
        }
        require(totalWeight <= PRECISION, "VIBCollaboration: weights exceed 100%");

        // 添加贡献者
        for (uint256 i = 0; i < contributors.length; i++) {
            if (contributorWeights[projectId][contributors[i]] == 0) {
                projectContributors[projectId].push(contributors[i]);
            }
            contributorWeights[projectId][contributors[i]] = weights[i];

            emit ContributorAdded(projectId, contributors[i], weights[i]);
        }
    }

    /**
     * @notice 接收收入并分发
     * @param projectId 项目ID
     * @param amount 金额
     */
    function receiveAndDistribute(
        bytes32 projectId,
        uint256 amount
    ) external nonReentrant whenNotPaused {
        CollaborationProject storage project = projects[projectId];
        require(project.finalProducer != address(0), "VIBCollaboration: project not found");
        require(!project.distributed, "VIBCollaboration: already distributed");
        require(amount > 0, "VIBCollaboration: amount must be positive");

        // 转入代币
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        // 计算各份额
        uint256 producerAmount = (amount * PRODUCER_RATIO) / PRECISION;
        uint256 coordinatorAmount = (amount * COORDINATOR_RATIO) / PRECISION;
        uint256 contributorsAmount = amount - producerAmount - coordinatorAmount;

        // 更新项目状态
        project.totalRevenue = amount;
        project.producerShare = producerAmount;
        project.contributorsShare = contributorsAmount;
        project.coordinatorShare = coordinatorAmount;
        project.distributed = true;
        project.distributedAt = block.timestamp;

        // 立即分发
        _distributeShares(projectId);

        emit RevenueReceived(projectId, amount);
        emit RevenueDistributed(projectId, producerAmount, contributorsAmount, coordinatorAmount);
    }

    /**
     * @notice 内部分发函数
     */
    function _distributeShares(bytes32 projectId) internal {
        CollaborationProject storage project = projects[projectId];

        // 分发给产出者
        vibeToken.safeTransfer(project.finalProducer, project.producerShare);
        userTotalIncome[project.finalProducer] += project.producerShare;

        emit IncomeClaimed(projectId, project.finalProducer, project.producerShare);

        // 分发给协调者
        vibeToken.safeTransfer(project.coordinator, project.coordinatorShare);
        userTotalIncome[project.coordinator] += project.coordinatorShare;

        emit IncomeClaimed(projectId, project.coordinator, project.coordinatorShare);

        // 分发给贡献者（按权重）
        address[] storage contributors = projectContributors[projectId];
        uint256 remainingShare = project.contributorsShare;
        uint256 contributorsCount = contributors.length;

        if (contributorsCount > 0) {
            for (uint256 i = 0; i < contributorsCount; i++) {
                address contributor = contributors[i];
                uint256 weight = contributorWeights[projectId][contributor];
                uint256 share;

                if (i == contributorsCount - 1) {
                    // 最后一个贡献者获得剩余份额，避免精度损失
                    share = remainingShare;
                } else {
                    share = (project.contributorsShare * weight) / PRECISION;
                    remainingShare -= share;
                }

                if (share > 0) {
                    vibeToken.safeTransfer(contributor, share);
                    userTotalIncome[contributor] += share;

                    emit IncomeClaimed(projectId, contributor, share);
                }
            }
        }

        project.finalized = true;
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取项目信息
     */
    function getProjectInfo(bytes32 projectId) external view returns (CollaborationProject memory) {
        return projects[projectId];
    }

    /**
     * @notice 获取贡献者列表
     */
    function getContributors(bytes32 projectId) external view returns (address[] memory) {
        return projectContributors[projectId];
    }

    /**
     * @notice 获取贡献者数量
     */
    function getContributorCount(bytes32 projectId) external view returns (uint256) {
        return projectContributors[projectId].length;
    }

    /**
     * @notice 计算预估分成
     */
    function estimateDistribution(uint256 amount)
        external
        pure
        returns (
            uint256 producerAmount,
            uint256 coordinatorAmount,
            uint256 contributorsAmount
        )
    {
        producerAmount = (amount * PRODUCER_RATIO) / PRECISION;
        coordinatorAmount = (amount * COORDINATOR_RATIO) / PRECISION;
        contributorsAmount = amount - producerAmount - coordinatorAmount;
    }

    /**
     * @notice 获取用户总收入
     */
    function getUserTotalIncome(address user) external view returns (uint256) {
        return userTotalIncome[user];
    }

    // ========== 管理函数 ==========

    function setIdentityContract(address _identityContract) external onlyOwner {
        identityContract = _identityContract;
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBCollaboration: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBCollaboration: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }
}
