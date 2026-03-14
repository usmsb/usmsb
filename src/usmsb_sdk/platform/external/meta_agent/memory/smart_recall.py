"""
智能记忆召回系统 - 万事不决问LLM
核心思想：每个不确定的决策都调用LLM来智能决定

基于 USMSB 设计文档 v1.0 实现
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class RetrievalDimension(StrEnum):
    """检索维度枚举"""
    SEMANTIC_VECTOR = "semantic_vector"       # 语义向量
    KEYWORD = "keyword"                        # 关键词精确匹配
    TASK_TYPE = "task_type"                   # 任务类型
    TIME_CONTEXT = "time_context"             # 时间上下文
    ENTITY_RELATION = "entity_relation"       # 实体关联
    EXPERIENCE_LESSON = "experience_lesson"   # 经验教训
    USER_DOCUMENT = "user_document"           # 用户文档
    KNOWLEDGE_BASE = "knowledge_base"        # 知识库
    KNOWLEDGE_GRAPH = "knowledge_graph"      # 知识图谱


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    timestamp: float
    importance: float = 0.5
    dimensions: dict[str, Any] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)
    task_type: str | None = None
    success: bool | None = None  # None=未评估, True=成功, False=失败
    user_emphasized: bool = False   # 用户是否强调要记住
    embedding: list[float] | None = None

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().timestamp()


@dataclass
class RetrievalResult:
    """检索结果"""
    items: list[MemoryItem]
    scores: dict[str, float]
    reasoning: str  # LLM给出的检索理由


@dataclass
class IntentUnderstanding:
    """意图理解结果"""
    explicit_intent: str = ""      # 显式意图
    implicit_intent: str = ""       # 隐式意图
    potential_intent: str = ""      # 潜在意图
    entities: list[str] = field(default_factory=list)
    task_type: str = "general"
    reasoning: str = ""


class IntelligentRecall:
    """
    智能召回系统
    核心：万事不决问LLM

    流程：
    1. 智能理解 - 用户真正想要什么？
    2. 智能决策 - 用哪些维度检索？
    3. 智能检索 - 不确定再问LLM
    4. 智能排序 - 不确定排优先级？
    5. 智能组装 - 空间不够放哪些？
    6. 智能压缩 - 不确定压缩哪个？
    """

    def __init__(self, llm_manager, memory_db, vector_store=None, knowledge_graph=None):
        """
        初始化智能召回系统

        Args:
            llm_manager: LLM管理器
            memory_db: 记忆数据库
            vector_store: 向量存储（可选）
            knowledge_graph: 知识图谱（可选）
        """
        self.llm = llm_manager
        self.memory_db = memory_db
        self.vector_store = vector_store
        self.kg = knowledge_graph

        # 检索维度默认权重
        self.dimension_weights: dict[RetrievalDimension, float] = {
            RetrievalDimension.SEMANTIC_VECTOR: 0.20,
            RetrievalDimension.KEYWORD: 0.15,
            RetrievalDimension.TASK_TYPE: 0.15,
            RetrievalDimension.TIME_CONTEXT: 0.10,
            RetrievalDimension.ENTITY_RELATION: 0.10,
            RetrievalDimension.EXPERIENCE_LESSON: 0.15,
            RetrievalDimension.USER_DOCUMENT: 0.10,
            RetrievalDimension.KNOWLEDGE_BASE: 0.025,
            RetrievalDimension.KNOWLEDGE_GRAPH: 0.025,
        }

        # 配置
        self.default_top_k = 20
        self.max_items_for_llm_ranking = 30
        self.compression_ratio = 0.7  # 压缩到70%

    async def recall(
        self,
        user_input: str,
        context: dict[str, Any]
    ) -> str:
        """
        主召回流程

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            格式化后的召回上下文
        """
        logger.info(f"Starting intelligent recall for: {user_input[:50]}...")

        # Step 1: 智能理解 - 用户真正想要什么？
        understanding = await self._smart_understand(user_input, context)
        logger.info(f"Intent understanding: {understanding.task_type}, entities: {understanding.entities}")

        # Step 2: 智能决策 - 用哪些维度检索？
        dimensions = await self._smart_decide_dimensions(understanding, context)
        logger.info(f"Retrieval dimensions: {[d.value for d in dimensions]}")

        # Step 3: 智能检索 - 多维度并行检索
        raw_results = await self._smart_search(understanding, dimensions, context)
        logger.info(f"Raw results count: {sum(len(r.items) for r in raw_results)}")

        # Step 4: 智能排序 - 不确定排优先级？
        sorted_items = await self._smart_rank(understanding, raw_results, context)
        logger.info(f"Sorted items count: {len(sorted_items)}")

        # Step 5: 智能组装 - 空间不够放哪些？
        assembled_items = await self._smart_assemble(sorted_items, context)
        logger.info(f"Assembled items count: {len(assembled_items)}")

        # Step 6: 智能压缩 - 不确定压缩哪个？
        final_context = await self._smart_compress(assembled_items, context)

        logger.info(f"Final context length: {len(final_context)} chars")
        return final_context

    # ==================== Step 1: 智能理解 ====================

    async def _smart_understand(
        self,
        user_input: str,
        context: dict[str, Any]
    ) -> IntentUnderstanding:
        """智能理解：调用LLM分析用户真正想要什么"""
        prompt = f"""分析用户输入，提取意图信息。

