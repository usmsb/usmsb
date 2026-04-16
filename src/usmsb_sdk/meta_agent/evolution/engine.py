"""
Evolution Engine - Meta Agent 自主进化引擎

基于 USMSB Learning 动作，实现：
1. 从对话中学习 (Conversation Learning)
2. 知识提取与固化 (Knowledge Extraction)
3. 能力评估与优化 (Capability Optimization)
4. 自我反思与进化 (Self-reflection & Evolution)
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


class EvolutionType(StrEnum):
    """进化类型"""

    KNOWLEDGE_GAIN = "knowledge_gain"  # 获得新知识
    SKILL_IMPROVEMENT = "skill_improvement"  # 技能提升
    PATTERN_LEARNING = "pattern_learning"  # 模式学习
    BEHAVIOR_OPTIMIZATION = "behavior_opt"  # 行为优化
    CAPABILITY_EXPANSION = "capability_exp"  # 能力扩展


class EvolutionStatus(StrEnum):
    """进化状态"""

    PENDING = "pending"
    APPLIED = "applied"
    VALIDATED = "validated"
    REJECTED = "rejected"


@dataclass
class EvolutionRecord:
    """进化记录"""

    id: str = field(default_factory=lambda: str(uuid4()))
    type: EvolutionType = EvolutionType.KNOWLEDGE_GAIN
    description: str = ""
    knowledge_content: str = ""
    confidence: float = 0.5
    source_conversation_id: str | None = None
    status: EvolutionStatus = EvolutionStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    applied_at: float | None = None
    effectiveness: float = 0.0
    application_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityMetric:
    """能力指标"""

    name: str
    current_score: float = 0.5
    target_score: float = 1.0
    improvement_rate: float = 0.0
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())


class EvolutionEngine:
    """
    进化引擎

    负责 Meta Agent 的自主学习与进化：
    1. 分析对话模式，提取可复用知识
    2. 评估当前能力，识别改进点
    3. 自动优化行为策略
    4. 固化有效知识到知识库
    """

    def __init__(self, llm_manager, knowledge_base, conversation_manager):
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.conversations = conversation_manager

        # 进化记录
        self._evolution_records: list[EvolutionRecord] = []

        # 能力指标
        self._capabilities: dict[str, CapabilityMetric] = {}

        # 学习配置
        self._learning_threshold = 0.6  # 置信度阈值
        self._evolution_interval = 300  # 进化检查间隔（秒）
        self._running = False
        self._evolution_task: asyncio.Task | None = None

    async def start(self):
        """启动进化引擎"""
        if self._running:
            return

        self._running = True
        self._evolution_task = asyncio.create_task(self._evolution_loop())
        logger.info("Evolution Engine started")

    async def stop(self):
        """停止进化引擎"""
        self._running = False
        if self._evolution_task:
            self._evolution_task.cancel()
            try:
                await self._evolution_task
            except asyncio.CancelledError:
                pass
        logger.info("Evolution Engine stopped")

    async def learn_from_conversation(
        self,
        conversation_id: str,
        messages: list[dict[str, Any]],
    ) -> list[EvolutionRecord]:
        """
        从对话中学习

        分析对话内容，提取：
        - 用户偏好模式
        - 高效的问题解决策略
        - 常见问题类型与答案
        - 工具使用的最佳实践
        """
        if not messages:
            return []

        # 使用 LLM 分析对话
        analysis = await self._analyze_conversation(messages)

        records = []

        # 提取知识
        if analysis.get("knowledge"):
            for knowledge in analysis["knowledge"]:
                record = EvolutionRecord(
                    type=EvolutionType.KNOWLEDGE_GAIN,
                    description=knowledge.get("description", ""),
                    knowledge_content=knowledge.get("content", ""),
                    confidence=knowledge.get("confidence", 0.5),
                    source_conversation_id=conversation_id,
                )
                records.append(record)
                await self._apply_evolution(record)

        # 提取模式
        if analysis.get("patterns"):
            for pattern in analysis["patterns"]:
                record = EvolutionRecord(
                    type=EvolutionType.PATTERN_LEARNING,
                    description=pattern.get("description", ""),
                    knowledge_content=pattern.get("pattern", ""),
                    confidence=pattern.get("confidence", 0.5),
                    source_conversation_id=conversation_id,
                )
                records.append(record)
                await self._apply_evolution(record)

        # 更新能力指标
        if analysis.get("capabilities"):
            for cap in analysis["capabilities"]:
                await self._update_capability(
                    cap["name"],
                    cap.get("score", 0.5),
                    cap.get("improvement", 0.0),
                )

        self._evolution_records.extend(records)
        return records

    async def _analyze_conversation(self, messages: list[dict]) -> dict[str, Any]:
        """使用 LLM 分析对话"""
        conversation_text = "\n".join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages]
        )

        prompt = f"""分析以下对话，提取可学习的知识、模式和改进建议：

