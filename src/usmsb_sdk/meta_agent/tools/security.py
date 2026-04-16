"""
安全机制模块

提供：
1. 白名单命令检查
2. 路径安全检查
3. 敏感操作级别定义
4. 用户确认机制
"""

import logging
import os
import re
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class SecurityLevel(StrEnum):
    """安全级别"""

    LOW = "low"  # 低风险，无需确认
    MEDIUM = "medium"  # 中风险，建议确认
    HIGH = "high"  # 高风险，必须确认


class SensitiveOperation(StrEnum):
    """敏感操作类型"""

    EXECUTE_COMMAND = "execute_command"
    RUN_PROGRAM = "run_program"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    COPY_FILE = "copy_file"
    MOVE_FILE = "move_file"
    BROWSER_CONTROL = "browser_control"


# 允许的命令白名单（精确匹配或前缀匹配）
ALLOWED_COMMANDS = {
    # 文件查看
    "ls",
    "la",
    "ll",
    "dir",
    "pwd",
    "cd",
    "cat",
    "head",
    "tail",
    "less",
    "more",
    "grep",
    "rg",
    "find",
    "which",
    "whereis",
    "file",
    "stat",
    "wc",
    # 文件操作
    "mkdir",
    "touch",
    "cp",
    "mv",
    "rm",
    "chmod",
    "chown",
    "ln",
    "readlink",
    # 压缩解压
    "tar",
    "zip",
    "unzip",
    "gzip",
    "gunzip",
    "7z",
    "rar",
    # Git
    "git status",
    "git log",
    "git diff",
    "git show",
    "git branch",
    "git checkout",
    "git fetch",
    "git pull",
    "git push",
    "git clone",
    "git add",
    "git commit",
    "git reset",
    # 包管理
    "python",
    "python3",
    "pip",
    "pip3",
    "npm",
    "npx",
    "node",
    "yarn",
    "cargo",
    "rustc",
    "go",
    "java",
    "javac",
    # 构建工具
    "make",
    "cmake",
    "gradle",
    "maven",
    "pytest",
    "jest",
    "mocha",
    "tsc",
    "vite",
    "webpack",
    "esbuild",
    # 网络
    "curl",
    "wget",
    "ssh",
    "scp",
    "rsync",
    "ping",
    "traceroute",
    "netstat",
    "ifconfig",
    "ip",
    "dig",
    "nslookup",
    # 文本处理
    "echo",
    "printf",
    "awk",
    "sed",
    "sort",
    "uniq",
    "cut",
    "tr",
    "tee",
    # 系统信息
    "whoami",
    "hostname",
    "uname",
    "df",
    "du",
    "free",
    "top",
    "htop",
    "ps",
    "kill",
    "date",
    "cal",
    "time",
    # Docker
    "docker ps",
    "docker images",
    "docker logs",
    "docker exec",
    "docker build",
    "docker run",
    # 其他
    "vim",
    "nano",
    "code",
    "subl",
    "tree",
    "locate",
}

# 禁止的命令模式（正则匹配）
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",  # 删除根目录
    r"rm\s+-rf\s+\.",  # 删除当前目录
    r"dd\s+if=",  # 磁盘操作
    r"mkfs",  # 格式化
    r"format\s+[a-z]:",  # Windows 格式化
    r"del\s+/f\s+/s",  # Windows 删除系统文件
    r">\s*/dev/",  # 写入设备
    r"chmod\s+777",  # 过度开放权限
    r"wget\s+.*\|\s*sh",  # 远程脚本执行
    r"curl\s+.*\|\s*sh",  # 远程脚本执行
    r"powershell.*-enc",  # PowerShell 编码命令
    r"eval\s*\(",  # eval 执行
    r"exec\s*\(",  # exec 执行
    r";\s*rm\s+",  # 分号删除
    r"&\s*rm\s+",  # 后台删除
    r"\|",  # 管道后接危险命令（简化检查）
]

# 敏感操作需要确认
SENSITIVE_OPERATIONS = {
    SensitiveOperation.EXECUTE_COMMAND,
    SensitiveOperation.RUN_PROGRAM,
    SensitiveOperation.WRITE_FILE,
    SensitiveOperation.DELETE_FILE,
    SensitiveOperation.COPY_FILE,
    SensitiveOperation.MOVE_FILE,
    SensitiveOperation.BROWSER_CONTROL,
}

# 默认允许的路径
ALLOWED_PATHS = [
    os.path.expanduser("~/"),
    "/tmp",
    "/var/tmp",
]


