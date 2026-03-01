// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBEcosystemPool
 * @notice 生态激励池协调器 - 完全去中心化自动分配
 * @dev 将EmissionController的30%生态激励自动分配到子池：
 *      - 节点激励: 40% (12% of total) → VIBNodeReward
 *      - 开发者激励: 35% (10.5% of total) → VIBDevReward
 *      - 建设者激励: 25% (7.5% of total) → VIBBuilderReward
 *
 * 完全去中心化：无需人工干预，由预言机/自动化系统触发
 */
contract VIBEcosystemPool is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 子池分配比例
    uint256 public constant NODE_REWARD_RATIO = 4000;      // 40%
    uint256 public constant DEV_REWARD_RATIO = 3500;       // 35%
    uint256 public constant BUILDER_REWARD_RATIO = 2500;   // 25%

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 节点激励合约
    address public nodeRewardContract;

    /// @notice 开发者激励合约
    address public devRewardContract;

    /// @notice 建设者激励合约
    address public builderRewardContract;

    /// @notice EmissionController地址（资金来源）
    address public emissionController;

    /// @notice 已分配总量
    uint256 public totalDistributed;

    /// @notice 分配到节点池的总量
    uint256 public totalNodeDistributed;

    /// @notice 分配到开发者池的总量
    uint256 public totalDevDistributed;

    /// @notice 分配到建设者池的总量
    uint256 public totalBuilderDistributed;

    /// @notice 分配记录
    DistributionRecord[] public distributionRecords;

    // ========== 结构体 ==========

    struct DistributionRecord {
        uint256 amount;
        uint256 nodeAmount;
        uint256 devAmount;
        uint256 builderAmount;
        uint256 timestamp;
        address trigger;
    }

    // ========== 事件 ==========

    event FundsReceived(uint256 amount, address from);
    event FundsDistributed(
        uint256 totalAmount,
        uint256 nodeAmount,
        uint256 devAmount,
        uint256 builderAmount,
        address trigger
    );
    event ContractsUpdated(
        address nodeReward,
        address devReward,
        address builderReward
    );
    event EmissionControllerUpdated(address controller);

    // ========== 修饰符 ==========

    modifier onlyEmissionController() {
        require(
            msg.sender == emissionController || msg.sender == owner(),
            "VIBEcosystemPool: only emission controller"
        );
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _emissionController
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBEcosystemPool: invalid token");
        vibeToken = IERC20(_vibeToken);
        emissionController = _emissionController;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 接收资金并自动分配到子池
     * @param amount 金额
     * @dev 由EmissionController调用，完全自动化
     */
    function receiveAndDistribute(uint256 amount)
        external
        onlyEmissionController
        nonReentrant
        whenNotPaused
    {
        require(amount > 0, "VIBEcosystemPool: amount must be positive");

        // 转入代币
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        emit FundsReceived(amount, msg.sender);

        // 计算各子池分配量
        uint256 nodeAmount = (amount * NODE_REWARD_RATIO) / PRECISION;
        uint256 devAmount = (amount * DEV_REWARD_RATIO) / PRECISION;
        uint256 builderAmount = amount - nodeAmount - devAmount; // 避免精度损失

        // 分配到各子池
        _distributeToPool(nodeRewardContract, nodeAmount);
        _distributeToPool(devRewardContract, devAmount);
        _distributeToPool(builderRewardContract, builderAmount);

        // 更新统计
        totalDistributed += amount;
        totalNodeDistributed += nodeAmount;
        totalDevDistributed += devAmount;
        totalBuilderDistributed += builderAmount;

        // 记录分配
        distributionRecords.push(DistributionRecord({
            amount: amount,
            nodeAmount: nodeAmount,
            devAmount: devAmount,
            builderAmount: builderAmount,
            timestamp: block.timestamp,
            trigger: msg.sender
        }));

        emit FundsDistributed(amount, nodeAmount, devAmount, builderAmount, msg.sender);
    }

    /**
     * @notice 手动触发分配（如果有余额）
     * @dev 任何人都可以调用，Gas补贴由各子池承担
     */
    function triggerDistribution() external nonReentrant whenNotPaused {
        uint256 balance = vibeToken.balanceOf(address(this));
        require(balance > 0, "VIBEcosystemPool: no balance to distribute");

        // 计算各子池分配量
        uint256 nodeAmount = (balance * NODE_REWARD_RATIO) / PRECISION;
        uint256 devAmount = (balance * DEV_REWARD_RATIO) / PRECISION;
        uint256 builderAmount = balance - nodeAmount - devAmount;

        // 分配到各子池
        _distributeToPool(nodeRewardContract, nodeAmount);
        _distributeToPool(devRewardContract, devAmount);
        _distributeToPool(builderRewardContract, builderAmount);

        // 更新统计
        totalDistributed += balance;
        totalNodeDistributed += nodeAmount;
        totalDevDistributed += devAmount;
        totalBuilderDistributed += builderAmount;

        // 记录分配
        distributionRecords.push(DistributionRecord({
            amount: balance,
            nodeAmount: nodeAmount,
            devAmount: devAmount,
            builderAmount: builderAmount,
            timestamp: block.timestamp,
            trigger: msg.sender
        }));

        emit FundsDistributed(balance, nodeAmount, devAmount, builderAmount, msg.sender);
    }

    // ========== 内部函数 ==========

    /**
     * @notice 分配到指定池
     */
    function _distributeToPool(address pool, uint256 amount) internal {
        if (pool != address(0) && amount > 0) {
            vibeToken.safeTransfer(pool, amount);
        }
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置子池合约地址
     */
    function setRewardContracts(
        address _nodeReward,
        address _devReward,
        address _builderReward
    ) external onlyOwner {
        nodeRewardContract = _nodeReward;
        devRewardContract = _devReward;
        builderRewardContract = _builderReward;
        emit ContractsUpdated(_nodeReward, _devReward, _builderReward);
    }

    /**
     * @notice 设置EmissionController
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        emissionController = _emissionController;
        emit EmissionControllerUpdated(_emissionController);
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
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBEcosystemPool: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBEcosystemPool: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取分配记录数量
     */
    function getDistributionRecordCount() external view returns (uint256) {
        return distributionRecords.length;
    }

    /**
     * @notice 获取分配记录
     */
    function getDistributionRecord(uint256 index) external view returns (DistributionRecord memory) {
        require(index < distributionRecords.length, "VIBEcosystemPool: index out of bounds");
        return distributionRecords[index];
    }

    /**
     * @notice 获取合约余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    /**
     * @notice 预估分配
     */
    function estimateDistribution(uint256 amount) external pure returns (
        uint256 nodeAmount,
        uint256 devAmount,
        uint256 builderAmount
    ) {
        nodeAmount = (amount * NODE_REWARD_RATIO) / PRECISION;
        devAmount = (amount * DEV_REWARD_RATIO) / PRECISION;
        builderAmount = amount - nodeAmount - devAmount;
    }
}
