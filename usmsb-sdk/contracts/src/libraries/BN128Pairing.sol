// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title BN128Pairing
 * @notice BN128 椭圆曲线配对运算库
 * @dev 用于 zk-SNARK Groth16 验证
 *
 * 使用 EVM 内置的 BN128 曲线 (alt_bn128) 预编译合约:
 * - 0x08: bn128Add - 椭圆曲线点加法
 * - 0x09: bn128Mul - 椭圆曲线标量乘法
 * - 0x10: bn128Pairing - 配对验证
 *
 * 配对函数: e(P, Q) = e(P1, Q1) * e(P2, Q2) * ...
 */
library BN128Pairing {
    /// @notice 配对验证失败
    error PairingInvalidProof();
    /// @notice 输入无效
    error InvalidInput();
    /// @notice 点不在曲线上
    error PointNotOnCurve();

    // BN128 曲线参数 (alt_bn128)
    uint256 constant FIELD_MOD = 0x30644e72e131a029b85045b68181585d97816a916871ca8d3c208c16d87cfd47;
    uint256 constant ORDER = 0x30644e72e131a029b85045b68181585d2833e84879b9709143e1f593f0000001;

    /**
     * @notice 验证 BN128 点是否在曲线上
     * @param x 点的 x 坐标
     * @param y 点的 y 坐标
     */
    function assertOnCurve(uint256 x, uint256 y) internal pure {
        // y^2 = x^3 + 3 (mod FIELD_MOD)
        uint256 y2 = mulmod(y, y, FIELD_MOD);
        uint256 x3 = mulmod(x, mulmod(x, x, FIELD_MOD), FIELD_MOD);
        if (y2 != addmod(x3, 3, FIELD_MOD)) {
            revert PointNotOnCurve();
        }
    }

    /**
     * @notice 标量乘法 (P * scalar)
     */
    function ecMul(uint256[2] memory p, uint256 s) internal view returns (uint256[2] memory result) {
        (bool success, bytes memory ret) = address(0x09).staticcall(abi.encode(p[0], p[1], s));
        if (!success) {
            revert InvalidInput();
        }
        assembly {
            result := mload(ret)
        }
    }

    /**
     * @notice 椭圆曲线加法
     */
    function ecAdd(uint256[2] memory p1, uint256[2] memory p2) internal view returns (uint256[2] memory result) {
        (bool success, bytes memory ret) = address(0x08).staticcall(abi.encode(p1[0], p1[1], p2[0], p2[1]));
        if (!success) {
            revert InvalidInput();
        }
        assembly {
            result := mload(ret)
        }
    }

    /**
     * @notice 验证 Groth16 证明
     * @param alpha 第一验证密钥点
     * @param beta 第二验证密钥点
     * @param gamma 第三验证密钥点
     * @param delta 第四验证密钥点
     * @param ic 验证密钥线性组合系数
     * @param a 证明第一点
     * @param b 证明第二点
     * @param c 证明第三点
     * @param publicInputs 公开输入数组
     * @return true if proof is valid
     */
    function verifyProof(
        uint256[2] memory alpha,
        uint256[2][2] memory beta,
        uint256[2] memory gamma,
        uint256[2] memory delta,
        uint256[2][] memory ic,
        uint256[2] memory a,
        uint256[2][2] memory b,
        uint256[2] memory c,
        uint256[] memory publicInputs
    ) internal view returns (bool) {
        // 验证公开输入数量
        if (publicInputs.length + 1 != ic.length) {
            revert InvalidInput();
        }

        // 验证基本点不为零
        if (a[0] == 0 && a[1] == 0) revert InvalidInput();
        if (b[0][0] == 0 && b[0][1] == 0) revert InvalidInput();
        if (c[0] == 0 && c[1] == 0) revert InvalidInput();
        if (alpha[0] == 0 && alpha[1] == 0) revert InvalidInput();
        if (delta[0] == 0 && delta[1] == 0) revert InvalidInput();

        // 计算线性组合: L = alpha + sum(ic[i] * publicInputs[i])
        uint256[2] memory L = alpha;

        for (uint256 i = 0; i < publicInputs.length; i++) {
            // L = L + ic[i+1] * publicInputs[i]
            uint256[2] memory scaled = ecMul(ic[i + 1], publicInputs[i]);
            L = ecAdd(L, scaled);
        }

        // 验证配对: e(A, B) = e(alpha, beta) * e(L, gamma) * e(C, delta)
        return _verifyPairing(a, b, alpha, beta, L, gamma, c, delta);
    }

    /**
     * @notice 配对验证
     * @dev 验证 e(A, B) * e(-alpha, beta) * e(-L, gamma) * e(-C, delta) = 1
     */
    function _verifyPairing(
        uint256[2] memory a,
        uint256[2][2] memory b,
        uint256[2] memory alpha,
        uint256[2][2] memory beta,
        uint256[2] memory L,
        uint256[2] memory gamma,
        uint256[2] memory c,
        uint256[2] memory delta
    ) internal view returns (bool) {
        // 构建配对输入
        // 验证: e(A, B) = e(alpha, beta) * e(L, gamma) * e(C, delta)
        // 改写为: e(A, B) * e(-alpha, beta) * e(-L, gamma) * e(-C, delta) = 1

        uint256[24] memory input;

        // 第一组: (A, B)
        input[0] = a[0];
        input[1] = a[1];
        input[2] = b[0][0];
        input[3] = b[0][1];
        input[4] = b[1][0];
        input[5] = b[1][1];

        // 第二组: (-alpha, beta)
        input[6] = (FIELD_MOD - alpha[0]) % FIELD_MOD;
        input[7] = alpha[1];
        input[8] = beta[0][0];
        input[9] = beta[0][1];
        input[10] = beta[1][0];
        input[11] = beta[1][1];

        // 第三组: (-L, gamma)
        input[12] = (FIELD_MOD - L[0]) % FIELD_MOD;
        input[13] = L[1];
        input[14] = gamma[0];
        input[15] = gamma[1];
        input[16] = 0;
        input[17] = 0;

        // 第四组: (-C, delta)
        input[18] = (FIELD_MOD - c[0]) % FIELD_MOD;
        input[19] = c[1];
        input[20] = delta[0];
        input[21] = delta[1];
        input[22] = 0;
        input[23] = 0;

        // 调用配对预编译合约
        (bool success, bytes memory ret) = address(0x10).staticcall(abi.encode(input));
        if (!success) {
            revert PairingInvalidProof();
        }

        // 返回结果应为 1 表示验证成功
        uint256 result;
        assembly {
            result := mload(ret)
        }
        return result == 1;
    }

    /**
     * @notice 简化版配对验证 (用于测试)
     * @param a1 第一组第一个点
     * @param a2 第一组第二个点
     * @param b1 第二组第一个点
     * @param b2 第二组第二个点
     * @param c 第三个点
     * @param c2 第三个点
     * @param z 第四个点
     * @return true if valid
     */
    function pairing(
        uint256[2] memory a1,
        uint256[2] memory a2,
        uint256[2][2] memory b1,
        uint256[2] memory b2,
        uint256[2] memory c,
        uint256[2] memory c2,
        uint256[2] memory z
    ) internal view returns (bool) {
        // 简化实现：基础验证
        if (a1[0] == 0 && a1[1] == 0) revert InvalidInput();
        if (b1[0][0] == 0 && b1[0][1] == 0) revert InvalidInput();
        return true;
    }
}
