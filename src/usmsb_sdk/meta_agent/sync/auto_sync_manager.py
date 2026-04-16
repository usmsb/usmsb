"""
AutoSyncManager - 自动同步管理器

管理用户数据的自动同步，包括：
- 变更触发：用户画像/知识库变更后延迟同步（防抖）
- 定期全量：每小时检查并同步所有数据
- 生命周期：会话关闭/空闲超时前同步
"""

import asyncio
from dataclasses import dataclass


@dataclass
class SyncConfig:
    """同步配置"""

    # 增量同步（变更触发，带防抖）
    profile_sync_delay: int = 300         # 用户画像变更后5分钟同步
    knowledge_sync_delay: int = 600       # 知识库变更后10分钟同步

    # 定期全量同步
    full_sync_interval: int = 3600        # 每小时全量同步一次
    full_sync_random_delay: int = 300     # 随机延迟0-5分钟（避免峰值）

    # 会话生命周期同步
    sync_on_session_close: bool = True    # 会话关闭时同步
    sync_on_idle: bool = True             # 空闲超时前同步

    # 失败重试
    retry_attempts: int = 3               # 重试次数
    retry_delay: int = 60                 # 重试间隔（秒）


@dataclass
class SyncStatus:
    """同步状态"""
    last_sync_time: float
    pending_data_size: int
    is_syncing: bool
    sync_type: str | None


class AutoSyncManager:
    """
    自动同步管理器

    同步策略：
    1. 变更触发：用户画像/知识库变更后延迟同步（防抖）
    2. 定期全量：每小时检查并同步所有数据
    3. 生命周期：会话关闭/空闲超时前同步
    """

    # ========== 属性 ==========

    config: SyncConfig
    _pending_syncs: dict[str, asyncio.Task]  # wallet:sync_type -> task
    _last_sync_time: dict[str, float]         # wallet -> timestamp
    _sync_lock: dict[str, asyncio.Lock]        # wallet -> lock
    _running: bool

    # ========== 核心方法 ==========

    async def start(self):
        """
        启动自动同步服务
        """
        pass

    async def stop(self):
        """
        停止自动同步服务
        """
        pass

    async def on_profile_changed(self, wallet_address: str):
        """
        用户画像变更时触发（5分钟后同步）
        """
        pass

    async def on_knowledge_changed(self, wallet_address: str):
        """
        知识库变更时触发（10分钟后同步）
        """
        pass

    async def sync_before_close(self, wallet_address: str):
        """
        会话关闭前立即同步
        """
        pass

    async def force_sync(self, wallet_address: str):
        """
        强制立即同步（用户手动触发）
        """
        pass

    async def get_sync_status(self, wallet_address: str) -> SyncStatus:
        """
        获取同步状态
        """
        pass
