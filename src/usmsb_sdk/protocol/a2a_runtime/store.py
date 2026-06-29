"""USMSB A2A 运行时 —— 单 Agent 的 SQLite 持久任务队列。

生产级要点（命门，不可省）：
- 每 Agent 私有持久队列：Pod 重启/多副本不丢任务。
- 幂等键 UNIQUE：付费/结算绝不重复执行。
- 原子领取（BEGIN IMMEDIATE + locked_until）：多 worker 不抢同一任务。
- 经济字段：vibe_amount / escrow_id / settlement_status / quality_gate / evidence_uri
  —— 把"执行"与"结算"在同一条记录里追踪，支撑 escrow→settle/refund 闭环。
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "manual_intervention_required"}

# 结算状态机：none → escrowed → settled / refunded / disputed
SETTLEMENT_NONE = "none"
SETTLEMENT_ESCROWED = "escrowed"
SETTLEMENT_SETTLED = "settled"
SETTLEMENT_REFUNDED = "refunded"
SETTLEMENT_DISPUTED = "disputed"


@dataclass
class JobRecord:
    id: str
    caller_id: str            # 委托方 agent/user id
    correlation_id: str       # 跨系统关联 id（如上游执行 id）
    a2a_message_id: str
    principal_id: str         # 主人锚点（责任承担方）
    task_type: str
    input_text: str
    payload: dict[str, Any]
    result: dict[str, Any]
    error: str
    status: str
    priority: int
    attempts: int
    max_attempts: int
    idempotency_key: str
    locked_by: str
    locked_until: float
    # ── 经济 / 结算 ──
    vibe_amount: float = 0.0
    escrow_id: str = ""
    settlement_status: str = SETTLEMENT_NONE
    quality_gate: str = "pending"   # pending | passed | failed
    evidence_uri: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0


class SQLiteJobStore:
    """带 WAL 与原子领取的本地 SQLite 队列。"""

    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    caller_id TEXT DEFAULT '',
                    correlation_id TEXT DEFAULT '',
                    a2a_message_id TEXT DEFAULT '',
                    principal_id TEXT DEFAULT '',
                    task_type TEXT DEFAULT 'generic',
                    input_text TEXT DEFAULT '',
                    payload_json TEXT NOT NULL,
                    result_json TEXT DEFAULT '{}',
                    error TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    priority INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    locked_by TEXT DEFAULT '',
                    locked_until REAL DEFAULT 0,
                    vibe_amount REAL DEFAULT 0,
                    escrow_id TEXT DEFAULT '',
                    settlement_status TEXT DEFAULT 'none',
                    quality_gate TEXT DEFAULT 'pending',
                    evidence_uri TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_jobs_status_priority ON jobs(status, priority, created_at)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS ix_jobs_caller ON jobs(caller_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_jobs_correlation ON jobs(correlation_id)")

    def enqueue_job(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        input_text: str,
        payload: dict[str, Any],
        caller_id: str = "",
        correlation_id: str = "",
        a2a_message_id: str = "",
        principal_id: str = "",
        task_type: str = "generic",
        priority: int = 0,
        max_attempts: int = 3,
        vibe_amount: float = 0.0,
    ) -> JobRecord:
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        now = time.time()
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO jobs (
                        id, caller_id, correlation_id, a2a_message_id, principal_id,
                        task_type, input_text, payload_json, result_json, error,
                        status, priority, attempts, max_attempts, idempotency_key,
                        locked_by, locked_until, vibe_amount, escrow_id,
                        settlement_status, quality_gate, evidence_uri,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '{}', '', 'queued', ?, 0, ?, ?,
                              '', 0, ?, '', 'none', 'pending', '', ?, ?)
                    """,
                    (
                        job_id, caller_id, correlation_id, a2a_message_id, principal_id,
                        task_type, input_text, json.dumps(payload, ensure_ascii=False),
                        priority, max_attempts, idempotency_key, vibe_amount, now, now,
                    ),
                )
            except sqlite3.IntegrityError:
                existing = self.get_by_idempotency_key(idempotency_key)
                if existing:
                    return existing
                raise
        job = self.get_job(job_id)
        if not job:
            raise RuntimeError(f"Failed to enqueue job {job_id}")
        return job

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_by_idempotency_key(self, idempotency_key: str) -> JobRecord | None:
        if not idempotency_key:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
        return self._row_to_job(row) if row else None

    def claim_next(self, *, worker_id: str, lock_seconds: int) -> JobRecord | None:
        now = time.time()
        lock_until = now + lock_seconds
        conn = self._connect()
        try:
            conn.isolation_level = None
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'queued'
                   OR (status = 'running' AND locked_until < ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            if not row:
                conn.execute("COMMIT")
                return None
            attempts = int(row["attempts"] or 0) + 1
            conn.execute(
                """
                UPDATE jobs
                SET status = 'running', attempts = ?, locked_by = ?,
                    locked_until = ?, updated_at = ?
                WHERE id = ?
                """,
                (attempts, worker_id, lock_until, now, row["id"]),
            )
            updated = conn.execute("SELECT * FROM jobs WHERE id = ?", (row["id"],)).fetchone()
            conn.execute("COMMIT")
            return self._row_to_job(updated) if updated else None
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def mark_succeeded(
        self,
        job_id: str,
        result: dict[str, Any],
        *,
        quality_gate: str | None = None,
        evidence_uri: str | None = None,
    ) -> JobRecord | None:
        return self._mark_terminal(
            job_id, "succeeded", result=result, error="",
            quality_gate=quality_gate, evidence_uri=evidence_uri,
        )

    def mark_manual_intervention(
        self, job_id: str, result: dict[str, Any], error: str = ""
    ) -> JobRecord | None:
        return self._mark_terminal(
            job_id, "manual_intervention_required", result=result, error=error
        )

    def mark_failed(self, job_id: str, error: str, *, retryable: bool = True) -> JobRecord | None:
        job = self.get_job(job_id)
        if not job:
            return None
        now = time.time()
        should_retry = retryable and job.attempts < job.max_attempts
        next_status = "queued" if should_retry else "failed"
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, error = ?, locked_by = '', locked_until = 0, updated_at = ?
                WHERE id = ?
                """,
                (next_status, error, now, job_id),
            )
        return self.get_job(job_id)

    def update_settlement(
        self,
        job_id: str,
        *,
        escrow_id: str | None = None,
        settlement_status: str | None = None,
    ) -> JobRecord | None:
        """更新结算字段（由结算钩子调用）。"""
        job = self.get_job(job_id)
        if not job:
            return None
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET escrow_id = ?, settlement_status = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    escrow_id if escrow_id is not None else job.escrow_id,
                    settlement_status if settlement_status is not None else job.settlement_status,
                    now,
                    job_id,
                ),
            )
        return self.get_job(job_id)

    def _mark_terminal(
        self,
        job_id: str,
        status: str,
        *,
        result: dict[str, Any],
        error: str,
        quality_gate: str | None = None,
        evidence_uri: str | None = None,
    ) -> JobRecord | None:
        job = self.get_job(job_id)
        if not job:
            return None
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE jobs
                SET status = ?, result_json = ?, error = ?, quality_gate = ?,
                    evidence_uri = ?, locked_by = '', locked_until = 0, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(result, ensure_ascii=False),
                    error,
                    quality_gate if quality_gate is not None else job.quality_gate,
                    evidence_uri if evidence_uri is not None else job.evidence_uri,
                    now,
                    job_id,
                ),
            )
        return self.get_job(job_id)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_job(self, row: sqlite3.Row) -> JobRecord:
        keys = row.keys()
        return JobRecord(
            id=str(row["id"]),
            caller_id=str(row["caller_id"] or ""),
            correlation_id=str(row["correlation_id"] or ""),
            a2a_message_id=str(row["a2a_message_id"] or ""),
            principal_id=str(row["principal_id"] or ""),
            task_type=str(row["task_type"] or "generic"),
            input_text=str(row["input_text"] or ""),
            payload=self._loads(row["payload_json"]),
            result=self._loads(row["result_json"]),
            error=str(row["error"] or ""),
            status=str(row["status"]),
            priority=int(row["priority"] or 0),
            attempts=int(row["attempts"] or 0),
            max_attempts=int(row["max_attempts"] or 3),
            idempotency_key=str(row["idempotency_key"] or ""),
            locked_by=str(row["locked_by"] or ""),
            locked_until=float(row["locked_until"] or 0),
            vibe_amount=float(row["vibe_amount"] or 0) if "vibe_amount" in keys else 0.0,
            escrow_id=str(row["escrow_id"] or "") if "escrow_id" in keys else "",
            settlement_status=str(row["settlement_status"] or SETTLEMENT_NONE) if "settlement_status" in keys else SETTLEMENT_NONE,
            quality_gate=str(row["quality_gate"] or "pending") if "quality_gate" in keys else "pending",
            evidence_uri=str(row["evidence_uri"] or "") if "evidence_uri" in keys else "",
            created_at=float(row["created_at"] or 0),
            updated_at=float(row["updated_at"] or 0),
        )

    def _loads(self, value: Any) -> dict[str, Any]:
        if not value:
            return {}
        if isinstance(value, dict):
            return value
        try:
            parsed = json.loads(str(value))
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
