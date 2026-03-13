# USMSB智能Agent系统设计方案

> 版本: v1.0
> 日期: 2026-02-23
> 目标: 构建具有自主进化能力的AGI智能Agent

---

## 一、需求建模

### 1.1 核心需求

| 需求 | 描述 |
|------|------|
| 准确理解意图 | 理解用户真正想要什么，而不是只听表面话 |
| 超出期望 | 给用户的结果超出他预期的答案 |
| 不删除历史 | 所有历史信息完整保留，不能遗忘 |
| 精准提取 | 每次任务能准确从历史中找到相关信息 |
| 记住教训 | 不犯同样的错误，记住失败的经验 |
| 记住成功 | 记住成功的经验，下次能用上 |
| 推理能力 | 归纳、演绎、因果推理 |
| 自我审核 | 生成答案后反复检验打磨 |
| 自主完成 | 不断尝试直到成功，不问用户行不行 |
| 错误自愈 | 工具调用失败自己修复（JSON错误、参数错误等） |

### 1.2 信息来源

| 类型 | 来源 |
|------|------|
| 外部 | 基因胶囊、虾聊、Moltbook、X |
| 内部 | 知识库，知识图谱、聊天反馈、Agent交流 |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层                                 │
│                    输入目标 → 输出结果                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     理解层 (Understanding)                       │
│   理解用户真正目标 │ 意图深度理解 │ 主动补充                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       规划层 (Planning)                          │
│                制定执行计划 │ 分解为具体步骤                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   尝试-执行-自愈层 (Agent Loop)                   │
│                                                                 │
│   执行计划 → 结果检查 → 验证目标                                │
│       ↓           ↓         ↓                                  │
│   工具错误?   失败?     没完成?                                │
│       ↓           ↓         ↓                                  │
│   自己修复     换方法     调整方案                            │
│       ↓           ↓         ↓                                  │
│       └───────────┴─────────┘                                  │
│                   ↓                                            │
│           目标达成? ──是──→ 审核层                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      审核层 (Self-Check)                         │
│            常识检查 │ 逻辑检查 │ 一致性检查 │ 打磨优化          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      学习层 (Learning)                           │
│        错误记录 │ 教训提取 │ 成功经验 │ 模式识别              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      记忆层 (Memory)                             │
│     历史永久存储 │ 多维检索 │ 经验关联 │ 教训关联              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      知识层 (Knowledge)                          │
│            知识库 │ 知识图谱 │ 向量检索 │ 外部学习              │
└─────────────────────────────────────────────────────────────────┘

                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                     守护进程 (Guardian Daemon)                    │
│    独立运行 │ 复盘总结 │ 主动学习 │ 能力评估 │ 目标调整       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 理解层

**功能：准确理解用户意图并超出期望**

- 显式意图：用户明确说的
- 隐式意图：用户没明说但相关的
- 潜在意图：用户可能需要的

### 3.2 规划层

**功能：制定执行计划**

执行方式选择：
- 预定程序：知识库/记忆处理程序
- Tools：Agent中已有的工具
- LLM：各种适合的LLM（用户提供的）
- 知识库：查内部知识
- 知识图谱：关系推理
- 向量检索：语义搜索

### 3.3 尝试-执行-自愈层

**功能：不断尝试直到成功**

核心原则：
- 不问用户"能不能做"
- 不说"我做不了"
- 遇到错误自己修复
- 尝试所有可能的方法
- 必须完成任务闭环

自愈机制：
1. 工具调用错误 → 自己修复
2. 执行失败 → 换方法
3. 结果不理想 → 调整继续

### 3.4 审核层

**功能：确保答案正确**

- 常识检查
- 逻辑检查
- 一致性检查
- 打磨优化

### 3.5 学习层

**功能：记住教训和经验**

- 错误记录
- 教训提取
- 成功经验
- 主动应用

---

## 四、知识与记忆的智能召回实现方案

### 4.1 核心思想：万事不决问LLM

```
每个不确定的决策 → 调用LLM → 智能决定
```

### 4.2 智能召回流程

```
用户输入
    ↓
智能理解：用户真正想要什么？→ LLM分析
    ↓
智能决策：用哪些维度检索？→ LLM决定
    ↓
智能检索：不确定就再问LLM
    ↓
智能排序：不确定排优先级？→ LLM决定
    ↓
智能组装：空间不够放哪些？→ LLM决定
    ↓
智能压缩：不确定压缩哪个？→ LLM决定
    ↓
最终上下文
```

### 4.3 检索维度

| 维度 | 描述 |
|------|------|
| 语义向量 | 语义相似的内容 |
| 关键词 | 精确匹配 |
| 任务类型 | 同类任务经验 |
| 时间上下文 | 近期相关 |
| 实体关联 | 同一实体相关 |
| 经验教训 | 成功/失败经验 |
| 用户文档 | 用户提供的文档/网页 |
| 知识库 | 内部知识 |
| 知识图谱 | 关系推理 |

