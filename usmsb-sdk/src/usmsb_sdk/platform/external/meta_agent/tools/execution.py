"""
代码执行、浏览器操作和技能执行工具

支持 UserSession 上下文，每个用户拥有独立的代码执行环境和浏览器会话。
"""

import asyncio
import io
import json
import logging
import os
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from ..session.user_session import UserSession

from .registry import Tool
from .security import SecurityLevel

logger = logging.getLogger(__name__)


def get_execution_tools() -> List[Tool]:
    """获取执行工具列表（支持 UserSession）"""
    return [
        Tool(
            name="execute_python",
            description="执行 Python 代码并返回结果。支持标准库和常见第三方库。",
            handler=execute_python,
            security_level=SecurityLevel.HIGH,
            requires_session=True,  # 需要访问用户的沙箱
        ),
        Tool(
            name="execute_javascript",
            description="执行 JavaScript 代码（需要 Node.js 环境）",
            handler=execute_javascript,
            security_level=SecurityLevel.HIGH,
            requires_session=False,  # 不需要会话（可全局执行）
        ),
        Tool(
            name="browser_open",
            description="打开浏览器并访问指定 URL（使用用户隔离的浏览器上下文）",
            handler=browser_open,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,  # 需要访问用户的浏览器上下文
        ),
        Tool(
            name="browser_click",
            description="点击页面元素（通过 CSS 选择器）",
            handler=browser_click,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
        ),
        Tool(
            name="browser_fill",
            description="填写表单输入框",
            handler=browser_fill,
            security_level=SecurityLevel.MEDIUM,
            requires_session=True,
        ),
        Tool(
            name="browser_get_content",
            description="获取浏览器当前页面内容",
            handler=browser_get_content,
            security_level=SecurityLevel.LOW,
            requires_session=True,
        ),
        Tool(
            name="browser_screenshot",
            description="截取浏览器当前页面截图",
            handler=browser_screenshot,
            security_level=SecurityLevel.LOW,
            requires_session=True,
        ),
        Tool(
            name="browser_close",
            description="关闭浏览器",
            handler=browser_close,
            security_level=SecurityLevel.LOW,
            requires_session=True,
        ),
        Tool(
            name="parse_skill_md",
            description="解析 skills.md 文件并提取技能定义",
            handler=parse_skill_md,
            security_level=SecurityLevel.LOW,
            requires_session=False,
        ),
        Tool(
            name="execute_skill",
            description="执行指定名称的技能（需要先解析 skills.md）",
            handler=execute_skill,
            security_level=SecurityLevel.HIGH,
            requires_session=True,  # 需要在用户的沙箱中执行
        ),
        Tool(
            name="list_skills",
            description="列出所有已加载的技能",
            handler=list_skills,
            security_level=SecurityLevel.LOW,
            requires_session=False,
        ),
    ]


async def register_tools(registry):
    """注册执行工具"""
    for tool in get_execution_tools():
        registry.register(tool)


# 每个用户会话的技能缓存（通过 session.wallet_address 隔离）
_skills_cache: Dict[str, Dict[str, Any]] = {}


