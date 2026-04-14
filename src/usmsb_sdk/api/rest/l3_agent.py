# -*- coding: utf-8 -*-
"""
L3 Agent Router - FastAPI HTTP 接口

为 L3Orchestrator 提供 HTTP 接口：

Routes:
- GET  /health                    # 健康检查
- GET  /well-known/agent.json     # Google A2A AgentCard
- GET  /agent/{id}/status         # Agent 状态
- GET  /agent/{id}/goals          # 当前目标
- POST /agent/{id}/goals          # 生成新目标
- POST /agent/{id}/tasks          # 提交任务 (A2A)
- GET  /agent/{id}/tasks/{tid}    # 任务状态
- GET  /agent/{id}/capabilities   # 能力画像
- GET  /agent/{id}/fitness        # 适应度
- GET  /agent/{id}/evolution      # 进化状态
- POST /agent/{id}/evolve         # 触发进化
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["L3 Agent"])

# Global L3Orchestrator registry
_l3_orchestrators: dict[str, Any] = {}


def register_l3_orchestrator(agent_id: str, orchestrator: Any) -> None:
    """注册 L3Orchestrator 实例"""
    _l3_orchestrators[agent_id] = orchestrator
    logger.info(f"Registered L3Orchestrator: {agent_id}")


def get_l3_orchestrator(agent_id: str) -> Any:
    """获取 L3Orchestrator 实例"""
    if agent_id not in _l3_orchestrators:
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    return _l3_orchestrators[agent_id]


# ========== Request/Response Models ==========

class GoalRequest(BaseModel):
    goal_name: str | None = None
    priority: int = 50

class TaskRequest(BaseModel):
    skill_name: str
    input_data: dict
    metadata: dict | None = None

class EvolveRequest(BaseModel):
    force: bool = False

class StatusResponse(BaseModel):
    agent_id: str
    status: str
    generation: int
    fitness: float
    capabilities: dict
    elimination_status: str
    uptime_seconds: float

class GoalResponse(BaseModel):
    id: str
    name: str
    status: str
    priority: int

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: float

class FitnessResponse(BaseModel):
    overall: float
    dimensions: dict
    trend: str
    history_count: int

class EvolutionResponse(BaseModel):
    generation: int
    population_size: int
    can_replicate: bool
    replication_reason: str
    elimination_status: str


# ========== Health & Discovery ==========

@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().timestamp(),
        "agents_registered": len(_l3_orchestrators),
    }


@router.get("/well-known/agent.json")
async def get_agent_card(agent_id: str = "default"):
    """
    获取 Google A2A AgentCard
    
    遵循 Google A2A 协议：
    GET /.well-known/agent.json
    """
    try:
        orch = get_l3_orchestrator(agent_id)
        return JSONResponse(
            content=json.loads(orch.google_a2a.get_agent_card_json())
        )
    except HTTPException:
        # Return default card if agent not found
        return JSONResponse(content={
            "name": f"USMSB Agent {agent_id}",
            "description": "USMSB Silicon-based Life Agent",
            "version": "2.0",
            "capabilities": {
                "streaming": True,
                "pushNotifications": True,
            },
            "skills": [
                {"id": "reasoning", "name": "Reasoning"},
                {"id": "coding", "name": "Coding"},
                {"id": "analysis", "name": "Analysis"},
            ],
        })


# ========== Agent Status ==========

@router.get("/agent/{agent_id}/status", response_model=StatusResponse)
async def get_agent_status(agent_id: str):
    """获取 Agent 完整状态"""
    orch = get_l3_orchestrator(agent_id)
    status = orch.get_agent_status()
    
    return StatusResponse(
        agent_id=agent_id,
        status=status.get("status", "unknown"),
        generation=status.get("generation", 0),
        fitness=status.get("fitness", {}).get("overall", 0.0),
        capabilities=status.get("capabilities", {}),
        elimination_status=status.get("elimination_status", "unknown"),
        uptime_seconds=status.get("uptime_seconds", 0.0),
    )


# ========== Goals ==========

@router.get("/agent/{agent_id}/goals")
async def get_goals(agent_id: str):
    """获取当前目标列表"""
    orch = get_l3_orchestrator(agent_id)
    
    goals = []
    for goal_id, goal in orch._goal_pools.items():
        goals.append({
            "id": goal_id,
            "name": goal.name if hasattr(goal, 'name') else str(goal),
            "status": goal.status if hasattr(goal, 'status') else "unknown",
            "priority": goal.priority if hasattr(goal, 'priority') else 0,
        })
    
    return {"goals": goals, "count": len(goals)}


@router.post("/agent/{agent_id}/goals")
async def generate_goal(agent_id: str, request: GoalRequest):
    """生成新的内在目标"""
    orch = get_l3_orchestrator(agent_id)
    
    # 生成目标
    goals = orch.generate_intrinsic_goals()
    
    return {
        "goals_generated": len(goals),
        "goals": [
            {
                "id": g.id if hasattr(g, 'id') else str(i),
                "name": g.name if hasattr(g, 'name') else str(g),
                "priority": g.priority if hasattr(g, 'priority') else 50,
            }
            for i, g in enumerate(goals)
        ],
    }


# ========== A2A Tasks ==========

@router.post("/agent/{agent_id}/tasks", response_model=TaskResponse)
async def submit_task(agent_id: str, request: TaskRequest):
    """
    提交 A2A 任务
    
    使用 Google A2A 协议提交任务：
    POST /agent/{id}/tasks
    """
    orch = get_l3_orchestrator(agent_id)
    
    # 提交任务
    task_id = await orch.google_a2a.submit_task(
        skill_name=request.skill_name,
        input_data=request.input_data,
        metadata=request.metadata,
    )
    
    return TaskResponse(
        task_id=task_id,
        status="submitted",
        created_at=datetime.now().timestamp(),
    )


@router.get("/agent/{agent_id}/tasks/{task_id}")
async def get_task_status(agent_id: str, task_id: str):
    """获取任务状态"""
    orch = get_l3_orchestrator(agent_id)
    
    status = await orch.google_a2a.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return status


# ========== Capabilities ==========

@router.get("/agent/{agent_id}/capabilities")
async def get_capabilities(agent_id: str):
    """获取能力画像"""
    orch = get_l3_orchestrator(agent_id)
    profile = orch.get_capability_profile()
    
    return profile


# ========== Fitness & Evolution ==========

@router.get("/agent/{agent_id}/fitness", response_model=FitnessResponse)
async def get_fitness(agent_id: str):
    """获取适应度信息"""
    orch = get_l3_orchestrator(agent_id)
    
    # 获取适应度历史
    history = orch.fitness_evaluator.get_history(agent_id, limit=10)
    
    if not history:
        return FitnessResponse(
            overall=0.5,
            dimensions={},
            trend="no_data",
            history_count=0,
        )
    
    latest = history[0]
    trend = orch.get_fitness_trend()
    
    return FitnessResponse(
        overall=latest.overall_score,
        dimensions=latest.dimensions.__dict__ if hasattr(latest.dimensions, '__dict__') else {},
        trend=trend,
        history_count=len(history),
    )


@router.get("/agent/{agent_id}/evolution", response_model=EvolutionResponse)
async def get_evolution_status(agent_id: str):
    """获取进化状态"""
    orch = get_l3_orchestrator(agent_id)
    
    can_replicate, reason = orch.check_can_replicate()
    elim_status = orch.elimination.get_agent_status(agent_id)
    
    return EvolutionResponse(
        generation=orch._generation,
        population_size=len(orch.evolution_controller.population),
        can_replicate=can_replicate,
        replication_reason=reason,
        elimination_status=elim_status.get("status", "unknown"),
    )


@router.post("/agent/{agent_id}/evolve")
async def trigger_evolution(agent_id: str, request: EvolveRequest):
    """触发进化"""
    orch = get_l3_orchestrator(agent_id)
    
    # 记录一些 outcome 数据以触发进化
    if request.force:
        for i in range(6):
            orch.evolution_loop.record_outcome(agent_id, {
                "success": True,
                "quality_score": 0.5 + i * 0.05,
                "value_created": 50 + i * 10,
            })
    
    # 尝试进化
    result = orch.evolution_loop.evolve_if_needed(agent_id)
    
    if result:
        return {
            "evolved": True,
            "generation": result.generation,
            "fitness_before": result.fitness_before,
            "fitness_after": result.fitness_after,
            "mutations": result.mutations[:3],
        }
    else:
        status = orch.evolution_loop.get_evolution_status(agent_id)
        return {
            "evolved": False,
            "reason": status["evolution_reason"],
            "time_since_last_evolution": status["time_since_last_evolution"],
        }


# ========== A2A Protocol (JSON-RPC) ==========

@router.post("/a2a")
async def handle_a2a_json_rpc(request: dict):
    """
    处理 A2A JSON-RPC 2.0 请求
    
    Google A2A 协议接口：
    {
        "jsonrpc": "2.0",
        "id": "...",
        "method": "tasks/submit|tasks/get|agents/card",
        "params": {...}
    }
    """
    # 获取默认 agent
    if _l3_orchestrators:
        agent_id = list(_l3_orchestrators.keys())[0]
        orch = _l3_orchestrators[agent_id]
        return orch.google_a2a.handle_json_rpc_request(request)
    
    return {
        "jsonrpc": "2.0",
        "error": {"code": -32603, "message": "No agents registered"},
        "id": request.get("id"),
    }


# ========== Loop Status ==========

@router.get("/agent/{agent_id}/loops")
async def get_loop_status(agent_id: str):
    """获取 Goal-Action-Outcome Loop 状态"""
    orch = get_l3_orchestrator(agent_id)
    status = orch.get_loop_status()
    
    return status


@router.post("/agent/{agent_id}/run-cycle")
async def run_cycle(agent_id: str):
    """运行一个完整的 Agent 周期"""
    orch = get_l3_orchestrator(agent_id)
    result = orch.run_cycle()
    
    return result
