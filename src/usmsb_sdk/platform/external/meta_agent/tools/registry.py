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
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.required_permissions = required_permissions or []
        self.security_level = security_level
        self.requires_session = requires_session
        self.parameters = parameters or {}

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
                raise RuntimeError(f"Tool {self.name} requires a UserSession but none was provided")
            # 需要 session 的工具：handler(session, params=dict)
            return await self.handler(session, params=kwargs)
        else:
            # 不需要 session 的工具：handler(params=dict)
            # 统一传递 params 字典格式
            return await self.handler(params=kwargs)

    def to_function_schema(self, provider: str = "anthropic") -> Dict[str, Any]:
        """转换为 Function Calling 的 JSON Schema 格式

        Args:
            provider: LLM提供商 (anthropic/openai/ollama/minimax)
        """
        if provider in ("anthropic", "minimax"):
            # Anthropic/MiniMax 兼容格式 - 使用 type: function
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": self._get_parameters(),
                        "required": self._get_required_parameters(),
                    },
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
                        "properties": self._get_parameters(),
                        "required": self._get_required_parameters(),
                    },
                },
            }

    def _get_parameters(self) -> Dict[str, Any]:
        """
        获取工具参数的 properties 字典

        设计初衷：
        MiniMax API 要求每个工具必须有有效的 parameters.properties 字段。
        这个方法确保返回的始终是有效的 properties 字典，而不是完整的 schema。

        常见错误格式：
        - parameters={'type': 'object'}  # 缺少 properties
        - parameters={}  # 空
        - parameters={'type': 'object', 'properties': {}}  # properties 为空

        正确格式：
        - parameters={'type': 'object', 'properties': {'key': {...}}}
        或者只传 properties：
        - parameters={'key': {'type': 'string', 'description': '...'}}
        """
        # 检查 self.parameters 是否是有效的 properties 格式
        if self.parameters:
            # 情况1：完整的 JSON Schema 格式 {'type': 'object', 'properties': {...}}
            if isinstance(self.parameters, dict):
                if "properties" in self.parameters:
                    # 提取 properties 字段
                    props = self.parameters.get("properties", {})
                    if props and isinstance(props, dict):
                        # 过滤掉非属性字段（如 'type'）
                        valid_props = {k: v for k, v in props.items()
                                     if isinstance(v, dict) and 'type' in v}
                        if valid_props:
                            return valid_props

                # 情况2：直接的 properties 格式 {'key': {'type': 'string', ...}}
                # 检查是否所有值都是有效的属性定义
                is_direct_props = all(
                    isinstance(v, dict) and 'type' in v
                    for v in self.parameters.values()
                ) if self.parameters else False

                if is_direct_props:
                    return self.parameters

                # 情况3：无效格式（如 {'type': 'object'}），忽略并使用预定义

        # 使用预定义的参数映射
        params_map = {
            "execute_command": {
                "command": {"type": "string", "description": "要执行的命令行命令"},
                "cwd": {"type": "string", "description": "工作目录路径"},
                "timeout": {"type": "integer", "description": "超时时间（秒）"},
            },
            "run_program": {
                "program_path": {"type": "string", "description": "程序或脚本的路径"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "命令行参数"},
                "cwd": {"type": "string", "description": "工作目录"},
                "timeout": {"type": "integer", "description": "超时时间"},
            },
            "read_file": {
                "path": {"type": "string", "description": "要读取的文件路径"},
                "offset": {"type": "integer", "description": "起始位置"},
                "limit": {"type": "integer", "description": "读取字节数"},
                "encoding": {"type": "string", "description": "文件编码"},
            },
            "write_file": {
                "path": {"type": "string", "description": "要写入的文件路径"},
                "content": {"type": "string", "description": "文件内容"},
                "mode": {"type": "string", "description": "写入模式 (w/a)"},
            },
            "list_directory": {
                "path": {"type": "string", "description": "目录路径"},
                "show_hidden": {"type": "boolean", "description": "是否显示隐藏文件"},
                "recursive": {"type": "boolean", "description": "是否递归列出"},
                "pattern": {"type": "string", "description": "文件匹配模式"},
            },
            "create_directory": {
                "path": {"type": "string", "description": "要创建的目录路径"},
                "parents": {"type": "boolean", "description": "是否创建父目录"},
            },
            "delete_file": {
                "path": {"type": "string", "description": "要删除的文件或目录路径"},
            },
            "search_files": {
                "path": {"type": "string", "description": "搜索目录"},
                "pattern": {"type": "string", "description": "文件匹配模式"},
                "max_results": {"type": "integer", "description": "最大结果数"},
                "recursive": {"type": "boolean", "description": "是否递归搜索"},
            },
            "get_file_info": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "copy_file": {
                "source": {"type": "string", "description": "源文件路径"},
                "destination": {"type": "string", "description": "目标文件路径"},
            },
            "move_file": {
                "source": {"type": "string", "description": "源文件路径"},
                "destination": {"type": "string", "description": "目标文件路径"},
            },
        }

        # 尝试从预定义映射获取
        params = params_map.get(self.name)
        if params:
            return params

        # 如果没有预定义参数，返回默认的 input 参数
        # 这是 MiniMax API 要求的：每个工具至少需要一个参数
        return {"input": {"type": "string", "description": f"{self.name}的输入参数"}}

    def _get_required_parameters(self) -> List[str]:
        """获取必需的参数列表"""
        if self.parameters and "required" in self.parameters:
            return self.parameters.get("required", [])

        required_map = {
            "execute_command": ["command"],
            "run_program": ["program_path"],
            "read_file": ["path"],
            "write_file": ["path", "content"],
            "list_directory": [],
            "create_directory": ["path"],
            "delete_file": ["path"],
            "search_files": [],
            "get_file_info": ["path"],
            "copy_file": ["source", "destination"],
            "move_file": ["source", "destination"],
        }
        return required_map.get(self.name, [])


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
        self, tool_name: str, session: Optional["UserSession"] = None, **kwargs
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
