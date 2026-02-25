// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBInflationControl
 * @notice VIBE 通胀控制合约
 * @dev 实现：
 *      - 年通胀上限 2% 硬约束
 *      - 月通胀 >0.5% 熔断机制
 *      - 动态释放控制
 */
contract VIBInflationControl is Ownable, ReentrancyGuard, Pausable {
    // ========== 常量 ==========

    /// @notice 年通胀上限 (2% = 200/10000)
    uint256 public constant MAX_ANNUAL_INFLATION = 200;

    /// @notice 月通胀熔断阈值 (0.5% = 50/10000)
    uint256 public constant MONTHLY_CIRCUIT_BREAKER_THRESHOLD = 50;

    /// @notice 精度因子
    uint256 public constant PRECISION = 10000;

    /// @notice 一年的秒数
    uint256 public constant SECONDS_PER_YEAR = 365 days;

    /// @notice 一个月的秒数
    uint256 public constant SECONDS_PER_MONTH = 30 days;

    // ========== 状态变量 ==========

    /// @notice 代币总供应量
    uint256 public totalSupply;

    /// @notice 初始供应量
    uint256 public initialSupply;

    /// @notice 年度起始供应量
    uint256 public yearlyStartSupply;

    /// @notice 年度起始时间
    uint256 public yearlyStartTime;

    /// @notice 月度起始供应量
    uint256 public monthlyStartSupply;

    /// @notice 月度起始时间
    uint256 public monthlyStartTime;

    /// @notice 已释放总量
    uint256 public totalReleased;

    /// @notice 年度已释放量
    uint256 public yearlyReleased;

    /// @notice 月度已释放量
    uint256 public monthlyReleased;

    /// @notice 熔断状态
    bool public circuitBreakerTriggered;

    /// @notice 熔断触发时间
    uint256 public circuitBreakerTriggerTime;

    /// @notice 熔断冷却期 (7天)
    uint256 public circuitBreakerCooldown = 7 days;

    /// @notice 授权释放者
    mapping(address => bool) public authorizedReleasers;

    /// @notice 释放记录
    ReleaseRecord[] public releaseRecords;

    // ========== 结构体 ==========

    struct ReleaseRecord {
        uint256 amount;
        uint256 timestamp;
        address releaser;
        string reason;
        bool successful;
    }

    // ========== 事件 ==========

    /// @notice 释放事件
    event TokensReleased(
        uint256 amount,
        address indexed releaser,
        string reason
    );

    /// @notice 释放拒绝事件
    event ReleaseRejected(
        uint256 amount,
        address indexed releaser,
        string reason
    );

    /// @notice 熔断触发事件
    event CircuitBreakerTriggered(
        uint256 monthlyInflation,
        uint256 threshold
    );

    /// @notice 熔断重置事件
    event CircuitBreakerReset();

    /// @notice 年度重置事件
    event YearlyReset(uint256 yearlyInflation);

    /// @notice 月度重置事件
    event MonthlyReset(uint256 monthlyInflation);

    /// @notice 授权释放者更新
    event ReleaserUpdated(address indexed releaser, bool authorized);

    // ========== 修饰符 ==========

    /// @notice 只允许授权释放者
    modifier onlyAuthorizedReleaser() {
        require(
            authorizedReleasers[msg.sender] || msg.sender == owner(),
            "VIBInflationControl: not authorized"
        );
        _;
    }

    /// @notice 检查熔断状态
    modifier notCircuitBroken() {
        require(!circuitBreakerTriggered, "VIBInflationControl: circuit breaker triggered");
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _initialSupply 初始供应量
     */
    constructor(uint256 _initialSupply) Ownable(msg.sender) {
        require(_initialSupply > 0, "VIBInflationControl: invalid supply");

        initialSupply = _initialSupply;
        totalSupply = _initialSupply;
        yearlyStartSupply = _initialSupply;
        monthlyStartSupply = _initialSupply;
        yearlyStartTime = block.timestamp;
        monthlyStartTime = block.timestamp;

        // 部署者默认为授权释放者
        authorizedReleasers[msg.sender] = true;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 请求释放代币
     * @param amount 释放数量
     * @param reason 释放原因
     * @return 是否成功
     */
    function requestRelease(uint256 amount, string calldata reason)
        external
        onlyAuthorizedReleaser
        nonReentrant
        whenNotPaused
        returns (bool)
    {
        // 检查熔断状态
        if (circuitBreakerTriggered) {
            // 检查冷却期是否已过
            if (block.timestamp >= circuitBreakerTriggerTime + circuitBreakerCooldown) {
                _resetCircuitBreaker();
            } else {
                emit ReleaseRejected(amount, msg.sender, "Circuit breaker active");
                return false;
            }
        }

        // 检查并重置周期
        _checkAndResetPeriods();

        // 检查年度通胀限制
        uint256 projectedYearlySupply = yearlyStartSupply + yearlyReleased + amount;
        uint256 yearlyInflation = ((projectedYearlySupply - yearlyStartSupply) * PRECISION) / yearlyStartSupply;

        if (yearlyInflation > MAX_ANNUAL_INFLATION) {
            emit ReleaseRejected(amount, msg.sender, "Exceeds annual inflation limit");
            return false;
        }

        // 检查月度通胀限制（熔断）
        uint256 projectedMonthlySupply = monthlyStartSupply + monthlyReleased + amount;
        uint256 monthlyInflation = ((projectedMonthlySupply - monthlyStartSupply) * PRECISION) / monthlyStartSupply;

        if (monthlyInflation > MONTHLY_CIRCUIT_BREAKER_THRESHOLD) {
            _triggerCircuitBreaker(monthlyInflation);
            emit ReleaseRejected(amount, msg.sender, "Would trigger circuit breaker");
            return false;
        }

        // 执行释放
        totalReleased += amount;
        yearlyReleased += amount;
        monthlyReleased += amount;
        totalSupply += amount;

        releaseRecords.push(ReleaseRecord({
            amount: amount,
            timestamp: block.timestamp,
            releaser: msg.sender,
            reason: reason,
            successful: true
        }));

        emit TokensReleased(amount, msg.sender, reason);

        return true;
    }

    /**
     * @notice 手动重置熔断（仅管理员）
     */
    function resetCircuitBreaker() external onlyOwner {
        _resetCircuitBreaker();
    }

    /**
     * @notice 更新总供应量（代币合约调用）
     * @param _totalSupply 新的总供应量
     */
    function updateTotalSupply(uint256 _totalSupply) external onlyOwner {
        totalSupply = _totalSupply;
    }

    /**
     * @notice 销毁代币时减少供应量
     * @param amount 销毁数量
     */
    function recordBurn(uint256 amount) external onlyAuthorizedReleaser {
        require(totalSupply >= amount, "VIBInflationControl: insufficient supply");
        totalSupply -= amount;
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置授权释放者
     * @param releaser 释放者地址
     * @param authorized 是否授权
     */
    function setAuthorizedReleaser(address releaser, bool authorized) external onlyOwner {
        require(releaser != address(0), "VIBInflationControl: invalid address");
        authorizedReleasers[releaser] = authorized;
        emit ReleaserUpdated(releaser, authorized);
    }

    /**
     * @notice 设置熔断冷却期
     * @param _cooldown 冷却期（秒）
     */
    function setCircuitBreakerCooldown(uint256 _cooldown) external onlyOwner {
        circuitBreakerCooldown = _cooldown;
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

    // ========== 视图函数 ==========

    /**
     * @notice 获取当前年度通胀率
     * @return 年度通胀率 (x10000)
     */
    function getCurrentYearlyInflation() external view returns (uint256) {
        if (yearlyStartSupply == 0) return 0;
        return (yearlyReleased * PRECISION) / yearlyStartSupply;
    }

    /**
     * @notice 获取当前月度通胀率
     * @return 月度通胀率 (x10000)
     */
    function getCurrentMonthlyInflation() external view returns (uint256) {
        if (monthlyStartSupply == 0) return 0;
        return (monthlyReleased * PRECISION) / monthlyStartSupply;
    }

    /**
     * @notice 获取剩余可释放量（年度）
     * @return 剩余可释放量
     */
    function getRemainingYearlyAllowance() external view returns (uint256) {
        uint256 maxYearlyRelease = (yearlyStartSupply * MAX_ANNUAL_INFLATION) / PRECISION;
        if (yearlyReleased >= maxYearlyRelease) return 0;
        return maxYearlyRelease - yearlyReleased;
    }

    /**
     * @notice 获取剩余可释放量（月度）
     * @return 剩余可释放量
     */
    function getRemainingMonthlyAllowance() external view returns (uint256) {
        uint256 maxMonthlyRelease = (monthlyStartSupply * MONTHLY_CIRCUIT_BREAKER_THRESHOLD) / PRECISION;
        if (monthlyReleased >= maxMonthlyRelease) return 0;
        return maxMonthlyRelease - monthlyReleased;
    }

    /**
     * @notice 检查是否可以释放指定数量
     * @param amount 释放数量
     * @return 是否可以释放
     */
    function canRelease(uint256 amount) external view returns (bool) {
        if (circuitBreakerTriggered) {
            if (block.timestamp < circuitBreakerTriggerTime + circuitBreakerCooldown) {
                return false;
            }
        }

        // 检查年度限制
        uint256 projectedYearlySupply = yearlyStartSupply + yearlyReleased + amount;
        uint256 yearlyInflation = ((projectedYearlySupply - yearlyStartSupply) * PRECISION) / yearlyStartSupply;
        if (yearlyInflation > MAX_ANNUAL_INFLATION) return false;

        // 检查月度限制
        uint256 projectedMonthlySupply = monthlyStartSupply + monthlyReleased + amount;
        uint256 monthlyInflation = ((projectedMonthlySupply - monthlyStartSupply) * PRECISION) / monthlyStartSupply;
        if (monthlyInflation > MONTHLY_CIRCUIT_BREAKER_THRESHOLD) return false;

        return true;
    }

    /**
     * @notice 获取通胀统计
     * @return currentSupply 当前供应量
     * @return yearlyInf 年度通胀率
     * @return monthlyInf 月度通胀率
     * @return totalRel 总释放量
     * @return circuitBroken 熔断状态
     */
    function getStats()
        external
        view
        returns (
            uint256 currentSupply,
            uint256 yearlyInf,
            uint256 monthlyInf,
            uint256 totalRel,
            bool circuitBroken
        )
    {
        currentSupply = totalSupply;
        yearlyInf = yearlyStartSupply > 0 ? (yearlyReleased * PRECISION) / yearlyStartSupply : 0;
        monthlyInf = monthlyStartSupply > 0 ? (monthlyReleased * PRECISION) / monthlyStartSupply : 0;
        totalRel = totalReleased;
        circuitBroken = circuitBreakerTriggered;
    }

    /**
     * @notice 获取释放记录数量
     * @return 记录数量
     */
    function getReleaseRecordCount() external view returns (uint256) {
        return releaseRecords.length;
    }

    /**
     * @notice 获取释放记录
     * @param index 索引
     * @return 释放记录
     */
    function getReleaseRecord(uint256 index) external view returns (ReleaseRecord memory) {
        require(index < releaseRecords.length, "VIBInflationControl: index out of bounds");
        return releaseRecords[index];
    }

    // ========== 内部函数 ==========

    /**
     * @notice 检查并重置周期
     */
    function _checkAndResetPeriods() internal {
        // 检查年度周期
        if (block.timestamp >= yearlyStartTime + SECONDS_PER_YEAR) {
            uint256 yearlyInflation = yearlyStartSupply > 0
                ? (yearlyReleased * PRECISION) / yearlyStartSupply
                : 0;

            emit YearlyReset(yearlyInflation);

            yearlyStartTime = block.timestamp;
            yearlyStartSupply = totalSupply;
            yearlyReleased = 0;
        }

        // 检查月度周期
        if (block.timestamp >= monthlyStartTime + SECONDS_PER_MONTH) {
            uint256 monthlyInflation = monthlyStartSupply > 0
                ? (monthlyReleased * PRECISION) / monthlyStartSupply
                : 0;

            emit MonthlyReset(monthlyInflation);

            monthlyStartTime = block.timestamp;
            monthlyStartSupply = totalSupply;
            monthlyReleased = 0;

            // 如果熔断触发但月度已重置，可以考虑自动恢复
            // 这里选择手动恢复，更安全
        }
    }

    /**
     * @notice 触发熔断
     * @param monthlyInflation 月度通胀率
     */
    function _triggerCircuitBreaker(uint256 monthlyInflation) internal {
        circuitBreakerTriggered = true;
        circuitBreakerTriggerTime = block.timestamp;

        emit CircuitBreakerTriggered(monthlyInflation, MONTHLY_CIRCUIT_BREAKER_THRESHOLD);
    }

    /**
     * @notice 重置熔断
     */
    function _resetCircuitBreaker() internal {
        circuitBreakerTriggered = false;
        circuitBreakerTriggerTime = 0;

        // 重置月度计数
        monthlyStartTime = block.timestamp;
        monthlyStartSupply = totalSupply;
        monthlyReleased = 0;

        emit CircuitBreakerReset();
    }
}
