// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./VIBEErrors.sol";

/**
 * @title AddressValidation
 * @notice 地址验证工具库
 * @dev 提供统一的地址验证函数，减少代码重复
 */
library AddressValidation {
    /**
     * @notice 验证地址不为零
     * @param addr 要验证的地址
     */
    function requireNonZero(address addr) internal pure {
        if (addr == address(0)) {
            revert VIBEErrors.ZeroAddress();
        }
    }

    /**
     * @notice 验证多个地址不为零
     * @param addresses 地址数组
     */
    function requireAllNonZero(address[] memory addresses) internal pure {
        for (uint256 i = 0; i < addresses.length; i++) {
            if (addresses[i] == address(0)) {
                revert VIBEErrors.ZeroAddress();
            }
        }
    }

    /**
     * @notice 验证地址是合约地址
     * @param addr 要验证的地址
     */
    function requireContract(address addr) internal view {
        requireNonZero(addr);
        if (addr.code.length == 0) {
            revert VIBEErrors.InvalidAddress(addr);
        }
    }

    /**
     * @notice 验证地址不是合约地址（EOA）
     * @param addr 要验证的地址
     */
    function requireEOA(address addr) internal view {
        requireNonZero(addr);
        if (addr.code.length > 0) {
            revert VIBEErrors.InvalidAddress(addr);
        }
    }

    /**
     * @notice 验证两个地址不同
     * @param addr1 第一个地址
     * @param addr2 第二个地址
     */
    function requireDifferent(address addr1, address addr2) internal pure {
        if (addr1 == addr2) {
            revert VIBEErrors.InvalidAddress(addr1);
        }
    }

    /**
     * @notice 验证地址在白名单中
     * @param addr 要验证的地址
     * @param whitelist 白名单映射
     */
    function requireWhitelisted(
        address addr,
        mapping(address => bool) storage whitelist
    ) internal view {
        requireNonZero(addr);
        if (!whitelist[addr]) {
            revert VIBEErrors.InvalidAddress(addr);
        }
    }
}