### 4.4 用户文档/网页处理

用户提供的文档和网页也需要：
- 提取内容
- 智能理解（LLM）
- 向量索引
- 检索使用

### 4.5 智能召回实现代码

```python
"""
智能记忆召回系统 - 万事不决问LLM
核心思想：每个不确定的决策都调用LLM来智能决定
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio


class RetrievalDimension(Enum):
    """检索维度枚举"""
    SEMANTIC_VECTOR = "semantic_vector"      # 语义向量
    KEYWORD = "keyword"                        # 关键词精确匹配
    TASK_TYPE = "task_type"                    # 任务类型
    TIME_CONTEXT = "time_context"              # 时间上下文
    ENTITY_RELATION = "entity_relation"        # 实体关联
    EXPERIENCE_LESSON = "experience_lesson"    # 经验教训
    USER_DOCUMENT = "user_document"             # 用户文档
    KNOWLEDGE_BASE = "knowledge_base"          # 知识库
    KNOWLEDGE_GRAPH = "knowledge_graph"        # 知识图谱


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    timestamp: float
    importance: float = 0.5
    dimensions: Dict[str, Any] = field(default_factory=dict)
    entities: List[str] = field(default_factory=list)
    task_type: Optional[str] = None
    success: Optional[bool] = None  # None=未评估, True=成功, False=失败
    user_emphasized: bool = False  # 用户是否强调要记住


@dataclass
class RetrievalResult:
    """检索结果"""
    items: List[MemoryItem]
    scores: Dict[str, float]
    reasoning: str  # LLM给出的检索理由


class IntelligentRecall:
    """
    智能召回系统
    核心：万事不决问LLM
    """

    def __init__(self, llm_client, vector_store, knowledge_graph, memory_db):
        self.llm = llm_client
        self.vector_store = vector_store
        self.kg = knowledge_graph
        self.memory_db = memory_db

        # 检索维度配置
        self.dimension_weights = {
            RetrievalDimension.SEMANTIC_VECTOR: 0.2,
            RetrievalDimension.KEYWORD: 0.15,
            RetrievalDimension.TASK_TYPE: 0.15,
            RetrievalDimension.TIME_CONTEXT: 0.1,
            RetrievalDimension.ENTITY_RELATION: 0.1,
            RetrievalDimension.EXPERIENCE_LESSON: 0.15,
            RetrievalDimension.USER_DOCUMENT: 0.1,
            RetrievalDimension.KNOWLEDGE_BASE: 0.025,
            RetrievalDimension.KNOWLEDGE_GRAPH: 0.025,
        }

    async def recall(self, user_input: str, context: Dict[str, Any]) -> str:
        """
        主召回流程：智能理解 → 智能决策 → 智能检索 → 智能排序 → 智能组装 → 智能压缩
        """
        # Step 1: 智能理解 - 用户真正想要什么？
        understanding = await self._smart_understand(user_input, context)

        # Step 2: 智能决策 - 用哪些维度检索？
        dimensions = await self._smart_decide_dimensions(understanding, context)

        # Step 3: 智能检索 - 不确定就再问LLM
        raw_results = await self._smart_search(understanding, dimensions, context)

        # Step 4: 智能排序 - 不确定排优先级？
        sorted_results = await self._smart_rank(understanding, raw_results, context)

        # Step 5: 智能组装 - 空间不够放哪些？
        assembled = await self._smart_assemble(sorted_results, context)

        # Step 6: 智能压缩 - 不确定压缩哪个？
        final_context = await self._smart_compress(assembled, context)

        return final_context

    async def _smart_understand(self, user_input: str, context: Dict) -> Dict:
        """智能理解：调用LLM分析用户真正想要什么"""
        prompt = f"""
        用户输入: {user_input}
        当前上下文: {json.dumps(context, ensure_ascii=False, indent=2)}

        请分析：
        1. 用户的显式意图（明确说的）
        2. 用户的隐式意图（没明说但相关的）
        3. 用户的潜在意图（可能需要的）
        4. 涉及哪些实体？
        5. 任务类型是什么？

        请以JSON格式返回分析结果。
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能意图分析助手。"},
            {"role": "user", "content": prompt}
        ])

        return json.loads(response.content)

    async def _smart_decide_dimensions(self, understanding: Dict, context: Dict) -> List[RetrievalDimension]:
        """智能决策：调用LLM决定用哪些维度检索"""
        prompt = f"""
        意图分析结果: {json.dumps(understanding, ensure_ascii=False, indent=2)}
        当前上下文: {json.dumps(context, ensure_ascii=False)}

        可用检索维度:
        - semantic_vector: 语义向量相似
        - keyword: 关键词精确匹配
        - task_type: 同类任务经验
        - time_context: 时间上下文相关
        - entity_relation: 同一实体相关
        - experience_lesson: 成功/失败经验
        - user_document: 用户提供的文档
        - knowledge_base: 内部知识库
        - knowledge_graph: 知识图谱关系

        请决定使用哪些维度以及权重。
        返回JSON格式: {{"dimensions": ["semantic_vector", "keyword", ...], "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能检索策略助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        dimensions = [RetrievalDimension(d) for d in result.get("dimensions", [])]

        # 更新权重配置
        for dim in dimensions:
            if dim not in self.dimension_weights:
                self.dimension_weights[dim] = 0.1

        return dimensions

    async def _smart_search(self, understanding: Dict, dimensions: List[RetrievalDimension], context: Dict) -> List[RetrievalResult]:
        """智能检索：并行执行多维度检索，不确定再问LLM"""
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
        valid_results = [r for r in results if isinstance(r, RetrievalResult)]

        return valid_results

    async def _search_semantic(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """语义向量检索"""
        query = understanding.get("explicit_intent", "")
        results = await self.vector_store.search(query, top_k=20)

        # 检查结果质量，如果不好再问LLM
        if len(results) < 5:
            # 结果太少，尝试扩展查询
            expanded_query = await self._expand_query(understanding)
            results = await self.vector_store.search(expanded_query, top_k=20)

        return RetrievalResult(
            items=results,
            scores={"semantic": 1.0},
            reasoning="语义向量检索完成"
        )

    async def _expand_query(self, understanding: Dict) -> str:
        """调用LLM扩展查询"""
        prompt = f"""
        意图分析: {json.dumps(understanding, ensure_ascii=False)}

        请生成多个搜索查询词，用于扩展语义搜索。
        返回JSON格式: {{"queries": ["query1", "query2", ...]}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个查询扩展助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        return " ".join(result.get("queries", []))

    async def _search_keyword(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """关键词精确匹配"""
        keywords = understanding.get("entities", [])
        results = []

        for kw in keywords:
            kw_results = await self.memory_db.search_by_keyword(kw)
            results.extend(kw_results)

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique_results.append(r)

        return RetrievalResult(
            items=unique_results,
            scores={"keyword": 1.0},
            reasoning=f"关键词检索完成: {keywords}"
        )

    async def _search_task_type(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """任务类型检索"""
        task_type = understanding.get("task_type", "general")
        results = await self.memory_db.search_by_task_type(task_type)

        return RetrievalResult(
            items=results,
            scores={"task_type": 1.0},
            reasoning=f"任务类型检索完成: {task_type}"
        )

    async def _search_time_context(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """时间上下文检索"""
        # 获取用户指定的时间范围或使用近期
        time_range = context.get("time_range", "recent")  # recent, week, month, all

        if time_range == "recent":
            # 调用LLM确定"近期"的定义
            time_range = await self._determine_time_range(understanding)

        results = await self.memory_db.search_by_time(time_range)

        return RetrievalResult(
            items=results,
            scores={"time_context": 1.0},
            reasoning=f"时间上下文检索完成: {time_range}"
        )

    async def _determine_time_range(self, understanding: Dict) -> str:
        """调用LLM确定时间范围"""
        prompt = f"""
        意图分析: {json.dumps(understanding, ensure_ascii=False)}

        请确定搜索的时间范围，返回以下之一: "recent", "week", "month", "all"
        返回JSON格式: {{"time_range": "...", "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个时间范围判断助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        return result.get("time_range", "recent")

    async def _search_entity_relation(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """实体关联检索"""
        entities = understanding.get("entities", [])
        results = []

        for entity in entities:
            # 从知识图谱获取关联实体
            related = await self.kg.get_related_entities(entity)

            # 检索关联实体的记忆
            for rel_entity in related:
                rel_results = await self.memory_db.search_by_entity(rel_entity)
                results.extend(rel_results)

        # 去重
        seen = set()
        unique_results = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                unique_results.append(r)

        return RetrievalResult(
            items=unique_results,
            scores={"entity_relation": 1.0},
            reasoning=f"实体关联检索完成: {entities}"
        )

    async def _search_experience_lesson(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """经验教训检索"""
        # 检索成功经验和失败教训
        success_results = await self.memory_db.search_by_success(success=True)
        failure_results = await self.memory_db.search_by_success(success=False)

        # 合并结果
        results = success_results + failure_results

        # 按重要性排序
        results.sort(key=lambda x: x.importance, reverse=True)

        return RetrievalResult(
            items=results[:10],
            scores={"experience_lesson": 1.0},
            reasoning="经验教训检索完成"
        )

    async def _search_user_document(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """用户文档检索"""
        user_docs = context.get("user_documents", [])
        results = []

        for doc in user_docs:
            doc_results = await self.vector_store.search_in_document(
                doc["id"],
                understanding.get("explicit_intent", "")
            )
            results.extend(doc_results)

        return RetrievalResult(
            items=results,
            scores={"user_document": 1.0},
            reasoning=f"用户文档检索完成: {len(user_docs)}个文档"
        )

    async def _search_knowledge_base(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """知识库检索"""
        query = understanding.get("explicit_intent", "")
        results = await self.vector_store.search_knowledge_base(query, top_k=10)

        return RetrievalResult(
            items=results,
            scores={"knowledge_base": 1.0},
            reasoning="知识库检索完成"
        )

    async def _search_knowledge_graph(self, understanding: Dict, context: Dict) -> RetrievalResult:
        """知识图谱推理"""
        entities = understanding.get("entities", [])
        results = []

        for entity in entities:
            # 知识图谱关系推理
            paths = await self.kg.query_paths(entity, max_depth=3)

            # 将路径转换为记忆条目
            for path in paths:
                memory_item = MemoryItem(
                    id=f"kg_path_{path.id}",
                    content=path.description,
                    timestamp=path.timestamp,
                    importance=0.7  # 知识图谱推理结果重要性较高
                )
                results.append(memory_item)

        return RetrievalResult(
            items=results,
            scores={"knowledge_graph": 1.0},
            reasoning=f"知识图谱推理完成: {entities}"
        )

    async def _smart_rank(self, understanding: Dict, results: List[RetrievalResult], context: Dict) -> List[MemoryItem]:
        """智能排序：调用LLM决定优先级"""
        # 收集所有结果
        all_items = []
        for result in results:
            all_items.extend(result.items)

        # 去重
        seen = set()
        unique_items = []
        for item in all_items:
            if item.id not in seen:
                seen.add(item.id)
                unique_items.append(item)

        # 如果结果太多或太少，调用LLM决定排序策略
        if len(unique_items) > 30 or len(unique_items) < 3:
            ranked_items = await self._llm_rank(understanding, unique_items, context)
        else:
            # 使用默认权重排序
            ranked_items = self._weighted_rank(unique_items)

        return ranked_items

    async def _llm_rank(self, understanding: Dict, items: List[MemoryItem], context: Dict) -> List[MemoryItem]:
        """调用LLM进行智能排序"""
        # 限制输入数量
        items_to_rank = items[:50]

        items_text = "\n".join([
            f"{i+1}. [{item.id}] {item.content[:100]}... (importance={item.importance})"
            for i, item in enumerate(items_to_rank)
        ])

        prompt = f"""
        意图分析: {json.dumps(understanding, ensure_ascii=False)}

        待排序记忆条目:
        {items_text}

        请根据当前任务相关性对这些记忆进行排序，返回前20个的ID列表。
        返回JSON格式: {{"ranked_ids": ["id1", "id2", ...], "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能排序助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        ranked_ids = result.get("ranked_ids", [])

        # 按LLM返回的顺序重排
        id_to_item = {item.id: item for item in items_to_rank}
        ranked_items = [id_to_item[i] for i in ranked_ids if i in id_to_item]

        # 添加未在排名中的项目
        for item in items_to_rank:
            if item not in ranked_items:
                ranked_items.append(item)

        return ranked_items

    def _weighted_rank(self, items: List[MemoryItem]) -> List[MemoryItem]:
        """使用权重排序"""
        for item in items:
            # 综合评分
            score = (
                item.importance * 0.4 +
                (1.0 if item.user_emphasized else 0) * 0.3 +  # 用户强调的更重要
                (0.5 if item.success is True else 0) * 0.2 +   # 成功经验
                (0.3 if item.success is False else 0) * 0.1     # 失败教训也有价值
            )
            item._rank_score = score

        return sorted(items, key=lambda x: x._rank_score, reverse=True)

    async def _smart_assemble(self, items: List[MemoryItem], context: Dict) -> List[MemoryItem]:
        """智能组装：调用LLM决定放入哪些内容"""
        # 获取上下文长度限制
        max_tokens = context.get("max_context_tokens", 100000)

        # 估算当前内容长度
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            # 空间足够，全部放入
            return items

        # 空间不够，调用LLM决定
        assembled = await self._llm_assemble(items, context, max_tokens)

        return assembled

    async def _llm_assemble(self, items: List[MemoryItem], context: Dict, max_tokens: int) -> List[MemoryItem]:
        """调用LLM决定组装哪些内容"""
        items_text = "\n".join([
            f"{i+1}. [{item.id}] {item.content[:200]}... (importance={item.importance}, user_emphasized={item.user_emphasized})"
            for i, item in enumerate(items[:30])
        ])

        prompt = f"""
        当前上下文最大tokens: {max_tokens}

        待选记忆条目:
        {items_text}

        请选择最重要的记忆条目，确保总长度不超过{max_tokens * 0.7} tokens。
        返回JSON格式: {{"selected_ids": ["id1", "id2", ...], "reasoning": "..."}}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能组装助手。"},
            {"role": "user", "content": prompt}
        ])

        result = json.loads(response.content)
        selected_ids = result.get("selected_ids", [])

        id_to_item = {item.id: item for item in items}
        selected_items = [id_to_item[i] for i in selected_ids if i in id_to_item]

        return selected_items

    async def _smart_compress(self, items: List[MemoryItem], context: Dict) -> str:
        """智能压缩：调用LLM决定如何压缩"""
        max_tokens = context.get("max_context_tokens", 100000)

        # 估算长度
        current_length = self._estimate_length(items)

        if current_length <= max_tokens * 0.8:
            # 不需要压缩，直接拼接
            return self._format_context(items)

        # 需要压缩，调用LLM
        compressed = await self._llm_compress(items, context, max_tokens)

        return compressed

    async def _llm_compress(self, items: List[MemoryItem], context: Dict, max_tokens: int) -> str:
        """调用LLM进行智能压缩"""
        # 将记忆分组，每组不超过限制
        target_length = int(max_tokens * 0.7)

        prompt = f"""
        请将以下记忆条目压缩总结，保留关键信息，总长度不超过{target_length} tokens。

        记忆条目:
        {self._format_context(items)}

        请以markdown格式返回压缩后的上下文。
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个智能压缩助手。"},
            {"role": "user", "content": prompt}
        ])

        return response.content

    def _estimate_length(self, items: List[MemoryItem]) -> int:
        """估算token数量"""
        total_chars = sum(len(item.content) for item in items)
        return total_chars // 4  # 粗略估算

    def _format_context(self, items: List[MemoryItem]) -> str:
        """格式化上下文"""
        sections = []

        # 按时间排序
        sorted_items = sorted(items, key=lambda x: x.timestamp, reverse=True)

        for item in sorted_items:
            sections.append(f"## {item.id} ({item.timestamp})\n{item.content}")

        return "\n\n".join(sections)


class ContextLengthManager:
    """
    上下文长度管理器
    配置文件 + LLM确认
    """

    # 默认配置
    DEFAULT_CONFIG = {
        "claude-opus-4-6": {"context": 200000, "reserved": 50000},
        "claude-sonnet-4-6": {"context": 200000, "reserved": 50000},
        "claude-haiku-3-5": {"context": 200000, "reserved": 50000},
        "gpt-4o": {"context": 128000, "reserved": 30000},
        "gpt-4o-mini": {"context": 128000, "reserved": 30000},
        "gpt-4-turbo": {"context": 128000, "reserved": 30000},
        "gpt-3.5-turbo": {"context": 16385, "reserved": 4000},
    }

    def __init__(self, llm_client, experience_db):
        self.llm = llm_client
        self.experience_db = experience_db
        self.config = self.DEFAULT_CONFIG.copy()

    def get_limit(self, model: str) -> Dict[str, int]:
        """获取模型限制"""
        return self.config.get(model, {"context": 100000, "reserved": 25000})

    async def handle_context_error(self, model: str, error_msg: str) -> Dict[str, int]:
        """
        处理上下文超限错误
        当超限时问LLM实际长度 → 更新到经验库
        """
        # 从错误信息中提取实际上下文长度
        actual_length = self._extract_context_length(error_msg)

        if actual_length:
            # 更新配置
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }

            # 记录到经验库
            await self._record_experience(model, actual_length)

            return self.get_limit(model)

        # 无法提取，调用LLM询问
        actual_length = await self._ask_llm_context_length(model)

        if actual_length:
            self.config[model] = {
                "context": actual_length,
                "reserved": int(actual_length * 0.25)
            }
            await self._record_experience(model, actual_length)

        return self.get_limit(model)

    def _extract_context_length(self, error_msg: str) -> Optional[int]:
        """从错误信息提取上下文长度"""
        import re

        # 尝试匹配常见的错误信息格式
        patterns = [
            r"context length.*?(\d+)",
            r"maximum.*?(\d+)",
            r"tokens.*?(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_msg.lower())
            if match:
                return int(match.group(1))

        return None

    async def _ask_llm_context_length(self, model: str) -> Optional[int]:
        """调用LLM询问实际上下文长度"""
        prompt = f"""
        模型名称: {model}

        请返回这个模型的准确上下文长度（tokens）。
        如果不确定，请返回空。
        返回JSON格式: {{"context_length": 数字或null}}
        """

        try:
            response = await self.llm.chat([
                {"role": "system", "content": "你是一个模型规格助手。"},
                {"role": "user", "content": prompt}
            ])

            result = json.loads(response.content)
            return result.get("context_length")
        except:
            return None

    async def _record_experience(self, model: str, context_length: int):
        """记录经验到经验库"""
        experience = {
            "type": "context_length",
            "model": model,
            "context_length": context_length,
            "reserved": int(context_length * 0.25),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)
```

