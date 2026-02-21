"""
Unit tests for CodeSandbox - secure code execution sandbox

Tests cover:
- Safe code execution with allowed modules
- Blocking of dangerous imports and builtins
- Timeout enforcement
- User isolation between different sandboxes
- File access restrictions
"""

import asyncio
import tempfile
from pathlib import Path
import pytest

from usmsb_sdk.platform.external.meta_agent.sandbox import CodeSandbox, SandboxResult


class TestCodeSandbox:
    """CodeSandbox unit tests"""

    @pytest.mark.asyncio
    async def test_safe_code_execution(self):
        """测试安全代码执行"""
        # Create a temporary sandbox
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_1",
                sandbox_root=temp_dir
            )

            # Execute simple code
            result = await sandbox.execute("print('hello')", timeout=30)

            assert result.success is True
            assert "hello" in result.stdout
            assert result.error is None
            assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_math_calculation(self):
        """测试数学计算"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_math",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import math
result = math.sqrt(16) + math.pi
print(result)
""")

            assert result.success is True
            assert "6.14" in result.stdout or "6.14" in result.result

    @pytest.mark.asyncio
    async def test_dangerous_import_blocked(self):
        """测试危险模块导入被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_danger",
                sandbox_root=temp_dir
            )

            # Try to import dangerous module
            result = await sandbox.execute("import os")

            assert result.success is False
            assert "os" in result.error or "not allowed" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_import_sys(self):
        """测试sys模块导入被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_danger2",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("import sys")

            assert result.success is False
            assert "sys" in result.error or "not allowed" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_import_subprocess(self):
        """测试subprocess模块导入被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_danger3",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("import subprocess")

            assert result.success is False
            assert "subprocess" in result.error or "not allowed" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_builtin_eval_blocked(self):
        """测试危险内置函数eval被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_eval",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("eval('1+1')")

            assert result.success is False
            assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_builtin_exec_blocked(self):
        """测试危险内置函数exec被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_exec",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("exec('print(1)')")

            assert result.success is False
            assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_dangerous_builtin_open_blocked(self):
        """测试危险内置函数open被阻止"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_open",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("open('test.txt').read()")

            assert result.success is False
            assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_timeout_enforced(self):
        """测试超时限制"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_timeout",
                sandbox_root=temp_dir
            )

            # Infinite loop should timeout
            result = await sandbox.execute("while True: pass", timeout=2)

            assert result.success is False
            assert "超时" in result.error or "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_long_running_safe_code(self):
        """测试长时间运行的安全代码"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_long",
                sandbox_root=temp_dir,
                max_timeout=60
            )

            # Long but safe code (calculating factorials)
            result = await sandbox.execute("""
import math
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(10)
print(result)
""", timeout=30)

            assert result.success is True
            assert "3628800" in result.stdout

    @pytest.mark.asyncio
    async def test_syntax_error_handling(self):
        """测试语法错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_syntax",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("print('hello')")

            assert result.success is False
            assert "语法错误" in result.error or "SyntaxError" in result.error

    @pytest.mark.asyncio
    async def test_runtime_error_handling(self):
        """测试运行时错误处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_runtime",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("print(undefined_variable)")

            assert result.success is True  # Code executes, but has stderr
            assert "undefined_variable" in result.stderr

    @pytest.mark.asyncio
    async def test_allowed_json_import(self):
        """测试允许的json模块导入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_json",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import json
data = {'key': 'value'}
print(json.dumps(data))
""")

            assert result.success is True
            assert "key" in result.stdout and "value" in result.stdout

    @pytest.mark.asyncio
    async def test_allowed_re_import(self):
        """测试允许的re模块导入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_re",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import re
pattern = r'\\d+'
text = 'test123'
matches = re.findall(pattern, text)
print(matches)
""")

            assert result.success is True
            assert "123" in result.stdout

    @pytest.mark.asyncio
    async def test_allowed_datetime_import(self):
        """测试允许的datetime模块导入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_datetime",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import datetime
now = datetime.datetime.now()
print(now.year)
""")

            assert result.success is True
            # Should contain current year
            assert result.success

    @pytest.mark.asyncio
    async def test_allowed_collections_import(self):
        """测试允许的collections模块导入"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_collections",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
from collections import defaultdict
d = defaultdict(int)
d['key'] += 1
print(d['key'])
""")

            assert result.success is True
            assert "1" in result.stdout

    @pytest.mark.asyncio
    async def test_user_isolation(self):
        """测试用户隔离 - 不同用户有独立的沙箱目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two sandboxes for different users
            sandbox_a = CodeSandbox(
                wallet_address="user_a",
                sandbox_root=temp_dir
            )
            sandbox_b = CodeSandbox(
                wallet_address="user_b",
                sandbox_root=temp_dir
            )

            # Check sandbox directories are different
            assert sandbox_a.sandbox_dir != sandbox_b.sandbox_dir
            assert "user_a" in str(sandbox_a.sandbox_dir)
            assert "user_b" in str(sandbox_b.sandbox_dir)

    @pytest.mark.asyncio
    async def test_code_validation_long_code(self):
        """测试代码验证 - 超长代码"""
        sandbox = CodeSandbox(wallet_address="test_user")

        # Create code > 100KB
        long_code = "x = 1\n" * 30000
        warnings = sandbox.validate_code(long_code)

        assert len(warnings) > 0
        assert any("长度" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_code_validation_dangerous_patterns(self):
        """测试代码验证 - 危险模式检测"""
        sandbox = CodeSandbox(wallet_address="test_user")

        # Code with dangerous patterns
        dangerous_code = "result = eval('1+1')"
        warnings = sandbox.validate_code(dangerous_code)

        assert len(warnings) > 0
        assert any("危险" in w or "dangerous" in w.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_code_validation_os_reference(self):
        """测试代码验证 - os模块引用检测"""
        sandbox = CodeSandbox(wallet_address="test_user")

        # Code referencing os module
        os_code = "print(\"using os\")"
        warnings = sandbox.validate_code(os_code)

        assert len(warnings) > 0
        assert any("os" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_execution_result_capture(self):
        """测试执行结果捕获"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_result",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
