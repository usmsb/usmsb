"""
AuditLogger - 审计日志记录器

提供安全审计功能，设计原则：
1. 只记录"发生了什么"，不记录"具体内容"
2. 用户ID哈希处理，保护隐私
3. 结构化日志，便于分析
4. 不可篡改（追加写入）
"""

import asyncio
import hashlib
import json
import os
import aiofiles
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, field


@dataclass
class AuditConfig:
    """审计配置"""

    # 日志保留
    retention_days: int = 90               # 保留90天
    archive_after_days: int = 30           # 30天后归档

    # 日志级别
    log_sensitive_content: bool = False   # 不记录敏感内容
    hash_user_id: bool = True              # 用户ID哈希处理

    # 审计事件
    audit_events: List[str] = field(default_factory=lambda: [
        # 会话事件
        "session_created",
        "session_closed",
        "session_timeout",

        # 认证事件
        "wallet_connected",
        "signature_verified",
        "auth_failed",

        # 数据事件
        "data_synced_to_ipfs",
        "data_migrated",
        "export_requested",

        # 执行事件
        "code_executed",
        "browser_opened",
        "file_uploaded",

        # 安全事件
        "sandbox_violation",
        "quota_exceeded",
        "suspicious_activity",
    ])


class AuditLogger:
    """
    审计日志记录器

    设计原则：
    1. 只记录"发生了什么"，不记录"具体内容"
    2. 用户ID哈希处理，保护隐私
    3. 结构化日志，便于分析
    4. 不可篡改（追加写入）
    """

    def __init__(self, config: Optional[AuditConfig] = None, log_dir: str = "/data/system"):
        """
        初始化审计日志记录器

        Args:
            config: 审计配置
            log_dir: 日志目录路径
        """
        self.config = config or AuditConfig()
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "audit.log"
        self.archive_dir = self.log_dir / "archive"
        self._write_lock = asyncio.Lock()

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保日志目录存在"""
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    async def log(
        self,
        event: str,
        wallet_address: str,
        details: Optional[Dict] = None,
        result: str = "success"
    ):
        """
        记录审计日志

        Args:
            event: 事件类型
            wallet_address: 用户钱包地址
            details: 事件详情（不包含敏感内容）
            result: 结果 (success/failed/blocked)
        """
        # 检查是否为需要审计的事件
        if event not in self.config.audit_events:
            return

        # 用户ID哈希处理
        user_hash = self._hash_user_id(wallet_address) if self.config.hash_user_id else wallet_address

        # 构建日志条目
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event": event,
            "user_hash": user_hash,
            "result": result,
            "details": details or {},
            "node_id": os.getenv("NODE_ID", "unknown"),
        }

        # 写入日志
        await self._write_log(log_entry)

    def _hash_user_id(self, wallet_address: str) -> str:
        """
        哈希用户ID

        使用SHA256哈希用户钱包地址，保护用户隐私

        Args:
            wallet_address: 用户钱包地址

        Returns:
            哈希后的用户ID（16位）
        """
        return hashlib.sha256(
            f"usmsb:{wallet_address}".encode()
        ).hexdigest()[:16]

    async def _write_log(self, entry: Dict):
        """
        写入日志（追加模式）

        Args:
            entry: 日志条目字典
        """
        async with self._write_lock:
            try:
                async with aiofiles.open(self.log_file, mode='a', encoding='utf-8') as f:
                    await f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as e:
                # 记录到标准错误输出，避免死循环
                print(f"[AuditLogger] Failed to write log: {e}")

    async def query_logs(
        self,
        event: str = None,
        user_hash: str = None,
        start_time: float = None,
        end_time: float = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        查询审计日志

        Args:
            event: 事件类型过滤
            user_hash: 用户哈希过滤
            start_time: 开始时间戳（Unix时间戳）
            end_time: 结束时间戳（Unix时间戳）
            limit: 返回结果最大数量

        Returns:
            匹配的日志条目列表
        """
        results = []

        try:
            async with aiofiles.open(self.log_file, mode='r', encoding='utf-8') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)

                        # 过滤条件检查
                        if event and entry.get("event") != event:
                            continue

                        if user_hash and entry.get("user_hash") != user_hash:
                            continue

                        # 时间过滤
                        ts_str = entry.get("timestamp", "").replace("Z", "+00:00")
                        entry_time = datetime.fromisoformat(ts_str).timestamp()

                        if start_time and entry_time < start_time:
                            continue

                        if end_time and entry_time > end_time:
                            continue

                        results.append(entry)

                        # 达到限制
                        if len(results) >= limit:
                            break

                    except json.JSONDecodeError:
                        # 跳过无法解析的行
                        continue

        except FileNotFoundError:
            # 日志文件不存在，返回空列表
            pass

        return results

    async def archive_old_logs(self):
        """
        归档旧日志

        将超过归档天数的日志移动到归档目录
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self.config.archive_after_days)
        archived_count = 0

        temp_file = self.log_file.with_suffix('.tmp')

        try:
            # 分离旧日志和新日志
            async with aiofiles.open(self.log_file, mode='r', encoding='utf-8') as f:
                async with aiofiles.open(temp_file, mode='w', encoding='utf-8') as new_f:
                    async with aiofiles.open(
                        self.archive_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log",
                        mode='a',
                        encoding='utf-8'
                    ) as archive_f:

                        async for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                entry = json.loads(line)
                                ts_str = entry.get("timestamp", "").replace("Z", "+00:00")
                                entry_time = datetime.fromisoformat(ts_str)

                                if entry_time < cutoff_time:
                                    # 归档旧日志
                                    await archive_f.write(line + "\n")
                                    archived_count += 1
                                else:
                                    # 保留新日志
                                    await new_f.write(line + "\n")

                            except json.JSONDecodeError:
                                continue

            # 替换原文件
            temp_file.replace(self.log_file)

        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[AuditLogger] Archive failed: {e}")
            if temp_file.exists():
                temp_file.unlink()

        return archived_count

    async def cleanup_expired_logs(self):
        """
        清理过期日志

        删除超过保留天数的归档日志文件
        """
        cutoff_time = datetime.now() - timedelta(days=self.config.retention_days)
        deleted_count = 0

        try:
            for file_path in self.archive_dir.glob("audit_*.log"):
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)

                if file_time < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1

        except Exception as e:
            print(f"[AuditLogger] Cleanup failed: {e}")

        return deleted_count

    async def get_log_stats(self) -> Dict:
        """
        获取日志统计信息

        Returns:
            日志统计字典
        """
        stats = {
            "total_entries": 0,
            "events_count": {},
            "last_entry": None,
            "log_file_size": 0,
        }

        try:
            # 获取日志文件大小
            if self.log_file.exists():
                stats["log_file_size"] = self.log_file.stat().st_size

            # 统计日志条目
            async with aiofiles.open(self.log_file, mode='r', encoding='utf-8') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        entry = json.loads(line)
                        stats["total_entries"] += 1

                        # 统计事件类型
                        event = entry.get("event", "unknown")
                        stats["events_count"][event] = stats["events_count"].get(event, 0) + 1

                        # 记录最后一条
                        stats["last_entry"] = entry.get("timestamp")

                    except json.JSONDecodeError:
                        continue

        except FileNotFoundError:
            pass

        return stats

    async def query_user_activity(
        self,
        user_hash: str,
        hours: int = 24
    ) -> List[Dict]:
        """
        查询用户活动日志

        Args:
            user_hash: 用户哈希
            hours: 查询最近几小时的活动

        Returns:
            用户活动日志列表
        """
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=hours)).timestamp()
        end_time = now.timestamp()

        return await self.query_logs(
            user_hash=user_hash,
            start_time=start_time,
            end_time=end_time,
            limit=1000
        )

    async def get_security_events(self, hours: int = 24) -> List[Dict]:
        """
        获取安全事件日志

        Args:
            hours: 查询最近几小时的事件

        Returns:
            安全事件日志列表
        """
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=hours)).timestamp()
        security_events = [
            "auth_failed",
            "sandbox_violation",
            "quota_exceeded",
            "suspicious_activity",
        ]

        results = []
        for event in security_events:
            results.extend(
                await self.query_logs(event=event, start_time=start_time, limit=100)
            )

        # 按时间排序
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results
