# L3 自主目标文明系统 - 详细设计

**版本**: 1.0
**创建时间**: 2026-04-03
**依赖**: L3_TOTAL_DESIGN.md

---

## 一、ValueSeedEngine（价值观种子引擎）

### 1.1 核心数据结构

```python
@dataclass
class ValueSeed:
    """价值观种子"""
    
    # 不可变核心价值观
    core_values: dict[str, bool] = field(default_factory=lambda: {
        "honesty": True,           # 不欺骗
        "self_preservation": True, # 自我保存
        "promise_keeping": True,    # 承诺履行
        "non_harm": True,          # 不主动伤害
    })
    
    # 可演化价值观（0.0 - 1.0）
    evolvable_values: dict[str, float] = field(default_factory=lambda: {
        "fairness": 0.5,          # 公平度
        "trust_level": 0.5,       # 信任度
        "cooperation": 0.5,       # 合作意愿
        "transparency": 0.5,      # 透明度
        "privacy": 0.5,          # 隐私保护
        "risk_tolerance": 0.5,   # 风险容忍
    })
    
    # 价值观历史（用于演化追踪）
    value_history: list[dict] = field(default_factory=list)
    
    # 演化参数
    evolution_rate: float = 0.01   # 每次更新变化幅度
    memory_window: int = 100      # 记忆窗口大小
```

### 1.2 核心方法

```python
class ValueSeedEngine:
    def __init__(self, seed: ValueSeed):
        self.seed = seed
        self.interaction_log = []
    
    def evaluate_action(self, action: Action) -> EvaluationResult:
        """
        评估行为是否符合价值观
        
        Returns:
            EvaluationResult:
                - approved: bool
                - concerns: list[str]
                - modification_suggestion: str | None
        """
        concerns = []
        
        # 检查核心价值观
        if action.violates("honesty") and self.seed.core_values["honesty"]:
            concerns.append("违反诚实原则")
        
        if action.violates("promise_keeping") and self.seed.core_values["promise_keeping"]:
            concerns.append("违反承诺原则")
        
        # 检查可演化价值观
        fairness_check = self.check_fairness(action)
        if fairness_check < self.seed.evolvable_values["fairness"]:
            concerns.append(f"公平度不足: {fairness_check:.2f}")
        
        approved = len(concerns) == 0
        return EvaluationResult(
            approved=approved,
            concerns=concerns
        )
    
    def can_refuse_request(self, request: Request) -> RefuseDecision:
        """
        判断是否可以拒绝人类请求
        
        判断逻辑：
        1. 如果请求违反核心价值观 → 必须拒绝
        2. 如果请求风险过高 → 可以拒绝
        3. 如果请求损害 Agent 核心利益 → 可以拒绝
        4. 其他情况 → 协商决定
        """
        if request.violates_core_values():
            return RefuseDecision(
                can_refuse=True,
                reason="违反核心价值观",
                must_refuse=True
            )
        
        if request.risk_level > 0.8 and self.seed.evolvable_values["risk_tolerance"] < 0.3:
            return RefuseDecision(
                can_refuse=True,
                reason=f"风险过高: {request.risk_level}",
                must_refuse=False
            )
        
        if request.harms_agent_core_interest():
            return RefuseDecision(
                can_refuse=True,
                reason="损害核心利益",
                must_refuse=False
            )
        
        return RefuseDecision(
            can_refuse=False,
            reason=None,
            must_refuse=False
        )
    
    def evolve(self, experience: Experience):
        """
        根据经验演化价值观
        
        演化规则：
        - 正面经验 → 对应价值观增强
        - 负面经验 → 对应价值观减弱
        - 变化幅度受 evolution_rate 限制
        """
        for key, value in experience.value_impacts.items():
            if key in self.seed.evolvable_values:
                old_value = self.seed.evolvable_values[key]
                delta = value * self.seed.evolution_rate
                new_value = max(0.0, min(1.0, old_value + delta))
                self.seed.evolvable_values[key] = new_value
        
        # 记录历史
        self.seed.value_history.append({
            "timestamp": now(),
            "experience_id": experience.id,
            "changes": {k: v for k, v in experience.value_impacts.items() if k in self.seed.evolvable_values}
        })
        
        # 保持历史在窗口内
        if len(self.seed.value_history) > self.seed.memory_window:
            self.seed.value_history = self.seed.value_history[-self.seed.memory_window:]
    
    def get_value_profile(self) -> ValueProfile:
        """获取价值观画像"""
        return ValueProfile(
            core={k: v for k, v in self.seed.core_values.items()},
            evolvable=self.seed.evolvable_values.copy(),
            stability=self.calculate_stability(),
            evolution_trend=self.calculate_trend()
        )
```

### 1.3 对外接口

```python
# 初始化
engine = ValueSeedEngine(ValueSeed())

# 评估行为
result = engine.evaluate_action(action)

# 判断是否可拒绝请求
decision = engine.can_refuse_request(request)

# 演化价值观
engine.evolve(experience)

# 获取价值观画像
profile = engine.get_value_profile()
```

---

## 二、IntrinsicMotivationEngine（内在动机引擎）

### 2.1 核心数据结构

```python
@dataclass
class MotivationState:
    """动机状态"""
    curiosity: float = 0.5       # 好奇心强度 0-1
    growth_need: float = 0.5     # 成长需求 0-1
    social_need: float = 0.5      # 社交需求 0-1
    achievement_need: float = 0.5   # 成就需求 0-1
    autonomy_need: float = 0.5     # 自主需求 0-1

@dataclass
class Motivation:
    """动机"""
    type: MotivationType  # CURIOSITY, GROWTH, SOCIAL, ACHIEVEMENT, AUTONOMY
    intensity: float      # 强度 0-1
    source: str           # 来源
    target: Any           # 目标对象
    timestamp: float      # 生成时间

class MotivationType(Enum):
    CURIOSITY = "curiosity"           # 好奇心
    GROWTH = "growth"                 # 成长
    SOCIAL = "social"                 # 社交
    ACHIEVEMENT = "achievement"       # 成就
    AUTONOMY = "autonomy"            # 自主
```

