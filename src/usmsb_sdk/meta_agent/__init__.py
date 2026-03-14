"""
Meta Agent Module - 多用户隔离架构

提供用户会话隔离、文件系统隔离、代码沙箱、浏览器上下文等功能。
"""

__version__ = "1.0.0"
__author__ = "USMSB Team"

# Workspace module
from usmsb_sdk.meta_agent.workspace import (
    DirectoryType,
    FileInfo,
    FileOperationError,
    PathValidationError,
    QuotaExceededError,
    UserWorkspace,
    WorkspaceConfig,
    WorkspaceError,
    create_workspace,
)

__all__ = [
    # Workspace
    "DirectoryType",
    "FileOperationError",
    "FileInfo",
    "UserWorkspace",
    "WorkspaceConfig",
    "WorkspaceError",
    "PathValidationError",
    "QuotaExceededError",
    "create_workspace",
]
