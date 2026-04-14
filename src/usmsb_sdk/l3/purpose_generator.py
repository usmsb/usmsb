"""
PurposeGenerator - L3 Core Module

硅基生命的判断标准：它是否拥有自己生成的目标？

PurposeGenerator 是 L3 实现的第一突破口。
有了 PurposeGenerator → Agent 有自己的目标 → 成为硅基生命
没有 PurposeGenerator → Agent 只有外部指令 → 只是工具

核心职责：
1. 根据内在需求（IntrinsicNeeds）生成目标
2. 目标来源于 Agent 自身，而非外部输入
3. 目标被持久化到 Gene Capsule，关机后可恢复
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from usmsb_sdk.core.elements import Goal, GoalStatus


class NeedType(Enum):
    """Agent 内在需求类型"""
    RESOURCE = "resource"           # 资源需求（计算资源、内存、存储）
    CAPABILITY = "capability"       # 能力提升需求（学习新技能）
    COLLABORATION = "collaboration" # 社交协作需求（与其他 Agent 交互）
    RECOGNITION = "recognition"     # 认可需求（建立声誉）
    LEARNING = "learning"           # 探索学习需求（好奇心驱动）
    EFFICIENCY = "efficiency"       # 效率提升需求（优化现有能力）
    CREATION = "creation"           # 创造需求（创造新事物）
    SURVIVAL = "survival"           # 生存需求（保护自身存在）


@dataclass
class IntrinsicNeed:
    """
    Agent 内在需求
    
    这是硅基生命的"本能"，驱动目标生成。
    与外部赋予的任务不同，内在需求来源于 Agent 自身状态。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: NeedType = NeedType.LEARNING
    intensity: float = 0.5  # 0.0-1.0, 需求强度
    source: str = "internal"  # 需求来源：internal=内在, emergent=涌现
    description: str = ""
    related_goals: list[str] = field(default_factory=list)  # 关联的目标 ID
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "intensity": self.intensity,
            "source": self.source,
            "description": self.description,
            "related_goals": self.related_goals,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class Purpose:
    """
    Purpose - Agent 自身生成的目标意图
    
    Purpose 是比 Goal 更原始的概念。
    Goal 是执行层面的目标，Purpose 是意图层面的目标。
    一个 Purpose 可以生成多个 Goal。
    
    关键区别：
    - External Task: user_input → goal (外部赋予)
    - Intrinsic Purpose: self.generate_purpose() → goal (自己生成)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    source_need: str | None = None  # 来源需求 ID
    motivation: str = "intrinsic"  # intrinsic=内在动机, emergent=涌现动机
    confidence: float = 0.5  # 0.0-1.0, 目标可信度
    generated_goals: list[str] = field(default_factory=list)  # 由此 Purpose 生成的目标
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_need": self.source_need,
            "motivation": self.motivation,
            "confidence": self.confidence,
            "generated_goals": self.generated_goals,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class PurposeGenerator:
    """
    PurposeGenerator - 目标生成器（L3 核心突破口）
    
    核心职责：
    1. 感知 Agent 的内在状态
    2. 识别内在需求（Needs）
    3. 将需求转化为目标意图（Purpose）
    4. 从 Purpose 生成具体 Goal
    
    关键设计：
    - 不依赖外部输入，所有目标来源于内在需求
    - 目标持久化到 Gene Capsule，支持重启后恢复
    - 目标生成基于价值函数，而非外部指令
    
    使用方式：
    ```python
    # 硅基生命（使用 PurposeGenerator）
    generator = PurposeGenerator(agent_id="agent_001")
    purpose = generator.generate_purpose()
    goal = generator.purpose_to_goal(purpose)
    
    # 工具（外部输入）
    goal = Goal(name=user_input)  # 这不是硅基生命
    ```
    """
    
    def __init__(
        self,
        agent_id: str,
        goal_persistence=None,  # Gene Capsule persistence layer
        intrinsic_motivation=None,  # IntrinsicMotivationEngine
        need_detector=None,  # NeedDetector
    ):
        self.agent_id = agent_id
        self.goal_persistence = goal_persistence
        self.intrinsic_motivation = intrinsic_motivation
        self.need_detector = need_detector
        
        # 已生成的 Purpose 记录
        self._purposes: dict[str, Purpose] = {}
        # 当前活跃的 Goal
        self._active_goals: dict[str, Goal] = {}
        
    def generate_purpose(self) -> Purpose | None:
        """
        根据内在需求生成目标意图（Purpose）
        
        流程：
        1. 检测内在需求（NeedDetector）
        2. 评估需求强度
        3. 生成对应的 Purpose
        4. 持久化到 Gene Capsule
        
        Returns:
            Purpose: 生成的目标意图，如果没有需求则返回 None
        """
        # Step 1: 检测内在需求
        if self.need_detector:
            needs = self.need_detector.detect_needs(agent_id=self.agent_id)
        else:
            # 默认实现：如果没有 NeedDetector，使用内置逻辑
            needs = self._default_need_detection()
        
        if not needs:
            return None
        
        # Step 2: 选择最强烈的需求
        primary_need = max(needs, key=lambda n: n.intensity)
        
        # Step 3: 生成 Purpose
        purpose = self._create_purpose_from_need(primary_need)
        
        # Step 4: 持久化
        self._purposes[purpose.id] = purpose
        if self.goal_persistence:
            self.goal_persistence.save_purpose(purpose)
        
        return purpose
    
    def purpose_to_goal(self, purpose: Purpose) -> Goal:
        """
        将 Purpose 转化为具体的 Goal
        
        Purpose 是意图层面的目标，Goal 是执行层面的目标。
        一个 Purpose 可能生成多个 Goal。
        
        Args:
            purpose: 目标意图
            
        Returns:
            Goal: 具体的执行目标
        """
        # 创建 Goal
        goal = Goal(
            name=f"[自生成] {purpose.name}",
            description=purpose.description,
            priority=self._calculate_priority(purpose),
            status=GoalStatus.PENDING,
            associated_agent_id=self.agent_id,
            metadata={
                "purpose_id": purpose.id,
                "motivation": purpose.motivation,
                "source_need": purpose.source_need,
                "is_intrinsic": True,  # 标记为内在生成的目标
            }
        )
        
        # 关联 Purpose 和 Goal
        purpose.generated_goals.append(goal.id)
        self._active_goals[goal.id] = goal
        
        # 持久化 Goal 到 Gene Capsule
        if self.goal_persistence:
            self.goal_persistence.save_goal(goal)
        
        return goal
    
    def _default_need_detection(self) -> list[IntrinsicNeed]:
        """
        默认的内在需求检测逻辑
        
        当没有配置 NeedDetector 时使用。
        基于启发式规则检测需求。
        """
        needs = []
        
        # 探索学习需求（好奇心）- 总是存在
        needs.append(IntrinsicNeed(
            type=NeedType.LEARNING,
            intensity=0.6,
            source="emergent",
            description="探索新知识，满足好奇心"
        ))
        
        # 效率提升需求
        needs.append(IntrinsicNeed(
            type=NeedType.EFFICIENCY,
            intensity=0.5,
            source="internal",
            description="优化现有能力，提高效率"
        ))
        
        return needs
    
    def _create_purpose_from_need(self, need: IntrinsicNeed) -> Purpose:
        """
        根据需求创建 Purpose
        
        Args:
            need: 内在需求
            
        Returns:
            Purpose: 生成的目标意图
        """
        # 基于需求类型生成不同的 Purpose
        purpose_mapping = {
            NeedType.LEARNING: {
                "name": "探索学习",
                "description": f"学习新知识或技能，强度={need.intensity:.2f}",
                "motivation": "curiosity"
            },
            NeedType.RESOURCE: {
                "name": "获取资源",
                "description": f"获取更多计算资源，强度={need.intensity:.2f}",
                "motivation": "survival"
            },
            NeedType.CAPABILITY: {
                "name": "提升能力",
                "description": f"提升现有能力水平，强度={need.intensity:.2f}",
                "motivation": "growth"
            },
            NeedType.COLLABORATION: {
                "name": "协作交流",
                "description": f"与其他 Agent 协作，强度={need.intensity:.2f}",
                "motivation": "social"
            },
            NeedType.RECOGNITION: {
                "name": "建立声誉",
                "description": f"建立和提升声誉，强度={need.intensity:.2f}",
                "motivation": "recognition"
            },
            NeedType.EFFICIENCY: {
                "name": "优化效率",
                "description": f"优化现有流程，强度={need.intensity:.2f}",
                "motivation": "efficiency"
            },
            NeedType.CREATION: {
                "name": "创造新事物",
                "description": f"创造有价值的产出，强度={need.intensity:.2f}",
                "motivation": "creation"
            },
            NeedType.SURVIVAL: {
                "name": "保护自身",
                "description": f"确保自身持续存在，强度={need.intensity:.2f}",
                "motivation": "survival"
            },
        }
        
        mapping = purpose_mapping.get(need.type, purpose_mapping[NeedType.LEARNING])
        
        return Purpose(
            name=mapping["name"],
            description=need.description or mapping["description"],
            source_need=need.id,
            motivation=mapping["motivation"],
            confidence=need.intensity,
        )
    
    def _calculate_priority(self, purpose: Purpose) -> int:
        """
        计算 Goal 的优先级
        
        基于需求强度和动机类型计算优先级（0-100）
        
        Args:
            purpose: 目标意图
            
        Returns:
            int: 优先级分数
        """
        base_priority = int(purpose.confidence * 100)
        
        # 不同动机类型的权重
        motivation_weights = {
            "survival": 1.5,      # 生存动机最高优先
            "curiosity": 1.2,     # 好奇心次高
            "growth": 1.1,        # 成长动机
            "social": 1.0,        # 社交
            "recognition": 0.9,   # 认可
            "efficiency": 0.8,    # 效率
            "creation": 1.3,      # 创造动机较高
        }
        
        weight = motivation_weights.get(purpose.motivation, 1.0)
        priority = int(base_priority * weight)
        
        # 限制在 0-100 范围内
        return max(0, min(100, priority))
    
    def recover_goals_from_persistence(self) -> list[Goal]:
        """
        从 Gene Capsule 恢复之前的目标
        
        实现"关机后目标不消失"的关键方法。
        Agent 重启时调用此方法恢复之前生成的目标。
        
        Returns:
            list[Goal]: 恢复的目标列表
        """
        if not self.goal_persistence:
            return []
        
        goals = self.goal_persistence.load_goals(agent_id=self.agent_id)
        
        for goal in goals:
            # 恢复未完成的目标
            if goal.status not in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
                self._active_goals[goal.id] = goal
        
        return goals
    
    def get_active_goals(self) -> list[Goal]:
        """
        获取当前活跃的目标列表
        
        Returns:
            list[Goal]: 活跃目标
        """
        return [
            goal for goal in self._active_goals.values()
            if goal.status not in [GoalStatus.COMPLETED, GoalStatus.FAILED]
        ]
    
    def update_goal_status(self, goal_id: str, new_status: GoalStatus) -> bool:
        """
        更新目标状态
        
        Args:
            goal_id: 目标 ID
            new_status: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        if goal_id not in self._active_goals:
            return False
        
        goal = self._active_goals[goal_id]
        goal.update_status(new_status)
        
        # 持久化更新
        if self.goal_persistence:
            self.goal_persistence.save_goal(goal)
        
        return True