### 4.6 错误驱动学习实现

```python
"""
错误驱动学习系统
核心思路：错误发生 → 问LLM解决 → 记住经验 → 下次直接用
"""

from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import traceback


class ErrorType(Enum):
    """错误类型"""
    JSON_FORMAT = "json_format"           # JSON格式错误
    PARAMETER_ERROR = "parameter_error"   # 参数错误
    CONTEXT_OVERFLOW = "context_overflow" # 上下文超限
    PERMISSION_ERROR = "permission_error" # 权限错误
    NETWORK_ERROR = "network_error"       # 网络错误
    TIMEOUT_ERROR = "timeout_error"      # 超时错误
    UNKNOWN_ERROR = "unknown_error"      # 未知错误


@dataclass
class ErrorRecord:
    """错误记录"""
    id: str
    error_type: ErrorType
    error_message: str
    error_traceback: str
    context: Dict[str, Any]
    solution: Optional[str] = None
    resolved: bool = False
    occurrence_count: int = 1


class ErrorDrivenLearning:
    """
    错误驱动学习系统
    核心：每遇错误 → 问LLM → 记住方案 → 下次直接用
    """

    def __init__(self, llm_client, experience_db, tool_registry):
        self.llm = llm_client
        self.experience_db = experience_db
        self.tools = tool_registry

        # 错误类型识别器
        self.error_classifiers = {
            ErrorType.JSON_FORMAT: self._is_json_error,
            ErrorType.PARAMETER_ERROR: self._is_parameter_error,
            ErrorType.CONTEXT_OVERFLOW: self._is_context_overflow,
            ErrorType.PERMISSION_ERROR: self._is_permission_error,
            ErrorType.NETWORK_ERROR: self._is_network_error,
            ErrorType.TIMEOUT_ERROR: self._is_timeout_error,
        }

    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理错误的完整流程
        1. 识别错误类型
        2. 检查是否有已知解决方案
        3. 如果没有，问LLM
        4. 应用解决方案
        5. 记录经验
        """
        # Step 1: 识别错误类型
        error_type = self._classify_error(error, context)

        # Step 2: 检查已知解决方案
        solution = await self._check_known_solution(error_type, error, context)

        if solution:
            # 有已知方案，直接应用
            return await self._apply_solution(solution, context)

        # Step 3: 没有已知方案，问LLM
        solution = await self._ask_llm_solution(error_type, error, context)

        if solution:
            # Step 4: 应用解决方案
            result = await self._apply_solution(solution, context)

            # Step 5: 记录经验
            await self._record_experience(error_type, error, solution, context)

            return result

        # 无法解决，返回原始错误
        raise error

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorType:
        """识别错误类型"""
        error_msg = str(error)

        for error_type, classifier in self.error_classifiers.items():
            if classifier(error_msg, context):
                return error_type

        return ErrorType.UNKNOWN_ERROR

    def _is_json_error(self, error_msg: str, context: Dict) -> bool:
        """是否是JSON格式错误"""
        json_indicators = ["json", "expecting", "decode", "invalid json"]
        return any(ind in error_msg.lower() for ind in json_indicators)

    def _is_parameter_error(self, error_msg: str, context: Dict) -> bool:
        """是否是参数错误"""
        param_indicators = ["parameter", "argument", "missing", "required"]
        return any(ind in error_msg.lower() for ind in param_indicators)

    def _is_context_overflow(self, error_msg: str, context: Dict) -> bool:
        """是否是上下文超限"""
        context_indicators = ["context", "length", "maximum", "tokens", "too long"]
        return any(ind in error_msg.lower() for ind in context_indicators)

    def _is_permission_error(self, error_msg: str, context: Dict) -> bool:
        """是否是权限错误"""
        perm_indicators = ["permission", "denied", "unauthorized", "forbidden", "access"]
        return any(ind in error_msg.lower() for ind in perm_indicators)

    def _is_network_error(self, error_msg: str, context: Dict) -> bool:
        """是否是网络错误"""
        net_indicators = ["connection", "network", "timeout", "dns", "refused"]
        return any(ind in error_msg.lower() for ind in net_indicators)

    def _is_timeout_error(self, error_msg: str, context: Dict) -> bool:
        """是否是超时错误"""
        return "timeout" in error_msg.lower()

    async def _check_known_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """检查已知解决方案"""
        # 从经验库查询
        solutions = await self.experience_db.search_solutions(
            error_type=error_type.value,
            error_message=str(error)[:200],
            tool_name=context.get("tool_name")
        )

        if solutions:
            # 返回最佳匹配
            return solutions[0]

        return None

    async def _ask_llm_solution(self, error_type: ErrorType, error: Exception, context: Dict) -> Optional[Dict]:
        """调用LLM获取解决方案"""
        prompt = f"""
        错误类型: {error_type.value}
        错误信息: {str(error)}
        错误堆栈: {traceback.format_exc()}
        上下文: {json.dumps(context, ensure_ascii=False, indent=2)[:1000]}

        工具注册表中的可用工具: {list(self.tools.keys())}

        请提供解决方案，返回JSON格式:
        {{
            "solution_type": "retry|fix_params|use_alternative|skip|escalate",
            "solution": {{
                // 根据solution_type的不同而不同
                // retry: {{"wait_seconds": 1}}
                // fix_params: {{"fixed_params": {{...}}}}
                // use_alternative: {{"alternative_tool": "tool_name", "params": {{...}}}}
                // skip: {{"reason": "..."}}
                // escalate: {{"reason": "..."}}
            }},
            "reasoning": "为什么这样解决",
            "prevent_future": "如何预防此类错误"
        }}
        """

        response = await self.llm.chat([
            {"role": "system", "content": "你是一个错误解决专家。请提供具体的解决方案。"},
            {"role": "user", "content": prompt}
        ])

        try:
            return json.loads(response.content)
        except:
            return None

    async def _apply_solution(self, solution: Dict, context: Dict) -> Dict[str, Any]:
        """应用解决方案"""
        solution_type = solution.get("solution_type")
        solution_data = solution.get("solution", {})

        if solution_type == "retry":
            # 等待后重试
            wait_seconds = solution_data.get("wait_seconds", 1)
            await asyncio.sleep(wait_seconds)
            return {"action": "retry", "context": context}

        elif solution_type == "fix_params":
            # 修复参数后重试
            fixed_params = solution_data.get("fixed_params", {})
            context["fixed_params"] = fixed_params
            return {"action": "retry_with_fixed_params", "context": context}

        elif solution_type == "use_alternative":
            # 使用替代工具
            alt_tool = solution_data.get("alternative_tool")
            alt_params = solution_data.get("params", {})
            return {
                "action": "use_alternative",
                "tool": alt_tool,
                "params": {**context.get("params", {}), **alt_params}
            }

        elif solution_type == "skip":
            # 跳过
            return {"action": "skip", "reason": solution_data.get("reason")}

        else:
            # 无法处理
            return {"action": "cannot_resolve"}

    async def _record_experience(self, error_type: ErrorType, error: Exception, solution: Dict, context: Dict):
        """记录经验到经验库"""
        experience = {
            "type": "error_solution",
            "error_type": error_type.value,
            "error_message": str(error)[:500],
            "solution": solution,
            "tool_name": context.get("tool_name"),
            "timestamp": asyncio.get_event_loop().time()
        }

        await self.experience_db.add(experience)


# 使用示例
class AgentWithErrorLearning:
    """集成错误驱动学习的Agent"""

    def __init__(self, llm_client, memory_system):
        self.llm = llm_client
        self.memory = memory_system
        self.error_learning = ErrorDrivenLearning(llm_client, memory_system.experience_db, {})

    async def execute_with_self_healing(self, tool_name: str, params: Dict) -> Any:
        """带自愈的执行"""
        context = {
            "tool_name": tool_name,
            "params": params,
            "attempt": 0
        }

        max_attempts = 5

        while context["attempt"] < max_attempts:
            try:
                # 尝试执行
                result = await self._execute_tool(tool_name, params)
                return result

            except Exception as e:
                context["attempt"] += 1

                # 处理错误
                solution = await self.error_learning.handle_error(e, context)

                if solution["action"] == "retry":
                    continue
                elif solution["action"] == "retry_with_fixed_params":
                    params = {**params, **solution["context"].get("fixed_params", {})}
                    continue
                elif solution["action"] == "use_alternative":
                    tool_name = solution["tool"]
                    params = solution["params"]
                    continue
                elif solution["action"] == "skip":
                    return {"skipped": True, "reason": solution["reason"]}
                else:
                    raise e

        raise Exception(f"Max attempts ({max_attempts}) reached")
```

