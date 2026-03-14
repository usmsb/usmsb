"""
AGI Core Integration System
整合专业版组件的统一接口

组件来源：
├── agi_core/memory.py        - 本地实现（多层记忆系统）
├── agi_core/knowledge_graph.py - 本地实现（动态知识图谱）
├── evolution_v2/             - 专业版（进化系统）
└── reasoning/                - 专业版（推理系统）
"""

import logging
from dataclasses import dataclass
from typing import Any

from usmsb_sdk.platform.external.meta_agent.evolution_v2 import (
    SelfEvolutionEngine,
    create_evolution_engine,
)
from usmsb_sdk.reasoning import (
    AbductiveEngine,
    AnalogicalEngine,
    CausalEngine,
    DeductiveEngine,
    InductiveEngine,
    ReasoningChainManager,
)

from .knowledge_graph import DynamicKnowledgeGraph, KnowledgeNode, RelationType
from .memory import AGIMemorySystem, MemoryConfig, MemoryLayer

logger = logging.getLogger(__name__)


@dataclass
class AGICoreConfig:
    memory_db: str = "agi_memory.db"
    knowledge_db: str = "agi_knowledge.db"
    enable_evolution: bool = True
    enable_inference: bool = True
    evolution_interval: int = 300


class AGICoreSystem:
    """
    AGI核心系统 - 整合专业版组件

    组件映射：
    ┌─────────────────┬──────────────────────────────────┐
    │ 组件            │ 来源                             │
    ├─────────────────┼──────────────────────────────────┤
    │ memory          │ agi_core/memory.py (本地)        │
    │ knowledge       │ agi_core/knowledge_graph.py (本地)│
    │ evolution       │ evolution_v2/ (专业版)           │
    │ reasoning       │ reasoning/ (专业版)              │
    └─────────────────┴──────────────────────────────────┘
    """

    def __init__(
        self, config: AGICoreConfig | None = None, llm_manager=None, data_dir: str = "."
    ):
        self.config = config or AGICoreConfig()
        self.llm = llm_manager
        self.data_dir = data_dir

        self.memory = AGIMemorySystem(
            db_path=f"{data_dir}/{self.config.memory_db}",
            llm_manager=llm_manager,
            config=MemoryConfig(),
        )
        self.knowledge = DynamicKnowledgeGraph(db_path=f"{data_dir}/{self.config.knowledge_db}")

        self._evolution: SelfEvolutionEngine | None = None
        self._reasoning_manager: ReasoningChainManager | None = None

        self._initialized = False

    async def init(self):
        if self._initialized:
            return

        await self.memory.init()
        await self.knowledge.init()

        if self.config.enable_evolution:
            self._evolution = await create_evolution_engine(
                llm_manager=self.llm,
                knowledge_base=self.knowledge,
                config={"evolution_interval": self.config.evolution_interval},
            )
            await self._evolution.start()

        if self.config.enable_inference:
            self._reasoning_manager = ReasoningChainManager()
            self._register_reasoning_engines()

        self._initialized = True
        logger.info("AGI Core System initialized with professional components")

    def _register_reasoning_engines(self):
        if not self._reasoning_manager or not self.llm:
            return

        self._reasoning_manager.register_engine(DeductiveEngine())
        self._reasoning_manager.register_engine(InductiveEngine())
        self._reasoning_manager.register_engine(AbductiveEngine())
        self._reasoning_manager.register_engine(CausalEngine())
        self._reasoning_manager.register_engine(AnalogicalEngine())

    async def close(self):
        if self._evolution:
            await self._evolution.stop()
        await self.memory.close()
        logger.info("AGI Core System closed")

    async def process_input(
        self,
        content: str,
        user_id: str = "",
        context: dict[str, Any] | None = None,
        usmsb_element: str | None = None,
    ) -> dict[str, Any]:
        await self.init()

        memory = await self.memory.memorize(
            content=content, user_id=user_id, context=context, usmsb_element=usmsb_element
        )

        if usmsb_element:
            await self.knowledge.add_node(
                content=content, usmsb_element=usmsb_element, source=f"user:{user_id}"
            )

        relevant = await self.memory.recall(content, user_id, top_k=5)

        inference_result = None
        if self.config.enable_inference and self._reasoning_manager:
            try:
                result = await self._reasoning_manager.execute(
                    premises=[content], context=context or {}
                )
                inference_result = {
                    "conclusion": str(result.conclusion) if result else None,
                    "confidence": result.confidence.value if result else 0,
                    "type": result.reasoning_type.value if result else None,
                }
            except Exception as e:
                logger.warning(f"Reasoning failed: {e}")

        if self._evolution:
            await self._evolution.learn_from_interaction(
                {
                    "messages": [{"content": content}],
                    "success": True,
                    "task_type": context.get("type", "chat") if context else "chat",
                }
            )

        return {
            "memory_id": memory.id,
            "memory_layer": memory.layer.value,
            "importance": memory.importance,
            "relevant_memories": [{"content": m.content[:100], "score": s} for m, s in relevant],
            "inference": inference_result,
            "evolution_state": self._evolution.get_evolution_state().__dict__
            if self._evolution
            else None,
        }

    async def build_context(self, query: str, user_id: str = "", max_tokens: int = 2000) -> str:
        await self.init()

        parts = []

        memory_context = await self.memory.build_context_prompt(query, user_id)
        if memory_context:
            parts.append(memory_context)

        kg_results = await self.knowledge.query(query, limit=5)
        if kg_results:
            parts.append("\n## 知识图谱")
            for node, score in kg_results[:3]:
                usmsb_tag = f"[{node.usmsb_element}]" if node.usmsb_element else ""
                parts.append(f"- {usmsb_tag} {node.content[:150]} (相关度: {score:.2f})")

        permanent = await self.memory.get_permanent(user_id)
        if permanent:
            parts.append("\n## 永久记忆（永不遗忘）")
            for mem in permanent[:3]:
                parts.append(f"- {mem.content[:150]}")

        if self._evolution:
            report = self._evolution.get_comprehensive_report()
            parts.append("\n## 进化状态")
            parts.append(f"- 阶段: {report['evolution_state']['phase']}")
            parts.append(f"- 知识量: {report['evolution_state']['total_knowledge']}")

        context = "\n".join(parts)

        if len(context) > max_tokens:
            context = context[:max_tokens] + "\n...[已截断]"

        return context

    async def add_usmsb_knowledge(
        self, element: str, content: str, relations: list[dict[str, str]] | None = None
    ) -> KnowledgeNode:
        await self.init()

        node = await self.knowledge.add_node(content=content, usmsb_element=element)

        await self.memory.memorize(
            content=f"[{element}] {content}", layer=MemoryLayer.SEMANTIC, usmsb_element=element
        )

        if relations:
            for rel in relations:
                await self.knowledge.add_edge(
                    source_id=node.id,
                    target_id=rel.get("target_id", ""),
                    relation_type=RelationType(rel.get("type", "relates")),
                )

        return node

    async def smart_recall(
        self, query: str, user_id: str = "", include_reasoning: bool = True
    ) -> dict[str, Any]:
        await self.init()

        memories = await self.memory.recall(query, user_id, top_k=10)

        knowledge = await self.knowledge.query(query, limit=10)

        reasoning = None
        if include_reasoning and self._reasoning_manager:
            try:
                result = await self._reasoning_manager.execute(premises=[query], context={})
                if result:
                    reasoning = {
                        "conclusion": str(result.conclusion),
                        "confidence": result.confidence.value,
                        "chain": [s.to_dict() for s in result.reasoning_chain],
                    }
            except Exception as e:
                logger.warning(f"Reasoning failed: {e}")

        return {
            "memories": [
                {
                    "content": m.content,
                    "layer": m.layer.value,
                    "importance": m.importance,
                    "score": s,
                }
                for m, s in memories
            ],
            "knowledge": [
                {
                    "content": n.content,
                    "usmsb_element": n.usmsb_element,
                    "confidence": n.confidence,
                    "score": s,
                }
                for n, s in knowledge
            ],
            "reasoning": reasoning,
            "stats": {
                "memory_count": len(memories),
                "knowledge_count": len(knowledge),
                "has_reasoning": reasoning is not None,
            },
        }

    async def autonomous_learning(self) -> dict[str, Any]:
        await self.init()

        if not self._evolution:
            return {"status": "evolution_disabled", "learned": 0}

        return await self._evolution.autonomous_learning()

    async def self_reflect(self) -> dict[str, Any]:
        await self.init()

        if not self._evolution:
            return {"status": "evolution_disabled"}

        reflection = await self._evolution.self_reflect()
        return {
            "observations": reflection.observations,
            "strengths": reflection.strengths,
            "weaknesses": reflection.weaknesses,
            "action_items": reflection.action_items,
            "confidence_level": reflection.confidence_level,
        }

    def get_system_stats(self) -> dict[str, Any]:
        stats = {
            "memory": {"initialized": self.memory._initialized},
            "knowledge": self.knowledge.get_stats(),
        }

        if self._evolution:
            stats["evolution"] = self._evolution.get_comprehensive_report()

        return stats

    async def export_knowledge(self) -> dict[str, Any]:
        await self.init()

        permanent = await self.memory.get_permanent()

        export_data = {
            "permanent_memories": [m.to_dict() for m in permanent],
            "knowledge_stats": self.knowledge.get_stats(),
        }

        if self._evolution:
            export_data["evolution_report"] = self._evolution.get_comprehensive_report()

        return export_data