async def execute_python(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    执行 Python 代码（用户隔离沙箱版本）

    在用户的专属沙箱中执行代码，确保：
    1. 代码执行环境完全隔离
    2. 文件系统访问限制在用户工作空间
    3. 执行时间和内存受限制

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - code: 要执行的 Python 代码
            - timeout: 超时时间（秒），默认 30
            - capture_output: 是否捕获输出，默认 True

    Returns:
        执行结果
    """
    code = params.get("code", "")
    timeout = params.get("timeout", 30)

    # 使用用户的沙箱执行代码
    try:
        result = await session.sandbox.execute(code, timeout=timeout)
        return result
    except Exception as e:
        logger.error(f"Python execution failed: {e}")
        return {
            "status": "error",
            "message": f"代码执行失败: {str(e)}",
        }


async def execute_javascript(params: dict) -> Dict[str, Any]:
    """
    执行 JavaScript 代码（全局版本，不需要用户会话）

    Args:
        params: 参数字典，包含:
            - code: 要执行的 JavaScript 代码
            - timeout: 超时时间，默认 30

    Returns:
        执行结果
    """
    code = params.get("code", "")
    timeout = params.get("timeout", 30)

    # 检查 Node.js 是否可用
    try:
        process = await asyncio.create_subprocess_exec(
            "node",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(process.communicate(), timeout=5)
    except Exception:
        return {"status": "error", "message": "Node.js 未安装或不可用"}

    # 创建临时文件执行代码
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(code)
        temp_file = f.name

    try:
        process = await asyncio.create_subprocess_exec(
            "node",
            temp_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            return {"status": "error", "message": f"执行超时（{timeout}秒）"}

        return {
            "status": "success",
            "stdout": stdout.decode("utf-8", errors="ignore"),
            "stderr": stderr.decode("utf-8", errors="ignore"),
            "returncode": process.returncode,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass


async def browser_open(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    打开浏览器并访问 URL（用户隔离版本）

    使用用户的专属浏览器上下文，确保：
    1. Cookie 和 LocalStorage 完全隔离
    2. 下载目录隔离
    3. 会话关闭时自动清理

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - url: 要访问的 URL
            - headless: 是否使用无头模式，默认 True

    Returns:
        执行结果
    """
    url = params.get("url", "")
    headless = params.get("headless", True)

    # 使用用户的浏览器上下文
    try:
        result = await session.browser_context.open(url, headless=headless)
        session.update_browser_activity()
        return result
    except Exception as e:
        logger.error(f"Browser open failed: {e}")
        return {
            "status": "error",
            "message": f"打开浏览器失败: {str(e)}",
        }


async def browser_click(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    点击页面元素（用户隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - selector: CSS 选择器

    Returns:
        执行结果
    """
    selector = params.get("selector", "")

    try:
        result = await session.browser_context.click(selector)
        session.update_browser_activity()
        return result
    except Exception as e:
        logger.error(f"Browser click failed: {e}")
        return {
            "status": "error",
            "message": f"点击元素失败: {str(e)}",
        }


async def browser_fill(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    填写表单输入框（用户隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - selector: CSS 选择器
            - value: 要填写的值

    Returns:
        执行结果
    """
    selector = params.get("selector", "")
    value = params.get("value", "")

    try:
        result = await session.browser_context.fill(selector, value)
        session.update_browser_activity()
        return result
    except Exception as e:
        logger.error(f"Browser fill failed: {e}")
        return {
            "status": "error",
            "message": f"填写表单失败: {str(e)}",
        }


async def browser_get_content(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    获取页面内容（用户隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - selector: 可选的 CSS 选择器，不提供则获取整个页面内容

    Returns:
        页面内容
    """
    selector = params.get("selector")
    format = params.get("format", "text")

    try:
        result = await session.browser_context.get_content(selector=selector, format=format)
        session.update_browser_activity()
        return result
    except Exception as e:
        logger.error(f"Browser get content failed: {e}")
        return {
            "status": "error",
            "message": f"获取页面内容失败: {str(e)}",
        }


async def browser_screenshot(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    截图（用户隔离版本）

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - path: 保存路径，不提供则返回 base64

    Returns:
        截图结果
    """
    path = params.get("path")

    try:
        result = await session.browser_context.screenshot(path)
        session.update_browser_activity()
        return result
    except Exception as e:
        logger.error(f"Browser screenshot failed: {e}")
        return {
            "status": "error",
            "message": f"截图失败: {str(e)}",
        }


async def browser_close(session: "UserSession", params: dict = None) -> Dict[str, Any]:
    """
    关闭浏览器（用户隔离版本）

    Args:
        session: 用户会话上下文

    Returns:
        执行结果
    """
    try:
        await session.browser_context.close()
        return {"status": "success", "message": "浏览器已关闭"}
    except Exception as e:
        logger.error(f"Browser close failed: {e}")
        return {
            "status": "error",
            "message": f"关闭浏览器失败: {str(e)}",
        }


async def parse_skill_md(params: dict) -> Dict[str, Any]:
    """
    解析 skills.md 文件

    Args:
        params: 参数字典，包含:
            - file_path: skills.md 文件路径
            - session_id: 可选的用户会话ID，用于技能缓存隔离

    Returns:
        解析结果
    """
    file_path = params.get("file_path", "")
    session_id = params.get("session_id", "global")

    if not os.path.exists(file_path):
        return {"status": "error", "message": f"文件不存在: {file_path}"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 初始化该用户的技能缓存
        if session_id not in _skills_cache:
            _skills_cache[session_id] = {}

        # 解析 skills.md 格式
        skills = []
        current_skill = None

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_skill:
                    skills.append(current_skill)
                skill_name = line[3:].strip()
                current_skill = {
                    "name": skill_name,
                    "description": "",
                    "parameters": {},
                    "code": "",
                }
            elif current_skill:
                if line.startswith("description:"):
                    current_skill["description"] = line[12:].strip()
                elif line.startswith("```") and current_skill["code"]:
                    # 代码块结束
                    pass
                elif line.startswith("    ") or line.startswith("\t"):
                    # 代码内容
                    current_skill["code"] += line.strip() + "\n"

        if current_skill:
            skills.append(current_skill)

        # 缓存技能（按用户隔离）
        for skill in skills:
            _skills_cache[session_id][skill["name"]] = skill

        return {
            "status": "success",
            "skills": skills,
            "count": len(skills),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_skill(session: "UserSession", params: dict) -> Dict[str, Any]:
    """
    执行指定技能（用户隔离版本）

    在用户的沙箱中执行技能代码。

    Args:
        session: 用户会话上下文
        params: 参数字典，包含:
            - skill_name: 技能名称
            - parameters: 技能参数

    Returns:
        执行结果
    """
    skill_name = params.get("skill_name", "")
    parameters = params.get("parameters", {})
    session_id = session.wallet_address

    # 获取用户专属的技能缓存
    user_skills = _skills_cache.get(session_id, {})

    if skill_name not in user_skills:
        return {
            "status": "error",
            "message": f"技能未找到: {skill_name}。请先使用 parse_skill_md 解析技能文件。",
        }

    skill = user_skills[skill_name]
    code = skill.get("code", "")

    if not code:
        return {"status": "error", "message": "技能代码为空"}

    parameters = parameters or {}

    # 在用户沙箱中执行技能代码
    try:
        # 构建执行代码，注入参数
        exec_code = f"""
{parameters}

# 技能代码
{code}
"""
        result = await session.sandbox.execute(exec_code)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def list_skills(params: dict = None) -> Dict[str, Any]:
    """
    列出所有已加载的技能

    Args:
        params: 参数字典，包含:
            - session_id: 可选的用户会话ID，不提供则显示全局技能

    Returns:
        技能列表
    """
    session_id = params.get("session_id", "global") if params else "global"
    user_skills = _skills_cache.get(session_id, {})

    return {
        "status": "success",
        "skills": [
            {"name": name, "description": skill.get("description", "")}
            for name, skill in user_skills.items()
        ],
        "count": len(user_skills),
    }
