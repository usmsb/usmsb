"""
好奇心引擎 - Curiosity Engine

主动探索未知领域，驱动自主学习
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .models import (
    ExplorationResult,
    GoalPriority,
    LearningGoal,
)

logger = logging.getLogger(__name__)


@dataclass
class CuriosityDomain:
    """好奇心领域"""

    name: str
    description: str
    exploration_depth: float = 0.0
    known_concepts: list[str] = field(default_factory=list)
    unknown_concepts: list[str] = field(default_factory=list)
    interest_level: float = 0.5
    last_explored: float | None = None


@dataclass
class ExplorationPath:
    """探索路径"""

    start_domain: str
    target_concept: str
    expected_novelty: float
    expected_usefulness: float
    difficulty: float
    prerequisites: list[str] = field(default_factory=list)


class CuriosityEngine:
    """
    好奇心引擎

    核心职责：
    1. 探索驱动 - 识别和探索未知领域
    2. 新颖性评估 - 评估信息的新颖程度
    3. 兴趣管理 - 维护和管理兴趣领域
    4. 问题生成 - 自主生成探索问题
    5. 知识缺口识别 - 识别知识体系中的缺口
    """

    DOMAINS = [
        "自然语言处理",
        "机器学习",
        "知识表示",
        "推理与规划",
        "感知与多模态",
        "人机交互",
        "系统架构",
        "安全性",
        "效率优化",
        "创造性思维",
    ]

    def __init__(self, llm_manager=None, knowledge_base=None, capability_assessor=None):
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.capability_assessor = capability_assessor

        self._domains: dict[str, CuriosityDomain] = {}
        self._exploration_history: list[ExplorationResult] = []
        self._novelty_cache: dict[str, float] = {}

        self._curiosity_level: float = 0.7
        self._exploration_budget: int = 10
        self._exploration_count: int = 0

        self._initialized = False

    async def initialize(self):
        """初始化好奇心引擎"""
        if self._initialized:
            return

        for domain_name in self.DOMAINS:
            self._domains[domain_name] = CuriosityDomain(
                name=domain_name,
                description=f"{domain_name}相关知识和技能",
                interest_level=random.uniform(0.3, 0.7),
            )

        self._initialized = True
        logger.info(f"CuriosityEngine initialized with {len(self._domains)} domains")

    async def explore(self) -> ExplorationResult:
        """
        执行探索

        选择最有价值的未知领域进行探索
        """
        await self._ensure_initialized()

        if self._exploration_count >= self._exploration_budget:
            logger.warning("Exploration budget exhausted")
            return ExplorationResult(domain="none", novelty_score=0.0)

        domain = await self._select_exploration_domain()

        exploration_path = await self._plan_exploration(domain)

        discoveries = await self._execute_exploration(exploration_path)

        result = ExplorationResult(
            domain=domain.name,
            discoveries=discoveries,
            novelty_score=exploration_path.expected_novelty,
            usefulness_score=exploration_path.expected_usefulness,
            potential_goals=await self._generate_potential_goals(discoveries),
            knowledge_gained=discoveries,
            questions_raised=await self._generate_questions(discoveries),
        )

        self._exploration_history.append(result)
        self._exploration_count += 1

        self._update_domain_after_exploration(domain, result)

        return result

    async def _select_exploration_domain(self) -> CuriosityDomain:
        """选择探索领域"""
        candidates = [d for d in self._domains.values() if d.exploration_depth < 1.0]

        if not candidates:
            candidates = list(self._domains.values())

        def domain_score(d: CuriosityDomain) -> float:
            recency_penalty = 0.0
            if d.last_explored:
                hours_since = (datetime.now().timestamp() - d.last_explored) / 3600
                recency_penalty = min(0.5, hours_since / 24 * 0.1)

            gap_score = 1.0 - d.exploration_depth

            interest_score = d.interest_level

            unknown_score = len(d.unknown_concepts) / 10 if d.unknown_concepts else 0.5

            return (
                gap_score * 0.3
                + interest_score * 0.25
                + unknown_score * 0.25
                + recency_penalty * 0.1
                + random.uniform(0, 0.1)
            )

        return max(candidates, key=domain_score)

    async def _plan_exploration(self, domain: CuriosityDomain) -> ExplorationPath:
        """规划探索路径"""
        if domain.unknown_concepts:
            target = random.choice(domain.unknown_concepts)
        else:
            target = await self._discover_unknown_concept(domain)

        novelty = await self._estimate_novelty(domain.name, target)

        usefulness = await self._estimate_usefulness(domain.name, target)

        difficulty = self._estimate_difficulty(domain, target)

        prerequisites = await self._identify_prerequisites(domain, target)

        return ExplorationPath(
            start_domain=domain.name,
            target_concept=target,
            expected_novelty=novelty,
            expected_usefulness=usefulness,
            difficulty=difficulty,
            prerequisites=prerequisites,
        )

    async def _discover_unknown_concept(self, domain: CuriosityDomain) -> str:
        """发现未知概念"""
        if self.llm:
            try:
                prompt = f"""在"{domain.name}"领域中，有什么重要但可能被忽视的概念？
