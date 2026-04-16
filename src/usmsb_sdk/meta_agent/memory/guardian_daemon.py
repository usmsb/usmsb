"""
守护进程 (Guardian Daemon)

独立于用户任务的自我进化进程
基于 USMSB 设计文档 v1.0 实现

功能：
1. 复盘总结 - 总结最近的任务执行情况
2. 错误复盘 - 从错误中学习
3. 经验提炼 - 提取成功经验
4. 主动学习 - 主动获取新知识
5. 能力评估 - 评估当前能力水平
6. 目标调整 - 调整进化目标
7. 探索新领域 - 扩展能力边界
8. 知识更新 - 更新知识库
9. 自我优化 - 优化执行策略
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class TriggerType(StrEnum):
    """触发条件类型"""
    IDLE = "idle"                    # 空闲触发
    TASK_COMPLETE = "task_complete"  # 任务完成触发
    ERROR_ACCUMULATED = "error_accumulated"  # 错误累积触发
    SCHEDULED = "scheduled"          # 时间周期触发
    CAPABILITY_GAP = "capability_gap"  # 能力缺口触发
    NEW_KNOWLEDGE = "new_knowledge"  # 新知识触发


class GuardianTask(StrEnum):
    """守护任务类型"""
    REVIEW_SUMMARY = "review_summary"       # 复盘总结
    ERROR_REVIEW = "error_review"           # 错误复盘
    EXPERIENCE_EXTRACTION = "experience_extraction"  # 经验提炼
    ACTIVE_LEARNING = "active_learning"     # 主动学习
    CAPABILITY_ASSESSMENT = "capability_assessment"  # 能力评估
    GOAL_ADJUSTMENT = "goal_adjustment"     # 目标调整
    EXPLORATION = "exploration"             # 探索新领域
    KNOWLEDGE_UPDATE = "knowledge_update"   # 知识更新
    SELF_OPTIMIZATION = "self_optimization" # 自我优化


@dataclass
class GuardianStats:
    """守护进程统计"""
    tasks_completed: int = 0
    last_task_time: float = 0
    total_evolutions: int = 0
    errors_learned_from: int = 0
    experiences_extracted: int = 0


@dataclass
class GuardianConfig:
    """守护进程配置"""
    # 触发条件
    idle_timeout_minutes: int = 5      # 空闲N分钟后触发
    tasks_before_trigger: int = 10     # 完成N个任务后触发
    errors_before_trigger: int = 3     # 连续N个错误后触发

    # 周期触发
    hourly_enabled: bool = True        # 每小时触发
    daily_enabled: bool = True         # 每天触发

    # 任务配置
    max_tasks_per_cycle: int = 3       # 每次最多执行N个任务
    task_timeout_seconds: int = 300    # 任务超时时间

    # 能力阈值
    min_capability_score: float = 0.7  # 最低能力分数


class GuardianDaemon:
    """
    守护进程

    独立于用户任务运行的自我进化系统

    与用户任务的区别：
    - 用户任务：解决问题 → 完成任务 → 返回结果
    - 守护进程：自我进化 → 能力提升 → 准备更好的服务
    """

    def __init__(
        self,
        llm_manager,
        knowledge_base,
        memory_manager,
        evolution_engine,
        config: GuardianConfig | None = None
    ):
        """
        初始化守护进程

        Args:
            llm_manager: LLM管理器
            knowledge_base: 知识库
            memory_manager: 记忆管理器
            evolution_engine: 进化引擎
            config: 配置
        """
        self.llm = llm_manager
        self.knowledge = knowledge_base
        self.memory = memory_manager
        self.evolution = evolution_engine
        self.config = config or GuardianConfig()

        # 状态
        self._running = False
        self._guardian_task: asyncio.Task | None = None

        # 统计
        self.stats = GuardianStats()

        # 任务计数
        self._task_count = 0
        self._error_count = 0
        self._last_task_time = 0.0
        self._idle_since = 0.0

        # 能力评估
        self._capabilities: dict[str, float] = {}
        self._evolution_goals: list[str] = []

    async def start(self):
        """启动守护进程"""
        if self._running:
            return

        self._running = True
        self._guardian_task = asyncio.create_task(self._guardian_loop())
        logger.info("Guardian Daemon started")

    async def stop(self):
        """停止守护进程"""
        self._running = False
        if self._guardian_task:
            self._guardian_task.cancel()
            try:
                await self._guardian_task
            except asyncio.CancelledError:
                pass
        logger.info("Guardian Daemon stopped")

    def notify_task_complete(self):
        """通知任务完成"""
        self._task_count += 1
        self._last_task_time = datetime.now().timestamp()
        self._error_count = 0  # 重置错误计数

        # 检查是否触发
        if self._task_count >= self.config.tasks_before_trigger:
            self._trigger_guardian(TriggerType.TASK_COMPLETE)

    def notify_error(self):
        """通知发生错误"""
        self._error_count += 1

        if self._error_count >= self.config.errors_before_trigger:
            self._trigger_guardian(TriggerType.ERROR_ACCUMULATED)

    def notify_idle(self):
        """通知空闲"""
        self._idle_since = datetime.now().timestamp()

        # 检查空闲时间
        idle_minutes = (datetime.now().timestamp() - self._idle_since) / 60
        if idle_minutes >= self.config.idle_timeout_minutes:
            self._trigger_guardian(TriggerType.IDLE)

    def notify_new_knowledge(self):
        """通知新知识"""
        self._trigger_guardian(TriggerType.NEW_KNOWLEDGE)

    def _trigger_guardian(self, trigger_type: TriggerType):
        """触发守护进程"""
        if not self._running:
            return

        logger.info(f"Guardian triggered by: {trigger_type.value}")

        # 异步执行守护任务（不阻塞主任务）
        asyncio.create_task(self._execute_guardian_tasks(trigger_type))

    async def _guardian_loop(self):
        """守护进程主循环"""
        while self._running:
            try:
                # 周期触发
                if self.config.hourly_enabled:
                    await self._check_hourly_trigger()

                if self.config.daily_enabled:
                    await self._check_daily_trigger()

                # 能力评估触发
                await self._check_capability_trigger()

                # 休息
                await asyncio.sleep(60)  # 每分钟检查一次

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Guardian loop error: {e}")
                await asyncio.sleep(60)

    async def _check_hourly_trigger(self):
        """检查小时触发"""
        # 简化的周期检查
        datetime.now().hour
        # 可以添加更复杂的周期逻辑
        pass

    async def _check_daily_trigger(self):
        """检查每日触发"""
        # 简化的周期检查
        pass

    async def _check_capability_trigger(self):
        """检查能力缺口触发"""
        for cap_name, score in self._capabilities.items():
            if score < self.config.min_capability_score:
                logger.info(f"Capability gap detected: {cap_name} = {score}")
                await self._execute_single_task(GuardianTask.CAPABILITY_ASSESSMENT)
                break

    async def _execute_guardian_tasks(self, trigger_type: TriggerType):
        """执行守护任务"""
        try:
            # 根据触发类型选择任务
            tasks = self._select_tasks(trigger_type)

            # 限制任务数量
            tasks = tasks[:self.config.max_tasks_per_cycle]

            logger.info(f"Executing guardian tasks: {[t.value for t in tasks]}")

            for task in tasks:
                try:
                    await asyncio.wait_for(
                        self._execute_single_task(task),
                        timeout=self.config.task_timeout_seconds
                    )
                    self.stats.tasks_completed += 1

                except TimeoutError:
                    logger.warning(f"Guardian task timeout: {task.value}")
                except Exception as e:
                    logger.error(f"Guardian task failed: {task.value}, error: {e}")

            # 重置计数
            self._task_count = 0

        except Exception as e:
            logger.error(f"Guardian tasks execution failed: {e}")

    def _select_tasks(self, trigger_type: TriggerType) -> list[GuardianTask]:
        """根据触发类型选择任务"""
        if trigger_type == TriggerType.IDLE:
            # 空闲时进行全面复盘
            return [
                GuardianTask.REVIEW_SUMMARY,
                GuardianTask.ERROR_REVIEW,
                GuardianTask.CAPABILITY_ASSESSMENT,
            ]

        elif trigger_type == TriggerType.TASK_COMPLETE:
            # 任务完成后提取经验
            return [
                GuardianTask.EXPERIENCE_EXTRACTION,
                GuardianTask.KNOWLEDGE_UPDATE,
            ]

        elif trigger_type == TriggerType.ERROR_ACCUMULATED:
            # 错误累积时专注错误学习
            return [
                GuardianTask.ERROR_REVIEW,
                GuardianTask.SELF_OPTIMIZATION,
            ]

        elif trigger_type == TriggerType.CAPABILITY_GAP:
            # 能力缺口时评估和调整
            return [
                GuardianTask.CAPABILITY_ASSESSMENT,
                GuardianTask.GOAL_ADJUSTMENT,
                GuardianTask.EXPLORATION,
            ]

        elif trigger_type == TriggerType.NEW_KNOWLEDGE:
            # 新知识时更新知识库
            return [
                GuardianTask.KNOWLEDGE_UPDATE,
                GuardianTask.EXPERIENCE_EXTRACTION,
            ]

        else:  # SCHEDULED
            # 周期任务
            return [
                GuardianTask.REVIEW_SUMMARY,
                GuardianTask.ACTIVE_LEARNING,
                GuardianTask.SELF_OPTIMIZATION,
            ]

    async def _execute_single_task(self, task: GuardianTask):
        """执行单个守护任务"""
        logger.info(f"Executing guardian task: {task.value}")

        if task == GuardianTask.REVIEW_SUMMARY:
            await self._review_summary()
        elif task == GuardianTask.ERROR_REVIEW:
            await self._error_review()
        elif task == GuardianTask.EXPERIENCE_EXTRACTION:
            await self._experience_extraction()
        elif task == GuardianTask.ACTIVE_LEARNING:
            await self._active_learning()
        elif task == GuardianTask.CAPABILITY_ASSESSMENT:
            await self._capability_assessment()
        elif task == GuardianTask.GOAL_ADJUSTMENT:
            await self._goal_adjustment()
        elif task == GuardianTask.EXPLORATION:
            await self._exploration()
        elif task == GuardianTask.KNOWLEDGE_UPDATE:
            await self._knowledge_update()
        elif task == GuardianTask.SELF_OPTIMIZATION:
            await self._self_optimization()

    # ==================== 守护任务实现 ====================

    async def _review_summary(self):
        """复盘总结 - 总结最近的任务执行情况"""
        logger.info("Performing review summary...")

        # 获取最近的对话历史
        recent_conversations = await self.memory.get_recent_conversations(limit=20)

        if not recent_conversations:
            return

        prompt = f"""作为Guardian Daemon，请对最近的任务执行情况进行复盘总结。