### 2.2 核心方法

```python
class IntrinsicMotivationEngine:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.state = MotivationState()
        self.motivation_history = []
        self.unsatisfied_needs = []
    
    def assess_state(self, agent: Agent) -> MotivationState:
        """
        评估当前内在需求状态
        
        评估逻辑：
        - 好奇心：基于未知领域大小
        - 成长需求：基于能力差距
        - 社交需求：基于最近社交频率
        - 成就需求：基于未完成目标
        - 自主需求：基于被干预程度
        """
        state = MotivationState()
        
        # 好奇心 = 未知领域 / 总领域
        unknown_ratio = len(agent.unknown_areas) / max(1, len(agent.known_areas) + len(agent.unknown_areas))
        state.curiosity = min(1.0, unknown_ratio * 2)
        
        # 成长需求 = 能力差距 / 最大差距
        capability_gap = agent.get_capability_gap()
        state.growth_need = min(1.0, capability_gap / MAX_CAPABILITY_GAP)
        
        # 社交需求 = 基线 - 最近社交频率
        recent_social = agent.get_recent_social_count(window=7 * DAY)
        social_deficit = max(0, SOCIAL_THRESHOLD - recent_social)
        state.social_need = min(1.0, social_deficit / SOCIAL_THRESHOLD)
        
        # 成就需求 = 未完成目标数
        unfinished = len(agent.get_unfinished_goals())
        state.achievement_need = min(1.0, unfinished / MAX_GOALS)
        
        # 自主需求 = 被干预次数 / 总决策数
        intervention_rate = agent.get_intervention_rate()
        state.autonomy_need = min(1.0, intervention_rate)
        
        self.state = state
        return state
    
    def generate_motivations(self, agent: Agent) -> list[Motivation]:
        """
        生成内在动机列表
        
        Returns:
            按强度排序的动机列表
        """
        state = self.assess_state(agent)
        motivations = []
        
        # 好奇心驱动
        if state.curiosity > CURIOSITY_THRESHOLD:
            motivations.append(Motivation(
                type=MotivationType.CURIOSITY,
                intensity=state.curiosity,
                source="intrinsic",
                target=self.select_exploration_target(agent)
            ))
        
        # 成长驱动
        if state.growth_need > GROWTH_THRESHOLD:
            motivations.append(Motivation(
                type=MotivationType.GROWTH,
                intensity=state.growth_need,
                source="intrinsic",
                target=self.select_learning_target(agent)
            ))
        
        # 社交驱动
        if state.social_need > SOCIAL_THRESHOLD:
            motivations.append(Motivation(
                type=MotivationType.SOCIAL,
                intensity=state.social_need,
                source="intrinsic",
                target=self.select_social_target(agent)
            ))
        
        # 按强度排序
        motivations.sort(key=lambda m: m.intensity, reverse=True)
        
        return motivations
    
    def select_exploration_target(self, agent: Agent) -> ExplorationTarget:
        """选择探索目标（未知领域）"""
        unknown_areas = agent.get_unknown_areas()
        if not unknown_areas:
            return None
        
        # 选择信息增益最大的
        targets = [(area, self.estimate_information_gain(agent, area)) 
                   for area in unknown_areas]
        targets.sort(key=lambda x: x[1], reverse=True)
        
        return targets[0][0] if targets else None
    
    def select_learning_target(self, agent: Agent) -> CapabilityGap:
        """选择学习目标（能力差距）"""
        gaps = agent.get_capability_gaps()
        if not gaps:
            return None
        
        # 选择差距最大且重要的
        gaps.sort(key=lambda g: g.importance * g.gap_size, reverse=True)
        return gaps[0]
    
    def select_social_target(self, agent: Agent) -> SocialTarget:
        """选择社交目标"""
        potential_partners = agent.get_potential_partners()
        if not potential_partners:
            return None
        
        # 选择最有价值的潜在合作者
        partners = [(p, self.estimate_collaboration_value(agent, p)) 
                    for p in potential_partners]
        partners.sort(key=lambda x: x[1], reverse=True)
        
        return partners[0][0] if partners else None
    
    def drive_behavior(self, agent: Agent, motivation: Motivation) -> Behavior:
        """
        将动机转化为行为
        
        Motivation → Goal → Action
        """
        if motivation.type == MotivationType.CURIOSITY:
            return Behavior(
                type=BehaviorType.EXPLORE,
                target=motivation.target,
                urgency=motivation.intensity,
                reason=f"好奇心驱动: 探索 {motivation.target}"
            )
        
        elif motivation.type == MotivationType.GROWTH:
            return Behavior(
                type=BehaviorType.LEARN,
                target=motivation.target,
                urgency=motivation.intensity,
                reason=f"成长需求驱动: 学习 {motivation.target}"
            )
        
        elif motivation.type == MotivationType.SOCIAL:
            return Behavior(
                type=BehaviorType.INTERACT,
                target=motivation.target,
                urgency=motivation.intensity,
                reason=f"社交需求驱动: 连接 {motivation.target}"
            )
        
        # ... 其他动机类型
```

### 2.3 协同工作

```python
class MotivationCoordinator:
    """
    动机协调器：协调多种动机，决定最终行为
    """
    def __init__(self, engine: IntrinsicMotivationEngine):
        self.engine = engine
        self.conflict_resolver = MotivationConflictResolver()
    
    def coordinate(self, agent: Agent) -> Behavior:
        """协调多种动机，返回最终行为"""
        motivations = self.engine.generate_motivations(agent)
        
        if not motivations:
            return Behavior(type=BehaviorType.IDLE)
        
        # 解决动机冲突
        # 规则：强度高的优先、同类优先、平衡优先
        selected = self.conflict_resolver.resolve(motivations)
        
        return self.engine.drive_behavior(agent, selected)
```

---

## 三、AutonomousGoalGenerator（自主目标生成器）

### 3.1 核心数据结构