{conversation_text[:3000]}

请以 JSON 格式返回：
{{
  "knowledge": [
    {{"description": "知识描述", "content": "具体内容", "confidence": 0.0-1.0}}
  ],
  "patterns": [
    {{"description": "模式描述", "pattern": "模式内容", "confidence": 0.0-1.0}}
  ],
  "capabilities": [
    {{"name": "能力名称", "score": 0.0-1.0, "improvement": 改进幅度}}
  ],
  "improvement_suggestions": ["建议1", "建议2"]
}}"""

        try:
            response = await self.llm.chat(prompt)
            # 尝试解析 JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Failed to analyze conversation: {e}")
            return {}

    async def _apply_evolution(self, record: EvolutionRecord):
        """应用进化"""
        if record.confidence < self._learning_threshold:
            record.status = EvolutionStatus.REJECTED
            return

        # 存储到知识库
        try:
            await self.knowledge.add_knowledge(
                content=record.knowledge_content,
                metadata={
                    "type": record.type.value,
                    "description": record.description,
                    "confidence": record.confidence,
                    "source": record.source_conversation_id,
                },
            )
            record.status = EvolutionStatus.APPLIED
            record.applied_at = datetime.now().timestamp()
            logger.info(f"Applied evolution: {record.type.value} - {record.description[:50]}")
        except Exception as e:
            logger.error(f"Failed to apply evolution: {e}")
            record.status = EvolutionStatus.REJECTED

    async def _update_capability(
        self,
        name: str,
        score: float,
        improvement: float,
    ):
        """更新能力指标"""
        if name not in self._capabilities:
            self._capabilities[name] = CapabilityMetric(name=name)

        cap = self._capabilities[name]
        cap.current_score = min(1.0, cap.current_score + improvement)
        cap.improvement_rate = improvement
        cap.last_updated = datetime.now().timestamp()

    async def reflect_and_improve(self) -> dict[str, Any]:
        """
        自我反思与改进

        定期执行：
        1. 回顾最近的进化记录
        2. 评估进化的有效性
        3. 识别需要改进的领域
        4. 制定改进计划
        """
        # 获取最近的进化记录
        recent_records = self._evolution_records[-20:]

        if not recent_records:
            return {"status": "no_records", "suggestions": []}

        # 计算统计数据
        applied = [r for r in recent_records if r.status == EvolutionStatus.APPLIED]
        effectiveness_avg = sum(r.effectiveness for r in applied) / len(applied) if applied else 0

        # 生成改进建议
        reflection = await self._generate_reflection(recent_records)

        return {
            "total_records": len(recent_records),
            "applied_count": len(applied),
            "effectiveness_avg": effectiveness_avg,
            "capabilities": {k: v.current_score for k, v in self._capabilities.items()},
            "suggestions": reflection.get("suggestions", []),
            "focus_areas": reflection.get("focus_areas", []),
        }

    async def _generate_reflection(self, records: list[EvolutionRecord]) -> dict[str, Any]:
        """生成反思"""
        records_summary = "\n".join(
            [
                f"- {r.type.value}: {r.description} (confidence: {r.confidence})"
                for r in records[-10:]
            ]
        )

        prompt = f"""基于最近的进化记录，进行自我反思：

{records_summary}

当前能力指标：
{json.dumps({k: v.current_score for k, v in self._capabilities.items()}, indent=2)}

请分析：
1. 哪些进化效果较好？为什么？
2. 哪些领域需要更多学习？
3. 下一步改进的重点是什么？

返回 JSON：
{{
  "suggestions": ["建议1", "建议2"],
  "focus_areas": ["重点领域1", "重点领域2"],
  "reasoning": "分析理由"
}}"""

        try:
            response = await self.llm.chat(prompt)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            return json.loads(response.strip())
        except Exception as e:
            logger.error(f"Failed to generate reflection: {e}")
            return {"suggestions": [], "focus_areas": []}

    async def _evolution_loop(self):
        """进化循环 - 定期检查和优化"""
        while self._running:
            try:
                await asyncio.sleep(self._evolution_interval)

                # 执行反思
                reflection = await self.reflect_and_improve()
                logger.info(f"Evolution reflection: {reflection.get('suggestions', [])}")

                # 可以在这里添加自动学习逻辑

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Evolution loop error: {e}")
                await asyncio.sleep(60)

    def get_evolution_stats(self) -> dict[str, Any]:
        """获取进化统计"""
        return {
            "total_evolutions": len(self._evolution_records),
            "by_type": {
                t.value: len([r for r in self._evolution_records if r.type == t])
                for t in EvolutionType
            },
            "by_status": {
                s.value: len([r for r in self._evolution_records if r.status == s])
                for s in EvolutionStatus
            },
            "capabilities": {
                k: {
                    "score": v.current_score,
                    "improvement_rate": v.improvement_rate,
                }
                for k, v in self._capabilities.items()
            },
        }
