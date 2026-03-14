"""
策略选择与编排系统

基于LLM自动选择最优的记忆/召回/守护策略组合

策略维度：
- 召回策略: SMART_RECALL / TRADITIONAL / AGI_MEMORY / HYBRID
- 存储策略: VECTOR_KB / TRADITIONAL_DB / AGI_KG / HYBRID_STORAGE
- 守护策略: GUARDIAN_DAEMON / AGI_CONSOLIDATION / NONE
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class RecallStrategy(StrEnum):
    """召回策略"""

    SMART_RECALL = "SMART_RECALL"  # LLM决策9维检索
    TRADITIONAL = "TRADITIONAL"  # 分层记忆+摘要
    AGI_MEMORY = "AGI_MEMORY"  # 认知5层+遗忘曲线
    HYBRID = "HYBRID"  # 组合策略


class StorageStrategy(StrEnum):
    """存储策略"""

    VECTOR_KB = "VECTOR_KB"  # 向量知识库
    TRADITIONAL_DB = "TRADITIONAL_DB"  # 传统SQLite
    AGI_KG = "AGI_KG"  # USMSB知识图谱
    HYBRID_STORAGE = "HYBRID_STORAGE"  # 组合存储


class GuardianStrategy(StrEnum):
    """守护策略"""

    GUARDIAN_DAEMON = "GUARDIAN_DAEMON"  # 全面自我进化
    AGI_CONSOLIDATION = "AGI_CONSOLIDATION"  # 仅记忆巩固
    NONE = "NONE"  # 不启用守护


@dataclass
class StrategyConfig:
    """策略配置"""

    recall_strategy: RecallStrategy = RecallStrategy.SMART_RECALL
    storage_strategy: StorageStrategy = StorageStrategy.HYBRID_STORAGE
    guardian_strategy: GuardianStrategy = GuardianStrategy.GUARDIAN_DAEMON
    reasoning: str = ""  # 选择理由


@dataclass
class TaskFeatures:
    """任务特征"""

    task_type: str = "general"  # general/coding/analysis/search/creative
    complexity: str = "medium"  # low/medium/high
    need_reasoning: bool = False  # 是否需要推理
    new_knowledge: bool = False  # 是否涉及新知识
    has_entities: bool = False  # 是否涉及实体
    has_error_history: bool = False  # 是否有错误历史
    time_sensitivity: str = "normal"  # urgent/normal
    user_emphasis: bool = False  # 用户是否强调
    context_length: int = 0  # 上下文长度


@dataclass
class ExecutionResult:
    """执行结果"""

    success: bool
    response: str = ""
    strategy_used: StrategyConfig | None = None
    execution_time: float = 0.0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StrategySelector:
    """
    LLM驱动的策略选择器

    核心功能：
    1. 提取任务特征
    2. LLM分析选择最优策略
    3. 返回策略配置
    """

    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def select_strategy(self, user_task: str, context: dict[str, Any]) -> StrategyConfig:
        """
        基于任务特征选择最优策略组合
        """

        # Step 1: 提取任务特征
        features = await self._extract_task_features(user_task, context)

        # Step 2: LLM选择策略
        strategy = await self._llm_select_strategy(user_task, features)

        logger.info(
            f"Strategy selected: {strategy.recall_strategy.value} + {strategy.storage_strategy.value} + {strategy.guardian_strategy.value}"
        )
        logger.info(f"Reasoning: {strategy.reasoning}")

        return strategy

    async def _extract_task_features(self, user_task: str, context: dict[str, Any]) -> TaskFeatures:
        """提取任务特征"""

        # 使用LLM分析任务特征
        prompt = f"""分析以下用户任务，提取任务特征。

用户任务: {user_task}

