"""
本地系统操作工具（支持 UserSession）

提供文件操作、命令执行、目录管理等本地系统能力。
文件操作现在支持用户工作空间隔离。
"""

import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..session.user_session import UserSession


def _get_path(params: dict) -> str:
    """统一获取路径参数

    支持两种参数名：path 和 file_path
    LLM 有时用 file_path，有时用 path，统一处理

    Args:
        params: 工具参数字典

    Returns:
        路径字符串，如果都没有则返回空字符串
    """
    return params.get("path") or params.get("file_path") or ""


if TYPE_CHECKING:
    from ..session.user_session import UserSession

from .registry import Tool
from .security import (
    SecurityLevel,
    check_command_whitelist,
    check_path_safety,
)

logger = logging.getLogger(__name__)


def get_system_tools() -> list[Tool]:
    """获取系统工具列表"""
    return [
        Tool(
            name="execute_command",
            description="执行命令行命令。用于运行终端命令、脚本等。",
            handler=execute_command,
            security_level=SecurityLevel.HIGH,
            requires_session=False,
            parameters={
                "command": {"type": "string", "description": "要执行的命令行命令"},
                "cwd": {"type": "string", "description": "工作目录路径"},
                "timeout": {"type": "integer", "description": "超时时间（秒）"},
            },
        ),
        Tool(
            name="run_program",
            description="运行程序或脚本文件",
            handler=run_program,
            security_level=SecurityLevel.HIGH,
            requires_session=False,
            parameters={
                "program_path": {"type": "string", "description": "程序或脚本的路径"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "命令行参数"},
                "cwd": {"type": "string", "description": "工作目录"},
                "timeout": {"type": "integer", "description": "超时时间"},
            },
        ),
        Tool(
            name="read_file",
            description="读取文件内容（支持用户工作空间隔离）",
            handler=read_file,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
            parameters={
                "path": {"type": "string", "description": "要读取的文件路径"},
                "offset": {"type": "integer", "description": "起始位置"},
                "limit": {"type": "integer", "description": "读取字节数"},
                "encoding": {"type": "string", "description": "文件编码"},
            },
        ),
        Tool(
            name="write_file",
            description="写入或创建文件（支持用户工作空间隔离）",
            handler=write_file,
            security_level=SecurityLevel.HIGH,
            requires_session=True,
            parameters={
                "path": {"type": "string", "description": "要写入的文件路径"},
                "content": {"type": "string", "description": "文件内容"},
                "mode": {"type": "string", "description": "写入模式 (w/a)"},
            },
        ),
        Tool(
            name="list_directory",
            description="列出目录内容（支持用户工作空间隔离）",
            handler=list_directory,
            security_level=SecurityLevel.LOW,
            requires_session=True,
            parameters={
                "path": {"type": "string", "description": "目录路径，默认为用户工作空间根目录"},
                "show_hidden": {"type": "boolean", "description": "是否显示隐藏文件"},
                "recursive": {"type": "boolean", "description": "是否递归列出子目录"},
            },
        ),
        Tool(
            name="create_directory",
            description="创建目录（支持用户工作空间隔离）",
            handler=create_directory,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
            parameters={
                "path": {"type": "string", "description": "要创建的目录路径"},
            },
        ),
        Tool(
            name="delete_file",
            description="删除文件或目录（支持用户工作空间隔离）",
            handler=delete_file,
            security_level=SecurityLevel.HIGH,
            requires_session=True,
            parameters={
                "path": {"type": "string", "description": "要删除的文件或目录路径"},
                "recursive": {"type": "boolean", "description": "是否递归删除"},
            },
        ),
        Tool(
            name="search_files",
            description="搜索文件（支持用户工作空间隔离）",
            handler=search_files,
            security_level=SecurityLevel.LOW,
            requires_session=True,
        ),
        Tool(
            name="get_file_info",
            description="获取文件信息（支持用户工作空间隔离）",
            handler=get_file_info,
            security_level=SecurityLevel.LOW,
            requires_session=True,
        ),
        Tool(
            name="copy_file",
            description="复制文件或目录（支持用户工作空间隔离）",
            handler=copy_file,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
        ),
        Tool(
            name="move_file",
            description="移动或重命名文件（支持用户工作空间隔离）",
            handler=move_file,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
        ),
    ]


async def register_tools(registry):
    """注册系统工具"""
    for tool in get_system_tools():
        registry.register(tool)


