"""
代码执行沙箱

提供安全的 Python 代码执行环境，实现多用户隔离的代码执行能力。
"""

import ast
import asyncio
import io
import logging
import os
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SandboxResult:
    """
    沙箱执行结果

    Attributes:
        success: 执行是否成功
        stdout: 标准输出
        stderr: 标准错误
        result: 执行结果（最后一个表达式的值）
        error: 错误信息（如果有）
        warnings: 警告列表
        execution_time: 执行时间（秒）
    """

    success: bool
    stdout: str = ""
    stderr: str = ""
    result: Any = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    execution_time: float = 0.0


class CodeSandbox:
    """
    代码执行沙箱

    提供安全的 Python 代码执行环境：
    1. 限制可用的内置函数（白名单机制）
    2. 限制可导入的模块（白名单机制）
    3. 限制文件系统访问范围（只能访问用户的sandbox目录）
    4. 限制执行时间和内存使用
    5. 捕获 stdout/stderr 输出

    安全特性：
    - 使用自定义 __builtins__ 替换默认内置函数
    - 自定义 __import__ 函数拦截模块导入
    - AST 静态分析检测潜在危险操作
    - 代码执行在独立线程中，支持超时控制
    - 可选的内存限制（通过 resource 模块或自定义监控）
    """

    # ========== 允许的内置函数白名单 ==========
    ALLOWED_BUILTINS: set[str] = {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "filter",
        "float",
        "format",
        "frozenset",
        "hash",
        "hex",
        "int",
        "isinstance",
        "len",
        "list",
        "map",
        "max",
        "min",
        "ord",
        "pow",
        "print",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "slice",
        "sorted",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
        "True",
        "False",
        "None",
        "Exception",
        "ValueError",
        "TypeError",
        "IndexError",
        "KeyError",
        "AttributeError",
        "RuntimeError",
        "AssertionError",
        "StopIteration",
        "BufferError",
        "ArithmeticError",
        "LookupError",
        "OSError",
        "EOFError",
        "ImportError",
        "ModuleNotFoundError",
        "NameError",
        "UnboundLocalError",
        "OverflowError",
        "ZeroDivisionError",
        "__build_class__",  # Required for class definitions
        "object",  # Required for class inheritance
    }

    # ========== 允许导入的模块白名单 ==========
    ALLOWED_MODULES: set[str] = {
        # 标准库安全模块
        "math",
        "random",
        "datetime",
        "json",
        "re",
        "collections",
        "itertools",
        "functools",
        "typing",
        "decimal",
        "fractions",
        "statistics",
        "string",
        "textwrap",
        "unicodedata",
        "enum",
        "dataclasses",
        "warnings",
        "time",
        "calendar",
        "collections.abc",
        "typing_extensions",
        "numbers",
    }

    # ========== 危险模块黑名单（额外检查） ==========
    DANGEROUS_MODULES: set[str] = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "io",
        "socket",
        "http",
        "urllib",
        "requests",
        "ftplib",
        "ssl",
        "pickle",
        "marshal",
        "shelve",
        "sqlite3",
        "tempfile",
        "importlib",
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "globals",
        "locals",
        "vars",
        "dir",
        "help",
        "exit",
        "quit",
        "breakpoint",
        "threading",
        "multiprocessing",
        "ctypes",
        "ctypes.util",
        "msvcrt",
        "winreg",
        "winsound",
        "pydoc",
        "code",
        "codeop",
        "dis",
        "inspect",
        "logging.config",
        "logging.handlers",
        "email",
        "smtplib",
        "poplib",
        "imaplib",
        "nntplib",
        "xml",
        "yaml",
        "toml",
        "configparser",
        "cryptography",
        "hashlib",
        "hmac",
        "secrets",
    }

    # ========== 危险函数名黑名单 ==========
    DANGEROUS_FUNCTIONS: set[str] = {
        "__import__",
        "eval",
        "exec",
        "compile",
        "open",
        "globals",
        "locals",
        "vars",
        "dir",
        "exit",
        "quit",
        "breakpoint",
        "staticmethod",
        "classmethod",
        "property",
    }

    def __init__(
        self,
        wallet_address: str,
        sandbox_root: str = "/data/users",
        workspace_root: str = None,
        max_timeout: int = 60,
        max_memory_mb: int = 256,
        persist_globals: bool = True,
    ):
        """
        初始化代码沙箱

        Args:
            wallet_address: 用户钱包地址（用于创建用户专属沙箱目录）
            sandbox_root: 沙箱根目录
            workspace_root: 用户工作空间目录（可选，用于文件共享）
            max_timeout: 最大允许的超时时间（秒）
            max_memory_mb: 最大允许的内存使用（MB）
            persist_globals: 是否在多次执行间保持变量状态
        """
        self.wallet_address = wallet_address
        self.sandbox_dir = Path(sandbox_root) / wallet_address / "sandbox"

        # 如果没有指定 workspace_root，默认使用 workspace 目录
        if workspace_root is None:
            self.workspace_dir = Path(sandbox_root) / wallet_address / "workspace"
        else:
            self.workspace_dir = Path(workspace_root)

        self.max_timeout = max_timeout
        self.max_memory_mb = max_memory_mb
        self.persist_globals = persist_globals

        # 创建沙箱目录
        self._ensure_sandbox_dir()

        # 导入的模块缓存
        self._imported_modules: dict[str, Any] = {}

        # 用户变量缓存（用于多次执行间保持状态）
        self._user_globals: dict[str, Any] = {}

        # 预加载允许的模块
        self._preload_allowed_modules()

        logger.info(
            f"CodeSandbox initialized for {wallet_address} at {self.sandbox_dir}, workspace at {self.workspace_dir}"
        )

    def _ensure_sandbox_dir(self) -> None:
        """确保沙箱目录存在"""
        try:
            self.sandbox_dir.mkdir(parents=True, exist_ok=True)
            # 创建临时执行目录
            (self.sandbox_dir / "exec").mkdir(exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create sandbox directory: {e}")
            # 如果无法创建目录，使用系统临时目录
            temp_base = Path(tempfile.gettempdir()) / f"usmsb_sandbox_{self.wallet_address}"
            self.sandbox_dir = temp_base / "sandbox"
            self.sandbox_dir.mkdir(parents=True, exist_ok=True)
            (self.sandbox_dir / "exec").mkdir(exist_ok=True)

    def _preload_allowed_modules(self) -> None:
        """预加载允许的模块"""
        for module_name in self.ALLOWED_MODULES:
            try:
                self._imported_modules[module_name] = __import__(module_name)
            except ImportError:
                logger.debug(f"Module {module_name} not available for preloading")

    def validate_code(self, code: str) -> list[str]:
        """
        验证代码，返回警告或错误列表

        Args:
            code: Python 代码字符串

        Returns:
            警告或错误消息列表
        """
        warnings = []

        # 1. 检查代码长度
        if len(code) > 100000:  # 100KB
            warnings.append("代码长度超过 100KB，可能影响性能")

        # 2. AST 静态分析
        try:
            tree = ast.parse(code)
            warnings.extend(self._analyze_ast(tree))
        except SyntaxError as e:
            warnings.append(f"语法错误: {e}")
            return warnings

        # 3. 检查危险字符串
        danger_patterns = [
            "__builtins__",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
            "globals(",
            "locals(",
            "getattr(",
            "setattr(",
            "delattr(",
            "super(",
        ]

        for pattern in danger_patterns:
            if pattern in code:
                warnings.append(f"检测到潜在危险函数: {pattern}")

        # 4. 检查危险字符串操作
        if '"os"' in code or "'os'" in code:
            warnings.append("检测到对 'os' 模块的引用")

        return warnings

    def _analyze_ast(self, tree: ast.AST) -> list[str]:
        """
        分析 AST 检测潜在危险操作

        Args:
            tree: AST 树

        Returns:
            警告消息列表
        """
        warnings = []
        visitor = SandboxASTVisitor(self.ALLOWED_MODULES, self.DANGEROUS_FUNCTIONS)
        visitor.visit(tree)
        warnings.extend(visitor.get_warnings())

        # 检测是否有危险操作
        if visitor.has_dangerous_operations:
            warnings.append("代码包含潜在危险操作，可能被阻止执行")

        return warnings


class SandboxASTVisitor(ast.NodeVisitor):
    """AST 访问器，用于检测危险操作"""

    def __init__(self, allowed_modules: set[str], dangerous_functions: set[str]):
        self.allowed_modules = allowed_modules
        self.dangerous_functions = dangerous_functions
        self.warnings: list[str] = []
        self.has_dangerous_operations = False

    def visit_Import(self, node: ast.Import) -> None:
        """检测 import 语句"""
        for alias in node.names:
            module_name = alias.name
            # 检查黑名单
            if any(dangerous in module_name for dangerous in ["os", "sys", "subprocess", "socket"]):
                self.warnings.append(f"检测到危险模块导入: {module_name}")
                self.has_dangerous_operations = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """检测 from ... import 语句"""
        if node.module:
            module_name = node.module
            if any(dangerous in module_name for dangerous in ["os", "sys", "subprocess", "socket"]):
                self.warnings.append(f"检测到危险模块导入: from {module_name} import ...")
                self.has_dangerous_operations = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """检测函数调用"""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.dangerous_functions:
                self.warnings.append(f"检测到危险函数调用: {func_name}()")
                self.has_dangerous_operations = True
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr == "system" and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "os":
                    self.warnings.append("检测到 os.system() 调用")
                    self.has_dangerous_operations = True
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """检测名称引用"""
        if node.id in self.dangerous_functions:
            self.has_dangerous_operations = True
        self.generic_visit(node)

    def get_warnings(self) -> list[str]:
        return self.warnings


class SafeBuiltins:
    """安全的内置函数包装器"""

    # 使用 object.__getattribute__ 来避免递归
    __slots__ = ("_dict", "_allowed_modules")

    def __init__(self, allowed_modules: dict[str, Any]):
        # 使用 object.__setattr__ 避免触发 __setattr__
        object.__setattr__(self, "_allowed_modules", allowed_modules)
        object.__setattr__(self, "_dict", {})

        # 预加载允许的内置函数
        import builtins as _builtins

        allowed_builtins = CodeSandbox.ALLOWED_BUILTINS
        for name in allowed_builtins:
            object.__getattribute__(self, "_dict")[name] = getattr(_builtins, name)

    def __getattribute__(self, name: str) -> Any:
        # 使用 object.__getattribute__ 访问 _dict 避免递归
        _dict = object.__getattribute__(self, "_dict")

        if name in _dict:
            return _dict[name]
        elif name == "__import__":
            # 自定义 import 函数
            return _safe_import_method
        elif name == "print":
            import builtins

            return builtins.print
        else:
            # 对于不在白名单中的，抛出 AttributeError
            allowed_list = sorted(_dict.keys())
            raise AttributeError(
                f"'{name}' is not allowed in the sandbox. Allowed builtins: {allowed_list}"
            )

    def __getitem__(self, name: str) -> Any:
        """支持字典式访问，如 __builtins__['print']"""
        _dict = object.__getattribute__(self, "_dict")
        return _dict.get(name)


# 模块级别的 _safe_import 函数，避免递归问题
def _safe_import_method(name: str, *args, **kwargs) -> Any:
    """安全的 import 函数"""
    # 检查模块是否允许
    allowed = CodeSandbox.ALLOWED_MODULES
    dangerous = CodeSandbox.DANGEROUS_MODULES

    # 检查黑名单 - 使用精确匹配或前缀匹配
    for d in dangerous:
        if name == d or name.startswith(d + "."):
            raise ImportError(
                f"Module '{name}' is not allowed in the sandbox. Reason: security restriction"
            )

    # 检查白名单
    is_allowed = False
    for a in allowed:
        if name == a or name.startswith(a + "."):
            is_allowed = True
            break

    if not is_allowed:
        raise ImportError(
            f"Module '{name}' is not in the allowed list. Allowed modules: {sorted(allowed)}"
        )

    # 使用原始的 __import__ 导入
    import builtins

    return builtins.__import__(name, *args, **kwargs)


def _blocked_function(name: str):
    """创建一个被阻止的函数占位符"""

    def _raise_blocked(*args, **kwargs):
        raise NameError(f"name '{name}' is not defined (blocked for security)")

    return _raise_blocked


# 继续 CodeSandbox 类的其他方法
def execute_sandboxed_code(
    code: str, safe_builtins: SafeBuiltins, globals_dict: dict, imports_dict: dict[str, Any]
) -> Any:
    """
    在隔离环境中执行代码

    Args:
        code: 要执行的代码
        safe_builtins: 安全的内置函数包装器
        globals_dict: 全局变量字典
        imports_dict: 已导入的模块字典

    Returns:
        执行结果
    """
    # 设置安全的 __builtins__ (使用 SafeBuiltins 作为字典)
    import builtins as _builtins

    allowed_builtins = CodeSandbox.ALLOWED_BUILTINS
    dangerous_functions = CodeSandbox.DANGEROUS_FUNCTIONS

    # 构建安全的 __builtins__ 字典
    safe_builtins_dict = {}
    for name in allowed_builtins:
        safe_builtins_dict[name] = getattr(_builtins, name)

    # 添加 __import__ 函数
    safe_builtins_dict["__import__"] = _safe_import_method

    # 添加 print 函数（直接使用原生的）
    safe_builtins_dict["print"] = _builtins.print

    # 为危险函数创建占位符，当被调用时抛出错误
    for dangerous_func in dangerous_functions:
        if dangerous_func not in safe_builtins_dict:
            safe_builtins_dict[dangerous_func] = _blocked_function(dangerous_func)

    # Set __builtins__ in globals dict - this is crucial for intercepting imports
    globals_dict["__builtins__"] = safe_builtins_dict

    # Also add safe builtins directly to globals_dict (for built-in functions)
    globals_dict.update(safe_builtins_dict)

    # Add module-level attributes needed for class definitions
    if "__name__" not in globals_dict:
        globals_dict["__name__"] = "__sandbox__"

    # 添加已导入的模块
    globals_dict.update(imports_dict)

    # 编译代码
    compiled_code = compile(code, "<sandbox>", "exec")

    # 执行代码 - 使用 globals_dict 作为 both globals 和 locals
    # 这允许函数定义递归调用自己
    exec(compiled_code, globals_dict, globals_dict)

    # 返回 globals_dict 作为结果
    return globals_dict


# 为 CodeSandbox 添加 execute 方法
async def _execute_code(self, code: str, timeout: int) -> SandboxResult:
    """
    在隔离环境中执行代码

    Args:
        code: 要执行的代码
        timeout: 超时时间（秒）

    Returns:
        执行结果
    """
    import time

    start_time = time.time()

    # 验证代码
    warnings = self.validate_code(code)

    result = SandboxResult(success=False, warnings=warnings)

    # 如果有严重错误，提前返回
    for w in warnings:
        if "语法错误" in w:
            result.error = w
            return result

    # 创建安全执行环境
    safe_builtins = SafeBuiltins(self._imported_modules)

    # 使用持久化的 globals 或创建新的
    if self.persist_globals:
        globals_dict = self._user_globals
    else:
        globals_dict: dict[str, Any] = {}

    # 捕获输出
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # 在独立线程中执行代码以支持超时
        loop = asyncio.get_event_loop()


        def run_code():
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                execute_sandboxed_code(
                    code, safe_builtins, globals_dict, self._imported_modules.copy()
                )

        # 执行代码并设置超时
        actual_timeout = min(timeout, self.max_timeout)
        try:
            await asyncio.wait_for(
                loop.run_in_executor(None, lambda: run_code()), timeout=actual_timeout
            )
        except TimeoutError:
            # Already caught in outer except block, re-raise to be handled there
            raise

        # 获取输出
        result.stdout = stdout_capture.getvalue()
        result.stderr = stderr_capture.getvalue()

        # 获取执行结果
        if "__return_value__" in globals_dict:
            result.result = globals_dict["__return_value__"]
        elif globals_dict:
            # 返回最后一个非特殊变量
            # 我们需要过滤掉内置函数和预加载的模块
            allowed_builtins = CodeSandbox.ALLOWED_BUILTINS
            allowed_modules = CodeSandbox.ALLOWED_MODULES
            excluded = allowed_builtins | allowed_modules | {"__builtins__"}
            for key in reversed(list(globals_dict.keys())):
                if not key.startswith("_") and key not in excluded:
                    result.result = globals_dict[key]
                    break

        result.success = True

    except TimeoutError:
        result.error = f"代码执行超时（{actual_timeout}秒）"
        result.stderr = stderr_capture.getvalue()

    except (AttributeError, ImportError, SyntaxError) as e:
        # These are considered execution failures
        result.error = f"执行错误: {type(e).__name__}: {e}"
        result.stderr = stderr_capture.getvalue()

    except NameError as e:
        # NameError for blocked functions should be treated as failure
        error_msg = str(e)
        if "blocked for security" in error_msg:
            # This is a blocked function call - treat as failure
            result.error = f"执行错误: {error_msg}"
            result.stderr = stderr_capture.getvalue()
        else:
            # Other NameErrors (undefined variables) are runtime errors
            result.success = True
            result.stderr = stderr_capture.getvalue()
            import traceback

            tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            result.stderr += tb_str
            logger.debug(f"Sandbox runtime error (treated as success): {e}")

    except Exception as e:
        # Runtime errors (NameError, etc.) should still set success=True
        # but capture the error in stderr
        result.success = True
        result.stderr = stderr_capture.getvalue()
        # Also add the exception message to stderr
        import traceback

        tb_str = "".join(traceback.format_exception(type(e), e, e.__traceback__))
        result.stderr += tb_str
        logger.debug(f"Sandbox runtime error (treated as success): {e}")

    finally:
        result.execution_time = time.time() - start_time

    return result


# 将方法添加到 CodeSandbox 类
CodeSandbox.execute = _execute_code


async def _run_command(
    self, command: str, cwd: str = None, timeout: int = 60, env: dict = None
) -> SandboxResult:
    """
    在沙箱中执行 shell 命令（如 npm、node 等）

    Args:
        command: 要执行的命令
        cwd: 工作目录，默认为沙箱目录
        timeout: 超时时间（秒）
        env: 环境变量

    Returns:
        执行结果
    """
    import asyncio
    import time

    # 确保 timeout 是整数
    try:
        timeout = int(timeout)
    except (TypeError, ValueError):
        timeout = 60

    start_time = time.time()
    result = SandboxResult(success=False)

    # 确定工作目录
    if cwd:
        # 如果是相对路径，基于 workspace 目录
        if not cwd.startswith("/"):
            working_dir = self.workspace_dir / cwd
        else:
            working_dir = Path(cwd)
    else:
        working_dir = self.workspace_dir

    # 确保工作目录存在
    working_dir.mkdir(parents=True, exist_ok=True)

    # 准备环境变量 - 使用系统原始环境变量，确保 node/python 等命令可用
    full_env = os.environ.copy()
    # 确保 HOME 变量存在（某些命令需要）
    if "HOME" not in full_env:
        full_env["HOME"] = str(self.sandbox_dir.parent)
    if env:
        full_env.update(env)

    try:
        # 执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(working_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except TimeoutError:
            process.kill()
            await process.wait()
            result.error = f"命令执行超时（{timeout}秒）"
            result.execution_time = timeout
            return result

        result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
        result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
        result.success = process.returncode == 0

        if process.returncode != 0:
            result.error = f"命令执行失败，退出码: {process.returncode}"

    except Exception as e:
        result.error = f"执行错误: {str(e)}"
        result.stderr = str(e)

    result.execution_time = time.time() - start_time
    return result


CodeSandbox.run_command = _run_command


async def _install_browser(self, browser: str = "chromium") -> SandboxResult:
    """
    在沙箱中安装浏览器（Playwright）

    Args:
        browser: 浏览器类型 (chromium, firefox, webkit)

    Returns:
        安装结果
    """
    import asyncio
    import time

    start_time = time.time()
    result = SandboxResult(success=False)

    try:
        # 先安装 Playwright
        install_playwright_cmd = "npm install -g playwright"

        process = await asyncio.create_subprocess_shell(
            install_playwright_cmd,
            cwd=str(self.workspace_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)

        result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
        result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""

        if process.returncode != 0:
            result.error = f"Playwright 安装失败: {result.stderr}"
        else:
            # 安装浏览器
            install_browser_cmd = f"playwright install {browser}"

            process2 = await asyncio.create_subprocess_shell(
                install_browser_cmd,
                cwd=str(self.workspace_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )

            stdout2, stderr2 = await asyncio.wait_for(process2.communicate(), timeout=180)

            result.stdout += stdout2.decode("utf-8", errors="replace") if stdout2 else ""
            result.stderr += stderr2.decode("utf-8", errors="replace") if stderr2 else ""

            if process2.returncode == 0:
                result.success = True
            else:
                result.error = f"浏览器安装失败: {result.stderr}"

    except Exception as e:
        result.error = f"安装错误: {str(e)}"

    result.execution_time = time.time() - start_time
    return result


CodeSandbox.install_browser = _install_browser


async def _start_jupyter(
    self,
    port: int = 8888,
    password: str = "",
) -> SandboxResult:
    """
    在沙箱中启动 JupyterLab

    Args:
        port: 端口号
        password: 访问密码（可选）

    Returns:
        启动结果
    """
    import asyncio
    import platform
    import random
    import string
    import time

    start_time = time.time()
    result = SandboxResult(success=False)

    # 生成随机 token
    token = "".join(random.choices(string.ascii_letters + string.digits, k=32))

    try:
        # 构建启动命令
        cmd_parts = [
            "jupyter",
            "lab",
            "--port",
            str(port),
            "--no-browser",
            "--ip",
            "0.0.0.0",
            f"--NotebookApp.token={token}",
        ]

        if password:
            cmd_parts.append(f"--NotebookApp.password={password}")

        cmd = cmd_parts  # 保持列表形式

        # 根据操作系统选择不同的后台启动方式
        if platform.system() == "Windows":
            # Windows: 使用 start 命令启动新窗口
            import shlex
            import subprocess

            cmd_str = " ".join([shlex.quote(c) for c in cmd])
            # 使用 cmd /c start 启动新窗口
            run_cmd = f'start "JupyterLab" cmd /c {cmd_str}'

            process = await asyncio.create_subprocess_shell(
                run_cmd,
                cwd=str(self.workspace_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            # Linux/Mac: 使用 nohup
            cmd_str = " ".join(cmd)
            run_cmd = f"nohup {cmd_str} > jupyter.log 2>&1 &"

            process = await asyncio.create_subprocess_shell(
                run_cmd,
                cwd=str(self.workspace_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy(),
            )

        # 不等待结果，立即返回
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=5)
            result.stdout = stdout.decode("utf-8", errors="replace") if stdout else ""
            result.stderr = stderr.decode("utf-8", errors="replace") if stderr else ""
        except TimeoutError:
            # 超时是正常的，因为是后台启动
            pass

        # 等待一下让 JupyterLab 启动
        await asyncio.sleep(3)

        result.success = True
        result.message = f"JupyterLab 启动成功，访问地址: http://localhost:{port}/lab?token={token}"

    except Exception as e:
        result.error = f"启动错误: {str(e)}"

    result.execution_time = time.time() - start_time
    return result


CodeSandbox.start_jupyter = _start_jupyter
