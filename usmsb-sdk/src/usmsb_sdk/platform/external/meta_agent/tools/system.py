"""
本地系统操作工具

提供文件操作、命令执行、目录管理等本地系统能力
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from .registry import Tool
from .security import (
    check_command_whitelist,
    check_path_safety,
    SecurityLevel,
)

logger = logging.getLogger(__name__)


def get_system_tools() -> List[Tool]:
    """获取系统工具列表"""
    return [
        Tool(
            name="execute_command",
            description="执行命令行命令。用于运行终端命令、脚本等。",
            handler=execute_command,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="run_program",
            description="运行程序或脚本文件",
            handler=run_program,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="read_file",
            description="读取文件内容",
            handler=read_file,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="write_file",
            description="写入或创建文件",
            handler=write_file,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="list_directory",
            description="列出目录内容",
            handler=list_directory,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="create_directory",
            description="创建目录",
            handler=create_directory,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="delete_file",
            description="删除文件或目录",
            handler=delete_file,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="search_files",
            description="搜索文件",
            handler=search_files,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="get_file_info",
            description="获取文件信息",
            handler=get_file_info,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="copy_file",
            description="复制文件或目录",
            handler=copy_file,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="move_file",
            description="移动或重命名文件",
            handler=move_file,
            security_level=SecurityLevel.MEDIUM,
        ),
    ]


async def register_tools(registry):
    """注册系统工具"""
    for tool in get_system_tools():
        registry.register(tool)


async def execute_command(params: dict) -> Dict[str, Any]:
    """
    执行命令行命令

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
        except asyncio.TimeoutError:
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


