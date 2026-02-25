// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title VIBTimelock
 * @notice VIBE 生态系统时间锁合约
 * @dev 用于治理参数变更的时间锁
 *      支持：质押 APY、交易费、销毁比例、分红比例
 */
contract VIBTimelock is Ownable, ReentrancyGuard {
    // ========== 常量 ==========

    /// @notice 操作类型
    enum OperationType {
        SET_APY,           // 设置 APY
        SET_FEE,          // 设置交易费
        SET_BURN_RATIO,   // 设置销毁比例
        SET_DIVIDEND_RATIO, // 设置分红比例
        SET_ECOSYSTEM_RATIO, // 设置生态基金比例
        SET_PROTOCOL_RATIO,  // 设置协议基金比例
        UPGRADE_CONTRACT,  // 升级合约
        EMERGENCY_WITHDRAW // 紧急提款
    }

    // ========== 状态变量 ==========

    /// @notice 延迟时间映射
    mapping(OperationType => uint256) public operationDelays;

    /// @notice 待执行操作队列
    mapping(bytes32 =>queuedOperation) public queuedOperations;

    /// @notice 操作计数器
    uint256 public operationCount;

    /// @notice 管理员地址集合
    mapping(address => bool) public admin;

    /// @notice 紧急暂停状态
    bool public paused;

    // ========== 结构体 ==========

    /**
     * @notice 待执行操作
     */
    struct queuedOperation {
        address target;           // 目标合约
        bytes data;             // 调用数据
        uint256 value;          // ETH 金额
        uint256 eta;            // 预计执行时间
        OperationType operationType; // 操作类型
        bool executed;           // 是否已执行
        bool cancelled;          // 是否已取消
    }

    // ========== 事件 =========-

    /// @notice 操作加入队列事件
    event OperationQueued(
        bytes32 indexed operationId,
        address indexed target,
        OperationType operationType,
        uint256 eta
    );

    /// @notice 操作执行事件
    event OperationExecuted(
        bytes32 indexed operationId,
        address indexed executor
    );

    /// @notice 操作取消事件
    event OperationCancelled(
        bytes32 indexed operationId,
        address indexed canceller
    );

    /// @notice 延迟更新事件
    event DelayUpdated(
        OperationType operationType,
        uint256 oldDelay,
        uint256 newDelay
    );

    /// @notice 紧急暂停事件
    event Paused(address pauser);

    /// @notice 恢复事件
    event Unpaused(address unpauser);

    // ========== 修饰符 ==========

    /// @notice 检查是否暂停
    modifier notPaused() {
        require(!paused, "VIBTimelock: paused");
        _;
    }

    /// @notice 检查是否是管理员
    modifier onlyAdmin() {
        require(admin[msg.sender] || msg.sender == owner(), "VIBTimelock: not admin");
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     */
    constructor() Ownable(msg.sender) {
        // 默认延迟设置
        operationDelays[OperationType.SET_APY] = 14 days;
        operationDelays[OperationType.SET_FEE] = 30 days;
        operationDelays[OperationType.SET_BURN_RATIO] = 30 days;
        operationDelays[OperationType.SET_DIVIDEND_RATIO] = 30 days;
        operationDelays[OperationType.SET_ECOSYSTEM_RATIO] = 30 days;
        operationDelays[OperationType.SET_PROTOCOL_RATIO] = 30 days;
        operationDelays[OperationType.UPGRADE_CONTRACT] = 60 days;
        operationDelays[OperationType.EMERGENCY_WITHDRAW] = 0; // 紧急操作无延迟

        // 部署者默认为管理员
        admin[msg.sender] = true;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 队列操作
     * @param target 目标合约
     * @param data 调用数据
     * @param operationType 操作类型
     * @return 操作 ID
     */
    function queueOperation(
        address target,
        bytes calldata data,
        OperationType operationType
    ) external onlyAdmin notPaused returns (bytes32) {
        uint256 delay = operationDelays[operationType];
        require(delay >= 0, "VIBTimelock: invalid operation type");

        uint256 eta = block.timestamp + delay;

        bytes32 operationId = keccak256(
            abi.encode(
                target,
                data,
                eta,
                operationType,
                operationCount++
            )
        );

        queuedOperations[operationId] = queuedOperation({
            target: target,
            data: data,
            value: 0,
            eta: eta,
            operationType: operationType,
            executed: false,
            cancelled: false
        });

        emit OperationQueued(operationId, target, operationType, eta);

        return operationId;
    }

    /**
     * @notice 执行操作
     * @param operationId 操作 ID
     */
    function executeOperation(bytes32 operationId)
        external
        nonReentrant
        onlyAdmin
        notPaused
    {
        queuedOperation storage operation = queuedOperations[operationId];

        require(operation.target != address(0), "VIBTimelock: operation not queued");
        require(!operation.executed, "VIBTimelock: already executed");
        require(!operation.cancelled, "VIBTimelock: operation cancelled");
        require(block.timestamp >= operation.eta, "VIBTimelock: not yet executable");

        // 标记为已执行
        operation.executed = true;

        // 执行调用
        (bool success, ) = operation.target.call{value: operation.value}(operation.data);
        require(success, "VIBTimelock: execution failed");

        emit OperationExecuted(operationId, msg.sender);
    }

    /**
     * @notice 取消操作
     * @param operationId 操作 ID
     */
    function cancelOperation(bytes32 operationId) external onlyAdmin {
        queuedOperation storage operation = queuedOperations[operationId];

        require(operation.target != address(0), "VIBTimelock: operation not queued");
        require(!operation.executed, "VIBTimelock: already executed");
        require(!operation.cancelled, "VIBTimelock: already cancelled");

        operation.cancelled = true;

        emit OperationCancelled(operationId, msg.sender);
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置操作延迟
     * @param operationType 操作类型
     * @param delay 延迟时间
     */
    function setDelay(OperationType operationType, uint256 delay) external onlyOwner {
        uint256 oldDelay = operationDelays[operationType];
        operationDelays[operationType] = delay;
        emit DelayUpdated(operationType, oldDelay, delay);
    }

    /**
     * @notice 添加管理员
     * @param account 管理员地址
     */
    function addAdmin(address account) external onlyOwner {
        require(account != address(0), "VIBTimelock: invalid address");
        admin[account] = true;
    }

    /**
     * @notice 移除管理员
     * @param account 管理员地址
     */
    function removeAdmin(address account) external onlyOwner {
        require(account != owner(), "VIBTimelock: cannot remove owner");
        admin[account] = false;
    }

    /**
     * @notice 紧急暂停
     */
    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    /**
     * @notice 恢复
     */
    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 检查操作是否可执行
     * @param operationId 操作 ID
     * @return 是否可执行
     */
    function isOperationReady(bytes32 operationId) external view returns (bool) {
        queuedOperation memory operation = queuedOperations[operationId];
        return operation.target != address(0) &&
               !operation.executed &&
               !operation.cancelled &&
               block.timestamp >= operation.eta;
    }

    /**
     * @notice 检查操作是否已执行
     * @param operationId 操作 ID
     * @return 是否已执行
     */
    function isOperationExecuted(bytes32 operationId) external view returns (bool) {
        return queuedOperations[operationId].executed;
    }

    /**
     * @notice 获取操作详情
     * @param operationId 操作 ID
     * @return 操作详情
     */
    function getOperation(bytes32 operationId)
        external
        view
        returns (queuedOperation memory)
    {
        return queuedOperations[operationId];
    }

    /**
     * @notice 获取操作延迟
     * @param operationType 操作类型
     * @return 延迟时间
     */
    function getDelay(OperationType operationType) external view returns (uint256) {
        return operationDelays[operationType];
    }
}
