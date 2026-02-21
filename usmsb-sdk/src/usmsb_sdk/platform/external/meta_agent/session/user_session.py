"""
UserSession - 用户会话核心类

该模块提供用户会话的核心实现，每个钱包地址对应一个 UserSession 实例。
会话内包含该用户专属的所有资源，包括工作空间、代码沙箱、浏览器上下文、数据库和 IPFS 客户端。

关键特性：
1. 延迟初始化：组件在首次访问时才创建
2. 资源隔离：每个用户的资源完全隔离
3. 会话生命周期管理：支持初始化、清理和状态跟踪
4. 跨节点支持：支持主节点检查和数据迁移
"""

import asyncio
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
from uuid import uuid4

if TYPE_CHECKING:
    # Type hints for components (延迟导入)
    from ..browser.browser_context import BrowserContext
    from ..database.user_database import UserDatabase
    from ..ipfs.ipfs_client import IPFSClient
    from ..migrate.data_migration import DataMigration
    from ..sandbox.code_sandbox import CodeSandbox
    from ..workspace.user_workspace import UserWorkspace


@dataclass
class SessionConfig:
    """
    会话配置类

    定义用户会话的各种超时和资源限制参数。

    Attributes:
        session_idle_timeout: 会话空闲超时时间（秒），默认30分钟
        browser_idle_timeout: 浏览器空闲超时时间（秒），默认10分钟
        max_code_timeout: 代码执行最大超时时间（秒）
        max_memory_mb: 代码执行最大内存限制（MB）
    """
    session_idle_timeout: int = 1800        # 30分钟
    browser_idle_timeout: int = 600         # 10分钟
    max_code_timeout: int = 30             # 代码执行超时30秒
    max_memory_mb: int = 256                # 最大内存256MB

    def is_session_idle(self, last_active: float) -> bool:
        """检查会话是否空闲超时"""
        return time.time() - last_active > self.session_idle_timeout

    def is_browser_idle(self, last_browser_active: float) -> bool:
        """检查浏览器是否空闲超时"""
        return time.time() - last_browser_active > self.browser_idle_timeout


@dataclass
class UserProfile:
    """
    用户画像数据结构

    Attributes:
        preferences: 用户偏好设置
        commitments: 用户承诺和目标
        knowledge: 用户知识总结
        last_updated: 最后更新时间
    """
    preferences: Dict[str, Any] = field(default_factory=dict)
    commitments: List[str] = field(default_factory=list)
    knowledge: Dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


