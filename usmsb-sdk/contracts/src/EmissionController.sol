// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title EmissionController
 * @notice 激励池分配控制器 - 白皮书修复
 * @dev 根据白皮书4.2.3节，激励池63%分配如下：
 *      - 质押激励: 40%
 *      - 生态激励: 25% (其中节点40%/开发者35%/建设者25%)
 *      - 产出激励: 13% (VIBOutputReward)
 *      - 治理激励: 12%
 *      - 储备基金: 10%
 *
 * 释放规则: 按5年线性释放
 */
contract EmissionController is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 分配比例（白皮书4.2.3节）
    uint256 public constant STAKING_RATIO = 4000;     // 40%
    uint256 public constant ECOSYSTEM_RATIO = 2500;  // 25%
    uint256 public constant OUTPUT_RATIO = 1300;     // 13% - 产出激励
    uint256 public constant GOVERNANCE_RATIO = 1200; // 12%
    uint256 public constant RESERVE_RATIO = 1000;     // 10%

    // 释放周期（5年线性释放）
    uint256 public constant RELEASE_PERIOD = 5 * 365 days;

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice 质押奖励池地址
    address public stakingRewardPool;

    /// @notice 生态激励池地址
    address public ecosystemPool;

    /// @notice 产出激励池地址（白皮书修复: 13%）
    address public outputRewardPool;

    /// @notice 治理奖励池地址
    address public governanceRewardPool;

    /// @notice 储备基金地址
    address public reservePool;

    /// @notice 释放开始时间
    uint256 public startTime;

    /// @notice 已释放总量
    uint256 public totalReleased;

    /// @notice 各池已分配数量
    mapping(address => uint256) public poolAllocated;

    // ========== 事件 ==========

    event DistributionTriggered(
        uint256 totalAmount,
        uint256 stakingAmount,
        uint256 ecosystemAmount,
        uint256 outputAmount,
        uint256 governanceAmount,
        uint256 reserveAmount
    );

    event PoolAddressesUpdated(
        address stakingPool,
        address ecosystemPool,
        address outputPool,
        address governancePool,
        address reservePool
    );

    // ========== 构造函数 ==========

    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "EmissionController: invalid token");
        vibeToken = IERC20(_vibeToken);
        startTime = block.timestamp;
    }

    // ========== 设置函数 ==========

    /**
     * @notice 设置各激励池地址
     * @param _staking 质押奖励池
     * @param _ecosystem 生态激励池
     * @param _output 产出激励池 (白皮书修复: 13%)
     * @param _governance 治理奖励池
     * @param _reserve 储备基金
     */
    function setPoolAddresses(
        address _staking,
        address _ecosystem,
        address _output,
        address _governance,
        address _reserve
    ) external onlyOwner {
        require(_staking != address(0), "EmissionController: invalid staking pool");
        require(_ecosystem != address(0), "EmissionController: invalid ecosystem pool");
        require(_output != address(0), "EmissionController: invalid output pool");
        require(_governance != address(0), "EmissionController: invalid governance pool");
        require(_reserve != address(0), "EmissionController: invalid reserve pool");

        stakingRewardPool = _staking;
        ecosystemPool = _ecosystem;
        outputRewardPool = _output;
        governanceRewardPool = _governance;
        reservePool = _reserve;

        emit PoolAddressesUpdated(
            _staking,
            _ecosystem,
            _output,
            _governance
        );
    }

    // ========== 分配函数 ==========

    /**
     * @notice 触发激励分配（白皮书修复: 按比例分配到各池）
     * @dev 根据白皮书4.2.3节:
     *      - 质押激励: 40%
     *      - 生态激励: 25% (VIBEcosystemPool)
     *      - 产出激励: 13% (VIBOutputReward) - 新增
     *      - 治理激励: 12%
     *      - 储备基金: 10%
     */
    function distribute() external nonReentrant {
        uint256 balance = vibeToken.balanceOf(address(this));
        require(balance > 0, "EmissionController: no balance to distribute");

        // 计算可释放数量（5年线性释放）
        uint256 elapsed = block.timestamp - startTime;
        if (elapsed > RELEASE_PERIOD) {
            elapsed = RELEASE_PERIOD;
        }

        // 计算本轮可释放数量
        uint256 totalSupply = 630_000_000 * 10**18; // 6.3亿
        uint256 totalToRelease = (totalSupply * elapsed) / RELEASE_PERIOD;
        uint256 releasable = totalToRelease - totalReleased;

        if (releasable > balance) {
            releasable = balance;
        }

        require(releasable > 0, "EmissionController: nothing to release");

        // 计算各池分配数量（白皮书比例）
        uint256 stakingAmount = (releasable * STAKING_RATIO) / PRECISION;
        uint256 ecosystemAmount = (releasable * ECOSYSTEM_RATIO) / PRECISION;
        uint256 outputAmount = (releasable * OUTPUT_RATIO) / PRECISION;      // 13%
        uint256 governanceAmount = (releasable * GOVERNANCE_RATIO) / PRECISION;
        uint256 reserveAmount = (releasable * RESERVE_RATIO) / PRECISION;

        // 分配到各池
        if (stakingAmount > 0 && stakingRewardPool != address(0)) {
            vibeToken.safeTransfer(stakingRewardPool, stakingAmount);
            poolAllocated[stakingRewardPool] += stakingAmount;
        }

        if (ecosystemAmount > 0 && ecosystemPool != address(0)) {
            vibeToken.safeTransfer(ecosystemPool, ecosystemAmount);
            poolAllocated[ecosystemPool] += ecosystemAmount;
        }

        // 白皮书修复: 产出激励分配到VIBOutputReward (13%)
        if (outputAmount > 0 && outputRewardPool != address(0)) {
            vibeToken.safeTransfer(outputRewardPool, outputAmount);
            poolAllocated[outputRewardPool] += outputAmount;
            
            // 调用VIBOutputReward的receiveDailyPool函数
            (bool success, ) = outputRewardPool.call(
                abi.encodeWithSignature("receiveDailyPool(uint256)", outputAmount)
            );
            // 不强制要求成功，因为VIBOutputReward可能没有实现该函数
        }

        if (governanceAmount > 0 && governanceRewardPool != address(0)) {
            vibeToken.safeTransfer(governanceRewardPool, governanceAmount);
            poolAllocated[governanceRewardPool] += governanceAmount;
        }

        if (reserveAmount > 0 && reservePool != address(0)) {
            vibeToken.safeTransfer(reservePool, reserveAmount);
            poolAllocated[reservePool] += reserveAmount;
        }

        totalReleased += releasable;

        emit DistributionTriggered(
            releasable,
            stakingAmount,
            ecosystemAmount,
            outputAmount,
            governanceAmount,
            reserveAmount
        );
    }

    /**
     * @notice 紧急提取（仅owner，7天时间锁）
     */
    uint256 public pendingEmergencyAmount;
    uint256 public emergencyAvailableTime;

    function initiateEmergencyWithdraw(uint256 amount) external onlyOwner {
        require(amount > 0, "EmissionController: invalid amount");
        require(amount <= vibeToken.balanceOf(address(this)), "EmissionController: insufficient balance");
        
        pendingEmergencyAmount = amount;
        emergencyAvailableTime = block.timestamp + 7 days;
    }

    function executeEmergencyWithdraw() external onlyOwner {
        require(block.timestamp >= emergencyAvailableTime, "EmissionController: timelock not expired");
        require(pendingEmergencyAmount > 0, "EmissionController: no pending withdraw");
        
        uint256 amount = pendingEmergencyAmount;
        pendingEmergencyAmount = 0;
        emergencyAvailableTime = 0;
        
        vibeToken.safeTransfer(owner(), amount);
    }

    // ========== 查询函数 ==========

    /**
     * @notice 获取当前可释放数量
     */
    function getReleasableAmount() external view returns (uint256) {
        uint256 balance = vibeToken.balanceOf(address(this));
        
        uint256 elapsed = block.timestamp - startTime;
        if (elapsed > RELEASE_PERIOD) {
            elapsed = RELEASE_PERIOD;
        }

        uint256 totalSupply = 630_000_000 * 10**18;
        uint256 totalToRelease = (totalSupply * elapsed) / RELEASE_PERIOD;
        uint256 releasable = totalToRelease - totalReleased;

        if (releasable > balance) {
            releasable = balance;
        }

        return releasable;
    }

    /**
     * @notice 获取各池分配比例
     */
    function getDistributionRatios() external pure returns (
        uint256 stakingRatio,
        uint256 ecosystemRatio,
        uint256 outputRatio,
        uint256 governanceRatio,
        uint256 reserveRatio
    ) {
        return (
            STAKING_RATIO,
            ECOSYSTEM_RATIO,
            OUTPUT_RATIO,
            GOVERNANCE_RATIO,
            RESERVE_RATIO
        );
    }
}
