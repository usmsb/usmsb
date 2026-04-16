"""
Base Skill Loader
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from ..types import SkillMetadata, SkillTier

logger = logging.getLogger(__name__)


class BaseSkillLoader(ABC):
    """Skill 加载器基类"""

    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self._impl: Any = None

    @property
    def tier(self) -> SkillTier:
        return self.metadata.tier

    @abstractmethod
    async def load(self, config: dict) -> None:
        """加载 Skill 实现"""
        pass

    @abstractmethod
    async def call(self, input_data: dict) -> Any:
        """调用 Skill"""
        pass

    @abstractmethod
    def supports_internal(self) -> bool:
        """是否有内部实现"""
        pass

    @abstractmethod
    def supports_sdk(self) -> bool:
        """是否有 SDK 实现"""
        pass


class L2SkillLoader(BaseSkillLoader):
    """L2 工具性 Skill 加载器"""

    async def load(self, config: dict) -> None:
        # 加载内部实现
        from ...l2.agent import L2Agent
        self._impl = L2Agent(config= config.get("l2_config", {}))

    async def call(self, input_data: dict) -> Any:
        return await self._impl.run(input_data.get("input", ""), input_data.get("context", {}))

    def supports_internal(self) -> bool:
        return True  # 有内部实现

    def supports_sdk(self) -> bool:
        return True  # SDK 就是 L2Agent


class L3SkillLoader(BaseSkillLoader):
    """L3 目标生成 Skill 加载器"""

    async def load(self, config: dict) -> None:
        from ...l3.purpose_generator import PurposeGenerator
        self._impl = PurposeGenerator()

    async def call(self, input_data: dict) -> Any:
        return await self._impl.generate_goal(input_data.get("context", {}))

    def supports_internal(self) -> bool:
        # 检查 MetaAgent 内部是否有 goals/engine
        try:
            from ...meta_agent.goals.engine import GoalEngine
            return True
        except ImportError:
            return False

    def supports_sdk(self) -> bool:
        return True  # SDK 就是 PurposeGenerator


class L4SkillLoader(BaseSkillLoader):
    """L4 自我意识 Skill 加载器"""

    async def load(self, config: dict) -> None:
        from ...l4.l4_agent import L4Agent
        self._impl = L4Agent()

    async def call(self, input_data: dict) -> Any:
        action = input_data.get("action", "self_model")
        if action == "self_model":
            return await self._impl.build_self_model(input_data.get("experience", []))
        elif action == "metacognize":
            return await self._impl.metacognize(input_data.get("thought", ""))
        elif action == "infer_mind":
            return await self._impl.infer_mind(
                input_data.get("other_agent_id", ""),
                input_data.get("history", [])
            )
        elif action == "feel":
            return await self._impl.feel(input_data.get("stimulus", {}))
        else:
            raise ValueError(f"Unknown L4 action: {action}")

    def supports_internal(self) -> bool:
        return False

    def supports_sdk(self) -> bool:
        return True


class L5SkillLoader(BaseSkillLoader):
    """L5 集体智能 Skill 加载器"""

    async def load(self, config: dict) -> None:
        from ...l5.l5_collective import L5Collective
        self._impl = L5Collective()

    async def call(self, input_data: dict) -> Any:
        return await self._impl.think_collectively(
            input_data.get("task", ""),
            input_data.get("agents", [])
        )

    def supports_internal(self) -> bool:
        return False

    def supports_sdk(self) -> bool:
        return True


def create_skill_loader(metadata: SkillMetadata) -> BaseSkillLoader:
    """工厂方法：根据 tier 创建 SkillLoader"""
    loaders = {
        SkillTier.L2: L2SkillLoader,
        SkillTier.L3: L3SkillLoader,
        SkillTier.L4: L4SkillLoader,
        SkillTier.L5: L5SkillLoader,
    }
    loader_cls = loaders.get(metadata.tier)
    if not loader_cls:
        raise ValueError(f"Unknown Skill tier: {metadata.tier}")
    return loader_cls(metadata)
