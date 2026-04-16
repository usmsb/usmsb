"""
敏感信息处理模块

提供敏感信息的注册、检测、验证能力
"""

from .registry import (
    SensitiveInfoHandler,
    SensitiveInfoMatch,
    SensitiveInfoRegistry,
    SensitiveInfoType,
    clear_sensitive_info_registry,
    get_sensitive_info_registry,
    register_sensitive_info_handler,
)

__all__ = [
    "SensitiveInfoHandler",
    "SensitiveInfoRegistry",
    "SensitiveInfoType",
    "SensitiveInfoMatch",
    "get_sensitive_info_registry",
    "register_sensitive_info_handler",
    "clear_sensitive_info_registry",
]
