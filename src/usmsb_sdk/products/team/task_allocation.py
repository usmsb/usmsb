# -*- coding: utf-8 -*-
"""
TaskAllocation - 任务自动分配

自动将任务分配给最合适的团队成员。

功能：
- 基于能力匹配
- 基于容量平衡
- 优先级调度
"""

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AllocationResult:
    """分配结果"""
    task_id: str
    member_id: str
    member_name: str
    confidence: float  # 分配置信度
    reason: str  # 分配原因


class TaskAllocation:
    """
    任务自动分配器
    
    根据能力、容量、优先级自动分配任务。
    
    使用方式：
    ```python
    allocator = TaskAllocation(team_leader)
    
    # 分配任务
    result = allocator.allocate_task(task_id)
    
    # 批量分配
    results = allocator.allocate_all_pending()
    ```
    """
    
    def __init__(self, team_leader: Any):
        self.team_leader = team_leader
    
    def allocate_task(self, task_id: str) -> AllocationResult | None:
        """
        分配单个任务
        
        Args:
            task_id: 任务 ID
            
        Returns:
            AllocationResult 或 None
        """
        task = self.team_leader.get_task(task_id)
        if not task:
            return None
        
        # 如果已分配，跳过
        if task.assignee:
            member = self.team_leader.get_member(task.assignee)
            return AllocationResult(
                task_id=task_id,
                member_id=task.assignee,
                member_name=member.name if member else "Unknown",
                confidence=1.0,
                reason="Already assigned"
            )
        
        # 找最佳成员
        candidates = self._find_candidates(task)
        
        if not candidates:
            return None
        
        # 选择最佳候选
        best = candidates[0]
        member = self.team_leader.get_member(best)
        
        # 执行分配
        self.team_leader.assign_task(task_id, best)
        
        return AllocationResult(
            task_id=task_id,
            member_id=best,
            member_name=member.name if member else "Unknown",
            confidence=best["score"],
            reason=best["reason"],
        )
    
    def _find_candidates(self, task: Any) -> list[dict]:
        """
        找到合适的候选人
        
        Returns:
            list of {"member_id": str, "score": float, "reason": str}
        """
        candidates = []
        members = self.team_leader.list_members()
        
        for member in members:
            score = 0.0
            reasons = []
            
            # 1. 能力匹配 (40%)
            skill_match = self._calculate_skill_match(member, task)
            score += skill_match * 0.4
            if skill_match > 0.5:
                reasons.append(f"技能匹配度: {skill_match:.0%}")
            
            # 2. 容量 (30%)
            capacity_score = self._calculate_capacity(member)
            score += capacity_score * 0.3
            if capacity_score > 0.7:
                reasons.append(f"可用容量: {capacity_score:.0%}")
            
            # 3. 历史表现 (20%)
            perf_score = self._calculate_performance(member)
            score += perf_score * 0.2
            if perf_score > 0.7:
                reasons.append(f"历史绩效: {perf_score:.0%}")
            
            # 4. 优先级加权 (10%)
            # 高优先级任务给高绩效成员
            priority_boost = (task.priority / 5.0) * (perf_score) * 0.1
            score += priority_boost
            
            if score > 0.3:  # 最低阈值
                candidates.append({
                    "member_id": member.id,
                    "score": score,
                    "reason": ", ".join(reasons) if reasons else "Default allocation"
                })
        
        # 按分数排序
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return candidates
    
    def _calculate_skill_match(self, member: Any, task: Any) -> float:
        """计算技能匹配度"""
        if not member.skills:
            return 0.5  # 默认
        
        # 简化：检查任务描述是否包含成员技能
        task_text = (task.title + " " + task.description).lower()
        skill_matches = sum(1 for skill in member.skills if skill.lower() in task_text)
        
        return skill_matches / len(member.skills) if member.skills else 0.5
    
    def _calculate_capacity(self, member: Any) -> float:
        """计算可用容量"""
        # 当前任务数
        current_tasks = len(self.team_leader.get_member_tasks(member.id))
        
        # 估算剩余容量
        workload = current_tasks * 0.2  # 每个任务约 20% 容量
        remaining = max(0, member.capacity - workload)
        
        return min(1.0, remaining / member.capacity) if member.capacity > 0 else 0
    
    def _calculate_performance(self, member: Any) -> float:
        """计算历史绩效"""
        perf = self.team_leader.get_member_performance(member.id)
        
        if "record_count" in perf:
            records = perf.get("records", [])
            if records:
                avg_value = sum(r["value"] for r in records) / len(records)
                return min(1.0, avg_value)
        
        # 基于完成的任务数估算
        completed = perf.get("tasks_completed", 0)
        if completed >= 10:
            return 0.9
        elif completed >= 5:
            return 0.7
        elif completed >= 1:
            return 0.5
        return 0.3
    
    def allocate_all_pending(self) -> list[AllocationResult]:
        """
        分配所有待分配任务
        
        Returns:
            list[AllocationResult]
        """
        results = []
        
        pending_tasks = [
            t for t in self.team_leader.tasks.values()
            if t.status == "pending" and not t.assignee
        ]
        
        # 按优先级排序
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        for task in pending_tasks:
            result = self.allocate_task(task.id)
            if result:
                results.append(result)
        
        return results
    
    def rebalance_team(self) -> dict:
        """
        重新平衡团队工作量
        
        Returns:
            dict: 重新分配结果
        """
        # 找到过载的成员
        overloaded = []
        underloaded = []
        
        for member in self.team_leader.list_members():
            current_tasks = len(self.team_leader.get_member_tasks(member.id))
            if current_tasks > 5:  # 过载阈值
                overloaded.append(member.id)
            elif current_tasks < 2:  # 欠载
                underloaded.append(member.id)
        
        # 从过载成员转移任务到欠载成员
        moved_count = 0
        for member_id in overloaded:
            member_tasks = self.team_leader.get_member_tasks(member_id)
            for task in member_tasks[:2]:  # 最多转移2个
                if underloaded:
                    target_id = underloaded.pop(0)
                    self.team_leader.assign_task(task.id, target_id)
                    moved_count += 1
        
        return {
            "overloaded_members": overloaded,
            "underloaded_members": underloaded,
            "tasks_moved": moved_count,
        }
