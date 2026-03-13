// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IVIBEToken
 * @notice VIBE 代币接口
 */
interface IVIBEToken {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
    function totalSupply() external view returns (uint256);
    function burn(uint256 amount) external;
    function mintReward(address to, uint256 amount) external;
    function dividendDistribution(address to, uint256 amount) external;
    function ecosystemFundWithdraw(address to, uint256 amount) external;
    function transactionTaxEnabled() external view returns (bool);
    function totalBurned() external view returns (uint256);
}
