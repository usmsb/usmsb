// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title VIBEErrors
 * @notice VIBE生态系统共享错误定义
 * @dev 使用自定义错误代替require字符串，节省Gas并提供更好的错误信息
 */
library VIBEErrors {
    // ========== 通用错误 ==========

    /// @notice 零地址错误
    error ZeroAddress();

    /// @notice 零值错误
    error ZeroValue();

    /// @notice 无效地址
    error InvalidAddress(address addr);

    /// @notice 数组长度不匹配
    error ArrayLengthMismatch();

    /// @notice 空数组
    error EmptyArray();

    // ========== 授权/权限错误 ==========

    /// @notice 未授权
    error Unauthorized();

    /// @notice 非所有者
    error NotOwner();

    /// @notice 非管理员
    error NotAdmin();

    // ========== 状态错误 ==========

    /// @notice 已暂停
    error Paused();

    /// @notice 未暂停
    error NotPaused();

    /// @notice 已存在
    error AlreadyExists();

    /// @notice 不存在
    error NotFound();

    /// @notice 已激活
    error AlreadyActive();

    /// @notice 未激活
    error NotActive();

    // ========== 数值错误 ==========

    /// @notice 金额不足
    error InsufficientAmount(uint256 required, uint256 provided);

    /// @notice 余额不足
    error InsufficientBalance(uint256 required, uint256 available);

    /// @notice 超出上限
    error ExceedsLimit(uint256 limit, uint256 value);

    /// @notice 低于下限
    error BelowMinimum(uint256 minimum, uint256 value);

    // ========== 时间错误 ==========

    /// @notice 未到时间
    error NotYetTime(uint256 requiredTime, uint256 currentTime);

    /// @notice 已过期
    error Expired(uint256 expiryTime);

    /// @notice 冷却中
    error CooldownNotExpired(uint256 remainingTime);

    // ========== VIBEToken 特定错误 ==========

    /// @notice 代币未分发
    error TokensNotDistributed();

    /// @notice 代币已分发
    error TokensAlreadyDistributed();

    /// @notice 交易税未启用
    error TransactionTaxNotEnabled();

    /// @notice 免税状态未改变
    error TaxExemptStatusUnchanged();

    // ========== VIBStaking 特定错误 ==========

    /// @notice 用户未质押
    error UserNotStaked();

    /// @notice 质押金额低于最小值
    error StakeAmountBelowMinimum(uint256 minimum);

    /// @notice 无效锁仓期
    error InvalidLockPeriod();

    /// @notice 质押未激活
    error StakeNotActive();

    /// @notice 锁仓期未满
    error LockPeriodNotEnded(uint256 unlockTime);

    /// @notice 价格预言机未设置
    error OracleNotSet();

    /// @notice 基准价格未设置
    error BasePriceNotSet();

    /// @notice 无效价格
    error InvalidPrice();

    /// @notice 非活跃质押者
    error NotActiveStaker();

    // ========== VIBGovernance 特定错误 ==========

    /// @notice 提案不存在
    error ProposalNotFound(uint256 proposalId);

    /// @notice 提案已执行
    error ProposalAlreadyExecuted();

    /// @notice 提案已取消
    error ProposalAlreadyCancelled();

    /// @notice 提案未通过
    error ProposalNotPassed();

    /// @notice 投票权不足
    error InsufficientVotingPower();

    /// @notice 持有期未满
    error HoldingPeriodNotMet(uint256 requiredHoldingPeriod);

    /// @notice 委托未找到
    error DelegationNotFound();

    /// @notice 执行目标不在白名单
    error TargetNotWhitelisted(address target);

    /// @notice 执行函数不在白名单
    error FunctionNotWhitelisted(bytes4 selector);

    // ========== VIBVesting 特定错误 ==========

    /// @notice 受益人已存在
    error BeneficiaryAlreadyExists();

    /// @notice 受益人不存在
    error BeneficiaryNotFound();

    /// @notice 无可释放金额
    error NothingToRelease();

    /// @notice 无效受益人类型
    error InvalidBeneficiaryType();

    // ========== VIBIdentity 特定错误 ==========

    /// @notice 身份已注册
    error IdentityAlreadyRegistered();

    /// @notice 身份未注册
    error IdentityNotRegistered();

    /// @notice 名称已使用
    error NameAlreadyUsed();

    /// @notice 代币不存在
    error TokenNotFound();

    // ========== JointOrder 特定错误 ==========

    /// @notice 池已满
    error PoolFull();

    /// @notice 池未取消
    error PoolNotCancelled();

    /// @notice 无贡献
    error NoContribution();

    /// @notice 已领取退款
    error RefundAlreadyClaimed();

    // ========== AssetVault 特定错误 ==========

    /// @notice 资产不存在
    error AssetNotFound();

    /// @notice 资产已兑换
    error AssetAlreadyRedeemed();

    /// @notice 份额不足
    error InsufficientShares();
}