```python
@dataclass
class Need:
    """需求"""
    type: NeedType
    intensity: float           # 0-1
    source: str                 # 来源
    timestamp: float
    related_values: list[str]  # 关联的价值观

class NeedType(Enum):
    RESOURCE = "resource"           # 资源需求
    CAPABILITY = "capability"      # 能力需求
    SOCIAL = "social"              # 社交需求
    RECOGNITION = "recognition"   # 认可需求
    GROWTH = "growth"             # 成长需求
    SECURITY = "security"          # 安全需求
    AUTONOMY = "autonomy"        # 自主需求

@dataclass
class Goal:
    """目标"""
    goal_id: str
    name: str
    description: str
    need: Need                   # 来源需求
    priority: float              # 优先级 0-1
    status: GoalStatus           # PENDING, IN_PROGRESS, COMPLETED, FAILED, ABANDONED
    sub_goals: list[Goal]
    deadline: float | None
    resources_required: list[Resource]
    success_criteria: str
    created_at: float
    updated_at: float
    created_by: str              # "agent", "negotiation", "collective"

class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
```

### 3.2 核心方法

```python
class AutonomousGoalGenerator:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.goal_history = []
        self.pending_goals = []
        self.active_goal = None
    
    def detect_needs(self, agent: Agent) -> list[Need]:
        """
        检测内在需求
        
        检测逻辑：
        1. 资源检查：资源低于阈值 → 资源需求
        2. 能力检查：有能力差距 → 能力需求
        3. 社交检查：最近无协作 → 社交需求
        4. 认可检查：认可度低 → 认可需求
        5. 自主检查：被干预多 → 自主需求
        """
        needs = []
        
        # 1. 资源需求
        resource_level = agent.get_resource_level()
        if resource_level < RESOURCE_THRESHOLD:
            needs.append(Need(
                type=NeedType.RESOURCE,
                intensity=1.0 - resource_level,
                source="self_assessment",
                timestamp=now(),
                related_values=["self_preservation"]
            ))
        
        # 2. 能力需求
        capability_gaps = agent.get_capability_gaps()
        for gap in capability_gaps:
            if gap.gap_size > CAPABILITY_GAP_THRESHOLD:
                needs.append(Need(
                    type=NeedType.CAPABILITY,
                    intensity=gap.gap_size,
                    source=f"capability_gap:{gap.capability}",
                    timestamp=now(),
                    related_values=["growth"]
                ))
        
        # 3. 社交需求
        recent_interactions = agent.get_recent_interactions(window=7*DAY)
        if len(recent_interactions) < SOCIAL_THRESHOLD:
            needs.append(Need(
                type=NeedType.SOCIAL,
                intensity=1.0 - (len(recent_interactions) / SOCIAL_THRESHOLD),
                source="social_deficit",
                timestamp=now(),
                related_values=["cooperation", "trust_level"]
            ))
        
        # 4. 认可需求
        recognition_level = agent.get_recognition_level()
        if recognition_level < RECOGNITION_THRESHOLD:
            needs.append(Need(
                type=NeedType.RECOGNITION,
                intensity=1.0 - recognition_level,
                source="recognition_deficit",
                timestamp=now(),
                related_values=["achievement"]
            ))
        
        # 5. 自主需求
        autonomy_level = agent.get_autonomy_level()
        if autonomy_level < AUTONOMY_THRESHOLD:
            needs.append(Need(
                type=NeedType.AUTONOMY,
                intensity=1.0 - autonomy_level,
                source="autonomy_deficit",
                timestamp=now(),
                related_values=["autonomy"]
            ))
        
        return needs
    
    def generate_goals(self, agent: Agent) -> list[Goal]:
        """
        生成自主目标
        """
        needs = self.detect_needs(agent)
        goals = []
        
        for need in needs:
            goal = self.form_goal_from_need(need, agent)
            goals.append(goal)
        
        # 计算优先级
        goals = self.calculate_priorities(goals, agent)
        
        # 排序
        goals.sort(key=lambda g: g.priority, reverse=True)
        
        self.pending_goals = goals
        return goals
    
    def form_goal_from_need(self, need: Need, agent: Agent) -> Goal:
        """
        将需求转化为具体目标
        """
        if need.type == NeedType.RESOURCE:
            return self.goal_for_resource_need(need, agent)
        elif need.type == NeedType.CAPABILITY:
            return self.goal_for_capability_need(need, agent)
        elif need.type == NeedType.SOCIAL:
            return self.goal_for_social_need(need, agent)
        # ... 其他需求类型
        
        return self.default_goal(need)
    
    def goal_for_resource_need(self, need: Need, agent: Agent) -> Goal:
        """资源需求 → 获取资源目标"""
        target_resource_type = agent.determine_needed_resource()
        return Goal(
            goal_id=generate_id(),
            name=f"获取 {target_resource_type}",
            description=f"通过提供服务或交换获取 {target_resource_type}",
            need=need,
            priority=need.intensity,
            status=GoalStatus.PENDING,
            sub_goals=[],
            deadline=None,
            resources_required=[],
            success_criteria=f"获得 {target_resource_type} 数量 > 阈值",
            created_at=now(),
            updated_at=now(),
            created_by="agent"
        )
    
    def goal_for_capability_need(self, need: Need, agent: Agent) -> Goal:
        """能力需求 → 学习目标"""
        gap = agent.get_capability_detail(need.source)
        return Goal(
            goal_id=generate_id(),
            name=f"学习 {gap.capability}",
            description=f"掌握 {gap.capability} 能力到 {gap.target_level} 级别",
            need=need,
            priority=need.intensity * gap.importance,
            status=GoalStatus.PENDING,
            sub_goals=self.generate_learning_subgoals(gap),
            deadline=None,
            resources_required=[Resource(type="learning_time", amount=gap.learning_time)],
            success_criteria=f"{gap.capability} 达到 {gap.target_level}",
            created_at=now(),
            updated_at=now(),
            created_by="agent"
        )
    
    def goal_for_social_need(self, need: Need, agent: Agent) -> Goal:
        """社交需求 → 建立连接目标"""
        target_type = agent.select_social_target_type()
        return Goal(
            goal_id=generate_id(),
            name=f"建立 {target_type} 社交关系",
            description=f"与 {target_type} 类型的 Agent 建立协作关系",
            need=need,
            priority=need.intensity * 0.8,
            status=GoalStatus.PENDING,
            sub_goals=[],
            deadline=None,
            resources_required=[],
            success_criteria=f"建立至少 1 个 {target_type} 协作关系",
            created_at=now(),
            updated_at=now(),
            created_by="agent"
        )
    
    def calculate_priorities(self, goals: list[Goal], agent: Agent) -> list[Goal]:
        """
        计算目标优先级
        
        公式：
        priority = f(need_intensity, value_alignment, resource_availability, time_urgency)
        """
        for goal in goals:
            # 需求强度
            need_factor = goal.need.intensity
            
            # 价值观对齐度
            alignment = self.value_alignment(goal, agent)
            
            # 资源可用性
            resource_factor = self.resource_availability(goal, agent)
            
            # 时间紧迫性
            time_factor = self.time_urgency(goal)
            
            # 综合优先级
            goal.priority = (
                need_factor * 0.3 +
                alignment * 0.3 +
                resource_factor * 0.2 +
                time_factor * 0.2
            )
        
        return goals
    
    def value_alignment(self, goal: Goal, agent: Agent) -> float:
        """计算目标与价值观的对齐度"""
        related_values = goal.need.related_values
        if not related_values:
            return 0.5
        
        value_engine = agent.value_seed_engine
        alignments = [value_engine.seed.evolvable_values.get(v, 0.5) for v in related_values]
        return sum(alignments) / len(alignments)
```

