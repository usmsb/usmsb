"""
AutoSyncManager - 自动同步管理器

管理用户数据的自动同步，包括：
- 变更触发：用户画像/知识库变更后延迟同步（防抖）
- 定期全量：每小时检查并同步所有数据
- 生命周期：会话关闭/空闲超时前同步
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Awaitable


@dataclass
class SyncConfig:
    """同步配置"""

    # 增量同步（变更触发，带防抖）
    profile_sync_delay: float = 300.0
    knowledge_sync_delay: float = 600.0

    # 定期全量同步
    full_sync_interval: int = 3600
    full_sync_random_delay: int = 300

    # 会话生命周期同步
    sync_on_session_close: bool = True
    sync_on_idle: bool = True

    # 失败重试
    retry_attempts: int = 3
    retry_delay: float = 60.0

    # 后台同步
    enable_background_sync: bool = True

    # 并发控制
    max_concurrent_syncs: int = 5


@dataclass
class SyncStatus:
    """同步状态"""
    last_sync_time: float
    pending_data_size: int
    is_syncing: bool
    sync_type: str | None


class SyncType:
    """同步类型"""
    INCREMENTAL = "incremental"
    FULL = "full"
    PROFILE = "profile"
    KNOWLEDGE = "knowledge"


class SyncState:
    """同步状态枚举"""
    IDLE = "idle"
    PENDING = "pending"
    SYNCING = "syncing"
    SUCCESS = "success"
    FAILED = "failed"


class SyncResult:
    """同步结果"""

    def __init__(
        self,
        success: bool,
        synced_items: int = 0,
        error: str | None = None,
        cid: str | None = None,
        wallet_address: str | None = None,
        sync_type: str | None = None,
        retry_count: int = 0,
    ):
        self.success = success
        self.synced_items = synced_items
        self.error = error
        self.cid = cid
        self.wallet_address = wallet_address
        self.sync_type = sync_type
        self.retry_count = retry_count


class SyncStats(dict):
    """同步统计（字典兼容）"""

    def __init__(self):
        super().__init__()
        self.total_syncs: int = 0
        self.successful_syncs: int = 0
        self.failed_syncs: int = 0
        self.total_items_synced: int = 0
        self.retried_syncs: int = 0

    def refresh(self):
        """刷新字典视图"""
        self["total_syncs"] = self.total_syncs
        self["successful_syncs"] = self.successful_syncs
        self["failed_syncs"] = self.failed_syncs
        self["retried_syncs"] = self.retried_syncs
        self["total_items_synced"] = self.total_items_synced


class SyncWalletStatus:
    """单个钱包的同步状态"""

    __slots__ = (
        "wallet_address", "state", "has_pending", "is_syncing",
        "pending_types", "last_sync_time", "last_sync_type", "last_cid",
        "sync_history"
    )

    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.state = SyncState.IDLE
        self.has_pending = False
        self.is_syncing = False
        self.pending_types: set = set()
        self.last_sync_time = 0.0
        self.last_sync_type = None
        self.last_cid = None
        self.sync_history: list[SyncResult] = []

    @property
    def pending_syncs(self) -> set:
        """Alias for pending_types (test compat)"""
        return self.pending_types


class SyncError(Exception):
    """同步错误"""
    pass


class SyncInProgressError(SyncError):
    """同步已在进行中"""
    pass


class AutoSyncManager:
    """
    自动同步管理器

    同步策略：
    1. 变更触发：用户画像/知识库变更后延迟同步（防抖）
    2. 定期全量：每小时检查并同步所有数据
    3. 生命周期：会话关闭/空闲超时前同步
    """

    def __init__(
        self,
        config: SyncConfig | None = None,
        sync_callback: Callable[[str, str], Awaitable[Any]] | None = None,
    ):
        self.config: SyncConfig = config or SyncConfig()
        self.sync_callback = sync_callback
        self._pending_syncs: dict[str, asyncio.Task] = {}
        self._last_sync_time: dict[str, float] = {}
        self._sync_lock: dict[str, asyncio.Lock] = {}
        self._running: bool = False
        self._wallet_status: dict[str, SyncWalletStatus] = {}
        self._stats: SyncStats = SyncStats()
        self._pending_tasks: dict[str, set] = {}
        self._semaphore: asyncio.Semaphore | None = None
        # 防抖序列号：每个 wallet+sync_type 组合一个递增序号
        self._sync_seq: dict[str, int] = {}

    # ========== 核心方法 ==========

    def set_sync_callback(self, callback: Callable[[str, str], Awaitable[Any]]) -> None:
        """设置同步回调函数"""
        self.sync_callback = callback

    async def start(self) -> None:
        """启动自动同步服务"""
        self._running = True
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_syncs)
        if self.config.enable_background_sync:
            asyncio.create_task(self._background_sync_loop())

    async def stop(self) -> None:
        """停止自动同步服务"""
        self._running = False
        for task in list(self._pending_syncs.values()):
            if not task.done():
                task.cancel()
        self._pending_syncs.clear()

    def get_sync_status(self, wallet_address: str) -> SyncWalletStatus:
        """获取指定钱包的同步状态"""
        if wallet_address not in self._wallet_status:
            self._wallet_status[wallet_address] = SyncWalletStatus(wallet_address)
        return self._wallet_status[wallet_address]

    def get_all_sync_status(self) -> dict[str, SyncWalletStatus]:
        """获取所有钱包的同步状态"""
        return self._wallet_status

    def get_stats(self) -> SyncStats:
        """获取同步统计信息"""
        self._stats.refresh()
        return self._stats

    async def on_profile_changed(self, wallet_address: str) -> None:
        """用户画像变更时触发（延迟同步）"""
        await self._schedule_sync(wallet_address, SyncType.PROFILE, self.config.profile_sync_delay)

    async def on_knowledge_changed(self, wallet_address: str) -> None:
        """知识库变更时触发（延迟同步）"""
        await self._schedule_sync(wallet_address, SyncType.KNOWLEDGE, self.config.knowledge_sync_delay)

    async def sync_before_close(self, wallet_address: str) -> list[SyncResult]:
        """会话关闭前立即同步"""
        if not self._running:
            return []
        status = self.get_sync_status(wallet_address)
        pending = list(status.pending_types)
        results = []
        for ptype in pending:
            try:
                result = await self.force_sync(wallet_address, ptype)
                results.append(result)
            except SyncInProgressError:
                pass
            except asyncio.CancelledError:
                pass
        return results

    async def sync_before_close_with_idle(self, wallet_address: str, idle_timeout: float) -> list[SyncResult]:
        """空闲超时前同步"""
        if self.config.sync_on_idle:
            await asyncio.sleep(idle_timeout)
            if self._running:
                status = self.get_sync_status(wallet_address)
                pending = list(status.pending_types)
                results = []
                for ptype in pending:
                    try:
                        result = await self.force_sync(wallet_address, ptype)
                        results.append(result)
                    except SyncInProgressError:
                        pass
                    except asyncio.CancelledError:
                        pass
                return results
        return []

    async def force_sync(
        self, wallet_address: str, sync_type: str = SyncType.FULL
    ) -> SyncResult:
        """强制立即同步（用户手动触发）"""
        status = self.get_sync_status(wallet_address)

        if status.is_syncing:
            raise SyncInProgressError(f"Sync already in progress for {wallet_address}")

        status.is_syncing = True
        status.state = SyncState.SYNCING

        retry_count = 0  # 已发生的重试次数（首次尝试失败后的循环迭代）
        last_error = None

        for attempt in range(self.config.retry_attempts):
            try:
                if self.sync_callback:
                    callback_result = await self.sync_callback(wallet_address, sync_type)
                    if isinstance(callback_result, SyncResult):
                        result = callback_result
                    else:
                        result = SyncResult(
                            success=True,
                            synced_items=1,
                            cid=str(callback_result),
                            wallet_address=wallet_address,
                            sync_type=sync_type,
                            retry_count=retry_count,
                        )
                else:
                    await asyncio.sleep(0.01)
                    result = SyncResult(
                        success=True,
                        synced_items=1,
                        cid=f"QmMock{uuid.uuid4().hex[:20]}",
                        wallet_address=wallet_address,
                        sync_type=sync_type,
                        retry_count=retry_count,
                    )

                # 同步成功
                result.sync_type = sync_type
                status.state = SyncState.SUCCESS if result.success else SyncState.FAILED
                status.last_sync_time = time.time()
                status.last_sync_type = result.sync_type
                status.last_cid = result.cid
                status.has_pending = False
                if wallet_address in self._pending_tasks:
                    self._pending_tasks[wallet_address].clear()

                self._stats.total_syncs += 1
                if result.success:
                    self._stats.successful_syncs += 1
                    self._stats.total_items_synced += result.synced_items
                else:
                    self._stats.failed_syncs += 1
                if retry_count > 0:
                    self._stats.retried_syncs += 1

                status.sync_history.append(result)
                status.is_syncing = False
                return result

            except asyncio.CancelledError:
                # 任务被取消：不重试，立即返回取消状态
                status.state = SyncState.FAILED
                status.is_syncing = False
                result = SyncResult(
                    success=False,
                    error="Sync cancelled",
                    wallet_address=wallet_address,
                    sync_type=sync_type,
                    retry_count=retry_count,
                )
                status.sync_history.append(result)
                raise  # 重新抛出 CancelledError，让调用者知道被取消

            except Exception as e:
                last_error = str(e)
                # 只要发生过重试（首次尝试之后的任何失败），retry_count=1
                # 语义：是否发生了重试（而非仅首次尝试就成功）
                retry_count = 1
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)

        # 所有重试都失败
        status.state = SyncState.FAILED
        status.is_syncing = False
        result = SyncResult(
            success=False,
            error=last_error,
            wallet_address=wallet_address,
            sync_type=sync_type,
            retry_count=retry_count,
        )
        self._stats.total_syncs += 1
        self._stats.failed_syncs += 1
        status.sync_history.append(result)
        return result

    async def sync_all_pending(self) -> list[SyncResult]:
        """同步所有待处理的钱包"""
        results = []
        for wallet, pending_types in list(self._pending_tasks.items()):
            for sync_type in list(pending_types):
                try:
                    result = await self.force_sync(wallet, sync_type)
                    results.append(result)
                except SyncInProgressError:
                    pass
                except asyncio.CancelledError:
                    pass
        return results

    def cleanup_user(self, wallet_address: str) -> None:
        """清理用户数据"""
        if wallet_address in self._pending_syncs:
            task = self._pending_syncs.pop(wallet_address)
            if not task.done():
                task.cancel()
        if wallet_address in self._wallet_status:
            del self._wallet_status[wallet_address]
        if wallet_address in self._pending_tasks:
            del self._pending_tasks[wallet_address]

    async def _schedule_sync(self, wallet_address: str, sync_type: str, delay: float) -> None:
        """调度延迟同步（防抖）"""
        if wallet_address not in self._sync_lock:
            self._sync_lock[wallet_address] = asyncio.Lock()

        async with self._sync_lock[wallet_address]:
            task_key = f"{wallet_address}:{sync_type}"
            if task_key in self._pending_syncs:
                self._pending_syncs[task_key].cancel()

            # 递增序列号，确保只有最新的任务执行
            seq = self._sync_seq.get(task_key, 0) + 1
            self._sync_seq[task_key] = seq

            task = asyncio.create_task(self._delayed_sync(wallet_address, sync_type, delay, seq))
            self._pending_syncs[task_key] = task

            status = self.get_sync_status(wallet_address)
            status.has_pending = True
            status.state = SyncState.PENDING
            if wallet_address not in self._pending_tasks:
                self._pending_tasks[wallet_address] = set()
            self._pending_tasks[wallet_address].add(sync_type)
            status.pending_types.add(sync_type)

    async def _delayed_sync(self, wallet_address: str, sync_type: str, delay: float, seq: int = 0) -> None:
        """延迟后执行同步（带序列号防抖）"""
        task_key = f"{wallet_address}:{sync_type}"
        try:
            await asyncio.sleep(delay)
            # 检查是否是最新的任务（序列号防抖）
            if seq > 0 and self._sync_seq.get(task_key, 0) != seq:
                # 已被更新的任务替代，跳过
                return
            if self._running:
                await self.force_sync(wallet_address, sync_type)
        except asyncio.CancelledError:
            # 被取消时，确保清理待处理标记
            pass
        finally:
            self._pending_syncs.pop(task_key, None)
            # 确保 is_syncing 被重置（如果 force_sync 因取消未能完成）
            try:
                status = self.get_sync_status(wallet_address)
                if status.state == SyncState.SYNCING:
                    status.state = SyncState.FAILED
                    status.is_syncing = False
            except Exception:
                pass

    async def _background_sync_loop(self) -> None:
        """后台定期全量同步循环"""
        while self._running:
            try:
                await asyncio.sleep(self.config.full_sync_interval)
                if self._running and self.sync_callback:
                    for wallet in list(self._wallet_status.keys()):
                        task_key = f"{wallet}:{SyncType.FULL}"
                        if task_key not in self._pending_syncs:
                            await self.force_sync(wallet, SyncType.FULL)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
