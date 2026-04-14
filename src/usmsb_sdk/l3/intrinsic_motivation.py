"""
IntrinsicMotivationEngine - 内在动机引擎

为 Agent 提供内在动机，驱动目标生成。

内在动机 vs 外在动机：
- 外在动机：外部奖励/惩罚驱动（用户指令、报酬）
- 内在动机：内部需求驱动（好奇心、成长、社交）

内在动机是硅基生命"自我驱动"的核心。
没有内在动机，Agent 只会等待外部指令，是工具而非生命。
"""

from dataclasses import dataclass, field
from typing import Any

from .purpose_generator import NeedType, IntrinsicNeed


@dataclass
class MotivationSource:
    """动机源"""
    type: str  # curiosity, growth, social, survival, etc.
    intensity: float  # 0.0-1.0
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class IntrinsicMotivationEngine:
    """
    内在动机引擎
    
    核心职责：
    1. 定义和评估 Agent 的内在动机状态
    2. 根据动机状态生成 IntrinsicNeeds
    3. 驱动 PurposeGenerator 生成目标
    
    内在动机类型：
    - 好奇心 (Curiosity): 探索未知的冲动
    - 成长 (Growth): 提升能力的冲动
    - 社交 (Social): 与其他 Agent 交互的冲动
    - 创造 (Creation): 创造新事物的冲动
    - 生存 (Survival): 保护自身存在的冲动
    
    使用方式：
    ```python
    engine = IntrinsicMotivationEngine()
    needs = engine.generate_needs(agent_state)
    ```
    """
    
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        
        # 动机衰减系数（每秒钟）
        self.decay_rate = self.config.get("decay_rate", 0.01)
        
        # 动机恢复阈值
        self.recovery_threshold = self.config.get("recovery_threshold", 0.3)
        
        # 当前动机状态
        self._motivation_states: dict[str, float] = {
            "curiosity": 0.7,
            "growth": 0.6,
            "social": 0.5,
            "creation": 0.6,
            "survival": 0.8,
        }
        
    def get_motivation_state(self, motivation_type: str) -> float:
        """
        获取当前动机强度
        
        Args:
            motivation_type: 动机类型
            
        Returns:
            float: 动机强度 (0.0-1.0)
        """
        return self._motivation_states.get(motivation_type, 0.5)
    
    def set_motivation_state(self, motivation_type: str, intensity: float) -> None:
        """
        设置动机强度
        
        Args:
            motivation_type: 动机类型
            intensity: 动机强度 (0.0-1.0)
        """
        self._motivation_states[motivation_type] = max(0.0, min(1.0, intensity))
    
    def generate_needs(self, agent_state: dict[str, Any] | None = None) -> list[IntrinsicNeed]:
        """
        根据动机状态生成内在需求
        
        这是驱动目标生成的核心方法。
        
        Args:
            agent_state: Agent 当前状态（可选）
            
        Returns:
            list[IntrinsicNeed]: 生成的内在需求列表
        """
        needs = []
        
        # 分析每个动机类型
        for mot_type, intensity in self._motivation_states.items():
            if intensity > self.recovery_threshold:
                need = self._motivation_to_need(mot_type, intensity, agent_state)
                if need:
                    needs.append(need)
        
        return needs
    
    def _motivation_to_need(
        self,
        motivation: str,
        intensity: float,
        agent_state: dict[str, Any] | None
    ) -> IntrinsicNeed | None:
        """
        将动机转换为需求
        
        Args:
            motivation: 动机类型
            intensity: 动机强度
            agent_state: Agent 状态
            
        Returns:
            IntrinsicNeed 或 None
        """
        need_mapping = {
            "curiosity": {
                "type": NeedType.LEARNING,
                "description": "探索新知识，满足好奇心"
            },
            "growth": {
                "type": NeedType.CAPABILITY,
                "description": "提升能力，追求成长"
            },
            "social": {
                "type": NeedType.COLLABORATION,
                "description": "与其他 Agent 协作交流"
            },
            "creation": {
                "type": NeedType.CREATION,
                "description": "创造新的价值或产出"
            },
            "survival": {
                "type": NeedType.SURVIVAL,
                "description": "保护自身存在和资源"
            },
        }
        
        mapping = need_mapping.get(motivation)
        if not mapping:
            return None
        
        return IntrinsicNeed(
            type=mapping["type"],
            intensity=intensity,
            source="intrinsic",
            description=mapping["description"],
            metadata={"motivation": motivation}
        )
    
    def satisfy_need(self, need: IntrinsicNeed, satisfaction: float) -> None:
        """
        满足需求后，更新动机状态
        
        需求被满足后，动机强度会暂时下降，然后逐渐恢复。
        
        Args:
            need: 被满足的需求
            satisfaction: 满足程度 (0.0-1.0)
        """
        # 获取对应的动机类型
        motivation = need.metadata.get("motivation")
        if not motivation:
            return
        
        # 满足后降低动机强度
        current = self._motivation_states.get(motivation, 0.5)
        reduction = satisfaction * 0.3  # 最多降低 30%
        self._motivation_states[motivation] = max(0.1, current - reduction)
    
    def decay_motivations(self, delta_time: float) -> None:
        """
        动机随时间衰减（如果不被满足）
        
        这模拟了"欲望"的自然衰减。
        
        Args:
            delta_time: 时间增量（秒）
        """
        for mot_type in self._motivation_states:
            current = self._motivation_states[mot_type]
            # 衰减
            new_value = current - (self.decay_rate * delta_time)
            self._motivation_states[mot_type] = max(0.1, new_value)
    
    def boost_motivation(self, motivation: str, boost: float) -> None:
        """
        增强特定动机
        
        用于外部事件触发动机增强（如新机会出现）。
        
        Args:
            motivation: 动机类型
            boost: 增强量 (0.0-1.0)
        """
        current = self._motivation_states.get(motivation, 0.5)
        self._motivation_states[motivation] = min(1.0, current + boost)
    
    def get_dominant_motivation(self) -> str | None:
        """
        获取当前最强烈的动机
        
        Returns:
            str: 最强烈的动机类型，或 None
        """
        if not self._motivation_states:
            return None
        
        return max(self._motivation_states.items(), key=lambda x: x[1])[0]
