"""
MCP Gateway - MCP 网关

MCP = Model Context Protocol
MCP 网关是 Agent 调用外部工具的统一入口。

功能：
- 工具调用
- 工具发现
- 调用统计
- 错误处理
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class CallStatus(Enum):
    """调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


@dataclass
class ToolCall:
    """工具调用记录"""
    id: str
    tool_id: str
    tool_name: str
    agent_id: str
    input_params: dict
    output: Any = None
    error: str | None = None
    status: CallStatus = CallStatus.SUCCESS
    duration_ms: float = 0.0
    cost: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class MCPCallError(Exception):
    """MCP 调用错误"""
    pass


class MCPGateway:
    """
    MCP 网关
    
    统一管理工具的注册、发现和调用。
    
    使用方式：
    ```python
    gateway = MCPGateway()
    
    # 注册工具
    gateway.register_tool(my_tool)
    
    # 调用工具
    result = gateway.call_tool(
        tool_name="web_search",
        params={"query": "AI news"},
        agent_id="agent_001"
    )
    
    # 发现工具
    tools = gateway.discover_tools(query="search")
    ```
    """
    
    def __init__(self, registry=None):
        """
        初始化 MCP 网关
        
        Args:
            registry: MCPRegistry 实例
        """
        from .mcp_registry import MCPRegistry
        self.registry = registry or MCPRegistry()
        
        # 调用处理函数：tool_name -> callable
        self._handlers: dict[str, Callable] = {}
        
        # 调用记录
        self._call_history: list[ToolCall] = []
        
        # 默认超时（毫秒）
        self._default_timeout_ms = 30000
    
    def register_handler(
        self,
        tool_name: str,
        handler: Callable,
        override: bool = False
    ) -> bool:
        """
        注册工具处理函数
        
        Args:
            tool_name: 工具名称
            handler: 处理函数
            override: 是否覆盖已存在的处理函数
            
        Returns:
            bool: 是否成功
        """
        if tool_name in self._handlers and not override:
            return False
        
        self._handlers[tool_name] = handler
        return True
    
    def register_tool(
        self,
        tool,
        handler: Callable | None = None,
        auto_register_handler: bool = True
    ) -> bool:
        """
        注册工具
        
        Args:
            tool: MCPTool 实例
            handler: 处理函数（可选）
            auto_register_handler: 是否自动注册处理函数
            
        Returns:
            bool: 是否成功
        """
        # 注册到 registry
        success = self.registry.register(tool)
        
        if not success:
            return False
        
        # 注册处理函数
        if handler and auto_register_handler:
            self.register_handler(tool.name, handler)
        
        return True
    
    def call_tool(
        self,
        tool_name: str,
        params: dict,
        agent_id: str,
        timeout_ms: int | None = None,
        skip_cost: bool = False
    ) -> Any:
        """
        调用工具
        
        Args:
            tool_name: 工具名称
            params: 输入参数
            agent_id: 调用方 Agent ID
            timeout_ms: 超时时间（毫秒）
            skip_cost: 是否跳过费用计算
            
        Returns:
            Any: 工具输出
            
        Raises:
            MCPCallError: 调用失败
        """
        import time
        
        # 获取工具
        tool = self.registry.get_by_name(tool_name)
        if not tool:
            raise MCPCallError(f"Tool not found: {tool_name}")
        
        # 获取处理函数
        handler = self._handlers.get(tool_name)
        if not handler:
            raise MCPCallError(f"Tool handler not registered: {tool_name}")
        
        # 创建调用记录
        call_id = str(uuid.uuid4())
        
        # 验证参数
        self._validate_params(tool, params)
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行调用
        try:
            output = handler(**params)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录调用
            call_record = ToolCall(
                id=call_id,
                tool_id=tool.id,
                tool_name=tool_name,
                agent_id=agent_id,
                input_params=params,
                output=output,
                status=CallStatus.SUCCESS,
                duration_ms=duration_ms,
                cost=0.0 if skip_cost else tool.cost_per_call
            )
            self._call_history.append(call_record)
            
            return output
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # 记录错误
            call_record = ToolCall(
                id=call_id,
                tool_id=tool.id,
                tool_name=tool_name,
                agent_id=agent_id,
                input_params=params,
                error=str(e),
                status=CallStatus.FAILED,
                duration_ms=duration_ms,
                cost=0.0
            )
            self._call_history.append(call_record)
            
            raise MCPCallError(f"Tool call failed: {e}")
    
    def call_tool_async(
        self,
        tool_name: str,
        params: dict,
        agent_id: str,
        callback: Callable[[Any], None] | None = None
    ) -> str:
        """
        异步调用工具
        
        Args:
            tool_name: 工具名称
            params: 输入参数
            agent_id: 调用方 Agent ID
            callback: 回调函数
            
        Returns:
            str: 调用 ID
        """
        import threading
        
        call_id = str(uuid.uuid4())
        
        def run():
            try:
                result = self.call_tool(tool_name, params, agent_id)
                if callback:
                    callback(result)
            except MCPCallError as e:
                if callback:
                    callback(None)
        
        thread = threading.Thread(target=run)
        thread.start()
        
        return call_id
    
    def discover_tools(
        self,
        query: str = "",
        category: str | None = None,
        capabilities: list[str] | None = None,
        limit: int = 10
    ) -> list:
        """
        发现工具
        
        Args:
            query: 搜索关键词
            category: 类别
            capabilities: 能力需求
            limit: 返回数量
            
        Returns:
            list: 匹配的工具列表
        """
        from .mcp_registry import ToolCategory
        
        cat = None
        if category:
            try:
                cat = ToolCategory(category)
            except ValueError:
                pass
        
        return self.registry.discover(
            query=query,
            category=cat,
            capabilities=capabilities,
            limit=limit
        )
    
    def get_tool_schema(self, tool_name: str) -> dict | None:
        """获取工具的 Schema"""
        tool = self.registry.get_by_name(tool_name)
        if not tool:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": {
                "type": tool.input_schema.type,
                "properties": tool.input_schema.properties,
                "required": tool.input_schema.required
            },
            "output_schema": {
                "type": tool.output_schema.type,
                "properties": tool.output_schema.properties
            },
            "cost": tool.cost_per_call,
            "category": tool.category.value
        }
    
    def _validate_params(self, tool, params: dict) -> None:
        """验证参数"""
        # 检查必需参数
        for required in tool.input_schema.required:
            if required not in params:
                raise MCPCallError(f"Missing required parameter: {required}")
        
        # 检查参数类型
        for param_name, param_value in params.items():
            if param_name in tool.input_schema.properties:
                expected_type = tool.input_schema.properties[param_name].get("type")
                if expected_type:
                    self._check_type(param_name, param_value, expected_type)
    
    def _check_type(self, name: str, value: Any, expected: str) -> None:
        """检查参数类型"""
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        expected_type = type_map.get(expected)
        if expected_type and not isinstance(value, expected_type):
            raise MCPCallError(
                f"Invalid type for {name}: expected {expected}, got {type(value).__name__}"
            )
    
    def get_call_history(
        self,
        agent_id: str | None = None,
        tool_name: str | None = None,
        limit: int = 100
    ) -> list[ToolCall]:
        """
        获取调用历史
        
        Args:
            agent_id: Agent ID 过滤
            tool_name: 工具名过滤
            limit: 返回数量
            
        Returns:
            list[ToolCall]: 调用记录列表
        """
        results = self._call_history
        
        if agent_id:
            results = [c for c in results if c.agent_id == agent_id]
        
        if tool_name:
            results = [c for c in results if c.tool_name == tool_name]
        
        return results[-limit:]
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total = len(self._call_history)
        success = sum(1 for c in self._call_history if c.status == CallStatus.SUCCESS)
        failed = sum(1 for c in self._call_history if c.status == CallStatus.FAILED)
        
        total_cost = sum(c.cost for c in self._call_history)
        avg_duration = sum(c.duration_ms for c in self._call_history) / total if total > 0 else 0
        
        # 按工具分组统计
        by_tool = {}
        for call in self._call_history:
            if call.tool_name not in by_tool:
                by_tool[call.tool_name] = {"count": 0, "success": 0, "failed": 0}
            by_tool[call.tool_name]["count"] += 1
            if call.status == CallStatus.SUCCESS:
                by_tool[call.tool_name]["success"] += 1
            else:
                by_tool[call.tool_name]["failed"] += 1
        
        return {
            "total_calls": total,
            "success": success,
            "failed": failed,
            "success_rate": success / total if total > 0 else 0,
            "total_cost": total_cost,
            "average_duration_ms": avg_duration,
            "tools_registered": len(self.registry.get_all_tools()),
            "handlers_registered": len(self._handlers),
            "by_tool": by_tool
        }