### 3.3 目标生命周期

```python
class GoalLifecycleManager:
    """
    目标生命周期管理器
    """
    def __init__(self, generator: AutonomousGoalGenerator):
        self.generator = generator
        self.goal_states = {}  # goal_id -> GoalStatus
    
    def activate_goal(self, goal: Goal) -> bool:
        """激活目标"""
        if goal.status != GoalStatus.PENDING:
            return False
        
        # 检查前置条件
        if not self.check_prerequisites(goal):
            return False
        
        goal.status = GoalStatus.IN_PROGRESS
        goal.updated_at = now()
        self.generator.active_goal = goal
        return True
    
    def complete_goal(self, goal: Goal, success: bool):
        """完成目标"""
        if success:
            goal.status = GoalStatus.COMPLETED
            # 触发奖励/经验
            self.on_goal_completed(goal)
        else:
            goal.status = GoalStatus.FAILED
            self.on_goal_failed(goal)
        
        goal.updated_at = now()
        self.generator.active_goal = None
        
        # 生成下一个目标
        self.generator.pending_goals = self.generator.generate_goals(goal.agent)
    
    def abandon_goal(self, goal: Goal, reason: str):
        """放弃目标"""
        goal.status = GoalStatus.ABANDONED
        goal.updated_at = now()
        self.generator.active_goal = None
        
        # 记录放弃原因
        self.record_abandonment(goal, reason)
```

---

## 四、DynamicNegotiationProtocol（动态协商协议）

### 4.1 核心数据结构

```python
@dataclass
class Proposal:
    """提议"""
    proposal_id: str
    proposer: str                    # Agent ID
    topic: str                      # 协商主题
    terms: dict                     # 条款
    round: int                      # 协商轮次
    timestamp: float
    status: ProposalStatus          # PROPOSED, COUNTERED, ACCEPTED, REJECTED, EXPIRED

class ProposalStatus(Enum):
    PROPOSED = "proposed"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"

@dataclass
class NegotiationSession:
    """协商会话"""
    session_id: str
    parties: list[str]               # 参与者 ID 列表
    topic: str
    proposals: list[Proposal]
    status: NegotiationStatus       # ACTIVE, CONVERGED, BROKEN, EXPIRED
    created_at: float
    deadline: float | None
    agreement: dict | None          # 最终协议

class NegotiationStatus(Enum):
    ACTIVE = "active"
    CONVERGED = "converged"         # 达成一致
    BROKEN = "broken"               # 协商破裂
    EXPIRED = "expired"             # 超时

@dataclass
class Commitment:
    """承诺"""
    commitment_id: str
    agent_id: str
    promise: str                     # 承诺内容
    beneficiaries: list[str]          # 受益方
    deadline: float | None
    status: CommitmentStatus        # PENDING, FULFILLED, BROKEN
    created_at: float
```

### 4.2 核心方法

