"""
目标生成器 - Goal Generator

自主生成学习目标
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    GoalPriority,
    LearningGoal,
    LearningType,
)

logger = logging.getLogger(__name__)


@dataclass
class GoalTemplate:
    """目标模板"""

    name: str
    description: str
    priority: GoalPriority
    learning_type: LearningType
    estimated_duration: float
    prerequisites: list[str] = field(default_factory=list)
    success_criteria: dict[str, Any] = field(default_factory=dict)


class GoalGenerator:
    """
    目标生成器

    核心职责：
    1. 目标自生成 - 基于系统状态自主生成目标
    2. 目标优先级排序 - 评估和排序目标重要性
    3. 目标分解 - 将大目标分解为子目标
    4. 目标依赖分析 - 分析目标间依赖关系
    5. 目标调度 - 制定目标执行计划
    """

    def __init__(self, llm_manager=None, capability_assessor=None, curiosity_engine=None):
        self.llm = llm_manager
        self.capability_assessor = capability_assessor
        self.curiosity_engine = curiosity_engine

        self._active_goals: dict[str, LearningGoal] = {}
        self._completed_goals: list[LearningGoal] = []
        self._goal_templates: list[GoalTemplate] = []

        self._goal_graph: dict[str, list[str]] = {}
        self._generation_count: int = 0

        self._initialized = False

    async def initialize(self):
        """初始化目标生成器"""
        if self._initialized:
            return

        self._initialize_templates()

        self._initialized = True
        logger.info("GoalGenerator initialized")

    def _initialize_templates(self):
        """初始化目标模板"""
        self._goal_templates = [
            GoalTemplate(
                name="capability_improvement",
                description="提升特定能力",
                priority=GoalPriority.HIGH,
                learning_type=LearningType.SUPERVISED,
                estimated_duration=3600,
                success_criteria={"improvement": 0.1},
            ),
            GoalTemplate(
                name="knowledge_acquisition",
                description="获取新知识",
                priority=GoalPriority.MEDIUM,
                learning_type=LearningType.SELF_SUPERVISED,
                estimated_duration=1800,
                success_criteria={"knowledge_units": 3},
            ),
            GoalTemplate(
                name="skill_practice",
                description="技能练习",
                priority=GoalPriority.MEDIUM,
                learning_type=LearningType.REINFORCEMENT,
                estimated_duration=2400,
                success_criteria={"practice_count": 5},
            ),
            GoalTemplate(
                name="exploration",
                description="探索新领域",
                priority=GoalPriority.EXPLORATORY,
                learning_type=LearningType.SELF_SUPERVISED,
                estimated_duration=1200,
                success_criteria={"discoveries": 2},
            ),
            GoalTemplate(
                name="knowledge_consolidation",
                description="知识固化",
                priority=GoalPriority.HIGH,
                learning_type=LearningType.META,
                estimated_duration=900,
                success_criteria={"consolidated_units": 5},
            ),
        ]

    async def generate_goals(
        self,
        count: int = 3,
        context: dict[str, Any] | None = None,
    ) -> list[LearningGoal]:
        """
        生成学习目标

        Args:
            count: 生成目标数量
            context: 额外上下文

        Returns:
            生成的目标列表
        """
        await self._ensure_initialized()

        goals = []

        weakness_goals = await self._generate_weakness_goals(count // 2)
        goals.extend(weakness_goals)

        exploration_goals = await self._generate_exploration_goals(1)
        goals.extend(exploration_goals)

        remaining = count - len(goals)
        if remaining > 0:
            improvement_goals = await self._generate_improvement_goals(remaining)
            goals.extend(improvement_goals)

        for goal in goals:
            self._active_goals[goal.id] = goal
            self._generation_count += 1

        return goals[:count]

    async def _generate_weakness_goals(self, count: int) -> list[LearningGoal]:
        """基于弱点生成目标"""
        goals = []

        if not self.capability_assessor:
            return goals

        weaknesses = await self.capability_assessor.identify_weaknesses()

        for weakness in weaknesses[:count]:
            goal = LearningGoal(
                title=f"提升{weakness.capability_name}",
                description=f"将{weakness.capability_name}从{weakness.current_level:.2f}提升到{min(1.0, weakness.current_level + 0.3):.2f}",
                priority=GoalPriority.HIGH if weakness.priority > 0.7 else GoalPriority.MEDIUM,
                target_capability=weakness.capability_id,
                learning_type=LearningType.SUPERVISED,
                expected_outcomes=[
                    f"理解{weakness.capability_name}的核心原理",
                    f"在实践中应用{weakness.capability_name}",
                ],
                success_criteria={
                    "target_score": min(1.0, weakness.current_level + 0.3),
                    "practice_count": 5,
                },
            )

            for suggestion in weakness.improvement_suggestions[:2]:
                goal.sub_goals.append(suggestion)

            goals.append(goal)

        return goals

    async def _generate_exploration_goals(self, count: int) -> list[LearningGoal]:
        """基于探索生成目标"""
        goals = []

        if not self.curiosity_engine:
            return goals

        exploration_goals = await self.curiosity_engine.generate_exploration_goals(count)

        for exp_goal in exploration_goals:
            exp_goal.priority = GoalPriority.EXPLORATORY
            goals.append(exp_goal)

        return goals

    async def _generate_improvement_goals(self, count: int) -> list[LearningGoal]:
        """生成一般改进目标"""
        goals = []

        templates = [
            t
            for t in self._goal_templates
            if t.priority in [GoalPriority.MEDIUM, GoalPriority.HIGH]
        ]

        for i in range(count):
            template = templates[i % len(templates)]

            goal = LearningGoal(
                title=template.name,
                description=template.description,
                priority=template.priority,
                learning_type=template.learning_type,
                expected_outcomes=[f"完成{template.name}"],
                success_criteria=template.success_criteria.copy(),
            )

            goals.append(goal)

        return goals

    async def prioritize_goals(self) -> list[LearningGoal]:
        """
        对目标进行优先级排序

        Returns:
            排序后的目标列表
        """
        await self._ensure_initialized()

        def goal_score(goal: LearningGoal) -> float:
            priority_weights = {
                GoalPriority.CRITICAL: 1.0,
                GoalPriority.HIGH: 0.8,
                GoalPriority.MEDIUM: 0.5,
                GoalPriority.LOW: 0.3,
                GoalPriority.EXPLORATORY: 0.2,
            }

            priority_score = priority_weights.get(goal.priority, 0.5)

            progress_penalty = goal.progress * 0.3

            attempt_penalty = min(0.3, goal.attempts * 0.1)

            age_bonus = 0.0
            if goal.created_at:
                age_hours = (datetime.now().timestamp() - goal.created_at) / 3600
                age_bonus = min(0.2, age_hours / 24 * 0.1)

            return priority_score - progress_penalty - attempt_penalty + age_bonus

        sorted_goals = sorted(
            self._active_goals.values(),
            key=goal_score,
            reverse=True,
        )

        return sorted_goals

    async def decompose_goal(
        self,
        goal: LearningGoal,
        max_sub_goals: int = 5,
    ) -> list[LearningGoal]:
        """
        分解目标

        Args:
            goal: 要分解的目标
            max_sub_goals: 最大子目标数

        Returns:
            子目标列表
        """
        await self._ensure_initialized()

        sub_goals = []

        if self.llm:
            try:
                sub_goals = await self._decompose_with_llm(goal, max_sub_goals)
            except Exception:
                sub_goals = self._decompose_default(goal, max_sub_goals)
        else:
            sub_goals = self._decompose_default(goal, max_sub_goals)

        for _i, sub in enumerate(sub_goals):
            sub.priority = goal.priority
            sub.deadline = goal.deadline
            goal.sub_goals.append(sub.id)
            self._active_goals[sub.id] = sub

        return sub_goals

    async def _decompose_with_llm(
        self,
        goal: LearningGoal,
        max_count: int,
    ) -> list[LearningGoal]:
        """使用LLM分解目标"""
        prompt = f"""将以下学习目标分解为{max_count}个子目标：