请返回JSON格式的特征分析:
{{
    "task_type": "general/coding/analysis/search/creative",
    "complexity": "low/medium/high",
    "need_reasoning": true/false,
    "new_knowledge": true/false,
    "has_entities": true/false,
    "has_error_history": true/false,
    "time_sensitivity": "urgent/normal",
    "user_emphasis": true/false,
    "context_length": 数字
}}
"""

        try:
            response = await self.llm.chat(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return TaskFeatures(
                task_type=data.get("task_type", "general"),
                complexity=data.get("complexity", "medium"),
                need_reasoning=data.get("need_reasoning", False),
                new_knowledge=data.get("new_knowledge", False),
                has_entities=data.get("has_entities", False),
                has_error_history=data.get("has_error_history", False),
                time_sensitivity=data.get("time_sensitivity", "normal"),
                user_emphasis=data.get("user_emphasis", False),
                context_length=data.get("context_length", 0),
            )

        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}, using defaults")
            return TaskFeatures()

    async def _llm_select_strategy(self, user_task: str, features: TaskFeatures) -> StrategyConfig:
        """LLM选择策略"""

        prompt = f"""作为策略选择专家，请为以下任务选择最优策略组合。

用户任务: {user_task}

任务特征:
- 任务类型: {features.task_type}
- 复杂度: {features.complexity}
- 是否需要推理: {features.need_reasoning}
- 是否涉及新知识: {features.new_knowledge}
- 是否有实体: {features.has_entities}
- 是否有错误历史: {features.has_error_history}
- 时间敏感度: {features.time_sensitivity}
- 用户是否强调: {features.user_emphasis}

【召回策略】
- SMART_RECALL: LLM决策9维检索，适合复杂/模糊/需要推理的任务
- TRADITIONAL: 分层记忆+摘要，适合简单明确任务
- AGI_MEMORY: 认知5层+遗忘曲线，适合需要长期记忆的任务
- HYBRID: 组合策略

【存储策略】
- VECTOR_KB: 向量知识库，适合精确检索
- TRADITIONAL_DB: 传统SQLite，适合结构化数据
- AGI_KG: USMSB知识图谱，适合关系推理
- HYBRID_STORAGE: 组合存储

【守护策略】
- GUARDIAN_DAEMON: 全面自我进化，适合长期/复杂任务
- AGI_CONSOLIDATION: 仅记忆巩固，适合简单任务
- NONE: 不启用守护，适合快速响应

