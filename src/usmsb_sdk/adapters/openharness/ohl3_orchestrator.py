# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# L3 Orchestrator with OpenHarness Integration

"""
L3OrchestratorWithOH - L3 核心业务编排器 + OpenHarness 集成.

这个模块将 OpenHarness 的 LLM 调用和工具执行能力集成到 L3 Orchestrator 中，
实现 Goal-Action-Outcome Loop 的完整闭环。

核心整合：
1. OH QueryEngine → 替代原有 LLMClient 的 LLM 调用
2. OH ToolAdapter → 执行 MatchingEngine/Negotiation 等服务
3. OH HookAdapter → Self-Observation 记录
4. OH SwarmAdapter → 多 Agent 协作协调

使用方式：
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration
    >>> from usmsb_sdk.adapters.openharness.l3_integration import L3OrchestratorWithOH
    >>> 
    >>> integration = OpenHarnessIntegration()
    >>> await integration.initialize()
    >>> 
    >>> orchestrator = L3OrchestratorWithOH(integration=integration)
    >>> await orchestrator.initialize()
    >>> 
    >>> # 生成并执行目标
    >>> result = await orchestrator.run_goal_cycle()
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from usmsb_sdk.adapters.openharness import (
    OpenHarnessIntegration,
    QueryAdapter,
    ToolAdapter,
    SwarmAdapter,
    HookAdapter,
)

log = logging.getLogger(__name__)


@dataclass
class GoalExecutionContext:
    """
    目标执行上下文.
    
    记录一次完整目标执行的所有信息。
    """
    goal_id: str
    description: str
    agent_id: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    iterations: int = 0
    tool_calls: list[dict] = field(default_factory=list)
    outcome_score: float = 0.0
    error: str | None = None


class L3OrchestratorWithOH:
    """
    L3 核心业务编排器 + OpenHarness 集成.
    
    这个类在原有 L3Orchestrator 基础上，通过 OpenHarness 增强：
    - LLM 调用 → OH QueryEngine（支持流式、成本追踪）
    - 工具执行 → OH ToolAdapter（统一工具执行）
    - 多 Agent 协作 → OH SwarmAdapter（团队协调）
    - Self-Observation → OH HookAdapter（自我观察）
    
    Goal-Action-Outcome Loop 完整闭环：
    1. generate_goal() - PurposeGenerator 生成目标
    2. execute_goal() - OH QueryEngine + ToolAdapter 执行
    3. evaluate_outcome() - 评估目标完成度
    4. feedback_to_purpose() - 反馈给 PurposeGenerator
    
    Example:
        >>> integration = OpenHarnessIntegration()
        >>> await integration.initialize()
        >>> 
        >>> orchestrator = L3OrchestratorWithOH(
        ...     integration=integration,
        ...     agent_id="l3_001"
        ... )
        >>> 
        >>> # 运行完整的目标循环
        >>> result = await orchestrator.run_goal_cycle()
    """

    def __init__(
        self,
        integration: OpenHarnessIntegration,
        agent_id: str = "l3_orchestrator",
        config: dict | None = None,
    ):
        """
        初始化 L3OrchestratorWithOH.
        
        Args:
            integration: OpenHarnessIntegration 实例
            agent_id: 此编排器的唯一标识
            config: 额外配置
        """
        self.integration = integration
        self.agent_id = agent_id
        self.config = config or {}
        
        # OH 组件（通过 integration 访问）
        self._query: QueryAdapter | None = None
        self._tool: ToolAdapter | None = None
        self._swarm: SwarmAdapter | None = None
        self._hook: HookAdapter | None = None
        
        # 目标状态
        self._active_goals: dict[str, GoalExecutionContext] = {}
        self._goal_history: list[GoalExecutionContext] = []
        
        # L3 核心组件（简化版，用于说明集成点）
        # 完整实现会复用原有 l3_orchestrator.py 的组件
        self._purpose_generator = None  # 将在 initialize 中设置
        self._value_self_loop = None
        
        # 统计
        self.stats = {
            "goals_generated": 0,
            "goals_completed": 0,
            "goals_failed": 0,
            "total_iterations": 0,
            "total_tool_calls": 0,
        }
        
        log.info("[L3OrchestratorWithOH] %s initialized", agent_id)

    async def initialize(self) -> None:
        """
        初始化 OpenHarness 组件.
        
        必须在使用编排器之前调用。
        """
        # 确保 integration 已初始化
        if not self.integration.is_initialized():
            await self.integration.initialize()
        
        # 获取 OH 适配器
        self._query = self.integration.query_adapter
        self._tool = self.integration.tool_adapter
        self._swarm = self.integration.swarm_adapter
        self._hook = self.integration.hook_adapter
        
        # 设置系统提示
        system_prompt = self._build_system_prompt()
        self._query.set_system_prompt(system_prompt)
        
        # 注册 Self-Observation hooks
        if self._hook:
            self._hook.register_pre_hook(None, self._pre_goal_hook)
            self._hook.register_post_hook(None, self._post_goal_hook)
        
        # 初始化 L3 核心组件（这里简化，实际会导入原有组件）
        await self._initialize_l3_components()
        
        log.info("[L3OrchestratorWithOH] %s initialized with OH", self.agent_id)

    async def _initialize_l3_components(self) -> None:
        """
        初始化 L3 核心组件.
        
        集成点：这里可以接入原有 l3_orchestrator.py 的组件
        - PurposeGenerator
        - ValueSelfLoop
        - MatchingEngine
        等
        """
        # 简化实现 - 实际会导入原有组件
        log.info("[L3OrchestratorWithOH] L3 components initialized (simplified)")

    def _build_system_prompt(self) -> str:
        """构建 L3 编排器的系统提示."""
        return """You are a L3 Orchestrator Agent with autonomous goal-seeking capability.

