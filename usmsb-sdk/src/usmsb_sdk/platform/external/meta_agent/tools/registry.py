"""
Tools Registry - 工具注册表

支持 UserSession 上下文的多用户工具执行。
"""

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from ..session.user_session import UserSession

logger = logging.getLogger(__name__)


class Tool:
    """工具定义

    支持两种模式的工具处理器：
    1. 旧模式：handler(params: dict) -> Dict
    2. 新模式：handler(session: UserSession, params: dict) -> Dict

    新模式下工具可以访问用户的隔离资源（workspace、sandbox、browser_context 等）。
    """

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        required_permissions: Optional[List[str]] = None,
        security_level: str = "low",  # low, medium, high
        requires_session: bool = False,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.required_permissions = required_permissions or []
        self.security_level = security_level
        self.requires_session = requires_session

    async def execute(self, session: Optional["UserSession"] = None, **kwargs) -> Any:
        """执行工具

        Args:
            session: 用户会话上下文（如果工具需要）
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        if self.requires_session:
            if session is None:
                raise RuntimeError(f"Tool {self.name} requires a UserSession")
            return await self.handler(session, params=kwargs)
        else:
            return await self.handler(params=kwargs)

    def to_function_schema(self, provider: str = "anthropic") -> Dict[str, Any]:
        """转换为 Function Calling 的 JSON Schema 格式

        Args:
            provider: LLM提供商 (anthropic/openai/ollama)
        """
        if provider == "anthropic":
            # Anthropic Claude 格式
            return {
                "name": self.name,
                "description": self.description,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
            }
        else:
            # OpenAI 格式 (默认)
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            }


class ToolRegistry:
    """工具注册表

    管理工具的注册和执行，支持 UserSession 上下文。
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (requires_session={tool.requires_session})")

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """列出所有工具"""
        return [{"name": t.name, "description": t.description} for t in self.tools.values()]

    def get_tools_schema(self, provider: str = "anthropic") -> List[Dict[str, Any]]:
        """获取所有工具的 Function Calling Schema

        Args:
            provider: LLM提供商 (anthropic/openai/ollama)
        """
        return [t.to_function_schema(provider) for t in self.tools.values()]

    async def execute(
        self,
        tool_name: str,
        session: Optional["UserSession"] = None,
        **kwargs
    ) -> Any:
        """执行工具

        Args:
            tool_name: 工具名称
            session: 用户会话上下文（如果工具需要）
            **kwargs: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 如果工具不存在
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        return await tool.execute(session=session, **kwargs)

    def get_tools_requiring_session(self) -> List[str]:
        """获取所有需要 UserSession 的工具名称"""
        return [name for name, tool in self.tools.items() if tool.requires_session]
