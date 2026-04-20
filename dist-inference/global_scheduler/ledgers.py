"""
Ledgers for tracking inference transactions, earnings, and withdrawals.
All data persisted to SQLite via db.py.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

from . import db

MAX_INFERENCE_RECORDS = 10000


class WithdrawalStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class InferenceRecord:
    """Record of a single inference transaction"""
    request_id: str
    node_id: str
    user_id: str
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    gpu_seconds: float
    cost_vibe: float
    node_reward_vibe: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class DailyEarnings:
    """Daily earnings for a node"""
    date: str  # "YYYY-MM-DD"
    revenue_vibe: float
    requests: int


@dataclass
class NodeEarnings:
    """Per-node earnings tracking"""
    node_id: str
    wallet_address: str
    daily_earnings: List[DailyEarnings] = field(default_factory=list)
    total_revenue_vibe: float = 0.0
    total_requests: int = 0
    last_active: float = field(default_factory=time.time)


@dataclass
class WithdrawalRequest:
    """Withdrawal request record"""
    id: str
    wallet_address: str
    amount_vibe: float
    status: WithdrawalStatus = WithdrawalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    tx_hash: Optional[str] = None


@dataclass
class UserRecord:
    """Per-user consumption tracking"""
    wallet_address: str
    total_consumption_vibe: float = 0.0
    total_requests: int = 0
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


@dataclass
class PlatformSettings:
    """Platform-wide settings"""
    platform_name: str = "USMSB Distributed Inference"
    scheduler_url: str = "http://localhost:8000"
    gpu_rate: float = 0.001
    token_rate: float = 0.001
    platform_share: float = 0.30


class InferenceLedger:
    """Tracks every inference transaction — persisted to SQLite."""

    async def record(
        self,
        request_id: str,
        node_id: str,
        user_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        gpu_seconds: float,
        cost_vibe: float,
        node_reward_vibe: float,
    ) -> InferenceRecord:
        record = InferenceRecord(
            request_id=request_id,
            node_id=node_id,
            user_id=user_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            gpu_seconds=gpu_seconds,
            cost_vibe=cost_vibe,
            node_reward_vibe=node_reward_vibe,
        )
        conn = await db.get_db()
        await conn.execute(
            """INSERT INTO inference_records
               (request_id, node_id, user_id, model_name, prompt_tokens,
                completion_tokens, gpu_seconds, cost_vibe, node_reward_vibe, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (request_id, node_id, user_id, model_name, prompt_tokens,
             completion_tokens, gpu_seconds, cost_vibe, node_reward_vibe, record.timestamp),
        )
        await conn.commit()

        # Trim if over cap
        count_row = await conn.execute("SELECT COUNT(*) FROM inference_records")
        count = (await count_row.fetchone())[0]
        if count > MAX_INFERENCE_RECORDS:
            excess = count - MAX_INFERENCE_RECORDS
            await conn.execute(
                f"""DELETE FROM inference_records WHERE id IN
                    (SELECT id FROM inference_records ORDER BY timestamp ASC LIMIT {excess})"""
            )
            await conn.commit()

        return record

    async def get_records(
        self,
        node_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InferenceRecord]:
        conn = await db.get_db()
        cols = "request_id, node_id, user_id, model_name, prompt_tokens, completion_tokens, gpu_seconds, cost_vibe, node_reward_vibe, timestamp"
        query = f"SELECT {cols} FROM inference_records WHERE 1=1"
        params: List[Any] = []
        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if request_id:
            query += " AND request_id = ?"
            params.append(request_id)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with conn.execute(query, params) as cur:
            rows = await cur.fetchall()
        return [InferenceRecord(**dict(r)) for r in rows]

    async def count(
        self,
        node_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> int:
        conn = await db.get_db()
        query = "SELECT COUNT(*) FROM inference_records WHERE 1=1"
        params: List[Any] = []
        if node_id:
            query += " AND node_id = ?"
            params.append(node_id)
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        async with conn.execute(query, params) as cur:
            row = await cur.fetchone()
        return row[0] if row else 0

    async def get_total_stats(
        self,
        node_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = await db.get_db()
        if node_id:
            async with conn.execute(
                """SELECT COUNT(*), COALESCE(SUM(cost_vibe),0), COALESCE(SUM(node_reward_vibe),0)
                   FROM inference_records WHERE node_id = ?""",
                (node_id,),
            ) as cur:
                row = await cur.fetchone()
        else:
            async with conn.execute(
                """SELECT COUNT(*), COALESCE(SUM(cost_vibe),0), COALESCE(SUM(node_reward_vibe),0)
                   FROM inference_records"""
            ) as cur:
                row = await cur.fetchone()
        return {
            "total_requests": row[0] if row else 0,
            "total_cost_vibe": row[1] if row else 0.0,
            "total_node_reward_vibe": row[2] if row else 0.0,
        }


class NodeEarningsLedger:
    """Tracks per-node earnings — persisted to SQLite."""

    def _date_str(self, t: float) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d")

    async def ensure_node(self, node_id: str, wallet_address: str = "") -> NodeEarnings:
        conn = await db.get_db()
        await conn.execute(
            """INSERT OR IGNORE INTO node_earnings
               (node_id, wallet_address, total_revenue_vibe, total_requests, last_active)
               VALUES (?, ?, 0.0, 0, ?)""",
            (node_id, wallet_address, time.time()),
        )
        await conn.commit()
        return await self._load_earnings(node_id)

    async def _load_earnings(self, node_id: str) -> Optional[NodeEarnings]:
        conn = await db.get_db()
        async with conn.execute(
            """SELECT node_id, wallet_address, total_revenue_vibe, total_requests, last_active
               FROM node_earnings WHERE node_id = ?""",
            (node_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        async with conn.execute(
            """SELECT date, revenue_vibe, requests FROM node_daily_earnings
               WHERE node_id = ? ORDER BY date DESC""",
            (node_id,),
        ) as cur:
            daily_rows = await cur.fetchall()
        daily = [DailyEarnings(date=r["date"], revenue_vibe=r["revenue_vibe"], requests=r["requests"]) for r in daily_rows]
        return NodeEarnings(
            node_id=row["node_id"],
            wallet_address=row["wallet_address"],
            total_revenue_vibe=row["total_revenue_vibe"],
            total_requests=row["total_requests"],
            last_active=row["last_active"],
            daily_earnings=daily,
        )

    async def add_inference(
        self,
        node_id: str,
        wallet_address: str,
        cost_vibe: float,
        node_reward_vibe: float,
        timestamp: Optional[float] = None,
    ) -> None:
        if timestamp is None:
            timestamp = time.time()
        conn = await db.get_db()
        date_str = self._date_str(timestamp)

        # Upsert node_earnings totals
        await conn.execute(
            """INSERT INTO node_earnings (node_id, wallet_address, total_revenue_vibe, total_requests, last_active)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(node_id) DO UPDATE SET
                   wallet_address=COALESCE(NULLIF(excluded.wallet_address,''), node_earnings.wallet_address),
                   total_revenue_vibe=node_earnings.total_revenue_vibe + excluded.total_revenue_vibe,
                   total_requests=node_earnings.total_requests + excluded.total_requests,
                   last_active=excluded.last_active""",
            (node_id, wallet_address, node_reward_vibe, 1, timestamp),
        )

        # Upsert daily earnings
        await conn.execute(
            """INSERT INTO node_daily_earnings (node_id, date, revenue_vibe, requests)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(node_id, date) DO UPDATE SET
                   revenue_vibe=node_daily_earnings.revenue_vibe + excluded.revenue_vibe,
                   requests=node_daily_earnings.requests + 1""",
            (node_id, date_str, node_reward_vibe),
        )
        await conn.commit()

    async def get_earnings(self, node_id: str) -> Optional[NodeEarnings]:
        return await self._load_earnings(node_id)

    async def get_all_earnings(self) -> List[NodeEarnings]:
        conn = await db.get_db()
        async with conn.execute("SELECT node_id FROM node_earnings") as cur:
            rows = await cur.fetchall()
        result = []
        for r in rows:
            e = await self._load_earnings(r["node_id"])
            if e:
                result.append(e)
        return result

    async def get_all_rankings(self) -> List[Dict[str, Any]]:
        conn = await db.get_db()
        async with conn.execute(
            """SELECT node_id, wallet_address, total_revenue_vibe, total_requests
               FROM node_earnings ORDER BY total_revenue_vibe DESC"""
        ) as cur:
            rows = await cur.fetchall()
        result = []
        for i, r in enumerate(rows):
            result.append({
                "node_id": r["node_id"],
                "wallet_address": r["wallet_address"],
                "total_earnings": r["total_revenue_vibe"],
                "total_requests": r["total_requests"],
                "rank": i + 1,
            })
        return result

    async def get_revenue_stats(self) -> Dict[str, float]:
        conn = await db.get_db()
        today_str = self._date_str(time.time())
        month_str = today_str[:7]

        async with conn.execute(
            """SELECT
                   COALESCE(SUM(total_revenue_vibe), 0.0) as total,
                   COALESCE((SELECT SUM(revenue_vibe) FROM node_daily_earnings WHERE date=?), 0.0) as today,
                   COALESCE((SELECT SUM(revenue_vibe) FROM node_daily_earnings WHERE date LIKE ?), 0.0) as month
               FROM node_earnings""",
            (today_str, month_str + "%"),
        ) as cur:
            row = await cur.fetchone()
        return {
            "total_revenue_vibe": row["total"] if row else 0.0,
            "today_revenue_vibe": row["today"] if row else 0.0,
            "month_revenue_vibe": row["month"] if row else 0.0,
        }

    async def get_revenue_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        import datetime
        conn = await db.get_db()
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=days)
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        async with conn.execute(
            """SELECT date, SUM(revenue_vibe) as revenue, SUM(requests) as reqs
               FROM node_daily_earnings
               WHERE date >= ? AND date <= ?
               GROUP BY date""",
            (start_str, end_str),
        ) as cur:
            rows = await cur.fetchall()

        data = {r["date"]: {"revenue_vibe": r["revenue"], "requests": r["reqs"]} for r in rows}
        result = []
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            result.append({
                "date": date_str,
                "revenue_vibe": data.get(date_str, {}).get("revenue_vibe", 0.0),
                "requests": data.get(date_str, {}).get("requests", 0),
            })
            current += datetime.timedelta(days=1)
        return result

    async def update_wallet(self, node_id: str, wallet_address: str) -> None:
        conn = await db.get_db()
        await conn.execute(
            "UPDATE node_earnings SET wallet_address = ? WHERE node_id = ?",
            (wallet_address, node_id),
        )
        # If node doesn't exist yet, create it
        await conn.execute(
            """INSERT OR IGNORE INTO node_earnings
               (node_id, wallet_address, total_revenue_vibe, total_requests, last_active)
               VALUES (?, ?, 0.0, 0, ?)""",
            (node_id, wallet_address, time.time()),
        )
        await conn.commit()


class WithdrawalLedger:
    """Tracks withdrawal requests — persisted to SQLite."""

    async def create(
        self,
        wallet_address: str,
        amount_vibe: float,
    ) -> WithdrawalRequest:
        withdrawal = WithdrawalRequest(
            id=f"wd_{uuid.uuid4().hex[:12]}",
            wallet_address=wallet_address,
            amount_vibe=amount_vibe,
        )
        conn = await db.get_db()
        await conn.execute(
            """INSERT INTO withdrawals
               (id, wallet_address, amount_vibe, status, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (withdrawal.id, wallet_address, amount_vibe, withdrawal.status.value, withdrawal.created_at),
        )
        await conn.commit()
        return withdrawal

    async def get_withdrawals(
        self,
        wallet_address: Optional[str] = None,
        status: Optional[WithdrawalStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WithdrawalRequest]:
        conn = await db.get_db()
        query = "SELECT * FROM withdrawals WHERE 1=1"
        params: List[Any] = []
        if wallet_address:
            query += " AND wallet_address = ?"
            params.append(wallet_address)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        async with conn.execute(query, params) as cur:
            rows = await cur.fetchall()
        return [
            WithdrawalRequest(
                id=r["id"],
                wallet_address=r["wallet_address"],
                amount_vibe=r["amount_vibe"],
                status=WithdrawalStatus(r["status"]),
                created_at=r["created_at"],
                completed_at=r["completed_at"],
                tx_hash=r["tx_hash"],
            )
            for r in rows
        ]

    async def complete(self, withdrawal_id: str, tx_hash: str) -> bool:
        conn = await db.get_db()
        await conn.execute(
            """UPDATE withdrawals SET status = ?, completed_at = ?, tx_hash = ?
               WHERE id = ? AND status = ?""",
            (WithdrawalStatus.COMPLETED.value, time.time(), tx_hash,
             withdrawal_id, WithdrawalStatus.PENDING.value),
        )
        await conn.commit()
        return conn.total_changes > 0


class UserLedger:
    """Tracks user consumption — persisted to SQLite."""

    async def ensure_user(self, wallet_address: str) -> UserRecord:
        conn = await db.get_db()
        now = time.time()
        await conn.execute(
            """INSERT OR IGNORE INTO users
               (wallet_address, total_consumption_vibe, total_requests, created_at, last_active)
               VALUES (?, 0.0, 0, ?, ?)""",
            (wallet_address, now, now),
        )
        await conn.commit()
        return await self.get_user(wallet_address)

    async def record_consumption(
        self,
        wallet_address: str,
        cost_vibe: float,
    ) -> None:
        conn = await db.get_db()
        now = time.time()
        await conn.execute(
            """INSERT INTO users
               (wallet_address, total_consumption_vibe, total_requests, created_at, last_active)
               VALUES (?, ?, 1, ?, ?)
               ON CONFLICT(wallet_address) DO UPDATE SET
                   total_consumption_vibe=users.total_consumption_vibe + excluded.total_consumption_vibe,
                   total_requests=users.total_requests + 1,
                   last_active=excluded.last_active""",
            (wallet_address, cost_vibe, now, now),
        )
        await conn.commit()

    async def get_user(self, wallet_address: str) -> Optional[UserRecord]:
        conn = await db.get_db()
        async with conn.execute(
            """SELECT wallet_address, total_consumption_vibe, total_requests, created_at, last_active
               FROM users WHERE wallet_address = ?""",
            (wallet_address,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        return UserRecord(
            wallet_address=row["wallet_address"],
            total_consumption_vibe=row["total_consumption_vibe"],
            total_requests=row["total_requests"],
            created_at=row["created_at"],
            last_active=row["last_active"],
        )

    async def get_users(
        self,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[UserRecord]:
        conn = await db.get_db()
        if search:
            async with conn.execute(
                """SELECT wallet_address, total_consumption_vibe, total_requests, created_at, last_active
                   FROM users WHERE wallet_address LIKE ? ORDER BY last_active DESC LIMIT ? OFFSET ?""",
                (f"%{search}%", limit, offset),
            ) as cur:
                rows = await cur.fetchall()
        else:
            async with conn.execute(
                """SELECT wallet_address, total_consumption_vibe, total_requests, created_at, last_active
                   FROM users ORDER BY last_active DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ) as cur:
                rows = await cur.fetchall()
        return [
            UserRecord(
                wallet_address=r["wallet_address"],
                total_consumption_vibe=r["total_consumption_vibe"],
                total_requests=r["total_requests"],
                created_at=r["created_at"],
                last_active=r["last_active"],
            )
            for r in rows
        ]

    async def count(self, search: Optional[str] = None) -> int:
        conn = await db.get_db()
        if search:
            async with conn.execute(
                "SELECT COUNT(*) FROM users WHERE wallet_address LIKE ?",
                (f"%{search}%",),
            ) as cur:
                row = await cur.fetchone()
        else:
            async with conn.execute("SELECT COUNT(*) FROM users") as cur:
                row = await cur.fetchone()
        return row[0] if row else 0


class PlatformSettingsStore:
    """Platform-wide settings store — persisted to SQLite."""

    async def get(self) -> PlatformSettings:
        conn = await db.get_db()
        async with conn.execute("SELECT key, value FROM platform_settings") as cur:
            rows = await cur.fetchall()
        if not rows:
            return PlatformSettings()
        settings = PlatformSettings()
        for r in rows:
            if hasattr(settings, r["key"]):
                val = r["value"]
                t = type(getattr(settings, r["key"]))
                if t == float:
                    val = float(val)
                elif t == int:
                    val = int(val)
                setattr(settings, r["key"], val)
        return settings

    async def update(self, **kwargs) -> PlatformSettings:
        conn = await db.get_db()
        for key, value in kwargs:
            val = str(value) if value is not None else ""
            await conn.execute(
                """INSERT INTO platform_settings (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                (key, val),
            )
        await conn.commit()
        return await self.get()


# Global singleton instances (same API as before)
inference_ledger = InferenceLedger()
node_earnings_ledger = NodeEarningsLedger()
withdrawal_ledger = WithdrawalLedger()
user_ledger = UserLedger()
settings_store = PlatformSettingsStore()