请选择最优组合:
{{
    "recall_strategy": "SMART_RECALL/TRADITIONAL/AGI_MEMORY/HYBRID",
    "storage_strategy": "VECTOR_KB/TRADITIONAL_DB/AGI_KG/HYBRID_STORAGE",
    "guardian_strategy": "GUARDIAN_DAEMON/AGI_CONSOLIDATION/NONE",
    "reasoning": "为什么选择这个组合"
}}
"""

        try:
            response = await self.llm.chat(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            return StrategyConfig(
                recall_strategy=RecallStrategy(data.get("recall_strategy", "SMART_RECALL")),
                storage_strategy=StorageStrategy(data.get("storage_strategy", "HYBRID_STORAGE")),
                guardian_strategy=GuardianStrategy(
                    data.get("guardian_strategy", "GUARDIAN_DAEMON")
                ),
                reasoning=data.get("reasoning", ""),
            )

        except Exception as e:
            logger.warning(f"Strategy selection failed: {e}, using defaults")
            return StrategyConfig(
                recall_strategy=RecallStrategy.SMART_RECALL,
                storage_strategy=StorageStrategy.HYBRID_STORAGE,
                guardian_strategy=GuardianStrategy.GUARDIAN_DAEMON,
                reasoning="Default fallback due to error",
            )


class StrategyOrchestrator:
    """
    策略编排器

    管理多策略切换，执行任务
    """

    def __init__(
        self,
        llm_manager,
        config: StrategyConfig | None = None,
        # 组件注入
        memory_manager=None,
        vector_kb=None,
        agi_memory=None,
        agi_kg=None,
        smart_recall=None,
        guardian_daemon=None,
        conversation_manager=None,
    ):
        self.llm = llm_manager
        self.config = config or StrategyConfig()
        self.selector = StrategySelector(llm_manager)

        # 注入的组件
        self.memory_manager = memory_manager
        self.vector_kb = vector_kb
        self.agi_memory = agi_memory
        self.agi_kg = agi_kg
        self.smart_recall = smart_recall
        self.guardian_daemon = guardian_daemon
        self.conversation_manager = conversation_manager

        # 当前激活的组件
        self._active_recall = None
        self._active_storage = None
        self._active_guardian = None

        # 执行历史
        self._execution_history: list[dict[str, Any]] = []

        logger.info("StrategyOrchestrator initialized")

    async def select_and_execute(
        self,
        user_task: str,
        user_id: str = "",
        context: dict[str, Any] | None = None,
        force_strategy: StrategyConfig | None = None,
    ) -> ExecutionResult:
        """
        选择策略并执行
        """

        start_time = datetime.now()
        context = context or {}

        try:
            # Step 1: LLM选择策略
            if force_strategy:
                strategy = force_strategy
            else:
                strategy = await self.selector.select_strategy(user_task, context)

            logger.info(
                f"Using strategy: {strategy.recall_strategy.value} + {strategy.storage_strategy.value} + {strategy.guardian_strategy.value}"
            )

            # Step 2: 设置组件
            await self._setup_components(strategy)

            # Step 3: 执行召回
            recall_context = await self._execute_recall(
                strategy.recall_strategy, user_task, user_id, context
            )

            # Step 4: 执行存储（如需要）
            await self._execute_storage(strategy.storage_strategy, user_task, user_id, context)

            # Step 5: 触发守护（如需要）
            await self._execute_guardian(strategy.guardian_strategy, user_task, context)

            execution_time = (datetime.now() - start_time).total_seconds()

            result = ExecutionResult(
                success=True,
                response=recall_context,
                strategy_used=strategy,
                execution_time=execution_time,
            )

            # 记录执行历史
            await self._record_execution(user_task, strategy, result)

            return result

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                strategy_used=self.config,
                execution_time=(datetime.now() - start_time).total_seconds(),
            )

    async def _setup_components(self, strategy: StrategyConfig):
        """根据策略配置设置组件"""

        # 召回组件
        if strategy.recall_strategy == RecallStrategy.SMART_RECALL:
            self._active_recall = self.smart_recall
        elif strategy.recall_strategy == RecallStrategy.TRADITIONAL:
            self._active_recall = self.memory_manager
        elif strategy.recall_strategy == RecallStrategy.AGI_MEMORY:
            self._active_recall = self.agi_memory

        # 存储组件
        if strategy.storage_strategy == StorageStrategy.VECTOR_KB:
            self._active_storage = self.vector_kb
        elif strategy.storage_strategy == StorageStrategy.TRADITIONAL_DB:
            self._active_storage = self.memory_manager
        elif strategy.storage_strategy == StorageStrategy.AGI_KG:
            self._active_storage = self.agi_kg

        # 守护组件
        if strategy.guardian_strategy == GuardianStrategy.GUARDIAN_DAEMON:
            self._active_guardian = self.guardian_daemon

    async def _execute_recall(
        self, strategy: RecallStrategy, user_task: str, user_id: str, context: dict[str, Any]
    ) -> str:
        """执行召回"""

        if strategy == RecallStrategy.SMART_RECALL and self.smart_recall:
            recall_result = await self.smart_recall.recall(user_task, context)
        elif strategy == RecallStrategy.AGI_MEMORY and self.agi_memory:
            recall_result = await self.agi_memory.build_context_prompt(user_task, user_id)
        elif strategy == RecallStrategy.TRADITIONAL and self.memory_manager:
            mem_context = await self.memory_manager.get_context(user_id)
            recall_result = self.memory_manager.build_context_prompt(mem_context)
        elif strategy == RecallStrategy.HYBRID:
            results = []
            if self.smart_recall:
                sr_result = await self.smart_recall.recall(user_task, context)
                results.append(sr_result)
            if self.agi_memory:
                agi_result = await self.agi_memory.build_context_prompt(user_task, user_id)
                results.append(agi_result)
            recall_result = "\n\n".join(results)
        else:
            recall_result = ""

        # ===== 方案一：跨会话历史消息搜索 =====
        history_context = await self._search_conversation_history(user_id, user_task)

        # ===== 方案五：动态更新重要实体 =====
        if history_context:
            await self._dynamic_update_from_recall(user_id, history_context)

        # 合并结果
        if history_context:
            if recall_result:
                return f"{recall_result}\n\n## 历史对话相关\n\n{history_context}"
            return history_context

        return recall_result

    async def _search_conversation_history(self, user_id: str, query: str) -> str:
        """
        方案一：跨会话搜索历史消息

        搜索用户所有会话中的消息，用于召回历史敏感信息等场景。
        """
        if not self.conversation_manager:
            return ""

        try:
            results = await self.conversation_manager.search_all_conversations(
                owner_id=user_id, query=query, limit=10
            )

            if not results:
                return ""

            formatted_results = []
            for r in results:
                timestamp = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
                formatted_results.append(
                    f"- [{timestamp}] {r['conversation_title']}\n  {r['content'][:200]}..."
                )

            return "## 历史对话搜索结果\n\n" + "\n".join(formatted_results)

        except Exception as e:
            logger.warning(f"Failed to search conversation history: {e}")
            return ""

    async def _dynamic_update_from_recall(self, user_id: str, recalled_content: str):
        """
        方案五：动态更新从召回中发现的敏感信息

        被召回的内容中发现重要实体时，自动更新到 important_memories。
        """
        if not self.memory_manager:
            return

        try:
            await self.memory_manager.dynamic_update_from_recall(
                user_id=user_id, recalled_content=recalled_content, source="strategy_orchestrator"
            )
        except Exception as e:
            logger.warning(f"Failed to dynamic update memories: {e}")

    async def _execute_storage(
        self, strategy: StorageStrategy, user_task: str, user_id: str, context: dict[str, Any]
    ):
        """执行存储"""

        if strategy == StorageStrategy.AGI_KG and self.agi_kg:
            # 存储到知识图谱
            await self.agi_kg.add_node(content=user_task, source=f"user:{user_id}")
        elif strategy == StorageStrategy.VECTOR_KB and self.vector_kb:
            # 存储到向量库
            await self.vector_kb.add_document(user_task, metadata={"user_id": user_id})

    async def _execute_guardian(
        self, strategy: GuardianStrategy, user_task: str, context: dict[str, Any]
    ):
        """执行守护"""

        if strategy == GuardianStrategy.GUARDIAN_DAEMON and self.guardian_daemon:
            self.guardian_daemon.notify_task_complete()
        elif strategy == GuardianStrategy.AGI_CONSOLIDATION and self.agi_memory:
            # AGI memory 有内置的自动巩固
            pass

    async def _record_execution(
        self, user_task: str, strategy: StrategyConfig, result: ExecutionResult
    ):
        """记录执行历史"""

        record = {
            "task": user_task[:100],
            "strategy": {
                "recall": strategy.recall_strategy.value,
                "storage": strategy.storage_strategy.value,
                "guardian": strategy.guardian_strategy.value,
            },
            "success": result.success,
            "execution_time": result.execution_time,
            "timestamp": datetime.now().timestamp(),
        }

        self._execution_history.append(record)

        # 保留最近100条
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-100:]

    def get_execution_history(self) -> list[dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""

        if not self._execution_history:
            return {"total_executions": 0}

        # 统计策略使用情况
        recall_counts = {}
        storage_counts = {}
        guardian_counts = {}

        for record in self._execution_history:
            recall_counts[record["strategy"]["recall"]] = (
                recall_counts.get(record["strategy"]["recall"], 0) + 1
            )
            storage_counts[record["strategy"]["storage"]] = (
                storage_counts.get(record["strategy"]["storage"], 0) + 1
            )
            guardian_counts[record["strategy"]["guardian"]] = (
                guardian_counts.get(record["strategy"]["guardian"], 0) + 1
            )

        return {
            "total_executions": len(self._execution_history),
            "success_rate": sum(1 for r in self._execution_history if r["success"])
            / len(self._execution_history),
            "avg_execution_time": sum(r["execution_time"] for r in self._execution_history)
            / len(self._execution_history),
            "recall_strategy_usage": recall_counts,
            "storage_strategy_usage": storage_counts,
            "guardian_strategy_usage": guardian_counts,
        }
