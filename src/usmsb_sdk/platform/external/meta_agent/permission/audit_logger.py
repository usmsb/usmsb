"""
Audit Logger - 操作审计日志

功能：
1. 记录所有敏感操作
2. 支持日志查询
3. 异常行为检测
"""

import asyncio
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditLevel(str, Enum):
    """审计级别"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    """审计操作类型"""

    # NPM/NPX 操作
    NPM_INSTALL = "npm:install"
    NPM_UNINSTALL = "npm:uninstall"
    NPM_RUN = "npm:run"
    NPM_GLOBAL = "npm:global"

    # Git 操作
    GIT_CLONE = "git:clone"
    GIT_PUSH = "git:push"
    GIT_PULL = "git:pull"
    GIT_COMMIT = "git:commit"
    GIT_RESET = "git:reset"

    # 文件操作
    FILE_READ = "file:read"
    FILE_WRITE = "file:write"
    FILE_DELETE = "file:delete"

    # 工具执行
    TOOL_EXECUTE = "tool:execute"
    SKILL_EXECUTE = "skill:execute"

    # 认证
    AUTH_LOGIN = "auth:login"
    AUTH_LOGOUT = "auth:logout"


@dataclass
class AuditLog:
    """审计日志条目"""

    id: str = field(default_factory=lambda: str(time.time()))
    timestamp: float = field(default_factory=time.time)
    level: AuditLevel = AuditLevel.INFO
    action: AuditAction = AuditAction.TOOL_EXECUTE
    user_id: str = ""
    wallet_address: str = ""
    role: str = ""
    resource: str = ""
    operation: str = ""
    result: str = "success"
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat(),
            "level": self.level.value,
            "action": self.action.value,
            "user_id": self.user_id,
            "wallet_address": self.wallet_address,
            "role": self.role,
            "resource": self.resource,
            "operation": self.operation,
            "result": self.result,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


class AuditLogger:
    """
    审计日志管理器

    记录所有敏感操作，支持查询和统计。
    """

    def __init__(self, db_path: str = "meta_agent_audit.db"):
        self.db_path = db_path
        self._initialized = False

    async def init(self):
        """初始化数据库"""
        if self._initialized:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info("Audit Logger initialized")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                level TEXT NOT NULL,
                action TEXT NOT NULL,
                user_id TEXT,
                wallet_address TEXT,
                role TEXT,
                resource TEXT,
                operation TEXT,
                result TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT
            )
        """)

        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet ON audit_logs(wallet_address)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_action ON audit_logs(action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON audit_logs(level)")

        conn.commit()
        conn.close()

    async def log(
        self,
        action: AuditAction,
        wallet_address: str = "",
        role: str = "",
        resource: str = "",
        operation: str = "",
        result: str = "success",
        level: AuditLevel = AuditLevel.INFO,
        details: Optional[Dict[str, Any]] = None,
        user_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ):
        """记录审计日志"""
        audit_log = AuditLog(
            level=level,
            action=action,
            user_id=user_id,
            wallet_address=wallet_address,
            role=role,
            resource=resource,
            operation=operation,
            result=result,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self._save_log(audit_log)

        # 根据级别输出日志
        if level == AuditLevel.CRITICAL:
            logger.critical(f"AUDIT: {action.value} by {wallet_address}: {result}")
        elif level == AuditLevel.ERROR:
            logger.error(f"AUDIT: {action.value} by {wallet_address}: {result}")
        elif level == AuditLevel.WARNING:
            logger.warning(f"AUDIT: {action.value} by {wallet_address}: {result}")

    async def _save_log(self, audit_log: AuditLog):
        """保存日志到数据库"""
        import asyncio

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._insert_log, audit_log)

    def _insert_log(self, audit_log: AuditLog):
        """插入日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audit_logs 
            (id, timestamp, level, action, user_id, wallet_address, role, 
             resource, operation, result, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_log.id,
                audit_log.timestamp,
                audit_log.level.value,
                audit_log.action.value,
                audit_log.user_id,
                audit_log.wallet_address,
                audit_log.role,
                audit_log.resource,
                audit_log.operation,
                audit_log.result,
                json.dumps(audit_log.details),
                audit_log.ip_address,
                audit_log.user_agent,
            ),
        )

        conn.commit()
        conn.close()

    async def query(
        self,
        wallet_address: Optional[str] = None,
        action: Optional[AuditAction] = None,
        level: Optional[AuditLevel] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询审计日志"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._query_logs, wallet_address, action, level, start_time, end_time, limit
        )

    def _query_logs(
        self,
        wallet_address: Optional[str],
        action: Optional[AuditAction],
        level: Optional[AuditLevel],
        start_time: Optional[float],
        end_time: Optional[float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """查询日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if wallet_address:
            query += " AND wallet_address = ?"
            params.append(wallet_address)

        if action:
            query += " AND action = ?"
            params.append(action.value)

        if level:
            query += " AND level = ?"
            params.append(level.value)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "datetime": datetime.fromtimestamp(row[1]).isoformat(),
                    "level": row[2],
                    "action": row[3],
                    "user_id": row[4],
                    "wallet_address": row[5],
                    "role": row[6],
                    "resource": row[7],
                    "operation": row[8],
                    "result": row[9],
                    "details": json.loads(row[10]) if row[10] else {},
                    "ip_address": row[11],
                    "user_agent": row[12],
                }
            )

        return results

    async def get_user_stats(self, wallet_address: str) -> Dict[str, Any]:
        """获取用户操作统计"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_user_stats, wallet_address)

    def _get_user_stats(self, wallet_address: str) -> Dict[str, Any]:
        """获取用户统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总操作数
        cursor.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE wallet_address = ?", (wallet_address,)
        )
        total = cursor.fetchone()[0]

        # 按操作类型统计
        cursor.execute(
            """
            SELECT action, COUNT(*) as count 
            FROM audit_logs 
            WHERE wallet_address = ? 
            GROUP BY action
            """,
            (wallet_address,),
        )
        action_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # 按结果统计
        cursor.execute(
            """
            SELECT result, COUNT(*) as count 
            FROM audit_logs 
            WHERE wallet_address = ? 
            GROUP BY result
            """,
            (wallet_address,),
        )
        result_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # 最近的操作
        cursor.execute(
            """
            SELECT action, operation, result, timestamp 
            FROM audit_logs 
            WHERE wallet_address = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
            """,
            (wallet_address,),
        )
        recent = [
            {
                "action": row[0],
                "operation": row[1],
                "result": row[2],
                "datetime": datetime.fromtimestamp(row[3]).isoformat(),
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            "total_operations": total,
            "by_action": action_counts,
            "by_result": result_counts,
            "recent_operations": recent,
        }


# 全局审计日志实例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_path: str = "meta_agent_audit.db") -> AuditLogger:
    """获取全局审计日志实例"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(db_path)
    return _audit_logger