async def run_program(params: dict) -> Dict[str, Any]:
    """
    运行程序或脚本

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
        except asyncio.TimeoutError:
            process.kill()
            return {"status": "timeout", "message": f"程序执行超时"}

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


async def read_file(params: dict) -> Dict[str, Any]:
    """
    读取文件内容

    Args:
        params: 参数字典，包含:
            - file_path: 文件路径
            - offset: 起始位置
            - limit: 读取字节数
            - encoding: 文件编码
    """
    file_path = params.get("file_path", "")
    offset = params.get("offset", 0)
    limit = params.get("limit", 10000)
    encoding = params.get("encoding", "utf-8")
    # 安全检查
    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在"}

    if not os.path.isfile(file_path):
        return {"status": "error", "message": "不是文件"}

    try:
        with open(file_path, "r", encoding=encoding, errors="ignore") as f:
            f.seek(offset)
            content = f.read(limit)

        # 获取文件信息
        stat = os.stat(file_path)

        return {
            "status": "success",
            "file_path": file_path,
            "content": content,
            "size": stat.st_size,
            "offset": offset,
            "read": len(content),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def write_file(params: dict) -> Dict[str, Any]:
    """
    写入文件

    Args:
        params: 参数字典，包含:
            - file_path: 文件路径
            - content: 文件内容
            - mode: 写入模式 (w/a)
            - encoding: 编码
            - user_confirmed: 用户确认
    """
    file_path = params.get("file_path", "")
    content = params.get("content", "")
    mode = params.get("mode", "w")
    encoding = params.get("encoding", "utf-8")
    user_confirmed = params.get("user_confirmed", False)
    # 安全检查
    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}

    # 检查目录是否存在
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            return {"status": "error", "message": f"无法创建目录: {e}"}

    # 检查文件是否已存在
    if os.path.exists(file_path) and not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "write_file",
            "file_path": file_path,
            "warning": "文件已存在，将被覆盖",
        }

    try:
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)

        return {
            "status": "success",
            "file_path": file_path,
            "bytes_written": len(content.encode(encoding)),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def list_directory(params: dict) -> Dict[str, Any]:
    """列出目录内容"""
    directory_path = params.get("directory_path", ".")
    show_hidden = params.get("show_hidden", False)

    if not check_path_safety(directory_path):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(directory_path):
        return {"status": "error", "message": "目录不存在"}

    if not os.path.isdir(directory_path):
        return {"status": "error", "message": "不是目录"}

    try:
        items = []
        for item in os.listdir(directory_path):
            if not show_hidden and item.startswith("."):
                continue

            item_path = os.path.join(directory_path, item)
            stat = os.stat(item_path)

            items.append(
                {
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )

        return {
            "status": "success",
            "directory": directory_path,
            "items": items,
            "count": len(items),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def create_directory(params: dict) -> Dict[str, Any]:
    """创建目录"""
    directory_path = params.get("directory_path", "")
    parents = params.get("parents", True)

    if not check_path_safety(directory_path):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(directory_path):
        return {"status": "error", "message": "路径不安全"}

    try:
        os.makedirs(directory_path, exist_ok=parents)
        return {
            "status": "success",
            "directory": directory_path,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def delete_file(params: dict) -> Dict[str, Any]:
    """删除文件或目录"""
    file_path = params.get("file_path", "")
    recursive = params.get("recursive", False)
    user_confirmed = params.get("user_confirmed", False)

    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(file_path):
        return {"status": "error", "message": "路径不存在"}

    # 敏感操作确认
    if not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "delete_file",
            "file_path": file_path,
            "warning": f"即将删除: {file_path}",
        }

    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif recursive:
            shutil.rmtree(file_path)
        else:
            os.rmdir(file_path)

        return {
            "status": "success",
            "file_path": file_path,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def search_files(params: dict) -> Dict[str, Any]:
    """搜索文件"""
    directory = params.get("directory", ".")
    pattern = params.get("pattern", "*")
    file_type = params.get("file_type")
    max_results = params.get("max_results", 100)

    if not check_path_safety(directory):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(directory):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(directory):
        return {"status": "error", "message": "目录不存在"}

    try:
        results = []
        path = Path(directory)

        # 构建搜索模式
        glob_pattern = pattern
        if file_type == "file":
            glob_pattern = f"{pattern}*"
        elif file_type == "directory":
            glob_pattern = f"{pattern}*/"

        for item in path.rglob(glob_pattern):
            if len(results) >= max_results:
                break

            if not show_hidden and item.name.startswith("."):
                continue

            rel_path = item.relative_to(directory)
            results.append(
                {
                    "path": str(item),
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }
            )

        return {
            "status": "success",
            "directory": directory,
            "pattern": pattern,
            "results": results,
            "count": len(results),
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_file_info(params: dict) -> Dict[str, Any]:
    """获取文件信息"""
    file_path = params.get("file_path", "")

    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(file_path):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(file_path):
        return {"status": "error", "message": "文件不存在"}

    try:
        stat = os.stat(file_path)

        return {
            "status": "success",
            "file_path": file_path,
            "name": os.path.basename(file_path),
            "type": "directory" if os.path.isdir(file_path) else "file",
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def copy_file(params: dict) -> Dict[str, Any]:
    """复制文件或目录"""
    source = params.get("source", "")
    destination = params.get("destination", "")
    user_confirmed = params.get("user_confirmed", False)

    if not check_path_safety(source) or not check_path_safety(destination):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(source) or not check_path_safety(destination):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(source):
        return {"status": "error", "message": "源文件不存在"}

    if os.path.exists(destination) and not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "copy_file",
            "source": source,
            "destination": destination,
        }

    try:
        if os.path.isdir(source):
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

        return {
            "status": "success",
            "source": source,
            "destination": destination,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def move_file(params: dict) -> Dict[str, Any]:
    """移动或重命名文件"""
    source = params.get("source", "")
    destination = params.get("destination", "")
    user_confirmed = params.get("user_confirmed", False)

    if not check_path_safety(source) or not check_path_safety(destination):
        return {"status": "error", "message": "路径不安全"}
    if not check_path_safety(source) or not check_path_safety(destination):
        return {"status": "error", "message": "路径不安全"}

    if not os.path.exists(source):
        return {"status": "error", "message": "源文件不存在"}

    if os.path.exists(destination) and not user_confirmed:
        return {
            "status": "requires_confirmation",
            "operation": "move_file",
            "source": source,
            "destination": destination,
        }

    try:
        shutil.move(source, destination)
        return {
            "status": "success",
            "source": source,
            "destination": destination,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def show_hidden(item: str) -> bool:
    """检查是否显示隐藏文件（辅助函数）"""
    return not item.startswith(".")