用户输入: {user_input}

当前上下文:
{json.dumps(context, ensure_ascii=False, indent=2)[:500]}

请分析并返回JSON格式:
{{
    "explicit_intent": "用户明确说的意图",
    "implicit_intent": "用户没明说但相关的意图",
    "potential_intent": "用户可能需要的意图",
    "entities": ["涉及到的实体列表"],
    "task_type": "任务类型如: general, coding, analysis, search, etc.",
    "reasoning": "分析理由"
}}"""

        try:
            response = await self.llm.chat(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return IntentUnderstanding(
                explicit_intent=data.get("explicit_intent", ""),
                implicit_intent=data.get("implicit_intent", ""),
                potential_intent=data.get("potential_intent", ""),
                entities=data.get("entities", []),
                task_type=data.get("task_type", "general"),
                reasoning=data.get("reasoning", "")
            )
        except Exception as e:
            logger.warning(f"Smart understand failed: {e}, using fallback")
            # 降级处理
            return IntentUnderstanding(
                explicit_intent=user_input,
                entities=[],
                task_type="general"
            )

    # ==================== Step 2: 智能决策 ====================

    async def _smart_decide_dimensions(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> list[RetrievalDimension]:
        """智能决策：调用LLM决定用哪些维度检索"""
        prompt = f"""基于意图分析结果，决定检索维度。

意图分析:
- 显式意图: {understanding.explicit_intent}
- 隐式意图: {understanding.implicit_intent}
- 潜在意图: {understanding.potential_intent}
- 实体: {understanding.entities}
- 任务类型: {understanding.task_type}

可用维度:
- semantic_vector: 语义向量相似
- keyword: 关键词精确匹配
- task_type: 同类任务经验
- time_context: 时间上下文相关
- entity_relation: 同一实体相关
- experience_lesson: 成功/失败经验
- user_document: 用户提供的文档
- knowledge_base: 内部知识库
- knowledge_graph: 知识图谱关系

