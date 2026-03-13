// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title IVIBStakingForVE
 * @notice VIBStaking接口，用于获取质押信息
 */
interface IVIBStakingForVE {
    function getStakeInfo(address user) external view returns (
        uint256 amount,
        uint256 startTime,
        uint256 unlockTime,
        uint256 lockPeriodIndex,
        uint256 tier,
        uint256 pendingReward,
        uint256 rewardDebt,
        bool isActive
    );
}

/**
 * @title IVIBOutputReward
 * @notice VIBOutputReward接口
 */
interface IVIBOutputReward {
    function getUserTotalRewards(address user) external view returns (uint256);
}

/**
 * @title VIBVEPoints
 * @notice VE积分系统 - AI-003修复
 * @dev 实现白皮书承诺的VE(Voting Escrow)积分系统：
 *      - 通过产出获得积分，权重是质押的2倍
 *      - 积分不可转让，随贡献衰减
 *      - 用于治理投票和收益加成
 *
 * 核心公式:
 *   VE积分 = 产出奖励 × 产出系数 + 质押量 × 时长系数
 *   其中产出系数 = 2.0 (质押的2倍权重)
 */
contract VIBVEPoints is Ownable, Pausable, ReentrancyGuard {
    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    /// @notice 产出权重系数 (200% = 2x质押权重)
    uint256 public constant OUTPUT_WEIGHT_MULTIPLIER = 20000;

    /// @notice 质押权重系数 (100%)
    uint256 public constant STAKE_WEIGHT_MULTIPLIER = 10000;

    /// @notice 时间权重系数 (每小时)
    uint256 public constant TIME_WEIGHT_PER_HOUR = 4; // 0.04% per hour

    /// @notice 衰减周期 (30天)
    uint256 public constant DECAY_PERIOD = 30 days;

    /// @notice 衰减率 (每月衰减10%)
    uint256 public constant DECAY_RATE = 1000; // 10%

    /// @notice 最小产出奖励金额 (1 VIBE)
    uint256 public constant MIN_OUTPUT_REWARD = 1 * 10**18;

    // ========== 状态变量 ==========

    /// @notice VIBStaking合约地址
    address public stakingContract;

    /// @notice VIBOutputReward合约地址
    address public outputRewardContract;

    /// @notice VIBGovernance合约地址 (授权调用)
    address public governanceContract;

    /// @notice 用户VE积分
    mapping(address => uint256) public vePoints;

    /// @notice 用户产出积分（来自产出奖励）
    mapping(address => uint256) public outputPoints;

    /// @notice 用户质押积分（来自质押）
    mapping(address => uint256) public stakePoints;

    /// @notice 上次更新时间
    mapping(address => uint256) public lastUpdateTime;

    /// @notice 上次衰减时间
    mapping(address => uint256) public lastDecayTime;

    /// @notice 累计获得的总VE积分
    mapping(address => uint256) public totalVePointsEarned;

    /// @notice 全局总VE积分
    uint256 public globalTotalVePoints;

    /// @notice 已注册的产出奖励记录器
    mapping(address => bool) public registeredOutputLoggers;

    // ========== 结构体 ==========

    struct VEPointInfo {
        uint256 vePoints;           // 当前VE积分
        uint256 outputPoints;       // 产出积分
        uint256 stakePoints;        // 质押积分
        uint256 lastUpdateTime;     // 上次更新时间
        uint256 lastDecayTime;      // 上次衰减时间
        uint256 totalEarned;        // 累计获得
    }

    // ========== 事件 ==========

    event VEPointsEarned(
        address indexed user,
        uint256 amount,
        string source // "output", "stake", "time_bonus"
    );

    event VEPointsDecayed(
        address indexed user,
        uint256 beforeDecay,
        uint256 afterDecay
    );

    event VEPointsUpdated(
        address indexed user,
        uint256 newTotal,
        uint256 outputComponent,
        uint256 stakeComponent
    );

    event OutputLoggerUpdated(address indexed logger, bool registered);
    event ContractsUpdated(
        address indexed stakingContract,
        address indexed outputRewardContract,
        address indexed governanceContract
    );

    // ========== 修饰符 ==========

    modifier onlyGovernance() {
        require(msg.sender == governanceContract, "VIBVEPoints: only governance");
        _;
    }

    modifier onlyOutputLogger() {
        require(registeredOutputLoggers[msg.sender], "VIBVEPoints: not output logger");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _stakingContract,
        address _outputRewardContract,
        address _governanceContract
    ) Ownable(msg.sender) {
        stakingContract = _stakingContract;
        outputRewardContract = _outputRewardContract;
        governanceContract = _governanceContract;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 记录产出奖励并计算VE积分
     * @param user 用户地址
     * @param rewardAmount 奖励金额
     * @dev 由VIBOutputReward或其他授权合约调用
     */
    function recordOutputReward(address user, uint256 rewardAmount)
        external
        onlyOutputLogger
        whenNotPaused
    {
        require(user != address(0), "VIBVEPoints: invalid user");
        require(rewardAmount >= MIN_OUTPUT_REWARD, "VIBVEPoints: reward too small");

        // 先应用衰减
        _applyDecay(user);

        // 计算产出积分: 奖励金额 × 产出权重系数 / 精度
        // 产出权重是质押的2倍，所以用OUTPUT_WEIGHT_MULTIPLIER (20000)
        uint256 newOutputPoints = (rewardAmount * OUTPUT_WEIGHT_MULTIPLIER) / PRECISION;

        outputPoints[user] += newOutputPoints;
        totalVePointsEarned[user] += newOutputPoints;
        globalTotalVePoints += newOutputPoints;

        _updateVePoints(user);

        emit VEPointsEarned(user, newOutputPoints, "output");
    }

    /**
     * @notice 更新质押积分
     * @param user 用户地址
     * @dev 由VIBStaking或其他授权合约调用
     */
    function updateStakePoints(address user) external whenNotPaused {
        require(
            msg.sender == stakingContract || msg.sender == owner(),
            "VIBVEPoints: unauthorized"
        );

        // 先应用衰减
        _applyDecay(user);

        // 从质押合约获取质押信息
        uint256 newStakePoints = _calculateStakePoints(user);

        // 更新质押积分
        uint256 oldStakePoints = stakePoints[user];
        stakePoints[user] = newStakePoints;

        // 更新全局总积分（只计算增量）
        if (newStakePoints > oldStakePoints) {
            globalTotalVePoints += (newStakePoints - oldStakePoints);
        } else if (oldStakePoints > newStakePoints) {
            globalTotalVePoints -= (oldStakePoints - newStakePoints);
        }

        _updateVePoints(user);

        emit VEPointsUpdated(user, vePoints[user], outputPoints[user], stakePoints[user]);
    }

    /**
     * @notice 手动触发衰减
     * @param user 用户地址
     */
    function triggerDecay(address user) external whenNotPaused {
        _applyDecay(user);
    }

    /**
     * @notice 批量触发衰减
     * @param users 用户地址数组
     */
    function batchTriggerDecay(address[] calldata users) external whenNotPaused {
        for (uint256 i = 0; i < users.length; i++) {
            _applyDecay(users[i]);
        }
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取用户VE积分信息
     */
    function getVEPointInfo(address user) external view returns (VEPointInfo memory) {
        return VEPointInfo({
            vePoints: vePoints[user],
            outputPoints: outputPoints[user],
            stakePoints: stakePoints[user],
            lastUpdateTime: lastUpdateTime[user],
            lastDecayTime: lastDecayTime[user],
            totalEarned: totalVePointsEarned[user]
        });
    }

    /**
     * @notice 获取用户当前VE积分（含待衰减）
     */
    function getCurrentVePoints(address user) external view returns (uint256) {
        uint256 currentPoints = vePoints[user];

        // 计算待衰减
        if (lastDecayTime[user] > 0) {
            uint256 timeSinceLastDecay = block.timestamp - lastDecayTime[user];
            uint256 decayPeriods = timeSinceLastDecay / DECAY_PERIOD;

            if (decayPeriods > 0) {
                for (uint256 i = 0; i < decayPeriods && currentPoints > 0; i++) {
                    currentPoints = (currentPoints * (PRECISION - DECAY_RATE)) / PRECISION;
                }
            }
        }

        return currentPoints;
    }

    /**
     * @notice 获取用户投票权重
     * @dev 用于治理合约调用，返回带精度的权重
     */
    function getVotingWeight(address user) external view returns (uint256) {
        return this.getCurrentVePoints(user);
    }

    /**
     * @notice 获取全球总VE积分
     */
    function getGlobalTotalVePoints() external view returns (uint256) {
        return globalTotalVePoints;
    }

    /**
     * @notice 预估产出奖励能获得的VE积分
     */
    function estimateOutputVePoints(uint256 rewardAmount) external pure returns (uint256) {
        return (rewardAmount * OUTPUT_WEIGHT_MULTIPLIER) / PRECISION;
    }

    /**
     * @notice 预估质押能获得的VE积分
     */
    function estimateStakeVePoints(uint256 amount, uint256 lockPeriodDays)
        external
        pure
        returns (uint256)
    {
        uint256 timeMultiplier = _getTimeMultiplier(lockPeriodDays);
        return (amount * STAKE_WEIGHT_MULTIPLIER * timeMultiplier) / (PRECISION * 100);
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置产出奖励记录器
     */
    function setOutputLogger(address logger, bool registered) external onlyOwner {
        registeredOutputLoggers[logger] = registered;
        emit OutputLoggerUpdated(logger, registered);
    }

    /**
     * @notice 设置合约地址
     */
    function setContracts(
        address _stakingContract,
        address _outputRewardContract,
        address _governanceContract
    ) external onlyOwner {
        stakingContract = _stakingContract;
        outputRewardContract = _outputRewardContract;
        governanceContract = _governanceContract;
        emit ContractsUpdated(_stakingContract, _outputRewardContract, _governanceContract);
    }

    /**
     * @notice 治理合约可以手动调整用户积分（紧急情况）
     */
    function governanceAdjustPoints(
        address user,
        int256 deltaOutput,
        int256 deltaStake
    ) external onlyGovernance {
        if (deltaOutput > 0) {
            outputPoints[user] += uint256(deltaOutput);
            globalTotalVePoints += uint256(deltaOutput);
        } else if (deltaOutput < 0) {
            uint256 decrease = uint256(-deltaOutput);
            if (outputPoints[user] >= decrease) {
                outputPoints[user] -= decrease;
            } else {
                outputPoints[user] = 0;
            }
            if (globalTotalVePoints >= decrease) {
                globalTotalVePoints -= decrease;
            }
        }

        if (deltaStake > 0) {
            stakePoints[user] += uint256(deltaStake);
            globalTotalVePoints += uint256(deltaStake);
        } else if (deltaStake < 0) {
            uint256 decrease = uint256(-deltaStake);
            if (stakePoints[user] >= decrease) {
                stakePoints[user] -= decrease;
            } else {
                stakePoints[user] = 0;
            }
            if (globalTotalVePoints >= decrease) {
                globalTotalVePoints -= decrease;
            }
        }

        _updateVePoints(user);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // ========== 内部函数 ==========

    /**
     * @notice 应用衰减
     */
    function _applyDecay(address user) internal {
        uint256 currentPoints = vePoints[user];

        if (currentPoints == 0) {
            lastDecayTime[user] = block.timestamp;
            return;
        }

        uint256 lastDecay = lastDecayTime[user];
        if (lastDecay == 0) {
            lastDecayTime[user] = block.timestamp;
            return;
        }

        uint256 timeSinceLastDecay = block.timestamp - lastDecay;
        uint256 decayPeriods = timeSinceLastDecay / DECAY_PERIOD;

        if (decayPeriods == 0) {
            return;
        }

        uint256 beforeDecay = currentPoints;

        // 应用衰减（每个周期衰减10%）
        for (uint256 i = 0; i < decayPeriods && currentPoints > 0; i++) {
            currentPoints = (currentPoints * (PRECISION - DECAY_RATE)) / PRECISION;
        }

        // 更新全局总积分
        if (globalTotalVePoints >= (beforeDecay - currentPoints)) {
            globalTotalVePoints -= (beforeDecay - currentPoints);
        }

        vePoints[user] = currentPoints;
        lastDecayTime[user] = block.timestamp;

        // 同比例衰减产出积分和质押积分
        if (beforeDecay > 0) {
            uint256 decayRatio = (currentPoints * PRECISION) / beforeDecay;
            outputPoints[user] = (outputPoints[user] * decayRatio) / PRECISION;
            stakePoints[user] = (stakePoints[user] * decayRatio) / PRECISION;
        }

        emit VEPointsDecayed(user, beforeDecay, currentPoints);
    }

    /**
     * @notice 更新VE积分
     */
    function _updateVePoints(address user) internal {
        vePoints[user] = outputPoints[user] + stakePoints[user];
        lastUpdateTime[user] = block.timestamp;

        emit VEPointsUpdated(user, vePoints[user], outputPoints[user], stakePoints[user]);
    }

    /**
     * @notice 计算质押积分
     */
    function _calculateStakePoints(address user) internal view returns (uint256) {
        if (stakingContract == address(0)) {
            return 0;
        }

        try IVIBStakingForVE(stakingContract).getStakeInfo(user) returns (
            uint256 amount,
            uint256 startTime,
            uint256 unlockTime,
            uint256 lockPeriodIndex,
            uint256 tier,
            uint256 pendingReward,
            uint256 rewardDebt,
            bool isActive
        ) {
            if (!isActive || amount == 0) {
                return 0;
            }

            // 计算时间乘数
            uint256 lockPeriodDays = 0;
            if (lockPeriodIndex == 1) lockPeriodDays = 30;
            else if (lockPeriodIndex == 2) lockPeriodDays = 90;
            else if (lockPeriodIndex == 3) lockPeriodDays = 180;
            else if (lockPeriodIndex == 4) lockPeriodDays = 365;

            uint256 timeMultiplier = _getTimeMultiplier(lockPeriodDays);

            // 质押积分 = 金额 × 质押权重 × 时间乘数 / 精度
            return (amount * STAKE_WEIGHT_MULTIPLIER * timeMultiplier) / (PRECISION * 100);
        } catch {
            return 0;
        }
    }

    /**
     * @notice 获取时间乘数
     * @param lockPeriodDays 锁仓天数
     * @return 时间乘数 (100 = 1x, 150 = 1.5x, 200 = 2x)
     */
    function _getTimeMultiplier(uint256 lockPeriodDays) internal pure returns (uint256) {
        if (lockPeriodDays >= 365) return 200;  // 1年: 2x
        if (lockPeriodDays >= 180) return 150;  // 6月: 1.5x
        if (lockPeriodDays >= 90) return 125;   // 3月: 1.25x
        if (lockPeriodDays >= 30) return 110;   // 1月: 1.1x
        return 100; // 无锁仓: 1x
    }
}
