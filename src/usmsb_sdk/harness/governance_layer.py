# -*- coding: utf-8 -*-
"""
治理运营层 - Governance Layer

经验沉淀飞轮：
1. 轨迹记录 → 观测体系捕获
2. 质量评估 → 治理体系筛选
3. 案例生成 → 知识体系承载
4. 规则演化 → 门控体系吸收

全链路 Trace：
- 跨 Agent 追踪
- 性能监控
- 异常检测
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TrajectoryStatus(Enum):
    """轨迹状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class TrajectoryRecord:
    """轨迹记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    agent_id: str = ""
    start_time: float = field(default_factory=lambda: datetime.now().timestamp())
    end_time: float | None = None
    status: TrajectoryStatus = TrajectoryStatus.RUNNING
    
    # 执行数据
    steps: list[dict] = field(default_factory=list)
    inputs: dict = field(default_factory=dict)
    outputs: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    
    # 评估数据
    quality_score: float | None = None
    efficiency_score: float | None = None
    metadata: dict = field(default_factory=dict)
    
    def add_step(self, step: dict) -> None:
        """添加执行步骤"""
        step["timestamp"] = datetime.now().timestamp()
        self.steps.append(step)
    
    def complete(self, status: TrajectoryStatus, outputs: dict | None = None) -> None:
        """完成轨迹"""
        self.end_time = datetime.now().timestamp()
        self.status = status
        if outputs:
            self.outputs = outputs
    
    def add_error(self, error: str) -> None:
        """添加错误"""
        self.errors.append(error)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "duration": self.end_time - self.start_time if self.end_time else None,
            "steps_count": len(self.steps),
            "errors_count": len(self.errors),
            "quality_score": self.quality_score,
        }


@dataclass
class CaseRecord:
    """案例记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trajectory_id: str = ""
    task_type: str = ""
    task_description: str = ""
    outcome: str = ""  # success / failure
    lessons: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    quality: float = 0.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class ExperienceRepository:
    """
    经验仓库
    
    存储和检索历史案例、模式
    """
    
    def __init__(self):
        self._trajectories: dict[str, TrajectoryRecord] = {}
        self._cases: dict[str, CaseRecord] = {}
        self._patterns: dict[str, dict] = {}
        self._case_index: dict[str, list[str]] = {}  # task_type -> case_ids
    
    def record_trajectory(self, trajectory: TrajectoryRecord) -> str:
        """记录轨迹"""
        self._trajectories[trajectory.id] = trajectory
        return trajectory.id
    
    def get_trajectory(self, trajectory_id: str) -> TrajectoryRecord | None:
        """获取轨迹"""
        return self._trajectories.get(trajectory_id)
    
    def generate_case(self, trajectory_id: str) -> str | None:
        """从轨迹生成案例"""
        trajectory = self._trajectories.get(trajectory_id)
        if not trajectory:
            return None
        
        # 提取教训
        lessons = self._extract_lessons(trajectory)
        
        # 提取模式
        patterns = self._extract_patterns(trajectory)
        
        case = CaseRecord(
            trajectory_id=trajectory_id,
            task_type=trajectory.task_id.split("_")[0] if trajectory.task_id else "unknown",
            task_description=str(trajectory.inputs),
            outcome="success" if trajectory.status == TrajectoryStatus.COMPLETED else "failure",
            lessons=lessons,
            patterns=patterns,
            quality=trajectory.quality_score or 0.0
        )
        
        self._cases[case.id] = case
        
        # 更新索引
        if case.task_type not in self._case_index:
            self._case_index[case.task_type] = []
        self._case_index[case.task_type].append(case.id)
        
        return case.id
    
    def _extract_lessons(self, trajectory: TrajectoryRecord) -> list[str]:
        """从轨迹提取教训"""
        lessons = []
        
        if trajectory.status == TrajectoryStatus.FAILED:
            for error in trajectory.errors:
                lessons.append(f"失败模式: {error}")
        
        for step in trajectory.steps:
            if step.get("type") == "retry":
                lessons.append(f"需要重试的操作")
        
        return lessons
    
    def _extract_patterns(self, trajectory: TrajectoryRecord) -> list[str]:
        """从轨迹提取模式"""
        patterns = []
        
        if len(trajectory.steps) > 10:
            patterns.append("长执行链")
        
        if trajectory.errors:
            patterns.append("错误处理需求")
        
        return patterns
    
    def query_similar_cases(self, task_description: str, limit: int = 5) -> list[CaseRecord]:
        """查询相似案例"""
        keywords = set(task_description.lower().split())
        scored = []
        
        for case in self._cases.values():
            score = sum(1 for kw in keywords if kw in case.task_description.lower())
            if score > 0:
                scored.append((score, case))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]
    
    def get_statistics(self) -> dict:
        """获取统计"""
        return {
            "trajectories": len(self._trajectories),
            "cases": len(self._cases),
            "patterns": len(self._patterns),
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """计算成功率"""
        if not self._trajectories:
            return 0.0
        
        completed = [t for t in self._trajectories.values() 
                    if t.status in [TrajectoryStatus.COMPLETED, TrajectoryStatus.FAILED]]
        if not completed:
            return 0.0
        
        successes = sum(1 for t in completed if t.status == TrajectoryStatus.COMPLETED)
        return successes / len(completed)


class GovernanceLayer:
    """
    治理运营层
    
    核心功能：
    1. 全链路轨迹追踪
    2. 经验沉淀飞轮
    3. 三层评估（自动/模型/人工）
    """
    
    def __init__(self):
        self.experience = ExperienceRepository()
        self._tracing_enabled = True
        self._active_traces: dict[str, TrajectoryRecord] = {}
    
    def start_trace(self, task_id: str, agent_id: str, inputs: dict) -> str:
        """
        开始轨迹追踪
        
        Args:
            task_id: 任务 ID
            agent_id: Agent ID
            inputs: 输入数据
            
        Returns:
            轨迹 ID
        """
        trajectory = TrajectoryRecord(
            task_id=task_id,
            agent_id=agent_id,
            inputs=inputs
        )
        
        self._active_traces[trajectory.id] = trajectory
        self.experience.record_trajectory(trajectory)
        
        return trajectory.id
    
    def add_step(self, trace_id: str, step: dict) -> None:
        """添加追踪步骤"""
        trajectory = self._active_traces.get(trace_id) or self.experience.get_trajectory(trace_id)
        if trajectory:
            trajectory.add_step(step)
    
    def end_trace(self, trace_id: str, status: TrajectoryStatus, outputs: dict | None = None) -> None:
        """结束轨迹追踪"""
        trajectory = self._active_traces.get(trace_id)
        if trajectory:
            trajectory.complete(status, outputs)
            self._active_traces.pop(trace_id, None)
            
            # 如果是失败轨迹，生成案例
            if status == TrajectoryStatus.FAILED:
                self.experience.generate_case(trace_id)
    
    def evaluate_quality(self, trace_id: str) -> float:
        """
        自动质量评估
        
        Args:
            trace_id: 轨迹 ID
            
        Returns:
            质量分数 (0-1)
        """
        trajectory = self.experience.get_trajectory(trace_id)
        if not trajectory:
            return 0.0
        
        # 简单评估逻辑
        score = 1.0
        
        # 错误惩罚
        score -= len(trajectory.errors) * 0.1
        
        # 步骤过多惩罚
        if len(trajectory.steps) > 20:
            score -= 0.2
        
        # 时间过长惩罚
        if trajectory.end_time and trajectory.start_time:
            duration = trajectory.end_time - trajectory.start_time
            if duration > 3600:  # 超过 1 小时
                score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def run_evaluation_flywheel(self) -> dict:
        """
        运行评估飞轮
        
        轨迹 → 评估 → 案例生成 → 规则演化
        """
        results = {
            "trajectories_processed": 0,
            "cases_generated": 0,
            "quality_scores_updated": 0
        }
        
        # 处理未评估的轨迹
        for trajectory in self.experience._trajectories.values():
            if trajectory.quality_score is None:
                score = self.evaluate_quality(trajectory.id)
                trajectory.quality_score = score
                results["quality_scores_updated"] += 1
                results["trajectories_processed"] += 1
                
                # 如果质量低，生成案例
                if score < 0.5:
                    self.experience.generate_case(trajectory.id)
                    results["cases_generated"] += 1
        
        return results
    
    def get_trace_summary(self, trace_id: str) -> dict | None:
        """获取轨迹摘要"""
        trajectory = self.experience.get_trajectory(trace_id)
        if not trajectory:
            return None
        
        return {
            "id": trajectory.id,
            "task_id": trajectory.task_id,
            "agent_id": trajectory.agent_id,
            "status": trajectory.status.value,
            "duration": trajectory.end_time - trajectory.start_time if trajectory.end_time else None,
            "steps": len(trajectory.steps),
            "errors": len(trajectory.errors),
            "quality": trajectory.quality_score
        }
    
    def get_statistics(self) -> dict:
        """获取治理统计"""
        return {
            "experience": self.experience.get_statistics(),
            "active_traces": len(self._active_traces),
            "tracing_enabled": self._tracing_enabled
        }
