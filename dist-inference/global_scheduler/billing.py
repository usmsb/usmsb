"""
Vibe Billing Engine - persisted to SQLite
"""

import time
from dataclasses import dataclass
from typing import Dict

from . import db


@dataclass
class UserBalance:
    """User balance information"""
    user_id: str
    vibe_balance: float = 1000.0
    owed_vibe: float = 0.0


class BillingEngine:
    """
    Vibe Billing Engine

    Billing rules:
    - GPU card time: 0.001 Vibe/second/GPU
    - Token: 0.001 Vibe/1K tokens
    - Platform fee: 30%
    """

    GPU_COST_PER_SECOND = 0.001
    TOKEN_COST_PER_1K = 0.001
    PLATFORM_FEE_RATIO = 0.30

    def __init__(self):
        pass  # All state is in SQLite

    def get_balance(self, user_id: str) -> float:
        """Get user balance (after deducting owed)"""
        balance = self._load_balance(user_id)
        return balance.vibe_balance - balance.owed_vibe

    def get_owed(self, user_id: str) -> float:
        """Get user owed amount"""
        balance = self._load_balance(user_id)
        return balance.owed_vibe

    def _load_balance(self, user_id: str) -> UserBalance:
        """Load balance from SQLite (sync read)"""
        import sqlite3
        conn = sqlite3.connect(db._db_path or "usmsb.db")
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT user_id, vibe_balance, owed_vibe FROM user_balances WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row:
                return UserBalance(user_id=row["user_id"], vibe_balance=row["vibe_balance"], owed_vibe=row["owed_vibe"])
            return UserBalance(user_id=user_id)
        finally:
            conn.close()

    async def _load_balance_async(self, user_id: str) -> UserBalance:
        """Load balance from SQLite (async read)"""
        conn = await db.get_db()
        async with conn.execute(
            "SELECT user_id, vibe_balance, owed_vibe FROM user_balances WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if row:
            return UserBalance(user_id=row["user_id"], vibe_balance=row["vibe_balance"], owed_vibe=row["owed_vibe"])
        return UserBalance(user_id=user_id)

    async def _save_balance(self, balance: UserBalance) -> None:
        """Persist balance to SQLite"""
        conn = await db.get_db()
        await conn.execute(
            """INSERT INTO user_balances (user_id, vibe_balance, owed_vibe, updated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   vibe_balance=excluded.vibe_balance,
                   owed_vibe=excluded.owed_vibe,
                   updated_at=excluded.updated_at""",
            (balance.user_id, balance.vibe_balance, balance.owed_vibe, time.time()),
        )
        await conn.commit()

    def estimate_cost(self, model_name: str, max_tokens: int) -> float:
        estimated_tokens = 500 + max_tokens
        token_cost = (estimated_tokens / 1000) * self.TOKEN_COST_PER_1K
        gpu_cost = 1.0 * self.GPU_COST_PER_SECOND
        return token_cost + gpu_cost

    def calculate_cost(
        self,
        gpu_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        gpu_count: int = 1
    ) -> float:
        gpu_cost = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        total_tokens = prompt_tokens + completion_tokens
        token_cost = (total_tokens / 1000) * self.TOKEN_COST_PER_1K
        total = gpu_cost + token_cost
        print(f"[Billing] Cost calculation: GPU({gpu_seconds}s x {gpu_count})={gpu_cost:.6f}, "
              f"Token({total_tokens})={token_cost:.6f}, Total={total:.6f} Vibe")
        return total

    async def charge(self, user_id: str, cost_vibe: float) -> Dict[str, float]:
        """
        Charge user (writes to SQLite)
        Returns:
            {"charged": xxx, "remaining": yyy, "new_owed": zzz}
        """
        balance = await self._load_balance_async(user_id)
        total_cost = cost_vibe + balance.owed_vibe

        if balance.vibe_balance >= total_cost:
            balance.vibe_balance -= total_cost
            balance.owed_vibe = 0.0
        else:
            balance.owed_vibe = total_cost - balance.vibe_balance
            balance.vibe_balance = 0.0

        await self._save_balance(balance)

        print(f"[Billing] Charged {cost_vibe:.6f} Vibe from {user_id}, "
              f"remaining: {balance.vibe_balance:.6f}, owed: {balance.owed_vibe:.6f}")

        return {
            "charged": cost_vibe,
            "remaining": balance.vibe_balance,
            "new_owed": balance.owed_vibe
        }

    def calculate_node_reward(self, gpu_seconds: float, gpu_count: int = 1) -> float:
        gross = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        net = gross * (1 - self.PLATFORM_FEE_RATIO)
        return net

    async def deposit(self, user_id: str, amount: float):
        """Deposit Vibe (writes to SQLite)"""
        balance = await self._load_balance_async(user_id)
        balance.vibe_balance += amount
        await self._save_balance(balance)
        print(f"[Billing] Deposited {amount} Vibe to {user_id}, "
              f"new balance: {balance.vibe_balance:.6f}")
