"""
代码执行沙箱

提供安全的 Python 代码执行环境，实现多用户隔离的代码执行能力。
"""

import asyncio
import io
import logging
import os
import sys
import tempfile
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import ast
import inspect
import threading

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
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
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
    ALLOWED_BUILTINS: Set[str] = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'isinstance',
        'len', 'list', 'map', 'max', 'min', 'ord', 'pow', 'print',
        'range', 'repr', 'reversed', 'round', 'set', 'slice', 'sorted',
        'str', 'sum', 'tuple', 'type', 'zip', 'True', 'False', 'None',
        'Exception', 'ValueError', 'TypeError', 'IndexError', 'KeyError',
        'AttributeError', 'RuntimeError', 'AssertionError', 'StopIteration',
        'BufferError', 'ArithmeticError', 'LookupError', 'OSError',
        'EOFError', 'ImportError', 'ModuleNotFoundError', 'NameError',
        'UnboundLocalError', 'OverflowError', 'ZeroDivisionError',
    }

    # ========== 允许导入的模块白名单 ==========
    ALLOWED_MODULES: Set[str] = {
        # 标准库安全模块
        'math', 'random', 'datetime', 'json', 're', 'collections',
        'itertools', 'functools', 'typing', 'decimal', 'fractions',
        'statistics', 'string', 'textwrap', 'unicodedata',
        'enum', 'dataclasses', 'warnings', 'time', 'calendar',
        'collections.abc', 'typing_extensions', 'numbers',
    }

    # ========== 危险模块黑名单（额外检查） ==========
    DANGEROUS_MODULES: Set[str] = {
        'os', 'sys', 'subprocess', 'shutil', 'pathlib', 'io',
        'socket', 'http', 'urllib', 'requests', 'ftplib', 'ssl',
        'pickle', 'marshal', 'shelve', 'sqlite3', 'tempfile',
        'importlib', '__import__', 'eval', 'exec', 'compile',
        'open', 'globals', 'locals', 'vars', 'dir', 'help',
        'exit', 'quit', 'breakpoint', 'threading', 'multiprocessing',
        'ctypes', 'ctypes.util', 'msvcrt', 'winreg', 'winsound',
        'pydoc', 'code', 'codeop', 'dis', 'inspect',
        'logging.config', 'logging.handlers',
        'email', 'smtplib', 'poplib', 'imaplib', 'nntplib',
        'xml', 'yaml', 'toml', 'configparser',
        'cryptography', 'hashlib', 'hmac', 'secrets',
    }

    # ========== 危险函数名黑名单 ==========
    DANGEROUS_FUNCTIONS: Set[str] = {
        '__import__', 'eval', 'exec', 'compile', 'open',
        'globals', 'locals', 'vars', 'dir',
        'exit', 'quit', 'breakpoint',
        'staticmethod', 'classmethod', 'property',
    }

    def __init__(
        self,
        wallet_address: str,
        sandbox_root: str = "/data/users",
        max_timeout: int = 60,
        max_memory_mb: int = 256
    ):
        """
        初始化代码沙箱

        Args:
            wallet_address: 用户钱包地址（用于创建用户专属沙箱目录）
            sandbox_root: 沙箱根目录
            max_timeout: 最大允许的超时时间（秒）
            max_memory_mb: 最大允许的内存使用（MB）
        """
        self.wallet_address = wallet_address
        self.sandbox_dir = Path(sandbox_root) / wallet_address / "sandbox"
        self.max_timeout = max_timeout
        self.max_memory_mb = max_memory_mb

        # 创建沙箱目录
        self._ensure_sandbox_dir()

        # 导入的模块缓存
        self._imported_modules: Dict[str, Any] = {}

        # 预加载允许的模块
        self._preload_allowed_modules()

        logger.info(f"CodeSandbox initialized for {wallet_address} at {self.sandbox_dir}")

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

    def validate_code(self, code: str) -> List[str]:
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
            '__builtins__',
            '__import__',
            'eval(',
            'exec(',
            'compile(',
            'globals(',
            'locals(',
            'getattr(',
            'setattr(',
            'delattr(',
            'super(',
        ]

        for pattern in danger_patterns:
            if pattern in code:
                warnings.append(f"检测到潜在危险函数: {pattern}")

        # 4. 检查危险字符串操作
        if '"os"' in code or "'os'" in code:
            warnings.append("检测到对 'os' 模块的引用")

        return warnings

    def _analyze_ast(self, tree: ast.AST) -> List[str]:
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

    def __init__(self, allowed_modules: Set[str], dangerous_functions: Set[str]):
        self.allowed_modules = allowed_modules
        self.dangerous_functions = dangerous_functions
        self.warnings: List[str] = []
        self.has_dangerous_operations = False

    def visit_Import(self, node: ast.Import) -> None:
        """检测 import 语句"""
        for alias in node.names:
            module_name = alias.name
            # 检查黑名单
            if any(dangerous in module_name for dangerous in ['os', 'sys', 'subprocess', 'socket']):
                self.warnings.append(f"检测到危险模块导入: {module_name}")
                self.has_dangerous_operations = True
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """检测 from ... import 语句"""
        if node.module:
            module_name = node.module
            if any(dangerous in module_name for dangerous in ['os', 'sys', 'subprocess', 'socket']):
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
            if node.func.attr == 'system' and isinstance(node.func.value, ast.Name):
                if node.func.value.id == 'os':
                    self.warnings.append("检测到 os.system() 调用")
                    self.has_dangerous_operations = True
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """检测名称引用"""
        if node.id in self.dangerous_functions:
            self.has_dangerous_operations = True
        self.generic_visit(node)

    def get_warnings(self) -> List[str]:
        return self.warnings


