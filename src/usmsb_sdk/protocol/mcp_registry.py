"""
MCP Registry - 工具注册与管理

MCP = Model Context Protocol
工具注册中心，用于管理 Agent 可以调用的外部工具。

功能：
- 工具注册
- 工具发现
- 工具分类
- 工具更新
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ToolCategory(Enum):
    """工具类别"""
    COMPUTATION = "computation"           # 计算
    DATA = "data"                       # 数据处理
    SEARCH = "search"                   # 搜索
    API = "api"                        # API 调用
    FILE = "file"                      # 文件处理
    COMMUNICATION = "communication"       # 通信
    UTILITY = "utility"                # 工具类


@dataclass
class ToolSchema:
    """工具输入/输出 Schema"""
    type: str = "object"
    properties: dict = field(default_factory=dict)
    required: list[str] = field(default_factory=list)


@dataclass
class MCPTool:
    """
    MCP 工具定义
    
    属性：
    - id: 工具唯一 ID
    - name: 工具名称
    - description: 工具描述
    - category: 工具类别
    - input_schema: 输入参数定义
    - output_schema: 输出结果定义
    - provider: 提供者
    - cost: 调用费用
    - capabilities: 关联的能力
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    input_schema: ToolSchema = field(default_factory=ToolSchema)
    output_schema: ToolSchema = field(default_factory=ToolSchema)
    provider: str = ""  # 工具提供者
    version: str = "1.0"
    cost_per_call: float = 0.0  # 每次调用费用 (VIBE)
    latency_ms: float = 100.0  # 预估延迟 (毫秒)
    capabilities: list[str] = field(default_factory=list)  # 关联能力
    tags: list[str] = field(default_factory=list)  # 标签
    is_async: bool = False  # 是否异步调用
    requires_auth: bool = False  # 是否需要认证
    auth_config: dict = field(default_factory=dict)  # 认证配置
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "input_schema": {
                "type": self.input_schema.type,
                "properties": self.input_schema.properties,
                "required": self.input_schema.required
            },
            "output_schema": {
                "type": self.output_schema.type,
                "properties": self.output_schema.properties
            },
            "provider": self.provider,
            "version": self.version,
            "cost_per_call": self.cost_per_call,
            "latency_ms": self.latency_ms,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_async": self.is_async,
            "requires_auth": self.requires_auth,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


class MCPRegistry:
    """
    MCP 工具注册表
    
    使用方式：
    ```python
    registry = MCPRegistry()
    
    # 注册工具
    tool = MCPTool(
        name="web_search",
        description="搜索互联网",
        category=ToolCategory.SEARCH
    )
    registry.register(tool)
    
    # 发现工具
    tools = registry.discover(query="search")
    
    # 获取工具
    tool = registry.get_tool("tool_id")
    ```
    """
    
    def __init__(self):
        # 工具存储
        self._tools: dict[str, MCPTool] = {}
        
        # 名称索引
        self._name_index: dict[str, str] = {}  # name -> tool_id
        
        # 类别索引
        self._category_index: dict[ToolCategory, list[str]] = {}
        
        # 能力索引
        self._capability_index: dict[str, list[str]] = {}  # capability -> [tool_id, ...]
        
        # 标签索引
        self._tag_index: dict[str, list[str]] = {}  # tag -> [tool_id, ...]
    
    def register(self, tool: MCPTool) -> bool:
        """
        注册工具
        
        Args:
            tool: MCP 工具
            
        Returns:
            bool: 是否成功
        """
        # 检查名称冲突
        if tool.name in self._name_index:
            return False
        
        # 添加索引
        self._tools[tool.id] = tool
        self._name_index[tool.name] = tool.id
        
        # 类别索引
        if tool.category not in self._category_index:
            self._category_index[tool.category] = []
        self._category_index[tool.category].append(tool.id)
        
        # 能力索引
        for cap in tool.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = []
            self._capability_index[cap].append(tool.id)
        
        # 标签索引
        for tag in tool.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(tool.id)
        
        tool.updated_at = datetime.now().timestamp()
        
        return True
    
    def unregister(self, tool_id: str) -> bool:
        """
        注销工具
        
        Args:
            tool_id: 工具 ID
            
        Returns:
            bool: 是否成功
        """
        if tool_id not in self._tools:
            return False
        
        tool = self._tools[tool_id]
        
        # 清理索引
        del self._name_index[tool.name]
        
        if tool.category in self._category_index:
            if tool_id in self._category_index[tool.category]:
                self._category_index[tool.category].remove(tool_id)
        
        for cap in tool.capabilities:
            if cap in self._capability_index:
                if tool_id in self._capability_index[cap]:
                    self._capability_index[cap].remove(tool_id)
        
        for tag in tool.tags:
            if tag in self._tag_index:
                if tool_id in self._tag_index[tag]:
                    self._tag_index[tag].remove(tool_id)
        
        del self._tools[tool_id]
        
        return True
    
    def get_tool(self, tool_id: str) -> MCPTool | None:
        """获取工具"""
        return self._tools.get(tool_id)
    
    def get_by_name(self, name: str) -> MCPTool | None:
        """通过名称获取工具"""
        tool_id = self._name_index.get(name)
        if tool_id:
            return self._tools.get(tool_id)
        return None
    
    def discover(
        self,
        query: str = "",
        category: ToolCategory | None = None,
        capabilities: list[str] | None = None,
        min_cost: float = 0,
        max_cost: float = float('inf'),
        limit: int = 10
    ) -> list[MCPTool]:
        """
        发现工具
        
        Args:
            query: 搜索关键词
            category: 类别过滤
            capabilities: 能力过滤
            min_cost: 最低费用
            max_cost: 最高费用
            limit: 返回数量
            
        Returns:
            list[MCPTool]: 匹配的工具列表
        """
        candidates = set()
        
        # 能力过滤
        if capabilities:
            for cap in capabilities:
                if cap in self._capability_index:
                    candidates.update(self._capability_index[cap])
        else:
            candidates = set(self._tools.keys())
        
        # 类别过滤
        if category:
            if category in self._category_index:
                candidates &= set(self._category_index[category])
            else:
                return []
        
        # 费用过滤
        if min_cost > 0 or max_cost < float('inf'):
            filtered = []
            for tool_id in candidates:
                tool = self._tools[tool_id]
                if min_cost <= tool.cost_per_call <= max_cost:
                    filtered.append(tool_id)
            candidates = filtered
        
        # 关键词过滤
        if query:
            query_lower = query.lower()
            filtered = []
            for tool_id in candidates:
                tool = self._tools[tool_id]
                if (query_lower in tool.name.lower() or
                    query_lower in tool.description.lower() or
                    any(query_lower in tag.lower() for tag in tool.tags)):
                    filtered.append(tool_id)
            candidates = filtered
        
        # 转换为工具对象
        results = [self._tools[tid] for tid in candidates if tid in self._tools]
        
        # 按费用排序（优先便宜的工具）
        results.sort(key=lambda t: t.cost_per_call)
        
        return results[:limit]
    
    def get_by_category(self, category: ToolCategory) -> list[MCPTool]:
        """获取某类别的所有工具"""
        tool_ids = self._category_index.get(category, [])
        return [self._tools[tid] for tid in tool_ids if tid in self._tools]
    
    def get_all_tools(self) -> list[MCPTool]:
        """获取所有工具"""
        return list(self._tools.values())
    
    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total = len(self._tools)
        by_category = {}
        total_cost = 0.0
        
        for tool in self._tools.values():
            cat = tool.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
            total_cost += tool.cost_per_call
        
        return {
            "total_tools": total,
            "by_category": by_category,
            "total_capabilities": len(self._capability_index),
            "average_cost": total_cost / total if total > 0 else 0,
        }


