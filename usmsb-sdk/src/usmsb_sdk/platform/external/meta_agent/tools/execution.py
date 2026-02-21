"""
代码执行、浏览器操作和技能执行工具
"""

import asyncio
import io
import json
import logging
import os
import re
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def get_execution_tools() -> List:
    """获取执行工具列表"""
    from .registry import Tool
    from .security import SecurityLevel

    return [
        Tool(
            name="execute_python",
            description="执行 Python 代码并返回结果。支持标准库和常见第三方库。",
            handler=execute_python,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="execute_javascript",
            description="执行 JavaScript 代码（需要 Node.js 环境）",
            handler=execute_javascript,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="browser_open",
            description="打开浏览器并访问指定 URL",
            handler=browser_open,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="browser_click",
            description="点击页面元素（通过 CSS 选择器）",
            handler=browser_click,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="browser_fill",
            description="填写表单输入框",
            handler=browser_fill,
            security_level=SecurityLevel.MEDIUM,
        ),
        Tool(
            name="browser_get_content",
            description="获取浏览器当前页面内容",
            handler=browser_get_content,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="browser_screenshot",
            description="截取浏览器当前页面截图",
            handler=browser_screenshot,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="browser_close",
            description="关闭浏览器",
            handler=browser_close,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="parse_skill_md",
            description="解析 skills.md 文件并提取技能定义",
            handler=parse_skill_md,
            security_level=SecurityLevel.LOW,
        ),
        Tool(
            name="execute_skill",
            description="执行指定名称的技能（需要先解析 skills.md）",
            handler=execute_skill,
            security_level=SecurityLevel.HIGH,
        ),
        Tool(
            name="list_skills",
            description="列出所有已加载的技能",
            handler=list_skills,
            security_level=SecurityLevel.LOW,
        ),
    ]


async def register_tools(registry):
    """注册执行工具"""
    for tool in get_execution_tools():
        registry.register(tool)


_browser_instance = None


async def execute_python(params: dict) -> Dict[str, Any]:
    """
    执行 Python 代码

    Args:
        params: 参数字典，包含:
            - code: 要执行的 Python 代码
            - timeout: 超时时间（秒），默认 30
            - capture_output: 是否捕获输出，默认 True

    Returns:
        执行结果
    """
    code = params.get("code", "")
    timeout = params.get("timeout", 30)
    capture_output = params.get("capture_output", True)
    if not code or not code.strip():
        return {"status": "error", "message": "代码不能为空"}

    # 限制代码执行时间
    try:
        # 创建局部执行环境
        local_vars = {}
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # 准备执行
        compiled = compile(code, "<string>", "exec")

        # 执行代码
        if capture_output:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: exec(compiled, {"__builtins__": __builtins__}, local_vars)
                    ),
                    timeout=timeout,
                )
        else:
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: exec(compiled, {"__builtins__": __builtins__}, local_vars)
                ),
                timeout=timeout,
            )

        stdout = stdout_capture.getvalue() if capture_output else ""
        stderr = stderr_capture.getvalue() if capture_output else ""

        # 提取返回值（如果代码有 return 语句）
        result = None
        if "__return_value__" in local_vars:
            result = local_vars["__return_value__"]
        elif local_vars:
            # 返回最后的表达式结果
            result = list(local_vars.values())[-1] if local_vars else None

        return {
            "status": "success",
            "stdout": stdout,
            "stderr": stderr,
            "result": str(result) if result is not None else None,
            "local_vars": {k: str(v) for k, v in list(local_vars.items())[:10]},
        }

    except asyncio.TimeoutError:
        return {"status": "error", "message": f"代码执行超时（{timeout}秒）"}
    except SyntaxError as e:
        return {"status": "error", "message": f"语法错误: {e}"}
    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}


async def execute_javascript(params: dict) -> Dict[str, Any]:
    """
    执行 JavaScript 代码（需要 Node.js）

    Args:
        params: 参数字典，包含:
            - code: 要执行的 JavaScript 代码
            - timeout: 超时时间，默认 30

    Returns:
        执行结果
    """
    code = params.get("code", "")
    timeout = params.get("timeout", 30)
    import aiohttp

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


