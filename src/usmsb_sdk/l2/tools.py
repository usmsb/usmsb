# -*- coding: utf-8 -*-
"""
L2 Tools Framework - 工具调用框架

L2 = L1 + 记忆 + 工具调用

功能：
- Tool 基类定义
- 工具注册机制
- 工具调用和验证
- 工具描述生成
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ToolCategory(Enum):
    """工具类别"""
    SEARCH = "search"          # 搜索
    CODE = "code"              # 代码执行
    DATA = "data"             # 数据处理
    WEB = "web"               # 网页访问
    FILE = "file"              # 文件操作
    API = "api"                # API 调用
    COMPUTATION = "computation"  # 计算
    MEMORY = "memory"          # 记忆操作
    AGENT = "agent"            # Agent 操作
    CUSTOM = "custom"          # 自定义


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str  # string, number, boolean, object, array
    description: str
    required: bool = True
    default: Any = None
    enum_values: list[Any] | None = None


@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    parameters: list[ToolParameter] = field(default_factory=list)
    returns: str = ""  # 返回值描述
    examples: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    
    def to_openai_format(self) -> dict:
        """转换为 OpenAI 工具格式"""
        properties = {}
        required = []
        
        for param in self.parameters:
            param_dict = {
                "type": param.type,
                "description": param.description,
            }
            
            if param.enum_values:
                param_dict["enum"] = param.enum_values
            
            properties[param.name] = param_dict
            
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                }
            }
        }


class Tool(ABC):
    """
    工具基类
    
    所有工具必须继承此类。
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        category: ToolCategory = ToolCategory.CUSTOM,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.category = category
        self.usage_count = 0
        self.success_count = 0
        self.total_latency_ms = 0.0
        self.created_at = datetime.now().timestamp()
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            dict: 执行结果，包含:
                - success: bool
                - result: Any
                - error: str (如果有)
        """
        pass
    
    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=self.get_parameters(),
            returns=self.get_returns_description(),
        )
    
    def get_parameters(self) -> list[ToolParameter]:
        """获取参数定义（子类可重写）"""
        return []
    
    def get_returns_description(self) -> str:
        """获取返回值描述（子类可重写）"""
        return "执行结果"
    
    def record_usage(self, success: bool, latency_ms: float) -> None:
        """记录使用统计"""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.total_latency_ms += latency_ms
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count
    
    def get_avg_latency(self) -> float:
        """获取平均延迟"""
        if self.usage_count == 0:
            return 0.0
        return self.total_latency_ms / self.usage_count
    
    def validate_parameters(self, params: dict) -> tuple[bool, str]:
        """
        验证参数
        
        Returns:
            (is_valid, error_message)
        """
        for param_def in self.get_parameters():
            if param_def.required and param_def.name not in params:
                return False, f"Missing required parameter: {param_def.name}"
            
            if param_def.name in params:
                value = params[param_def.name]
                
                # 类型检查
                expected_type = param_def.type
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"{param_def.name} must be string"
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return False, f"{param_def.name} must be number"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"{param_def.name} must be boolean"
                
                # 枚举检查
                if param_def.enum_values and value not in param_def.enum_values:
                    return False, f"{param_def.name} must be one of {param_def.enum_values}"
        
        return True, ""
    
    def __repr__(self) -> str:
        return f"Tool({self.name}, category={self.category.value}, usage={self.usage_count})"


class ToolRegistry:
    """
    工具注册表
    
    管理所有可用工具。
    """
    
    def __init__(self):
        self.tools: dict[str, Tool] = {}
        self.category_index: dict[ToolCategory, list[str]] = {}
    
    def register(self, tool: Tool) -> str:
        """注册工具"""
        self.tools[tool.name] = tool
        
        # 更新类别索引
        if tool.category not in self.category_index:
            self.category_index[tool.category] = []
        if tool.name not in self.category_index[tool.category]:
            self.category_index[tool.category].append(tool.name)
        
        return tool.id
    
    def unregister(self, tool_name: str) -> bool:
        """注销工具"""
        if tool_name not in self.tools:
            return False
        
        tool = self.tools[tool_name]
        del self.tools[tool_name]
        
        # 更新索引
        if tool.category in self.category_index:
            if tool_name in self.category_index[tool.category]:
                self.category_index[tool.category].remove(tool_name)
        
        return True
    
    def get(self, tool_name: str) -> Tool | None:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def list_all(self) -> list[Tool]:
        """列出所有工具"""
        return list(self.tools.values())
    
    def list_by_category(self, category: ToolCategory) -> list[Tool]:
        """按类别列出工具"""
        tool_names = self.category_index.get(category, [])
        return [self.tools[name] for name in tool_names if name in self.tools]
    
    def get_tool_definitions(self) -> list[ToolDefinition]:
        """获取所有工具定义（用于 LLM）"""
        return [tool.get_definition() for tool in self.tools.values()]
    
    def get_openai_tools(self) -> list[dict]:
        """获取 OpenAI 格式的工具定义"""
        return [tool.get_definition().to_openai_format() for tool in self.tools.values()]
    
    def search(self, query: str) -> list[Tool]:
        """搜索工具"""
        query_lower = query.lower()
        results = []
        
        for tool in self.tools.values():
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower()):
                results.append(tool)
        
        return results
    
    def get_statistics(self) -> dict:
        """获取统计"""
        total_usage = sum(t.usage_count for t in self.tools.values())
        total_success = sum(t.success_count for t in self.tools.values())
        
        return {
            "tool_count": len(self.tools),
            "total_usage": total_usage,
            "total_success": total_success,
            "overall_success_rate": total_success / total_usage if total_usage > 0 else 0.0,
            "by_category": {
                cat.value: len(tools)
                for cat, tools in [
                    (cat, self.list_by_category(cat))
                    for cat in ToolCategory
                ]
            },
        }
    
    def __repr__(self) -> str:
        return f"ToolRegistry(tools={len(self.tools)})"


# ========== 内置工具示例 ==========

class CalculatorTool(Tool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算",
            category=ToolCategory.COMPUTATION,
        )
    
    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="expression",
                type="string",
                description="数学表达式，如 '2 + 3 * 4'",
                required=True,
            ),
        ]
    
    def get_returns_description(self) -> str:
        return "计算结果数字"
    
    async def execute(self, **kwargs) -> dict:
        expression = kwargs.get("expression", "")
        
        try:
            # 安全评估（只允许基本运算）
            allowed_chars = set("0123456789+-*/(). ")
            if not all(c in allowed_chars for c in expression):
                return {"success": False, "error": "Invalid characters in expression"}
            
            result = eval(expression)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


class SearchTool(Tool):
    """搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="搜索互联网获取信息",
            category=ToolCategory.SEARCH,
        )
    
    def get_parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type="number",
                description="最大结果数",
                required=False,
                default=5,
            ),
        ]
    
    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)
        
        # 简化实现，实际会调用真实搜索 API
        return {
            "success": True,
            "result": {
                "query": query,
                "results": [
                    {"title": f"Result {i+1} for {query}", "url": f"https://example.com/{i}"}
                    for i in range(max_results)
                ]
            }
        }


def create_tool_registry() -> ToolRegistry:
    """创建预配置的工具注册表"""
    registry = ToolRegistry()
    
    # 注册内置工具
    registry.register(CalculatorTool())
    registry.register(SearchTool())
    
    return registry
