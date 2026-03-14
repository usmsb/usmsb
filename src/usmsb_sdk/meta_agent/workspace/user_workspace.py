"""
UserWorkspace - 用户工作空间

管理用户专属的文件系统空间，提供安全的文件操作接口。
所有文件操作都限制在用户工作空间内，防止目录遍历攻击。

Author: USMSB Team
Version: 1.0.0
"""

import asyncio
import logging
import shutil
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class WorkspaceError(Exception):
    """工作空间基础异常"""

    pass


class PathValidationError(WorkspaceError):
    """路径验证异常 - 路径不在工作空间内"""

    pass


class QuotaExceededError(WorkspaceError):
    """配额超限异常"""

    pass


class FileOperationError(WorkspaceError):
    """文件操作异常"""

    pass


class DirectoryType(Enum):
    """目录类型枚举"""

    TEMP = "temp"
    OUTPUT = "output"
    UPLOADS = "uploads"


@dataclass
class WorkspaceConfig:
    """
    工作空间配置

    Attributes:
        workspace_root: 工作空间根目录
        max_file_size_mb: 单文件最大大小（MB），默认10MB
        max_storage_mb: 存储空间限制（MB），默认100MB
        max_files: 最大文件数量，默认1000个
        auto_cleanup_temp: 是否自动清理临时文件
        temp_file_ttl_seconds: 临时文件过期时间（秒），默认24小时
    """

    workspace_root: str = "/data/users"
    max_file_size_mb: int = 10
    max_storage_mb: int = 100
    max_files: int = 1000
    auto_cleanup_temp: bool = True
    temp_file_ttl_seconds: int = 86400  # 24 hours

    @property
    def max_file_size_bytes(self) -> int:
        """单文件最大大小（字节）"""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_storage_bytes(self) -> int:
        """存储空间限制（字节）"""
        return self.max_storage_mb * 1024 * 1024


@dataclass
class FileInfo:
    """
    文件信息

    Attributes:
        name: 文件名
        path: 相对于工作空间的路径
        size: 文件大小（字节）
        is_dir: 是否为目录
        modified_at: 最后修改时间戳
        created_at: 创建时间戳（可选）
    """

    name: str
    path: str
    size: int
    is_dir: bool
    modified_at: float
    created_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "path": self.path,
            "size": self.size,
            "is_dir": self.is_dir,
            "modified_at": self.modified_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_path(cls, path: Path, relative_to: Path) -> "FileInfo":
        """从路径创建 FileInfo"""
        stat = path.stat()
        relative_path = str(path.relative_to(relative_to))

        return cls(
            name=path.name,
            path=relative_path,
            size=stat.st_size,
            is_dir=path.is_dir(),
            modified_at=stat.st_mtime,
            created_at=stat.st_ctime,
        )