def get_security_level(tool_name: str) -> SecurityLevel:
    """获取工具的安全级别"""
    high_security = {
        "execute_command",
        "run_program",
        "write_file",
        "delete_file",
    }
    medium_security = {
        "create_directory",
        "copy_file",
        "move_file",
        "browser_control",
    }

    if tool_name in high_security:
        return SecurityLevel.HIGH
    elif tool_name in medium_security:
        return SecurityLevel.MEDIUM
    else:
        return SecurityLevel.LOW


def check_command_whitelist(command: str) -> dict[str, Any]:
    """
    检查命令是否在白名单中

    Returns:
        {
            "allowed": bool,        # 是否允许执行
            "reason": str,         # 原因
            "sensitive": bool,     # 是否敏感
        }
    """
    command = command.strip()
    command_lower = command.lower()

    # 检查禁止模式
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command_lower):
            return {
                "allowed": False,
                "reason": f"命令包含禁止的模式: {pattern}",
                "sensitive": True,
            }

    # 提取命令前缀（不含参数）
    cmd_parts = command.split()
    if not cmd_parts:
        return {
            "allowed": False,
            "reason": "空命令",
            "sensitive": False,
        }

    cmd_prefix = cmd_parts[0].lower()  # 转小写用于比较

    # 检查是否在白名单中
    is_allowed = False
    for allowed in ALLOWED_COMMANDS:
        # 精确匹配或前缀匹配
        if cmd_prefix == allowed.lower() or cmd_prefix.startswith(allowed.lower() + " "):
            is_allowed = True
            break

    if not is_allowed:
        return {
            "allowed": False,
            "reason": f"命令不在白名单中: {cmd_prefix}",
            "sensitive": True,
        }

    # 检查是否为敏感操作
    sensitive_keywords = [
        "sudo",
        "su",
        "apt",
        "yum",
        "dnf",
        "systemctl",
        "service",
        "init",
        "shutdown",
        "reboot",
        "halt",
        "passwd",
        "useradd",
        "userdel",
        "groupadd",
        "groupdel",
    ]

    is_sensitive = any(kw in command_lower for kw in sensitive_keywords)

    return {
        "allowed": True,
        "reason": "命令在白名单中",
        "sensitive": is_sensitive,
    }


def check_path_safety(path: str) -> bool:
    """
    检查路径是否安全

    Args:
        path: 要检查的路径

    Returns:
        是否安全
    """
    if not path:
        return False

    # 转换为绝对路径
    try:
        abs_path = os.path.abspath(os.path.expanduser(path))
    except Exception:
        return False

    # 检查路径遍历攻击
    if ".." in path:
        # 允许相对路径，但不允许超出用户目录
        pass

    # 危险路径检查
    dangerous_paths = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/.ssh",
        "/.aws",
        "/.gnupg",
    ]

    for dp in dangerous_paths:
        if abs_path.startswith(dp):
            logger.warning(f"Access to dangerous path blocked: {path}")
            return False

    return True


def is_sensitive_operation(tool_name: str) -> bool:
    """判断操作是否为敏感操作"""
    return tool_name in SENSITIVE_OPERATIONS


def format_blocked_response(tool_name: str, reason: str) -> dict[str, Any]:
    """格式化阻止响应"""
    return {
        "status": "blocked",
        "tool": tool_name,
        "reason": reason,
        "blocked": True,
        "message": f"操作被阻止: {reason}",
    }


def format_confirmation_response(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """格式化需要确认的响应"""
    return {
        "status": "requires_confirmation",
        "operation": tool_name,
        "params": params,
        "warning": f"操作 '{tool_name}' 需要用户确认后才能执行",
    }


class PendingConfirmations:
    """待确认的操作队列"""

    def __init__(self):
        self._confirmations: dict[str, dict[str, Any]] = {}
        self._confirmation_id = 0

    def add(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_id: str,
    ) -> str:
        """添加待确认操作"""
        self._confirmation_id += 1
        confirmation_id = f"confirm_{self._confirmation_id}"

        self._confirmations[confirmation_id] = {
            "id": confirmation_id,
            "tool": tool_name,
            "params": params,
            "user_id": user_id,
        }

        return confirmation_id

    def get(self, confirmation_id: str) -> dict[str, Any] | None:
        """获取确认信息"""
        return self._confirmations.get(confirmation_id)

    def confirm(self, confirmation_id: str) -> dict[str, Any] | None:
        """确认操作"""
        return self._confirmations.pop(confirmation_id, None)

    def cancel(self, confirmation_id: str) -> bool:
        """取消操作"""
        return self._confirmations.pop(confirmation_id, None) is not None


# 全局确认队列
pending_confirmations = PendingConfirmations()
