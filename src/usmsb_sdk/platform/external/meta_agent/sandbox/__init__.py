"""
代码执行沙箱模块

提供安全的 Python 代码执行环境，用于多用户隔离场景。
"""

from .code_sandbox import CodeSandbox, SandboxResult

__all__ = ['CodeSandbox', 'SandboxResult']