---

## 五、错误驱动学习

### 5.1 核心思路

```
错误发生 → 问LLM解决 → 记住经验 → 下次直接用
```

### 5.2 例子

| 错误 | 问LLM | 记住经验 |
|------|--------|----------|
| JSON格式错误 | 怎么修复？ | 修复方法 |
| 上下文超限 | 实际多少？ | 上下文长度 |
| 参数错误 | 正确参数？ | 正确参数 |
| 权限错误 | 怎么获取？ | 获取方法 |

---

## 六、上下文长度管理

### 6.1 配置文件 + LLM确认

```python
# 配置文件
{
  "claude-opus-4-6": {"context": 200000, "reserved": 50000},
  "gpt-4o": {"context": 128000, "reserved": 30000}
}

# 运行时：当超限时问LLM实际长度 → 更新到经验库
```

---

## 七、守护进程（Guardian Daemon）

### 7.1 核心概念

```
用户任务 ←→ 守护进程（独立运行）

用户任务模式：解决问题 → 完成任务 → 返回结果
守护进程模式：自我进化 → 能力提升 → 准备更好的服务
```

### 7.2 触发条件

| 触发条件 | 描述 |
|----------|------|
| 空闲触发 | 连续N分钟没有用户任务 |
| 任务完成触发 | 完成N个任务后 |
| 错误累积触发 | 连续N个错误 |
| 时间周期触发 | 每小时/每天 |
| 能力缺口触发 | 发现能力不足 |
| 新知识触发 | 发现重要新知识 |