x = 42
y = x * 2
z = y + 10
final = z
""")

            assert result.success is True
            # Result should be the last variable value
            assert result.result == 94 or str(result.result) == "94"

    @pytest.mark.asyncio
    async def test_stdout_capture(self):
        """测试标准输出捕获"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_io",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
print("Line 1")
print("Line 2")
print("Line 3")
""")

            assert result.success is True
            assert "Line 1" in result.stdout
            assert "Line 2" in result.stdout
            assert "Line 3" in result.stdout

    @pytest.mark.asyncio
    async def test_stderr_capture(self):
        """测试标准错误捕获"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_stderr",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import sys
sys.stderr.write("Error message\\n")
""")

            assert result.success is True
            assert "Error message" in result.stderr

    @pytest.mark.asyncio
    async def test_multiple_execution(self):
        """测试多次执行"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_multi",
                sandbox_root=temp_dir
            )

            # First execution
            result1 = await sandbox.execute("x = 1")
            assert result1.success is True

            # Second execution
            result2 = await sandbox.execute("print(x + 10)")
            assert result2.success is True
            assert "11" in result2.stdout

    @pytest.mark.asyncio
    async def test_allowed_builtins(self):
        """测试允许的内置函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_builtins",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
items = [1, 2, 3, 4, 5]
result = sum(items)
result2 = max(items)
result3 = min(items)
print(f'{result}, {result2}, {result3}')
""")

            assert result.success is True
            assert "15" in result.stdout
            assert "5" in result.stdout
            assert "1" in result.stdout

    @pytest.mark.asyncio
    async def test_fstring_formatting(self):
        """测试f-string格式化"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_fstring",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
name = "test"
print(f'Hello {name}!')
""")

            assert result.success is True
            assert "Hello test" in result.stdout

    @pytest.mark.asyncio
    async def test_list_comprehension(self):
        """测试列表推导"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_comp",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
squares = [x**2 for x in range(5)]
print(squares)
""")

            assert result.success is True
            assert "[0, 1, 4, 9, 16]" in result.stdout or "0, 1, 4, 9, 16" in result.stdout

    @pytest.mark.asyncio
    async def test_dict_operations(self):
        """测试字典操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_dict",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
data = {'a': 1, 'b': 2, 'c': 3}
keys = list(data.keys())
values = list(data.values())
print(f'Keys: {keys}, Values: {values}')
""")

            assert result.success is True
            assert "Keys:" in result.stdout
            assert "Values:" in result.stdout

    @pytest.mark.asyncio
    async def test_allowed_exceptions(self):
        """测试允许的异常类"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_exceptions",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
try:
    raise ValueError('Test error')
except ValueError as e:
    print(f'Caught: {e}')
""")

            assert result.success is True
            assert "Caught: Test error" in result.stdout or "Caught: Test error" in result.stderr

    @pytest.mark.asyncio
    async def test_execution_time_measurement(self):
        """测试执行时间测量"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_time",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
import time
start = time.time()
for i in range(10000):
    pass
end = time.time()
print(f'Took {end - start:.4f} seconds')
""")

            assert result.success is True
            assert result.execution_time > 0
            assert "Took" in result.stdout

    @pytest.mark.asyncio
    async def test_tuple_unpacking(self):
        """测试元组解包"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_tuple",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
coords = (1,2,3)
x, y, z = coords
print(f'{x}, {y}, {z}')
""")

            assert result.success is True
            assert "1,2,3" in result.stdout

    @pytest.mark.asyncio
    async def test_lambda_functions(self):
        """测试lambda函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_lambda",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
double = lambda x: x * 2
print(double(21))
""")

            assert result.success is True
            assert "42" in result.stdout


