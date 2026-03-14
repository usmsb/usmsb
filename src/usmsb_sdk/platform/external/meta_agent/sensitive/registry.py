"""
敏感信息处理器注册表

提供通用的敏感信息处理架构，支持动态注册不同平台/服务的敏感信息处理逻辑。
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from re import Pattern
from typing import Any

logger = logging.getLogger(__name__)


class SensitiveInfoType(Enum):
    """敏感信息类型枚举"""

    API_KEY = "api_key"
    PASSWORD = "password"
    TOKEN = "token"
    CREDENTIAL = "credential"
    CUSTOM = "custom"


@dataclass
class SensitiveInfoMatch:
    """敏感信息匹配结果"""

    info_type: str
    value: str
    source: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SensitiveInfoHandler(ABC):
    """
    敏感信息处理器抽象基类

    所有特定平台/服务的敏感信息处理器都应该继承此类。
    通过注册表注册后，Agent 可以动态发现和使用不同类型的敏感信息。
    """

    def __init__(
        self,
        name: str,
        description: str,
    ):
        self.name = name
        self.description = description

    @abstractmethod
    def get_keywords(self) -> list[str]:
        """
        获取用于检索的关键词列表

        Returns:
            关键词列表，用于在历史对话中搜索
        """
        pass

    @abstractmethod
    def get_patterns(self) -> dict[str, Pattern]:
        """
        获取用于正则匹配的模式

        Returns:
            字典，key 为模式名称，value 为正则表达式
        """
        pass

    @abstractmethod
    def get_info_type(self) -> str:
        """
        获取此处理器处理的信息类型

        Returns:
            信息类型标识符
        """
        pass

    def validate_format(self, value: str) -> bool:
        """
        验证值是否符合此处理器的格式

        Args:
            value: 要验证的值

        Returns:
            是否符合格式
        """
        patterns = self.get_patterns()
        for _pattern_name, pattern in patterns.items():
                try:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True
                except re.error:
                    continue
        return False

    async def validate_with_api(
        self,
        value: str,
        api_client: Any | None = None
    ) -> bool:
        """
        通过 API 验证值是否有效（可选实现)

        Args:
            value: 要验证的值
            api_client: API 客户端（可选）

        Returns:
            值是否有效，默认返回 None 表示不支持 API 验证
        """
        return False  # 默认不支持 API 验证

    def get_prompt_hint(self) -> str:
        """
        获取用于 LLM Prompt 的格式提示（可选)

        注意：此方法返回的内容会被添加到 LLM Prompt 中，
        用于帮助 LLM 识别特定格式的敏感信息。

        默认返回空字符串，避免泄露敏感信息格式。

        Returns:
            格式提示字符串，如果不需要提示则返回空字符串
        """
        return ""


class GenericAPIKeyHandler(SensitiveInfoHandler):
    """通用 API Key 处理器 - 不包含任何特定平台的格式"""

    def __init__(self):
        super().__init__(
            name="generic_api_key",
            description="通用 API Key 处理器，支持多种常见格式但不包含特定平台"
        )

    def get_keywords(self) -> list[str]:
        return [
            "api key",
            "apikey",
            "api_key",
            "secret key",
            "secretkey",
            "access key",
            "密钥",
            "认证",
        ]

    def get_patterns(self) -> dict[str, Pattern]:
        return {
            # 通用 UUID 格式 (不特定于任何平台)
            "uuid_format": r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
            # Bearer token 格式
            "bearer_token": r"Bearer\s+[a-zA-Z0-9_\-\.]+",
            # 通用 API Key 艹值匹配
            "key_assignment": r"(?:api[_-]?key|secret[_-]?key|access[_-]?key)\s*[是为：:\s]+\s*\S+",
        }

    def get_info_type(self) -> str:
        return SensitiveInfoType.API_KEY.value

    def get_prompt_hint(self) -> str:
        # 不提供特定格式提示
        return ""


class PasswordHandler(SensitiveInfoHandler):
    """密码处理器"""

    def __init__(self):
        super().__init__(
            name="password",
            description="密码处理处理器"
        )

    def get_keywords(self) -> list[str]:
        return [
            "password",
            "密码",
            "passwd",
            "pwd",
        ]

    def get_patterns(self) -> dict[str, Pattern]:
        return {
            "password_assignment": r"(?:密码|password|passwd|pwd)\s*[是为：:\s]+\s*\S+",
        }

    def get_info_type(self) -> str:
        return SensitiveInfoType.PASSWORD.value


    def get_prompt_hint(self) -> str:
        return ""


class TokenHandler(SensitiveInfoHandler):
    """认证令牌处理器"""

    def __init__(self):
        super().__init__(
            name="token",
            description="认证令牌处理器"
        )

    def get_keywords(self) -> list[str]:
        return [
            "token",
            "令牌",
            "auth",
            "bearer",
        ]

    def get_patterns(self) -> dict[str, Pattern]:
        return {
            "bearer": r"Bearer\s+[a-zA-Z0-9_\-\.]+",
            "token_assignment": r"token\s*[是为：:\s]+\s*[a-zA-Z0-9_\-]+",
        }

    def get_info_type(self) -> str:
        return SensitiveInfoType.TOKEN.value


class AccountHandler(SensitiveInfoHandler):
    """账号处理器"""

    def __init__(self):
        super().__init__(
            name="account",
            description="账号信息处理器"
        )

    def get_keywords(self) -> list[str]:
        return [
            "account",
            "账号",
            "账户",
            "username",
            "用户名",
            "login",
            "登录",
        ]

    def get_patterns(self) -> dict[str, Pattern]:
        return {
            "account_assignment": r"(?:账号|账户|username|用户名)\s*[是为：:\s]+\s*\S+",
        }

    def get_info_type(self) -> str:
        return SensitiveInfoType.CREDENTIAL.value


class SensitiveInfoRegistry:
    """
    敏感信息注册表

    管理所有敏感信息处理器，提供统一的接口。
    支持动态注册自定义处理器，无需修改核心代码。
    """

    def __init__(self):
        self._handlers: dict[str, SensitiveInfoHandler] = {}
        self._initialized = False

    def register(self, handler: SensitiveInfoHandler) -> None:
        """
        注册敏感信息处理器

        Args:
            handler: 处理器实例
        """
        self._handlers[handler.name] = handler
        logger.info(f"Registered sensitive info handler: {handler.name}")

    def unregister(self, name: str) -> None:
        """
        注销敏感信息处理器

        Args:
            name: 处理器名称
        """
        if name in self._handlers:
            del self._handlers[name]
            logger.info(f"Unregistered sensitive info handler: {name}")

    def get_handler(self, name: str) -> SensitiveInfoHandler | None:
        """获取指定处理器"""
        return self._handlers.get(name)

    def get_all_handlers(self) -> list[SensitiveInfoHandler]:
        """获取所有处理器"""
        return list(self._handlers.values())

    def get_all_keywords(self) -> list[str]:
        """
        获取所有处理器的关键词

        Returns:
            所有关键词列表（去重）
        """
        keywords = set()
        for handler in self._handlers.values():
            keywords.update(handler.get_keywords())
        return list(keywords)

    def get_all_patterns(self) -> dict[str, Pattern]:
        """
        获取所有处理器的正则模式

        Returns:
            所有正则模式的字典
        """
        patterns = {}
        for handler in self._handlers.values():
                for name, pattern in handler.get_patterns().items():
                    patterns[f"{handler.name}_{name}"] = pattern
        return patterns

    def get_all_prompt_hints(self) -> str:
        """
        获取所有处理器的 LLM 提示

        Returns:
            合并后的提示字符串
        """
        hints = []
        for handler in self._handlers.values():
            hint = handler.get_prompt_hint()
            if hint:
                hints.append(hint)
        return "\n".join(hints) if hints else ""

    def detect_info_type(self, value: str) -> str | None:
        """
        检测值的敏感信息类型

        Args:
            value: 要检测的值

        Returns:
            信息类型，如果无法识别则返回 None
        """
        for handler in self._handlers.values():
            if handler.validate_format(value):
                return handler.get_info_type()
        return None

    def extract_from_content(self, content: str) -> list[SensitiveInfoMatch]:
        """
        从内容中提取所有敏感信息

        Args:
            content: 要搜索的内容

        Returns:
            匹配结果列表
        """
        matches = []
        patterns = self.get_all_patterns()

        for pattern_name, pattern in patterns.items():
            try:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    value = match.group(0)
                    info_type = self.detect_info_type(value)
                    if info_type:
                        matches.append(SensitiveInfoMatch(
                            info_type=info_type,
                            value=value,
                            source="regex",
                            confidence=1.0,
                            metadata={"pattern": pattern_name}
                        ))
            except re.error:
                continue
        return matches

    def initialize_defaults(self) -> None:
        """
        初始化默认的处理器

        注册通用的敏感信息处理器
        """
        if self._initialized:
            return

        # 注册通用处理器
        self.register(GenericAPIKeyHandler())
        self.register(PasswordHandler())
        self.register(TokenHandler())
        self.register(AccountHandler())

        self._initialized = True
        logger.info("Initialized default sensitive info handlers")

    @classmethod
    def create_with_defaults(cls) -> "SensitiveInfoRegistry":
        """
        工厂方法：创建并初始化带有默认处理器的注册表

        Returns:
            初始化后的注册表实例
        """
        registry = cls()
        registry.initialize_defaults()
        return registry


# 全局注册表实例（延迟初始化)
_sensitive_info_registry: SensitiveInfoRegistry | None = None


def get_sensitive_info_registry() -> SensitiveInfoRegistry:
    """
    获取全局敏感信息注册表实例

    使用延迟初始化模式，首次访问时才创建实例。

    Returns:
            全局敏感信息注册表实例
    """
    global _sensitive_info_registry
    if _sensitive_info_registry is None:
        _sensitive_info_registry = SensitiveInfoRegistry.create_with_defaults()
    return _sensitive_info_registry


def register_sensitive_info_handler(handler: SensitiveInfoHandler) -> None:
    """
    注册自定义敏感信息处理器

    Args:
        handler: 处理器实例
    """
    registry = get_sensitive_info_registry()
    registry.register(handler)


def clear_sensitive_info_registry() -> None:
    """
    清除全局注册表（主要用于测试）
    """
    global _sensitive_info_registry
    _sensitive_info_registry = None