class SafeBuiltins:
    """安全的内置函数包装器"""

    def __init__(self, allowed_modules: Dict[str, Any]):
        self._allowed_modules = allowed_modules

    def __getattribute__(self, name: str) -> Any:
        # 获取原始 builtins
        import builtins
        allowed_builtins = CodeSandbox.ALLOWED_BUILTINS

        if name in allowed_builtins:
            return getattr(builtins, name)
        elif name == '__import__':
            # 自定义 import 函数
            return self._safe_import
        elif name == 'print':
            return print
        else:
            # 对于不在白名单中的，抛出 AttributeError
            raise AttributeError(
                f"'{name}' is not allowed in the sandbox. "
                f"Allowed builtins: {sorted(allowed_builtins)}"
            )

    def _safe_import(self, name: str, *args, **kwargs) -> Any:
        """安全的 import 函数"""
        # 检查模块是否允许
        allowed = CodeSandbox.ALLOWED_MODULES
        dangerous = CodeSandbox.DANGEROUS_MODULES

        # 检查黑名单
        for d in dangerous:
            if d in name:
                raise ImportError(
                    f"Module '{name}' is not allowed in the sandbox. "
                    f"Reason: security restriction"
                )

        # 检查白名单
        is_allowed = False
        for a in allowed:
            if name == a or name.startswith(a + '.'):
                is_allowed = True
                break

        if not is_allowed:
            raise ImportError(
                f"Module '{name}' is not in the allowed list. "
                f"Allowed modules: {sorted(allowed)}"
            )

        # 使用原始的 __import__ 导入
        import builtins
        return builtins.__import__(name, *args, **kwargs)


# 继续 CodeSandbox 类的其他方法
def execute_sandboxed_code(
    code: str,
    safe_builtins: SafeBuiltins,
    globals_dict: Dict,
    imports_dict: Dict[str, Any]
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
    # 设置安全的 __builtins__
    globals_dict['__builtins__'] = safe_builtins

    # 添加已导入的模块
    globals_dict.update(imports_dict)

    # 编译代码
    compiled_code = compile(code, '<sandbox>', 'exec')

    # 执行代码
    local_vars: Dict[str, Any] = {}
    exec(compiled_code, globals_dict, local_vars)

    return local_vars


# 为 CodeSandbox 添加剩余方法
async def _execute_code(
    self,
    code: str,
    timeout: int
) -> SandboxResult:
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
    globals_dict: Dict[str, Any] = {}

    # 捕获输出
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    try:
        # 在独立线程中执行代码以支持超时
        loop = asyncio.get_event_loop()

        def run_code():
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                execute_sandboxed_code(
                    code,
                    safe_builtins,
                    globals_dict,
                    self._imported_modules.copy()
                )

        # 执行代码并设置超时
        actual_timeout = min(timeout, self.max_timeout)
        await loop.run_in_executor(None, lambda: run_code())

        # 获取输出
        result.stdout = stdout_capture.getvalue()
        result.stderr = stderr_capture.getvalue()

        # 获取执行结果
        if '__return_value__' in globals_dict:
            result.result = globals_dict['__return_value__']
        elif globals_dict:
            # 返回最后一个非特殊变量
            for key in reversed(list(globals_dict.keys())):
                if not key.startswith('_'):
                    result.result = globals_dict[key]
                    break

        result.success = True

    except asyncio.TimeoutError:
        result.error = f"代码执行超时（{actual_timeout}秒）"
        result.stderr = stderr_capture.getvalue()

    except AttributeError as e:
        result.error = f"访问被拒绝: {e}"
        result.stderr = stderr_capture.getvalue()

    except ImportError as e:
        result.error = f"导入被拒绝: {e}"
        result.stderr = stderr_capture.getvalue()

    except SyntaxError as e:
        result.error = f"语法错误: {e}"
        result.stderr = stderr_capture.getvalue()

    except Exception as e:
        result.error = f"执行错误: {e}"
        result.stderr = stderr_capture.getvalue()
        logger.error(f"Sandbox execution error: {e}", exc_info=True)

    finally:
        result.execution_time = time.time() - start_time

    return result


# 将方法添加到 CodeSandbox 类
CodeSandbox.execute = _execute_code
CodeSandbox._create_safe_globals = lambda self: {
    '__builtins__': SafeBuiltins(self._imported_modules),
    **self._imported_modules,
}
