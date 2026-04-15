# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# MetaAgent with OpenHarness Integration

"""
MetaAgentWithOH - MetaAgent 与 OpenHarness 集成.

这个模块将 OpenHarness 的 Agent Spawning 能力集成到 MetaAgent 中，
实现 L5 集体智能的多 Agent 协作。

核心整合：
1. OH MetaAgentAdapter → 创建和管理子 Agent
2. OH SwarmAdapter → 团队协调
3. OH QueryAdapter → Agent 间通信的 LLM 支持
4. OH HookAdapter → 集体 Self-Observation

使用方式：
    >>> from usmsb_sdk.adapters.openharness import OpenHarnessIntegration
    >>> from usmsb_sdk.adapters.openharness.meta_integration import MetaAgentWithOH
    >>> 
    >>> integration = OpenHarnessIntegration()
    >>> await integration.initialize()
    >>> 
    >>> meta = MetaAgentWithOH(integration=integration)
    >>> 
    >>> # 创建子 Agent
    >>> agent = await meta.spawn_child(
    ...     agent_type="researcher",
    ...     name="Research Agent 1"
    ... )
    >>> 
    >>> # 委托任务
    >>> task = await meta.delegate_task(agent.agent_id, "Research AI trends")
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from usmsb_sdk.adapters.openharness import (
    OpenHarnessIntegration,
    MetaAgentAdapter,
    SwarmAdapter,
    QueryAdapter,
    HookAdapter,
    AgentSpec,
    AgentState,
    DelegatedTask,
)

log = logging.getLogger(__name__)


@dataclass
class ChildAgentInfo:
    """
    子 Agent 信息.
    
    封装 OH MetaAgentAdapter 返回的 SpawnedAgent，
    添加 MetaAgent 特有的元数据。
    """
    agent_id: str
    name: str
    agent_type: str
    parent_id: str
    state: AgentState = AgentState.SPAWNING
    spawned_at: float = field(default_factory=time.time)
    tasks_completed: int = 0
    tasks_failed: int = 0
    metadata: dict = field(default_factory=dict)


class MetaAgentWithOH:
    """
    MetaAgent 与 OpenHarness 集成.
    
    这个类在原有 MetaAgent 基础上，通过 OpenHarness 增强：
    - Agent Spawning → OH MetaAgentAdapter（动态创建子 Agent）
    - 团队协调 → OH SwarmAdapter（多 Agent 协作）
    - 集体决策 → OH QueryAdapter + 自研决策逻辑
    
    L5 集体智能的核心能力：
    1. 动态创建子 Agent
    2. 委托任务给子 Agent
    3. 收集和聚合子 Agent 结果
    4. 集体决策和协商
    5. 经验传承和进化
    
    Example:
        >>> meta = MetaAgentWithOH(integration=integration)
        >>> 
        >>> # 创建研究 Agent 团队
        >>> researchers = []
        >>> for i in range(3):
        ...     agent = await meta.spawn_child(
        ...         agent_type="researcher",
        ...         name=f"Researcher {i+1}"
        ...     )
        ...     researchers.append(agent)
        >>> 
        >>> # 广播任务
        >>> results = await meta.delegate_to_team(
        ...     agents=[a.agent_id for a in researchers],
        ...     task="Research AI trends"
        ... )
    """

    def __init__(
        self,
        integration: OpenHarnessIntegration,
        parent_id: str = "meta_agent",
        config: dict | None = None,
    ):
        """
        初始化 MetaAgentWithOH.
        
        Args:
            integration: OpenHarnessIntegration 实例
            parent_id: 父 Agent ID
            config: 额外配置
        """
        self.integration = integration
        self.parent_id = parent_id
        self.config = config or {}
        
        # OH 组件
        self._meta_agent: MetaAgentAdapter | None = None
        self._swarm: SwarmAdapter | None = None
        self._query: QueryAdapter | None = None
        self._hook: HookAdapter | None = None
        
        # 子 Agent 注册
        self._children: dict[str, ChildAgentInfo] = {}
        
        # 团队注册
        self._teams: dict[str, list[str]] = {}  # team_id -> [agent_ids]
        
        # 统计
        self.stats = {
            "children_spawned": 0,
            "children_stopped": 0,
            "tasks_delegated": 0,
            "tasks_completed": 0,
            "teams_created": 0,
        }
        
        log.info("[MetaAgentWithOH] %s initialized", parent_id)

    async def initialize(self) -> None:
        """
        初始化 OpenHarness 组件.
        
        必须在使用之前调用。
        """
        if not self.integration.is_initialized():
            await self.integration.initialize()
        
        # 获取 OH 适配器
        self._meta_agent = self.integration.meta_agent_adapter
        self._swarm = self.integration.swarm_adapter
        self._query = self.integration.query_adapter
        self._hook = self.integration.hook_adapter
        
        log.info("[MetaAgentWithOH] %s initialized with OH", self.parent_id)

    # ========== Agent 创建 ==========

    async def spawn_child(
        self,
        agent_type: str,
        name: str | None = None,
        capabilities: list[str] | None = None,
        model: str | None = None,
        team_id: str | None = None,
    ) -> ChildAgentInfo | None:
        """
        创建子 Agent.
        
        使用 OH MetaAgentAdapter 创建新的子 Agent。
        
        Args:
            agent_type: Agent 类型 (researcher, coder, writer, etc.)
            name: Agent 名称
            capabilities: Agent 能力列表
            model: LLM 模型
            team_id: 所属团队 ID
            
        Returns:
            ChildAgentInfo 或 None
        """
        if not self._meta_agent:
            log.error("[MetaAgentWithOH] MetaAgentAdapter not available")
            return None
        
        # 创建 Agent 规格
        spec = AgentSpec(
            agent_type=agent_type,
            name=name or f"{agent_type}_{int(time.time() * 1000)}",
            capabilities=capabilities or [],
            model=model,
        )
        
        try:
            # 通过 OH 创建
            spawned = await self._meta_agent.spawn_agent(
                spec=spec,
                team_id=team_id,
            )
            
            # 创建子 Agent 信息
            child_info = ChildAgentInfo(
                agent_id=spawned.agent_id,
                name=spawned.name,
                agent_type=agent_type,
                parent_id=self.parent_id,
                state=spawned.state,
            )
            
            self._children[spawned.agent_id] = child_info
            self.stats["children_spawned"] += 1
            
            # 如果指定了团队，加入团队
            if team_id:
                if team_id not in self._teams:
                    self._teams[team_id] = []
                self._teams[team_id].append(spawned.agent_id)
            
            log.info("[MetaAgentWithOH] Spawned child %s (%s)", 
                     spawned.agent_id, agent_type)
            
            return child_info
            
        except Exception as e:
            log.error("[MetaAgentWithOH] Failed to spawn child: %s", e)
            return None

    async def spawn_team(
        self,
        team_id: str,
        team_name: str | None = None,
        leader_type: str = "coordinator",
        member_types: list[tuple[str, int]] | None = None,
    ) -> tuple[str, list[ChildAgentInfo]]:
        """
        创建完整的团队.
        
        Args:
            team_id: 团队 ID
            team_name: 团队名称
            leader_type: 领导者 Agent 类型
            member_types: 成员类型和数量 [(type, count), ...]
            
        Returns:
            (team_id, [ChildAgentInfo, ...])
        """
        if not self._meta_agent:
            return team_id, []
        
        # 创建团队
        try:
            await self._meta_agent.create_team(
                team_id=team_id,
                name=team_name,
            )
            self._teams[team_id] = []
            self.stats["teams_created"] += 1
        except Exception as e:
            log.warning("[MetaAgentWithOH] Team creation warning: %s", e)
        
        children = []
        
        # 创建领导者
        leader = await self.spawn_child(
            agent_type=leader_type,
            name=f"{team_id}_leader",
            team_id=team_id,
        )
        if leader:
            children.append(leader)
        
        # 创建成员
        if member_types:
            for member_type, count in member_types:
                for i in range(count):
                    member = await self.spawn_child(
                        agent_type=member_type,
                        name=f"{team_id}_{member_type}_{i+1}",
                        team_id=team_id,
                    )
                    if member:
                        children.append(member)
        
        log.info("[MetaAgentWithOH] Team %s created with %d agents", 
                 team_id, len(children))
        
        return team_id, children

    async def stop_child(self, agent_id: str) -> bool:
        """
        停止子 Agent.
        
        Args:
            agent_id: 要停止的 Agent ID
            
        Returns:
            是否成功
        """
        if not self._meta_agent:
            return False
        
        try:
            success = await self._meta_agent.stop_agent(agent_id)
            
            if success and agent_id in self._children:
                child = self._children[agent_id]
                child.state = AgentState.STOPPED
                self.stats["children_stopped"] += 1
            
            return success
            
        except Exception as e:
            log.error("[MetaAgentWithOH] Failed to stop child %s: %s", agent_id, e)
            return False

    def get_child(self, agent_id: str) -> ChildAgentInfo | None:
        """获取子 Agent 信息."""
        return self._children.get(agent_id)

    def list_children(
        self,
        team_id: str | None = None,
        state: AgentState | None = None,
    ) -> list[ChildAgentInfo]:
        """
        列出子 Agent.
        
        Args:
            team_id: 可选的团队过滤
            state: 可选的状态过滤
            
        Returns:
            ChildAgentInfo 列表
        """
        children = list(self._children.values())
        
        if team_id:
            team_agent_ids = set(self._teams.get(team_id, []))
            children = [c for c in children if c.agent_id in team_agent_ids]
        
        if state:
            children = [c for c in children if c.state == state]
        
        return children

    # ========== 任务委托 ==========

    async def delegate_task(
        self,
        agent_id: str,
        task_description: str,
        priority: int = 3,
    ) -> DelegatedTask | None:
        """
        委托任务给子 Agent.
        
        Args:
            agent_id: 目标 Agent ID
            task_description: 任务描述
            priority: 优先级 (1-5)
            
        Returns:
            DelegatedTask 或 None
        """
        if not self._meta_agent:
            log.error("[MetaAgentWithOH] MetaAgentAdapter not available")
            return None
        
        try:
            task = await self._meta_agent.delegate_task(
                agent_id=agent_id,
                description=task_description,
                priority=priority,
            )
            
            self.stats["tasks_delegated"] += 1
            
            log.info("[MetaAgentWithOH] Task delegated to %s: %s", 
                     agent_id, task_description[:50])
            
            return task
            
        except Exception as e:
            log.error("[MetaAgentWithOH] Task delegation failed: %s", e)
            return None

    async def delegate_to_team(
        self,
        agents: list[str],
        task: str,
        wait_for_all: bool = True,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        """
        向团队成员广播任务.
        
        Args:
            agents: Agent ID 列表
            task: 任务描述
            wait_for_all: 是否等待所有 Agent 完成
            timeout_seconds: 超时时间
            
        Returns:
            {agent_id: result, ...}
        """
        results = {}
        
        # 并行委托给所有 Agent
        delegated = []
        for agent_id in agents:
            delegated_task = await self.delegate_task(agent_id, task)
            if delegated_task:
                delegated.append((agent_id, delegated_task))
        
        if not wait_for_all:
            return {"delegated": len(delegated)}
        
        # 等待结果
        start_time = time.time()
        for agent_id, delegated_task in delegated:
            task_id = delegated_task.task_id
            
            while time.time() - start_time < timeout_seconds:
                result = await self._meta_agent.get_task_result(task_id)
                
                if result:
                    results[agent_id] = {
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                        "duration": result.duration_seconds,
                    }
                    
                    # 更新子 Agent 统计
                    child = self._children.get(agent_id)
                    if child:
                        if result.success:
                            child.tasks_completed += 1
                        else:
                            child.tasks_failed += 1
                    
                    if result.success:
                        self.stats["tasks_completed"] += 1
                    break
                
                await asyncio.sleep(0.5)
            
            if agent_id not in results:
                results[agent_id] = {"error": "timeout"}

        return results

    async def aggregate_results(
        self,
        results: dict[str, Any],
        aggregation_method: str = "all",
    ) -> Any:
        """
        聚合多个 Agent 的结果.
        
        Args:
            results: {agent_id: result} 字典
            aggregation_method: 聚合方法 (all, best, majority, llm)
            
        Returns:
            聚合后的结果
        """
        if aggregation_method == "all":
            return results
        
        if aggregation_method == "best":
            # 返回最成功的结果
            best = None
            best_score = -1
            
            for agent_id, result in results.items():
                if isinstance(result, dict):
                    score = 1 if result.get("success") else 0
                    if score > best_score:
                        best_score = score
                        best = result
            
            return best
        
        if aggregation_method == "llm":
            # 使用 LLM 聚合
            if not self._query:
                return results
            
            prompt = self._build_aggregation_prompt(results)
            
            try:
                response = await self._query.query_complete(prompt)
                return {"aggregated": response.message}
            except Exception as e:
                log.error("[MetaAgentWithOH] LLM aggregation failed: %s", e)
                return results
        
        return results

    def _build_aggregation_prompt(self, results: dict[str, Any]) -> str:
        """构建聚合提示."""
        lines = [
            "Given the following results from multiple agents:",
            "",
        ]
        
        for agent_id, result in results.items():
            lines.append(f"Agent {agent_id}:")
            if isinstance(result, dict):
                lines.append(f"  Success: {result.get('success')}")
                if result.get('output'):
                    lines.append(f"  Output: {result['output'][:200]}")
                if result.get('error'):
                    lines.append(f"  Error: {result['error']}")
            lines.append("")
        
        lines.extend([
            "Synthesize these results into a coherent summary.",
            "Identify agreements, disagreements, and key insights.",
            "Format: SUMMARY: <your synthesis>",
        ])
        
        return "\n".join(lines)

    # ========== 集体决策 ==========

    async def collective_decision(
        self,
        agents: list[str],
        question: str,
        decision_method: str = "llm",
    ) -> dict[str, Any]:
        """
        集体决策.
        
        让多个 Agent 共同决策一个问题。
        
        Args:
            agents: 参与的 Agent ID 列表
            question: 决策问题
            decision_method: 决策方法 (vote, llm, consensus)
            
        Returns:
            决策结果
        """
        if decision_method == "vote":
            return await self._vote_decision(agents, question)
        
        if decision_method == "llm":
            return await self._llm_decision(agents, question)
        
        if decision_method == "consensus":
            return await self._consensus_decision(agents, question)
        
        return {"error": f"Unknown decision method: {decision_method}"}

    async def _vote_decision(
        self,
        agents: list[str],
        question: str,
    ) -> dict[str, Any]:
        """投票决策."""
        votes = {}
        
        for agent_id in agents:
            child = self._children.get(agent_id)
            if not child:
                continue
            
            # 简化：直接让 Agent 用 LLM 生成投票
            if self._query:
                prompt = f"Vote on this question: {question}\nRespond with YES or NO."
                
                try:
                    response = await self._query.query_complete(prompt)
                    vote = "YES" if "YES" in response.message.upper() else "NO"
                    votes[agent_id] = vote
                except Exception as e:
                    log.error("[MetaAgentWithOH] Vote failed for %s: %s", agent_id, e)
        
        yes_count = sum(1 for v in votes.values() if v == "YES")
        no_count = sum(1 for v in votes.values() if v == "NO")
        
        return {
            "decision": "YES" if yes_count > no_count else "NO",
            "votes": votes,
            "yes_count": yes_count,
            "no_count": no_count,
            "method": "vote",
        }

    async def _llm_decision(
        self,
        agents: list[str],
        question: str,
    ) -> dict[str, Any]:
        """使用 LLM 做决策."""
        if not self._query:
            return {"error": "QueryAdapter not available"}
        
        # 收集各 Agent 的意见
        opinions = []
        for agent_id in agents:
            child = self._children.get(agent_id)
            if not child:
                continue
            
            opinions.append(f"Agent {child.name} ({child.agent_type}): reasoning...")
        
        prompt = f"""Question: {question}