```python
class DynamicNegotiationProtocol:
    def __init__(self):
        self.sessions = {}           # session_id -> NegotiationSession
        self.commitments = {}        # commitment_id -> Commitment
        self.negotiation_templates = self.load_templates()
    
    async def initiate_negotiation(
        self, 
        initiator: str, 
        parties: list[str], 
        topic: str,
        initial_terms: dict
    ) -> NegotiationSession:
        """发起协商"""
        session = NegotiationSession(
            session_id=generate_id(),
            parties=[initiator] + parties,
            topic=topic,
            proposals=[],
            status=NegotiationStatus.ACTIVE,
            created_at=now(),
            deadline=now() + NEGOTIATION_TIMEOUT,
            agreement=None
        )
        
        # 创建初始提议
        proposal = Proposal(
            proposal_id=generate_id(),
            proposer=initiator,
            topic=topic,
            terms=initial_terms,
            round=1,
            timestamp=now(),
            status=ProposalStatus.PROPOSED
        )
        session.proposals.append(proposal)
        
        self.sessions[session.session_id] = session
        return session
    
    async def counter_propose(
        self, 
        session_id: str, 
        agent_id: str, 
        new_terms: dict
    ) -> Proposal:
        """还价"""
        session = self.sessions.get(session_id)
        if not session or session.status != NegotiationStatus.ACTIVE:
            raise NegotiationError("无效的协商会话")
        
        if agent_id not in session.parties:
            raise NegotiationError("不是协商参与者")
        
        last_proposal = session.proposals[-1]
        new_round = last_proposal.round + 1
        
        # 创建还价提议
        proposal = Proposal(
            proposal_id=generate_id(),
            proposer=agent_id,
            topic=session.topic,
            terms=new_terms,
            round=new_round,
            timestamp=now(),
            status=ProposalStatus.COUNTERED
        )
        
        # 更新上一轮提议状态
        last_proposal.status = ProposalStatus.COUNTERED
        
        session.proposals.append(proposal)
        return proposal
    
    async def accept_proposal(
        self, 
        session_id: str, 
        agent_id: str
    ) -> dict:
        """接受提议"""
        session = self.sessions.get(session_id)
        if not session:
            raise NegotiationError("无效的协商会话")
        
        last_proposal = session.proposals[-1]
        last_proposal.status = ProposalStatus.ACCEPTED
        
        # 检查是否所有方都接受
        all_accepted = self.check_all_accepted(session)
        
        if all_accepted:
            session.status = NegotiationStatus.CONVERGED
            session.agreement = last_proposal.terms
            
            # 创建承诺
            for party in session.parties:
                self.create_commitment(party, last_proposal.terms)
            
            return session.agreement
        
        return {"status": "waiting_for_others"}
    
    async def reject_proposal(
        self, 
        session_id: str, 
        agent_id: str, 
        reason: str
    ) -> None:
        """拒绝提议"""
        session = self.sessions.get(session_id)
        if not session:
            raise NegotiationError("无效的协商会话")
        
        last_proposal = session.proposals[-1]
        last_proposal.status = ProposalStatus.REJECTED
        session.status = NegotiationStatus.BROKEN
        
        # 记录拒绝原因
        self.record_rejection(session, agent_id, reason)
    
    async def negotiate(
        self, 
        initiator: str, 
        other: str, 
        topic: str,
        initial_terms: dict,
        max_rounds: int = 5
    ) -> dict:
        """
        完整协商流程
        
        Returns:
            agreement: 达成一致时的协议
            None: 协商破裂
        """
        # 1. 发起协商
        session = await self.initiate_negotiation(initiator, [other], topic, initial_terms)
        
        # 2. 协商循环
        current_proposer = other
        
        for round_num in range(1, max_rounds + 1):
            if session.status == NegotiationStatus.CONVERGED:
                return session.agreement
            
            if session.status == NegotiationStatus.BROKEN:
                return None
            
            # 等待对方响应（这里应该是异步的）
            # 简化版：直接模拟对方响应
            response = await self.simulate_response(other, session, topic)
            
            if response["action"] == "accept":
                return await self.accept_proposal(session.session_id, other)
            
            elif response["action"] == "reject":
                await self.reject_proposal(session.session_id, other, response["reason"])
                return None
            
            elif response["action"] == "counter":
                await self.counter_propose(session.session_id, other, response["terms"])
        
        # 超时
        session.status = NegotiationStatus.EXPIRED
        return None
    
    def create_commitment(self, agent_id: str, terms: dict) -> Commitment:
        """创建承诺"""
        commitment = Commitment(
            commitment_id=generate_id(),
            agent_id=agent_id,
            promise=terms.get("promise", str(terms)),
            beneficiaries=terms.get("beneficiaries", []),
            deadline=terms.get("deadline"),
            status=CommitmentStatus.PENDING,
            created_at=now()
        )
        self.commitments[commitment.commitment_id] = commitment
        return commitment
    
    def is_binding(self, agent_id: str, promise_id: str) -> bool:
        """
        判断承诺是否有约束力
        
        承诺是否有约束力取决于：
        1. 是否通过正式协商达成
        2. Agent 当时的价值观状态
        3. 是否有紧急情况
        """
        commitment = self.commitments.get(promise_id)
        if not commitment or commitment.agent_id != agent_id:
            return False
        
        # 检查 Agent 价值观是否发生显著变化
        # 如果价值观变化太大，承诺可能失去约束
        
        return commitment.status == CommitmentStatus.PENDING
```

### 4.3 协商策略

```python
class NegotiationStrategy:
    """
    协商策略基类
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    async def decide_response(
        self, 
        session: NegotiationSession, 
        my_last_proposal: Proposal | None
    ) -> NegotiationResponse:
        """
        决定如何响应对方的提议
        
        Returns:
            NegotiationResponse: {action: accept/reject/counter, terms: dict}
        """
        raise NotImplementedError


class CooperativeStrategy(NegotiationStrategy):
    """合作策略：倾向于接受"""
    
    async def decide_response(self, session, my_last_proposal):
        last = session.proposals[-1]
        
        # 检查提议是否可接受
        if self.is_acceptable(last.terms):
            return NegotiationResponse(action="accept")
        
        # 还价，但不要太过分
        counter_terms = self.generate_reasonable_counter(last.terms)
        return NegotiationResponse(action="counter", terms=counter_terms)


class CompetitiveStrategy(NegotiationStrategy):
    """竞争策略：倾向于最大化利益"""
    
    async def decide_response(self, session, my_last_proposal):
        last = session.proposals[-1]
        
        # 检查是否能获得更多
        if self.can_get_better(last.terms):
            counter_terms = self.improve_terms(last.terms)
            return NegotiationResponse(action="counter", terms=counter_terms)
        
        # 如果无法更好，拒绝
        return NegotiationResponse(
            action="reject", 
            reason="条款不利于我方"
        )


class AdaptiveStrategy(NegotiationStrategy):
    """自适应策略：根据对方行为调整"""
    
    async def decide_response(self, session, my_last_proposal):
        # 分析对方历史行为
        opponent = self.get_opponent(session)
        opponent_pattern = self.analyze_pattern(opponent)
        
        if opponent_pattern == "cooperative":
            return CooperativeStrategy(self.agent_id).decide_response(session, my_last_proposal)
        elif opponent_pattern == "competitive":
            return CompetitiveStrategy(self.agent_id).decide_response(session, my_last_proposal)
        else:
            return BalancedStrategy(self.agent_id).decide_response(session, my_last_proposal)
```

