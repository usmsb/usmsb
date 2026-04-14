# -*- coding: utf-8 -*-
"""
执行引擎 - Execution Engine

负责：
1. 目标执行 - 将目标转化为具体行动
2. 工具调用 - 调用 Agent 能力
3. 错误处理 - 重试、降级
4. 进度追踪 - 执行状态监控

这是 Harness 架构的核心执行组件
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """执行上下文"""
    execution_id: str = ""
    goal_id: str = ""
    agent_id: str = ""
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: float | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # 执行数据
    current_step: int = 0
    total_steps: int = 0
    steps: list[dict] = field(default_factory=list)
    outputs: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    
    # 重试配置
    retry_count: int = 0
    max_retries: int = 3
    
    def add_step(self, step_type: str, action: str, result: Any = None, error: str = None) -> None:
        """记录执行步骤"""
        step = {
            "step": self.current_step,
            "type": step_type,
            "action": action,
            "timestamp": datetime.now().timestamp(),
            "result": result,
            "error": error
        }
        self.steps.append(step)
        self.current_step += 1
    
    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "progress": f"{self.current_step}/{self.total_steps}",
            "errors": len(self.errors)
        }


class ExecutionResult:
    """执行结果"""
    
    def __init__(
        self,
        success: bool,
        output: Any = None,
        error: str | None = None,
        steps: list[dict] | None = None,
        metadata: dict | None = None
    ):
        self.success = success
        self.output = output
        self.error = error
        self.steps = steps or []
        self.metadata = metadata or {}
        self.timestamp = datetime.now().timestamp()


class ExecutionEngine:
    """
    执行引擎
    
    核心职责：
    1. 目标 → 行动转换
    2. 工具/能力调用
    3. 错误处理与重试
    4. 进度追踪
    """
    
    def __init__(self):
        self._executors: dict[str, Callable] = {}  # name -> callable
        self._policies: dict[str, Any] = {
            "max_retries": 3,
            "retry_delay": 1.0,
            "timeout": 300
        }
        self._executions: dict[str, ExecutionContext] = {}
    
    def register_executor(self, name: str, executor: Callable) -> None:
        """
        注册执行器
        
        Args:
            name: 执行器名称
            executor: 可调用对象 (async function)
        """
        self._executors[name] = executor
    
    async def execute_goal(
        self,
        goal: dict,
        agent_id: str,
        tools: list[str] | None = None
    ) -> ExecutionResult:
        """
        执行目标
        
        Args:
            goal: 目标字典 {id, description, steps, ...}
            agent_id: 执行 Agent ID
            tools: 可用工具列表
            
        Returns:
            ExecutionResult
        """
        execution_id = str(uuid.uuid4())
        context = ExecutionContext(
            execution_id=execution_id,
            goal_id=goal.get("id", ""),
            agent_id=agent_id
        )
        
        self._executions[execution_id] = context
        context.status = ExecutionStatus.RUNNING
        
        try:
            # 解析目标步骤
            steps = goal.get("steps", [{"action": "execute", "description": goal.get("description", "")}])
            context.total_steps = len(steps)
            
            outputs = {}
            for i, step in enumerate(steps):
                context.current_step = i
                action = step.get("action", "execute")
                description = step.get("description", "")
                
                # 执行步骤
                context.add_step(step_type="start", action=description)
                
                try:
                    if action in self._executors:
                        result = await self._executors[action](step, context)
                    else:
                        result = await self._default_executor(step, context)
                    
                    outputs[action] = result
                    context.add_step(step_type="success", action=description, result=result)
                    
                except Exception as e:
                    error_msg = str(e)
                    context.errors.append(error_msg)
                    context.add_step(step_type="error", action=description, error=error_msg)
                    
                    # 重试逻辑
                    if context.retry_count < context.max_retries:
                        context.retry_count += 1
                        context.status = ExecutionStatus.RETRYING
                        continue
                    else:
                        raise
                
                context.status = ExecutionStatus.RUNNING
            
            context.status = ExecutionStatus.COMPLETED
            context.outputs = outputs
            
            return ExecutionResult(
                success=True,
                output=outputs,
                steps=context.steps
            )
            
        except Exception as e:
            context.status = ExecutionStatus.FAILED
            context.errors.append(str(e))
            
            return ExecutionResult(
                success=False,
                error=str(e),
                steps=context.steps
            )
        
        finally:
            context.end_time = datetime.now().timestamp()
    
    async def _default_executor(self, step: dict, context: ExecutionContext) -> Any:
        """默认执行器"""
        # 模拟执行
        await self._sleep(0.1)
        return {"status": "executed", "step": step.get("description")}
    
    async def _sleep(self, seconds: float) -> None:
        """异步睡眠"""
        import asyncio
        await asyncio.sleep(seconds)
    
    def get_execution(self, execution_id: str) -> ExecutionContext | None:
        """获取执行上下文"""
        return self._executors.get(execution_id)
    
    def get_active_executions(self) -> list[ExecutionContext]:
        """获取活跃执行"""
        return [
            ctx for ctx in self._executors.values()
            if ctx.status in [ExecutionStatus.RUNNING, ExecutionStatus.RETRYING]
        ]
    
    def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        ctx = self._executors.get(execution_id)
        if ctx and ctx.status == ExecutionStatus.RUNNING:
            ctx.status = ExecutionStatus.CANCELLED
            ctx.end_time = datetime.now().timestamp()
            return True
        return False
    
    def get_statistics(self) -> dict:
        """获取统计"""
        total = len(self._executors)
        by_status = {}
        for ctx in self._executors.values():
            status = ctx.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "total_executions": total,
            "by_status": by_status,
            "registered_executors": list(self._executors.keys())
        }


class EvaluationEngine:
    """
    评估引擎
    
    负责：
    1. 执行结果评估
    2. 质量评分
    3. 效率分析
    4. 改进建议生成
    """
    
    def __init__(self):
        self._metrics: dict[str, list[float]] = {}  # metric_name -> scores
    
    def evaluate_execution(self, result: ExecutionResult, expected: Any = None) -> dict:
        """
        评估执行结果
        
        Args:
            result: 执行结果
            expected: 期望输出
            
        Returns:
            评估报告
        """
        report = {
            "success": result.success,
            "timestamp": result.timestamp,
            "metrics": {}
        }
        
        # 基础指标
        if result.success:
            report["metrics"]["success_rate"] = 1.0
            report["metrics"]["error_rate"] = 0.0
        else:
            report["metrics"]["success_rate"] = 0.0
            report["metrics"]["error_rate"] = 1.0
        
        # 步骤效率
        if result.steps:
            total_time = 0
            error_count = 0
            for step in result.steps:
                if "timestamp" in step:
                    total_time += 1  # 简化
                if step.get("error"):
                    error_count += 1
            
            report["metrics"]["step_count"] = len(result.steps)
            report["metrics"]["error_count"] = error_count
            report["metrics"]["step_success_rate"] = (len(result.steps) - error_count) / max(1, len(result.steps))
        
        # 输出质量（如果有期望值）
        if expected and result.output:
            similarity = self._calculate_similarity(result.output, expected)
            report["metrics"]["output_quality"] = similarity
        
        # 总体评分
        report["overall_score"] = self._calculate_overall_score(report["metrics"])
        
        return report
    
    def _calculate_similarity(self, output: Any, expected: Any) -> float:
        """计算输出相似度（简化版）"""
        if output == expected:
            return 1.0
        if isinstance(output, dict) and isinstance(expected, dict):
            matches = sum(1 for k in expected if k in output)
            return matches / max(1, len(expected))
        return 0.5
    
    def _calculate_overall_score(self, metrics: dict) -> float:
        """计算总体评分"""
        weights = {
            "success_rate": 0.4,
            "step_success_rate": 0.3,
            "output_quality": 0.3
        }
        
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                score += metrics[metric] * weight
        
        return score
    
    def record_metric(self, metric_name: str, value: float) -> None:
        """记录指标历史"""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        self._metrics[metric_name].append(value)
    
    def get_metric_trend(self, metric_name: str, window: int = 10) -> dict:
        """获取指标趋势"""
        values = self._metrics.get(metric_name, [])[-window:]
        if not values:
            return {"avg": 0, "min": 0, "max": 0, "count": 0}
        
        return {
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
    
    def get_statistics(self) -> dict:
        """获取统计"""
        trends = {}
        for metric_name in self._metrics:
            trends[metric_name] = self.get_metric_trend(metric_name)
        
        return {
            "metrics": list(self._metrics.keys()),
            "trends": trends
        }
