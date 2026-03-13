"""
AutoSyncManager - 自动同步管理器

负责管理用户数据的自动同步，包括：
1. 增量同步（变更触发，带防抖）
2. 定期全量同步
3. 生命周期同步（会话关闭/空闲前）
4. 失败重试机制
"""

import asyncio
import random
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Callable, Awaitable
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class SyncType(Enum):
    """同步类型"""
    PROFILE = "profile"          # 用户画像同步
    KNOWLEDGE = "knowledge"      # 知识库同步
    FULL = "full"                # 全量同步
    CLOSE = "close"              # 会话关闭前同步


class SyncState(Enum):
    """同步状态"""
    IDLE = "idle"                # 空闲
    PENDING = "pending"          # 待执行
    IN_PROGRESS = "in_progress"  # 执行中
    FAILED = "failed"            # 失败
    SUCCESS = "success"          # 成功


class SyncError(Exception):
    """同步错误基类"""
    pass


class SyncInProgressError(SyncError):
    """同步正在进行中的错误"""
    pass


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

    # 其他
    enable_background_sync: bool = True   # 启用后台同步
    max_concurrent_syncs: int = 5         # 最大并发同步数


@dataclass
class SyncStatus:
    """同步状态"""
    wallet_address: str
    state: SyncState = SyncState.IDLE
    last_sync_time: float = 0.0
    last_sync_type: Optional[SyncType] = None
    last_cid: Optional[str] = None
    pending_syncs: Set[SyncType] = field(default_factory=set)
    in_progress_sync: Optional[SyncType] = None
    retry_count: int = 0
    last_error: Optional[str] = None

    @property
    def is_syncing(self) -> bool:
        """是否正在同步"""
        return self.state == SyncState.IN_PROGRESS

    @property
    def has_pending(self) -> bool:
        """是否有待同步任务"""
        return len(self.pending_syncs) > 0


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    wallet_address: str
    sync_type: SyncType
    cid: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None
    retry_count: int = 0


