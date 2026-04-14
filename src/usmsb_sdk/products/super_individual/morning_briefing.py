# -*- coding: utf-8 -*-
"""
MorningBriefing - 早晨汇报生成器

每日计划生成，包括：
- 今日目标
- 时间安排
- 优先级
- 建议
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class DailyGoal:
    """每日目标"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    priority: int = 0  # 1-5, 5最高
    estimated_time: float = 0.0  # 小时
    category: str = ""  # work, personal, health, etc.
    completed: bool = False


@dataclass
class ScheduleBlock:
    """日程块"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_time: str = ""  # "09:00"
    end_time: str = ""
    title: str = ""
    description: str = ""
    goal_id: str | None = None  # 关联的目标


@dataclass
class MorningBriefingReport:
    """早晨汇报"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: str = ""  # "2026-04-14"
    
    # 天气信息（可选）
    weather: str = ""
    temperature: str = ""
    
    # 今日概览
    focus_theme: str = ""  # 今日主题
    goal_count: int = 0
    total_estimated_hours: float = 0.0
    
    # 目标
    goals: list[DailyGoal] = field(default_factory=list)
    
    # 日程
    schedule: list[ScheduleBlock] = field(default_factory=list)
    
    # 建议
    suggestions: list[str] = field(default_factory=list)
    
    # 用户价值观提醒
    value_reminders: list[str] = field(default_factory=list)
    
    # 生成时间
    generated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class MorningBriefing:
    """
    早晨汇报生成器
    
    生成每日的计划汇报。
    """
    
    def __init__(self, user_memory=None, llm_client=None):
        self.user_memory = user_memory
        self.llm_client = llm_client
        
        # 默认日程模板
        self.default_schedule = [
            ("09:00", "10:00", "深度工作"),
            ("10:00", "10:30", "休息"),
            ("10:30", "12:00", "核心任务"),
            ("12:00", "13:30", "午餐休息"),
            ("13:30", "15:00", "协作会议"),
            ("15:00", "15:30", "休息"),
            ("15:30", "17:00", "执行任务"),
            ("17:00", "18:00", "收尾工作"),
        ]
    
    async def generate(
        self,
        date: str | None = None,
        pending_tasks: list[dict] | None = None,
        calendar_events: list[dict] | None = None
    ) -> MorningBriefingReport:
        """
        生成早晨汇报
        
        Args:
            date: 日期 (默认今天)
            pending_tasks: 待处理任务
            calendar_events: 日历事件
            
        Returns:
            MorningBriefingReport
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 获取用户价值观
        value_reminders = self._get_value_reminders()
        
        # 生成目标
        goals = self._generate_goals(pending_tasks or [])
        
        # 生成日程
        schedule = self._generate_schedule(calendar_events or [], goals)
        
        # 生成建议
        suggestions = self._generate_suggestions(goals, value_reminders)
        
        # 生成主题
        focus_theme = self._generate_focus_theme(goals)
        
        # 计算总时间
        total_hours = sum(g.estimated_time for g in goals)
        
        return MorningBriefingReport(
            date=date,
            focus_theme=focus_theme,
            goal_count=len(goals),
            total_estimated_hours=total_hours,
            goals=goals,
            schedule=schedule,
            suggestions=suggestions,
            value_reminders=value_reminders,
        )
    
    def _get_value_reminders(self) -> list[str]:
        """获取价值观提醒"""
        if not self.user_memory or not self.user_memory.profile:
            return []
        
        reminders = []
        for value in self.user_memory.profile.values[:3]:
            if value.strength > 0.7:
                reminders.append(f"记住你的价值观：{value.name}")
        
        return reminders
    
    def _generate_goals(self, pending_tasks: list[dict]) -> list[DailyGoal]:
        """生成今日目标"""
        goals = []
        
        # 从待处理任务生成
        for task in pending_tasks[:5]:
            goal = DailyGoal(
                title=task.get("title", "未命名任务"),
                description=task.get("description", ""),
                priority=task.get("priority", 3),
                estimated_time=task.get("estimated_hours", 1.0),
                category=task.get("category", "work"),
            )
            goals.append(goal)
        
        # 如果没有任务，添加默认目标
        if not goals:
            goals.append(DailyGoal(
                title="深度工作",
                description="进行2小时的深度工作",
                priority=5,
                estimated_time=2.0,
                category="work",
            ))
            goals.append(DailyGoal(
                title="学习",
                description="学习新知识1小时",
                priority=3,
                estimated_time=1.0,
                category="personal",
            ))
        
        # 按优先级排序
        goals.sort(key=lambda g: g.priority, reverse=True)
        
        return goals
    
    def _generate_schedule(
        self,
        calendar_events: list[dict],
        goals: list[DailyGoal]
    ) -> list[ScheduleBlock]:
        """生成日程"""
        schedule = []
        
        # 合并日历事件
        all_blocks = []
        
        # 添加日历事件
        for event in calendar_events:
            all_blocks.append(ScheduleBlock(
                start_time=event.get("start", ""),
                end_time=event.get("end", ""),
                title=event.get("title", "日历事件"),
                description=event.get("description", ""),
            ))
        
        # 如果日程不足，使用默认模板
        if len(all_blocks) < 3:
            for start, end, title in self.default_schedule[:5]:
                all_blocks.append(ScheduleBlock(
                    start_time=start,
                    end_time=end,
                    title=title,
                    description="",
                ))
        
        # 按时间排序
        all_blocks.sort(key=lambda b: b.start_time)
        
        return all_blocks[:8]  # 最多8个
    
    def _generate_suggestions(
        self,
        goals: list[DailyGoal],
        value_reminders: list[str]
    ) -> list[str]:
        """生成建议"""
        suggestions = []
        
        # 基于目标
        if len(goals) > 3:
            suggestions.append("今天任务较多，建议先完成最重要的3个")
        
        # 基于价值观
        suggestions.extend(value_reminders[:2])
        
        # 通用建议
        suggestions.append("保持专注，避免多任务切换")
        suggestions.append("记得适时休息，保持精力")
        
        return suggestions
    
    def _generate_focus_theme(self, goals: list[DailyGoal]) -> str:
        """生成今日主题"""
        if not goals:
            return "准备迎接新的一天"
        
        # 统计类别
        categories = {}
        for goal in goals:
            cat = goal.category
            categories[cat] = categories.get(cat, 0) + goal.priority
        
        # 找最重要的类别
        if categories:
            dominant = max(categories.items(), key=lambda x: x[1])
            themes = {
                "work": "高效工作",
                "personal": "个人成长",
                "health": "健康生活",
                "social": "社交连接",
            }
            return themes.get(dominant[0], f"专注{dominant[0]}")
        
        return "充实的一天"
    
    def format_report(self, report: MorningBriefingReport) -> str:
        """格式化汇报为文本"""
        lines = [
            f"☀️ 早晨汇报 - {report.date}",
            f"主题：{report.focus_theme}",
            "",
            "📋 今日目标：",
        ]
        
        for i, goal in enumerate(report.goals, 1):
            priority_stars = "⭐" * goal.priority
            lines.append(f"  {i}. {goal.title} {priority_stars}")
            if goal.description:
                lines.append(f"     {goal.description}")
            lines.append(f"     预计: {goal.estimated_time}h")
        
        lines.append("")
        lines.append("📅 日程：")
        for block in report.schedule:
            lines.append(f"  {block.start_time}-{block.end_time} {block.title}")
        
        if report.suggestions:
            lines.append("")
            lines.append("💡 建议：")
            for suggestion in report.suggestions:
                lines.append(f"  • {suggestion}")
        
        if report.value_reminders:
            lines.append("")
            lines.append("🎯 价值观提醒：")
            for reminder in report.value_reminders:
                lines.append(f"  • {reminder}")
        
        return "\n".join(lines)
    
    def to_dict(self, report: MorningBriefingReport) -> dict:
        """转换为字典"""
        return {
            "id": report.id,
            "date": report.date,
            "focus_theme": report.focus_theme,
            "goals": [
                {
                    "id": g.id,
                    "title": g.title,
                    "priority": g.priority,
                    "estimated_time": g.estimated_time,
                    "category": g.category,
                    "completed": g.completed,
                }
                for g in report.goals
            ],
            "schedule": [
                {
                    "start": b.start_time,
                    "end": b.end_time,
                    "title": b.title,
                }
                for b in report.schedule
            ],
            "suggestions": report.suggestions,
            "value_reminders": report.value_reminders,
            "total_hours": report.total_estimated_hours,
        }