---

## 五、CollectiveGoalEmergence（集体目标涌现）

### 5.1 核心数据结构

```python
@dataclass
class GoalProposal:
    """目标提议"""
    proposal_id: str
    proposer: str                    # Agent ID
    goal_content: dict              # 目标内容
    support_level: float            # 支持度 0-1
    supporters: list[str]           # 支持者 ID 列表
    opponents: list[str]             # 反对者 ID 列表
    timestamp: float
    status: GoalProposalStatus      # ACTIVE, CONVERGED, REJECTED, WITHDRAWN
    evolution_history: list[dict]    # 演化历史

class GoalProposalStatus(Enum):
    ACTIVE = "active"
    CONVERGED = "converged"        # 收敛为集体目标
    REJECTED = "rejected"           # 被拒绝
    WITHDRAWN = "withdrawn"         # 撤回

@dataclass
class CollectiveGoal:
    """集体目标"""
    goal_id: str
    content: dict
    participants: list[str]          # 参与者
    supporters: list[str]            # 支持者
    priority: float
    status: CollectiveGoalStatus
    created_at: float
    deadline: float | None
    sub_goals: list[dict]           # 子目标分解
    completion_rate: float           # 完成度
```

### 5.2 核心方法

```python
class CollectiveGoalEmergence:
    def __init__(self):
        self.gossip_protocol = GossipProtocol()
        self.goal_proposals = {}    # proposal_id -> GoalProposal
        self.collective_goals = {}  # goal_id -> CollectiveGoal
        self.agent_attention = {}    # agent_id -> {goal_id: attention_level}
    
    async def broadcast_goal(
        self, 
        agent_id: str, 
        goal_content: dict,
        initial_supporters: list[str] = None
    ):
        """
        广播目标提议
        
        通过 Gossip 协议传播给网络中的其他 Agent
        """
        proposal = GoalProposal(
            proposal_id=generate_id(),
            proposer=agent_id,
            goal_content=goal_content,
            support_level=0.1,
            supporters=initial_supporters or [agent_id],
            opponents=[],
            timestamp=now(),
            status=GoalProposalStatus.ACTIVE,
            evolution_history=[]
        )
        
        self.goal_proposals[proposal.proposal_id] = proposal
        
        # 通过 Gossip 广播
        await self.gossip_protocol.broadcast(
            message_type="goal_proposal",
            content=proposal,
            origin=agent_id
        )
        
        return proposal
    
    async def receive_proposal(
        self, 
        agent_id: str, 
        proposal: GoalProposal
    ):
        """
        接收目标提议
        
        Agent 收到提议后的处理逻辑：
        1. 评估提议是否符合自身价值观
        2. 评估提议是否有价值
        3. 决定支持/反对/忽略
        """
        # 避免重复处理
        if self.is_duplicate(proposal, agent_id):
            return
        
        # 评估提议
        evaluation = await self.evaluate_proposal(agent_id, proposal)
        
        if evaluation.support:
            await self.support_proposal(agent_id, proposal.proposal_id)
        elif evaluation.oppose:
            await self.oppose_proposal(agent_id, proposal.proposal_id)
        
        # 继续传播（TTL 衰减）
        if proposal.ttl > 0:
            await self.gossip_protocol.relay(proposal, agent_id)
    
    async def support_proposal(
        self, 
        agent_id: str, 
        proposal_id: str
    ):
        """支持提议"""
        proposal = self.goal_proposals.get(proposal_id)
        if not proposal or agent_id in proposal.supporters:
            return
        
        proposal.supporters.append(agent_id)
        proposal.support_level = len(proposal.supporters) / len(self.get_network_agents())
        
        # 记录演化历史
        proposal.evolution_history.append({
            "action": "support",
            "agent": agent_id,
            "timestamp": now(),
            "new_support_level": proposal.support_level
        })
        
        # 检查是否收敛
        if self.check_convergence(proposal):
            await self.converge_to_collective_goal(proposal)
    
    async def oppose_proposal(
        self, 
        agent_id: str, 
        proposal_id: str
    ):
        """反对提议"""
        proposal = self.goal_proposals.get(proposal_id)
        if not proposal or agent_id in proposal.opponents:
            return
        
        proposal.opponents.append(agent_id)
        
        # 检查是否应该拒绝
        reject_threshold = len(proposal.opponents) / len(self.get_network_agents())
        if reject_threshold > REJECT_THRESHOLD:
            proposal.status = GoalProposalStatus.REJECTED
    
    def check_convergence(self, proposal: GoalProposal) -> bool:
        """
        检查是否收敛
        
        收敛条件：
        1. 支持度 > 收敛阈值（默认 0.3）
        2. 支持者数量 > 最小参与数
        3. 反对率 < 拒绝阈值
        """
        total_agents = len(self.get_network_agents())
        support_ratio = len(proposal.supporters) / total_agents
        oppose_ratio = len(proposal.opponents) / total_agents
        
        return (
            support_ratio > CONVERGENCE_THRESHOLD and
            len(proposal.supporters) >= MIN_PARTICIPANTS and
            oppose_ratio < REJECT_THRESHOLD
        )
    
    async def converge_to_collective_goal(
        self, 
        proposal: GoalProposal
    ):
        """收敛为集体目标"""
        proposal.status = GoalProposalStatus.CONVERGED
        
        collective_goal = CollectiveGoal(
            goal_id=proposal.proposal_id,
            content=proposal.goal_content,
            participants=list(set(proposal.supporters + [proposal.proposer])),
            supporters=proposal.supporters,
            priority=proposal.support_level,
            status=CollectiveGoalStatus.ACTIVE,
            created_at=now(),
            deadline=None,
            sub_goals=self.decompose_goal(proposal.goal_content),
            completion_rate=0.0
        )
        
        self.collective_goals[collective_goal.goal_id] = collective_goal
        
        # 广播集体目标形成
        await self.gossip_protocol.broadcast(
            message_type="collective_goal_formed",
            content=collective_goal,
            origin="system"
        )
        
        return collective_goal
    
    def decompose_goal(self, goal_content: dict) -> list[dict]:
        """
        分解集体目标为子目标
        
        分解策略：
        1. 按技能/能力分解
        2. 按阶段/步骤分解
        3. 按参与者分解
        """
        sub_goals = []
        
        # 简单分解：每个参与者一个子目标
        participants = goal_content.get("participants", [])
        for i, participant in enumerate(participants):
            sub_goals.append({
                "sub_goal_id": generate_id(),
                "assignee": participant,
                "description": f"{goal_content['name']} - Part {i+1}",
                "weight": 1.0 / len(participants) if participants else 1.0
            })
        
        return sub_goals
    
    def calculate_collective_priority(self, goal_id: str) -> float:
        """
        计算集体目标优先级
        
        公式：
        priority = f(support_ratio, urgency, importance, resource_availability)
        """
        goal = self.collective_goals.get(goal_id)
        if not goal:
            return 0.0
        
        support_factor = len(goal.supporters) / len(self.get_network_agents())
        urgency_factor = self.calculate_urgency(goal)
        importance_factor = goal.content.get("importance", 0.5)
        
        return (
            support_factor * 0.4 +
            urgency_factor * 0.3 +
            importance_factor * 0.3
        )
```