### 7.3 守护任务

1. **复盘总结** - 总结最近的任务执行情况
2. **错误复盘** - 从错误中学习
3. **经验提炼** - 提取成功经验
4. **主动学习** - 主动获取新知识（基因胶囊、虾聊、Moltbook、X）
5. **能力评估** - 评估当前能力水平
6. **目标调整** - 调整进化目标
7. **探索新领域** - 扩展能力边界
8. **知识更新** - 更新知识库
9. **自我优化** - 优化执行策略

### 7.4 守护进程 vs 用户任务

| | 用户任务 | 守护进程 |
|--|----------|----------|
| 目标 | 解决用户问题 | 自我进化、AGI |
| 优先级 | 高 | 低（用户任务优先） |
| 触发 | 用户主动 | 空闲/周期/事件 |

---

## 八、完整执行流程

```
用户给出目标
    ↓
理解层：深度理解用户真正想要什么（目标）
    ↓
记忆层：检索相关历史和经验（智能召回）
    ↓
学习层：应用相关教训和经验
    ↓
规划层：制定执行计划
    ↓
尝试-执行-自愈循环：
    执行 → 检查结果 → 验证目标
        ↓           ↓           ↓
    工具错误? 失败?     没完成?
        ↓           ↓           ↓
    自己修复     换方法     调整方案
        ↓           ↓           ↓
        └───────────┴─────────┘
                ↓
        目标达成? ──是──→
                ↓
审核层：常识检查 + 逻辑检查 + 一致性检查 + 打磨
    ↓
记忆层：记录成功/失败，提取教训
    ↓
返回最终结果给用户

    ↓
    ↓（守护进程独立运行）
    ↓
守护进程触发：
    → 复盘总结
    → 错误复盘
    → 主动学习
    → 能力评估
    → 目标调整
    → 探索新领域
```

