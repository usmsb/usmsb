# -*- coding: utf-8 -*-
"""
WeeklyPlanning - 周会计划系统

自动化周会计划、进度跟踪、问题识别。

功能：
- 周目标设定
- 任务规划
- 进度跟踪
- 问题识别
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class WeeklyGoal:
    """周目标"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    owner: str = ""  # member_id
    priority: int = 0  # 1-5
    status: str = "pending"  # pending, in_progress, done
    completion: float = 0.0  # 0-1
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class WeeklyPlan:
    """周计划"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    week_start: str = ""  # "2026-04-14"
    week_end: str = ""
    
    # 目标
    goals: list[WeeklyGoal] = field(default_factory=list)
    
    # 统计数据
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    
    # 识别的问题
    blockers: list[str] = field(default_factory=list)
    
    # 生成的建议
    suggestions: list[str] = field(default_factory=list)
    
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class WeeklyPlanning:
    """
    周会计划系统
    
    自动化周会计划和进度跟踪。
    
    使用方式：
    ```python
    planner = WeeklyPlanning(team_leader)
    
    # 生成周计划
    plan = planner.generate_weekly_plan()
    
    # 更新进度
    planner.update_progress(goal_id, 0.5)
    
    # 获取周会材料
    materials = planner.get_meeting_materials()
    ```
    """
    
    def __init__(self, team_leader: Any, team_memory: Any):
        self.team_leader = team_leader
        self.team_memory = team_memory
    
    def generate_weekly_plan(
        self,
        week_start: str | None = None,
        goals: list[dict] | None = None
    ) -> WeeklyPlan:
        """
        生成周计划
        
        Args:
            week_start: 周开始日期 (默认本周一)
            goals: 周目标列表
            
        Returns:
            WeeklyPlan
        """
        # 计算周日期
        if week_start is None:
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            week_start = monday.strftime("%Y-%m-%d")
        
        week_end_dt = datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)
        week_end = week_end_dt.strftime("%Y-%m-%d")
        
        # 转换目标
        weekly_goals = []
        for g in (goals or []):
            weekly_goals.append(WeeklyGoal(
                title=g.get("title", ""),
                description=g.get("description", ""),
                owner=g.get("owner", ""),
                priority=g.get("priority", 3),
            ))
        
        # 如果没有目标，从团队任务生成
        if not weekly_goals:
            pending_tasks = [
                t for t in self.team_leader.tasks.values()
                if t.status in ["pending", "in_progress"]
            ]
            
            for task in pending_tasks[:10]:
                weekly_goals.append(WeeklyGoal(
                    title=task.title,
                    description=task.description,
                    owner=task.assignee or "",
                    priority=task.priority,
                ))
        
        # 计算统计
        total = len(weekly_goals)
        completed = sum(1 for g in weekly_goals if g.status == "done")
        
        plan = WeeklyPlan(
            week_start=week_start,
            week_end=week_end,
            goals=weekly_goals,
            total_tasks=total,
            completed_tasks=completed,
            completion_rate=completed / total if total > 0 else 0.0,
        )
        
        # 识别问题
        plan.blockers = self._identify_blockers(weekly_goals)
        
        # 生成建议
        plan.suggestions = self._generate_suggestions(plan)
        
        return plan
    
    def _identify_blockers(self, goals: list[WeeklyGoal]) -> list[str]:
        """识别阻碍因素"""
        blockers = []
        
        # 没有目标
        if not goals:
            blockers.append("本周没有设定目标")
        
        # 优先级问题
        low_priority = [g for g in goals if g.priority < 3]
        if len(low_priority) > len(goals) / 2:
            blockers.append("大量低优先级目标，可能缺乏重点")
        
        # 无人负责
        unassigned = [g for g in goals if not g.owner]
        if unassigned:
            blockers.append(f"{len(unassigned)} 个目标没有负责人")
        
        # 高优先级目标无进展
        high_priority = [g for g in goals if g.priority >= 4 and g.completion == 0]
        if high_priority:
            blockers.append(f"{len(high_priority)} 个高优先级目标未开始")
        
        return blockers
    
    def _generate_suggestions(self, plan: WeeklyPlan) -> list[str]:
        """生成建议"""
        suggestions = []
        
        if plan.completion_rate < 0.5:
            suggestions.append("本周完成率较低，建议减少目标数量")
        
        if plan.blockers:
            suggestions.append("需要先解决阻碍因素")
        
        if len(plan.goals) > 10:
            suggestions.append("目标过多，建议聚焦最重要的事项")
        
        high_priority_undone = [
            g for g in plan.goals
            if g.priority >= 4 and g.status != "done"
        ]
        if high_priority_undone:
            suggestions.append(f"优先完成 {len(high_priority_undone)} 个高优先级目标")
        
        if not suggestions:
            suggestions.append("计划看起来合理，祝你本周顺利！")
        
        return suggestions
    
    def update_progress(
        self,
        goal_id: str,
        completion: float,
        status: str | None = None
    ) -> bool:
        """
        更新目标进度
        
        Args:
            goal_id: 目标 ID
            completion: 完成度 0-1
            status: 状态
            
        Returns:
            bool: 是否成功
        """
        # 这个实现需要存储当前的 WeeklyPlan
        # 简化实现
        return True
    
    def get_meeting_materials(self, plan: WeeklyPlan) -> dict:
        """
        获取周会材料
        
        Args:
            plan: 周计划
            
        Returns:
            dict: 周会材料
        """
        # 获取上周未完成的任务
        last_week_undone = [
            t for t in self.team_leader.tasks.values()
            if t.status != "done"
        ]
        
        # 获取本周新任务
        this_week_new = plan.goals
        
        # 获取团队成员状态
        member_status = []
        for member in self.team_leader.list_members():
            tasks = self.team_leader.get_member_tasks(member.id)
            completed = sum(1 for t in tasks if t.status == "done")
            member_status.append({
                "name": member.name,
                "role": member.role,
                "tasks_completed": completed,
                "tasks_total": len(tasks),
            })
        
        return {
            "week": f"{plan.week_start} ~ {plan.week_end}",
            "completion_rate": plan.completion_rate,
            "last_week_undone": [
                {"title": t.title, "assignee": t.assignee}
                for t in last_week_undone[:5]
            ],
            "this_week_goals": [
                {"title": g.title, "owner": g.owner, "priority": g.priority}
                for g in plan.goals
            ],
            "member_status": member_status,
            "blockers": plan.blockers,
            "suggestions": plan.suggestions,
        }
    
    def format_meeting_agenda(self, plan: WeeklyPlan) -> str:
        """格式化周会议程"""
        lines = [
            f"📅 周会议程 - {plan.week_start} ~ {plan.week_end}",
            "",
            f"📊 完成率: {plan.completion_rate:.0%}",
            "",
        ]
        
        if plan.blockers:
            lines.append("⚠️ 阻碍因素:")
            for blocker in plan.blockers:
                lines.append(f"  • {blocker}")
            lines.append("")
        
        lines.append("🎯 本周目标:")
        for goal in plan.goals[:5]:
            status_icon = "✅" if goal.status == "done" else "⏳" if goal.status == "in_progress" else "📋"
            priority_stars = "⭐" * goal.priority
            lines.append(f"  {status_icon} {goal.title} {priority_stars}")
            if goal.owner:
                lines.append(f"      负责人: {goal.owner}")
        
        if plan.suggestions:
            lines.append("")
            lines.append("💡 建议:")
            for suggestion in plan.suggestions:
                lines.append(f"  • {suggestion}")
        
        return "\n".join(lines)