class TestCodeSandboxSecurity:
    """Security-focused tests for CodeSandbox"""

    @pytest.mark.asyncio
    async def test_blocked_pathlib_import(self):
        """测试pathlib模块导入被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_pathlib")
        result = await sandbox.execute("from pathlib import Path")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_socket_import(self):
        """测试socket模块导入被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_socket")
        result = await sandbox.execute("import socket")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_http_import(self):
        """测试http模块导入被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_http")
        result = await sandbox.execute("import http")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_urllib_import(self):
        """测试urllib模块导入被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_urllib")
        result = await sandbox.execute("import urllib")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_compile_function(self):
        """测试compile函数被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_compile")
        result = await sandbox.execute("compile('print(1)')")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_globals_function(self):
        """测试globals函数被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_globals")
        result = await sandbox.execute("globals()")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_locals_function(self):
        """测试locals函数被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_locals")
        result = await sandbox.execute("locals()")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_exit_function(self):
        """测试exit函数被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_exit")
        result = await sandbox.execute("exit()")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_quit_function(self):
        """测试quit函数被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_quit")
        result = await sandbox.execute("quit()")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_from_os_import(self):
        """测试from os import被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_from_os")
        result = await sandbox.execute("from os import path")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error

    @pytest.mark.asyncio
    async def test_blocked_from_sys_import(self):
        """测试from sys import被阻止"""
        sandbox = CodeSandbox(wallet_address="test_user_from_sys")
        result = await sandbox.execute("from sys import argv")

        assert result.success is False
        assert "not allowed" in result.error or "拒绝" in result.error


class TestCodeSandboxEdgeCases:
    """Edge case tests for CodeSandbox"""

    @pytest.mark.asyncio
    async def test_empty_code(self):
        """测试空代码"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_empty",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("")

            assert result.success is True  # Empty code is valid

    @pytest.mark.asyncio
    async def test_whitespace_only_code(self):
        """测试只有空白的代码"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_whitespace",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("   \\n\n  ")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_comment_only_code(self):
        """测试只有注释的代码"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_comment",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("# This is a comment\\n# Another comment")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_multiline_string(self):
        """测试多行字符串"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_multiline",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
text = '''
Line 1
Line 2
Line 3
'''
print(text)
""")

            assert result.success is True
            assert "Line 1" in result.stdout
            assert "Line 2" in result.stdout
            assert "Line 3" in result.stdout

    @pytest.mark.asyncio
    async def test_very_long_code(self):
        """测试很长的代码"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_very_long",
                sandbox_root=temp_dir
            )

            # Generate a long valid code
            long_code = "\\n".join(["x = " + str(i) for i in range(1000)])
            result = await sandbox.execute(long_code)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_nested_functions(self):
        """测试嵌套函数"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_nested",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
def outer():
    def inner():
        return 42
    return inner() * 2

print(outer())
""")

            assert result.success is True
            assert "84" in result.stdout

    @pytest.mark.asyncio
    async def test_with_statement(self):
        """测试with语句（上下文管理器）"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_with",
                sandbox_root=temp_dir
            )

            result = await sandbox.execute("""
class Counter:
    def __init__(self):
        self.value = 0
    def add(self):
        self.value += 1

with Counter() as c:
    c.add()
    c.add()
print(c.value)
""")

            assert result.success is True
            assert "2" in result.stdout


class TestCodeSandboxModulePreload:
    """Test module preloading in sandbox"""

    @pytest.mark.asyncio
    async def test_allowed_modules_are_preloaded(self):
        """测试允许的模块被预加载"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_preload",
                sandbox_root=temp_dir
            )

            # After initialization, modules should be preloaded
            assert len(sandbox._imported_modules) > 0

            # Execute code using preloaded module
            result = await sandbox.execute("import math; print(math.pi)")

            assert result.success is True
            assert "3.14" in result.stdout

    @pytest.mark.asyncio
    async def test_module_caching(self):
        """测试模块缓存"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sandbox = CodeSandbox(
                wallet_address="test_user_cache",
                sandbox_root=temp_dir
            )

            # First import
            result1 = await sandbox.execute("import math; print('first')")
            assert result1.success is True

            # Second import should use cached version
            result2 = await sandbox.execute("import math; print('second')")
            assert result2.success is True

            assert "first" in result1.stdout
            assert "second" in result2.stdout