请决定使用哪些维度，返回JSON:
{{
    "dimensions": ["dim1", "dim2", ...],
    "weights": {{"dim1": 0.3, "dim2": 0.2, ...}},
    "reasoning": "理由"
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            # 更新权重
            if "weights" in data:
                for dim_str, weight in data["weights"].items():
                    try:
                        dim = RetrievalDimension(dim_str)
                        self.dimension_weights[dim] = weight
                    except ValueError:
                        pass

            dimensions = []
            for dim_str in data.get("dimensions", []):
                try:
                    dimensions.append(RetrievalDimension(dim_str))
                except ValueError:
                    pass

            return dimensions if dimensions else [RetrievalDimension.SEMANTIC_VECTOR]

        except Exception as e:
            logger.warning(f"Smart decide dimensions failed: {e}, using defaults")
            # 默认使用语义向量
            return [RetrievalDimension.SEMANTIC_VECTOR]

    # ==================== Step 3: 智能检索 ====================

    async def _smart_search(
        self,
        understanding: IntentUnderstanding,
        dimensions: list[RetrievalDimension],
        context: dict[str, Any]
    ) -> list[RetrievalResult]:
        """智能检索：并行执行多维度检索"""
        tasks = []

        for dim in dimensions:
            if dim == RetrievalDimension.SEMANTIC_VECTOR:
                tasks.append(self._search_semantic(understanding, context))
            elif dim == RetrievalDimension.KEYWORD:
                tasks.append(self._search_keyword(understanding, context))
            elif dim == RetrievalDimension.TASK_TYPE:
                tasks.append(self._search_task_type(understanding, context))
            elif dim == RetrievalDimension.TIME_CONTEXT:
                tasks.append(self._search_time_context(understanding, context))
            elif dim == RetrievalDimension.ENTITY_RELATION:
                tasks.append(self._search_entity_relation(understanding, context))
            elif dim == RetrievalDimension.EXPERIENCE_LESSON:
                tasks.append(self._search_experience_lesson(understanding, context))
            elif dim == RetrievalDimension.USER_DOCUMENT:
                tasks.append(self._search_user_document(understanding, context))
            elif dim == RetrievalDimension.KNOWLEDGE_BASE:
                tasks.append(self._search_knowledge_base(understanding, context))
            elif dim == RetrievalDimension.KNOWLEDGE_GRAPH:
                tasks.append(self._search_knowledge_graph(understanding, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for r in results:
            if isinstance(r, RetrievalResult):
                valid_results.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Search dimension failed: {r}")

        return valid_results

    async def _search_semantic(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """语义向量检索"""
        query = understanding.explicit_intent or understanding.potential_intent

        if not query:
            return RetrievalResult(items=[], scores={}, reasoning="No query")

        # 使用向量存储
        if self.vector_store:
            results = await self.vector_store.search(query, top_k=self.default_top_k)

            # 如果结果太少，尝试扩展查询
            if len(results) < 5:
                expanded_query = await self._expand_query(understanding)
                if expanded_query:
                    results = await self.vector_store.search(
                        expanded_query,
                        top_k=self.default_top_k
                    )
        else:
            # 降级到内存搜索
            results = await self._memory_search(query)

        return RetrievalResult(
            items=results,
            scores={"semantic_vector": 1.0},
            reasoning=f"Semantic search: {len(results)} results"
        )

    async def _expand_query(self, understanding: IntentUnderstanding) -> str:
        """调用LLM扩展查询"""
        prompt = f"""为以下意图生成扩展搜索查询。

意图: {understanding.explicit_intent}
实体: {understanding.entities}

返回JSON: {{"queries": ["query1", "query2", ...]}}
"""

        try:
            response = await self.llm.chat(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())
            return " ".join(data.get("queries", []))
        except:
            return ""

    async def _memory_search(self, query: str, top_k: int = 20) -> list[MemoryItem]:
        """内存搜索（降级方案）"""
        if not self.memory_db:
            return []

        try:
            # 简单关键词匹配
            results = await self.memory_db.search(query, limit=top_k)
            return [
                MemoryItem(
                    id=str(r.get("id", "")),
                    content=r.get("content", ""),
                    timestamp=r.get("timestamp", 0),
                    importance=r.get("importance", 0.5)
                )
                for r in results
            ]
        except:
            return []

    async def _search_keyword(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """关键词精确匹配"""
        keywords = understanding.entities
        if not keywords:
            keywords = await self._extract_keywords(understanding)

        results = []
        for kw in keywords:
            if self.memory_db:
                kw_results = await self.memory_db.search_by_keyword(kw)
                results.extend(kw_results)

        # 去重
        unique_results = self._deduplicate(results)

        return RetrievalResult(
            items=unique_results,
            scores={"keyword": 1.0},
            reasoning=f"Keyword search: {keywords}"
        )

    async def _extract_keywords(self, understanding: IntentUnderstanding) -> list[str]:
        """提取关键词"""
        # 使用实体作为关键词
        return understanding.entities

    async def _search_task_type(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """任务类型检索"""
        task_type = understanding.task_type

        if self.memory_db:
            results = await self.memory_db.search_by_task_type(task_type)
        else:
            results = []

        return RetrievalResult(
            items=results,
            scores={"task_type": 1.0},
            reasoning=f"Task type search: {task_type}"
        )

    async def _search_time_context(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """时间上下文检索"""
        # 获取时间范围
        time_range = context.get("time_range", "recent")

        if time_range == "recent":
            # 调用LLM确定时间范围
            time_range = await self._determine_time_range(understanding)

        if self.memory_db:
            results = await self.memory_db.search_by_time(time_range)
        else:
            results = []

        return RetrievalResult(
            items=results,
            scores={"time_context": 1.0},
            reasoning=f"Time context search: {time_range}"
        )

    async def _determine_time_range(self, understanding: IntentUnderstanding) -> str:
        """调用LLM确定时间范围"""
        prompt = f"""确定搜索的时间范围。

意图: {understanding.explicit_intent}
实体: {understanding.entities}

返回: "recent"(最近), "week"(一周), "month"(一月), "all"(全部)

JSON: {{"time_range": "...", "reasoning": "..."}}
"""

        try:
            response = await self.llm.chat(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())
            return data.get("time_range", "recent")
        except:
            return "recent"

    async def _search_entity_relation(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """实体关联检索"""
        entities = understanding.entities
        results = []

        if not entities:
            return RetrievalResult(items=[], scores={}, reasoning="No entities")

        # 知识图谱检索
        if self.kg:
            for entity in entities:
                related = await self.kg.get_related_entities(entity)
                for rel_entity in related:
                    if self.memory_db:
                        rel_results = await self.memory_db.search_by_entity(rel_entity)
                        results.extend(rel_results)

        # 去重
        unique_results = self._deduplicate(results)

        return RetrievalResult(
            items=unique_results,
            scores={"entity_relation": 1.0},
            reasoning=f"Entity relation search: {entities}"
        )

    async def _search_experience_lesson(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """经验教训检索"""
        if not self.memory_db:
            return RetrievalResult(items=[], scores={}, reasoning="No memory DB")

        # 检索成功经验
        success_results = await self.memory_db.search_by_success(success=True)

        # 检索失败教训
        failure_results = await self.memory_db.search_by_success(success=False)

        # 合并
        results = success_results + failure_results

        # 按重要性排序
        results.sort(key=lambda x: x.importance if hasattr(x, 'importance') else 0.5, reverse=True)

        return RetrievalResult(
            items=results[:10],
            scores={"experience_lesson": 1.0},
            reasoning=f"Experience lesson search: {len(results)} results"
        )

    async def _search_user_document(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """用户文档检索"""
        user_docs = context.get("user_documents", [])
        results = []

        for doc in user_docs:
            if self.vector_store:
                doc_results = await self.vector_store.search_in_document(
                    doc.get("id", ""),
                    understanding.explicit_intent
                )
                results.extend(doc_results)

        return RetrievalResult(
            items=results,
            scores={"user_document": 1.0},
            reasoning=f"User document search: {len(user_docs)} docs"
        )

    async def _search_knowledge_base(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """知识库检索"""
        query = understanding.explicit_intent

        if not query:
            return RetrievalResult(items=[], scores={}, reasoning="No query")

        if self.vector_store:
            results = await self.vector_store.search_knowledge_base(query, top_k=10)
        else:
            results = []

        return RetrievalResult(
            items=results,
            scores={"knowledge_base": 1.0},
            reasoning="Knowledge base search"
        )

    async def _search_knowledge_graph(
        self,
        understanding: IntentUnderstanding,
        context: dict[str, Any]
    ) -> RetrievalResult:
        """知识图谱推理"""
        entities = understanding.entities

        if not entities or not self.kg:
            return RetrievalResult(items=[], scores={}, reasoning="No entities or KG")

        results = []
        for entity in entities:
            paths = await self.kg.query_paths(entity, max_depth=3)
            for path in paths:
                item = MemoryItem(
                    id=f"kg_{path.id}",
                    content=path.description,
                    timestamp=path.timestamp,
                    importance=0.7
                )
                results.append(item)

        return RetrievalResult(
            items=results,
            scores={"knowledge_graph": 1.0},
            reasoning=f"Knowledge graph推理: {entities}"
        )

    # ==================== Step 4: 智能排序 ====================

    async def _smart_rank(
        self,
        understanding: IntentUnderstanding,
        results: list[RetrievalResult],
        context: dict[str, Any]
    ) -> list[MemoryItem]:
        """智能排序：调用LLM决定优先级"""
        # 收集所有结果
        all_items = []
        for result in results:
            all_items.extend(result.items)

        # 去重
        unique_items = self._deduplicate(all_items)

        # 如果结果太多或太少，使用LLM排序
        if len(unique_items) > self.max_items_for_llm_ranking or len(unique_items) < 3:
            ranked_items = await self._llm_rank(understanding, unique_items, context)
        else:
            # 使用权重排序
            ranked_items = self._weighted_rank(unique_items)

        return ranked_items

    async def _llm_rank(
        self,
        understanding: IntentUnderstanding,
        items: list[MemoryItem],
        context: dict[str, Any]
    ) -> list[MemoryItem]:
        """调用LLM进行智能排序"""
        items_to_rank = items[:50]  # 限制数量

        items_text = "\n".join([
            f"{i+1}. [{item.id}] {item.content[:100]}... (importance={item.importance})"
            for i, item in enumerate(items_to_rank)
        ])

        prompt = f"""对以下记忆按与当前任务相关性排序。

意图: {understanding.explicit_intent}
任务类型: {understanding.task_type}

记忆条目:
{items_text}

请返回排序后的ID列表（前20个）:
{{"ranked_ids": ["id1", "id2", ...], "reasoning": "..."}}
"""

        try:
            response = await self.llm.chat(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            ranked_ids = data.get("ranked_ids", [])
            id_to_item = {item.id: item for item in items_to_rank}

            ranked_items = [id_to_item[i] for i in ranked_ids if i in id_to_item]

            # 添加未在排名中的
            for item in items_to_rank:
                if item not in ranked_items:
                    ranked_items.append(item)

            return ranked_items

        except Exception as e:
            logger.warning(f"LLM rank failed: {e}")
            return self._weighted_rank(items)

    def _weighted_rank(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """使用权重排序"""
        for item in items:
            score = (
                item.importance * 0.4 +
                (1.0 if item.user_emphasized else 0) * 0.3 +
                (0.5 if item.success is True else 0) * 0.2 +
                (0.3 if item.success is False else 0) * 0.1
            )
            item._rank_score = score

        return sorted(items, key=lambda x: getattr(x, '_rank_score', 0), reverse=True)

    # ==================== Step 5: 智能组装 ====================

    async def _smart_assemble(
        self,
        items: list[MemoryItem],
        context: dict[str, Any]
    ) -> list[MemoryItem]:
        """智能组装：调用LLM决定放入哪些内容"""
        max_tokens = context.get("max_context_tokens", 100000)
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            return items

        # 空间不够，调用LLM决定
        assembled = await self._llm_assemble(items, context, max_tokens)
        return assembled

    async def _llm_assemble(
        self,
        items: list[MemoryItem],
        context: dict[str, Any],
        max_tokens: int
    ) -> list[MemoryItem]:
        """调用LLM决定组装哪些内容"""
        target_length = int(max_tokens * 0.7)

        items_text = "\n".join([
            f"{i+1}. [{item.id}] {item.content[:200]}... (importance={item.importance}, emphasized={item.user_emphasized})"
            for i, item in enumerate(items[:30])
        ])

        prompt = f"""选择最重要的记忆，确保总长度不超过{target_length} tokens。

待选记忆:
{items_text}

返回JSON: {{"selected_ids": ["id1", "id2", ...], "reasoning": "..."}}
"""

        try:
            response = await self.llm.chat(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            selected_ids = data.get("selected_ids", [])
            id_to_item = {item.id: item for item in items}

            return [id_to_item[i] for i in selected_ids if i in id_to_item]

        except Exception as e:
            logger.warning(f"LLM assemble failed: {e}")
            # 降级：截断
            return items[:int(len(items) * 0.7)]

    # ==================== Step 6: 智能压缩 ====================

    async def _smart_compress(
        self,
        items: list[MemoryItem],
        context: dict[str, Any]
    ) -> str:
        """智能压缩：调用LLM决定如何压缩"""
        max_tokens = context.get("max_context_tokens", 100000)
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            return self._format_context(items)

        # 需要压缩
        compressed = await self._llm_compress(items, context, max_tokens)
        return compressed

    async def _llm_compress(
        self,
        items: list[MemoryItem],
        context: dict[str, Any],
        max_tokens: int
    ) -> str:
        """调用LLM进行智能压缩"""
        target_length = int(max_tokens * 0.7)

        context_text = self._format_context(items)

        prompt = f"""将以下记忆压缩总结，保留关键信息，总长度不超过{target_length} tokens。

记忆:
{context_text[:3000]}

请以markdown格式返回压缩后的上下文。
"""

        try:
            response = await self.llm.chat(prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"LLM compress failed: {e}")
            return context_text

    # ==================== 辅助方法 ====================

    def _estimate_length(self, items: list[MemoryItem]) -> int:
        """估算token数量"""
        total_chars = sum(len(item.content) for item in items)
        return total_chars // 4

    def _format_context(self, items: list[MemoryItem]) -> str:
        """格式化上下文"""
        sections = []
        sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

        for item in sorted_items:
            sections.append(f"## {item.id} ({item.timestamp})\n{item.content}")

        return "\n\n".join(sections)

    def _deduplicate(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """去重"""
        seen: set[str] = set()
        unique = []
        for item in items:
            if item.id not in seen:
                seen.add(item.id)
                unique.append(item)
        return unique