最近对话:
{json.dumps(recent_conversations[:10], ensure_ascii=False, indent=2)}

请分析：
1. 整体表现如何？
2. 有哪些成功经验？
3. 有哪些需要改进的地方？
4. 下一步建议？

返回JSON:
{{
    "summary": "总结",
    "successes": ["成功点1", "成功点2"],
    "improvements": ["改进点1", "改进点2"],
    "suggestions": ["建议1", "建议2"]
}}"""

        try:
            response = await self.llm.chat(prompt)

            # 解析并记录
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            logger.info(f"Review summary: {data.get('summary', '')[:200]}")

            # 可以将总结存入知识库
            await self.knowledge.add_knowledge(
                content=data.get("summary", ""),
                metadata={"type": "review_summary", "timestamp": datetime.now().timestamp()}
            )

        except Exception as e:
            logger.error(f"Review summary failed: {e}")

    async def _error_review(self):
        """错误复盘 - 从错误中学习"""
        logger.info("Performing error review...")

        # 获取最近的错误记录
        error_records = await self.memory.get_recent_errors(limit=10)

        if not error_records:
            return

        prompt = f"""作为Guardian Daemon，请对最近的错误进行复盘分析。

错误记录:
{json.dumps(error_records, ensure_ascii=False, indent=2)[:2000]}

