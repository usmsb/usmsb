"""
SessionManager - 会话管理器

负责用户会话的创建、获取、清理。
确保每个钱包地址只有一个活跃会话。

职责:
- 管理所有用户会话的生命周期
- 确保会话的隔离性和线程安全
- 自动清理空闲会话
"""

import asyncio
import logging
import time
from pathlib import Path

from .user_session import SessionConfig, UserSession

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话管理器

    负责用户会话的创建、获取、清理
    确保每个钱包地址只有一个活跃会话
    """

    def __init__(
        self,
        node_id: str,
        data_dir: str | None = None,
        config: SessionConfig | None = None
    ):
        """
        初始化会话管理器

        Args:
            node_id: 当前节点ID
            data_dir: 数据目录，默认 /data
            config: 会话配置，默认使用默认配置
        """
        self.node_id: str = node_id
        self.data_dir: Path = Path(data_dir or "/data")
        self.config: SessionConfig = config or SessionConfig()

        # 会话存储
        self._sessions: dict[str, UserSession] = {}  # wallet -> session 映射
        self._lock: asyncio.Lock = asyncio.Lock()

        # 状态
        self._running: bool = False
        self._cleanup_task: asyncio.Task | None = None

        # 确保数据目录存在
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        """
        启动会话管理器

        启动后台清理任务，定期清理空闲会话。
        """
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"SessionManager started for node {self.node_id}")

    async def stop(self) -> None:
        """
        停止会话管理器

        停止后台清理任务，并关闭所有会话。
        """
        if not self._running:
            return

        self._running = False

        # 取消清理任务
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # 关闭所有会话
        await self.close_all_sessions()

        logger.info(f"SessionManager stopped for node {self.node_id}")

    async def get_or_create_session(
        self,
        wallet_address: str
    ) -> UserSession:
        """
        获取或创建用户会话

        确保每个钱包地址只有一个活跃会话。

        Args:
            wallet_address: 用户钱包地址

        Returns:
            UserSession: 用户会话实例
        """
        async with self._lock:
            # 检查是否已存在会话
            if wallet_address in self._sessions:
                session = self._sessions[wallet_address]
                # 更新活跃时间
                session.update_activity()
                logger.debug(f"Retrieved existing session for {wallet_address[:10]}...")
                return session

            # 创建新会话
            session = UserSession(
                wallet_address=wallet_address,
                node_id=self.node_id,
                config=self.config,
                data_dir=str(self.data_dir)
            )

            # 初始化会话
            await session.init()

            # 存储会话
            self._sessions[wallet_address] = session

            logger.info(f"Created new session for {wallet_address[:10]}...")
            return session

    async def get_session(
        self,
        wallet_address: str
    ) -> UserSession | None:
        """
        获取已存在的会话（不创建）

        Args:
            wallet_address: 用户钱包地址

        Returns:
            UserSession: 用户会话实例，如果不存在返回 None
        """
        async with self._lock:
            return self._sessions.get(wallet_address)

    async def close_session(
        self,
        wallet_address: str,
        sync_to_ipfs: bool = True
    ) -> bool:
        """
        关闭指定用户的会话

        Args:
            wallet_address: 用户钱包地址
            sync_to_ipfs: 是否同步数据到 IPFS，默认 True

        Returns:
            bool: 如果会话存在并关闭成功返回 True，否则返回 False

        Note:
            - 关闭前会尝试同步数据到 IPFS（如果 sync_to_ipfs 为 True）
            - 会话资源会被释放，但用户数据文件保留
        """
        async with self._lock:
            session = self._sessions.pop(wallet_address, None)
            if session is None:
                return False

        # 在锁外执行清理操作（避免长时间持锁）
        try:
            # 同步数据到 IPFS（如果需要）
            if sync_to_ipfs:
                try:
                    cid = await session.sync_to_ipfs()
                    logger.info(
                        f"Session {wallet_address[:10]}... synced to IPFS: {cid}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to sync session {wallet_address[:10]}... to IPFS: {e}"
                    )

            # 清理会话资源
            await session.cleanup()

            logger.info(f"Closed session for {wallet_address[:10]}...")
            return True

        except Exception as e:
            logger.error(f"Error closing session for {wallet_address[:10]}...: {e}")
            return False

    async def close_all_sessions(self, sync_to_ipfs: bool = True) -> None:
        """
        关闭所有会话（服务关闭时调用）

        Args:
            sync_to_ipfs: 是否同步数据到 IPFS，默认 True

        Note:
            - 在服务关闭前调用此方法确保资源正确释放
            - 会按顺序关闭每个会话
        """
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        for session in sessions:
            try:
                # 同步数据到 IPFS（如果需要）
                if sync_to_ipfs:
                    try:
                        cid = await session.sync_to_ipfs()
                        logger.info(
                            f"Session {session.wallet_address[:10]}... synced to IPFS: {cid}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to sync session {session.wallet_address[:10]}...: {e}"
                        )

                # 清理会话资源
                await session.cleanup()

            except Exception as e:
                logger.error(f"Error closing session {session.session_id}: {e}")

        logger.info(f"Closed all sessions, total: {len(sessions)}")

    async def get_active_sessions(self) -> list[str]:
        """
        获取所有活跃会话的钱包地址列表

        Returns:
            List[str]: 钱包地址列表，按最后活跃时间排序（最新在前）
        """
        async with self._lock:
            sessions = list(self._sessions.items())
            # 按最后活跃时间排序（最新在前）
            sessions.sort(key=lambda x: x[1].last_active, reverse=True)
            return [wallet for wallet, _ in sessions]

    async def cleanup_idle_sessions(
        self,
        max_idle_seconds: int | None = None
    ) -> int:
        """
        清理空闲超过指定时间的会话

        Args:
            max_idle_seconds: 最大空闲时间（秒），不提供则使用配置默认值

        Returns:
            int: 清理的会话数量

        Note:
            - 清理前会同步数据到 IPFS
            - 只关闭空闲会话，不影响活跃会话
        """
        if max_idle_seconds is None:
            max_idle_seconds = self.config.session_idle_timeout

        async with self._lock:
            idle_wallets = []
            for wallet_address, session in self._sessions.items():
                if session.is_idle():
                    # 检查空闲时间是否超过阈值
                    idle_time = time.time() - session.last_active
                    if idle_time > max_idle_seconds:
                        idle_wallets.append(wallet_address)

        # 在锁外执行清理（避免长时间持锁）
        cleaned = 0
        for wallet_address in idle_wallets:
            if await self.close_session(wallet_address, sync_to_ipfs=True):
                cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} idle sessions")

        return cleaned

    async def _cleanup_loop(self) -> None:
        """
        后台清理循环

        定期检查并清理空闲会话。
        此方法由 start() 启动为后台任务。
        """
        logger.info("Cleanup loop started (interval: 60s)")

        while self._running:
            try:
                # 每分钟检查一次
                await asyncio.sleep(60)

                if not self._running:
                    break

                # 清理空闲会话
                await self.cleanup_idle_sessions(
                    max_idle_seconds=self.config.session_idle_timeout
                )

            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

        logger.info("Cleanup loop stopped")

    def get_session_count(self) -> int:
        """
        获取当前活跃会话数量

        Returns:
            int: 活跃会话数量
        """
        return len(self._sessions)

    async def cleanup_idle_browsers(self) -> int:
        """
        清理空闲浏览器

        关闭所有空闲浏览器上下文（不关闭会话）。

        Returns:
            int: 清理的浏览器数量

        Note:
            - 只关闭浏览器实例，会话保持活跃
            - 浏览器可以按需重新打开
        """
        cleaned = 0

        # 获取所有会话
        async with self._lock:
            sessions = list(self._sessions.values())

        for session in sessions:
            if not session._cleanup_done and session.is_browser_idle():
                try:
                    if session._browser_context is not None:
                        await session._browser_context.close()
                        session._browser_context = None
                        cleaned += 1
                        logger.info(f"Browser closed for session {session.wallet_address[:10]}...")
                except Exception as e:
                    logger.error(
                        f"Error closing browser for {session.wallet_address[:10]}...: {e}"
                    )

        return cleaned

    async def get_session_info(self, wallet_address: str) -> dict | None:
        """
        获取会话详细信息

        Args:
            wallet_address: 用户钱包地址

        Returns:
            Optional[Dict]: 会话信息字典，如果会话不存在则返回 None
                - wallet_address: 钱包地址
                - session_id: 会话 ID
                - node_id: 节点 ID
                - is_primary_node: 是否是主节点
                - created_at: 创建时间
                - last_active: 最后活跃时间
                - idle_seconds: 空闲秒数
                - is_browser_idle: 浏览器是否空闲
        """
        session = await self.get_session(wallet_address)
        if not session:
            return None

        return {
            "wallet_address": session.wallet_address,
            "session_id": session.session_id,
            "node_id": session.node_id,
            "is_primary_node": session.is_primary_node,
            "created_at": session.created_at,
            "last_active": session.last_active,
            "idle_seconds": time.time() - session.last_active,
            "is_browser_idle": session.is_browser_idle(),
        }

    async def get_session_stats(self) -> dict:
        """
        获取会话统计信息

        Returns:
            Dict: 统计信息
                - total_sessions: 总会话数
                - active_sessions: 活跃会话数
                - idle_sessions: 空闲会话数
                - browser_active: 浏览器活跃数
                - avg_idle_time: 平均空闲时间（秒）
                - max_idle_time: 最大空闲时间（秒）
                - node_id: 节点 ID
                - running: 是否正在运行
        """
        async with self._lock:
            sessions = list(self._sessions.values())

        total = len(sessions)
        idle = sum(1 for s in sessions if s.is_idle())
        browser_idle = sum(1 for s in sessions if s.is_browser_idle())

        # 计算空闲时间统计
        if sessions:
            idle_times = [time.time() - s.last_active for s in sessions]
            avg_idle_time = sum(idle_times) / len(idle_times)
            max_idle_time = max(idle_times)
        else:
            avg_idle_time = 0
            max_idle_time = 0

        return {
            "total_sessions": total,
            "active_sessions": total - idle,
            "idle_sessions": idle,
            "browser_active": total - browser_idle,
            "avg_idle_time": round(avg_idle_time, 2),
            "max_idle_time": round(max_idle_time, 2),
            "node_id": self.node_id,
            "running": self._running,
        }

    def __repr__(self) -> str:
        """返回会话管理器的字符串表示"""
        return (
            f"SessionManager(node_id={self.node_id}, "
            f"sessions={len(self._sessions)}, "
            f"running={self._running})"
        )
