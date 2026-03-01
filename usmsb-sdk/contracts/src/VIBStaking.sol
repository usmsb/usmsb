// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./libraries/VIBEErrors.sol";
import "./libraries/AddressValidation.sol";

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
    using AddressValidation for address;

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

    /// @notice 待生效的基准价格变更
    uint256 public pendingBasePrice;
    uint256 public pendingBasePriceTime;

    /// @notice 基准价格变更延迟 (3天)
    uint256 public constant BASE_PRICE_CHANGE_DELAY = 3 days;

    /// @notice 上次价格更新时间
    uint256 public lastPriceUpdateTime;

    /// @notice 价格历史记录（循环缓冲区）
    uint256[24] public priceHistoryBuffer;

    /// @notice 价格历史当前索引
    uint256 public priceHistoryIndex;

    /// @notice 价格历史记录数量
    uint256 public priceHistoryCount;

    /// @notice 最大价格历史记录数
    uint256 public constant MAX_PRICE_HISTORY = 24; // 24小时

    /// @notice 价格下跌阈值（触发 APY 提升）
    uint256 public constant PRICE_DROP_THRESHOLD = 10; // 10%

    /// @notice 价格大幅下跌阈值（触发最大 APY）
    uint256 public constant PRICE_CRASH_THRESHOLD = 20; // 20%

    /// @notice APY 调整最小阈值（防止小幅度价格波动导致频繁调整）
    uint256 public constant MIN_APY_ADJUSTMENT_THRESHOLD = 10; // 10% - 安全增强

    /// @notice APY 调整冷却期（秒）
    uint256 public constant APY_ADJUSTMENT_COOLDOWN = 1 hours;

    /// @notice 质押总金额
    uint256 public totalStaked;

    /// @notice 已分配奖励总额
    uint256 public totalRewardsDistributed;

    /// @notice 累计接收的 ETH 金额
    uint256 public totalEthReceived;

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

    /**
     * @notice 质押事件
     * @dev 当用户成功质押代币时触发
     * @param user 质押用户地址
     * @param amount 质押金额（wei）
     * @param tier 质押等级（Bronze/Silver/Gold/Platinum）
     * @param lockPeriod 锁仓期类型
     * @param unlockTime 解锁时间戳
     */
    event Staked(
        address indexed user,
        uint256 amount,
        StakeTier tier,
        LockPeriod lockPeriod,
        uint256 unlockTime
    );

    /**
     * @notice 提取质押事件
     * @dev 当用户提取质押的代币时触发
     * @param user 用户地址
     * @param amount 提取金额（wei）
     */
    event Unstaked(address indexed user, uint256 amount);

    /**
     * @notice 领取奖励事件
     * @dev 当用户领取质押奖励时触发
     * @param user 用户地址
     * @param amount 奖励金额（wei）
     */
    event RewardClaimed(address indexed user, uint256 amount);

    /**
     * @notice APY 更新事件
     * @dev 当APY手动更新时触发
     * @param oldAPY 旧APY值（百分比）
     * @param newAPY 新APY值（百分比）
     */
    event APYUpdated(uint256 oldAPY, uint256 newAPY);

    /**
     * @notice 动态 APY 调整事件
     * @dev 当根据价格变化自动调整APY时触发
     * @param oldAPY 调整前APY
     * @param newAPY 调整后APY
     * @param currentPrice 当前价格
     * @param basePrice 基准价格
     * @param priceChangePercent 价格变化百分比（正数上涨，负数下跌）
     */
    event DynamicAPYAdjusted(
        uint256 oldAPY,
        uint256 newAPY,
        uint256 currentPrice,
        uint256 basePrice,
        int256 priceChangePercent
    );

    /**
     * @notice 价格更新事件
     * @dev 当价格预言机更新价格时触发
     * @param price 新价格
     * @param timestamp 更新时间戳
     */
    event PriceUpdated(uint256 price, uint256 timestamp);

    /**
     * @notice 价格预言机设置事件
     * @dev 当管理员设置价格预言机地址时触发
     * @param oracle 预言机合约地址
     */
    event PriceOracleSet(address indexed oracle);

    /**
     * @notice 基准价格设置事件
     * @dev 当管理员设置基准价格时触发
     * @param basePrice 基准价格
     */
    event BasePriceSet(uint256 basePrice);
    event BasePriceChangeInitiated(uint256 newPrice, uint256 effectiveTime);
    event BasePriceChangeCancelled();

    /**
     * @notice 代币地址更新事件
     * @dev 当管理员更新VIBE代币地址时触发
     * @param oldToken 旧代币地址
     * @param newToken 新代币地址
     */
    event TokenUpdated(address indexed oldToken, address indexed newToken);

    /**
     * @notice 紧急提取事件
     * @dev 当用户紧急提取质押（放弃奖励）时触发
     * @param user 用户地址
     * @param amount 提取金额
     */
    event EmergencyWithdraw(address indexed user, uint256 amount);

    /**
     * @notice 释放控制器更新事件
     * @dev 当管理员更新释放控制器地址时触发
     * @param oldAddress 旧地址
     * @param newAddress 新地址
     */
    event EmissionControllerUpdated(address indexed oldAddress, address indexed newAddress);

    /**
     * @notice 奖励接收事件
     * @dev 当合约接收外部奖励时触发
     * @param amount 奖励金额
     * @param from 发送者地址
     */
    event RewardsReceived(uint256 amount, address indexed from);

    /**
     * @notice Keeper奖励支付事件
     * @dev 当Keeper因更新价格获得奖励时触发
     * @param keeper Keeper地址
     * @param reward 奖励金额
     */
    event KeeperRewardPaid(address indexed keeper, uint256 reward);
    event EthReceived(address indexed from, uint256 amount);

    // ========== 修饰符 ==========

    /// @notice 检查用户是否已质押
    modifier isStaked(address user) {
        if (!stakeInfos[user].isActive) revert VIBEErrors.UserNotStaked();
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
        if (_vibeToken == address(0)) revert VIBEErrors.ZeroAddress();
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
        if (amount < TIER_MIN_AMOUNTS[0]) revert VIBEErrors.StakeAmountBelowMinimum(TIER_MIN_AMOUNTS[0]);
        if (lockPeriod >= 5) revert VIBEErrors.InvalidLockPeriod();

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
     * @dev 安全增强: 验证是有效合约地址
     */
    function setPriceOracle(address _priceOracle) external onlyOwner {
        require(_priceOracle != address(0), "VIBStaking: invalid oracle address");
        // 验证是否为合约地址
        uint256 size;
        assembly {
            size := extcodesize(_priceOracle)
        }
        require(size > 0, "VIBStaking: not a contract");
        priceOracle = _priceOracle;
        emit PriceOracleSet(_priceOracle);
    }

    /**
     * @notice 设置基准价格（用于计算价格变化）
     * @param _basePrice 基准价格
     * @dev 安全增强: 需要3天时间锁
     */
    function setBasePrice(uint256 _basePrice) external onlyOwner {
        require(_basePrice > 0, "VIBStaking: invalid base price");

        // 如果没有待生效的变更，立即生效
        if (pendingBasePriceTime == 0) {
            basePrice = _basePrice;
            emit BasePriceSet(_basePrice);
        } else {
            // 等待时间锁
            require(
                block.timestamp >= pendingBasePriceTime,
                "VIBStaking: timelock not elapsed"
            );
            basePrice = pendingBasePrice;
            pendingBasePrice = 0;
            pendingBasePriceTime = 0;
            emit BasePriceSet(basePrice);
        }
    }

    /**
     * @notice 发起基准价格变更（需要时间锁）
     * @param _basePrice 新的基准价格
     */
    function initiateBasePriceChange(uint256 _basePrice) external onlyOwner {
        require(_basePrice > 0, "VIBStaking: invalid base price");
        pendingBasePrice = _basePrice;
        pendingBasePriceTime = block.timestamp + BASE_PRICE_CHANGE_DELAY;
        emit BasePriceChangeInitiated(_basePrice, pendingBasePriceTime);
    }

    /**
     * @notice 取消待生效的基准价格变更
     */
    function cancelBasePriceChange() external onlyOwner {
        require(pendingBasePriceTime > 0, "VIBStaking: no pending change");
        pendingBasePrice = 0;
        pendingBasePriceTime = 0;
        emit BasePriceChangeCancelled();
    }

    // ========== Keeper 激励机制 ==========

    /// @notice Keeper 奖励金额 (0.1 VIBE)
    uint256 public constant KEEPER_REWARD = 1 * 10**17;

    /// @notice 上次 Keeper 奖励发放时间
    uint256 public lastKeeperRewardTime;

    /// @notice Keeper 奖励最小间隔 (4小时)
    uint256 public constant KEEPER_REWARD_INTERVAL = 4 hours;

    /**
     * @notice 更新价格并调整 APY（反死螺旋机制）
     * @dev 安全修复: 只有活跃质押者才能调用，防止价格操纵攻击
     */
    function updatePriceAndAdjustAPY() external {
        if (priceOracle == address(0)) revert VIBEErrors.OracleNotSet();
        if (basePrice == 0) revert VIBEErrors.BasePriceNotSet();

        // 安全修复: 只有活跃质押者才能调用此函数
        if (!stakeInfos[msg.sender].isActive ||
            stakeInfos[msg.sender].amount < TIER_MIN_AMOUNTS[0]) {
            revert VIBEErrors.NotActiveStaker();
        }

        // 检查冷却期
        if (block.timestamp < lastPriceUpdateTime + APY_ADJUSTMENT_COOLDOWN) {
            revert VIBEErrors.CooldownNotExpired(
                lastPriceUpdateTime + APY_ADJUSTMENT_COOLDOWN - block.timestamp
            );
        }

        // 获取当前价格
        uint256 currentPrice = IPriceOracle(priceOracle).getPrice();
        if (currentPrice == 0) revert VIBEErrors.InvalidPrice();

        // 更新价格历史（使用循环缓冲区，O(1)复杂度）
        priceHistoryBuffer[priceHistoryIndex] = currentPrice;
        priceHistoryIndex = (priceHistoryIndex + 1) % MAX_PRICE_HISTORY;
        if (priceHistoryCount < MAX_PRICE_HISTORY) {
            priceHistoryCount++;
        }

        lastPriceUpdateTime = block.timestamp;
        emit PriceUpdated(currentPrice, block.timestamp);

        // 计算价格变化百分比
        int256 priceChangePercent = _calculatePriceChangePercent(currentPrice);

        // 根据价格变化调整 APY
        _adjustAPYBasedOnPrice(currentPrice, priceChangePercent);

        // ========== Keeper 激励 ==========
        // 安全修复: 只有在有显著价格变化时才发放奖励
        if (block.timestamp >= lastKeeperRewardTime + KEEPER_REWARD_INTERVAL) {
            // 检查是否有显著价格变化（>=3%）
            int256 absPriceChange = priceChangePercent >= 0 ? priceChangePercent : -priceChangePercent;
            bool significantChange = absPriceChange >= 3; // 3% 阈值

            if (significantChange) {
                uint256 balance = vibeToken.balanceOf(address(this));
                if (balance >= KEEPER_REWARD) {
                    lastKeeperRewardTime = block.timestamp;
                    vibeToken.safeTransfer(msg.sender, KEEPER_REWARD);
                    emit KeeperRewardPaid(msg.sender, KEEPER_REWARD);
                }
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
        // 安全增强: 如果价格变化小于最小阈值，不调整 APY（防止前端运行攻击）
        int256 absChange = priceChangePercent >= 0 ? priceChangePercent : -priceChangePercent;
        if (absChange < int256(MIN_APY_ADJUSTMENT_THRESHOLD)) {
            // 价格变化太小，不调整 APY
            return;
        }

        // 更新全局奖励
        updateGlobalRewards();

        uint256 oldAPY = currentAPY;
        uint256 newAPY = BASE_APY;

        // 反死螺旋机制：价格下跌时提升 APY
        // STK-001修复: 严格按照白皮书公式实现
        // - 下跌<10%:  APY = 3 + (下跌% / 10) × 3.5，范围3%~6.5%
        // - 下跌10-20%: APY = 6.5 + ((下跌% - 10) / 10) × 3.5，范围6.5%~10%
        // - 下跌≥20%: APY = 10%（最大）
        //
        // 使用精度100来保留1位小数: 3% = 300, 3.5% = 350, 6.5% = 650, 10% = 1000
        if (priceChangePercent < 0) {
            int256 dropPercent = -priceChangePercent; // 转为正数

            if (dropPercent >= int256(int256(PRICE_CRASH_THRESHOLD))) {
                // 价格下跌 >= 20%：最大 APY (10%)
                newAPY = MAX_APY;
            } else if (dropPercent >= int256(int256(PRICE_DROP_THRESHOLD))) {
                // 价格下跌 10-20%：
                // 白皮书公式: APY = 6.5 + ((下跌% - 10) / 10) × 3.5
                // 使用精度100: APY (精度100) = 650 + ((下跌% - 10) × 35)
                uint256 excessDrop = uint256(dropPercent - int256(PRICE_DROP_THRESHOLD)); // 0-10
                // 每跌1%加35个基点(0.35%)
                uint256 apyWithPrecision = 650 + (excessDrop * 35); // 精度100
                newAPY = apyWithPrecision / 100; // 转回百分比
                if (newAPY > MAX_APY) newAPY = MAX_APY;
            } else {
                // 价格下跌 < 10%：
                // 白皮书公式: APY = 3 + (下跌% / 10) × 3.5
                // 使用精度100: APY (精度100) = 300 + (下跌% × 35)
                uint256 apyWithPrecision = 300 + (uint256(dropPercent) * 35); // 精度100
                newAPY = apyWithPrecision / 100; // 转回百分比
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
        if (_vibeToken == address(0)) revert VIBEErrors.ZeroAddress();
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
     * @notice 向合约添加奖励
     * @dev 仅允许 owner 或 emissionController 调用
     * @param amount 奖励数量
     */
    function addRewards(uint256 amount) external {
        require(
            msg.sender == owner() || msg.sender == emissionController,
            "VIBStaking: not authorized to add rewards"
        );
        require(amount > 0, "VIBStaking: amount must be greater than 0");
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /**
     * @notice 设置释放控制器地址
     * @param _emissionController 释放控制器地址
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        if (_emissionController == address(0)) revert VIBEErrors.ZeroAddress();
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
     * @notice 获取价格历史记录
     * @return prices 价格数组（按时间顺序，最新的在最后）
     * @return count 有效记录数量
     */
    function getPriceHistory() external view returns (uint256[] memory prices, uint256 count) {
        count = priceHistoryCount;
        prices = new uint256[](count);

        if (count == 0) {
            return (prices, 0);
        }

        // 计算起始索引（最旧的记录）
        uint256 startIndex;
        if (count < MAX_PRICE_HISTORY) {
            startIndex = 0;
        } else {
            startIndex = priceHistoryIndex; // 缓冲区已满，当前索引指向最旧的
        }

        // 按时间顺序填充数组
        for (uint256 i = 0; i < count; i++) {
            prices[i] = priceHistoryBuffer[(startIndex + i) % MAX_PRICE_HISTORY];
        }
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
     * @notice 接收以太（用于资助奖励池）
     */
    receive() external payable {
        require(msg.value > 0, "VIBStaking: zero ETH");
        totalEthReceived += msg.value;
        emit EthReceived(msg.sender, msg.value);
    }

    /**
     * @notice 回退函数
     */
    fallback() external payable {
        revert("VIBStaking: fallback not allowed");
    }
}