请分析：
1. 错误的根本原因是什么？
2. 如何避免类似错误？
3. 可以提取什么经验教训？

返回JSON:
{{
    "root_causes": ["原因1", "原因2"],
    "preventions": ["预防措施1", "预防措施2"],
    "lessons": ["教训1", "教训2"]
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            json.loads(response.strip())

            self.stats.errors_learned_from += len(error_records)
            logger.info(f"Error review completed: {len(error_records)} errors analyzed")

        except Exception as e:
            logger.error(f"Error review failed: {e}")

    async def _experience_extraction(self):
        """经验提炼 - 提取成功经验"""
        logger.info("Extracting experiences...")

        # 获取成功的对话
        successful_conversations = await self.memory.get_successful_conversations(limit=10)

        if not successful_conversations:
            return

        prompt = f"""作为Guardian Daemon，请从成功的对话中提炼可复用的经验。

成功对话:
{json.dumps(successful_conversations[:5], ensure_ascii=False, indent=2)[:2000]}

请提炼：
1. 成功的关键因素
2. 可复用的模式
3. 最佳实践

返回JSON:
{{
    "key_factors": ["因素1", "因素2"],
    "patterns": ["模式1", "模式2"],
    "best_practices": ["实践1", "实践2"]
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            # 存入知识库
            for pattern in data.get("patterns", []):
                await self.knowledge.add_knowledge(
                    content=pattern,
                    metadata={"type": "experience_pattern", "timestamp": datetime.now().timestamp()}
                )

            self.stats.experiences_extracted += len(data.get("patterns", []))
            logger.info(f"Extracted {len(data.get('patterns', []))} experiences")

        except Exception as e:
            logger.error(f"Experience extraction failed: {e}")

    async def _active_learning(self):
        """主动学习 - 主动获取新知识"""
        logger.info("Performing active learning...")

        # 定义学习来源
        learning_sources = [
            "最新技术文档",
            "行业最佳实践",
            "问题解决策略",
        ]

        prompt = f"""作为Guardian Daemon，请主动学习新知识。

可选学习方向:
{json.dumps(learning_sources, ensure_ascii=False)}

请选择一个方向，学习并总结关键知识。
返回JSON:
{{
    "topic": "学习主题",
    "key_points": ["要点1", "要点2", "要点3"],
    "applications": ["应用场景1", "应用场景2"]
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            # 存入知识库
            for point in data.get("key_points", []):
                await self.knowledge.add_knowledge(
                    content=point,
                    metadata={
                        "type": "active_learning",
                        "topic": data.get("topic", ""),
                        "timestamp": datetime.now().timestamp()
                    }
                )

            logger.info(f"Active learning completed: {data.get('topic')}")

        except Exception as e:
            logger.error(f"Active learning failed: {e}")

    async def _capability_assessment(self):
        """能力评估 - 评估当前能力水平"""
        logger.info("Performing capability assessment...")

        # 定义能力维度
        capability_dimensions = [
            "意图理解",
            "知识召回",
            "问题解决",
            "自我学习",
            "错误修复",
            "推理能力",
        ]

        prompt = f"""作为Guardian Daemon，请评估当前的能力水平。

能力维度:
{json.dumps(capability_dimensions, ensure_ascii=False)}

请对每个维度给出0-1的评分，并识别需要提升的领域。
返回JSON:
{{
    "capabilities": {{
        "意图理解": 0.8,
        "知识召回": 0.7,
        ...
    }},
    "improvement_areas": ["需要提升的领域1", "领域2"],
    "strengths": ["优势领域1", "领域2"]
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            # 更新能力评分
            capabilities = data.get("capabilities", {})
            for name, score in capabilities.items():
                self._capabilities[name] = score

            logger.info(f"Capability assessment: {capabilities}")

        except Exception as e:
            logger.error(f"Capability assessment failed: {e}")

    async def _goal_adjustment(self):
        """目标调整 - 调整进化目标"""
        logger.info("Adjusting evolution goals...")

        # 基于能力评估调整目标
        weak_areas = [
            name for name, score in self._capabilities.items()
            if score < self.config.min_capability_score
        ]

        if not weak_areas:
            logger.info("All capabilities above threshold, no adjustment needed")
            return

        prompt = f"""作为Guardian Daemon，请基于当前的能力缺口调整进化目标。

能力缺口: {json.dumps(weak_areas, ensure_ascii=False)}

请制定针对性的提升目标。
返回JSON:
{{
    "goals": ["目标1", "目标2"],
    "priorities": ["优先级1", "优先级2"],
    "timeline": "时间线建议"
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            self._evolution_goals = data.get("goals", [])
            logger.info(f"Evolution goals adjusted: {self._evolution_goals}")

        except Exception as e:
            logger.error(f"Goal adjustment failed: {e}")

    async def _exploration(self):
        """探索新领域 - 扩展能力边界"""
        logger.info("Exploring new domains...")

        prompt = f"""作为Guardian Daemon，请探索新的能力领域。

当前能力: {json.dumps(list(self._capabilities.keys()), ensure_ascii=False)}
当前目标: {json.dumps(self._evolution_goals, ensure_ascii=False)}

请建议可以探索的新领域。
返回JSON:
{{
    "new_domains": ["领域1", "领域2"],
    "relevance": "与当前任务的关联",
    "potential_impact": "潜在影响"
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            logger.info(f"Explored new domains: {data.get('new_domains', [])}")

        except Exception as e:
            logger.error(f"Exploration failed: {e}")

    async def _knowledge_update(self):
        """知识更新 - 更新知识库"""
        logger.info("Updating knowledge base...")

        # 获取待更新的知识
        pending_knowledge = await self.memory.get_pending_knowledge()

        if not pending_knowledge:
            return

        # 验证和固化知识
        for knowledge in pending_knowledge:
            try:
                # LLM验证
                is_valid = await self._validate_knowledge(knowledge)

                if is_valid:
                    await self.knowledge.add_knowledge(
                        content=knowledge["content"],
                        metadata={
                            "type": "validated_knowledge",
                            "source": knowledge.get("source", ""),
                            "timestamp": datetime.now().timestamp()
                        }
                    )
                    await self.memory.mark_knowledge_validated(knowledge["id"])

            except Exception as e:
                logger.warning(f"Knowledge validation failed: {e}")

        logger.info(f"Knowledge update completed: {len(pending_knowledge)} items")

    async def _validate_knowledge(self, knowledge: dict) -> bool:
        """验证知识"""
        prompt = f"""请验证以下知识的准确性。

知识内容:
{knowledge.get('content', '')}

返回JSON: {{"valid": true/false, "reasoning": "理由"}}
"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            return data.get("valid", False)

        except:
            return True  # 默认通过

    async def _self_optimization(self):
        """自我优化 - 优化执行策略"""
        logger.info("Performing self-optimization...")

        # 分析执行日志
        execution_logs = await self.memory.get_execution_logs(limit=50)

        if not execution_logs:
            return

        prompt = f"""作为Guardian Daemon，请分析执行日志，优化执行策略。

执行日志摘要:
{json.dumps(execution_logs[:20], ensure_ascii=False, indent=2)[:2000]}

请提出优化建议。
返回JSON:
{{
    "optimizations": ["优化点1", "优化点2"],
    "reasoning": "理由"
}}"""

        try:
            response = await self.llm.chat(prompt)

            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            data = json.loads(response.strip())

            logger.info(f"Self-optimization: {data.get('optimizations', [])}")

            # 可以将优化建议应用到配置中

        except Exception as e:
            logger.error(f"Self-optimization failed: {e}")

    def get_stats(self) -> dict[str, Any]:
        """获取守护进程统计"""
        return {
            "running": self._running,
            "tasks_completed": self.stats.tasks_completed,
            "total_evolutions": self.stats.total_evolutions,
            "errors_learned_from": self.stats.errors_learned_from,
            "experiences_extracted": self.stats.experiences_extracted,
            "capabilities": self._capabilities,
            "evolution_goals": self._evolution_goals,
        }