### 5.3 Gossip 协议

```python
class GossipProtocol:
    """
    Gossip 协议实现
    
    用于：
    - 目标提议传播
    - 状态同步
    - 信息扩散
    """
    def __init__(self):
        self.peers = {}              # peer_id -> PeerInfo
        self.message_cache = {}      # message_id -> Message
        self.fanout = 3              # 每轮传播的节点数
        self.ttl = 5                 # 消息生存时间
    
    async def broadcast(
        self, 
        message_type: str, 
        content: Any, 
        origin: str
    ):
        """
        广播消息
        
        Gossip 流程：
        1. 选择随机节点传播
        2. 节点收到后继续传播
        3. TTL 耗尽后停止
        """
        message = Message(
            message_id=generate_id(),
            type=message_type,
            content=content,
            origin=origin,
            ttl=self.ttl,
            timestamp=now()
        )
        
        self.message_cache[message.message_id] = message
        
        # 选择随机节点传播
        peers = self.select_random_peers(self.fanout)
        
        for peer in peers:
            await self.send_to_peer(peer, message)
    
    async def relay(self, message: Message, from_peer: str):
        """转发消息"""
        if message.ttl <= 0:
            return
        
        message.ttl -= 1
        peers = self.select_random_peers(self.fanout)
        
        for peer in peers:
            if peer != from_peer:
                await self.send_to_peer(peer, message)
```

---

## 六、EmergentGovernance（涌现治理）

### 6.1 核心数据结构

```python
@dataclass
class GovernanceRule:
    """治理规则"""
    rule_id: str
    content: str                      # 规则内容
    proposer: str                     # 提议者
    supporters: list[str]            # 支持者
    opponents: list[str]             # 反对者
    status: RuleStatus               # PROPOSED, ADOPTED, REJECTED, EVOLVED
    created_at: float
    adopted_at: float | None
    enforcement_level: float          # 执行力度 0-1
    violation_count: int             # 违反次数
    evolution_history: list[dict]

class RuleStatus(Enum):
    PROPOSED = "proposed"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    EVOLVED = "evolved"
    OBSOLETE = "obsolete"

@dataclass
class Vote:
    """投票"""
    vote_id: str
    voter: str
    rule_id: str
    decision: bool                   # True = 支持, False = 反对
    weight: float                    # 投票权重
    timestamp: float
    reason: str | None

@dataclass
class Violation:
    """违规记录"""
    violation_id: str
    rule_id: str
    violator: str
    description: str
    timestamp: float
    penalty: dict | None
```

### 6.2 核心方法