async def execute_command(params: dict) -> dict[str, Any]:
    """
    执行命令行命令（全局版本，不需要用户会话）

    Args:
        params: 参数字典，包含:
            - command: 要执行的命令
            - cwd: 工作目录
            - timeout: 超时时间（秒）
            - env: 环境变量
            - user_confirmed: 用户是否已确认

    Returns:
        执行结果
    """
    command = params.get("command", "")
    cwd = params.get("cwd")
    timeout = params.get("timeout", 30)
    env = params.get("env")
    user_confirmed = params.get("user_confirmed", False)

    # 安全检查
    security_check = check_command_whitelist(command)
    if not security_check["allowed"]:
        return {
            "status": "blocked",
            "reason": security_check["reason"],
            "blocked": True,
        }

    if security_check["sensitive"] and not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "execute_command",
            "command": command,
            "warning": "这是一个敏感操作，需要用户确认",
        }

    try:
        # 设置工作目录
        if cwd:
            if not check_path_safety(cwd):
                return {"status": "error", "message": "路径不安全"}
        else:
            cwd = os.getcwd()

        # 执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env or {},
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            return {
                "status": "timeout",
                "message": f"命令执行超时（{timeout}秒）",
            }

        return {
            "status": "success",
            "command": command,
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
        }

    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def run_program(params: dict) -> dict[str, Any]:
    """
    运行程序或脚本（全局版本，不需要用户会话）

    Args:
        params: 参数字典，包含:
            - program_path: 程序路径
            - args: 命令行参数
            - cwd: 工作目录
            - timeout: 超时时间
            - user_confirmed: 用户确认
    """
    program_path = params.get("program_path", "")
    args = params.get("args")
    cwd = params.get("cwd")
    timeout = params.get("timeout", 60)
    user_confirmed = params.get("user_confirmed", False)

    # 安全检查
    if not check_path_safety(program_path):
        return {"status": "error", "message": "路径不安全"}

    # 检查文件是否存在
    if not os.path.exists(program_path):
        return {"status": "error", "message": f"文件不存在: {program_path}"}

    # 构建命令
    cmd = [program_path]
    if args:
        cmd.extend(args)

    command = " ".join(cmd)

    # 检查是否敏感
    sensitive_check = check_command_whitelist(command)
    if sensitive_check["sensitive"] and not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "run_program",
            "program": program_path,
            "args": args,
        }

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd or os.path.dirname(program_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            return {"status": "timeout", "message": "程序执行超时"}

        return {
            "status": "success",
            "program": program_path,
            "args": args,
            "returncode": process.returncode,
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def read_file(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    读取文件内容（用户工作空间隔离版本）

    在用户的工作空间中读取文件，确保：
    1. 只能访问用户工作空间内的文件
    2. 路径自动解析为工作空间相对路径

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 文件相对路径（相对于用户工作空间）
            - offset: 起始位置
            - limit: 读取字节数
            - encoding: 文件编码

    Returns:
        读取结果
    """
    path = _get_path(params)
    offset = params.get("offset", 0)
    limit = params.get("limit", 10000)
    params.get("encoding", "utf-8")

    try:
        # 使用用户工作空间读取文件
        content = await session.workspace.read_file(path, as_text=True)

        # 处理 offset 和 limit
        if offset > 0:
            content = content[offset:]
        if limit:
            content = content[:limit]

        return {
            "status": "success",
            "path": path,
            "content": content,
            "size": len(content),
            "offset": offset,
            "read": len(content),
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"文件不存在: {path}",
        }
    except Exception as e:
        logger.error(f"File read failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def write_file(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    写入文件（用户工作空间隔离版本）

    在用户的工作空间中写入文件，确保：
    1. 只能写入用户工作空间内的文件
    2. 路径自动解析为工作空间相对路径

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 文件相对路径（相对于用户工作空间）
            - content: 文件内容
            - mode: 写入模式 (w/a)
            - user_confirmed: 用户确认（用于覆盖确认）

    Returns:
        写入结果
    """
    path = _get_path(params)
    content = params.get("content", "")
    params.get("mode", "w")
    user_confirmed = params.get("user_confirmed", False)

    try:
        # 检查文件是否已存在
        workspace = session.workspace
        if await workspace.exists(path) and not user_confirmed:
            return {
                "status": "requires_confirmation",
                "operation": "write_file",
                "path": path,
                "warning": "文件已存在，将被覆盖",
            }

        # 使用用户工作空间写入文件
        await workspace.write_file(path, content)

        return {
            "status": "success",
            "path": path,
            "bytes_written": len(content),
        }

    except Exception as e:
        logger.error(f"File write failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def list_directory(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    列出目录内容（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 目录相对路径（相对于用户工作空间），默认为根目录
            - show_hidden: 是否显示隐藏文件
            - recursive: 是否递归列出

    Returns:
        目录内容
    """
    path = _get_path(params)
    show_hidden = params.get("show_hidden", False)
    recursive = params.get("recursive", False)
    pattern = params.get("pattern", "*")

    try:
        # 使用用户工作空间列出文件
        files = await session.workspace.list_files(
            directory=path, pattern=pattern, recursive=recursive
        )

        # 过滤隐藏文件
        if not show_hidden:
            files = [f for f in files if not f.name.startswith(".")]

        return {
            "status": "success",
            "path": path,
            "files": [f.to_dict() for f in files],
            "count": len(files),
        }

    except Exception as e:
        logger.error(f"Directory listing failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def create_directory(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    创建目录（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 目录相对路径（相对于用户工作空间）
            - parents: 是否创建父目录，默认 True

    Returns:
        创建结果
    """
    path = _get_path(params)
    params.get("parents", True)

    try:
        # 使用用户工作空间创建目录
        await session.workspace.create_directory(path)

        return {
            "status": "success",
            "path": path,
        }

    except Exception as e:
        logger.error(f"Directory creation failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def delete_file(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    删除文件或目录（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 文件相对路径（相对于用户工作空间）
            - user_confirmed: 用户确认

    Returns:
        删除结果
    """
    path = _get_path(params)
    user_confirmed = params.get("user_confirmed", False)

    if not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "delete_file",
            "path": path,
            "warning": f"即将删除: {path}",
        }

    try:
        # 使用用户工作空间删除文件
        deleted = await session.workspace.delete_file(path)

        return {
            "status": "success",
            "path": path,
            "deleted": deleted,
        }

    except Exception as e:
        logger.error(f"File deletion failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def search_files(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    搜索文件（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 搜索目录相对路径，默认为根目录
            - pattern: 文件匹配模式（如 *.py）
            - max_results: 最大结果数量
            - recursive: 是否递归搜索

    Returns:
        搜索结果
    """
    path = _get_path(params)
    pattern = params.get("pattern", "*")
    max_results = params.get("max_results", 100)
    recursive = params.get("recursive", True)

    try:
        # 使用用户工作空间搜索文件
        files = await session.workspace.list_files(
            directory=path, pattern=pattern, recursive=recursive
        )

        # 限制结果数量
        files = files[:max_results]

        return {
            "status": "success",
            "path": path,
            "pattern": pattern,
            "results": [f.to_dict() for f in files],
            "count": len(files),
        }

    except Exception as e:
        logger.error(f"File search failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def get_file_info(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    获取文件信息（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 文件相对路径（相对于用户工作空间）

    Returns:
        文件信息
    """
    path = _get_path(params)

    try:
        # 使用用户工作空间获取文件信息
        info = await session.workspace.get_file_info(path)

        if info is None:
            return {
                "status": "error",
                "message": f"文件不存在: {path}",
            }

        return {
            "status": "success",
            "path": path,
            "info": info.to_dict(),
        }

    except Exception as e:
        logger.error(f"File info retrieval failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def copy_file(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    复制文件或目录（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - source: 源文件相对路径
            - destination: 目标文件相对路径
            - user_confirmed: 用户确认

    Returns:
        复制结果
    """
    source = params.get("source", "")
    destination = params.get("destination", "")
    params.get("user_confirmed", False)

    try:
        # 使用用户工作空间复制文件
        await session.workspace.copy_file(source, destination)

        return {
            "status": "success",
            "source": source,
            "destination": destination,
        }

    except Exception as e:
        logger.error(f"File copy failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }


async def move_file(session: "UserSession", params: dict) -> dict[str, Any]:
    """
    移动或重命名文件（用户工作空间隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - source: 源文件相对路径
            - destination: 目标文件相对路径
            - user_confirmed: 用户确认

    Returns:
        移动结果
    """
    source = params.get("source", "")
    destination = params.get("destination", "")
    params.get("user_confirmed", False)

    try:
        # 使用用户工作空间移动文件
        await session.workspace.move_file(source, destination)

        return {
            "status": "success",
            "source": source,
            "destination": destination,
        }

    except Exception as e:
        logger.error(f"File move failed: {e}")
        return {
            "status": "error",
            "message": str(e),
        }
