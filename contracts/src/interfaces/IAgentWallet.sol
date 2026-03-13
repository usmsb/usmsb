// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IAgentWallet
 * @notice Agent 钱包接口
 */
interface IAgentWallet {
    function executeTransfer(address to, uint256 amount) external returns (bool);

    function getOwner() external view returns (address);

    function getAgent() external view returns (address);

    function getBalance() external view returns (uint256);

    function getStakedAmount() external view returns (uint256);

    function getDailySpent() external view returns (uint256);

    function getMaxPerTx() external view returns (uint256);

    function getDailyLimit() external view returns (uint256);
}
