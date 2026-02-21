"""
UserWorkspace - 用户工作空间

管理用户专属的文件系统空间，包括：
- 所有文件操作限制在用户目录内
- 提供安全路径验证
- 支持文件上传下载
"""

from typing import Union, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    size: int
    is_dir: bool
    modified_time: float


class UserWorkspace:
    """
    用户工作空间

    管理用户专属的文件系统空间：
    1. 所有文件操作限制在用户目录内
    2. 提供安全路径验证
    3. 支持文件上传下载
    """

    # ========== 属性 ==========

    wallet_address: str
    workspace_root: Path                 # 工作空间根目录

    # 目录
    temp_dir: Path                       # 临时文件
    output_dir: Path                     # 输出文件
    uploads_dir: Path                    # 上传文件

    # ========== 核心方法 ==========

    def resolve_path(self, relative_path: str) -> Path:
        """
        解析相对路径为绝对路径（限制在工作空间内）
        """
        pass

    def validate_path(self, path: Path) -> bool:
        """
        验证路径是否在工作空间内
        """
        pass

    async def write_file(
        self,
        relative_path: str,
        content: Union[str, bytes]
    ) -> Path:
        """
        写入文件
        """
        pass

    async def read_file(self, relative_path: str) -> bytes:
        """
        读取文件
        """
        pass

    async def list_files(
        self,
        directory: str = "",
        pattern: str = "*"
    ) -> List[FileInfo]:
        """
        列出文件
        """
        pass

    async def delete_file(self, relative_path: str) -> bool:
        """
        删除文件
        """
        pass

    async def cleanup_temp(self) -> int:
        """
        清理临时文件
        """
        pass