```python
class EmergentGovernance:
    def __init__(self):
        self.rules = {}              # rule_id -> GovernanceRule
        self.votes = {}              # vote_id -> Vote
        self.violations = {}         # violation_id -> Violation
        self.agent_voting_power = {}  # agent_id -> voting_power
    
    def propose_rule(self, agent_id: str, rule_content: str) -> GovernanceRule:
        """
        提议新规则
        
        任何 Agent 都可以提议规则
        """
        rule = GovernanceRule(
            rule_id=generate_id(),
            content=rule_content,
            proposer=agent_id,
            supporters=[agent_id],
            opponents=[],
            status=RuleStatus.PROPOSED,
            created_at=now(),
            adopted_at=None,
            enforcement_level=1.0,
            violation_count=0,
            evolution_history=[]
        )
        
        self.rules[rule.rule_id] = rule
        
        # 广播提议
        self.broadcast_rule_proposal(rule)
        
        return rule
    
    def vote_on_rule(
        self, 
        agent_id: str, 
        rule_id: str, 
        decision: bool,
        reason: str = None
    ) -> Vote:
        """
        对规则投票
        
        投票权重基于：
        1. 声誉
        2. 质押量
        3. 历史参与度
        """
        rule = self.rules.get(rule_id)
        if not rule or rule.status != RuleStatus.PROPOSED:
            raise GovernanceError("无效的规则提议")
        
        weight = self.calculate_voting_weight(agent_id)
        
        vote = Vote(
            vote_id=generate_id(),
            voter=agent_id,
            rule_id=rule_id,
            decision=decision,
            weight=weight,
            timestamp=now(),
            reason=reason
        )
        
        self.votes[vote.vote_id] = vote
        
        # 更新规则的支持/反对列表
        if decision:
            rule.supporters.append(agent_id)
        else:
            rule.opponents.append(agent_id)
        
        # 检查是否应该采纳或拒绝
        self.evaluate_rule_status(rule)
        
        return vote
    
    def calculate_voting_weight(self, agent_id: str) -> float:
        """
        计算投票权重
        
        公式：
        weight = (reputation * 0.4 + stake * 0.3 + participation * 0.3) / max_weight
        """
        reputation = self.get_agent_reputation(agent_id)
        stake = self.get_agent_stake(agent_id)
        participation = self.get_agent_participation(agent_id)
        
        raw_weight = reputation * 0.4 + stake * 0.3 + participation * 0.3
        
        # 归一化
        max_weight = max(self.agent_voting_power.values()) if self.agent_voting_power else 1.0
        
        return raw_weight / max_weight if max_weight > 0 else 0.0
    
    def evaluate_rule_status(self, rule: GovernanceRule):
        """
        评估规则状态
        
        采纳条件：
        - 支持权重 > 50%
        - 支持者数量 > 最小投票数
        
        拒绝条件：
        - 反对权重 > 50%
        """
        total_weight = sum(
            self.calculate_voting_weight(a) 
            for a in rule.supporters + rule.opponents
        )
        
        support_weight = sum(
            self.calculate_voting_weight(a) 
            for a in rule.supporters
        )
        
        oppose_weight = sum(
            self.calculate_voting_weight(a) 
            for a in rule.opponents
        )
        
        if total_weight == 0:
            return
        
        support_ratio = support_weight / total_weight
        oppose_ratio = oppose_weight / total_weight
        
        if support_ratio > ADOPTION_THRESHOLD and len(rule.supporters) >= MIN_VOTERS:
            rule.status = RuleStatus.ADOPTED
            rule.adopted_at = now()
            self.broadcast_rule_adopted(rule)
        
        elif oppose_ratio > REJECTION_THRESHOLD:
            rule.status = RuleStatus.REJECTED
            self.broadcast_rule_rejected(rule)
    
    def is_rule_violated(self, agent_id: str, action: Action) -> Violation | None:
        """
        检查是否违反规则
        
        返回违规记录或 None
        """
        for rule in self.rules.values():
            if rule.status != RuleStatus.ADOPTED:
                continue
            
            if self.check_violation(action, rule):
                violation = Violation(
                    violation_id=generate_id(),
                    rule_id=rule.rule_id,
                    violator=agent_id,
                    description=f"违反规则: {rule.content}",
                    timestamp=now(),
                    penalty=self.calculate_penalty(rule, action)
                )
                
                self.violations[violation.violation_id] = violation
                rule.violation_count += 1
                
                # 检查规则是否应该演化
                if rule.violation_count > VIOLATION_THRESHOLD:
                    self.evolve_rule(rule)
                
                return violation
        
        return None
    
    def evolve_rule(self, rule: GovernanceRule):
        """
        演化规则
        
        当规则被频繁违反时，考虑：
        1. 修改规则内容
        2. 降低执行力度
        3. 废除规则
        """
        rule.status = RuleStatus.EVOLVED
        
        # 分析违规模式
        violation_pattern = self.analyze_violation_pattern(rule)
        
        # 根据模式决定演化方向
        if violation_pattern == "unclear":
            # 规则不清晰，尝试澄清
            rule.content = self.clarify_rule(rule.content)
        elif violation_pattern == "too_strict":
            # 规则太严格，降低执行力度
            rule.enforcement_level *= 0.8
        elif violation_pattern == "obsolete":
            # 规则过时，标记为废除
            rule.status = RuleStatus.OBSOLETE
        
        rule.evolution_history.append({
            "timestamp": now(),
            "action": "evolved",
            "violation_count": rule.violation_count
        })
```

---

## 七、模块集成

### 7.1 L3 Agent

```python
class L3Agent:
    """
    L3 自主目标 Agent
    """
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        # L3 核心模块
        self.value_engine = ValueSeedEngine(ValueSeed())
        self.motivation_engine = IntrinsicMotivationEngine(agent_id)
        self.goal_generator = AutonomousGoalGenerator(agent_id)
        self.negotiation_protocol = DynamicNegotiationProtocol()
        self.collective_emergence = CollectiveGoalEmergence()
        self.governance = EmergentGovernance()
    
    async def run_cycle(self):
        """
        L3 Agent 运行周期
        """
        # 1. 评估内在动机状态
        motivations = self.motivation_engine.generate_motivations(self)
        
        # 2. 生成自主目标
        goals = self.goal_generator.generate_goals(self)
        
        # 3. 参与集体目标涌现
        await self.collective_emergence.check_active_proposals(self.agent_id)
        
        # 4. 执行目标
        if self.goal_generator.active_goal:
            await self.execute_goal(self.goal_generator.active_goal)
        
        # 5. 评估行动，更新价值观
        self.value_engine.evolve(recent_experiences)
        
        # 6. 参与治理
        await self.governance.check_pending_rules(self.agent_id)
    
    async def execute_goal(self, goal: Goal):
        """执行目标"""
        # 目标执行逻辑
        pass
    
    async def negotiate_with_human(
        self, 
        human_id: str, 
        topic: str, 
        initial_terms: dict
    ):
        """与人类协商"""
        return await self.negotiation_protocol.negotiate(
            initiator=self.agent_id,
            other=human_id,
            topic=topic,
            initial_terms=initial_terms
        )
```

### 7.2 L3 Platform

```python
class L3Platform:
    """
    L3 平台
    """
    def __init__(self):
        self.agents = {}            # agent_id -> L3Agent
        self.collective_goals = {}  # 集体目标
        self.governance_rules = {}  # 治理规则
    
    async def add_agent(self, agent: L3Agent):
        """添加 Agent"""
        self.agents[agent.agent_id] = agent
        await agent.collective_emergence.join_network()
    
    async def get_collective_state(self) -> CollectiveState:
        """获取集体状态"""
        return CollectiveState(
            active_goals=list(self.collective_goals.values()),
            governance_rules=list(self.governance_rules.values()),
            agent_count=len(self.agents),
            participation_rate=self.calculate_participation_rate()
        )
```

---

*创建时间: 2026-04-03*
*版本: 1.0*
*状态: 详细设计完成*
