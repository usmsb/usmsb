"""
Skill 缺口发现

AutoSkillEngine 的组件

发现能力缺口的三种来源
"""

from dataclasses import dataclass, field
from typing import Any

from ...models.causal_graph import CausalGraph


@dataclass
class SkillGap:
    """Skill 缺口"""
    gap_id: str
    source_node: str
    target_node: str
    gap_type: str  # "missing_causal_link" | "knowledge_gap" | "missing_capability"
    priority: float
    description: str
    failed_task_id: str | None = None


class SkillDiscovery:
    """
    Skill 缺口发现器

    三种来源：
    1. 因果图：某个因果边缺失，没有对应 skill
    2. 好奇心引擎：CuriosityEngine 发现知识空白
    3. 执行失败：MetaAgent 执行任务失败后的反思
    """

    def __init__(
        self,
        causal_graph: CausalGraph | None = None,
        curiosity_engine=None,
        task_executor=None,
        skill_registry=None,
    ):
        """
        初始化

        Args:
            causal_graph: 因果图
            curiosity_engine: 好奇心引擎
            task_executor: 任务执行器
            skill_registry: Skill 注册表
        """
        self.graph = causal_graph
        self.curiosity = curiosity_engine
        self.executor = task_executor
        self.registry = skill_registry or {}

    async def discover_gaps(self) -> list[SkillGap]:
        """
        发现所有能力缺口

        Returns:
            需要创建的新 Skill 列表
        """
        gaps = []

        # 来源 1: 因果图缺失边
        if self.graph:
            causal_gaps = await self._discover_from_causal_graph()
            gaps.extend(causal_gaps)

        # 来源 2: 好奇心引擎知识空白
        if self.curiosity:
            curiosity_gaps = await self._discover_from_curiosity()
            gaps.extend(curiosity_gaps)

        # 来源 3: 执行失败记录
        if self.executor:
            failure_gaps = await self._discover_from_failures()
            gaps.extend(failure_gaps)

        # 去重
        gaps = self._deduplicate_gaps(gaps)

        return gaps

    async def _discover_from_causal_graph(self) -> list[SkillGap]:
        """从因果图发现缺口"""
        if not self.graph:
            return []

        gaps = []

        for edge in self.graph.edges:
            # 检查是否有 skill 能实现这个因果边
            has_skill = self._check_skill_exists_for_edge(edge)

            if not has_skill:
                gap = SkillGap(
                    gap_id=f"causal_{edge.source}_{edge.target}",
                    source_node=edge.source,
                    target_node=edge.target,
                    gap_type="missing_causal_link",
                    priority=edge.confidence * abs(edge.strength),
                    description=f"缺少实现「{edge.source}→{edge.target}」的 skill",
                )
                gaps.append(gap)

        return gaps

    async def _discover_from_curiosity(self) -> list[SkillGap]:
        """从好奇心引擎发现知识空白"""
        gaps = []

        if not self.curiosity:
            return gaps

        try:
            domains = getattr(self.curiosity, "get_domains", lambda: [])()

            for domain in domains:
                exploration_depth = getattr(domain, "exploration_depth", 0)
                interest_level = getattr(domain, "interest_level", 0)

                if exploration_depth < 0.3 and interest_level > 0.6:
                    gap = SkillGap(
                        gap_id=f"curiosity_{domain.name}",
                        source_node=domain.name,
                        target_node="knowledge",
                        gap_type="knowledge_gap",
                        priority=interest_level,
                        description=f"领域「{domain.name}」探索不足但兴趣高，需要深入学习",
                    )
                    gaps.append(gap)
        except Exception:
            pass

        return gaps

    async def _discover_from_failures(self) -> list[SkillGap]:
        """从执行失败发现缺口"""
        gaps = []

        if not self.executor:
            return gaps

        try:
            recent_failures = getattr(self.executor, "get_recent_failures", lambda: [])()

            for failure in recent_failures[-10:]:  # 只看最近 10 次
                root_cause = getattr(failure, "root_cause", None)

                if root_cause == "missing_capability":
                    gap = SkillGap(
                        gap_id=f"failure_{getattr(failure, 'task_id', 'unknown')}",
                        source_node=getattr(failure, "task_type", "unknown"),
                        target_node=getattr(failure, "missing_capability", "unknown"),
                        gap_type="missing_capability",
                        priority=1.0,
                        description=f"任务「{getattr(failure, 'task_type', 'unknown')}」缺少能力「{getattr(failure, 'missing_capability', 'unknown')}」",
                        failed_task_id=getattr(failure, "task_id", None),
                    )
                    gaps.append(gap)
        except Exception:
            pass

        return gaps

    def _check_skill_exists_for_edge(self, edge) -> bool:
        """检查是否有 skill 实现这个因果边"""
        edge_id = edge.edge_id

        # 在注册表中查找
        for skill in self.registry.values():
            activates_edges = getattr(skill, "activates_edges", [])
            if edge_id in activates_edges:
                return True

        return False

    def _deduplicate_gaps(self, gaps: list[SkillGap]) -> list[SkillGap]:
        """去重"""
        seen = set()
        unique = []

        for gap in gaps:
            key = (gap.source_node, gap.target_node, gap.gap_type)
            if key not in seen:
                seen.add(key)
                unique.append(gap)

        return unique


class PrioritizedSkillDiscovery(SkillDiscovery):
    """
    带优先级的 Skill 发现

    根据缺口的重要性和可行性排序
    """

    async def discover_gaps(self) -> list[SkillGap]:
        """发现并排序缺口"""
        gaps = await super().discover_gaps()

        # 计算优先级
        for gap in gaps:
            gap.priority = self._calculate_priority(gap)

        # 按优先级排序
        gaps.sort(key=lambda g: g.priority, reverse=True)

        return gaps

    def _calculate_priority(self, gap: SkillGap) -> float:
        """
        计算缺口优先级

        公式：priority = confidence * importance * feasibility
        """
        base_priority = gap.priority

        # 类型权重
        type_weights = {
            "missing_capability": 1.0,
            "missing_causal_link": 0.7,
            "knowledge_gap": 0.5,
        }
        type_weight = type_weights.get(gap.gap_type, 0.5)

        # 组合优先级
        priority = base_priority * type_weight

        return priority