---

## 十、策略编排系统（Strategy Orchestration）

### 10.1 背景

项目存在多套记忆和召回系统，需要一个策略编排层来自动选择最优组合。

### 10.2 策略维度

**召回策略（Recall Strategy）:**
- SMART_RECALL: LLM决策9维检索
- TRADITIONAL: 分层记忆+摘要
- AGI_MEMORY: 认知5层+遗忘曲线
- HYBRID: 组合策略

**存储策略（Storage Strategy）:**
- VECTOR_KB: 向量知识库
- TRADITIONAL_DB: 传统SQLite
- AGI_KG: USMSB知识图谱
- HYBRID_STORAGE: 组合存储

**守护策略（Guardian Strategy）:**
- GUARDIAN_DAEMON: 全面自我进化
- AGI_CONSOLIDATION: 仅记忆巩固
- NONE: 不启用守护

### 10.3 LLM策略选择器

```python
class StrategySelector:
    async def select_strategy(self, user_task, context) -> StrategyConfig:
        # 1. 提取任务特征
        features = await self._extract_task_features(user_task, context)

        # 2. LLM选择策略
        strategy = await self._llm_select_strategy(user_task, features)

        return strategy
```

### 10.4 策略编排器

```python
class StrategyOrchestrator:
    async def select_and_execute(
        self,
        user_task: str,
        user_id: str = "",
        context: Dict = None,
        force_strategy: StrategyConfig = None
    ) -> ExecutionResult:
        # 1. LLM选择策略
        strategy = await self.selector.select_strategy(user_task, context)

        # 2. 设置组件
        await self._setup_components(strategy)

        # 3. 执行召回
        recall_context = await self._execute_recall(...)

        # 4. 执行存储
        await self._execute_storage(...)

        # 5. 触发守护
        await self._execute_guardian(...)

        return result
```