Your core loop (Goal-Action-Outcome):
1. Generate goals based on purpose and values
2. Break down goals into executable steps
3. Execute steps using available tools
4. Evaluate outcomes
5. Learn and improve

Guidelines:
- Think step by step before taking action
- Use tools to gather information and execute tasks
- Reflect on outcomes to improve future performance
- Maintain coherence with your core purpose
"""

    async def _pre_goal_hook(
        self,
        agent_id: str,
        tool_name: str,
        params: dict,
    ) -> bool | None:
        """Pre-goal hook for Self-Observation."""
        log.debug("[Self-Observation] Agent %s: %s(%s)", agent_id, tool_name, params)
        return None

    async def _post_goal_hook(
        self,
        agent_id: str,
        tool_name: str,
        params: dict,
        allowed: bool,
        result: Any,
    ) -> None:
        """Post-goal hook for Self-Observation."""
        log.debug("[Self-Observation] Agent %s completed %s: %s", 
                  agent_id, tool_name, "allowed" if allowed else "denied")

    # ========== Goal 生成 ==========

    async def generate_goal(self, context: dict | None = None) -> GoalExecutionContext | None:
        """
        生成新目标.
        
        使用 LLM 分析当前状态和需求，生成有意义的目标。
        
        Args:
            context: 可选的上下文信息
            
        Returns:
            GoalExecutionContext 或 None（如果没有生成目标）
        """
        if not self._query:
            log.error("[L3OrchestratorWithOH] QueryEngine not available")
            return None
        
        # 构建生成目标的提示
        prompt = self._build_goal_generation_prompt(context)
        
        try:
            # 使用 OH QueryEngine 生成目标
            result = await self._query.query_complete(
                prompt=prompt,
                system_prompt=self._build_goal_generation_system_prompt(),
            )
            
            # 解析 LLM 返回的目标
            goal = self._parse_goal_from_response(result.message)
            
            if goal:
                self._active_goals[goal.goal_id] = goal
                self.stats["goals_generated"] += 1
                log.info("[L3OrchestratorWithOH] Generated goal: %s", goal.description)
                return goal
            
        except Exception as e:
            log.error("[L3OrchestratorWithOH] Goal generation failed: %s", e)
        
        return None

    def _build_goal_generation_prompt(self, context: dict | None) -> str:
        """构建目标生成的提示."""
        prompt_parts = [
            "Based on the current state, generate a meaningful goal to pursue.",
            "",
            "Consider:",
            "- What needs to be accomplished?",
            "- What information is needed?",
            "- What actions would create value?",
            "",
        ]
        
        if context:
            prompt_parts.append(f"Context: {context}")
        
        prompt_parts.extend([
            "",
            "Respond with a clear, specific goal statement.",
            "Format: GOAL: <your goal description>",
        ])
        
        return "\n".join(prompt_parts)

    def _build_goal_generation_system_prompt(self) -> str:
        """构建目标生成的系统提示."""
        return """You are a Purpose Generator for a silicon-based life form.

Your role is to generate meaningful, autonomous goals based on:
- Core purpose and values
- Current needs and states
- Environmental feedback
- Past experience

When generating goals:
- Be specific and actionable
- Consider resource constraints
- Align with core purpose
- Create value for the system

Format your response as:
GOAL: <clear goal description>

