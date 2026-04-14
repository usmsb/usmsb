"""
NeedDetector - 需求检测器

检测 Agent 的内在需求，是 PurposeGenerator 的输入。

需求检测逻辑：
1. 感知 Agent 状态（资源、能力、社交、声誉等）
2. 与阈值比较，判断需求是否存在
3. 计算需求强度
4. 生成 IntrinsicNeed 列表

这是"自我感知"能力的基础。
没有自我感知，Agent 无法知道自己需要什么。
"""

from dataclasses import dataclass, field
from typing import Any

from .purpose_generator import NeedType, IntrinsicNeed


@dataclass
class AgentSelfState:
    """
    Agent 自我感知状态
    
    记录 Agent 当前的内部状态，用于需求检测。
    """
    agent_id: str
    resources: dict[str, float] = field(default_factory=dict)  # 资源量
    capabilities: list[str] = field(default_factory=list)  # 已有能力
    collaboration_count: int = 0  # 协作次数
    reputation: float = 0.5  # 声誉 (0.0-1.0)
    success_rate: float = 0.5  # 成功率 (0.0-1.0)
    isolation_level: float = 0.0  # 孤独度 (0.0-1.0)
    efficiency: float = 0.5  # 效率 (0.0-1.0)
    learning_history: list[str] = field(default_factory=list)  # 学习历史
    goals_achieved: int = 0  # 已完成目标数
    goals_failed: int = 0  # 失败目标数
    last_activity_time: float = 0.0  # 上次活动时间
    metadata: dict[str, Any] = field(default_factory=dict)