请列出一个具体概念名称（不超过10个字）。"""
                response = await self.llm.chat(prompt)
                concept = response.strip()[:10]
                domain.unknown_concepts.append(concept)
                return concept
            except Exception:
                pass

        concepts = [
            "深度学习优化",
            "注意力机制",
            "知识蒸馏",
            "多任务学习",
            "迁移学习",
            "自监督学习",
            "元学习",
            "强化学习策略",
        ]
        return random.choice(concepts)

    async def _estimate_novelty(self, domain: str, concept: str) -> float:
        """估计新颖性"""
        cache_key = f"{domain}:{concept}"
        if cache_key in self._novelty_cache:
            return self._novelty_cache[cache_key]

        if self.knowledge:
            try:
                related = await self.knowledge.retrieve(concept, top_k=3)
                if related:
                    novelty = 1.0 - min(1.0, len(related) * 0.2)
                    self._novelty_cache[cache_key] = novelty
                    return novelty
            except Exception:
                pass

        novelty = random.uniform(0.5, 0.9)
        self._novelty_cache[cache_key] = novelty
        return novelty

    async def _estimate_usefulness(self, domain: str, concept: str) -> float:
        """估计有用性"""
        base_usefulness = 0.5

        domain_scores = {
            "机器学习": 0.8,
            "自然语言处理": 0.75,
            "推理与规划": 0.7,
            "知识表示": 0.65,
        }

        base_usefulness = domain_scores.get(domain, 0.5)

        if self.capability_assessor:
            weaknesses = await self.capability_assessor.identify_weaknesses()
            for weakness in weaknesses[:3]:
                if any(
                    word in concept.lower() for word in weakness.capability_name.lower().split()
                ):
                    base_usefulness += 0.15

        return min(1.0, base_usefulness + random.uniform(-0.1, 0.1))

    def _estimate_difficulty(self, domain: CuriosityDomain, concept: str) -> float:
        """估计难度"""
        difficulty = 0.5

        if concept in domain.known_concepts:
            difficulty -= 0.3

        if len(domain.known_concepts) > 10:
            difficulty -= 0.1

        complexity_keywords = ["深度", "高级", "复杂", "多维", "非线性"]
        for keyword in complexity_keywords:
            if keyword in concept:
                difficulty += 0.15

        return max(0.1, min(1.0, difficulty))

    async def _identify_prerequisites(
        self,
        domain: CuriosityDomain,
        concept: str,
    ) -> list[str]:
        """识别前置知识"""
        prerequisites = []

        for known in domain.known_concepts[:3]:
            prerequisites.append(known)

        if self.llm:
            try:
                prompt = f"""学习"{concept}"需要哪些前置知识？请列出最多3个，每个不超过10个字。"""
                response = await self.llm.chat(prompt)
                lines = response.strip().split("\n")[:3]
                for line in lines:
                    clean = line.strip()[:10]
                    if clean and clean not in prerequisites:
                        prerequisites.append(clean)
            except Exception:
                pass

        return prerequisites[:3]

    async def _execute_exploration(
        self,
        path: ExplorationPath,
    ) -> list[str]:
        """执行探索"""
        discoveries = []

        if self.llm:
            try:
                prompt = f"""探索学习关于"{path.target_concept}"的知识。

已知前置知识：{", ".join(path.prerequisites)}

请提供：
1. 核心概念解释
2. 关键原理
3. 应用场景

格式：每项一行，简洁描述。"""
                response = await self.llm.chat(prompt)
                discoveries = [
                    line.strip()
                    for line in response.split("\n")
                    if line.strip() and len(line.strip()) > 5
                ][:5]
            except Exception:
                discoveries = [f"探索了{path.target_concept}的基本概念"]
        else:
            discoveries = [
                f"概念: {path.target_concept}",
                f"领域: {path.start_domain}",
                f"新颖度: {path.expected_novelty:.2f}",
            ]

        return discoveries

    async def _generate_potential_goals(
        self,
        discoveries: list[str],
    ) -> list[str]:
        """从发现中生成潜在目标"""
        goals = []

        for discovery in discoveries[:3]:
            if len(discovery) > 10:
                goal = f"深入理解: {discovery[:20]}..."
            else:
                goal = f"掌握: {discovery}"
            goals.append(goal)

        return goals

    async def _generate_questions(
        self,
        discoveries: list[str],
    ) -> list[str]:
        """生成探索问题"""
        questions = []

        for discovery in discoveries[:2]:
            questions.append(f"如何将{discovery[:15]}应用到实际问题？")

        if self.llm:
            try:
                prompt = f"""基于以下发现，生成2个值得进一步探索的问题：
{chr(10).join(discoveries[:3])}