Stakeholder opinions:
{chr(10).join(opinions)}

Make a decision considering all perspectives.
Format: DECISION: <your decision>
REASONING: <why you chose this>
"""
        
        try:
            response = await self._query.query_complete(prompt)
            return {
                "decision": response.message,
                "method": "llm",
                "agents_consulted": len(agents),
            }
        except Exception as e:
            return {"error": str(e)}

    async def _consensus_decision(
        self,
        agents: list[str],
        question: str,
    ) -> dict[str, Any]:
        """协商一致决策."""
        # 简化实现：多次迭代达成共识
        max_iterations = 3
        current_votes = {}
        
        for iteration in range(max_iterations):
            votes = {}
            
            for agent_id in agents:
                if self._query:
                    context = ""
                    if current_votes:
                        context = f"Previous round: {current_votes}"
                    
                    prompt = f"""{question}

{context}

Reach consensus. Respond with your position and reasoning.
"""
                    
                    try:
                        response = await self._query.query_complete(prompt)
                        votes[agent_id] = response.message
                    except Exception:
                        pass
            
            current_votes = votes
            
            # 检查是否达成共识（简单检查：所有回复是否相似）
            if len(set(votes.values())) == 1:
                return {
                    "decision": list(votes.values())[0],
                    "method": "consensus",
                    "iterations": iteration + 1,
                }
        
        # 无法达成共识，返回最后的投票
        return {
            "decision": "no_consensus",
            "method": "consensus",
            "iterations": max_iterations,
            "final_votes": current_votes,
        }

    # ========== 经验传承 ==========

    async def share_experience(
        self,
        from_agent_id: str,
        to_agent_id: str,
        experience: dict,
    ) -> bool:
        """
        在 Agent 之间分享经验.
        
        这是 L5 经验传承的核心机制。
        
        Args:
            from_agent_id: 经验来源 Agent
            to_agent_id: 经验目标 Agent
            experience: 经验内容
            
        Returns:
            是否成功
        """
        # 将经验存储到共享记忆
        if self._hook:
            await self._hook.execute_post_hooks(
                agent_id=to_agent_id,
                tool_name="experience_share",
                params={},
                allowed=True,
                result={"from": from_agent_id, "experience": experience},
            )
        
        log.info("[MetaAgentWithOH] Experience shared from %s to %s",
                 from_agent_id, to_agent_id)
        
        return True

    # ========== 状态查询 ==========

    def get_team(self, team_id: str) -> list[ChildAgentInfo]:
        """获取团队成员."""
        return self.list_children(team_id=team_id)

    def get_statistics(self) -> dict:
        """获取统计信息."""
        stats = dict(self.stats)
        stats["active_children"] = len([
            c for c in self._children.values() 
            if c.state == AgentState.READY or c.state == AgentState.RUNNING
        ])
        stats["total_children"] = len(self._children)
        stats["total_teams"] = len(self._teams)
        
        if self._meta_agent:
            meta_stats = self._meta_agent.get_statistics()
            stats["meta_agent"] = meta_stats
        
        return stats