class UserWorkspace:
    """
    用户工作空间

    管理用户专属的文件系统空间：

    1. 所有文件操作限制在用户目录内
    2. 提供安全路径验证
    3. 支持文件上传下载
    4. 配额管理（文件大小、存储空间、文件数量）

    目录结构:
        /data/users/{wallet_address}/workspace/
            ├── temp/       # 临时文件
            ├── output/     # 输出文件
            └── uploads/    # 用户上传文件

    安全特性:
        - 路径验证：防止 ../ 等目录遍历攻击
        - 文件大小限制：单文件不超过配置的大小
        - 存储配额：总存储空间限制
        - 文件数量限制：防止文件数过多

    使用示例:
        >>> workspace = UserWorkspace("0x1234...")
        >>> await workspace.init()
        >>> await workspace.write_file("test.txt", "Hello, World!")
        >>> content = await workspace.read_file("test.txt")
        >>> files = await workspace.list_files()
    """

    def __init__(
        self,
        wallet_address: str,
        config: WorkspaceConfig | None = None,
    ):
        """
        初始化用户工作空间

        Args:
            wallet_address: 用户钱包地址
            config: 工作空间配置，默认使用默认配置
        """
        self.wallet_address = wallet_address
        self.config = config or WorkspaceConfig()

        # 工作空间根目录
        self.workspace_root = (
            Path(self.config.workspace_root) / wallet_address / "workspace"
        )

        # 子目录
        self.temp_dir = self.workspace_root / DirectoryType.TEMP.value
        self.output_dir = self.workspace_root / DirectoryType.OUTPUT.value
        self.uploads_dir = self.workspace_root / DirectoryType.UPLOADS.value

        # 所有子目录
        self._subdirs = {
            DirectoryType.TEMP: self.temp_dir,
            DirectoryType.OUTPUT: self.output_dir,
            DirectoryType.UPLOADS: self.uploads_dir,
        }

        # 配额统计缓存
        self._storage_used_cache: int | None = None
        self._file_count_cache: int | None = None
        self._cache_timestamp: float | None = None
        self._cache_ttl = 60  # 缓存60秒

        # 写锁（用于并发控制）
        self._write_lock = asyncio.Lock()

        logger.info(
            f"UserWorkspace initialized for {wallet_address} at {self.workspace_root}"
        )

    async def init(self) -> None:
        """
        初始化工作空间目录

        创建必要的目录结构：
        - {workspace_root}/temp/
        - {workspace_root}/output/
        - {workspace_root}/uploads/

        Raises:
            WorkspaceError: 如果创建目录失败
        """
        logger.info(f"Initializing workspace for {self.wallet_address}")

        try:
            # 创建工作空间根目录
            self.workspace_root.mkdir(parents=True, exist_ok=True)

            # 创建子目录
            for _dir_type, dir_path in self._subdirs.items():
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")

            # 创建 .gitkeep 保持空目录在版本控制中
            for dir_path in self._subdirs.values():
                gitkeep = dir_path / ".gitkeep"
                if not gitkeep.exists():
                    gitkeep.touch()

            logger.info(f"Workspace initialized successfully for {self.wallet_address}")

        except OSError as e:
            error_msg = f"Failed to initialize workspace for {self.wallet_address}: {e}"
            logger.error(error_msg)
            raise WorkspaceError(error_msg) from e

    def resolve_path(
        self, relative_path: str, subdir: DirectoryType | None = None
    ) -> Path:
        """
        解析相对路径为绝对路径（限制在工作空间内）

        Args:
            relative_path: 相对路径（例如: "test.txt", "subdir/file.txt"）
            subdir: 可选的子目录类型（temp, output, uploads）

        Returns:
            绝对路径

        Raises:
            PathValidationError: 如果路径不在工作空间内

        Examples:
            >>> workspace.resolve_path("test.txt")
            PosixPath('/data/users/0x1234/workspace/test.txt')

            >>> workspace.resolve_path("test.txt", DirectoryType.TEMP)
            PosixPath('/data/users/0x1234/workspace/temp/test.txt')
        """
        # 规范化路径
        relative_path = relative_path.strip().lstrip("/")

        # 处理空路径
        if not relative_path or relative_path == ".":
            base_dir = self._subdirs.get(subdir, self.workspace_root)
            return base_dir

        # 确定基础目录
        base_dir = self._subdirs.get(subdir, self.workspace_root)

        # 解析为 Path 对象
        try:
            resolved = (base_dir / relative_path).resolve()
        except RuntimeError as e:
            error_msg = f"Invalid path '{relative_path}': {e}"
            logger.warning(error_msg)
            raise PathValidationError(error_msg) from e

        # 验证路径是否在指定的基础目录内
        # 如果指定了子目录，则路径必须在该子目录内
        if subdir:
            subdir_resolved = base_dir.resolve()
            try:
                resolved.relative_to(subdir_resolved)
            except ValueError:
                error_msg = (
                    f"Path '{relative_path}' resolves outside {subdir.value} directory: {resolved}"
                )
                logger.warning(error_msg)
                raise PathValidationError(error_msg)
        else:
            # 如果没有指定子目录，检查是否在工作空间根目录内
            if not self.validate_path(resolved):
                error_msg = (
                    f"Path '{relative_path}' resolves outside workspace: {resolved}"
                )
                logger.warning(error_msg)
                raise PathValidationError(error_msg)

        return resolved

    def validate_path(self, path: Path) -> bool:
        """
        验证路径是否在工作空间内（防止目录遍历攻击）

        Args:
            path: 要验证的路径

        Returns:
            True 如果路径在工作空间内，否则 False

        安全检查:
            - 路径必须解析在工作空间根目录下
            - 不能包含 .. 逃逸到工作空间外
        """
        try:
            # 解析为绝对路径
            resolved = path.resolve()

            # 检查是否是工作空间的子路径
            workspace_resolved = self.workspace_root.resolve()
            try:
                resolved.relative_to(workspace_resolved)
                return True
            except ValueError:
                return False
        except (OSError, RuntimeError) as e:
            logger.debug(f"Path validation failed for {path}: {e}")
            return False

    def _validate_file_size(self, size: int) -> None:
        """
        验证文件大小

        Args:
            size: 文件大小（字节）

        Raises:
            QuotaExceededError: 如果文件大小超过限制
        """
        if size > self.config.max_file_size_bytes:
            error_msg = (
                f"File size {size} bytes exceeds maximum "
                f"{self.config.max_file_size_mb}MB"
            )
            logger.warning(error_msg)
            raise QuotaExceededError(error_msg)

    async def _check_quota(self, file_size: int = 0) -> None:
        """
        检查配额限制

        Args:
            file_size: 要写入的文件大小（字节）

        Raises:
            QuotaExceededError: 如果超过配额限制
        """
        storage_used = await self.get_storage_used()
        file_count = await self.get_file_count()

        # 检查存储空间
        if storage_used + file_size > self.config.max_storage_bytes:
            used_mb = storage_used / (1024 * 1024)
            max_mb = self.config.max_storage_mb
            error_msg = (
                f"Storage quota exceeded: {used_mb:.2f}MB used "
                f"({max_mb}MB limit)"
            )
            logger.warning(error_msg)
            raise QuotaExceededError(error_msg)

        # 检查文件数量
        if file_count >= self.config.max_files:
            error_msg = (
                f"File count quota exceeded: {file_count} files "
                f"({self.config.max_files} limit)"
            )
            logger.warning(error_msg)
            raise QuotaExceededError(error_msg)

    def _invalidate_cache(self) -> None:
        """使缓存失效"""
        self._storage_used_cache = None
        self._file_count_cache = None
        self._cache_timestamp = None

    async def write_file(
        self,
        relative_path: str,
        content: str | bytes,
        subdir: DirectoryType | None = None,
        overwrite: bool = True,
    ) -> Path:
        """
        写入文件

        Args:
            relative_path: 相对路径
            content: 文件内容（字符串或字节）
            subdir: 可选的子目录类型
            overwrite: 是否覆盖已存在文件

        Returns:
            文件路径

        Raises:
            PathValidationError: 路径无效
            QuotaExceededError: 配额超限
            FileOperationError: 文件操作失败

        Examples:
            >>> await workspace.write_file("hello.txt", "Hello, World!")
            >>> await workspace.write_file("data.json", '{"key": "value"}', DirectoryType.OUTPUT)
        """
        async with self._write_lock:
            # 解析路径
            abs_path = self.resolve_path(relative_path, subdir)

            # 如果文件已存在且不覆盖
            if abs_path.exists() and not overwrite:
                raise FileOperationError(f"File already exists: {relative_path}")

            # 转换内容为字节
            if isinstance(content, str):
                content_bytes = content.encode("utf-8")
            else:
                content_bytes = content

            # 验证文件大小
            self._validate_file_size(len(content_bytes))

            # 检查配额（减去已存在文件的大小）
            existing_size = 0
            if abs_path.exists():
                existing_size = abs_path.stat().st_size

            await self._check_quota(len(content_bytes) - existing_size)

            # 写入文件
            try:
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                abs_path.write_bytes(content_bytes)

                # 使缓存失效
                self._invalidate_cache()

                logger.debug(
                    f"Wrote file {relative_path} ({len(content_bytes)} bytes) "
                    f"for {self.wallet_address}"
                )

                return abs_path

            except OSError as e:
                error_msg = f"Failed to write file {relative_path}: {e}"
                logger.error(error_msg)
                raise FileOperationError(error_msg) from e

    async def read_file(
        self,
        relative_path: str,
        subdir: DirectoryType | None = None,
        as_text: bool = False,
    ) -> bytes | str:
        """
        读取文件

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型
            as_text: 是否返回字符串（True）或字节（False）

        Returns:
            文件内容（字节或字符串）

        Raises:
            PathValidationError: 路径无效
            FileNotFoundError: 文件不存在
            FileOperationError: 文件操作失败

        Examples:
            >>> content = await workspace.read_file("hello.txt")
            >>> text = await workspace.read_file("hello.txt", as_text=True)
        """
        abs_path = self.resolve_path(relative_path, subdir)

        if not abs_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")

        if not abs_path.is_file():
            raise FileOperationError(f"Not a file: {relative_path}")

        try:
            if as_text:
                content = abs_path.read_text(encoding="utf-8")
            else:
                content = abs_path.read_bytes()

            logger.debug(f"Read file {relative_path} for {self.wallet_address}")
            return content

        except OSError as e:
            error_msg = f"Failed to read file {relative_path}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def list_files(
        self,
        directory: str = "",
        subdir: DirectoryType | None = None,
        pattern: str = "*",
        recursive: bool = False,
    ) -> list[FileInfo]:
        """
        列出文件

        Args:
            directory: 相对目录路径
            subdir: 可选的子目录类型
            pattern: 文件匹配模式（例如: "*.txt", "image_*.png"）
            recursive: 是否递归列出子目录

        Returns:
            文件信息列表

        Raises:
            PathValidationError: 路径无效
            FileOperationError: 文件操作失败

        Examples:
            >>> files = await workspace.list_files()
            >>> files = await workspace.list_files("images", pattern="*.png")
            >>> all_files = await workspace.list_files(recursive=True)
        """
        # 获取目录路径
        base_path = self.resolve_path(directory, subdir)

        if not base_path.exists():
            return []

        if not base_path.is_dir():
            raise FileOperationError(f"Not a directory: {directory}")

        try:
            # 查找文件
            if recursive:
                matches = base_path.rglob(pattern)
            else:
                matches = base_path.glob(pattern)

            # 转换为 FileInfo 列表
            files = []
            for path in matches:
                files.append(FileInfo.from_path(path, self.workspace_root))

            # 按名称排序（目录优先）
            files.sort(key=lambda f: (not f.is_dir, f.name.lower()))

            logger.debug(
                f"Listed {len(files)} files in {directory} "
                f"for {self.wallet_address}"
            )

            return files

        except OSError as e:
            error_msg = f"Failed to list files in {directory}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def delete_file(
        self, relative_path: str, subdir: DirectoryType | None = None
    ) -> bool:
        """
        删除文件或目录

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型

        Returns:
            True 如果删除成功，False 如果文件不存在

        Raises:
            PathValidationError: 路径无效
            FileOperationError: 删除失败

        Examples:
            >>> await workspace.delete_file("temp.txt")
            >>> await workspace.delete_file("old_dir", DirectoryType.TEMP)
        """
        abs_path = self.resolve_path(relative_path, subdir)

        if not abs_path.exists():
            return False

        try:
            if abs_path.is_dir():
                shutil.rmtree(abs_path)
            else:
                abs_path.unlink()

            # 使缓存失效
            self._invalidate_cache()

            logger.debug(f"Deleted {relative_path} for {self.wallet_address}")
            return True

        except OSError as e:
            error_msg = f"Failed to delete {relative_path}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def exists(
        self, relative_path: str, subdir: DirectoryType | None = None
    ) -> bool:
        """
        检查文件是否存在

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型

        Returns:
            True 如果文件存在，否则 False

        Examples:
            >>> if await workspace.exists("hello.txt"):
            ...     content = await workspace.read_file("hello.txt")
        """
        try:
            abs_path = self.resolve_path(relative_path, subdir)
            return abs_path.exists()
        except PathValidationError:
            return False

    async def create_directory(
        self, relative_path: str, subdir: DirectoryType | None = None
    ) -> Path:
        """
        创建目录

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型

        Returns:
            目录路径

        Raises:
            PathValidationError: 路径无效
            FileOperationError: 创建失败

        Examples:
            >>> await workspace.create_directory("subdir/nested")
        """
        abs_path = self.resolve_path(relative_path, subdir)

        try:
            abs_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory {relative_path} for {self.wallet_address}")
            return abs_path
        except OSError as e:
            error_msg = f"Failed to create directory {relative_path}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def get_file_info(
        self, relative_path: str, subdir: DirectoryType | None = None
    ) -> FileInfo | None:
        """
        获取文件信息

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型

        Returns:
            文件信息，如果文件不存在则返回 None

        Examples:
            >>> info = await workspace.get_file_info("hello.txt")
            >>> if info:
            ...     print(f"Size: {info.size} bytes")
        """
        try:
            abs_path = self.resolve_path(relative_path, subdir)
            if not abs_path.exists():
                return None
            return FileInfo.from_path(abs_path, self.workspace_root)
        except PathValidationError:
            return None

    async def move_file(
        self,
        src_path: str,
        dst_path: str,
        src_subdir: DirectoryType | None = None,
        dst_subdir: DirectoryType | None = None,
    ) -> Path:
        """
        移动文件

        Args:
            src_path: 源相对路径
            dst_path: 目标相对路径
            src_subdir: 源子目录类型
            dst_subdir: 目标子目录类型

        Returns:
            新的文件路径

        Raises:
            PathValidationError: 路径无效
            FileOperationError: 移动失败

        Examples:
            >>> await workspace.move_file("temp/data.txt", "output/data.txt")
        """
        src_abs = self.resolve_path(src_path, src_subdir)
        dst_abs = self.resolve_path(dst_path, dst_subdir)

        if not src_abs.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")

        try:
            shutil.move(str(src_abs), str(dst_abs))
            self._invalidate_cache()
            logger.debug(
                f"Moved {src_path} to {dst_path} for {self.wallet_address}"
            )
            return dst_abs
        except OSError as e:
            error_msg = f"Failed to move {src_path} to {dst_path}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def copy_file(
        self,
        src_path: str,
        dst_path: str,
        src_subdir: DirectoryType | None = None,
        dst_subdir: DirectoryType | None = None,
    ) -> Path:
        """
        复制文件

        Args:
            src_path: 源相对路径
            dst_path: 目标相对路径
            src_subdir: 源子目录类型
            dst_subdir: 目标子目录类型

        Returns:
            新的文件路径

        Raises:
            PathValidationError: 路径无效
            FileOperationError: 复制失败

        Examples:
            >>> await workspace.copy_file("output/data.txt", "uploads/data_backup.txt")
        """
        src_abs = self.resolve_path(src_path, src_subdir)
        dst_abs = self.resolve_path(dst_path, dst_subdir)

        if not src_abs.exists():
            raise FileNotFoundError(f"Source file not found: {src_path}")

        try:
            dst_abs.parent.mkdir(parents=True, exist_ok=True)

            if src_abs.is_dir():
                shutil.copytree(src_abs, dst_abs)
            else:
                shutil.copy2(src_abs, dst_abs)

            await self._check_quota(dst_abs.stat().st_size)
            self._invalidate_cache()

            logger.debug(
                f"Copied {src_path} to {dst_path} for {self.wallet_address}"
            )
            return dst_abs
        except OSError as e:
            error_msg = f"Failed to copy {src_path} to {dst_path}: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def cleanup_temp(self, max_age_seconds: int | None = None) -> int:
        """
        清理临时文件

        删除超过指定时间的临时文件。

        Args:
            max_age_seconds: 最大年龄（秒），None 则使用配置中的 TTL

        Returns:
            删除的文件数量

        Examples:
            >>> deleted_count = await workspace.cleanup_temp()
            >>> print(f"Deleted {deleted_count} temporary files")
        """
        max_age = max_age_seconds or self.config.temp_file_ttl_seconds
        cutoff_time = time.time() - max_age

        deleted_count = 0

        try:
            for path in self.temp_dir.rglob("*"):
                if path.is_file():
                    stat = path.stat()
                    if stat.st_mtime < cutoff_time:
                        path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted temp file: {path.name}")

            # 清理空目录
            for dir_path in sorted(self.temp_dir.rglob("*"), reverse=True):
                if dir_path.is_dir():
                    try:
                        dir_path.rmdir()
                    except OSError:
                        # 非空目录，跳过
                        pass

            self._invalidate_cache()

            logger.info(
                f"Cleaned up {deleted_count} temp files for {self.wallet_address}"
            )

            return deleted_count

        except OSError as e:
            error_msg = f"Failed to cleanup temp files: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def get_storage_used(self) -> int:
        """
        获取已使用的存储空间（字节）

        Returns:
            已使用的字节数

        Examples:
            >>> used_bytes = await workspace.get_storage_used()
            >>> used_mb = used_bytes / (1024 * 1024)
        """
        current_time = time.time()

        # 检查缓存
        if (
            self._storage_used_cache is not None
            and self._cache_timestamp is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            return self._storage_used_cache

        try:
            total_size = 0
            for path in self.workspace_root.rglob("*"):
                if path.is_file():
                    total_size += path.stat().st_size

            self._storage_used_cache = total_size
            self._cache_timestamp = current_time

            return total_size

        except OSError as e:
            error_msg = f"Failed to calculate storage used: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def get_file_count(self) -> int:
        """
        获取文件数量

        Returns:
            文件数量

        Examples:
            >>> count = await workspace.get_file_count()
            >>> print(f"Total files: {count}")
        """
        current_time = time.time()

        # 检查缓存
        if (
            self._file_count_cache is not None
            and self._cache_timestamp is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            return self._file_count_cache

        try:
            count = 0
            for path in self.workspace_root.rglob("*"):
                if path.is_file():
                    count += 1

            self._file_count_cache = count
            self._cache_timestamp = current_time

            return count

        except OSError as e:
            error_msg = f"Failed to calculate file count: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def get_quota_info(self) -> dict[str, Any]:
        """
        获取配额使用情况

        Returns:
            包含配额信息的字典

        Examples:
            >>> quota = await workspace.get_quota_info()
            >>> print(f"Storage: {quota['storage_used_mb']} / {quota['storage_limit_mb']} MB")
        """
        storage_used = await self.get_storage_used()
        file_count = await self.get_file_count()

        return {
            "wallet_address": self.wallet_address,
            "storage": {
                "used_bytes": storage_used,
                "used_mb": storage_used / (1024 * 1024),
                "limit_bytes": self.config.max_storage_bytes,
                "limit_mb": self.config.max_storage_mb,
                "used_percent": (storage_used / self.config.max_storage_bytes) * 100,
                "remaining_bytes": self.config.max_storage_bytes - storage_used,
                "remaining_mb": (
                    self.config.max_storage_bytes - storage_used
                ) / (1024 * 1024),
            },
            "files": {
                "count": file_count,
                "limit": self.config.max_files,
                "used_percent": (file_count / self.config.max_files) * 100,
                "remaining": self.config.max_files - file_count,
            },
            "file_size_limit": {
                "max_bytes": self.config.max_file_size_bytes,
                "max_mb": self.config.max_file_size_mb,
            },
        }

    async def clear_subdir(
        self, subdir: DirectoryType, max_age_seconds: int | None = None
    ) -> int:
        """
        清空指定子目录

        Args:
            subdir: 子目录类型
            max_age_seconds: 可选的最大年龄，None 则清空全部

        Returns:
            删除的文件数量

        Examples:
            >>> await workspace.clear_subdir(DirectoryType.TEMP)
        """
        dir_path = self._subdirs[subdir]

        if not dir_path.exists():
            return 0

        deleted_count = 0
        cutoff_time = time.time() - max_age_seconds if max_age_seconds else 0

        try:
            if max_age_seconds:
                # 只删除旧文件
                for path in dir_path.rglob("*"):
                    if path.is_file() and path.stat().st_mtime < cutoff_time:
                        path.unlink()
                        deleted_count += 1
            else:
                # 清空整个目录
                shutil.rmtree(dir_path)
                dir_path.mkdir(parents=True, exist_ok=True)
                (dir_path / ".gitkeep").touch()
                deleted_count = -1  # 表示全部清空

            self._invalidate_cache()

            logger.info(
                f"Cleared {subdir.value} directory for {self.wallet_address}, "
                f"deleted: {deleted_count}"
            )

            return deleted_count

        except OSError as e:
            error_msg = f"Failed to clear {subdir.value} directory: {e}"
            logger.error(error_msg)
            raise FileOperationError(error_msg) from e

    async def get_stats(self) -> dict[str, Any]:
        """
        获取工作空间统计信息

        Returns:
            包含统计信息的字典

        Examples:
            >>> stats = await workspace.get_stats()
            >>> print(f"Total files: {stats['total_files']}")
        """
        storage_used = await self.get_storage_used()
        file_count = await self.get_file_count()

        # 统计各子目录的文件数
        dir_stats = {}
        for dir_type, dir_path in self._subdirs.items():
            if dir_path.exists():
                dir_file_count = sum(1 for _ in dir_path.rglob("*") if _.is_file())
                dir_stats[dir_type.value] = dir_file_count
            else:
                dir_stats[dir_type.value] = 0

        return {
            "wallet_address": self.wallet_address,
            "workspace_root": str(self.workspace_root),
            "storage_used_bytes": storage_used,
            "storage_used_mb": storage_used / (1024 * 1024),
            "total_files": file_count,
            "directories": dir_stats,
            "max_file_size_mb": self.config.max_file_size_mb,
            "max_storage_mb": self.config.max_storage_mb,
        }

    def get_path(self, relative_path: str, subdir: DirectoryType | None = None) -> str:
        """
        获取文件/目录的绝对路径（字符串形式）

        这是 resolve_path 的简化版本，返回字符串。

        Args:
            relative_path: 相对路径
            subdir: 可选的子目录类型

        Returns:
            绝对路径字符串

        Examples:
            >>> path = workspace.get_path("test.txt")
            >>> print(f"File location: {path}")
        """
        return str(self.resolve_path(relative_path, subdir))

    def is_within_workspace(self, path: str | Path) -> bool:
        """
        检查给定路径是否在工作空间内

        Args:
            path: 要检查的路径

        Returns:
            True 如果路径在工作空间内

        Examples:
            >>> if workspace.is_within_workspace("/some/path"):
            ...     print("Path is safe")
        """
        if isinstance(path, str):
            path = Path(path)
        return self.validate_path(path)


# 便利函数


async def create_workspace(
    wallet_address: str,
    workspace_root: str | None = None,
    **kwargs,
) -> UserWorkspace:
    """
    创建并初始化用户工作空间

    Args:
        wallet_address: 用户钱包地址
        workspace_root: 可选的工作空间根目录
        **kwargs: 其他 WorkspaceConfig 参数

    Returns:
        初始化完成的工作空间实例

    Examples:
        >>> workspace = await create_workspace("0x1234...")
        >>> await workspace.write_file("test.txt", "Hello")
    """
    config = WorkspaceConfig(workspace_root=workspace_root, **kwargs)
    workspace = UserWorkspace(wallet_address, config)
    await workspace.init()
    return workspace
