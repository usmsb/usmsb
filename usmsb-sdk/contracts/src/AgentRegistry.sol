// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "./interfaces/IAgentRegistry.sol";

/**
 * @title AgentRegistry
 * @notice Agent 注册表合约，记录所有有效的 Agent 钱包地址
 * @dev 用于验证转账目标是否为合法的系统内 Agent
 */
contract AgentRegistry is IAgentRegistry, Ownable, ReentrancyGuard {
    // ========== 状态变量 ==========

    /// @notice 注册的 Agent 钱包地址列表
    address[] private _registeredAgents;

    /// @notice 验证地址是否为有效 Agent
    mapping(address => bool) private _validAgents;

    /// @notice Agent 钱包地址 -> 主人地址
    mapping(address => address) private _agentToOwner;

    /// @notice 主人地址 -> 拥有的 Agent 数量
    mapping(address => uint256) private _ownerAgentCount;

    // ========== 事件 ==========

    /// @notice Agent 注册事件
    event AgentRegistered(address indexed agentWallet, address indexed owner);

    /// @notice Agent 注销事件
    event AgentUnregistered(address indexed agentWallet);

    // ========== 构造函数 ==========

    constructor() Ownable(msg.sender) {}

    // ========== 外部函数 ==========

    /**
     * @notice 注册 Agent 钱包地址
     * @param agentWallet Agent 的合约钱包地址
     */
    function registerAgent(address agentWallet) external override nonReentrant {
        require(agentWallet != address(0), "AgentRegistry: invalid address");
        require(!_validAgents[agentWallet], "AgentRegistry: already registered");

        // 获取调用者地址（在实际部署时，这应该是创建 Agent 的主人）
        address owner = msg.sender;

        _validAgents[agentWallet] = true;
        _agentToOwner[agentWallet] = owner;
        _ownerAgentCount[owner]++;
        _registeredAgents.push(agentWallet);

        emit AgentRegistered(agentWallet, owner);
    }

    /**
     * @notice 注销 Agent（紧急情况）
     * @param agentWallet Agent 的合约钱包地址
     */
    function unregisterAgent(address agentWallet) external onlyOwner nonReentrant {
        require(_validAgents[agentWallet], "AgentRegistry: not registered");

        address owner = _agentToOwner[agentWallet];

        _validAgents[agentWallet] = false;
        _agentToOwner[agentWallet] = address(0);
        if (_ownerAgentCount[owner] > 0) {
            _ownerAgentCount[owner]--;
        }

        emit AgentUnregistered(agentWallet);
    }

    /**
     * @notice 验证地址是否为有效的 Agent
     * @param addr 要验证的地址
     * @return bool 是否为有效 Agent
     */
    function isValidAgent(address addr) external view override returns (bool) {
        return _validAgents[addr];
    }

    /**
     * @notice 验证地址是否已注册（包含已注销的）
     * @param wallet 要验证的地址
     * @return bool 是否注册过
     */
    function isRegistered(address wallet) external view override returns (bool) {
        return _agentToOwner[wallet] != address(0) || _validAgents[wallet];
    }

    /**
     * @notice 获取 Agent 的主人地址
     * @param agent Agent 钱包地址
     * @return address 主人地址
     */
    function getAgentOwner(address agent) external view override returns (address) {
        return _agentToOwner[agent];
    }

    /**
     * @notice 获取已注册的 Agent 数量
     * @return uint256 Agent 数量
     */
    function getAgentCount() external view override returns (uint256) {
        return _registeredAgents.length;
    }

    /**
     * @notice 获取指定索引的 Agent 地址
     * @param index 索引
     * @return address Agent 地址
     */
    function getAgentAt(uint256 index) external view returns (address) {
        require(index < _registeredAgents.length, "AgentRegistry: index out of bounds");
        return _registeredAgents[index];
    }

    /**
     * @notice 获取主人拥有的 Agent 数量
     * @param owner 主人地址
     * @return uint256 Agent 数量
     */
    function getOwnerAgentCount(address owner) external view returns (uint256) {
        return _ownerAgentCount[owner];
    }
}