class UserSession:
    """
    用户会话 - 所有用户操作的隔离上下文

    每个钱包地址对应一个 UserSession 实例，会话内包含该用户专属的所有资源。
    使用延迟初始化模式，组件在首次访问时才创建，提高启动性能。

    资源隔离保证：
    1. 工作空间：每个用户有独立的文件系统空间
    2. 代码沙箱：每个用户的代码执行环境完全隔离
    3. 浏览器上下文：每个用户有独立的 Cookie 和 LocalStorage
    4. 数据库：每个用户有专属的 SQLite 数据库文件
    5. IPFS 客户端：使用用户私钥派生的加密密钥

    Attributes:
        wallet_address: 用户钱包地址（主键）
        node_id: 当前节点 ID
        session_id: 会话唯一标识符
        is_primary_node: 是否是用户的主节点
        config: 会话配置对象
        created_at: 会话创建时间戳
        last_active: 最后活跃时间戳
    """

    def __init__(
        self,
        wallet_address: str,
        node_id: str,
        config: Optional[SessionConfig] = None,
        data_dir: Optional[str] = None
    ):
        """
        初始化用户会话

        Args:
            wallet_address: 用户钱包地址，作为用户唯一标识
            node_id: 当前节点 ID
            config: 会话配置，不提供则使用默认配置
            data_dir: 用户数据根目录，默认 /data/users
        """
        self.wallet_address: str = wallet_address
        self.node_id: str = node_id
        self.session_id: str = f"{wallet_address[:8]}_{uuid4().hex[:8]}"
        self.config: SessionConfig = config or SessionConfig()
        self._data_dir: str = data_dir or "/data/users"

        # 主节点检查
        self.is_primary_node: bool = False

        # 延迟初始化组件（首次访问时创建）
        self._workspace: Optional["UserWorkspace"] = None
        self._sandbox: Optional["CodeSandbox"] = None
        self._browser_context: Optional["BrowserContext"] = None
        self._db: Optional["UserDatabase"] = None
        self._ipfs_client: Optional["IPFSClient"] = None

        # 状态跟踪
        self.created_at: float = time.time()
        self.last_active: float = time.time()
        self._initialized: bool = False
        self._cleanup_done: bool = False

        # 浏览器活跃时间（独立跟踪）
        self._last_browser_active: float = time.time()

        # 用户缓存数据
        self._profile_cache: Optional[UserProfile] = None
        self._ipfs_cid: Optional[str] = None

        # 数据迁移服务（延迟初始化）
        self._data_migration: Optional[DataMigration] = None

    # ========== 属性访问器（延迟初始化） ==========

    @property
    def workspace(self) -> "UserWorkspace":
        """
        延迟初始化工作空间

        工作空间提供用户专属的文件系统隔离。

        Returns:
            UserWorkspace: 用户工作空间实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._workspace is None:
            from ..workspace.user_workspace import UserWorkspace

            self._workspace = UserWorkspace(
                wallet_address=self.wallet_address,
                workspace_root=Path(self._data_dir) / self.wallet_address / "workspace"
            )
        return self._workspace

    @property
    def sandbox(self) -> "CodeSandbox":
        """
        延迟初始化代码沙箱

        沙箱提供安全的 Python 代码执行环境，限制可用的内置函数、
        模块、文件系统访问、执行时间和内存使用。

        Returns:
            CodeSandbox: 代码沙箱实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._sandbox is None:
            from ..sandbox.code_sandbox import CodeSandbox

            self._sandbox = CodeSandbox(
                wallet_address=self.wallet_address,
                sandbox_root=self._data_dir
            )
        return self._sandbox

    @property
    def browser_context(self) -> "BrowserContext":
        """
        延迟初始化浏览器上下文

        浏览器上下文提供用户隔离的浏览器会话，包括：
        - 隔离的 Cookie 和 LocalStorage
        - 隔离的下载目录
        - 会话结束时自动清理

        Returns:
            BrowserContext: 浏览器上下文实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._browser_context is None:
            from ..browser.browser_context import BrowserContext

            self._browser_context = BrowserContext(
                wallet_address=self.wallet_address,
                user_data_dir=Path(self._data_dir) / self.wallet_address / "browser/user_data"
            )
        return self._browser_context

    @property
    def db(self) -> "UserDatabase":
        """
        延迟初始化数据库

        数据库提供用户专属的 SQLite 数据库连接，包括：
        - 对话历史（conversations.db）
        - 记忆/画像（memory.db）
        - 私有知识库（knowledge.db）

        Returns:
            UserDatabase: 用户数据库实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._db is None:
            from ..database.user_database import UserDatabase

            self._db = UserDatabase(
                wallet_address=self.wallet_address,
                data_dir=self._data_dir
            )
        return self._db

    @property
    def ipfs_client(self) -> "IPFSClient":
        """
        延迟初始化 IPFS 客户端

        IPFS 客户端处理用户数据的 IPFS 存储，包括：
        - 加密上传
        - 下载解密
        - CID 管理

        Returns:
            IPFSClient: IPFS 客户端实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._ipfs_client is None:
            from ..ipfs.ipfs_client import IPFSClient

            self._ipfs_client = IPFSClient(
                gateways=[os.getenv("IPFS_NODE", "https://ipfs.io")]
            )
        return self._ipfs_client

    @property
    def data_migration(self) -> "DataMigration":
        """
        延迟初始化数据迁移服务

        数据迁移服务提供：
        - 从 IPFS 导入数据到本地
        - 从本地导出数据到 IPFS
        - 迁移验证和进度跟踪

        Returns:
            DataMigration: 数据迁移服务实例

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        if self._data_migration is None:
            from ..migrate.data_migration import DataMigration

            self._data_migration = DataMigration(session=self)
        return self._data_migration

    # ========== 核心方法 ==========

    async def init(self) -> None:
        """
        初始化会话

        创建必要的目录结构和元数据文件。
        组件使用延迟初始化，在此处不创建组件实例。

        目录结构：
        /data/users/{wallet_address}/
        ├── meta.json              # 用户元信息
        ├── conversations.db       # 对话历史
        ├── memory.db              # 记忆/画像
        ├── knowledge.db            # 私有知识库
        ├── workspace/              # 工作目录
        │   ├── temp/
        │   ├── output/
        │   └── uploads/
        ├── sandbox/                # 代码执行沙箱
        └── browser/                # 浏览器数据
            └── user_data/

        Raises:
            IOError: 如果无法创建目录或写入元数据
        """
        if self._initialized:
            return  # 已初始化，直接返回

        user_dir = Path(self._data_dir) / self.wallet_address
        user_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        subdirs = [
            user_dir / "workspace" / "temp",
            user_dir / "workspace" / "output",
            user_dir / "workspace" / "uploads",
            user_dir / "sandbox",
            user_dir / "browser" / "user_data",
        ]
        for subdir in subdirs:
            subdir.mkdir(parents=True, exist_ok=True)

        # 加载或创建元数据
        meta_file = user_dir / "meta.json"
        if meta_file.exists():
            with open(meta_file, 'r') as f:
                meta_data = json.load(f)
                self.is_primary_node = meta_data.get("primary_node") == self.node_id
                self._ipfs_cid = meta_data.get("ipfs_cid")
        else:
            # 新用户，当前节点作为主节点
            meta_data = {
                "wallet_address": self.wallet_address,
                "primary_node": self.node_id,
                "created_at": self.created_at,
                "last_active": self.last_active,
                "ipfs_cid": None
            }
            with open(meta_file, 'w') as f:
                json.dump(meta_data, f, indent=2)
            self.is_primary_node = True

        self._initialized = True

    async def cleanup(self) -> None:
        """
        清理会话资源

        释放会话占用的所有资源：
        1. 关闭浏览器上下文（保留用户数据目录）
        2. 关闭数据库连接
        3. 清理沙箱变量
        4. 更新元数据文件的 last_active 时间
        5. 清除内存中的加密密钥

        注意：
        - 不删除用户数据文件（对话历史、画像等已持久化）
        - 浏览器会话的 Cookie/登录状态会被清除
        - IPFS 同步需要由 SessionManager 触发
        """
        if self._cleanup_done or not self._initialized:
            return

        # 关闭浏览器
        if self._browser_context is not None:
            await self._browser_context.close()
            self._browser_context = None

        # 关闭数据库连接
        if self._db is not None:
            await self._db.close()
            self._db = None

        # 清理沙箱（内存清除）
        if self._sandbox is not None:
            # CodeSandbox 没有持久化资源，只需清除引用
            self._sandbox = None

        # 清除 IPFS 客户端（内存清除）
        if self._ipfs_client is not None:
            # IPFSClient 需要清除加密密钥
            if hasattr(self._ipfs_client, 'clear_key'):
                self._ipfs_client.clear_key()
            self._ipfs_client = None

        # 清除数据迁移服务
        self._data_migration = None

        # 更新元数据
        await self._update_metadata()

        # 清除缓存
        self._profile_cache = None

        self._cleanup_done = True

    async def get_profile(self) -> Dict[str, Any]:
        """
        获取用户画像（本地优先）

        获取用户画像数据的策略：
        1. 首先检查内存缓存
        2. 其次查询本地数据库
        3. 如果本地无数据，尝试从 IPFS 拉取
        4. 如果 IPFS 也没数据，返回空画像

        Returns:
            Dict: 用户画像数据，包含：
                - preferences: 用户偏好设置
                - commitments: 用户承诺和目标
                - knowledge: 用户知识总结
                - last_updated: 最后更新时间

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        # 检查缓存
        if self._profile_cache is not None:
            return self._profile_cache.to_dict()

        # 查询本地数据库
        try:
            profile_data = await self.db.get_profile()
            if profile_data:
                self._profile_cache = UserProfile(**profile_data)
                return profile_data
        except Exception as e:
            # 本地查询失败，继续尝试 IPFS
            pass

        # 尝试从 IPFS 拉取
        try:
            if self._ipfs_cid:
                ipfs_data = await self.ipfs_client.download_user_data(
                    self.wallet_address,
                    self._ipfs_cid
                )
                if ipfs_data and "profile" in ipfs_data:
                    profile_data = ipfs_data["profile"]
                    # 导入到本地数据库
                    await self.db.update_profile(UserProfile(**profile_data))
                    self._profile_cache = UserProfile(**profile_data)
                    return profile_data
        except Exception as e:
            # IPFS 拉取失败，返回空画像
            pass

        # 返回空画像
        return UserProfile().to_dict()

    async def update_profile(self, profile: UserProfile) -> None:
        """
        更新用户画像

        Args:
            profile: 用户画像对象

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        # 更新数据库
        await self.db.update_profile(profile)

        # 更新缓存
        self._profile_cache = profile

        # 更新活跃时间
        self.update_activity()

    async def sync_to_ipfs(
        self,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        verify: bool = True
    ) -> str:
        """
        同步数据到 IPFS

        将用户数据同步到 IPFS 网络：
        1. 导出用户画像和私有知识库
        2. 使用用户私钥派生的密钥加密
        3. 上传到 IPFS
        4. 更新元数据文件中的 CID
        5. 返回新的 CID

        Args:
            progress_callback: 可选的进度回调函数
                接收包含 stage, percentage, message 的字典
            verify: 是否验证上传数据（默认 True）

        Returns:
            str: IPFS CID（内容标识符）

        Raises:
            RuntimeError: 如果会话未初始化
            IOError: 如果 IPFS 上传失败
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        # 添加进度回调
        if progress_callback:
            self.data_migration.add_progress_callback(
                lambda p: progress_callback({
                    "stage": p.stage,
                    "percentage": p.percentage,
                    "message": p.message,
                    "elapsed_seconds": p.elapsed_seconds,
                    "speed_mb_per_sec": p.speed_mb_per_sec,
                    "total_items": p.total_items,
                    "completed_items": p.completed_items
                })
            )

        # 使用 DataMigration 服务导出数据
        result = await self.data_migration.export_to_ipfs(verify=verify)

        if not result.success:
            raise IOError(f"IPFS sync failed: {result.error}")

        return result.cid

    async def check_primary_node(self) -> bool:
        """
        检查当前节点是否是用户的主节点

        主节点是指用户首次访问时所在的节点，负责存储用户元信息。
        主节点的判断存储在 meta.json 文件中。

        Returns:
            bool: 如果当前节点是主节点返回 True，否则返回 False

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        return self.is_primary_node

    async def migrate_to_this_node(
        self,
        progress_callback: Optional[Callable[[Dict], None]] = None,
        force: bool = False,
        verify: bool = True
    ) -> bool:
        """
        从 IPFS 迁移数据到当前节点

        将用户数据从 IPFS 迁移到当前节点：
        1. 从 IPFS 获取最新的 CID
        2. 下载并解密用户数据
        3. 导入到本地数据库
        4. 更新元数据文件

        Args:
            progress_callback: 可选的进度回调函数
                接收包含 stage, percentage, message 的字典
            force: 强制迁移，即使本地已有数据（默认 False）
            verify: 是否验证迁移数据（默认 True）

        Returns:
            bool: 迁移成功返回 True，否则返回 False

        Raises:
            RuntimeError: 如果会话未初始化
        """
        if not self._initialized:
            raise RuntimeError("Session not initialized. Call init() first.")

        # 添加进度回调
        if progress_callback:
            self.data_migration.add_progress_callback(
                lambda p: progress_callback({
                    "stage": p.stage,
                    "percentage": p.percentage,
                    "message": p.message,
                    "elapsed_seconds": p.elapsed_seconds,
                    "speed_mb_per_sec": p.speed_mb_per_sec,
                    "total_items": p.total_items,
                    "completed_items": p.completed_items
                })
            )

        # 使用 DataMigration 服务导入数据
        result = await self.data_migration.migrate_from_ipfs(force=force, verify=verify)

        return result.success

    def update_activity(self) -> None:
        """
        更新活跃时间

        更新会话的 last_active 时间戳，用于超时检测。
        每次用户执行操作时都应该调用此方法。

        同时更新浏览器活跃时间。
        """
        self.last_active = time.time()
        self._last_browser_active = time.time()

    def update_browser_activity(self) -> None:
        """
        更新浏览器活跃时间

        更新浏览器的 last_active 时间戳，用于浏览器超时检测。
        每次浏览器操作时都应该调用此方法。
        """
        self._last_browser_active = time.time()

    def is_idle(self) -> bool:
        """
        检查会话是否空闲超时

        Returns:
            bool: 如果会话空闲时间超过配置的阈值返回 True
        """
        return self.config.is_session_idle(self.last_active)

    def is_browser_idle(self) -> bool:
        """
        检查浏览器是否空闲超时

        Returns:
            bool: 如果浏览器空闲时间超过配置的阈值返回 True
        """
        return self.config.is_browser_idle(self._last_browser_active)

    async def _update_metadata(self) -> None:
        """
        更新元数据文件

        私有方法，用于更新 meta.json 文件中的 last_active 和 ipfs_cid。
        """
        user_dir = Path(self._data_dir) / self.wallet_address
        meta_file = user_dir / "meta.json"

        meta_data = {
            "wallet_address": self.wallet_address,
            "primary_node": self.node_id if self.is_primary_node else None,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "ipfs_cid": self._ipfs_cid
        }

        with open(meta_file, 'w') as f:
            json.dump(meta_data, f, indent=2)

    def __repr__(self) -> str:
        """返回会话的字符串表示"""
        return (
            f"UserSession(session_id={self.session_id}, "
            f"wallet={self.wallet_address[:10]}..., "
            f"node={self.node_id}, "
            f"primary={self.is_primary_node}, "
            f"age={int(time.time() - self.created_at)}s)"
        )


# 为 UserProfile 添加 to_dict 方法
def _user_profile_to_dict(self) -> Dict[str, Any]:
    """将 UserProfile 转换为字典"""
    return {
        "preferences": self.preferences,
        "commitments": self.commitments,
        "knowledge": self.knowledge,
        "last_updated": self.last_updated
    }


UserProfile.to_dict = _user_profile_to_dict  # type: ignore
