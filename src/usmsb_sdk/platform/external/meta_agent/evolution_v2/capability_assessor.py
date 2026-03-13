"""
能力评估器 - Capability Assessor

评估和监控系统能力，识别弱点
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from .models import (
    Capability,
    CapabilityLevel,
    PerformanceMetric,
    SelfReflection,
)

logger = logging.getLogger(__name__)


@dataclass
class AssessmentContext:
    """评估上下文"""

    task_type: str
    difficulty: float
    time_limit: Optional[float] = None
    resource_constraints: Dict[str, Any] = field(default_factory=dict)
    previous_attempts: int = 0


@dataclass
class WeaknessAnalysis:
    """弱点分析结果"""

    capability_id: str
    capability_name: str
    current_level: float
    target_level: float
    gap: float
    root_causes: List[str]
    improvement_suggestions: List[str]
    priority: float


class CapabilityAssessor:
    """
    能力评估器

    核心职责：
    1. 能力评估 - 多维度评估各项能力
    2. 性能监控 - 实时监控能力表现
    3. 弱点识别 - 识别需要改进的能力
    4. 优势发现 - 发现和强化优势能力
    5. 趋势分析 - 分析能力发展趋势
    """

    def __init__(self, llm_manager=None, knowledge_base=None):
        self.llm = llm_manager
        self.knowledge = knowledge_base

        self._capabilities: Dict[str, Capability] = {}
        self._performance_metrics: Dict[str, PerformanceMetric] = {}
        self._assessment_history: List[Dict[str, Any]] = []
        self._weakness_cache: Dict[str, WeaknessAnalysis] = {}

        self._capability_graph: Dict[str, List[str]] = {}

        self._initialized = False

    async def initialize(self):
        """初始化能力评估器"""
        if self._initialized:
            return

        self._initialize_core_capabilities()

        self._initialize_performance_metrics()

        self._initialized = True
        logger.info(f"CapabilityAssessor initialized with {len(self._capabilities)} capabilities")

    def _initialize_core_capabilities(self):
        """初始化核心能力集"""
        core_capabilities = [
            ("reasoning", "推理能力", "进行逻辑推理和问题分析的能力", []),
            ("learning", "学习能力", "从经验中获取新知识的能力", []),
            ("communication", "沟通能力", "与用户有效沟通的能力", []),
            ("problem_solving", "问题解决", "识别和解决复杂问题的能力", ["reasoning"]),
            ("creativity", "创造力", "产生新颖想法和解决方案的能力", []),
            ("adaptation", "适应能力", "适应新环境和任务的能力", ["learning"]),
            ("planning", "规划能力", "制定和执行计划的能力", ["reasoning"]),
            ("execution", "执行能力", "有效执行任务的能力", ["planning"]),
            ("self_reflection", "自我反思", "评估自身表现的能力", ["reasoning"]),
            ("knowledge_integration", "知识整合", "整合多领域知识的能力", ["learning"]),
            ("pattern_recognition", "模式识别", "识别数据和信息中的模式", ["reasoning"]),
            ("decision_making", "决策能力", "做出明智决策的能力", ["reasoning", "problem_solving"]),
            ("tool_usage", "工具使用", "有效使用各种工具的能力", ["execution"]),
            ("code_generation", "代码生成", "生成高质量代码的能力", ["creativity", "execution"]),
            (
                "debugging",
                "调试能力",
                "发现和修复错误的能力",
                ["problem_solving", "pattern_recognition"],
            ),
        ]

        for cap_id, name, description, prereqs in core_capabilities:
            self._capabilities[cap_id] = Capability(
                id=cap_id,
                name=name,
                description=description,
                prerequisite_ids=prereqs,
            )

        self._build_capability_graph()

    def _build_capability_graph(self):
        """构建能力依赖图"""
        self._capability_graph = {}
        for cap_id, cap in self._capabilities.items():
            self._capability_graph[cap_id] = cap.prerequisite_ids.copy()

            for prereq_id in cap.prerequisite_ids:
                if prereq_id not in self._capability_graph:
                    self._capability_graph[prereq_id] = []
                self._capability_graph[prereq_id].append(cap_id)

    def _initialize_performance_metrics(self):
        """初始化性能指标"""
        metrics = [
            ("task_success_rate", "任务成功率", 1.0),
            ("response_quality", "响应质量", 1.0),
            ("learning_efficiency", "学习效率", 1.0),
            ("adaptation_speed", "适应速度", 1.0),
            ("knowledge_retention", "知识保持率", 1.0),
            ("error_rate", "错误率", 0.0),
            ("improvement_rate", "改进率", 0.5),
            ("goal_achievement", "目标达成率", 1.0),
        ]

        for metric_id, name, target in metrics:
            self._performance_metrics[metric_id] = PerformanceMetric(
                name=name,
                target=target,
            )

    async def assess_capability(
        self,
        capability_id: str,
        context: Optional[AssessmentContext] = None,
    ) -> Dict[str, Any]:
        """
        评估单项能力

        Args:
            capability_id: 能力ID
            context: 评估上下文

        Returns:
            评估结果
        """
        await self._ensure_initialized()

        if capability_id not in self._capabilities:
            return {"error": f"Unknown capability: {capability_id}"}

        capability = self._capabilities[capability_id]

        assessment = {
            "capability_id": capability_id,
            "name": capability.name,
            "level": capability.level.value,
            "score": capability.score,
            "success_rate": capability.success_rate,
            "experience_points": capability.experience_points,
            "practice_count": capability.practice_count,
            "trend": self._calculate_capability_trend(capability),
            "prerequisites_met": await self._check_prerequisites(capability),
            "derived_capabilities": self._get_derived_capabilities(capability_id),
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
        }

        assessment["strengths"] = self._identify_strengths(capability)
        assessment["weaknesses"] = self._identify_weaknesses(capability)
        assessment["recommendations"] = self._generate_recommendations(capability, context)

        self._assessment_history.append(
            {
                "capability_id": capability_id,
                "timestamp": datetime.now().timestamp(),
                "score": capability.score,
                "context": context.task_type if context else None,
            }
        )

        return assessment

    def _calculate_capability_trend(self, capability: Capability) -> float:
        """计算能力趋势"""
        if len(capability.performance_history) < 2:
            return 0.0

        recent = capability.performance_history[-5:]
        older = capability.performance_history[:-5] or capability.performance_history[:5]

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        return recent_avg - older_avg

    async def _check_prerequisites(self, capability: Capability) -> Dict[str, bool]:
        """检查前置能力是否满足"""
        results = {}
        for prereq_id in capability.prerequisite_ids:
            if prereq_id in self._capabilities:
                prereq = self._capabilities[prereq_id]
                results[prereq_id] = prereq.score >= 0.5
            else:
                results[prereq_id] = False
        return results

    def _get_derived_capabilities(self, capability_id: str) -> List[Dict[str, Any]]:
        """获取派生能力"""
        derived = []
        for cap_id, prereqs in self._capability_graph.items():
            if capability_id in prereqs and cap_id != capability_id:
                if cap_id in self._capabilities:
                    cap = self._capabilities[cap_id]
                    derived.append(
                        {
                            "id": cap_id,
                            "name": cap.name,
                            "level": cap.level.value,
                        }
                    )
        return derived

    def _identify_strengths(self, capability: Capability) -> List[str]:
        """识别能力优势"""
        strengths = []

        if capability.success_rate > 0.8:
            strengths.append("高成功率")
        if capability.score > 0.7:
            strengths.append("表现优秀")
        if self._calculate_capability_trend(capability) > 0.1:
            strengths.append("持续进步")
        if capability.experience_points > 100:
            strengths.append("经验丰富")

        return strengths

    def _identify_weaknesses(self, capability: Capability) -> List[str]:
        """识别能力弱点"""
        weaknesses = []

        if capability.success_rate < 0.5:
            weaknesses.append("成功率较低")
        if capability.score < 0.3:
            weaknesses.append("能力不足")
        if self._calculate_capability_trend(capability) < -0.1:
            weaknesses.append("表现下滑")
        if capability.practice_count < 5:
            weaknesses.append("缺乏练习")

        unmet_prereqs = [
            p
            for p in capability.prerequisite_ids
            if p in self._capabilities and self._capabilities[p].score < 0.5
        ]
        if unmet_prereqs:
            weaknesses.append(f"前置能力不足: {', '.join(unmet_prereqs)}")

        return weaknesses

    def _generate_recommendations(
        self,
        capability: Capability,
        context: Optional[AssessmentContext],
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if capability.score < 0.5:
            recommendations.append("建议进行基础训练")

        unmet_prereqs = [
            p
            for p in capability.prerequisite_ids
            if p in self._capabilities and self._capabilities[p].score < 0.5
        ]
        if unmet_prereqs:
            recommendations.append(f"先提升前置能力: {', '.join(unmet_prereqs)}")

        if capability.practice_count < 10:
            recommendations.append("增加实践机会")

        if capability.success_rate < 0.6:
            recommendations.append("分析失败案例，找出问题根源")

        return recommendations

    async def assess_all_capabilities(self) -> Dict[str, Any]:
        """
        评估所有能力

        Returns:
            综合评估报告
        """
        await self._ensure_initialized()

        assessments = {}
        for cap_id in self._capabilities:
            assessments[cap_id] = await self.assess_capability(cap_id)

        overall_score = sum(cap.score for cap in self._capabilities.values()) / len(
            self._capabilities
        )

        level_distribution = {}
        for cap in self._capabilities.values():
            level = cap.level.value
            level_distribution[level] = level_distribution.get(level, 0) + 1

        return {
            "overall_score": overall_score,
            "total_capabilities": len(self._capabilities),
            "level_distribution": level_distribution,
            "assessments": assessments,
            "strongest": self._get_top_capabilities(5, ascending=False),
            "weakest": self._get_top_capabilities(5, ascending=True),
            "improvement_priorities": self._get_improvement_priorities(),
        }

    def _get_top_capabilities(self, n: int, ascending: bool) -> List[Dict[str, Any]]:
        """获取顶部能力"""
        sorted_caps = sorted(
            self._capabilities.values(),
            key=lambda c: c.score,
            reverse=not ascending,
        )
        return [
            {
                "id": c.id,
                "name": c.name,
                "score": c.score,
                "level": c.level.value,
            }
            for c in sorted_caps[:n]
        ]

    def _get_improvement_priorities(self) -> List[Dict[str, Any]]:
        """获取改进优先级"""
        priorities = []

        for cap in self._capabilities.values():
            priority_score = self._calculate_improvement_priority(cap)
            if priority_score > 0.5:
                priorities.append(
                    {
                        "capability_id": cap.id,
                        "name": cap.name,
                        "priority": priority_score,
                        "current_score": cap.score,
                        "gap": 1.0 - cap.score,
                    }
                )

        return sorted(priorities, key=lambda x: x["priority"], reverse=True)

    def _calculate_improvement_priority(self, capability: Capability) -> float:
        """计算改进优先级"""
        gap = 1.0 - capability.score

        dependency_score = len(self._get_derived_capabilities(capability.id)) * 0.1

        trend_penalty = max(0, -self._calculate_capability_trend(capability)) * 0.5

        return min(1.0, gap * 0.5 + dependency_score + trend_penalty)

    async def record_performance(
        self,
        capability_id: str,
        success: bool,
        performance_score: float,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        记录能力表现

        Args:
            capability_id: 能力ID
            success: 是否成功
            performance_score: 表现分数
            context: 额外上下文
        """
        await self._ensure_initialized()

        if capability_id not in self._capabilities:
            logger.warning(f"Unknown capability: {capability_id}")
            return

        capability = self._capabilities[capability_id]
        capability.add_experience(success, performance_score)
        capability.last_improvement = datetime.now().timestamp()

        self._update_dependent_capabilities(capability_id, performance_score)

        logger.debug(
            f"Recorded performance for {capability_id}: "
            f"success={success}, score={performance_score:.2f}, "
            f"level={capability.level.value}"
        )

    def _update_dependent_capabilities(self, capability_id: str, performance: float):
        """更新依赖能力的影响"""
        if capability_id not in self._capability_graph:
            return

        for dependent_id in self._capability_graph[capability_id]:
            if dependent_id in self._capabilities:
                dependent = self._capabilities[dependent_id]

                all_prereqs_met = all(
                    self._capabilities.get(p, Capability(name="")).score >= 0.5
                    for p in dependent.prerequisite_ids
                )

                if all_prereqs_met and performance > 0.7:
                    dependent.score = min(1.0, dependent.score + 0.02)

    async def identify_weaknesses(self) -> List[WeaknessAnalysis]:
        """
        识别能力弱点

        Returns:
            弱点分析列表
        """
        await self._ensure_initialized()

        weaknesses = []

        for capability in self._capabilities.values():
            if capability.score < 0.5 or capability.success_rate < 0.6:
                root_causes = await self._analyze_root_causes(capability)

                suggestions = await self._generate_improvement_suggestions(capability, root_causes)

                analysis = WeaknessAnalysis(
                    capability_id=capability.id,
                    capability_name=capability.name,
                    current_level=capability.score,
                    target_level=1.0,
                    gap=1.0 - capability.score,
                    root_causes=root_causes,
                    improvement_suggestions=suggestions,
                    priority=self._calculate_improvement_priority(capability),
                )

                weaknesses.append(analysis)
                self._weakness_cache[capability.id] = analysis

        return sorted(weaknesses, key=lambda w: w.priority, reverse=True)

    async def _analyze_root_causes(self, capability: Capability) -> List[str]:
        """分析弱点根本原因"""
        causes = []

        unmet_prereqs = [
            self._capabilities[p].name
            for p in capability.prerequisite_ids
            if p in self._capabilities and self._capabilities[p].score < 0.5
        ]
        if unmet_prereqs:
            causes.append(f"前置能力不足: {', '.join(unmet_prereqs)}")

        if capability.practice_count < 10:
            causes.append("缺乏足够的练习")

        if capability.success_rate < 0.5:
            causes.append("方法论可能存在问题")

        trend = self._calculate_capability_trend(capability)
        if trend < 0:
            causes.append("能力呈现下降趋势")

        if self.llm and len(causes) == 0:
            causes.append(await self._deep_analyze_causes(capability))

        return causes or ["未明确识别的原因"]

    async def _deep_analyze_causes(self, capability: Capability) -> str:
        """深度分析原因"""
        if not self.llm:
            return "需要进一步分析"

        prompt = f"""分析能力"{capability.name}"表现不佳的原因：
- 当前分数: {capability.score:.2f}
- 成功率: {capability.success_rate:.2f}
- 练习次数: {capability.practice_count}
- 前置能力: {[self._capabilities.get(p, Capability(name="unknown")).name for p in capability.prerequisite_ids]}

请给出一个最主要的根本原因。"""
        try:
            response = await self.llm.chat(prompt)
            return response[:100]
        except Exception:
            return "需要进一步分析"

    async def _generate_improvement_suggestions(
        self,
        capability: Capability,
        root_causes: List[str],
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        for cause in root_causes:
            if "前置能力" in cause:
                suggestions.append("优先提升前置能力")
            elif "练习" in cause:
                suggestions.append("增加针对性的练习任务")
            elif "方法论" in cause:
                suggestions.append("分析成功和失败案例，优化方法")
            elif "下降趋势" in cause:
                suggestions.append("回顾近期变化，找出干扰因素")

        if capability.score < 0.3:
            suggestions.append("从基础开始系统学习")

        if not suggestions:
            suggestions.append("制定针对性训练计划")

        return suggestions

    async def generate_self_reflection(self) -> SelfReflection:
        """
        生成自我反思报告

        Returns:
            自我反思结果
        """
        await self._ensure_initialized()

        assessment = await self.assess_all_capabilities()
        weaknesses = await self.identify_weaknesses()

        reflection = SelfReflection(
            type="capability_assessment",
            observations=[
                f"当前总体能力评分: {assessment['overall_score']:.2f}",
                f"能力分布: {assessment['level_distribution']}",
            ],
            strengths=[c["name"] for c in assessment["strongest"][:3]],
            weaknesses=[w.capability_name for w in weaknesses[:3]],
            improvement_areas=[
                {
                    "capability": w.capability_name,
                    "priority": w.priority,
                    "suggestions": w.improvement_suggestions[:2],
                }
                for w in weaknesses[:5]
            ],
            action_items=[
                {
                    "action": f"提升{w.capability_name}",
                    "priority": "high" if w.priority > 0.7 else "medium",
                    "target": f"达到{min(0.8, w.current_level + 0.3):.1f}",
                }
                for w in weaknesses[:3]
            ],
            confidence_level=assessment["overall_score"],
        )

        return reflection

    async def update_metric(self, metric_name: str, value: float):
        """更新性能指标"""
        if metric_name in self._performance_metrics:
            self._performance_metrics[metric_name].update(value)

    async def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            "metrics": {
                name: {
                    "value": m.value,
                    "target": m.target,
                    "trend": m.trend,
                }
                for name, m in self._performance_metrics.items()
            },
            "capabilities_summary": {
                "total": len(self._capabilities),
                "by_level": {
                    level.value: len([c for c in self._capabilities.values() if c.level == level])
                    for level in CapabilityLevel
                },
            },
        }

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """获取能力"""
        return self._capabilities.get(capability_id)

    def get_all_capabilities(self) -> Dict[str, Capability]:
        """获取所有能力"""
        return self._capabilities.copy()

    def add_capability(self, capability: Capability):
        """添加新能力"""
        self._capabilities[capability.id] = capability
        self._build_capability_graph()
