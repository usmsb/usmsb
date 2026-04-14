# -*- coding: utf-8 -*-
"""
EveningSummary - 晚间总结生成器

每日复盘，包括：
- 今日完成
- 学习教训
- 明日建议
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CompletedTask:
    """已完成任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    quality: float = 0.5  # 0-1
    time_spent: float = 0.0  # 小时
    notes: str = ""


@dataclass
class Learning:
    """今日学习"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    category: str = ""  # skill, knowledge, insight
    source: str = ""  # 来自什么任务


@dataclass
class EveningSummaryReport:
    """晚间总结"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: str = ""  # "2026-04-14"
    
    # 统计数据
    tasks_completed: int = 0
    tasks_incomplete: int = 0
    total_hours_worked: float = 0.0
    productivity_score: float = 0.0  # 0-1
    
    # 完成的任务
    completed_tasks: list[CompletedTask] = field(default_factory=list)
    
    # 未完成任务
    incomplete_tasks: list[str] = field(default_factory=list)
    
    # 学习
    learnings: list[Learning] = field(default_factory=list)
    
    # 教训
    lessons: list[str] = field(default_factory=list)
    
    # 明日建议
    tomorrow_suggestions: list[str] = field(default_factory=list)
    
    # 自我反思
    reflection: str = ""
    
    # 情绪状态
    mood: str = ""
    
    generated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class EveningSummary:
    """
    晚间总结生成器
    
    生成每日复盘。
    """
    
    def __init__(self, user_memory=None, llm_client=None):
        self.user_memory = user_memory
        self.llm_client = llm_client
    
    async def generate(
        self,
        date: str | None = None,
        completed_tasks: list[dict] | None = None,
        incomplete_tasks: list[str] | None = None,
        mood: str = ""
    ) -> EveningSummaryReport:
        """
        生成晚间总结
        
        Args:
            date: 日期
            completed_tasks: 完成的任务
            incomplete_tasks: 未完成的任务
            mood: 情绪状态
            
        Returns:
            EveningSummaryReport
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 处理完成的任务
        completed = []
        total_hours = 0.0
        total_quality = 0.0
        
        for task in (completed_tasks or []):
            ct = CompletedTask(
                title=task.get("title", "未命名"),
                quality=task.get("quality", 0.5),
                time_spent=task.get("time_spent", 0.0),
                notes=task.get("notes", ""),
            )
            completed.append(ct)
            total_hours += ct.time_spent
            total_quality += ct.quality
        
        avg_quality = total_quality / len(completed) if completed else 0.5
        
        # 计算生产力分数
        productivity = self._calculate_productivity(
            len(completed),
            total_hours,
            avg_quality,
            len(incomplete_tasks or [])
        )
        
        # 生成学习和教训
        learnings = self._extract_learnings(completed)
        lessons = self._generate_lessons(completed, incomplete_tasks or [])
        
        # 生成明日建议
        tomorrow = self._generate_tomorrow_suggestions(
            completed,
            incomplete_tasks or [],
            learnings
        )
        
        # 生成反思
        reflection = self._generate_reflection(
            completed,
            incomplete_tasks or [],
            productivity
        )
        
        return EveningSummaryReport(
            date=date,
            tasks_completed=len(completed),
            tasks_incomplete=len(incomplete_tasks or []),
            total_hours_worked=total_hours,
            productivity_score=productivity,
            completed_tasks=completed,
            incomplete_tasks=incomplete_tasks or [],
            learnings=learnings,
            lessons=lessons,
            tomorrow_suggestions=tomorrow,
            reflection=reflection,
            mood=mood,
        )
    
    def _calculate_productivity(
        self,
        completed_count: int,
        hours: float,
        quality: float,
        incomplete_count: int
    ) -> float:
        """计算生产力分数"""
        # 基于完成数量 (40%)
        count_score = min(1.0, completed_count / 5) * 0.4
        
        # 基于时间效率 (30%)
        time_score = min(1.0, hours / 8) * 0.3
        
        # 基于质量 (20%)
        quality_score = quality * 0.2
        
        # 基于完成率 (10%)
        total = completed_count + incomplete_count
        completion_rate = completed_count / total if total > 0 else 0
        completion_score = completion_rate * 0.1
        
        return count_score + time_score + quality_score + completion_score
    
    def _extract_learnings(self, completed: list[CompletedTask]) -> list[Learning]:
        """提取学习"""
        learnings = []
        
        # 基于完成的任务生成学习
        for task in completed:
            if task.quality > 0.7:
                learnings.append(Learning(
                    content=f"成功完成了：{task.title}",
                    category="skill",
                    source=task.title,
                ))
        
        # 添加通用学习
        learnings.append(Learning(
            content="时间管理是生产力的关键",
            category="insight",
            source="general",
        ))
        
        return learnings[:5]  # 最多5个
    
    def _generate_lessons(
        self,
        completed: list[CompletedTask],
        incomplete: list[str]
    ) -> list[str]:
        """生成教训"""
        lessons = []
        
        # 基于未完成任务
        if incomplete:
            lessons.append(f"有{len(incomplete)}个任务未完成，需要改进计划")
        
        # 基于质量
        low_quality = [t for t in completed if t.quality < 0.5]
        if low_quality:
            lessons.append("部分任务质量较低，需要更多时间")
        
        # 基于时间
        long_tasks = [t for t in completed if t.time_spent > 3.0]
        if len(long_tasks) > 2:
            lessons.append("任务时间过长，可能需要拆分")
        
        if not lessons:
            lessons.append("今天表现不错，继续保持")
        
        return lessons
    
    def _generate_tomorrow_suggestions(
        self,
        completed: list[CompletedTask],
        incomplete: list[str],
        learnings: list[Learning]
    ) -> list[str]:
        """生成明日建议"""
        suggestions = []
        
        # 延续未完成任务
        if incomplete:
            suggestions.append(f"优先完成：{', '.join(incomplete[:2])}")
        
        # 延续学习
        if learnings:
            skill_learnings = [l for l in learnings if l.category == "skill"]
            if skill_learnings:
                suggestions.append(f"继续练习：{skill_learnings[0].content[:30]}")
        
        # 通用建议
        suggestions.append("早睡早起，保持精力")
        suggestions.append("先完成最难的任务")
        
        return suggestions[:3]
    
    def _generate_reflection(
        self,
        completed: list[CompletedTask],
        incomplete: list[str],
        productivity: float
    ) -> str:
        """生成自我反思"""
        if productivity > 0.8:
            return "今天是高效的一天！我很好地完成了任务。"
        elif productivity > 0.5:
            return "今天是充实的一天，有些地方可以改进。"
        else:
            return "今天是挑战的一天，需要调整明天的计划。"
    
    def format_report(self, report: EveningSummaryReport) -> str:
        """格式化汇报为文本"""
        lines = [
            f"🌙 晚间总结 - {report.date}",
            "",
            f"📊 今日数据：",
            f"  完成任务：{report.tasks_completed}",
            f"  未完成任务：{report.tasks_incomplete}",
            f"  工作时间：{report.total_hours_worked:.1f}h",
            f"  生产力分数：{report.productivity_score:.0%}",
            "",
        ]
        
        if report.completed_tasks:
            lines.append("✅ 完成的任务：")
            for task in report.completed_tasks:
                quality_bar = "█" * int(task.quality * 5) + "░" * (5 - int(task.quality * 5))
                lines.append(f"  • {task.title} [{quality_bar}]")
            lines.append("")
        
        if report.learnings:
            lines.append("📚 今日学习：")
            for learning in report.learnings:
                lines.append(f"  • {learning.content}")
            lines.append("")
        
        if report.lessons:
            lines.append("💭 教训：")
            for lesson in report.lessons:
                lines.append(f"  • {lesson}")
            lines.append("")
        
        if report.tomorrow_suggestions:
            lines.append("🌅 明日建议：")
            for suggestion in report.tomorrow_suggestions:
                lines.append(f"  • {suggestion}")
            lines.append("")
        
        lines.append(f"🤔 反思：{report.reflection}")
        
        return "\n".join(lines)
    
    def to_dict(self, report: EveningSummaryReport) -> dict:
        """转换为字典"""
        return {
            "id": report.id,
            "date": report.date,
            "tasks_completed": report.tasks_completed,
            "tasks_incomplete": report.tasks_incomplete,
            "total_hours": report.total_hours_worked,
            "productivity_score": report.productivity_score,
            "completed_tasks": [
                {"title": t.title, "quality": t.quality}
                for t in report.completed_tasks
            ],
            "learnings": [
                {"content": l.content, "category": l.category}
                for l in report.learnings
            ],
            "lessons": report.lessons,
            "tomorrow_suggestions": report.tomorrow_suggestions,
            "reflection": report.reflection,
        }
