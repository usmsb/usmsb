"""
Wallet Manager - 钱包管理器（真实 VIBE Token 实现）

管理 Meta Agent 的区块链钱包，基于 Base Sepolia + VIBE Token。
"""

import logging
import os
from typing import Any

from usmsb_sdk.blockchain.vibe_token import (
    VIBEToken,
    VIBEBalance,
    get_vibe_token,
    BASE_SEPOLIA_CHAIN_ID,
    VIBE_TOKEN_ADDRESS,
)

logger = logging.getLogger(__name__)


class WalletManager:
    """
    Meta Agent 区块链钱包管理器。

    管理钱包的生命周期：创建、查询、转账、授权等。
    支持 Base Sepolia 测试网上的 VIBE Token（ERC-20）。

    环境变量：
        USMSB_WALLET_PRIVATE_KEY: 钱包私钥（用于签名交易）
        USMSB_WALLET_ADDRESS: 钱包地址（可选，不提供则从私钥派生）
    """

    def __init__(self, config: Any | None = None):
        self.config = config
        self._vibe: VIBEToken | None = None
        self._address: str | None = None

    # ── 初始化 ────────────────────────────────────────────────

    async def init(self) -> None:
        """初始化钱包管理器，连接 VIBE Token。"""
        private_key = os.environ.get("USMSB_WALLET_PRIVATE_KEY")
        self._vibe = get_vibe_token(private_key=private_key)

        # 如果配置了地址则使用，否则从私钥派生
        self._address = os.environ.get("USMSB_WALLET_ADDRESS")

        connected = self._vibe.is_connected
        logger.info(
            f"WalletManager initialized: chain=base_sepolia, "
            f"contract={VIBE_TOKEN_ADDRESS}, connected={connected}"
        )

        if private_key and not self._address:
            try:
                acct = self._vibe.w3.eth.account.from_key(private_key)
                self._address = acct.address
                logger.info(f"Derived wallet address: {self._address}")
            except Exception as e:
                logger.warning(f"Failed to derive address from private key: {e}")

    # ── 钱包操作 ──────────────────────────────────────────────

    async def create_wallet(self) -> dict[str, Any]:
        """
        创建新钱包。

        Returns:
            dict: 包含 address, private_key（仅本次返回，请妥善保管）, public_key
        """
        if self._vibe is None:
            await self.init()

        wallet = self._vibe.create_wallet()
        self._address = wallet["address"]
        logger.info(f"Created new wallet: {self._address}")
        return wallet

    async def get_balance(self, address: str | None = None) -> VIBEBalance:
        """
        查询 VIBE 余额。

        Args:
            address: 钱包地址，None 则查本钱包

        Returns:
            VIBEBalance 对象
        """
        if self._vibe is None:
            await self.init()

        addr = address or self._address
        if not addr:
            raise ValueError("No address specified and no wallet configured")
        return self._vibe.get_balance(addr)

    async def get_native_balance(self) -> dict[str, Any]:
        """查询本钱包 ETH 原生余额（用于支付 gas）。"""
        if self._vibe is None:
            await self.init()
        if not self._address:
            return {"success": False, "error": "No wallet address configured"}

        try:
            balance_wei = self._vibe.w3.eth.get_balance(self._address)
            balance_eth = self._vibe.w3.from_wei(balance_wei, "ether")
            return {
                "success": True,
                "address": self._address,
                "balance_eth": float(balance_eth),
                "balance_wei": balance_wei,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── 转账 ─────────────────────────────────────────────────

    async def transfer(
        self,
        to_address: str,
        amount_vibe: float,
    ) -> dict[str, Any]:
        """
        转账 VIBE 代币。

        Args:
            to_address: 收款地址
            amount_vibe: 转账数量（VIBE）

        Returns:
            dict: 包含 success, tx_hash, explorer_url
        """
        if self._vibe is None:
            await self.init()

        private_key = os.environ.get("USMSB_WALLET_PRIVATE_KEY")
        if not private_key:
            return {
                "success": False,
                "error": "未配置 USMSB_WALLET_PRIVATE_KEY，无法发起转账",
            }

        result = self._vibe.transfer(
            from_private_key=private_key,
            to_address=to_address,
            amount_vibe=amount_vibe,
        )
        return {
            "success": result["success"],
            "tx_hash": result["tx_hash"],
            "block_number": result.get("block_number"),
            "explorer_url": result.get("explorer_url"),
            "amount_vibe": amount_vibe,
            "to_address": to_address,
        }

    async def approve(
        self,
        spender_address: str,
        amount_vibe: float,
    ) -> dict[str, Any]:
        """
        授权代币给其他地址。

        Args:
            spender_address: 被授权地址
            amount_vibe: 授权数量

        Returns:
            dict: 包含 success, tx_hash, explorer_url
        """
        if self._vibe is None:
            await self.init()

        private_key = os.environ.get("USMSB_WALLET_PRIVATE_KEY")
        if not private_key:
            return {
                "success": False,
                "error": "未配置 USMSB_WALLET_PRIVATE_KEY，无法发起授权",
            }

        result = self._vibe.approve(
            private_key=private_key,
            spender_address=spender_address,
            amount_vibe=amount_vibe,
        )
        return {
            "success": result["success"],
            "tx_hash": result["tx_hash"],
            "explorer_url": result.get("explorer_url"),
            "amount_vibe": amount_vibe,
            "spender_address": spender_address,
        }

    # ── 查询 ─────────────────────────────────────────────────

    async def get_transfer_history(
        self,
        address: str | None = None,
        from_block: int = 0,
    ) -> list[dict[str, Any]]:
        """
        获取转账历史。

        Args:
            address: 钱包地址，None 则查本钱包
            from_block: 起始区块号

        Returns:
            list[dict]: 转账记录列表
        """
        if self._vibe is None:
            await self.init()

        addr = address or self._address
        if not addr:
            return []
        return self._vibe.get_transfer_history(addr, from_block=from_block)

    async def get_total_supply(self) -> float:
        """获取 VIBE Token 总供应量。"""
        if self._vibe is None:
            await self.init()
        return self._vibe.get_total_supply()

    async def get_chain_info(self) -> dict[str, Any]:
        """获取链信息。"""
        if self._vibe is None:
            await self.init()

        return {
            "chain": "base_sepolia",
            "chain_id": BASE_SEPOLIA_CHAIN_ID,
            "block_number": self._vibe.w3.eth.block_number,
            "is_connected": self._vibe.is_connected,
            "contract": VIBE_TOKEN_ADDRESS,
            "wallet_address": self._address,
        }

    # ── 属性 ─────────────────────────────────────────────────

    @property
    def address(self) -> str | None:
        """当前钱包地址。"""
        return self._address

    @property
    def is_configured(self) -> bool:
        """是否已配置私钥。"""
        return bool(os.environ.get("USMSB_WALLET_PRIVATE_KEY"))

    @property
    def vibe_token(self) -> VIBEToken | None:
        """底层 VIBEToken 实例。"""
        return self._vibe