class MCPToolBuilder:
    """
    MCP 工具构建器
    
    方便创建标准化的 MCP 工具。
    
    使用方式：
    ```python
    builder = MCPToolBuilder()
    
    tool = (builder
        .name("web_search")
        .description("Search the web")
        .category(ToolCategory.SEARCH)
        .input_prop("query", "string", "Search query")
        .input_required("query")
        .output_prop("results", "array", "Search results")
        .cost(0.01)
        .build())
    ```
    """
    
    def __init__(self):
        self._name = ""
        self._description = ""
        self._category = ToolCategory.UTILITY
        self._provider = ""
        self._input_props = {}
        self._input_required = []
        self._output_props = {}
        self._cost = 0.0
        self._capabilities = []
        self._tags = []
    
    def name(self, name: str) -> "MCPToolBuilder":
        self._name = name
        return self
    
    def description(self, desc: str) -> "MCPToolBuilder":
        self._description = desc
        return self
    
    def category(self, cat: ToolCategory) -> "MCPToolBuilder":
        self._category = cat
        return self
    
    def provider(self, provider: str) -> "MCPToolBuilder":
        self._provider = provider
        return self
    
    def input_prop(
        self,
        name: str,
        ptype: str,
        description: str = ""
    ) -> "MCPToolBuilder":
        self._input_props[name] = {
            "type": ptype,
            "description": description
        }
        return self
    
    def input_required(self, *props: str) -> "MCPToolBuilder":
        self._input_required = list(props)
        return self
    
    def output_prop(
        self,
        name: str,
        ptype: str,
        description: str = ""
    ) -> "MCPToolBuilder":
        self._output_props[name] = {
            "type": ptype,
            "description": description
        }
        return self
    
    def cost(self, cost: float) -> "MCPToolBuilder":
        self._cost = cost
        return self
    
    def capabilities(self, *caps: str) -> "MCPToolBuilder":
        self._capabilities = list(caps)
        return self
    
    def tags(self, *tag_list: str) -> "MCPToolBuilder":
        self._tags = list(tag_list)
        return self
    
    def build(self) -> MCPTool:
        """构建工具"""
        return MCPTool(
            name=self._name,
            description=self._description,
            category=self._category,
            provider=self._provider,
            input_schema=ToolSchema(
                type="object",
                properties=self._input_props,
                required=self._input_required
            ),
            output_schema=ToolSchema(
                type="object",
                properties=self._output_props
            ),
            cost_per_call=self._cost,
            capabilities=self._capabilities,
            tags=self._tags
        )
