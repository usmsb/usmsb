"""
Tools Registry - 工具注册表
"""

import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Tool:
    """工具定义"""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable,
        required_permissions: Optional[List[str]] = None,
        security_level: str = "low",  # low, medium, high
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.required_permissions = required_permissions or []
        self.security_level = security_level

    async def execute(self, **kwargs) -> Any:
        return await self.handler(**kwargs)

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
    """工具注册表"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

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

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        # 将关键字参数包装成 params 字典传给 handler
        return await tool.execute(params=kwargs)
