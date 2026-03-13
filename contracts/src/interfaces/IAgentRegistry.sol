// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IAgentRegistry
 * @notice Agent 注册表接口
 */
interface IAgentRegistry {
    function registerAgent(address agentWallet) external;

    function isValidAgent(address addr) external view returns (bool);

    function getAgentOwner(address agent) external view returns (address);

    function getAgentCount() external view returns (uint256);

    function isRegistered(address wallet) external view returns (bool);
}