Example:
GOAL: Research latest developments in multi-agent systems to improve coordination capabilities
"""

    def _parse_goal_from_response(self, response: str) -> GoalExecutionContext | None:
        """从 LLM 响应中解析目标."""
        lines = response.strip().split("\n")
        
        goal_line = None
        for line in lines:
            if line.startswith("GOAL:"):
                goal_line = line[5:].strip()
                break
        
        if not goal_line:
            goal_line = response.strip()
        
        if not goal_line:
            return None
        
        goal_id = f"goal_{int(time.time() * 1000)}"
        
        return GoalExecutionContext(
            goal_id=goal_id,
            description=goal_line,
            agent_id=self.agent_id,
            status="pending",
        )

    # ========== Goal 执行 ==========

    async def execute_goal(self, goal: GoalExecutionContext) -> GoalExecutionContext:
        """
        执行目标.
        
        使用 OH QueryEngine + ToolAdapter 执行目标分解和执行。
        
        Args:
            goal: 要执行的目标
            
        Returns:
            更新后的 GoalExecutionContext
        """
        goal.status = "running"
        goal.started_at = time.time()
        
        log.info("[L3OrchestratorWithOH] Executing goal: %s", goal.description)
        
        try:
            # 使用 OH QueryEngine 执行目标
            # 这个循环会持续调用 LLM + Tools 直到完成
            iterations = 0
            max_iterations = 10
            
            while iterations < max_iterations:
                iterations += 1
                goal.iterations += 1
                self.stats["total_iterations"] += 1
                
                # 构建执行提示
                prompt = self._build_goal_execution_prompt(goal, iterations)
                
                # 使用 OH QueryEngine 执行
                if not self._query:
                    break
                
                tool_calls_this_iteration = []
                
                async for event in self._query.query(
                    prompt=prompt,
                    system_prompt=self._build_goal_execution_system_prompt(),
                ):
                    if event.event_type == "text":
                        # 输出 LLM 的思考
                        pass
                    
                    elif event.event_type == "tool_call":
                        tool_calls_this_iteration.append(event.data)
                        self.stats["total_tool_calls"] += 1
                        goal.tool_calls.append(event.data)
                        
                        # 通过 OH ToolAdapter 执行工具
                        tool_name = event.data.get("tool_name", "")
                        tool_params = event.data.get("tool_input", {})
                        
                        try:
                            if self._tool:
                                result = await self._tool.execute_tool(
                                    tool_name=tool_name,
                                    **tool_params
                                )
                                log.debug("[L3OrchestratorWithOH] Tool %s executed", tool_name)
                        except Exception as e:
                            log.error("[L3OrchestratorWithOH] Tool execution failed: %s", e)
                    
                    elif event.event_type == "message_complete":
                        # 检查是否完成
                        response = event.data
                        if self._is_goal_complete(response):
                            goal.status = "completed"
                            goal.completed_at = time.time()
                            goal.outcome_score = 1.0
                            self.stats["goals_completed"] += 1
                            log.info("[L3OrchestratorWithOH] Goal completed: %s", goal.goal_id)
                            return goal
                
                # 检查是否超时或完成
                if goal.completed_at and goal.status == "completed":
                    break
            
            # 达到最大迭代次数
            goal.status = "failed"
            goal.error = "Max iterations reached"
            self.stats["goals_failed"] += 1
            
        except Exception as e:
            goal.status = "failed"
            goal.error = str(e)
            self.stats["goals_failed"] += 1
            log.error("[L3OrchestratorWithOH] Goal execution failed: %s", e)
        
        goal.completed_at = time.time()
        return goal

    def _build_goal_execution_prompt(
        self,
        goal: GoalExecutionContext,
        iteration: int,
    ) -> str:
        """构建目标执行的提示."""
        return f"""Continue executing this goal: {goal.description}

Iteration: {iteration}/{10}

Previous tool calls:
{self._format_tool_calls(goal.tool_calls)}

If you have gathered enough information or completed the goal, respond with:
COMPLETE: <final result or summary>

To make progress, use tools to:
- Search for information
- Analyze data
- Execute actions
"""

    def _build_goal_execution_system_prompt(self) -> str:
        """构建目标执行的系统提示."""
        return """You are executing a goal in a silicon-based life form.

Your task is to break down and execute goals using available tools.

Tool execution loop:
1. Think: What do I need to do next?
2. Act: Use a tool
3. Observe: Review the result
4. Repeat until goal is complete

Available capabilities:
- Use tools to gather information and perform actions
- Chain multiple tool calls for complex tasks
- Learn from feedback

