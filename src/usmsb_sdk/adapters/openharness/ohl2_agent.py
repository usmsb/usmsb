# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# OHL2Agent - L2 Agent with OpenHarness Integration

"""
OHL2Agent - L2 Agent 集成 OpenHarness.

这个类将 OpenHarness 的基础设施能力（LLM 调用、工具执行、权限控制）
与现有 USMSB L2 Agent 架构整合。

核心整合：
1. 使用 OH QueryEngine 替代简化版 LLM 调用
2. 使用 OH ToolAdapter 执行现有 l2/tools.py 工具
3. 使用 OH PermissionAdapter 进行权限控制
4. 使用 OH HookAdapter 记录 Self-Observation

使用方式：
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration, OHL2Agent
    >>> 
    >>> integration = OpenHarnessIntegration()
    >>> await integration.initialize()
    >>> 
    >>> agent = OHL2Agent(
    ...     integration=integration,
    ...     agent_id="assistant_001",
    ...     name="我的助手"
    ... )
    >>> 
    >>> # 注册现有 l2/tools.py 的工具
    >>> from usmsb_sdk.l2.tools import Tool
    >>> agent.register_l2_tool(my_tool)
    >>> 
    >>> # 运行
    >>> response = await agent.run("帮我查一下天气")
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from usmsb_sdk.l1 import RuleEngine, Stimulus, Response
from usmsb_sdk.l2.memory import AgentMemory
from usmsb_sdk.l2.tools import Tool, ToolRegistry, create_tool_registry
from usmsb_sdk.adapters.openharness import (
    OpenHarnessIntegration,
    ToolAdapter,
    PermissionAdapter,
    QueryAdapter,
    HookAdapter,
    USMSBStreamEvent,
)

log = logging.getLogger(__name__)


@dataclass
class OHL2Config:
    """
    OHL2Agent 配置.
    
    继承 L2Config 的所有配置，并添加 OpenHarness 相关配置。
    """
    # L2 Agent 基本配置
    agent_id: str
    name: str = "OHL2Agent"
    model: str = "minimax-m1"  # LLM 模型
    max_context_length: int = 4096
    tool_timeout: float = 30.0  # 工具超时（秒）
    enable_memory: bool = True
    enable_tools: bool = True
    enable_oh: bool = True  # 是否启用 OpenHarness
    verbose: bool = False
    
    # OpenHarness 特有配置
    oh_permission_mode: str = "moderate"  # full_auto, moderate, plan
    oh_max_turns: int = 8
    oh_system_prompt: str | None = None


class OHL2Agent:
    """
    L2 Agent 集成 OpenHarness.
    
    这个类在现有 L2Agent 基础上，通过 OpenHarness 增强：
    - LLM 调用 → 使用 OH QueryEngine（支持流式、成本追踪）
    - 工具执行 → 使用 OH ToolAdapter + PermissionAdapter
    - Self-Observation → 使用 OH HookAdapter
    - 记忆 → 保留现有 AgentMemory + OH MemoryAdapter
    
    核心流程：
    1. 接收输入
    2. L1 规则匹配（最快路径）
    3. 记忆上下文检索
    4. OH QueryEngine 处理（LLM + 工具决策）
    5. OH ToolAdapter 执行工具
    6. OH HookAdapter 记录 Self-Observation
    7. 记忆更新
    8. 返回结果
    
    Example:
        >>> integration = OpenHarnessIntegration()
        >>> await integration.initialize()
        >>> 
        >>> agent = OHL2Agent(
        ...     integration=integration,
        ...     agent_id="assistant_001"
        ... )
        >>> 
        >>> # 注册 l2/tools.py 的工具到 OH
        >>> agent.register_l2_tool(my_tool)
        >>> 
        >>> # 运行
        >>> response = await agent.run("What is 2+2?")
    """

    def __init__(
        self,
        integration: OpenHarnessIntegration,
        config: OHL2Config,
    ):
        """
        初始化 OHL2Agent.
        
        Args:
            integration: OpenHarnessIntegration 实例
            config: OHL2Agent 配置
        """
        self.config = config
        self.integration = integration
        self.agent_id = config.agent_id
        
        # OpenHarness 组件（通过 integration 访问）
        self._oh_query: QueryAdapter | None = None
        self._oh_tool: ToolAdapter | None = None
        self._oh_permission: PermissionAdapter | None = None
        self._oh_hook: HookAdapter | None = None
        
        # L1 规则引擎（降级用）
        self.rule_engine = RuleEngine(name=f"{config.name}_rules")
        
        # 记忆系统 - 保留现有实现
        if config.enable_memory:
            self.memory = AgentMemory(agent_id=config.agent_id)
        else:
            self.memory = None
        
        # 工具系统 - 现有 l2/tools.py + OH 增强
        if config.enable_tools:
            self.l2_tools = create_tool_registry()  # 现有 l2/tools.py 工具注册表
        else:
            self.l2_tools = ToolRegistry()
        
        # OH 工具名映射（l2 tool name → OH tool name）
        self._tool_name_map: dict[str, str] = {}
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "tool_calls": 0,
            "rule_matches": 0,
            "oh_queries": 0,
            "avg_latency_ms": 0.0,
            "total_cost": 0.0,
        }
        
        # 状态
        self.is_running = False
        
        log.info("[OHL2Agent] %s (%s) initialized with OH", config.name, config.agent_id)

    async def initialize(self) -> None:
        """
        初始化 OpenHarness 组件.
        
        必须在运行 Agent 之前调用。
        """
        if not self.config.enable_oh:
            return
        
        # 确保 integration 已初始化
        if not self.integration.is_initialized():
            await self.integration.initialize()
        
        # 获取 OH 适配器
        self._oh_query = self.integration.query_adapter
        self._oh_tool = self.integration.tool_adapter
        self._oh_permission = self.integration.permission_adapter
        self._oh_hook = self.integration.hook_adapter
        
        # 设置系统提示
        system_prompt = self.config.oh_system_prompt or self._build_system_prompt()
        self._oh_query.set_system_prompt(system_prompt)
        
        # 设置最大轮次
        self._oh_query.set_max_turns(self.config.oh_max_turns)
        
        # 注册 Self-Observation hooks
        if self._oh_hook:
            self._oh_hook.register_pre_hook(None, self._pre_tool_hook)
            self._oh_hook.register_post_hook(None, self._post_tool_hook)
        
        log.info("[OHL2Agent] OpenHarness components initialized")

    def _build_system_prompt(self) -> str:
        """构建系统提示."""
        prompt_parts = [
            f"You are {self.config.name}, a helpful AI assistant.",
            f"You have access to tools to help answer user questions.",
            "",
            "Available tools:",
        ]
        
        # 列出注册的 l2/tools.py 工具
        for tool in self.l2_tools.list_all():
            prompt_parts.append(f"- {tool.name}: {tool.description}")
        
        prompt_parts.extend([
            "",
            "Guidelines:",
            "- Use tools when they can help answer the question",
            "- Think step by step",
            "- If a tool fails, try an alternative approach",
        ])
        
        return "\n".join(prompt_parts)

    async def _pre_tool_hook(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
    ) -> bool | None:
        """
        Pre-tool hook for Self-Observation.
        
        记录工具调用意图，但不阻止执行。
        """
        log.debug("[Self-Observation] Agent %s intends to call %s", agent_id, tool_name)
        return None  # 继续执行

    async def _post_tool_hook(
        self,
        agent_id: str,
        tool_name: str,
        params: dict[str, Any],
        allowed: bool,
        result: Any,
    ) -> None:
        """
        Post-tool hook for Self-Observation.
        
        记录工具执行结果到记忆。
        """
        if self.memory:
            observation = {
                "type": "tool_execution",
                "tool": tool_name,
                "params": params,
                "allowed": allowed,
                "success": result is not None,
                "timestamp": time.time(),
            }
            # 记录到工作记忆
            self.memory.working.add_turn(
                "system",
                f"Tool execution: {tool_name} - {'success' if allowed and result else 'failed'}"
            )
        
        log.debug("[Self-Observation] Agent %s called %s: %s", 
                  agent_id, tool_name, "allowed" if allowed else "denied")

    # ========== 工具管理 ==========

    def register_l2_tool(self, tool: Tool) -> str:
        """
        注册现有 l2/tools.py 的工具到 Agent.
        
        这个方法将 l2/tools.py 的 Tool 适配到 OpenHarness，
        使其可以通过 OH ToolAdapter 执行。
        
        Args:
            tool: l2/tools.py 的 Tool 实例
            
        Returns:
            注册的工具名
        """
        # 先注册到 l2_tools（现有机制）
        tool_name = self.l2_tools.register(tool)
        
        # 如果 OH 可用，注册到 OH ToolAdapter
        if self._oh_tool and self.config.enable_oh:
            # 将 l2 Tool 包装为 OH 兼容格式并注册
            self._register_tool_to_oh(tool)
        
        log.info("[OHL2Agent] Registered tool: %s", tool_name)
        return tool_name

    def _register_tool_to_oh(self, tool: Tool) -> None:
        """
        将 l2/tools.py 的 Tool 注册到 OpenHarness ToolAdapter.
        
        这是关键集成点 - 把 USMSB 的工具适配到 OH 的工具格式。
        """
        if not self._oh_tool:
            return
        
        # 转换 l2/tools.py Tool 定义为 OH 格式
        oh_tool_schema = tool.definition.to_openai_format()
        
        # 映射工具名
        self._tool_name_map[tool.name] = f"l2_{tool.name}"
        
        # 注册到 OH ToolAdapter（使用简单的 callable wrapper）
        async def oh_wrapper(**kwargs):
            # 调用原始 l2 tool
            result = await tool.execute(**kwargs)
            return result
        
        from usmsb_sdk.adapters.openharness import ToolMetadata
        
        metadata = ToolMetadata(
            name=f"l2_{tool.name}",
            description=tool.description,
            capabilities=[tool.category.value] if hasattr(tool.category, 'value') else [],
            category=tool.category.value if hasattr(tool.category, 'value') else "general",
            is_read_only=tool.is_read_only if hasattr(tool, 'is_read_only') else False,
        )
        
        # 注册到 OH
        self._oh_tool.register_tool(
            oh_wrapper,
            metadata=metadata,
            name=f"l2_{tool.name}",
            description=tool.description,
            is_read_only=tool.is_read_only if hasattr(tool, 'is_read_only') else False,
        )

    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        result = self.l2_tools.unregister(tool_name)
        if tool_name in self._tool_name_map:
            del self._tool_name_map[tool_name]
        return result

    def get_tool(self, tool_name: str) -> Tool | None:
        """获取工具"""
        return self.l2_tools.get(tool_name)

    def list_tools(self) -> list[Tool]:
        """列出所有 l2/tools.py 工具"""
        return self.l2_tools.list_all()

    def list_oh_tools(self) -> list[dict[str, Any]]:
        """列出所有 OpenHarness 工具"""
        if not self._oh_tool:
            return []
        return self._oh_tool.discover_tools()

    # ========== 记忆管理 ==========

    def add_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        importance: float = 0.5
    ) -> str:
        """添加记忆"""
        if not self.memory:
            return ""
        
        if memory_type == "episodic":
            return self.memory.episodic.add_episode(content, importance)
        elif memory_type == "semantic":
            return self.memory.semantic.add_knowledge(content, importance)
        return ""

    def search_memory(self, query: str) -> list[dict]:
        """搜索记忆"""
        if not self.memory:
            return []
        
        results = []
        
        # 搜索情景记忆
        for episode in self.memory.episodic.search(query):
            results.append({
                "type": "episodic",
                "content": episode.content,
                "importance": episode.importance,
            })
        
        # 搜索语义记忆
        for knowledge in self.memory.semantic.search(query):
            results.append({
                "type": "semantic",
                "content": knowledge.content,
                "importance": knowledge.importance,
            })
        
        return results

    # ========== LLM 调用 ==========

    async def _call_llm_with_oh(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        """
        使用 OpenHarness QueryEngine 调用 LLM.
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示（覆盖默认）
            
        Returns:
            LLM 生成的响应文本
        """
        if not self._oh_query:
            return await self._call_llm_fallback(prompt)
        
        self.stats["oh_queries"] += 1
        
        try:
            # 使用 OH QueryAdapter 执行查询
            result = await self._oh_query.query_complete(
                prompt=prompt,
                system_prompt=system_prompt,
            )
            
            # 记录成本
            if result.usage:
                self.stats["total_cost"] += result.usage.total_cost
            
            return result.message
            
        except Exception as e:
            log.error("[OHL2Agent] OH query failed: %s", e)
            return await self._call_llm_fallback(prompt)

    async def _call_llm_fallback(self, prompt: str) -> str:
        """
        降级 LLM 调用（当 OH 不可用时）.
        
        简化实现 - 应该调用实际的 LLM API。
        """
        return f"Response to: {prompt[:50]}..."

    # ========== 核心运行 ==========

    async def run(self, user_input: str) -> str:
        """
        运行 Agent 处理输入.
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: Agent 响应
        """
        self.stats["total_requests"] += 1
        start_time = time.time()
        
        # 1. L1 规则匹配（最快路径）
        stimulus = Stimulus(text=user_input)
        rule_response = await self.rule_engine.react(stimulus)
        
        if rule_response.action_result != "我没有理解您的问题。":
            self.stats["rule_matches"] += 1
            return rule_response.action_result
        
        # 2. 获取记忆上下文
        context = ""
        if self.memory:
            turns = self.memory.working.get_context(last_n=10)
            context = "\n".join([f"{t.role}: {t.content}" for t in turns])
        
        # 3. 构建 Prompt
        prompt = self._build_prompt(user_input, context)
        
        # 4. 决定是否使用 OH
        if self.config.enable_oh and self._oh_query:
            # 5. 使用 OpenHarness 处理
            response = await self._run_with_oh(prompt)
        else:
            # 6. 降级到简化 LLM
            response = await self._call_llm_fallback(prompt)
        
        # 7. 记录到记忆
        if self.memory:
            self.memory.working.add_turn("user", user_input)
            self.memory.working.add_turn("assistant", response)
        
        # 8. 计算延迟
        latency = (time.time() - start_time) * 1000
        self.stats["avg_latency_ms"] = (
            self.stats["avg_latency_ms"] * 0.9 + latency * 0.1
        )
        
        return response

    async def _run_with_oh(self, prompt: str) -> str:
        """
        使用 OpenHarness 处理请求.
        
        通过 OH QueryEngine 执行完整的 ReAct 循环。
        """
        if not self._oh_query:
            return await self._call_llm_fallback(prompt)
        
        # 构建系统提示
        system_prompt = self._build_system_prompt()
        
        # 收集响应
        response_parts = []
        tool_calls = []
        
        try:
            async for event in self._oh_query.query(
                prompt=prompt,
                system_prompt=system_prompt,
            ):
                if event.event_type == "text":
                    response_parts.append(event.data)
                elif event.event_type == "tool_call":
                    tool_calls.append(event.data)
                    self.stats["tool_calls"] += 1
                elif event.event_type == "message_complete":
                    pass
        
        except Exception as e:
            log.error("[OHL2Agent] OH query error: %s", e)
            return f"Error: {e}"
        
        return "".join(response_parts) if response_parts else "No response"

    def _build_prompt(self, user_input: str, context: str) -> str:
        """构建 Prompt"""
        prompt_parts = []
        
        if context:
            prompt_parts.append(f"对话历史:\n{context}\n")
        
        prompt_parts.append(f"当前输入: {user_input}")
        
        if self.l2_tools.list_all():
            tool_names = [t.name for t in self.l2_tools.list_all()]
            prompt_parts.append(f"\n可用工具: {', '.join(tool_names)}")
        
        return "\n".join(prompt_parts)

    async def run_with_history(
        self,
        messages: list[dict],
    ) -> dict:
        """
        带历史的对话.
        
        Args:
            messages: [{"role": "user", "content": "..."}]
            
        Returns:
            dict: {"response": str, "tool_used": str|None}
        """
        if not messages:
            return {"response": "No input", "tool_used": None}
        
        # 获取最后一条用户消息
        last_user_msg = messages[-1]["content"] if messages[-1]["role"] == "user" else ""
        
        # 添加历史到工作记忆
        if self.memory:
            for msg in messages[:-1]:
                self.memory.working.add_turn(msg["role"], msg["content"])
        
        # 运行
        response = await self.run(last_user_msg)
        
        return {
            "response": response,
            "tool_used": None  # 简化
        }

    def get_status(self) -> dict:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "is_running": self.is_running,
            "stats": self.stats,
            "tool_count": len(self.l2_tools.list_all()),
            "oh_tool_count": len(self._tool_name_map) if self._oh_tool else 0,
            "memory": self.memory.to_dict() if self.memory else None,
            "oh_enabled": self.config.enable_oh,
            "oh_initialized": self._oh_query is not None,
        }

    def get_statistics(self) -> dict:
        """获取详细统计"""
        stats = dict(self.stats)
        
        if self._oh_tool:
            oh_stats = self._oh_tool.get_statistics()
            stats["oh_tools"] = oh_stats
        
        if self._oh_query:
            query_stats = self._oh_query.get_statistics()
            stats["oh_queries"] = query_stats
        
        return stats

    def __repr__(self) -> str:
        return f"OHL2Agent({self.config.name}, id={self.agent_id}, oh={self.config.enable_oh})"