async def browser_open(params: dict) -> Dict[str, Any]:
    """
    打开浏览器并访问 URL

    Args:
        params: 参数字典，包含:
            - url: 要访问的 URL
            - headless: 是否使用无头模式，默认 True

    Returns:
        执行结果
    """
    url = params.get("url", "")
    headless = params.get("headless", True)
    global _browser_instance

    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url)

        _browser_instance = {"browser": browser, "page": page, "playwright": playwright}

        return {
            "status": "success",
            "message": f"已打开浏览器并访问 {url}",
            "url": url,
        }
    except ImportError:
        return {
            "status": "error",
            "message": "需要安装 playwright: pip install playwright && playwright install chromium",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def browser_click(params: dict) -> Dict[str, Any]:
    """
    点击页面元素

    Args:
        params: 参数字典，包含:
            - selector: CSS 选择器

    Returns:
        执行结果
    """
    selector = params.get("selector", "")
    global _browser_instance

    if not _browser_instance:
        return {"status": "error", "message": "浏览器未打开，请先使用 browser_open"}

    try:
        page = _browser_instance["page"]
        await page.click(selector)
        return {"status": "success", "message": f"已点击元素: {selector}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def browser_fill(params: dict) -> Dict[str, Any]:
    """
    填写表单输入框

    Args:
        params: 参数字典，包含:
            - selector: CSS 选择器
            - value: 要填写的值

    Returns:
        执行结果
    """
    selector = params.get("selector", "")
    value = params.get("value", "")
    global _browser_instance

    if not _browser_instance:
        return {"status": "error", "message": "浏览器未打开，请先使用 browser_open"}

    try:
        page = _browser_instance["page"]
        await page.fill(selector, value)
        return {"status": "success", "message": f"已填写 {selector}: {value}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def browser_get_content(params: dict) -> Dict[str, Any]:
    """
    获取页面内容

    Args:
        params: 参数字典，包含:
            - selector: 可选的 CSS 选择器，不提供则获取整个页面内容

    Returns:
        页面内容
    """
    selector = params.get("selector")
    global _browser_instance

    if not _browser_instance:
        return {"status": "error", "message": "浏览器未打开，请先使用 browser_open"}

    try:
        page = _browser_instance["page"]
        if selector:
            content = await page.inner_text(selector)
        else:
            content = await page.content()

        return {
            "status": "success",
            "content": content[:50000],
            "url": page.url,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def browser_screenshot(params: dict) -> Dict[str, Any]:
    """
    截图

    Args:
        params: 参数字典，包含:
            - path: 保存路径，不提供则返回 base64

    Returns:
        截图结果
    """
    path = params.get("path")
    global _browser_instance

    if not _browser_instance:
        return {"status": "error", "message": "浏览器未打开，请先使用 browser_open"}

    try:
        page = _browser_instance["page"]
        if path:
            await page.screenshot(path=path)
            return {"status": "success", "path": path}
        else:
            screenshot_bytes = await page.screenshot()
            import base64

            b64 = base64.b64encode(screenshot_bytes).decode()
            return {"status": "success", "screenshot": b64}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def browser_close(params: dict = None) -> Dict[str, Any]:
    """
    关闭浏览器

    Returns:
        执行结果
    """
    global _browser_instance

    if not _browser_instance:
        return {"status": "error", "message": "浏览器未打开"}

    try:
        browser = _browser_instance["browser"]
        playwright = _browser_instance["playwright"]
        await browser.close()
        await playwright.stop()
        _browser_instance = None
        return {"status": "success", "message": "浏览器已关闭"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


_skills_cache: Dict[str, Any] = {}


async def parse_skill_md(params: dict) -> Dict[str, Any]:
    """
    解析 skills.md 文件

    Args:
        params: 参数字典，包含:
            - file_path: skills.md 文件路径

    Returns:
        解析结果
    """
    file_path = params.get("file_path", "")
    global _skills_cache

    if not os.path.exists(file_path):
        return {"status": "error", "message": f"文件不存在: {file_path}"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 解析 skills.md 格式
        # 格式: ## skill_name
        # description: ...
        # parameters: ...
        # code: |
        #   ...

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
                elif line.startswith("parameters:"):
                    # 解析参数
                    pass
                elif line.startswith("```") and current_skill["code"]:
                    # 代码块结束
                    pass
                elif line.startswith("    ") or line.startswith("\t"):
                    # 代码内容
                    current_skill["code"] += line.strip() + "\n"

        if current_skill:
            skills.append(current_skill)

        # 缓存技能
        for skill in skills:
            _skills_cache[skill["name"]] = skill

        return {
            "status": "success",
            "skills": skills,
            "count": len(skills),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def execute_skill(params: dict) -> Dict[str, Any]:
    """
    执行指定技能

    Args:
        params: 参数字典，包含:
            - skill_name: 技能名称
            - parameters: 技能参数

    Returns:
        执行结果
    """
    skill_name = params.get("skill_name", "")
    parameters = params.get("parameters", {})
    global _skills_cache

    if skill_name not in _skills_cache:
        return {"status": "error", "message": f"技能未找到: {skill_name}"}

    skill = _skills_cache[skill_name]
    code = skill.get("code", "")

    if not code:
        return {"status": "error", "message": "技能代码为空"}

    parameters = parameters or {}

    # 将参数注入到代码中
    try:
        # 简单的方式：将参数作为全局变量
        exec_globals = {"__builtins__": __builtins__}
        exec_globals.update(parameters)

        compiled = compile(code, "<skill>", "exec")
        local_vars = {}

        exec(compiled, exec_globals, local_vars)

        return {
            "status": "success",
            "skill_name": skill_name,
            "result": local_vars.get("result"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def list_skills(params: dict = None) -> Dict[str, Any]:
    """
    列出所有已加载的技能

    Returns:
        技能列表
    """
    global _skills_cache

    return {
        "status": "success",
        "skills": [
            {"name": name, "description": skill.get("description", "")}
            for name, skill in _skills_cache.items()
        ],
        "count": len(_skills_cache),
    }
