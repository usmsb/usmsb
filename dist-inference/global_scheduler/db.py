"""
SQLite persistence layer for USMSB global scheduler.
All ledgers use aiosqlite for async SQLite access.
"""

import aiosqlite
import asyncio
import json
import os
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS inference_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    gpu_seconds REAL NOT NULL,
    cost_vibe REAL NOT NULL,
    node_reward_vibe REAL NOT NULL,
    timestamp REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inference_node ON inference_records(node_id);
CREATE INDEX IF NOT EXISTS idx_inference_user ON inference_records(user_id);
CREATE INDEX IF NOT EXISTS idx_inference_timestamp ON inference_records(timestamp DESC);

CREATE TABLE IF NOT EXISTS node_earnings (
    node_id TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL DEFAULT '',
    total_revenue_vibe REAL NOT NULL DEFAULT 0.0,
    total_requests INTEGER NOT NULL DEFAULT 0,
    last_active REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS node_daily_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL,
    date TEXT NOT NULL,
    revenue_vibe REAL NOT NULL DEFAULT 0.0,
    requests INTEGER NOT NULL DEFAULT 0,
    UNIQUE(node_id, date)
);

CREATE TABLE IF NOT EXISTS withdrawals (
    id TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL,
    amount_vibe REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at REAL NOT NULL,
    completed_at REAL,
    tx_hash TEXT
);

CREATE TABLE IF NOT EXISTS users (
    wallet_address TEXT PRIMARY KEY,
    total_consumption_vibe REAL NOT NULL DEFAULT 0.0,
    total_requests INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    last_active REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_balances (
    user_id TEXT PRIMARY KEY,
    vibe_balance REAL NOT NULL DEFAULT 1000.0,
    owed_vibe REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS gpu_nodes (
    node_id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    port INTEGER NOT NULL,
    gpu_count INTEGER NOT NULL,
    gpu_type TEXT NOT NULL,
    total_vram_gb INTEGER NOT NULL,
    available_vram_gb INTEGER NOT NULL,
    status TEXT NOT NULL,
    loaded_models TEXT NOT NULL DEFAULT '[]',
    last_heartbeat REAL NOT NULL,
    gpu_utilization TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS model_registry (
    model_name TEXT PRIMARY KEY,
    model_type TEXT NOT NULL,
    min_gpu_count INTEGER NOT NULL,
    min_vram_per_gpu_gb INTEGER NOT NULL,
    context_length INTEGER NOT NULL,
    is_preloaded INTEGER NOT NULL
);
"""

_db_path = os.environ.get("USMSB_DB_PATH", "usmsb.db")
_db_conn: Optional[aiosqlite.Connection] = None
_init_lock = asyncio.Lock()


async def get_db() -> aiosqlite.Connection:
    """Get the shared database connection."""
    global _db_conn
    if _db_conn is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db_conn


async def init_db() -> None:
    """Initialize the database, creating tables if needed."""
    global _db_conn
    async with _init_lock:
        if _db_conn is not None:
            return
        conn = await aiosqlite.connect(_db_path)
        conn.row_factory = aiosqlite.Row
        _db_conn = conn
        await conn.executescript(SCHEMA)
        await conn.commit()


async def close_db() -> None:
    """Close the database connection."""
    global _db_conn
    if _db_conn is not None:
        await _db_conn.close()
        _db_conn = None