目标：{goal.title}
描述：{goal.description}

请以JSON格式返回子目标列表：
[
  {{"title": "子目标1", "description": "描述"}},
  ...
]"""

        response = await self.llm.chat(prompt)

        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]

        sub_data = json.loads(response.strip())

        return [
            LearningGoal(
                title=item.get("title", f"子目标{i}"),
                description=item.get("description", ""),
                priority=goal.priority,
                learning_type=goal.learning_type,
            )
            for i, item in enumerate(sub_data[:max_count])
        ]

    def _decompose_default(
        self,
        goal: LearningGoal,
        max_count: int,
    ) -> list[LearningGoal]:
        """默认分解策略"""
        phases = ["理解概念", "学习原理", "实践应用", "总结反思", "巩固提升"]

        return [
            LearningGoal(
                title=f"{phase} - {goal.title[:10]}",
                description=f"{goal.title}的{phase}阶段",
                priority=goal.priority,
                learning_type=goal.learning_type,
            )
            for phase in phases[:max_count]
        ]

    async def check_goal_dependencies(
        self,
        goal: LearningGoal,
    ) -> dict[str, Any]:
        """
        检查目标依赖

        Args:
            goal: 要检查的目标

        Returns:
            依赖状态
        """
        result = {
            "can_start": True,
            "blocking_goals": [],
            "satisfied_prerequisites": [],
            "unsatisfied_prerequisites": [],
        }

        for prereq_id in goal.prerequisites:
            if prereq_id in self._active_goals:
                prereq = self._active_goals[prereq_id]
                if prereq.progress < 1.0:
                    result["blocking_goals"].append(prereq)
                    result["can_start"] = False
                else:
                    result["satisfied_prerequisites"].append(prereq)
            else:
                result["satisfied_prerequisites"].append({"id": prereq_id, "status": "completed"})

        return result

    async def schedule_goals(self) -> list[dict[str, Any]]:
        """
        调度目标执行

        Returns:
            执行计划
        """
        await self._ensure_initialized()

        prioritized = await self.prioritize_goals()

        schedule = []
        current_time = datetime.now().timestamp()

        for _i, goal in enumerate(prioritized):
            dep_check = await self.check_goal_dependencies(goal)

            start_time = current_time
            if dep_check["blocking_goals"]:
                blocking_end = max(
                    g.created_at or current_time for g in dep_check["blocking_goals"]
                )
                start_time = max(start_time, blocking_end + 3600)

            schedule.append(
                {
                    "goal_id": goal.id,
                    "title": goal.title,
                    "priority": goal.priority.value,
                    "scheduled_start": start_time,
                    "estimated_duration": 3600,
                    "can_start_now": dep_check["can_start"],
                    "blocking": [g.id for g in dep_check["blocking_goals"]],
                }
            )

            current_time = start_time + 3600

        return schedule

    def complete_goal(self, goal_id: str, success: bool = True):
        """完成目标"""
        if goal_id in self._active_goals:
            goal = self._active_goals.pop(goal_id)
            goal.progress = 1.0
            goal.completed_at = datetime.now().timestamp()

            if success:
                self._completed_goals.append(goal)

    def get_active_goals(self) -> list[LearningGoal]:
        """获取活跃目标"""
        return list(self._active_goals.values())

    def get_goal(self, goal_id: str) -> LearningGoal | None:
        """获取特定目标"""
        return self._active_goals.get(goal_id)

    def get_goal_stats(self) -> dict[str, Any]:
        """获取目标统计"""
        return {
            "active_goals": len(self._active_goals),
            "completed_goals": len(self._completed_goals),
            "generation_count": self._generation_count,
            "by_priority": {
                p.value: len([g for g in self._active_goals.values() if g.priority == p])
                for p in GoalPriority
            },
        }

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()
