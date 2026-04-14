# -*- coding: utf-8 -*-
"""
执行编排层 - Execution Orchestrator

MAS 协调核心：
1. 任务分解与 Agent 路由
2. 协调拓扑动态选择（Supervisor/Hierarchical/Mesh）
3. 跨 Agent 状态同步
4. Replan 与协调恢复

参考：MAS Harness Engineering
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TopologyType(Enum):
    """协调拓扑类型"""
    SUPERVISOR = "supervisor"      # 中央协调
    HIERARCHICAL = "hierarchical"  # 分层
    MESH = "mesh"                  # P2P
    HYBRID = "hybrid"              # 混合


class AgentRole(Enum):
    """Agent 角色"""
    COORDINATOR = "coordinator"    # 协调者
    EXECUTOR = "executor"          # 执行者
    VERIFIER = "verifier"          # 验证者
    SPECIALIST = "specialist"       # 专家


@dataclass
class TaskDecomposition:
    """任务分解结果"""
    task_id: str
    subtasks: list[dict]
    dependencies: dict[str, list[str]]  # task_id -> [dependent_task_ids]
    estimated_duration: float
    required_capabilities: list[str]


@dataclass
class AgentAssignment:
    """Agent 分配"""
    subtask_id: str
    agent_id: str
    role: AgentRole
    estimated_completion: float


class ExecutionOrchestrator:
    """
    MAS 执行编排器
    
    负责：
    1. 任务分解
    2. Agent 路由与分配
    3. 协调拓扑选择
    4. 状态同步
    5. Replan 恢复
    """
    
    def __init__(self):
        self._agents: dict[str, Any] = {}
        self._topology: TopologyType = TopologyType.SUPERVISOR
        self._tasks: dict[str, dict] = {}
        self._assignments: dict[str, AgentAssignment] = {}
        self._state: dict[str, Any] = {}
    
    def register_agent(self, agent_id: str, capabilities: list[str]) -> None:
        """注册 Agent"""
        self._agents[agent_id] = {
            "id": agent_id,
            "capabilities": capabilities,
            "status": "available",
            "current_task": None
        }
    
    def select_topology(self, task_complexity: int, agent_count: int) -> TopologyType:
        """
        动态选择协调拓扑
        
        Args:
            task_complexity: 任务复杂度 (1-10)
            agent_count: 可用 Agent 数量
            
        Returns:
            适合的拓扑类型
        """
        if task_complexity <= 2 and agent_count <= 3:
            return TopologyType.SUPERVISOR
        elif task_complexity >= 7 and agent_count >= 5:
            return TopologyType.MESH
        elif task_complexity >= 4:
            return TopologyType.HIERARCHICAL
        else:
            return TopologyType.HYBRID
    
    def decompose_task(self, task_description: str, context: dict | None = None) -> TaskDecomposition:
        """
        任务分解
        
        Args:
            task_description: 任务描述
            context: 上下文信息
            
        Returns:
            分解后的子任务
        """
        task_id = str(uuid.uuid4())
        
        # 简单分解逻辑（实际应该用 LLM）
        subtasks = []
        
        if "分析" in task_description:
            subtasks.append({"id": f"{task_id}_1", "type": "analysis", "description": "数据分析"})
            subtasks.append({"id": f"{task_id}_2", "type": "report", "description": "生成报告"})
        elif "开发" in task_description:
            subtasks.append({"id": f"{task_id}_1", "type": "design", "description": "设计"})
            subtasks.append({"id": f"{task_id}_2", "type": "coding", "description": "编码"})
            subtasks.append({"id": f"{task_id}_3", "type": "test", "description": "测试"})
        else:
            subtasks.append({"id": f"{task_id}_1", "type": "execute", "description": task_description})
        
        return TaskDecomposition(
            task_id=task_id,
            subtasks=subtasks,
            dependencies={},
            estimated_duration=len(subtasks) * 10.0,
            required_capabilities=["reasoning", "execution"]
        )
    
    def assign_task(self, subtask: dict, agent_id: str, role: AgentRole = AgentRole.EXECUTOR) -> AgentAssignment:
        """
        分配任务给 Agent
        
        Args:
            subtask: 子任务
            agent_id: Agent ID
            role: Agent 角色
            
        Returns:
            分配结果
        """
        assignment = AgentAssignment(
            subtask_id=subtask["id"],
            agent_id=agent_id,
            role=role,
            estimated_completion=datetime.now().timestamp() + 300
        )
        
        self._assignments[subtask["id"]] = assignment
        
        if agent_id in self._agents:
            self._agents[agent_id]["current_task"] = subtask["id"]
            self._agents[agent_id]["status"] = "busy"
        
        return assignment
    
    def sync_state(self) -> dict:
        """
        跨 Agent 状态同步
        
        Returns:
            全局任务状态
        """
        state = {
            "agents": {},
            "tasks": {},
            "pending": len([a for a in self._agents.values() if a["status"] == "available"]),
            "busy": len([a for a in self._agents.values() if a["status"] == "busy"])
        }
        
        for agent_id, agent in self._agents.items():
            state["agents"][agent_id] = {
                "status": agent["status"],
                "current_task": agent["current_task"]
            }
        
        for task_id, assignment in self._assignments.items():
            state["tasks"][task_id] = {
                "agent_id": assignment.agent_id,
                "role": assignment.role.value,
                "completion": assignment.estimated_completion
            }
        
        self._state = state
        return state
    
    def replan(self, failed_task_id: str, error: str) -> list[dict]:
        """
        局部 Replan（避免全局回滚）
        
        Args:
            failed_task_id: 失败的任务 ID
            error: 错误信息
            
        Returns:
            新的执行计划
        """
        new_plan = []
        
        # 找到依赖此任务的其他任务
        dependents = []
        for task_id, deps in self._tasks.get("dependencies", {}).items():
            if failed_task_id in deps:
                dependents.append(task_id)
        
        # 重新分配失败任务
        new_plan.append({
            "action": "retry",
            "task_id": failed_task_id,
            "reason": error
        })
        
        # 如果有依赖任务受影响，标记它们需要重新执行
        for dep in dependents:
            new_plan.append({
                "action": "reexecute",
                "task_id": dep,
                "reason": f"dependency {failed_task_id} failed"
            })
        
        return new_plan
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        return {
            "registered_agents": len(self._agents),
            "active_assignments": len(self._assignments),
            "current_topology": self._topology.value,
            "state": self._state
        }
