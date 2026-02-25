"""
知识固化器 - Knowledge Solidifier

将临时知识转化为永久能力
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .models import (
    KnowledgeUnit,
    KnowledgeState,
    Capability,
)

logger = logging.getLogger(__name__)


@dataclass
class SolidificationRule:
    """固化规则"""

    name: str
    condition: Dict[str, Any]
    target_state: KnowledgeState
    priority: int = 0


@dataclass
class SolidificationResult:
    """固化结果"""

    knowledge_id: str
    old_state: KnowledgeState
    new_state: KnowledgeState
    success: bool
    confidence: float
    message: str


class KnowledgeSolidifier:
    """
    知识固化器

    核心职责：
    1. 知识状态管理 - 管理知识从临时到永久的转化
    2. 固化决策 - 决定何时固化哪些知识
    3. 知识压缩 - 压缩冗余知识
    4. 知识验证 - 验证固化的知识有效性
    5. 能力转化 - 将知识转化为能力
    """

    EPISODIC_THRESHOLD = 1
    WORKING_THRESHOLD = 3
    SEMANTIC_THRESHOLD = 10
    PROCEDURAL_THRESHOLD = 20
    SUCCESS_RATE_THRESHOLD = 0.7

    def __init__(self, llm_manager=None, knowledge_base=None, capability_assessor=None):
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.capability_assessor = capability_assessor

        self._knowledge_units: Dict[str, KnowledgeUnit] = {}
        self._solidification_rules: List[SolidificationRule] = []
        self._solidification_history: List[SolidificationResult] = []

        self._consolidation_queue: List[str] = []
        self._last_consolidation: float = 0

        self._initialized = False

    async def initialize(self):
        """初始化知识固化器"""
        if self._initialized:
            return

        self._initialize_solidification_rules()

        self._initialized = True
        logger.info("KnowledgeSolidifier initialized")

    def _initialize_solidification_rules(self):
        """初始化固化规则"""
        self._solidification_rules = [
            SolidificationRule(
                name="frequent_access",
                condition={"min_access_count": self.WORKING_THRESHOLD},
                target_state=KnowledgeState.WORKING,
                priority=1,
            ),
            SolidificationRule(
                name="high_success_rate",
                condition={"min_success_rate": self.SUCCESS_RATE_THRESHOLD},
                target_state=KnowledgeState.SEMANTIC,
                priority=2,
            ),
            SolidificationRule(
                name="procedural_mastery",
                condition={
                    "min_access_count": self.PROCEDURAL_THRESHOLD,
                    "min_success_rate": 0.8,
                },
                target_state=KnowledgeState.PROCEDURAL,
                priority=3,
            ),
            SolidificationRule(
                name="crystallization",
                condition={
                    "min_access_count": 50,
                    "min_success_rate": 0.9,
                    "min_confidence": 0.9,
                },
                target_state=KnowledgeState.CRYSTALLIZED,
                priority=4,
            ),
        ]

    async def add_knowledge(
        self,
        content: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加新知识

        新知识以EPISODIC状态开始
        """
        await self._ensure_initialized()

        unit = KnowledgeUnit(
            content=content,
            state=KnowledgeState.EPISODIC,
            source=source,
            metadata=metadata or {},
        )

        self._knowledge_units[unit.id] = unit

        logger.debug(f"Added knowledge {unit.id} in EPISODIC state")

        return unit.id

    async def access_knowledge(
        self,
        knowledge_id: str,
        success: bool = True,
    ) -> Optional[KnowledgeUnit]:
        """
        访问知识并记录

        每次访问都会触发状态检查
        """
        await self._ensure_initialized()

        if knowledge_id not in self._knowledge_units:
            return None

        unit = self._knowledge_units[knowledge_id]
        unit.access_count += 1
        unit.last_accessed = datetime.now().timestamp()

        if success:
            unit.success_rate = (
                unit.success_rate * (unit.access_count - 1) + 1.0
            ) / unit.access_count
        else:
            unit.success_rate = (unit.success_rate * (unit.access_count - 1)) / unit.access_count

        await self._check_solidification(unit)

        return unit

    async def _check_solidification(self, unit: KnowledgeUnit):
        """检查是否需要固化"""
        for rule in sorted(
            self._solidification_rules,
            key=lambda r: r.priority,
            reverse=True,
        ):
            if self._matches_rule(unit, rule):
                if unit.state != rule.target_state:
                    await self._solidify(unit, rule)
                break

    def _matches_rule(self, unit: KnowledgeUnit, rule: SolidificationRule) -> bool:
        """检查知识是否匹配规则"""
        conditions = rule.condition

        if "min_access_count" in conditions:
            if unit.access_count < conditions["min_access_count"]:
                return False

        if "min_success_rate" in conditions:
            if unit.success_rate < conditions["min_success_rate"]:
                return False

        if "min_confidence" in conditions:
            if unit.confidence < conditions["min_confidence"]:
                return False

        return True

    async def _solidify(
        self,
        unit: KnowledgeUnit,
        rule: SolidificationRule,
    ) -> SolidificationResult:
        """执行固化"""
        old_state = unit.state
        new_state = rule.target_state

        success = True
        message = f"Solidified by rule: {rule.name}"

        try:
            unit.state = new_state
            unit.confidence = min(1.0, unit.confidence + 0.1)

            if new_state in [KnowledgeState.SEMANTIC, KnowledgeState.PROCEDURAL]:
                await self._store_to_knowledge_base(unit)

            if new_state == KnowledgeState.PROCEDURAL:
                await self._convert_to_capability(unit)

            logger.info(f"Knowledge {unit.id} solidified: {old_state.value} -> {new_state.value}")

        except Exception as e:
            success = False
            message = f"Solidification failed: {str(e)}"
            logger.error(f"Solidification error: {e}")

        result = SolidificationResult(
            knowledge_id=unit.id,
            old_state=old_state,
            new_state=new_state,
            success=success,
            confidence=unit.confidence,
            message=message,
        )

        self._solidification_history.append(result)

        return result

    async def _store_to_knowledge_base(self, unit: KnowledgeUnit):
        """存储到知识库"""
        if self.knowledge:
            try:
                await self.knowledge.add_knowledge(
                    content=unit.content,
                    metadata={
                        "state": unit.state.value,
                        "access_count": unit.access_count,
                        "success_rate": unit.success_rate,
                        "source": unit.source,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to store to knowledge base: {e}")

    async def _convert_to_capability(self, unit: KnowledgeUnit):
        """将知识转化为能力"""
        if not self.capability_assessor:
            return

        capability_name = await self._extract_capability_name(unit)

        if capability_name:
            existing = None
            for cap in self.capability_assessor.get_all_capabilities().values():
                if cap.name == capability_name:
                    existing = cap
                    break

            if existing:
                existing.add_experience(True, unit.success_rate)
            else:
                new_capability = Capability(
                    name=capability_name,
                    description=f"From knowledge: {unit.content[:100]}",
                    score=unit.success_rate,
                )
                self.capability_assessor.add_capability(new_capability)
                logger.info(f"Created new capability: {capability_name}")

    async def _extract_capability_name(self, unit: KnowledgeUnit) -> Optional[str]:
        """从知识单元提取能力名称"""
        if self.llm:
            try:
                prompt = f"""从以下知识内容中提取一个简短的能力名称（最多4个字）：
{unit.content[:200]}

只输出能力名称，不要其他内容。"""
                response = await self.llm.chat(prompt)
                return response.strip()[:4]
            except Exception:
                pass

        words = unit.content.split()[:3]
        return "_".join(words) if words else None

    async def consolidate_knowledge(self) -> Dict[str, Any]:
        """
        批量固化知识

        对所有知识进行状态检查和固化
        """
        await self._ensure_initialized()

        results = {
            "checked": 0,
            "solidified": 0,
            "failed": 0,
            "details": [],
        }

        for unit_id, unit in self._knowledge_units.items():
            results["checked"] += 1

            old_state = unit.state
            await self._check_solidification(unit)

            if unit.state != old_state:
                results["solidified"] += 1
                results["details"].append(
                    {
                        "id": unit_id,
                        "from": old_state.value,
                        "to": unit.state.value,
                    }
                )

        self._last_consolidation = datetime.now().timestamp()

        return results

    async def compress_knowledge(self) -> Dict[str, Any]:
        """
        压缩知识

        合并相似知识，删除冗余
        """
        await self._ensure_initialized()

        results = {
            "merged": 0,
            "deleted": 0,
            "space_saved": 0,
        }

        clusters = await self._cluster_similar_knowledge()

        for cluster in clusters:
            if len(cluster) > 1:
                merged = await self._merge_knowledge_cluster(cluster)
                if merged:
                    results["merged"] += len(cluster) - 1
                    results["space_saved"] += len(cluster) - 1

        low_value = [uid for uid, unit in self._knowledge_units.items() if self._is_low_value(unit)]

        for uid in low_value:
            del self._knowledge_units[uid]
            results["deleted"] += 1

        return results

    async def _cluster_similar_knowledge(self) -> List[List[str]]:
        """聚类相似知识"""
        clusters = []
        visited = set()

        for uid1, unit1 in self._knowledge_units.items():
            if uid1 in visited:
                continue

            cluster = [uid1]
            visited.add(uid1)

            for uid2, unit2 in self._knowledge_units.items():
                if uid2 in visited:
                    continue

                if await self._are_similar(unit1, unit2):
                    cluster.append(uid2)
                    visited.add(uid2)

            if len(cluster) > 1:
                clusters.append(cluster)

        return clusters

    async def _are_similar(
        self,
        unit1: KnowledgeUnit,
        unit2: KnowledgeUnit,
    ) -> bool:
        """判断两个知识单元是否相似"""
        if unit1.state != unit2.state:
            return False

        if unit1.embeddings and unit2.embeddings:
            similarity = self._cosine_similarity(unit1.embeddings, unit2.embeddings)
            return similarity > 0.9

        content1 = set(unit1.content.lower().split())
        content2 = set(unit2.content.lower().split())

        if not content1 or not content2:
            return False

        intersection = content1 & content2
        union = content1 | content2

        jaccard = len(intersection) / len(union) if union else 0
        return jaccard > 0.7

    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """计算余弦相似度"""
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _merge_knowledge_cluster(
        self,
        cluster: List[str],
    ) -> Optional[str]:
        """合并知识簇"""
        units = [self._knowledge_units[uid] for uid in cluster]

        best_unit = max(units, key=lambda u: u.consolidate_score())

        for uid in cluster:
            if uid != best_unit.id:
                unit = self._knowledge_units[uid]
                best_unit.associations.extend(unit.associations)
                del self._knowledge_units[uid]

        return best_unit.id

    def _is_low_value(self, unit: KnowledgeUnit) -> bool:
        """判断是否为低价值知识"""
        age_days = (datetime.now().timestamp() - unit.created_at) / 86400

        return (
            unit.state == KnowledgeState.EPISODIC
            and unit.access_count < self.EPISODIC_THRESHOLD
            and age_days > 30
            and unit.success_rate < 0.3
        )

    async def validate_knowledge(
        self,
        knowledge_id: str,
    ) -> Dict[str, Any]:
        """验证知识有效性"""
        await self._ensure_initialized()

        if knowledge_id not in self._knowledge_units:
            return {"valid": False, "reason": "not_found"}

        unit = self._knowledge_units[knowledge_id]

        validation = {
            "valid": True,
            "confidence": unit.confidence,
            "success_rate": unit.success_rate,
            "access_count": unit.access_count,
            "state": unit.state.value,
            "issues": [],
        }

        if unit.success_rate < 0.5:
            validation["issues"].append("low_success_rate")
            validation["valid"] = False

        if unit.state == KnowledgeState.EPISODIC and unit.access_count < 2:
            validation["issues"].append("unverified")
            validation["valid"] = False

        if self.llm:
            content_validation = await self._validate_content_with_llm(unit)
            validation["content_validation"] = content_validation
            if not content_validation.get("valid", True):
                validation["valid"] = False
                validation["issues"].append("content_invalid")

        return validation

    async def _validate_content_with_llm(
        self,
        unit: KnowledgeUnit,
    ) -> Dict[str, Any]:
        """使用LLM验证内容"""
        if not self.llm:
            return {"valid": True}

        try:
            prompt = f"""验证以下知识的正确性和实用性（回答是/否并说明理由）：
{unit.content[:500]}"""
            response = await self.llm.chat(prompt)
            return {
                "valid": "是" in response or "yes" in response.lower(),
                "reason": response[:200],
            }
        except Exception:
            return {"valid": True}

    def get_knowledge_state_summary(self) -> Dict[str, Any]:
        """获取知识状态摘要"""
        summary = {
            "total": len(self._knowledge_units),
            "by_state": {},
            "avg_success_rate": 0.0,
            "avg_confidence": 0.0,
            "solidification_history": len(self._solidification_history),
        }

        if not self._knowledge_units:
            return summary

        for state in KnowledgeState:
            count = len([u for u in self._knowledge_units.values() if u.state == state])
            summary["by_state"][state.value] = count

        summary["avg_success_rate"] = sum(
            u.success_rate for u in self._knowledge_units.values()
        ) / len(self._knowledge_units)

        summary["avg_confidence"] = sum(u.confidence for u in self._knowledge_units.values()) / len(
            self._knowledge_units
        )

        return summary

    async def _ensure_initialized(self):
        """确保已初始化"""
        if not self._initialized:
            await self.initialize()

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeUnit]:
        """获取知识单元"""
        return self._knowledge_units.get(knowledge_id)

    def search_knowledge(
        self,
        query: str,
        state_filter: Optional[KnowledgeState] = None,
        top_k: int = 10,
    ) -> List[KnowledgeUnit]:
        """搜索知识"""
        results = []
        query_lower = query.lower()

        for unit in self._knowledge_units.values():
            if state_filter and unit.state != state_filter:
                continue

            if query_lower in unit.content.lower():
                results.append(unit)

        results.sort(key=lambda u: u.consolidate_score(), reverse=True)

        return results[:top_k]