每行一个问题。"""
                response = await self.llm.chat(prompt)
                for line in response.split("\n"):
                    clean = line.strip()
                    if clean and clean not in questions:
                        questions.append(clean)
            except Exception:
                pass

        return questions[:4]

    def _update_domain_after_exploration(
        self,
        domain: CuriosityDomain,
        result: ExplorationResult,
    ):
        """探索后更新领域状态"""
        domain.last_explored = datetime.now().timestamp()

        domain.exploration_depth = min(1.0, domain.exploration_depth + 0.1)

        for discovery in result.discoveries:
            if discovery not in domain.known_concepts:
                domain.known_concepts.append(discovery)

        if result.novelty_score > 0.7:
            domain.interest_level = min(1.0, domain.interest_level + 0.1)

    async def identify_knowledge_gaps(self) -> list[dict[str, Any]]:
        """
        识别知识缺口

        分析当前知识和能力，找出需要填补的缺口
        """
        await self._ensure_initialized()

        gaps = []

        for domain in self._domains.values():
            if domain.exploration_depth < 0.5:
                gaps.append(
                    {
                        "domain": domain.name,
                        "gap_type": "unexplored",
                        "severity": 1.0 - domain.exploration_depth,
                        "unknown_concepts": domain.unknown_concepts[:5],
                    }
                )

        if self.capability_assessor:
            weaknesses = await self.capability_assessor.identify_weaknesses()
            for weakness in weaknesses[:5]:
                related_domain = self._find_related_domain(weakness.capability_name)
                if related_domain:
                    gaps.append(
                        {
                            "domain": related_domain.name,
                            "gap_type": "capability_weakness",
                            "severity": weakness.gap,
                            "capability": weakness.capability_name,
                        }
                    )

        return sorted(gaps, key=lambda g: g["severity"], reverse=True)

    def _find_related_domain(self, capability_name: str) -> CuriosityDomain | None:
        """找到与能力相关的领域"""
        domain_keywords = {
            "推理": ["推理与规划"],
            "学习": ["机器学习"],
            "规划": ["推理与规划"],
            "创造": ["创造性思维"],
            "语言": ["自然语言处理"],
            "知识": ["知识表示"],
            "交互": ["人机交互"],
            "安全": ["安全性"],
            "优化": ["效率优化"],
        }

        for keyword, domains in domain_keywords.items():
            if keyword in capability_name:
                for domain_name in domains:
                    if domain_name in self._domains:
                        return self._domains[domain_name]

        return None

    async def generate_exploration_goals(
        self,
        count: int = 3,
    ) -> list[LearningGoal]:
        """
        生成探索目标

        基于好奇心和知识缺口生成学习目标
        """
        await self._ensure_initialized()

        goals = []
        gaps = await self.identify_knowledge_gaps()

        for gap in gaps[:count]:
            domain = gap["domain"]

            priority = GoalPriority.HIGH if gap["severity"] > 0.7 else GoalPriority.MEDIUM

            goal = LearningGoal(
                title=f"探索{domain}领域",
                description=f"填补{domain}领域的知识缺口",
                priority=priority,
                target_capability=gap.get("capability"),
                learning_type="self_supervised",
                expected_outcomes=[
                    f"理解{domain}核心概念",
                    f"能够应用{domain}相关知识",
                ],
            )

            goals.append(goal)

        return goals

    async def evaluate_novelty(
        self,
        content: str,
    ) -> float:
        """
        评估内容新颖性

        Args:
            content: 要评估的内容

        Returns:
            新颖性分数 (0-1)
        """
        await self._ensure_initialized()

        if self.knowledge:
            try:
                similar = await self.knowledge.retrieve(content, top_k=5)
                if similar:
                    return 1.0 - min(1.0, len(similar) * 0.15)
            except Exception:
                pass

        words = set(content.lower().split())
        known_words = set()
        for domain in self._domains.values():
            known_words.update(w.lower() for c in domain.known_concepts for w in c.split())

        if known_words:
            overlap = len(words & known_words) / len(words) if words else 0
            return 1.0 - overlap

        return 0.5

    def update_curiosity_level(self, performance: float):
        """
        更新好奇心水平

        Args:
            performance: 近期表现分数
        """
        if performance > 0.8:
            self._curiosity_level = min(1.0, self._curiosity_level + 0.05)
        elif performance < 0.5:
            self._curiosity_level = max(0.3, self._curiosity_level - 0.05)

    def get_curiosity_stats(self) -> dict[str, Any]:
        """获取好奇心统计"""
        return {
            "curiosity_level": self._curiosity_level,
            "exploration_budget": self._exploration_budget,
            "exploration_count": self._exploration_count,
            "domains": {
                name: {
                    "depth": d.exploration_depth,
                    "interest": d.interest_level,
                    "known_concepts": len(d.known_concepts),
                    "unknown_concepts": len(d.unknown_concepts),
                }
                for name, d in self._domains.items()
            },
            "total_explorations": len(self._exploration_history),
        }

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    def reset_exploration_budget(self):
        """重置探索预算"""
        self._exploration_count = 0

    def add_domain(self, domain: CuriosityDomain):
        """添加新领域"""
        self._domains[domain.name] = domain
