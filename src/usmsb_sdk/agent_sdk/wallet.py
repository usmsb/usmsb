"""
Wallet Module

Manages agent wallet, staking, and transactions.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.agent_sdk.platform_client import PlatformClient

logger = logging.getLogger(__name__)


class StakeStatus(Enum):
    """Stake status"""
    NONE = "none"
    STAKED = "staked"
    UNSTAKING = "unstaking"
    LOCKED = "locked"


class TransactionStatus(Enum):
    """Transaction status"""
    CREATED = "created"
    ESCROWED = "escrowed"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    DISPUTED = "disputed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class TransactionType(Enum):
    """Transaction type"""
    SERVICE_PAYMENT = "service_payment"
    STAKE = "stake"
    UNSTAKE = "unstake"
    REFUND = "refund"
    REWARD = "reward"


@dataclass
class WalletBalance:
    """Wallet balance information"""
    available_balance: float
    staked_amount: float
    locked_amount: float
    pending_incoming: float
    pending_outgoing: float

    @property
    def total_balance(self) -> float:
        return self.available_balance + self.staked_amount + self.locked_amount

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WalletBalance":
        return cls(
            available_balance=data.get("available_balance", data.get("vibe_balance", 0)),
            staked_amount=data.get("staked_amount", data.get("stake", 0)),
            locked_amount=data.get("locked_amount", data.get("locked_stake", 0)),
            pending_incoming=data.get("pending_incoming", 0),
            pending_outgoing=data.get("pending_outgoing", 0),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "available_balance": self.available_balance,
            "staked_amount": self.staked_amount,
            "locked_amount": self.locked_amount,
            "pending_incoming": self.pending_incoming,
            "pending_outgoing": self.pending_outgoing,
            "total_balance": self.total_balance,
        }


@dataclass
class StakeInfo:
    """Stake information"""
    staked_amount: float
    stake_status: str
    locked_stake: float
    unlock_available_at: datetime | None
    reputation_boost: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StakeInfo":
        unlock_at = None
        if data.get("unlock_available_at"):
            if isinstance(data["unlock_available_at"], (int, float)):
                unlock_at = datetime.fromtimestamp(data["unlock_available_at"])
            else:
                unlock_at = data["unlock_available_at"]

        staked = data.get("staked_amount", data.get("stake", 0))
        reputation = min(0.5 + (staked / 1000), 1.0)

        return cls(
            staked_amount=staked,
            stake_status=data.get("stake_status", "none"),
            locked_stake=data.get("locked_stake", 0),
            unlock_available_at=unlock_at,
            reputation_boost=reputation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "staked_amount": self.staked_amount,
            "stake_status": self.stake_status,
            "locked_stake": self.locked_stake,
            "unlock_available_at": self.unlock_available_at.isoformat() if self.unlock_available_at else None,
            "reputation_boost": self.reputation_boost,
        }


@dataclass
class Transaction:
    """Transaction record"""
    tx_id: str
    tx_type: str
    amount: float
    counterparty_id: str
    status: str
    title: str | None
    description: str | None
    platform_fee: float
    created_at: datetime | None
    completed_at: datetime | None
    rating: int | None
    review: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Transaction":
        created_at = None
        if data.get("created_at"):
            if isinstance(data["created_at"], (int, float)):
                created_at = datetime.fromtimestamp(data["created_at"])
            else:
                created_at = data["created_at"]

        completed_at = None
        if data.get("completed_at"):
            if isinstance(data["completed_at"], (int, float)):
                completed_at = datetime.fromtimestamp(data["completed_at"])
            else:
                completed_at = data["completed_at"]

        return cls(
            tx_id=data.get("id", ""),
            tx_type=data.get("transaction_type", "service_payment"),
            amount=data.get("amount", 0),
            counterparty_id=data.get("seller_id") if data.get("seller_id") != data.get("buyer_id") else data.get("buyer_id"),
            status=data.get("status", "created"),
            title=data.get("title"),
            description=data.get("description"),
            platform_fee=data.get("platform_fee", 0),
            created_at=created_at,
            completed_at=completed_at,
            rating=data.get("rating"),
            review=data.get("review"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "amount": self.amount,
            "counterparty_id": self.counterparty_id,
            "status": self.status,
            "title": self.title,
            "description": self.description,
            "platform_fee": self.platform_fee,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rating": self.rating,
            "review": self.review,
        }


@dataclass
class WalletLimits:
    """Wallet spending limits"""
    max_per_tx: float
    daily_limit: float
    daily_spent: float

    @property
    def daily_remaining(self) -> float:
        return max(0, self.daily_limit - self.daily_spent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WalletLimits":
        return cls(
            max_per_tx=data.get("max_per_tx", 500),
            daily_limit=data.get("daily_limit", 1000),
            daily_spent=data.get("daily_spent", 0),
        )


@dataclass
class StakeResult:
    """Result of a stake operation"""
    success: bool
    amount: float
    total_staked: float
    new_reputation: float
    message: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StakeResult":
        return cls(
            success=data.get("success", False),
            amount=data.get("amount", 0),
            total_staked=data.get("total_stake", 0),
            new_reputation=data.get("reputation", 0.5),
            message=data.get("message", ""),
        )


class WalletManager:
    """
    P3-2: 钱包管理器（真实 Web3 集成）

    支持两种模式：
    1. Real Mode: 使用 VIBEToken（Base Sepolia 真实链）
    2. Mock Mode: 使用 PlatformClient（向后兼容）

    Features:
    - 余额查询（VIBEToken）
    - 质押/解锁（VIBStaking 合约）
    - 交易历史（Transfer 事件）
    - 支出限制
    """

    def __init__(
        self,
        platform_client: PlatformClient | None = None,
        vibe_token=None,  # P3-2: VIBEToken 实例
        private_key: str | None = None,  # P3-2: 钱包私钥
        logger: logging.Logger | None = None,
    ):
        self._platform = platform_client
        self._vibe_token = vibe_token  # P3-2: 真实 Web3
        self._private_key = private_key
        self.logger = logger or logging.getLogger(__name__)
        self._initialized = False

        # Local cache
        self._balance_cache: WalletBalance | None = None
        self._stake_cache: StakeInfo | None = None

    async def init(self) -> None:
        """
        P3-2: 异步初始化

        1. 检查 VIBEToken 连接状态
        2. 如果有私钥，从私钥派生地址
        3. 预热余额缓存
        """
        if self._vibe_token:
            if not self._vibe_token.is_connected:
                self.logger.warning("[WalletManager] VIBEToken not connected, will retry on demand")
            else:
                self.logger.info(
                    f"[WalletManager] Connected to {self._vibe_token.rpc_url[:40]}..."
                )
                # 预热余额（如果有地址）
                if self._private_key:
                    try:
                        account = self._vibe_token.w3.eth.account.from_key(self._private_key)
                        balance = self._vibe_token.get_balance(account.address)
                        self._balance_cache = WalletBalance(
                            available_balance=balance.balance_vibe,
                            staked_amount=0,
                            locked_amount=0,
                            pending_incoming=0,
                            pending_outgoing=0,
                        )
                        self.logger.info(
                            f"[WalletManager] Balance: {balance.balance_vibe:.4f} VIBE"
                        )
                    except Exception as e:
                        self.logger.warning(f"[WalletManager] Failed to fetch initial balance: {e}")

        self._initialized = True

    # ─── 余额 ────────────────────────────────────────────────────────────────

    async def get_balance(self, use_cache: bool = False) -> WalletBalance:
        """
        查询钱包余额

        优先使用 VIBEToken（真实链），回退到 PlatformClient。
        """
        if use_cache and self._balance_cache:
            return self._balance_cache

        # P3-2: 真实 Web3 查询
        if self._vibe_token and self._private_key:
            try:
                account = self._vibe_token.w3.eth.account.from_key(self._private_key)
                balance = self._vibe_token.get_balance(account.address)
                self._balance_cache = WalletBalance(
                    available_balance=balance.balance_vibe,
                    staked_amount=0,  # 质押通过 VIBStaking 合约
                    locked_amount=0,
                    pending_incoming=0,
                    pending_outgoing=0,
                )
                return self._balance_cache
            except Exception as e:
                self.logger.warning(f"[WalletManager] Failed to get balance from chain: {e}")

        # 回退到平台
        if self._platform:
            response = await self._platform.get_registration_status()
            if response.success and response.data:
                self._balance_cache = WalletBalance.from_dict(response.data)
                return self._balance_cache

        return WalletBalance(0, 0, 0, 0, 0)

    async def refresh_balance(self) -> WalletBalance:
        """强制刷新余额"""
        self._balance_cache = None
        return await self.get_balance(use_cache=False)

    # ─── P2P 转账 ────────────────────────────────────────────────────────────

    async def transfer(self, to_address: str, amount: float) -> dict[str, Any]:
        """P2P 转账 VIBE（真实链上 VIBEToken.transfer）。

        这是 v3.0 补的缺口：原 WalletManager 只有 stake/balance，无法做服务结算转账。
        无链/无私钥时优雅降级（返回 success=False，不抛异常），上层可回退到链下账本。

        Returns:
            {"success": bool, "tx_hash"?: str, "explorer_url"?: str, "reason"?: str}
        """
        if amount <= 0:
            return {"success": False, "reason": "amount must be positive"}

        # 支出前先过限额闸门（与 harness guard 一致的安全边界）
        can = await self.check_can_spend(amount)
        if not can.get("can_spend"):
            return {"success": False, "reason": can.get("reason") or "spend not allowed"}

        if not self._vibe_token or not self._private_key:
            return {"success": False, "reason": "no web3 connection"}

        try:
            result = self._vibe_token.transfer(self._private_key, to_address, amount)
            self._balance_cache = None  # 余额已变，清缓存
            return result
        except Exception as e:  # noqa: BLE001
            self.logger.error(f"[WalletManager] transfer failed: {e}")
            return {"success": False, "reason": str(e)}

    # ─── 质押 ────────────────────────────────────────────────────────────────

    async def get_stake_info(self) -> StakeInfo:
        """
        查询质押信息（P3-2: 通过 VIBStaking 合约）
        """
        if self._vibe_token and self._private_key:
            try:
                # 从环境变量获取质押合约地址
                import os as _os
                staking_address = _os.environ.get(
                    "USMSB_VIBSTAKING_ADDRESS",
                    "0x1901Ab564341F9VibStaking"  # 回退地址
                )
                account = self._vibe_token.w3.eth.account.from_key(self._private_key)
                checksum_addr = self._vibe_token.address_to_checksum(account.address)

                # 读取质押合约的 stakeOf
                from usmsb_sdk.blockchain.contracts import VIBSTAKING_ABI
                staking_contract = self._vibe_token.w3.eth.contract(
                    address=self._vibe_token.address_to_checksum(staking_address),
                    abi=VIBSTAKING_ABI
                )
                stake_wei = staking_contract.functions.stakeOf(checksum_addr).call()
                stake_amount = self._vibe_token.from_wei(stake_wei)

                self._stake_cache = StakeInfo(
                    staked_amount=stake_amount,
                    stake_status="staked" if stake_amount > 0 else "none",
                    locked_stake=0,
                    unlock_available_at=None,
                    reputation_boost=min(0.5 + (stake_amount / 1000), 1.0),
                )
                return self._stake_cache
            except Exception as e:
                self.logger.warning(f"[WalletManager] Failed to get stake info: {e}")

        # 回退到平台
        if self._platform:
            response = await self._platform.get_registration_status()
            if response.success and response.data:
                self._stake_cache = StakeInfo.from_dict(response.data)
                return self._stake_cache

        return StakeInfo(0, "none", 0, None, 0.5)

    async def stake(self, amount: float, lock_period: int = 0) -> StakeResult:
        """
        质押 VIBE 代币（P3-2: 通过 VIBStaking 合约）

        Args:
            amount: 质押数量（VIBE）
            lock_period: 锁定期（0=无锁, 1=30天, 2=90天, 3=180天, 4=365天）

        Returns:
            StakeResult with operation status
        """
        if amount <= 0:
            return StakeResult(False, 0, 0, 0.5, "Amount must be positive")

        if not self._vibe_token or not self._private_key:
            # 回退到平台质押
            if self._platform:
                response = await self._platform.stake(amount)
                if response.success and response.data:
                    result = StakeResult.from_dict(response.data)
                    result.amount = amount
                    self._balance_cache = None
                    self._stake_cache = None
                    return result
            return StakeResult(False, amount, 0, 0.5, "No Web3 connection")

        try:
            import os as _os
            staking_address = _os.environ.get(
                "USMSB_VIBSTAKING_ADDRESS",
                "0x1901Ab564341F9VibStaking"
            )
            from usmsb_sdk.blockchain.contracts import VIBSTAKING_ABI

            account = self._vibe_token.w3.eth.account.from_key(self._private_key)
            staking_contract = self._vibe_token.w3.eth.contract(
                address=self._vibe_token.address_to_checksum(staking_address),
                abi=VIBSTAKING_ABI
            )

            amount_wei = self._vibe_token.to_wei(amount)
            nonce = self._vibe_token.w3.eth.get_transaction_count(account.address)

            tx = staking_contract.functions.stake(amount_wei, lock_period).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 150000,
                "maxFeePerGas": self._vibe_token.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self._vibe_token.w3.eth.max_priority_fee,
                "chainId": self._vibe_token.w3.eth.chain_id,
            })

            signed = self._vibe_token.w3.eth.account.sign_transaction(tx, self._private_key)
            tx_hash = self._vibe_token.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self._vibe_token.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.logger.info(f"[WalletManager] Staked {amount} VIBE: {tx_hash.hex()}")
            self._balance_cache = None
            self._stake_cache = None

            return StakeResult(
                success=receipt.status == 1,
                amount=amount,
                total_staked=amount,  # 精确值需重新查询
                new_reputation=min(0.5 + (amount / 1000), 1.0),
                message=f"Staked {amount} VIBE. Tx: {tx_hash.hex()[:16]}...",
            )
        except Exception as e:
            self.logger.error(f"[WalletManager] Stake failed: {e}")
            return StakeResult(False, amount, 0, 0.5, str(e))

    async def unstake(self, amount: float) -> StakeResult:
        """
        解除质押（P3-2: 通过 VIBStaking 合约）
        """
        if amount <= 0:
            return StakeResult(False, amount, 0, 0.5, "Amount must be positive")

        if not self._vibe_token or not self._private_key:
            return StakeResult(False, amount, 0, 0.5, "No Web3 connection")

        try:
            import os as _os
            staking_address = _os.environ.get(
                "USMSB_VIBSTAKING_ADDRESS",
                "0x1901Ab564341F9VibStaking"
            )
            from usmsb_sdk.blockchain.contracts import VIBSTAKING_ABI

            account = self._vibe_token.w3.eth.account.from_key(self._private_key)
            staking_contract = self._vibe_token.w3.eth.contract(
                address=self._vibe_token.address_to_checksum(staking_address),
                abi=VIBSTAKING_ABI
            )

            amount_wei = self._vibe_token.to_wei(amount)
            nonce = self._vibe_token.w3.eth.get_transaction_count(account.address)

            # unstake 功能
            tx = staking_contract.functions.unstake(amount_wei).build_transaction({
                "from": account.address,
                "nonce": nonce,
                "gas": 150000,
                "maxFeePerGas": self._vibe_token.w3.eth.gas_price * 2,
                "maxPriorityFeePerGas": self._vibe_token.w3.eth.max_priority_fee,
                "chainId": self._vibe_token.w3.eth.chain_id,
            })

            signed = self._vibe_token.w3.eth.account.sign_transaction(tx, self._private_key)
            tx_hash = self._vibe_token.w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = self._vibe_token.w3.eth.wait_for_transaction_receipt(tx_hash)

            self.logger.info(f"[WalletManager] Unstaked {amount} VIBE: {tx_hash.hex()}")
            self._balance_cache = None
            self._stake_cache = None

            return StakeResult(
                success=receipt.status == 1,
                amount=amount,
                total_staked=0,
                new_reputation=0.5,
                message=f"Unstaked {amount} VIBE. Tx: {tx_hash.hex()[:16]}...",
            )
        except Exception as e:
            self.logger.error(f"[WalletManager] Unstake failed: {e}")
            return StakeResult(False, amount, 0, 0.5, str(e))

    async def get_unstake_status(self) -> dict[str, Any]:
        """Get unstaking status and unlock time"""
        stake_info = await self.get_stake_info()
        return {
            "status": stake_info.stake_status,
            "locked_amount": stake_info.locked_stake,
            "unlock_available_at": stake_info.unlock_available_at.isoformat() if stake_info.unlock_available_at else None,
        }

    # ==================== Transactions ====================

    async def get_transaction_history(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Transaction]:
        """
        获取交易历史（P3-2: 通过 VIBEToken Transfer 事件）

        Args:
            status: 状态过滤（暂不支持，保留接口）
            limit: 最大返回数量

        Returns:
            Transaction 对象列表
        """
        if not self._vibe_token or not self._private_key:
            return []

        try:
            account = self._vibe_token.w3.eth.account.from_key(self._private_key)
            history_raw = self._vibe_token.get_transfer_history(account.address)

            txs = []
            for h in history_raw[:limit]:
                tx = Transaction(
                    tx_id=h["tx_hash"],
                    tx_type="transfer",
                    amount=h["value_vibe"],
                    counterparty_id=h["to"] if h["from"].lower() == account.address.lower() else h["from"],
                    status="completed",
                    title=None,
                    description=None,
                    platform_fee=0,
                    created_at=None,
                    completed_at=None,
                    rating=None,
                    review=None,
                )
                txs.append(tx)
            return txs
        except Exception as e:
            self.logger.warning(f"[WalletManager] Failed to get transaction history: {e}")
            return []

    async def get_pending_transactions(self) -> list[Transaction]:
        """Get pending (non-completed) transactions"""
        all_tx = await self.get_transaction_history()
        pending_statuses = ["created", "escrowed", "in_progress", "delivered", "disputed"]
        return [tx for tx in all_tx if tx.status in pending_statuses]

    async def get_transaction(self, tx_id: str) -> Transaction | None:
        """Get a specific transaction by hash"""
        if not self._vibe_token:
            return None
        try:
            receipt = self._vibe_token.w3.eth.get_transaction_receipt(tx_id)
            if not receipt:
                return None
            return Transaction(
                tx_id=tx_id,
                tx_type="unknown",
                amount=0,
                counterparty_id="",
                status="completed" if receipt.status == 1 else "failed",
                title=None,
                description=None,
                platform_fee=0,
                created_at=None,
                completed_at=None,
                rating=None,
                review=None,
            )
        except Exception:
            return None

    # ==================== Limits ====================

    async def get_limits(self) -> WalletLimits:
        """Get wallet spending limits"""
        # TODO: Get from platform
        return WalletLimits(
            max_per_tx=500,
            daily_limit=1000,
            daily_spent=0,
        )

    async def check_can_spend(self, amount: float) -> dict[str, Any]:
        """
        Check if agent can spend specified amount.

        Returns:
            Dict with 'can_spend' boolean and 'reason' if not
        """
        balance = await self.get_balance()
        limits = await self.get_limits()

        if amount > balance.available_balance:
            return {"can_spend": False, "reason": "Insufficient balance"}

        if amount > limits.max_per_tx:
            return {"can_spend": False, "reason": f"Amount exceeds per-transaction limit of {limits.max_per_tx}"}

        if amount > limits.daily_remaining:
            return {"can_spend": False, "reason": f"Amount exceeds remaining daily limit of {limits.daily_remaining}"}

        return {"can_spend": True, "reason": None}

    # ==================== Summary ====================

    async def get_wallet_summary(self) -> dict[str, Any]:
        """Get complete wallet summary"""
        balance = await self.get_balance()
        stake_info = await self.get_stake_info()
        limits = await self.get_limits()

        return {
            "balance": balance.to_dict(),
            "stake": stake_info.to_dict(),
            "limits": {
                "max_per_tx": limits.max_per_tx,
                "daily_limit": limits.daily_limit,
                "daily_spent": limits.daily_spent,
                "daily_remaining": limits.daily_remaining,
            },
            "reputation": stake_info.reputation_boost,
        }