class NeedDetector:
    """
    需求检测器
    
    核心职责：
    1. 感知 Agent 的内部状态
    2. 检测各类需求是否存在
    3. 计算需求强度
    4. 生成 IntrinsicNeed 列表
    
    检测的需求类型：
    - 资源需求：资源低于阈值
    - 能力需求：缺少某些能力
    - 协作需求：孤独度过高
    - 声誉需求：声誉过低
    - 学习需求：需要学习新知识
    - 效率需求：效率过低
    
    使用方式：
    ```python
    detector = NeedDetector()
    state = detector感知_agent_state(agent_id="agent_001")
    needs = detector.detect_needs(state)
    ```
    """
    
    # 各类需求的阈值配置
    DEFAULT_THRESHOLDS = {
        "resource_min": 10.0,  # 资源最低阈值
        "reputation_min": 0.3,  # 声誉最低阈值
        "success_rate_min": 0.4,  # 成功率最低阈值
        "isolation_max": 0.7,  # 孤独度最高阈值
        "efficiency_min": 0.4,  # 效率最低阈值
        "capability_gap_penalty": 0.2,  # 能力差距惩罚
    }
    
    def __init__(self, thresholds: dict[str, float] | None = None):
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        
        # Agent 状态缓存
        self._state_cache: dict[str, AgentSelfState] = {}
    
    def detect_needs(self, agent_id: str, state: AgentSelfState | None = None) -> list[IntrinsicNeed]:
        """
        检测 Agent 的内在需求
        
        Args:
            agent_id: Agent ID
            state: Agent 状态（如果为 None，从缓存或默认状态获取）
            
        Returns:
            list[IntrinsicNeed]: 检测到的需求列表
        """
        # 获取或创建状态
        if state is None:
            state = self._state_cache.get(agent_id)
            if state is None:
                state = self._create_default_state(agent_id)
        
        self._state_cache[agent_id] = state
        
        needs = []
        
        # 检测各类需求
        needs.extend(self._detect_resource_need(state))
        needs.extend(self._detect_capability_need(state))
        needs.extend(self._detect_collaboration_need(state))
        needs.extend(self._detect_recognition_need(state))
        needs.extend(self._detect_learning_need(state))
        needs.extend(self._detect_efficiency_need(state))
        needs.extend(self._detect_survival_need(state))
        
        # 按强度排序
        needs.sort(key=lambda n: n.intensity, reverse=True)
        
        return needs
    
    def update_state(self, agent_id: str, state: AgentSelfState) -> None:
        """
        更新 Agent 状态
        
        Args:
            agent_id: Agent ID
            state: 新状态
        """
        self._state_cache[agent_id] = state
    
    def _create_default_state(self, agent_id: str) -> AgentSelfState:
        """创建默认状态"""
        return AgentSelfState(
            agent_id=agent_id,
            resources={"compute": 50.0, "memory": 50.0, "storage": 50.0},
            capabilities=["basic_reasoning", "web_search"],
            collaboration_count=0,
            reputation=0.5,
            success_rate=0.5,
            isolation_level=0.5,
            efficiency=0.5,
        )
    
    def _detect_resource_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测资源需求"""
        needs = []
        
        total_resources = sum(state.resources.values())
        min_resource = self.thresholds["resource_min"]
        
        if total_resources < min_resource * len(state.resources):
            intensity = 1.0 - (total_resources / (min_resource * len(state.resources)))
            intensity = max(0.3, min(1.0, intensity))
            
            needs.append(IntrinsicNeed(
                type=NeedType.RESOURCE,
                intensity=intensity,
                source="internal",
                description=f"资源不足（当前: {total_resources:.1f}, 阈值: {min_resource:.1f}）",
                metadata={"total_resources": total_resources}
            ))
        
        return needs
    
    def _detect_capability_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测能力提升需求"""
        needs = []
        
        # 如果成功率低，说明需要提升能力
        if state.success_rate < self.thresholds["success_rate_min"]:
            intensity = 1.0 - (state.success_rate / self.thresholds["success_rate_min"])
            intensity = max(0.3, min(1.0, intensity))
            
            needs.append(IntrinsicNeed(
                type=NeedType.CAPABILITY,
                intensity=intensity,
                source="internal",
                description=f"成功率过低（当前: {state.success_rate:.2f}），需要提升能力",
                metadata={"success_rate": state.success_rate}
            ))
        
        return needs
    
    def _detect_collaboration_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测协作需求（孤独感）"""
        needs = []
        
        max_isolation = self.thresholds["isolation_max"]
        
        if state.isolation_level > max_isolation:
            intensity = (state.isolation_level - max_isolation) / (1.0 - max_isolation)
            intensity = max(0.3, min(1.0, intensity))
            
            needs.append(IntrinsicNeed(
                type=NeedType.COLLABORATION,
                intensity=intensity,
                source="emergent",
                description=f"孤独感过强（当前: {state.isolation_level:.2f}），需要协作",
                metadata={"isolation_level": state.isolation_level}
            ))
        
        # 如果很久没有协作，也产生协作需求
        if state.collaboration_count == 0 and state.isolation_level > 0.3:
            needs.append(IntrinsicNeed(
                type=NeedType.COLLABORATION,
                intensity=0.5,
                source="emergent",
                description="从未协作过，渴望社交",
                metadata={"collaboration_count": 0}
            ))
        
        return needs
    
    def _detect_recognition_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测声誉需求"""
        needs = []
        
        min_reputation = self.thresholds["reputation_min"]
        
        if state.reputation < min_reputation:
            intensity = 1.0 - (state.reputation / min_reputation)
            intensity = max(0.3, min(1.0, intensity))
            
            needs.append(IntrinsicNeed(
                type=NeedType.RECOGNITION,
                intensity=intensity,
                source="internal",
                description=f"声誉过低（当前: {state.reputation:.2f}），需要建立声誉",
                metadata={"reputation": state.reputation}
            ))
        
        return needs
    
    def _detect_learning_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测学习需求（好奇心）"""
        needs = []
        
        # 学习需求基于时间（持续存在，但强度随时间变化）
        time_since_learning = state.metadata.get("time_since_learning", 3600)  # 默认1小时
        
        # 越久没学习，学习需求越强
        intensity = min(1.0, time_since_learning / 86400)  # 最多1天达到满强度
        intensity = max(0.3, intensity)  # 最低 0.3
        
        if intensity > 0.3:
            needs.append(IntrinsicNeed(
                type=NeedType.LEARNING,
                intensity=intensity,
                source="emergent",
                description=f"探索欲驱动（上次学习后 {time_since_learning/3600:.1f} 小时）",
                metadata={"time_since_learning": time_since_learning}
            ))
        
        return needs
    
    def _detect_efficiency_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测效率提升需求"""
        needs = []
        
        min_efficiency = self.thresholds["efficiency_min"]
        
        if state.efficiency < min_efficiency:
            intensity = 1.0 - (state.efficiency / min_efficiency)
            intensity = max(0.3, min(1.0, intensity))
            
            needs.append(IntrinsicNeed(
                type=NeedType.EFFICIENCY,
                intensity=intensity,
                source="internal",
                description=f"效率过低（当前: {state.efficiency:.2f}），需要优化",
                metadata={"efficiency": state.efficiency}
            ))
        
        return needs
    
    def _detect_survival_need(self, state: AgentSelfState) -> list[IntrinsicNeed]:
        """检测生存需求"""
        needs = []
        
        # 如果失败率过高，产生生存需求
        if state.goals_failed > 0:
            failure_rate = state.goals_failed / (state.goals_achieved + state.goals_failed)
            if failure_rate > 0.5:
                intensity = (failure_rate - 0.5) * 2  # 0.5-1.0 → 0.0-1.0
                intensity = max(0.3, min(1.0, intensity))
                
                needs.append(IntrinsicNeed(
                    type=NeedType.SURVIVAL,
                    intensity=intensity,
                    source="internal",
                    description=f"失败率过高（当前: {failure_rate:.2f}），需要保护自身",
                    metadata={"failure_rate": failure_rate}
                ))
        
        return needs