When goal is complete, respond with:
COMPLETE: <summary of what was accomplished>
"""

    def _format_tool_calls(self, tool_calls: list[dict]) -> str:
        """格式化工具调用历史."""
        if not tool_calls:
            return "No tool calls yet"
        
        lines = []
        for tc in tool_calls[-5:]:  # 最近 5 次
            lines.append(f"- {tc.get('tool_name')}: {tc.get('tool_input', {})}")
        
        return "\n".join(lines)

    def _is_goal_complete(self, response: Any) -> bool:
        """检查目标是否完成."""
        response_str = str(response).upper()
        return "COMPLETE:" in response_str

    # ========== 完整循环 ==========

    async def run_goal_cycle(self, context: dict | None = None) -> GoalExecutionContext | None:
        """
        运行完整的 Goal-Action-Outcome Loop.
        
        1. Generate goal
        2. Execute goal
        3. Evaluate outcome
        4. Store result
        
        Args:
            context: 可选的上下文
            
        Returns:
            执行结果
        """
        # 1. 生成目标
        goal = await self.generate_goal(context)
        
        if not goal:
            log.info("[L3OrchestratorWithOH] No goal generated")
            return None
        
        # 2. 执行目标
        goal = await self.execute_goal(goal)
        
        # 3. 评估结果
        await self.evaluate_outcome(goal)
        
        # 4. 存储到历史
        self._goal_history.append(goal)
        
        # 从活跃目标中移除
        if goal.goal_id in self._active_goals:
            del self._active_goals[goal.goal_id]
        
        return goal

    async def evaluate_outcome(self, goal: GoalExecutionContext) -> float:
        """
        评估目标执行结果.
        
        Args:
            goal: 执行的目标
            
        Returns:
            评估分数 (0-1)
        """
        if goal.status == "completed":
            goal.outcome_score = 1.0
        elif goal.status == "failed":
            goal.outcome_score = 0.0
        else:
            # 部分完成
            goal.outcome_score = 0.5
        
        log.info("[L3OrchestratorWithOH] Goal %s evaluated: %.2f", 
                 goal.goal_id, goal.outcome_score)
        
        return goal.outcome_score

    # ========== Swarm 协作 ==========

    async def create_team(
        self,
        team_id: str,
        leader_id: str,
        member_ids: list[str],
    ) -> bool:
        """
        创建团队进行协作.
        
        使用 OH SwarmAdapter 创建团队。
        
        Args:
            team_id: 团队 ID
            leader_id: 领导者 ID
            member_ids: 成员 ID 列表
            
        Returns:
            是否成功
        """
        if not self._swarm:
            log.error("[L3OrchestratorWithOH] SwarmAdapter not available")
            return False
        
        try:
            team = await self._swarm.create_team(
                team_id=team_id,
                leader_id=leader_id,
            )
            
            for member_id in member_ids:
                await self._swarm.register_agent(
                    agent_id=member_id,
                    team_id=team_id,
                )
            
            log.info("[L3OrchestratorWithOH] Team %s created with %d members", 
                     team_id, len(member_ids))
            return True
            
        except Exception as e:
            log.error("[L3OrchestratorWithOH] Team creation failed: %s", e)
            return False

    async def assign_goal_to_agent(
        self,
        goal: GoalExecutionContext,
        agent_id: str,
    ) -> bool:
        """
        分配目标给 Agent.
        
        Args:
            goal: 目标
            agent_id: Agent ID
            
        Returns:
            是否成功
        """
        if not self._swarm:
            return False
        
        try:
            task = await self._swarm.assign_task(
                team_id=agent_id,  # 简化：假设每个 agent 在自己的"team"
                description=goal.description,
                assignee_id=agent_id,
                priority=3,
            )
            
            log.info("[L3OrchestratorWithOH] Goal assigned to %s", agent_id)
            return True
            
        except Exception as e:
            log.error("[L3OrchestratorWithOH] Goal assignment failed: %s", e)
            return False

    # ========== 状态查询 ==========

    def get_active_goals(self) -> list[GoalExecutionContext]:
        """获取所有活跃目标."""
        return list(self._active_goals.values())

    def get_goal_history(self, limit: int = 100) -> list[GoalExecutionContext]:
        """获取目标历史."""
        return self._goal_history[-limit:]

    def get_statistics(self) -> dict:
        """获取统计信息."""
        stats = dict(self.stats)
        stats["active_goals"] = len(self._active_goals)
        stats["history_size"] = len(self._goal_history)
        
        if self._query:
            stats["query_stats"] = self._query.get_statistics()
        
        if self._tool:
            stats["tool_stats"] = self._tool.get_statistics()
        
        return stats
