// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IPriceOracle
 * @notice 价格预言机接口
 */
interface IPriceOracle {
    function getPrice() external view returns (uint256);
    function get7DayAverage() external view returns (uint256);
    function lastValidPrice() external view returns (uint256);
}

/**
 * @title VIBStaking
 * @notice VIBE 代币质押合约，支持多等级、多锁仓期
 * @dev 使用 SafeERC20 安全操作代币转账
 */
contract VIBStaking is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 最小 APY
    uint256 public constant MIN_APY = 1; // 1%

    /// @notice 最大 APY
    uint256 public constant MAX_APY = 10; // 10%

    /// @notice 一年的秒数
    uint256 public constant SECONDS_PER_YEAR = 365 days;

    /// @notice 基础奖励精度
    uint256 public constant REWARD_PRECISION = 1e18;

    // ========== 质押时长系数 (用于治理投票权) ==========

    /// @notice 质押时长阈值 (天)
    uint256 public constant TIME_TIER_1 = 90 days;   // 1-90天: 100%
    uint256 public constant TIME_TIER_2 = 180 days;  // 91-180天: 110%
    uint256 public constant TIME_TIER_3 = 365 days;  // 181-365天: 125%
    // 365天+: 150%

    /// @notice 质押时长系数 (x10000)
    uint256 public constant TIME_MULTIPLIER_1 = 10000;  // 100%
    uint256 public constant TIME_MULTIPLIER_2 = 11000;  // 110%
    uint256 public constant TIME_MULTIPLIER_3 = 12500;  // 125%
    uint256 public constant TIME_MULTIPLIER_4 = 15000;  // 150%

    // ========== 质押等级 ==========

    /// @notice 质押等级枚举
    enum StakeTier {
        BRONZE,  // 青铜: 100-999 VIBE
        SILVER,  // 白银: 1000-4999 VIBE
        GOLD,    // 黄金: 5000-9999 VIBE
        PLATINUM // 铂金: 10000+ VIBE
    }

    /// @notice 质押等级最小质押量
    uint256[4] public TIER_MIN_AMOUNTS;

    // ========== 锁仓期 ==========

    /// @notice 锁仓期类型
    enum LockPeriod {
        NONE,    // 无锁仓
        THIRTY,  // 30 天
        NINETY,  // 90 天
        ONE80,   // 180 天
        ONE_YEAR // 365 天
    }

    /// @notice 锁仓期秒数
    uint256[5] public LOCK_PERIOD_SECONDS;

    /// @notice 锁仓期加成百分比（x10000）
    uint256[5] public LOCK_PERIOD_BONUS;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 释放控制器地址
    address public emissionController;

    /// @notice 价格预言机地址
    address public priceOracle;

    /// @notice 当前 APY (3%)
    uint256 public currentAPY = 3; // 3%

    /// @notice 基础 APY (3%)
    uint256 public constant BASE_APY = 3;

    /// @notice 最大动态 APY 加成 (7%，使 APY 最高可达 10%)
    uint256 public constant MAX_APY_BONUS = 7;

    // ========== 动态 APY 价格跟踪 ==========

    /// @notice 基准价格（用于计算价格变化）
    uint256 public basePrice;

    /// @notice 上次价格更新时间
    uint256 public lastPriceUpdateTime;

    /// @notice 价格历史记录（用于计算趋势）
    uint256[] public priceHistory;

    /// @notice 最大价格历史记录数
    uint256 public constant MAX_PRICE_HISTORY = 24; // 24小时

    /// @notice 价格下跌阈值（触发 APY 提升）
    uint256 public constant PRICE_DROP_THRESHOLD = 10; // 10%

    /// @notice 价格大幅下跌阈值（触发最大 APY）
    uint256 public constant PRICE_CRASH_THRESHOLD = 20; // 20%

    /// @notice APY 调整冷却期（秒）
    uint256 public constant APY_ADJUSTMENT_COOLDOWN = 1 hours;

    /// @notice 质押总金额
    uint256 public totalStaked;

    /// @notice 已分配奖励总额
    uint256 public totalRewardsDistributed;

    /// @notice 上次奖励计算时间
    uint256 public lastUpdateTime;

    /// @notice 累计奖励每代币
    uint256 public rewardPerTokenStored;

    /// @notice 用户质押信息
    mapping(address => StakeInfo) public stakeInfos;

    /// @notice 奖励余额
    mapping(address => uint256) public rewards;

    /// @notice 质押者地址列表
    address[] public stakers;

    /// @notice 地址是否为质押者
    mapping(address => bool) public isStaker;

    // ========== 结构体 ==========

    /**
     * @notice 质押信息
     */
    struct StakeInfo {
        uint256 amount;           // 质押数量
        uint256 tier;             // 质押等级
        uint256 lockPeriod;       // 锁仓期
        uint256 stakeTime;        // 质押时间
        uint256 unlockTime;       // 解锁时间
        uint256 rewardPerTokenPaid; // 已领取奖励每代币
        bool isActive;            // 是否活跃
    }

    // ========== 事件 ==========

    /// @notice 质押事件
    event Staked(
        address indexed user,
        uint256 amount,
        StakeTier tier,
        LockPeriod lockPeriod,
        uint256 unlockTime
    );

    /// @notice 提取质押事件
    event Unstaked(address indexed user, uint256 amount);

    /// @notice 领取奖励事件
    event RewardClaimed(address indexed user, uint256 amount);

    /// @notice APY 更新事件
    event APYUpdated(uint256 oldAPY, uint256 newAPY);

    /// @notice 动态 APY 调整事件
    event DynamicAPYAdjusted(
        uint256 oldAPY,
        uint256 newAPY,
        uint256 currentPrice,
        uint256 basePrice,
        int256 priceChangePercent
    );

    /// @notice 价格更新事件
    event PriceUpdated(uint256 price, uint256 timestamp);

    /// @notice 价格预言机设置事件
    event PriceOracleSet(address indexed oracle);

    /// @notice 基准价格设置事件
    event BasePriceSet(uint256 basePrice);

    /// @notice 代币地址更新事件
    event TokenUpdated(address indexed oldToken, address indexed newToken);

    /// @notice 紧急提取事件
    event EmergencyWithdraw(address indexed user, uint256 amount);

    /// @notice 释放控制器更新事件
    event EmissionControllerUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 奖励接收事件
    event RewardsReceived(uint256 amount, address indexed from);

    // ========== 修饰符 ==========

    /// @notice 检查用户是否已质押
    modifier isStaked(address user) {
        require(stakeInfos[user].isActive, "VIBStaking: user not staked");
        _;
    }

    /// @notice 检查锁仓期是否已过期
    modifier lockExpired(address user) {
        require(
            block.timestamp >= stakeInfos[user].unlockTime,
            "VIBStaking: lock period not expired"
        );
        _;
    }

    /// @notice 只允许释放控制器调用
    modifier onlyEmissionController() {
        require(
            msg.sender == emissionController,
            "VIBStaking: caller is not emission controller"
        );
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _vibeToken VIBE 代币地址
     */
    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBStaking: invalid token address");
        vibeToken = IERC20(_vibeToken);
        lastUpdateTime = block.timestamp;

        // 初始化质押等级最小质押量
        TIER_MIN_AMOUNTS = [uint256(100 * 10**18), uint256(1000 * 10**18), uint256(5000 * 10**18), uint256(10000 * 10**18)];

        // 初始化锁仓期秒数
        LOCK_PERIOD_SECONDS = [uint256(0), uint256(30 days), uint256(90 days), uint256(180 days), uint256(365 days)];

        // 初始化锁仓期加成
        LOCK_PERIOD_BONUS = [uint256(10000), uint256(10500), uint256(11000), uint256(12000), uint256(15000)];
    }

    // ========== 外部函数 ==========

    /**
     * @notice 质押 VIBE 代币
     * @param amount 质押数量
     * @param lockPeriod 锁仓期 (0=无, 1=30天, 2=90天, 3=180天, 4=365天)
     */
    function stake(uint256 amount, uint256 lockPeriod)
        external
        nonReentrant
        whenNotPaused
    {
        require(amount >= TIER_MIN_AMOUNTS[0], "VIBStaking: amount below minimum");
        require(lockPeriod < 5, "VIBStaking: invalid lock period");

        // 更新全局奖励
        updateGlobalRewards();

        // 如果用户已有质押，先结算奖励
        if (stakeInfos[msg.sender].isActive) {
            _claimReward(msg.sender);
            totalStaked -= stakeInfos[msg.sender].amount;
        } else {
            // 新质押者加入列表
            stakers.push(msg.sender);
            isStaker[msg.sender] = true;
        }

        // 转入代币
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        // 计算质押等级
        StakeTier tier = _calculateTier(amount);

        // 计算解锁时间
        uint256 unlockTime = block.timestamp + LOCK_PERIOD_SECONDS[lockPeriod];

        // 更新质押信息
        stakeInfos[msg.sender] = StakeInfo({
            amount: amount,
            tier: uint256(tier),
            lockPeriod: lockPeriod,
            stakeTime: block.timestamp,
            unlockTime: unlockTime,
            rewardPerTokenPaid: rewardPerTokenStored,
            isActive: true
        });

        totalStaked += amount;

        emit Staked(msg.sender, amount, tier, LockPeriod(lockPeriod), unlockTime);
    }

    /**
     * @notice 提取质押和奖励
     */
    function unstake() external nonReentrant whenNotPaused isStaked(msg.sender) lockExpired(msg.sender) {
        // 更新全局奖励
        updateGlobalRewards();

        // 结算奖励
        _claimReward(msg.sender);

        StakeInfo storage info = stakeInfos[msg.sender];

        // 转回质押代币
        vibeToken.safeTransfer(msg.sender, info.amount);

        emit Unstaked(msg.sender, info.amount);

        // 重置质押信息
        totalStaked -= info.amount;
        info.amount = 0;
        info.isActive = false;
    }

    /**
     * @notice 提取奖励（保持质押状态）
     */
    function claimReward() external nonReentrant whenNotPaused isStaked(msg.sender) {
        updateGlobalRewards();
        _claimReward(msg.sender);
    }

    /**
     * @notice 紧急提取（惩罚：放弃所有奖励）
     */
    function emergencyWithdraw() external nonReentrant isStaked(msg.sender) {
        StakeInfo storage info = stakeInfos[msg.sender];

        // 不更新奖励，直接提取
        vibeToken.safeTransfer(msg.sender, info.amount);

        emit EmergencyWithdraw(msg.sender, info.amount);

        totalStaked -= info.amount;
        info.amount = 0;
        rewards[msg.sender] = 0;
        info.isActive = false;
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置 APY
     * @param newAPY 新的 APY (1-10)
     */
    function setAPY(uint256 newAPY) external onlyOwner {
        require(
            newAPY >= MIN_APY && newAPY <= MAX_APY,
            "VIBStaking: APY out of range"
        );

        // 更新全局奖励
        updateGlobalRewards();

        emit APYUpdated(currentAPY, newAPY);
        currentAPY = newAPY;
    }

    // ========== 动态 APY 功能 ==========

    /**
     * @notice 设置价格预言机
     * @param _priceOracle 价格预言机地址
     */
    function setPriceOracle(address _priceOracle) external onlyOwner {
        priceOracle = _priceOracle;
        emit PriceOracleSet(_priceOracle);
    }

    /**
     * @notice 设置基准价格（用于计算价格变化）
     * @param _basePrice 基准价格
     */
    function setBasePrice(uint256 _basePrice) external onlyOwner {
        require(_basePrice > 0, "VIBStaking: invalid base price");
        basePrice = _basePrice;
        emit BasePriceSet(_basePrice);
    }

    // ========== Keeper 激励机制 ==========

    /// @notice Keeper 奖励金额 (0.1 VIBE)
    uint256 public constant KEEPER_REWARD = 1 * 10**17;

    /// @notice 上次 Keeper 奖励发放时间
    uint256 public lastKeeperRewardTime;

    /// @notice Keeper 奖励最小间隔 (4小时)
    uint256 public constant KEEPER_REWARD_INTERVAL = 4 hours;

    /// @notice Keeper 奖励事件
    event KeeperRewardPaid(address indexed keeper, uint256 reward);

    /**
     * @notice 更新价格并调整 APY（反死螺旋机制）
     * @dev 任何人都可以调用，有冷却期和奖励激励
     */
    function updatePriceAndAdjustAPY() external {
        require(priceOracle != address(0), "VIBStaking: oracle not set");
        require(basePrice > 0, "VIBStaking: base price not set");

        // 检查冷却期
        require(
            block.timestamp >= lastPriceUpdateTime + APY_ADJUSTMENT_COOLDOWN,
            "VIBStaking: cooldown not expired"
        );

        // 获取当前价格
        uint256 currentPrice = IPriceOracle(priceOracle).getPrice();
        require(currentPrice > 0, "VIBStaking: invalid price");

        // 更新价格历史
        priceHistory.push(currentPrice);
        if (priceHistory.length > MAX_PRICE_HISTORY) {
            // 移除最旧的记录
            for (uint256 i = 0; i < priceHistory.length - MAX_PRICE_HISTORY; i++) {
                priceHistory[i] = priceHistory[i + 1];
            }
            priceHistory.pop();
        }

        lastPriceUpdateTime = block.timestamp;
        emit PriceUpdated(currentPrice, block.timestamp);

        // 计算价格变化百分比
        int256 priceChangePercent = _calculatePriceChangePercent(currentPrice);

        // 根据价格变化调整 APY
        _adjustAPYBasedOnPrice(currentPrice, priceChangePercent);

        // ========== Keeper 激励 ==========
        // 如果满足间隔要求且有足够余额，发放奖励
        if (block.timestamp >= lastKeeperRewardTime + KEEPER_REWARD_INTERVAL) {
            uint256 balance = vibeToken.balanceOf(address(this));
            if (balance >= KEEPER_REWARD) {
                lastKeeperRewardTime = block.timestamp;
                vibeToken.safeTransfer(msg.sender, KEEPER_REWARD);
                emit KeeperRewardPaid(msg.sender, KEEPER_REWARD);
            }
        }
    }

    /**
     * @notice 计算价格变化百分比
     * @param currentPrice 当前价格
     * @return 价格变化百分比（正数表示上涨，负数表示下跌）
     */
    function _calculatePriceChangePercent(uint256 currentPrice) internal view returns (int256) {
        if (basePrice == 0) return 0;

        int256 change = int256(currentPrice) - int256(basePrice);
        return (change * 100) / int256(basePrice);
    }

    /**
     * @notice 根据价格变化调整 APY（反死螺旋机制）
     * @param currentPrice 当前价格
     * @param priceChangePercent 价格变化百分比
     */
    function _adjustAPYBasedOnPrice(uint256 currentPrice, int256 priceChangePercent) internal {
        // 更新全局奖励
        updateGlobalRewards();

        uint256 oldAPY = currentAPY;
        uint256 newAPY = BASE_APY;

        // 反死螺旋机制：价格下跌时提升 APY
        if (priceChangePercent < 0) {
            int256 dropPercent = -priceChangePercent; // 转为正数

            if (dropPercent >= int256(int256(PRICE_CRASH_THRESHOLD))) {
                // 价格下跌 >= 20%：最大 APY (10%)
                newAPY = BASE_APY + MAX_APY_BONUS;
            } else if (dropPercent >= int256(int256(PRICE_DROP_THRESHOLD))) {
                // 价格下跌 10-20%：按比例提升 APY
                // APY 加成 = (下跌百分比 / 20%) * 最大加成
                uint256 bonusRate = uint256(dropPercent - int256(PRICE_DROP_THRESHOLD)) * MAX_APY_BONUS /
                                   (PRICE_CRASH_THRESHOLD - PRICE_DROP_THRESHOLD);
                newAPY = BASE_APY + (MAX_APY_BONUS / 2) + bonusRate;
            } else {
                // 价格下跌 < 10%：小幅提升 APY
                // APY 加成 = (下跌百分比 / 10%) * (最大加成 / 2)
                uint256 bonusRate = uint256(dropPercent) * (MAX_APY_BONUS / 2) / PRICE_DROP_THRESHOLD;
                newAPY = BASE_APY + bonusRate;
            }
        } else {
            // 价格上涨或持平：恢复基础 APY
            newAPY = BASE_APY;
        }

        // 确保 APY 在有效范围内
        if (newAPY > MAX_APY) {
            newAPY = MAX_APY;
        }
        if (newAPY < MIN_APY) {
            newAPY = MIN_APY;
        }

        // 更新 APY
        if (newAPY != oldAPY) {
            currentAPY = newAPY;
            emit DynamicAPYAdjusted(oldAPY, newAPY, currentPrice, basePrice, priceChangePercent);
        }
    }

    /**
     * @notice 获取当前动态 APY（不实际更新）
     * @return 当前 APY
     */
    function getDynamicAPY() external view returns (uint256) {
        if (priceOracle == address(0) || basePrice == 0) {
            return currentAPY;
        }

        uint256 currentPrice = IPriceOracle(priceOracle).getPrice();
        if (currentPrice == 0) {
            return currentAPY;
        }

        int256 priceChangePercent = _calculatePriceChangePercent(currentPrice);

        uint256 newAPY = BASE_APY;

        if (priceChangePercent < 0) {
            int256 dropPercent = -priceChangePercent;

            if (dropPercent >= int256(int256(PRICE_CRASH_THRESHOLD))) {
                newAPY = BASE_APY + MAX_APY_BONUS;
            } else if (dropPercent >= int256(int256(PRICE_DROP_THRESHOLD))) {
                uint256 bonusRate = uint256(dropPercent - int256(PRICE_DROP_THRESHOLD)) * MAX_APY_BONUS /
                                   (PRICE_CRASH_THRESHOLD - PRICE_DROP_THRESHOLD);
                newAPY = BASE_APY + (MAX_APY_BONUS / 2) + bonusRate;
            } else {
                uint256 bonusRate = uint256(dropPercent) * (MAX_APY_BONUS / 2) / PRICE_DROP_THRESHOLD;
                newAPY = BASE_APY + bonusRate;
            }
        } else {
            newAPY = BASE_APY;
        }

        if (newAPY > MAX_APY) newAPY = MAX_APY;
        if (newAPY < MIN_APY) newAPY = MIN_APY;

        return newAPY;
    }

    /**
     * @notice 更新 VIBE 代币地址
     * @param _vibeToken 新的代币地址
     */
    function setVibeToken(address _vibeToken) external onlyOwner {
        require(_vibeToken != address(0), "VIBStaking: invalid token address");
        emit TokenUpdated(address(vibeToken), _vibeToken);
        vibeToken = IERC20(_vibeToken);
    }

    /**
     * @notice 暂停合约
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice 恢复合约
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 向合约添加奖励（从外部资助）
     * @param amount 奖励数量
     */
    function addRewards(uint256 amount) external {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /**
     * @notice 设置释放控制器地址
     * @param _emissionController 释放控制器地址
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        require(_emissionController != address(0), "VIBStaking: invalid address");
        emit EmissionControllerUpdated(emissionController, _emissionController);
        emissionController = _emissionController;
    }

    /**
     * @notice 接收来自释放控制器的奖励
     * @dev 只有释放控制器可以调用
     * @param amount 奖励数量
     */
    function receiveRewards(uint256 amount) external onlyEmissionController {
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        emit RewardsReceived(amount, msg.sender);
    }

    // ========== 公共视图函数 ==========

    /**
     * @notice 获取用户可领取奖励
     * @param user 用户地址
     * @return 可领取奖励数量
     */
    function getPendingReward(address user) public view returns (uint256) {
        if (!stakeInfos[user].isActive) {
            return rewards[user];
        }

        StakeInfo memory info = stakeInfos[user];

        // 计算时间加权奖励
        uint256 timeElapsed = block.timestamp - lastUpdateTime;
        if (totalStaked == 0 || timeElapsed == 0) {
            timeElapsed = 0;
        }

        uint256 rewardPerToken = rewardPerTokenStored +
            _calculateRewardPerToken(timeElapsed);

        return rewards[user] +
            ((info.amount * (rewardPerToken - info.rewardPerTokenPaid)) / REWARD_PRECISION);
    }

    /**
     * @notice 获取质押信息
     * @param user 用户地址
     * @return 质押信息
     */
    function getStakeInfo(address user) external view returns (StakeInfo memory) {
        return stakeInfos[user];
    }

    /**
     * @notice 获取用户质押等级
     * @param user 用户地址
     * @return 质押等级
     */
    function getUserTier(address user) external view returns (StakeTier) {
        require(stakeInfos[user].isActive, "VIBStaking: user not staked");
        return StakeTier(stakeInfos[user].tier);
    }

    /**
     * @notice 计算质押等级
     * @param amount 质押数量
     * @return 质押等级
     */
    function calculateTier(uint256 amount) external view returns (StakeTier) {
        return _calculateTier(amount);
    }

    /**
     * @notice 获取质押者数量
     * @return 质押者数量
     */
    function getStakerCount() external view returns (uint256) {
        return stakers.length;
    }

    /**
     * @notice 获取质押者列表
     * @param offset 偏移量
     * @param limit 数量限制
     * @return 质押者地址列表
     */
    function getStakers(uint256 offset, uint256 limit)
        external
        view
        returns (address[] memory)
    {
        require(offset < stakers.length, "VIBStaking: offset out of bounds");
        uint256 end = offset + limit;
        if (end > stakers.length) {
            end = stakers.length;
        }

        address[] memory result = new address[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = stakers[i];
        }
        return result;
    }

    /**
     * @notice 获取用户质押时长系数
     * @param user 用户地址
     * @return 时长系数 (x10000)
     */
    function getTimeMultiplier(address user) public view returns (uint256) {
        StakeInfo storage info = stakeInfos[user];
        if (!info.isActive) {
            return 0;
        }

        uint256 stakedDuration = block.timestamp - info.stakeTime;

        if (stakedDuration >= TIME_TIER_3) {
            return TIME_MULTIPLIER_4; // 365天+: 150%
        } else if (stakedDuration >= TIME_TIER_2) {
            return TIME_MULTIPLIER_3; // 181-365天: 125%
        } else if (stakedDuration >= TIME_TIER_1) {
            return TIME_MULTIPLIER_2; // 91-180天: 110%
        } else {
            return TIME_MULTIPLIER_1; // 1-90天: 100%
        }
    }

    /**
     * @notice 获取用户投票权 (质押量 × 时长系数)
     * @param user 用户地址
     * @return 投票权
     * @dev 用于治理合约计算资本权重
     */
    function getVotingPower(address user) external view returns (uint256) {
        StakeInfo storage info = stakeInfos[user];
        if (!info.isActive) {
            return 0;
        }

        uint256 multiplier = getTimeMultiplier(user);
        return (info.amount * multiplier) / 10000;
    }

    /**
     * @notice 批量获取投票权
     * @param users 用户地址列表
     * @return 投票权列表
     */
    function getVotingPowerBatch(address[] calldata users)
        external
        view
        returns (uint256[] memory)
    {
        uint256[] memory powers = new uint256[](users.length);
        for (uint256 i = 0; i < users.length; i++) {
            StakeInfo storage info = stakeInfos[users[i]];
            if (info.isActive) {
                uint256 multiplier = getTimeMultiplier(users[i]);
                powers[i] = (info.amount * multiplier) / 10000;
            } else {
                powers[i] = 0;
            }
        }
        return powers;
    }

    /**
     * @notice 获取用户质押时长（秒）
     * @param user 用户地址
     * @return 质押时长
     */
    function getStakedDuration(address user) external view returns (uint256) {
        StakeInfo storage info = stakeInfos[user];
        if (!info.isActive) {
            return 0;
        }
        return block.timestamp - info.stakeTime;
    }

    /**
     * @notice 获取用户质押详情（用于治理）
     * @param user 用户地址
     * @return amount 质押数量
     * @return tier 质押等级
     * @return timeMultiplier 时长系数
     * @return votingPower 投票权
     */
    function getStakeDetails(address user)
        external
        view
        returns (
            uint256 amount,
            uint256 tier,
            uint256 timeMultiplier,
            uint256 votingPower
        )
    {
        StakeInfo storage info = stakeInfos[user];
        if (!info.isActive) {
            return (0, 0, 0, 0);
        }

        amount = info.amount;
        tier = info.tier;
        timeMultiplier = getTimeMultiplier(user);
        votingPower = (amount * timeMultiplier) / 10000;
    }

    // ========== 内部函数 ==========

    /**
     * @notice 更新全局奖励
     */
    function updateGlobalRewards() public {
        if (totalStaked == 0) {
            lastUpdateTime = block.timestamp;
            return;
        }

        uint256 timeElapsed = block.timestamp - lastUpdateTime;
        if (timeElapsed == 0) {
            return;
        }

        rewardPerTokenStored += _calculateRewardPerToken(timeElapsed);
        lastUpdateTime = block.timestamp;
    }

    /**
     * @notice 计算每代币奖励
     * @param timeElapsed 经过的秒数
     * @return 每代币奖励
     */
    function _calculateRewardPerToken(uint256 timeElapsed) internal view returns (uint256) {
        // 基础年化奖励 = 总质押 * APY / 100
        // 实际奖励 = 基础奖励 * 时间比例
        // 每代币奖励 = 实际奖励 / 总质押

        uint256 annualReward = (totalStaked * currentAPY) / 100;
        uint256 timeReward = (annualReward * timeElapsed) / SECONDS_PER_YEAR;

        return (timeReward * REWARD_PRECISION) / totalStaked;
    }

    /**
     * @notice 计算质押等级
     * @param amount 质押数量
     * @return 质押等级
     */
    function _calculateTier(uint256 amount) internal view returns (StakeTier) {
        if (amount < TIER_MIN_AMOUNTS[1]) {
            return StakeTier.BRONZE;
        } else if (amount < TIER_MIN_AMOUNTS[2]) {
            return StakeTier.SILVER;
        } else if (amount < TIER_MIN_AMOUNTS[3]) {
            return StakeTier.GOLD;
        } else {
            return StakeTier.PLATINUM;
        }
    }

    /**
     * @notice 结算并发放奖励
     * @param user 用户地址
     */
    function _claimReward(address user) internal {
        StakeInfo storage info = stakeInfos[user];

        // 计算新增奖励
        uint256 reward = ((info.amount * (rewardPerTokenStored - info.rewardPerTokenPaid)) / REWARD_PRECISION);

        if (reward > 0) {
            // 应用锁仓期加成
            uint256 bonusMultiplier = LOCK_PERIOD_BONUS[info.lockPeriod];
            reward = (reward * bonusMultiplier) / 10000;

            rewards[user] += reward;

            // 检查合约余额是否足够
            uint256 balance = vibeToken.balanceOf(address(this));
            if (balance >= rewards[user]) {
                uint256 amount = rewards[user];
                rewards[user] = 0;
                vibeToken.safeTransfer(user, amount);
                totalRewardsDistributed += amount;
                emit RewardClaimed(user, amount);
            }
        }

        info.rewardPerTokenPaid = rewardPerTokenStored;
    }

    // ========== 接收函数 ==========

    /**
     * @notice 接收以太（仅用于资助奖励池）
     */
    receive() external payable {
        // ETH 将转换为 VIBE 代币用于奖励
    }

    /**
     * @notice 回退函数
     */
    fallback() external payable {
        revert("VIBStaking: fallback not allowed");
    }
}