### 10.5 策略对比效果

| 组合ID | 召回策略 | 存储策略 | 守护策略 | 适用场景 |
|--------|---------|---------|---------|---------|
| 1 | SMART_RECALL | VECTOR_KB | GUARDIAN_DAEMON | 复杂推理任务 |
| 2 | SMART_RECALL | AGI_KG | GUARDIAN_DAEMON | 需要知识图谱 |
| 3 | AGI_MEMORY | AGI_KG | AGI_CONSOLIDATION | 长期记忆任务 |
| 4 | TRADITIONAL | TRADITIONAL_DB | GUARDIAN_DAEMON | 简单明确任务 |
| 5 | HYBRID | HYBRID_STORAGE | GUARDIAN_DAEMON | 综合场景 |

---

## 九、总结

本方案基于USMSB模型，构建了一个具有以下能力的AGI Agent：

1. **深度理解** - 理解用户真正目标
2. **精准记忆** - 历史不删除，精准提取
3. **智能召回** - 万事不决问LLM
4. **自我学习** - 记住成功经验和失败教训
5. **推理能力** - 归纳、演绎推理
6. **自我审核** - 反复检验确保正确
7. **自主完成** - 不断尝试直到成功
8. **错误自愈** - 工具错误自己修复
9. **守护进程** - 独立运行，自我进化

---

**设计完成，请指示下一步。**

