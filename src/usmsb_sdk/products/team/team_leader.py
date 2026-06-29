# -*- coding: utf-8 -*-
"""
TeamLeader - 团队 Leader Agent

.. deprecated:: v3.0
    本模块为早期内存 dict-CRUD stub（无智能、无经济）。请改用
    `usmsb_sdk.products.team.team_leader_pea.TeamLeaderPea`
    （多 PEA over A2A：LLM 拆解→能力发现组队→联合订单 Shapley 分账）。

负责任务分配、进度跟踪、团队协调。

功能：
- 任务分配给部门 Agent
- 进度跟踪
- 周会组织
- 绩效评估
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class TeamMember:
    """团队成员"""
    id: str
    name: str
    role: str  # engineering, design, product, marketing, etc.
    agent_id: str  # 对应的 Agent ID
    department: str = ""
    skills: list[str] = field(default_factory=list)
    capacity: float = 1.0  # 工作容量 0-1


@dataclass
class TeamTask:
    """团队任务"""
    id: str = ""
    title: str = ""
    description: str = ""
    assignee: str | None = None  # member_id
    status: str = "pending"  # pending, in_progress, review, done
    priority: int = 0  # 1-5
    deadline: float | None = None
    progress: float = 0.0  # 0-1
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Department:
    """部门"""
    id: str
    name: str
    leader_id: str  # member_id
    member_ids: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)


class TeamLeader:
    """
    团队 Leader Agent
    
    管理团队任务和成员。
    
    使用方式：
    ```python
    leader = TeamLeader(team_id="team_001")
    
    # 添加成员
    leader.add_member(member)
    
    # 分配任务
    leader.assign_task(task, member_id)
    
    # 检查进度
    status = leader.get_team_status()
    ```
    """
    
    def __init__(self, team_id: str, team_name: str = ""):
        self.team_id = team_id
        self.team_name = team_name or f"Team {team_id}"
        
        # 成员管理
        self.members: dict[str, TeamMember] = {}
        self.departments: dict[str, Department] = {}
        
        # 任务管理
        self.tasks: dict[str, TeamTask] = {}
        
        # 历史
        self.meetings: list[dict] = []
        self.performance_records: dict[str, list] = {}
        
        print(f"[TeamLeader] {self.team_name} initialized")
    
    # ========== 成员管理 ==========
    
    def add_member(self, member: TeamMember) -> None:
        """添加成员"""
        self.members[member.id] = member
        
        # 按部门分组
        if member.department:
            if member.department not in self.departments:
                self.departments[member.department] = Department(
                    id=member.department,
                    name=member.department,
                    leader_id=member.id,
                )
            self.departments[member.department].member_ids.append(member.id)
        
        print(f"[TeamLeader] Added member: {member.name} ({member.role})")
    
    def remove_member(self, member_id: str) -> bool:
        """移除成员"""
        if member_id in self.members:
            member = self.members[member_id]
            del self.members[member_id]
            
            # 从部门移除
            if member.department in self.departments:
                dept = self.departments[member.department]
                if member_id in dept.member_ids:
                    dept.member_ids.remove(member_id)
            
            return True
        return False
    
    def get_member(self, member_id: str) -> TeamMember | None:
        """获取成员"""
        return self.members.get(member_id)
    
    def list_members(self, department: str | None = None) -> list[TeamMember]:
        """列出成员"""
        if department:
            dept = self.departments.get(department)
            if dept:
                return [self.members[mid] for mid in dept.member_ids if mid in self.members]
            return []
        return list(self.members.values())
    
    # ========== 任务管理 ==========
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: int = 3,
        assignee: str | None = None,
        deadline: float | None = None
    ) -> str:
        """创建任务"""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        task = TeamTask(
            id=task_id,
            title=title,
            description=description,
            priority=priority,
            assignee=assignee,
            deadline=deadline,
        )
        
        self.tasks[task_id] = task
        return task_id
    
    def assign_task(self, task_id: str, member_id: str) -> bool:
        """分配任务"""
        if task_id not in self.tasks or member_id not in self.members:
            return False
        
        self.tasks[task_id].assignee = member_id
        self.tasks[task_id].status = "in_progress"
        
        return True
    
    def update_task_progress(
        self,
        task_id: str,
        progress: float,
        status: str | None = None
    ) -> bool:
        """更新任务进度"""
        if task_id not in self.tasks:
            return False
        
        self.tasks[task_id].progress = min(1.0, max(0.0, progress))
        
        if status:
            self.tasks[task_id].status = status
        elif progress >= 1.0:
            self.tasks[task_id].status = "done"
        
        return True
    
    def get_task(self, task_id: str) -> TeamTask | None:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_member_tasks(self, member_id: str) -> list[TeamTask]:
        """获取成员的任务"""
        return [t for t in self.tasks.values() if t.assignee == member_id]
    
    # ========== 进度跟踪 ==========
    
    def get_team_status(self) -> dict:
        """获取团队状态"""
        total_tasks = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == "done")
        in_progress = sum(1 for t in self.tasks.values() if t.status == "in_progress")
        
        # 按部门统计
        dept_status = {}
        for dept_id, dept in self.departments.items():
            member_tasks = self.get_member_tasks(dept.leader_id)
            dept_completed = sum(1 for t in member_tasks if t.status == "done")
            dept_status[dept_id] = {
                "name": dept.name,
                "member_count": len(dept.member_ids),
                "tasks_completed": dept_completed,
            }
        
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "member_count": len(self.members),
            "task_stats": {
                "total": total_tasks,
                "completed": completed,
                "in_progress": in_progress,
                "pending": total_tasks - completed - in_progress,
            },
            "completion_rate": completed / total_tasks if total_tasks > 0 else 0,
            "departments": dept_status,
        }
    
    def get_overdue_tasks(self) -> list[TeamTask]:
        """获取逾期任务"""
        now = datetime.now().timestamp()
        return [
            t for t in self.tasks.values()
            if t.deadline and t.deadline < now and t.status != "done"
        ]
    
    # ========== 周会 ==========
    
    def prepare_weekly_meeting(self) -> dict:
        """准备周会"""
        # 获取本周任务
        now = datetime.now()
        week_ago = now.timestamp() - 7 * 86400
        
        # 统计完成情况
        completed_this_week = []
        for task in self.tasks.values():
            if task.status == "done":
                completed_this_week.append(task)
        
        # 获取下周任务
        upcoming = [t for t in self.tasks.values() if t.status != "done"]
        upcoming.sort(key=lambda t: t.priority, reverse=True)
        
        return {
            "date": now.strftime("%Y-%m-%d"),
            "completed_count": len(completed_this_week),
            "completed_tasks": [
                {"id": t.id, "title": t.title}
                for t in completed_this_week[:10]
            ],
            "upcoming_count": len(upcoming),
            "high_priority_tasks": [
                {"id": t.id, "title": t.title, "priority": t.priority}
                for t in upcoming[:5]
            ],
            "department_status": self.get_team_status()["departments"],
        }
    
    # ========== 绩效 ==========
    
    def record_performance(
        self,
        member_id: str,
        metric: str,
        value: float
    ) -> None:
        """记录绩效"""
        if member_id not in self.performance_records:
            self.performance_records[member_id] = []
        
        self.performance_records[member_id].append({
            "metric": metric,
            "value": value,
            "timestamp": datetime.now().timestamp(),
        })
    
    def get_member_performance(self, member_id: str) -> dict:
        """获取成员绩效"""
        records = self.performance_records.get(member_id, [])
        
        if not records:
            tasks = self.get_member_tasks(member_id)
            completed = sum(1 for t in tasks if t.status == "done")
            
            return {
                "member_id": member_id,
                "tasks_completed": completed,
                "tasks_in_progress": sum(1 for t in tasks if t.status == "in_progress"),
                "avg_priority": sum(t.priority for t in tasks) / len(tasks) if tasks else 0,
            }
        
        return {
            "member_id": member_id,
            "record_count": len(records),
            "records": records[-10:],  # 最近10条
        }
