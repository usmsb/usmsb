"""
自动同步模块

管理用户数据的自动同步，包括变更触发、定期全量和生命周期同步。
"""

from .auto_sync_manager import AutoSyncManager

__all__ = ["AutoSyncManager"]