class AutoSyncManager:
    """
    自动同步管理器

    同步策略：
    1. 变更触发：用户画像/知识库变更后延迟同步（防抖）
    2. 定期全量：每小时检查并同步所有数据
    3. 生命周期：会话关闭/空闲超时前同步
    4. 失败重试：自动重试失败的同步任务
    """

    def __init__(
        self,
        config: Optional[SyncConfig] = None,
        sync_callback: Optional[Callable[[str, SyncType], Awaitable[str]]] = None
    ):
        """
        初始化自动同步管理器

        Args:
            config: 同步配置，不提供则使用默认配置
            sync_callback: 同步回调函数，接收 (wallet_address, sync_type)，返回 CID
        """
        self.config = config or SyncConfig()
        self._sync_callback = sync_callback

        # 状态管理
        self._sync_status: Dict[str, SyncStatus] = {}
        self._pending_tasks: Dict[str, Dict[SyncType, asyncio.Task]] = defaultdict(dict)
        self._sync_locks: Dict[str, asyncio.Lock] = {}

        # 服务状态
        self._running = False
        self._background_tasks: Set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()

        # 统计信息
        self._stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "retried_syncs": 0,
        }

    async def start(self):
        """启动自动同步服务"""
        if self._running:
            logger.warning("AutoSyncManager is already running")
            return

        self._running = True
        logger.info("AutoSyncManager started")

        # 启动定期全量同步任务
        if self.config.enable_background_sync:
            task = asyncio.create_task(self._periodic_full_sync())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def stop(self):
        """停止自动同步服务"""
        if not self._running:
            return

        logger.info("Stopping AutoSyncManager...")
        self._running = False
        self._shutdown_event.set()

        # 等待所有待处理的同步任务完成或取消
        for wallet, tasks in self._pending_tasks.items():
            for sync_type, task in tasks.items():
                if not task.done():
                    logger.info(f"Cancelling pending sync task for {wallet}:{sync_type.value}")
                    task.cancel()

        # 等待后台任务完成
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
            self._background_tasks.clear()

        logger.info("AutoSyncManager stopped")

    async def on_profile_changed(self, wallet_address: str):
        """
        用户画像变更时触发

        5分钟后执行增量同步，多次变更只触发一次（防抖）
        """
        if not self._running:
            logger.warning(f"AutoSyncManager not running, ignoring profile change for {wallet_address}")
            return

        logger.debug(f"Profile changed for {wallet_address}, scheduling sync in {self.config.profile_sync_delay}s")
        await self._schedule_incremental_sync(
            wallet_address,
            SyncType.PROFILE,
            self.config.profile_sync_delay
        )

    async def on_knowledge_changed(self, wallet_address: str):
        """
        知识库变更时触发

        10分钟后执行增量同步，多次变更只触发一次（防抖）
        """
        if not self._running:
            logger.warning(f"AutoSyncManager not running, ignoring knowledge change for {wallet_address}")
            return

        logger.debug(f"Knowledge changed for {wallet_address}, scheduling sync in {self.config.knowledge_sync_delay}s")
        await self._schedule_incremental_sync(
            wallet_address,
            SyncType.KNOWLEDGE,
            self.config.knowledge_sync_delay
        )

    async def _schedule_incremental_sync(
        self,
        wallet_address: str,
        sync_type: SyncType,
        delay: int
    ):
        """
        调度增量同步（防抖）

        如果已有待执行的同类同步任务，先取消它再创建新的
        """
        # 获取或创建用户状态
        status = self._get_or_create_status(wallet_address)

        # 取消现有的待执行任务（防抖）
        if sync_type in self._pending_tasks[wallet_address]:
            existing_task = self._pending_tasks[wallet_address][sync_type]
            if not existing_task.done():
                existing_task.cancel()
                logger.debug(f"Debounced: cancelled previous {sync_type.value} sync task for {wallet_address}")

        # 标记待同步
        status.pending_syncs.add(sync_type)
        status.state = SyncState.PENDING

        # 创建新的延迟任务
        async def delayed_sync():
            try:
                await asyncio.sleep(delay)
                if not self._running:
                    return

                # 再次检查是否还有待同步请求（可能又被取消又重新调度）
                if sync_type in self._pending_tasks[wallet_address]:
                    await self._do_sync(wallet_address, sync_type)

            except asyncio.CancelledError:
                logger.debug(f"Delayed sync task cancelled for {wallet_address}:{sync_type.value}")
            except Exception as e:
                logger.error(f"Error in delayed sync task for {wallet_address}:{sync_type.value}: {e}")

        task = asyncio.create_task(delayed_sync())
        self._pending_tasks[wallet_address][sync_type] = task

    async def sync_before_close(self, wallet_address: str):
        """
        会话关闭前立即同步

        确保数据不丢失，同步所有待同步的数据类型
        """
        if not self.config.sync_on_session_close:
            logger.debug(f"Sync on session close disabled for {wallet_address}")
            return

        logger.info(f"Syncing before session close for {wallet_address}")
        status = self._get_or_create_status(wallet_address)

        # 收集所有待同步类型
        sync_types = list(status.pending_syncs)

        # 如果没有待同步但配置了空闲同步，也执行一次全量同步
        if not sync_types and self.config.sync_on_idle:
            sync_types = [SyncType.FULL]

        # 依次执行同步
        results = []
        for sync_type in sync_types:
            result = await self._do_sync(wallet_address, sync_type, immediate=True)
            results.append(result)

        # 记录结果
        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Session close sync for {wallet_address}: {successful}/{len(results)} successful"
        )

        return results

    async def force_sync(self, wallet_address: str, sync_type: Optional[SyncType] = None):
        """
        强制立即同步（用户手动触发）

        Args:
            wallet_address: 钱包地址
            sync_type: 同步类型，不指定则执行全量同步

        Returns:
            同步结果
        """
        logger.info(f"Force sync requested for {wallet_address}, type: {sync_type}")

        if sync_type is None:
            sync_type = SyncType.FULL

        return await self._do_sync(wallet_address, sync_type, immediate=True)

    async def _do_sync(
        self,
        wallet_address: str,
        sync_type: SyncType,
        immediate: bool = False
    ) -> SyncResult:
        """
        执行同步

        Args:
            wallet_address: 钱包地址
            sync_type: 同步类型
            immediate: 是否立即执行（不检查防抖延迟）

        Returns:
            同步结果
        """
        status = self._get_or_create_status(wallet_address)

        # 从待处理列表中移除
        status.pending_syncs.discard(sync_type)

        # 获取锁
        lock = self._get_lock(wallet_address)

        async with lock:
            if status.is_syncing and not immediate:
                raise SyncInProgressError(f"Sync already in progress for {wallet_address}")

            status.state = SyncState.IN_PROGRESS
            status.in_progress_sync = sync_type
            status.retry_count = 0

            logger.info(
                f"Starting {sync_type.value} sync for {wallet_address} "
                f"(attempt {status.retry_count + 1}/{self.config.retry_attempts})"
            )

            result = await self._execute_sync_with_retry(wallet_address, sync_type)

            # 更新状态
            if result.success:
                status.state = SyncState.SUCCESS
                status.last_sync_time = result.timestamp
                status.last_sync_type = result.sync_type
                status.last_cid = result.cid
                status.last_error = None
            else:
                status.state = SyncState.FAILED
                status.last_error = result.error

            status.in_progress_sync = None
            status.retry_count = 0

            return result

    async def _execute_sync_with_retry(
        self,
        wallet_address: str,
        sync_type: SyncType
    ) -> SyncResult:
        """
        执行带重试的同步

        Args:
            wallet_address: 钱包地址
            sync_type: 同步类型

        Returns:
            同步结果
        """
        status = self._get_or_create_status(wallet_address)

        for attempt in range(self.config.retry_attempts):
            status.retry_count = attempt + 1

            try:
                # 执行同步
                if self._sync_callback is None:
                    # 如果没有回调函数，模拟同步成功
                    cid = f"QmMock{random.randint(100000, 999999)}"
                    logger.info(f"Mock sync successful for {wallet_address}:{sync_type.value}, CID: {cid}")
                else:
                    cid = await self._sync_callback(wallet_address, sync_type)

                self._stats["total_syncs"] += 1
                self._stats["successful_syncs"] += 1

                return SyncResult(
                    success=True,
                    wallet_address=wallet_address,
                    sync_type=sync_type,
                    cid=cid,
                    retry_count=attempt,
                )

            except Exception as e:
                logger.error(
                    f"Sync attempt {attempt + 1}/{self.config.retry_attempts} failed "
                    f"for {wallet_address}:{sync_type.value}: {e}"
                )

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                    self._stats["retried_syncs"] += 1
                else:
                    self._stats["total_syncs"] += 1
                    self._stats["failed_syncs"] += 1

                    return SyncResult(
                        success=False,
                        wallet_address=wallet_address,
                        sync_type=sync_type,
                        error=str(e),
                        retry_count=attempt,
                    )

    async def _periodic_full_sync(self):
        """定期全量同步任务"""
        logger.info("Periodic full sync task started")

        while not self._shutdown_event.is_set():
            try:
                # 计算随机延迟避免峰值
                random_delay = random.randint(0, self.config.full_sync_random_delay)
                logger.debug(f"Next full sync in {self.config.full_sync_interval + random_delay}s")

                # 等待（带可中断性）
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.config.full_sync_interval + random_delay
                    )
                    # 如果被唤醒，退出
                    break
                except asyncio.TimeoutError:
                    pass

                if self._shutdown_event.is_set():
                    break

                # 获取所有有状态的用户
                active_wallets = list(self._sync_status.keys())

                logger.info(f"Running periodic full sync for {len(active_wallets)} users")

                # 并发同步（限制并发数）
                semaphore = asyncio.Semaphore(self.config.max_concurrent_syncs)

                async def sync_with_limit(wallet: str):
                    async with semaphore:
                        try:
                            return await self._do_sync(wallet, SyncType.FULL)
                        except Exception as e:
                            logger.error(f"Periodic sync error for {wallet}: {e}")
                            return None

                results = await asyncio.gather(
                    *[sync_with_limit(wallet) for wallet in active_wallets],
                    return_exceptions=True
                )

                successful = sum(1 for r in results if r and getattr(r, 'success', False))
                logger.info(f"Periodic full sync completed: {successful}/{len(active_wallets)} successful")

            except Exception as e:
                logger.error(f"Error in periodic full sync task: {e}")

        logger.info("Periodic full sync task stopped")

    def get_sync_status(self, wallet_address: str) -> SyncStatus:
        """
        获取同步状态

        Args:
            wallet_address: 钱包地址

        Returns:
            同步状态
        """
        return self._get_or_create_status(wallet_address)

    def get_all_sync_status(self) -> Dict[str, SyncStatus]:
        """
        获取所有用户的同步状态

        Returns:
            钱包地址到同步状态的映射
        """
        return self._sync_status.copy()

    def get_stats(self) -> Dict:
        """
        获取同步统计信息

        Returns:
            统计信息字典
        """
        return self._stats.copy()

    def _get_or_create_status(self, wallet_address: str) -> SyncStatus:
        """获取或创建用户的同步状态"""
        if wallet_address not in self._sync_status:
            self._sync_status[wallet_address] = SyncStatus(wallet_address=wallet_address)
        return self._sync_status[wallet_address]

    def _get_lock(self, wallet_address: str) -> asyncio.Lock:
        """获取用户的同步锁"""
        if wallet_address not in self._sync_locks:
            self._sync_locks[wallet_address] = asyncio.Lock()
        return self._sync_locks[wallet_address]

    def cleanup_user(self, wallet_address: str):
        """
        清理用户的同步状态（用户下线时调用）

        Args:
            wallet_address: 钱包地址
        """
        # 取消待处理的任务
        if wallet_address in self._pending_tasks:
            for task in self._pending_tasks[wallet_address].values():
                if not task.done():
                    task.cancel()
            del self._pending_tasks[wallet_address]

        # 清理状态
        if wallet_address in self._sync_status:
            del self._sync_status[wallet_address]

        # 清理锁
        if wallet_address in self._sync_locks:
            del self._sync_locks[wallet_address]

        logger.debug(f"Cleaned up sync state for {wallet_address}")

    def set_sync_callback(
        self,
        callback: Callable[[str, SyncType], Awaitable[str]]
    ):
        """
        设置同步回调函数

        Args:
            callback: 同步回调函数，接收 (wallet_address, sync_type)，返回 CID
        """
        self._sync_callback = callback
        logger.info("Sync callback updated")

    async def sync_all_pending(self) -> List[SyncResult]:
        """
        同步所有待处理的数据

        Returns:
            同步结果列表
        """
        logger.info("Syncing all pending data")

        results = []
        for wallet_address, status in self._sync_status.items():
            if status.has_pending:
                for sync_type in list(status.pending_syncs):
                    try:
                        result = await self._do_sync(wallet_address, sync_type, immediate=True)
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error syncing {wallet_address}:{sync_type.value}: {e}")

        logger.info(f"Synced {len(results)} pending items")
        return results
