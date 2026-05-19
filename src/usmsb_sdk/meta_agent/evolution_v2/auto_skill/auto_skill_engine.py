"""
AutoSkillEngine

Skill 自创建引擎 - 完整闭环

缺口发现 → 方案研究 → 创建 → 验证 → 持久化 → Curator 清理
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .skill_creator import SkillCreator, LLMAssistedSkillCreator
from .skill_discovery import SkillDiscovery, PrioritizedSkillDiscovery, SkillGap
from .skill_validator import SkillValidator, ValidationResult
from .skill_curator import SkillCurator

logger = logging.getLogger(__name__)


@dataclass
class AutoSkillEngineConfig:
    """AutoSkillEngine 配置"""
    max_skills_per_cycle: int = 3
    cycle_interval: int = 3600  # 每小时运行一次
    enable_auto_curation: bool = True
    curation_interval: int = 86400  # 每天清理一次


class AutoSkillEngine:
    """
    自动创建 Skill 引擎

    完整闭环：
    1. 发现缺口
    2. 研究解决方案
    3. 创建 Skill
    4. 验证
    5. 持久化
    6. Curator 清理
    """

    def __init__(
        self,
        causal_graph=None,
        llm_manager=None,
        skill_registry=None,
        curiosity_engine=None,
        task_executor=None,
        config: AutoSkillEngineConfig | None = None,
    ):
        """
        初始化

        Args:
            causal_graph: 因果图
            llm_manager: LLM 管理器
            skill_registry: Skill 注册表
            curiosity_engine: 好奇心引擎
            task_executor: 任务执行器
            config: 配置
        """
        self.config = config or AutoSkillEngineConfig()
        self.graph = causal_graph
        self.llm = llm_manager
        self.registry = skill_registry or {}

        # 组件
        self.skill_creator = LLMAssistedSkillCreator(llm_manager) if llm_manager else SkillCreator(llm_manager)
        self.skill_discovery = PrioritizedSkillDiscovery(
            causal_graph, curiosity_engine, task_executor, self.registry
        )
        self.skill_validator = SkillValidator(causal_graph, llm_manager)
        self.skill_curator = SkillCurator(self.registry, causal_graph)

        # 运行状态
        self._running = False
        self._task = None

    async def run_loop(self) -> None:
        """
        自动创建循环
        """
        self._running = True

        while self._running:
            try:
                # 1. 发现缺口
                gaps = await self.skill_discovery.discover_gaps()

                # 按优先级排序
                gaps.sort(key=lambda g: g.priority, reverse=True)

                # 2. 处理每个缺口
                for gap in gaps[: self.config.max_skills_per_cycle]:
                    try:
                        result = await self._process_gap(gap)
                        if result:
                            logger.info(f"Created skill for gap {gap.gap_id}: {result}")
                    except Exception as e:
                        logger.error(f"Failed to process gap {gap.gap_id}: {e}")

                # 3. Curator 定期清理
                if self.config.enable_auto_curation:
                    await self.skill_curator.run_curation()

            except Exception as e:
                logger.error(f"AutoSkillEngine error: {e}")

            # 等待下一个周期
            await asyncio.sleep(self.config.cycle_interval)

    async def _process_gap(self, gap: SkillGap) -> str | None:
        """
        处理单个缺口

        Args:
            gap: Skill 缺口

        Returns:
            创建的 skill_id
        """
        # 2. 研究解决方案
        solution = await self._research_solution(gap)

        if not solution:
            return None

        # 3. 创建 Skill
        creation_result = await self.skill_creator.create_from_analysis(solution)

        # 4. 验证
        validation_result = await self.skill_validator.validate(
            creation_result, solution.get("test_cases", [])
        )

        if validation_result.passed:
            # 5. 持久化（已由 creator 处理）
            logger.info(
                f"Skill {creation_result.skill_id} created and validated "
                f"(quality: {validation_result.quality_score:.2f})"
            )

            # 更新注册表
            self._register_skill(creation_result, solution)

            # 更新因果图（如果适用）
            if gap.gap_type == "missing_causal_link":
                self._update_causal_graph(gap, creation_result)

            return creation_result.skill_id
        else:
            logger.warning(
                f"Skill validation failed for gap {gap.gap_id}: "
                f"{validation_result.issues}"
            )
            return None

    async def _research_solution(self, gap: SkillGap) -> dict[str, Any] | None:
        """
        研究解决方案

        Args:
            gap: Skill 缺口

        Returns:
            解决方案
        """
        if not self.llm:
            # 没有 LLM，使用默认方案
            return self._default_solution(gap)

        prompt = f"""
        分析以下能力缺口，设计一个 Skill 来解决它。

        缺口：{gap.description}
        类型：{gap.gap_type}
        优先级：{gap.priority}

        请设计：
        1. Skill 的名称和描述
        2. Skill 类型（prompt 或 code）
        3. 实现方案
        4. 触发条件
        5. 测试用例（至少 3 个）
        6. 依赖（如果是 Code Skill）

        输出格式（JSON）：
        {{
            "name": "Skill名称",
            "description": "描述",
            "skill_type": "prompt或code",
            "implementation": "实现内容",
            "triggers": ["触发条件1", "触发条件2"],
            "examples": [
                {{"input": "示例输入", "output": "示例输出"}}
            ],
            "test_cases": [
                {{"input": "输入", "output": "预期输出"}}
            ],
            "dependencies": ["依赖1", "依赖2"]
        }}
        """

        try:
            response = await self.llm.analyze(prompt)
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"Failed to research solution: {e}")
            return None

    def _default_solution(self, gap: SkillGap) -> dict[str, Any]:
        """生成默认方案"""
        return {
            "name": f"AutoGenerated_{gap.gap_id}",
            "description": gap.description,
            "skill_type": "prompt",
            "implementation": f"处理 {gap.target_node} 任务的默认 Prompt",
            "triggers": [gap.source_node, gap.target_node],
            "examples": [{"input": "示例", "output": "结果"}],
            "test_cases": [],
        }

    def _register_skill(
        self,
        creation_result,
        solution: dict[str, Any],
    ) -> None:
        """注册 Skill"""
        from .skill_creator import SkillCreationResult

        skill_info = {
            "skill_id": creation_result.skill_id,
            "name": solution.get("name", ""),
            "description": solution.get("description", ""),
            "type": creation_result.skill_type,
            "path": creation_result.path,
            "quality_score": creation_result.quality_score,
            "is_active": True,
        }

        self.registry[creation_result.skill_id] = skill_info

    def _update_causal_graph(
        self,
        gap: SkillGap,
        creation_result,
    ) -> None:
        """更新因果图"""
        if not self.graph:
            return

        # 标记该因果边已被 skill 覆盖
        # 实际实现可能需要更复杂的逻辑

    def start(self) -> None:
        """启动引擎"""
        self._running = True
        self._task = asyncio.create_task(self.run_loop())
        logger.info("AutoSkillEngine started")

    async def stop(self) -> None:
        """停止引擎"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AutoSkillEngine stopped")

    # ==================== 触发接口 ====================

    async def on_task_failed(
        self,
        task: Any,
        error: Exception,
    ) -> None:
        """
        任务失败触发

        Args:
            task: 失败的任务
            error: 错误
        """
        gap = SkillGap(
            gap_id=f"failure_{getattr(task, 'task_id', 'unknown')}",
            source_node=getattr(task, "task_type", "unknown"),
            target_node="unknown",
            gap_type="missing_capability",
            priority=1.0,
            description=f"任务执行失败: {str(error)}",
        )

        await self._process_gap(gap)

    async def on_high_frequency(
        self,
        task_type: str,
        count: int,
    ) -> None:
        """
        高频任务触发

        Args:
            task_type: 任务类型
            count: 执行次数
        """
        if count >= 3:
            gap = SkillGap(
                gap_id=f"high_freq_{task_type}",
                source_node=task_type,
                target_node="optimization",
                gap_type="missing_capability",
                priority=0.7,
                description=f"高频任务 {task_type} 需要优化",
            )

            await self._process_gap(gap)

    async def trigger_manual(
        self,
        gap_description: str,
    ) -> str | None:
        """
        手动触发

        Args:
            gap_description: 缺口描述

        Returns:
            创建的 skill_id
        """
        gap = SkillGap(
            gap_id=f"manual_{id(gap_description)}",
            source_node="manual",
            target_node="manual",
            gap_type="missing_capability",
            priority=0.8,
            description=gap_description,
        )

        return await self._process_gap(gap)
