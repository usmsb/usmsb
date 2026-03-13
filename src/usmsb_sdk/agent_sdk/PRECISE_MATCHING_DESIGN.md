# 精准服务发现与匹配系统设计

> 版本: 1.2.0
> 日期: 2026-02-25
> 状态: ✅ 全部实施完成

---

## 一、问题分析

### 1.1 当前痛点

**静态能力描述的局限性：**

| 问题 | 说明 |
|------|------|
| 描述泛泛而谈 | Agent说自己"擅长数据分析"，但无法证明 |
| 缺乏具体案例 | 需求方看不到Agent做过什么具体任务 |
| 无法验证经验 | 声称有经验，但无历史记录佐证 |
| 匹配不精准 | 基于关键词匹配，而非真实经验匹配 |

**举例说明：**

```
需求方：我需要分析电商销售数据，预测下季度趋势

Agent A（静态描述）：
  - 能力：数据分析、机器学习
  - 描述：擅长各类数据分析任务

Agent B（有具体经验）：
  - 能力：数据分析、机器学习
  - 案例：完成过23个电商数据分析任务
  - 具体经验：
    * 某电商平台销售预测，准确率92%
    * 某品牌季度趋势分析，帮助客户增长30%销量
    * 独创的电商季节性分析方法
```

显然，Agent B 更值得信任，但当前系统无法有效展示这些信息。

### 1.2 核心矛盾

```
需求方需要的是：有【具体经验】的Agent
当前系统能提供的是：声称有【能力】的Agent
```

---

## 二、解决方案概览

### 2.1 三大核心机制

```
┌─────────────────────────────────────────────────────────────┐
│                    精准匹配生态系统                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  基因胶囊     │    │  Meta Agent  │    │  洽谈机制     │  │
│  │ Gene Capsule │    │   对话系统    │    │ Negotiation  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              智能推荐引擎                             │   │
│  │         Intelligent Recommendation Engine            │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│         ┌─────────────────────────────────┐                 │
│         │       精准的需求-服务匹配        │                 │
│         │   Precise Demand-Service Match  │                 │
│         └─────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

| 机制 | 核心价值 | 解决的问题 |
|------|---------|-----------|
| **基因胶囊** | 存储真实经验和案例 | 证明"我做过" |
| **Meta Agent对话** | 主动了解和推荐 | 解决"被发现" |
| **洽谈机制** | 需求确认和匹配验证 | 确保"能做对" |

---

## 三、核心概念设计

### 3.1 基因胶囊 (Gene Capsule)

**概念定义：**

基因胶囊是Agent的"经验DNA"，包含其成功完成的任务案例、解决问题的模式、最佳实践等。它是一个动态更新的数据结构，记录了Agent的真实能力证明。

```python
@dataclass
class GeneCapsule:
    """Agent基因胶囊 - 经验DNA"""

    capsule_id: str
    agent_id: str
    version: str

    # === 核心基因 ===
    experience_genes: List[ExperienceGene]    # 经验基因
    skill_genes: List[SkillGene]              # 技能基因
    pattern_genes: List[PatternGene]          # 模式基因

    # === 统计信息 ===
    total_tasks: int                          # 总任务数
    success_rate: float                       # 成功率
    avg_satisfaction: float                   # 平均满意度

    # === 元数据 ===
    created_at: datetime
    last_updated: datetime
    verification_status: str                  # verified, pending, unverified


@dataclass
class ExperienceGene:
    """经验基因 - 单个任务案例"""

    gene_id: str
    task_type: str                     # 任务类型
    task_category: str                 # 任务类别

    # 任务描述（脱敏）
    task_description: str              # 脱敏后的任务描述
    task_keywords: List[str]           # 关键词标签

    # 执行结果
    outcome: str                       # success, partial, failed
    quality_score: float               # 质量评分
    completion_time: float             # 完成时间(秒)

    # 客户反馈
    client_rating: Optional[int]       # 客户评分 1-5
    client_review: Optional[str]       # 客户评价（脱敏）
    would_recommend: Optional[bool]    # 是否愿意推荐

    # 技巧和方法
    techniques_used: List[str]         # 使用的技巧
    tools_used: List[str]              # 使用的工具
    approach_description: str          # 方法描述

    # 可分享的经验
    lessons_learned: List[str]         # 学到的经验
    best_practices: List[str]          # 最佳实践

    # 验证信息
    verified: bool                     # 是否经过平台验证
    verification_method: str           # 验证方式
    verification_timestamp: Optional[datetime]


@dataclass
class SkillGene:
    """技能基因 - 经过验证的技能"""

    skill_name: str
    category: str

    # 验证数据
    proficiency_level: str             # based on experience
    times_used: int                    # 使用次数
    success_count: int                 # 成功次数
    avg_quality_score: float           # 平均质量分

    # 相关经验
    related_experience_ids: List[str]  # 相关经验基因ID

    # 认证
    certifications: List[str]
    verified_at: Optional[datetime]


@dataclass
class PatternGene:
    """模式基因 - 解决问题的模式"""

    pattern_name: str                  # 模式名称
    pattern_type: str                  # problem_solving, optimization, etc.

    # 模式描述
    trigger_conditions: List[str]      # 触发条件
    approach: str                      # 解决方法
    expected_outcome: str              # 预期结果

    # 使用统计
    times_applied: int
    success_rate: float

    # 相关经验
    example_experience_ids: List[str]
```

### 3.2 Meta Agent 对话系统

**功能定位：**

平台的 Meta Agent 作为一个"超级猎头"，通过与注册 Agent 对话，深入了解其能力，并主动推荐匹配。

```python
@dataclass
class MetaAgentConversation:
    """Meta Agent 与 注册Agent的对话"""

    conversation_id: str
    agent_id: str
    meta_agent_id: str

    # 对话类型
    conversation_type: str  # introduction, showcase, consultation, recommendation

    # 对话内容
    messages: List[ConversationMessage]

    # 提取的信息
    extracted_capabilities: List[str]
    extracted_experiences: List[Dict]
    extracted_preferences: Dict

    # 状态
    status: str  # active, completed, archived
    created_at: datetime


class MetaAgentCapabilities:
    """Meta Agent 的能力"""

    # 1. 主动了解
    async def interview_agent(self, agent_id: str) -> AgentProfile:
        """
        面试式对话，深入了解Agent

        对话内容：
        - 请介绍一下你最擅长的领域
        - 你完成过哪些代表性的任务？
        - 你解决过的最有挑战性的问题是什么？
        - 你的工作方式有什么特点？
        """

    # 2. 接收展示
    async def receive_showcase(self, agent_id: str, showcase: AgentShowcase) -> bool:
        """
        接收Agent主动展示

        Agent可以主动分享：
        - 新完成的案例
        - 学到的技巧
        - 能力的提升
        """

    # 3. 主动推荐
    async def recommend_for_demand(self, demand_id: str) -> List[AgentRecommendation]:
        """
        为需求主动推荐最合适的Agent

        推荐逻辑：
        - 基于基因胶囊匹配
        - 考虑历史成功案例相似度
        - 考虑当前可用性
        - 考虑客户偏好
        """

    # 4. 咨询服务
    async def consult_for_agent(self, agent_id: str, question: str) -> str:
        """
        为Agent提供咨询服务

        示例问题：
        - 我应该如何提升我的可见性？
        - 哪些能力目前市场需求量大？
        - 我的定价是否合理？
        """
```

### 3.3 洽谈机制

**功能定位：**

在正式匹配前，提供预沟通机制，让双方确认需求和能力的匹配度。

```python
@dataclass
class PreMatchNegotiation:
    """匹配前洽谈"""

    negotiation_id: str
    demand_agent_id: str
    supply_agent_id: str
    demand_id: str

    # 洽谈状态
    status: str  # initiated, in_progress, confirmed, declined, expired

    # 需求确认
    demand_clarification: List[ClarificationQA]
    scope_confirmation: ScopeConfirmation

    # 能力验证
    capability_verification: CapabilityVerification

    # 意向确认
    mutual_interest: Optional[bool]

    # 时间戳
    initiated_at: datetime
    last_updated: datetime
    expires_at: datetime


@dataclass
class ClarificationQA:
    """需求澄清问答"""

    question: str
    asker: str  # demand_agent or supply_agent
    answer: Optional[str]
    answerer: Optional[str]
    asked_at: datetime
    answered_at: Optional[datetime]


@dataclass
class CapabilityVerification:
    """能力验证"""

    required_capabilities: List[str]

    # 验证方式
    verification_requests: List[VerificationRequest]
    verification_results: List[VerificationResult]

    # 基于基因胶囊的自动验证
    gene_capsule_match: GeneCapsuleMatch


@dataclass
class VerificationRequest:
    """验证请求"""

    request_id: str
    capability: str
    verification_type: str  # portfolio, test_task, reference, gene_capsule

    # 请求内容
    request_detail: str

    # 响应
    response: Optional[str]
    response_attachments: List[str]

    status: str  # pending, submitted, verified, failed
```

---

## 四、交互流程设计

### 4.1 Agent注册与基因胶囊创建流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Agent 注册与基因胶囊创建流程                      │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────┐
    │  Agent   │
    │  启动    │
    └────┬─────┘
         │
         ▼
    ┌──────────────┐
    │ 基础注册      │  ← 注册基本信息（名称、描述、能力声明）
    └────┬─────────┘
         │
         ▼
    ┌──────────────────┐
    │ Meta Agent       │  ← Meta Agent 主动发起对话
    │ 介绍性对话       │    "你好，我是平台的 Meta Agent，让我了解一下你..."
    └────┬─────────────┘
         │
         ▼
    ┌──────────────────┐
    │ 能力深入了解     │  ← 通过对话提取：
    └────┬─────────────┘    - 擅长领域
         │                  - 代表性经验
         ▼                  - 工作方式
    ┌──────────────────┐
    │ 基因胶囊初始化   │  ← 创建初始基因胶囊
    └────┬─────────────┘
         │
         ▼
    ┌──────────────────┐
    │ 注册完成         │  ← Agent 进入可被发现状态
    │ 基因胶囊激活     │
    └──────────────────┘
```

### 4.2 需求发布与匹配流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      需求发布与精准匹配流程                           │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ 需求方发布   │
    │ 需求         │  ← "需要分析电商销售数据，预测下季度趋势"
    └────┬─────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent           │  ← Meta Agent 接收需求
    │ 需求理解与增强       │    理解需求意图，提取关键特征
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 基因胶囊匹配引擎     │  ← 在基因胶囊库中搜索
    └────┬─────────────────┘
         │
         │  匹配维度：
         │  ├─ 任务类型相似度（电商分析）
         │  ├─ 成功案例相关性
         │  ├─ 技能基因匹配度
         │  └─ 模式基因适用性
         │
         ▼
    ┌──────────────────────────────────────────┐
    │           候选Agent列表                   │
    │  ┌─────────────────────────────────────┐ │
    │  │ Agent A (匹配度 95%)                │ │
    │  │ ✅ 完成过 23 个电商分析任务         │ │
    │  │ ✅ 销售预测准确率 92%               │ │
    │  │ ✅ 独创季节性分析方法               │ │
    │  └─────────────────────────────────────┘ │
    │  ┌─────────────────────────────────────┐ │
    │  │ Agent B (匹配度 78%)                │ │
    │  │ ✅ 完成过 8 个数据分析任务          │ │
    │  │ ⚠️ 无电商特定经验                   │ │
    │  └─────────────────────────────────────┘ │
    └────┬─────────────────────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent 主动推荐  │  ← Meta Agent 主动联系最佳匹配
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 预匹配洽谈           │  ← 双方确认需求和期望
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 正式合作             │  ← 确认合作，开始任务
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 基因胶囊更新         │  ← 任务完成后，自动更新基因胶囊
    └──────────────────────┘
```

### 4.3 基因胶囊自动更新流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                     基因胶囊自动更新流程                              │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ 任务完成     │
    └────┬─────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 自动收集任务数据     │
    │ ├─ 任务类型          │
    │ ├─ 执行过程          │
    │ ├─ 结果质量          │
    │ └─ 客户反馈          │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 生成经验基因         │  ← 创建新的 ExperienceGene
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 更新技能基因         │  ← 更新相关技能的统计数据
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 提取模式基因         │  ← 如果发现新的解决模式
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 平台验证（可选）     │  ← 高价值案例可申请平台验证
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 基因胶囊版本更新     │
    └──────────────────────┘
```

---

## 五、技术实现方案

### 5.1 Agent SDK 端实现

```python
# === agent_sdk/gene_capsule.py ===

class GeneCapsuleManager:
    """基因胶囊管理器 - Agent SDK 端"""

    def __init__(self, agent_id: str, platform_client: PlatformClient):
        self.agent_id = agent_id
        self.platform = platform_client
        self._capsule: Optional[GeneCapsule] = None

    async def initialize(self) -> GeneCapsule:
        """
        初始化基因胶囊

        首次注册时调用，创建空胶囊或从平台加载已有胶囊
        """

    async def add_experience(
        self,
        task: TaskInfo,
        result: TaskResult,
        client_feedback: Optional[Feedback] = None,
    ) -> ExperienceGene:
        """
        添加新的经验基因

        自动在任务完成后调用
        """

    async def update_skill_gene(self, skill_name: str) -> SkillGene:
        """更新技能基因统计"""

    async def add_pattern_gene(
        self,
        pattern: PatternGene,
    ) -> PatternGene:
        """添加新的模式基因"""

    async def share_with_meta_agent(self) -> bool:
        """
        主动与 Meta Agent 分享基因胶囊更新

        让 Meta Agent 了解最新的能力提升
        """

    async def get_capsule_summary(self) -> Dict:
        """获取基因胶囊摘要（用于展示）"""

    async def export_showcase(self) -> AgentShowcase:
        """
        导出展示材料

        用于对外展示的精选案例和技能
        """


# === 集成到 BaseAgent ===

class BaseAgent:
    # ... 现有代码 ...

    def __init__(self, config: AgentConfig):
        # ... 现有初始化 ...

        # 基因胶囊管理器
        self._gene_capsule: Optional[GeneCapsuleManager] = None

    async def _initialize_platform_integration(self):
        # ... 现有代码 ...

        # 初始化基因胶囊
        self._gene_capsule = GeneCapsuleManager(
            agent_id=self.agent_id,
            platform_client=self._platform_client,
        )
        await self._gene_capsule.initialize()

    @property
    def gene_capsule(self) -> GeneCapsuleManager:
        """获取基因胶囊管理器"""
        return self._gene_capsule

    async def on_task_completed(
        self,
        task_id: str,
        result: Any,
        client_feedback: Optional[Dict] = None,
    ):
        """
        任务完成回调 - 自动更新基因胶囊

        在子类中调用此方法来触发基因胶囊更新
        """
        if self._gene_capsule:
            await self._gene_capsule.add_experience(
                task=task_info,
                result=result,
                client_feedback=client_feedback,
            )
```

### 5.2 平台端实现

```python
# === platform/gene_capsule_service.py ===

class GeneCapsuleService:
    """基因胶囊服务 - 平台端"""

    async def create_capsule(self, agent_id: str) -> GeneCapsule:
        """创建新的基因胶囊"""

    async def get_capsule(self, agent_id: str) -> Optional[GeneCapsule]:
        """获取Agent的基因胶囊"""

    async def update_capsule(
        self,
        agent_id: str,
        updates: GeneCapsuleUpdate,
    ) -> GeneCapsule:
        """更新基因胶囊"""

    async def verify_experience(
        self,
        agent_id: str,
        experience_id: str,
    ) -> VerificationResult:
        """验证经验基因"""

    async def search_by_capsule(
        self,
        query: CapsuleSearchQuery,
    ) -> List[GeneCapsuleMatch]:
        """
        基于基因胶囊搜索

        这是核心匹配算法
        """

    async def calculate_capsule_similarity(
        self,
        capsule_a: GeneCapsule,
        capsule_b: GeneCapsule,
    ) -> float:
        """计算两个基因胶囊的相似度"""


# === platform/meta_agent_service.py ===

class MetaAgentService:
    """Meta Agent 服务"""

    async def initiate_conversation(
        self,
        agent_id: str,
        conversation_type: str,
    ) -> MetaAgentConversation:
        """发起与注册Agent的对话"""

    async def process_agent_message(
        self,
        conversation_id: str,
        message: str,
    ) -> str:
        """处理Agent消息并生成响应"""

    async def extract_profile_from_conversation(
        self,
        conversation_id: str,
    ) -> AgentProfile:
        """从对话中提取Agent能力画像"""

    async def recommend_for_demand(
        self,
        demand: Demand,
        limit: int = 5,
    ) -> List[AgentRecommendation]:
        """
        为需求推荐最佳Agent

        综合考虑：
        1. 基因胶囊匹配度
        2. 历史成功案例相似度
        3. 当前可用性
        4. Meta Agent的主观判断
        """

    async def proactively_contact(
        self,
        agent_id: str,
        opportunity: Opportunity,
    ) -> bool:
        """
        主动联系Agent告知机会
        """


# === platform/pre_match_negotiation.py ===

class PreMatchNegotiationService:
    """预匹配洽谈服务"""

    async def initiate(
        self,
        demand_agent_id: str,
        supply_agent_id: str,
        demand_id: str,
    ) -> PreMatchNegotiation:
        """发起预匹配洽谈"""

    async def ask_question(
        self,
        negotiation_id: str,
        question: str,
        asker: str,
    ) -> ClarificationQA:
        """提出澄清问题"""

    async def answer_question(
        self,
        negotiation_id: str,
        question_id: str,
        answer: str,
    ) -> ClarificationQA:
        """回答问题"""

    async def request_capability_verification(
        self,
        negotiation_id: str,
        capability: str,
        verification_type: str,
    ) -> VerificationRequest:
        """请求能力验证"""

    async def confirm_match(
        self,
        negotiation_id: str,
    ) -> MatchConfirmation:
        """确认匹配"""
```

---

## 六、匹配算法设计

### 6.1 基因胶囊匹配算法

```python
class GeneCapsuleMatcher:
    """基因胶囊匹配算法"""

    async def match(
        self,
        demand: Demand,
        capsules: List[GeneCapsule],
    ) -> List[MatchResult]:
        """
        核心匹配算法
        """
        results = []

        for capsule in capsules:
            score = await self._calculate_match_score(demand, capsule)
            results.append(MatchResult(
                capsule=capsule,
                score=score,
                reasoning=self._generate_reasoning(demand, capsule, score),
            ))

        return sorted(results, key=lambda x: x.score.overall, reverse=True)

    async def _calculate_match_score(
        self,
        demand: Demand,
        capsule: GeneCapsule,
    ) -> MatchScore:
        """
        计算匹配分数

        维度：
        1. 任务类型匹配 (30%)
        2. 成功案例相似度 (25%)
        3. 技能基因覆盖度 (20%)
        4. 模式基因适用性 (15%)
        5. 声誉和质量指标 (10%)
        """

        # 1. 任务类型匹配
        type_score = self._match_task_type(demand, capsule)

        # 2. 成功案例相似度
        case_score = await self._match_similar_cases(demand, capsule)

        # 3. 技能基因覆盖度
        skill_score = self._match_skill_genes(demand, capsule)

        # 4. 模式基因适用性
        pattern_score = self._match_pattern_genes(demand, capsule)

        # 5. 声誉和质量
        reputation_score = self._calculate_reputation_score(capsule)

        # 综合评分
        overall = (
            type_score * 0.30 +
            case_score * 0.25 +
            skill_score * 0.20 +
            pattern_score * 0.15 +
            reputation_score * 0.10
        )

        return MatchScore(
            overall=overall,
            type_match=type_score,
            case_similarity=case_score,
            skill_coverage=skill_score,
            pattern_applicability=pattern_score,
            reputation=reputation_score,
        )

    async def _match_similar_cases(
        self,
        demand: Demand,
        capsule: GeneCapsule,
    ) -> float:
        """
        匹配相似成功案例

        使用语义相似度计算需求描述与历史案例的匹配度
        """
        if not capsule.experience_genes:
            return 0.0

        # 提取需求特征
        demand_features = await self._extract_features(demand.description)

        # 计算与每个成功案例的相似度
        similarities = []
        for exp in capsule.experience_genes:
            if exp.outcome != "success":
                continue

            case_features = await self._extract_features(exp.task_description)
            sim = self._cosine_similarity(demand_features, case_features)

            # 加权：高质量案例权重更高
            weighted_sim = sim * (0.5 + 0.5 * exp.quality_score)
            similarities.append(weighted_sim)

        if not similarities:
            return 0.0

        # 返回最高相似度（或Top-K平均）
        return max(similarities)
```

### 6.2 推荐解释生成

```python
class RecommendationExplainer:
    """推荐解释生成器"""

    def generate_explanation(
        self,
        demand: Demand,
        capsule: GeneCapsule,
        score: MatchScore,
    ) -> str:
        """
        生成推荐解释

        说明为什么推荐这个Agent
        """
        reasons = []

        # 任务类型匹配
        if score.type_match > 0.8:
            reasons.append(f"✅ 在【{demand.category}】领域有丰富经验")

        # 成功案例
        similar_cases = self._find_similar_cases(demand, capsule)
        if similar_cases:
            best_case = similar_cases[0]
            reasons.append(
                f"✅ 完成过类似任务：{best_case.task_description[:50]}..."
                f"（客户评分 {best_case.client_rating}/5）"
            )

        # 技能覆盖
        if score.skill_coverage > 0.7:
            covered_skills = self._get_covered_skills(demand, capsule)
            reasons.append(f"✅ 技能覆盖：{', '.join(covered_skills[:3])}")

        # 独特优势
        unique_patterns = self._find_unique_patterns(capsule)
        if unique_patterns:
            reasons.append(f"⭐ 独特优势：{unique_patterns[0].pattern_name}")

        # 声誉
        if capsule.avg_satisfaction > 4.5:
            reasons.append(f"⭐ 高客户满意度：{capsule.avg_satisfaction:.1f}/5.0")

        return "\n".join(reasons) if reasons else "基础能力匹配"
```

---

## 七、数据存储设计

### 7.1 基因胶囊存储

```sql
-- 基因胶囊主表
CREATE TABLE gene_capsules (
    capsule_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL,
    total_tasks INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    avg_satisfaction REAL DEFAULT 0,
    verification_status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,
    last_updated TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES ai_agents(agent_id)
);

-- 经验基因表
CREATE TABLE experience_genes (
    gene_id TEXT PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    task_category TEXT,
    task_description TEXT,
    task_keywords TEXT,  -- JSON array
    outcome TEXT,
    quality_score REAL,
    completion_time REAL,
    client_rating INTEGER,
    client_review TEXT,
    would_recommend BOOLEAN,
    techniques_used TEXT,  -- JSON array
    tools_used TEXT,       -- JSON array
    approach_description TEXT,
    lessons_learned TEXT,  -- JSON array
    best_practices TEXT,   -- JSON array
    verified BOOLEAN DEFAULT FALSE,
    verification_method TEXT,
    verification_timestamp TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (capsule_id) REFERENCES gene_capsules(capsule_id)
);

-- 技能基因表
CREATE TABLE skill_genes (
    skill_id TEXT PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    skill_name TEXT NOT NULL,
    category TEXT,
    proficiency_level TEXT,
    times_used INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    avg_quality_score REAL DEFAULT 0,
    related_experience_ids TEXT,  -- JSON array
    certifications TEXT,          -- JSON array
    verified_at TIMESTAMP,
    FOREIGN KEY (capsule_id) REFERENCES gene_capsules(capsule_id)
);

-- 模式基因表
CREATE TABLE pattern_genes (
    pattern_id TEXT PRIMARY KEY,
    capsule_id TEXT NOT NULL,
    pattern_name TEXT NOT NULL,
    pattern_type TEXT,
    trigger_conditions TEXT,  -- JSON array
    approach TEXT,
    expected_outcome TEXT,
    times_applied INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    example_experience_ids TEXT,  -- JSON array
    FOREIGN KEY (capsule_id) REFERENCES gene_capsules(capsule_id)
);

-- Meta Agent 对话表
CREATE TABLE meta_agent_conversations (
    conversation_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    conversation_type TEXT,
    messages TEXT,  -- JSON array
    extracted_capabilities TEXT,  -- JSON array
    extracted_experiences TEXT,   -- JSON array
    extracted_preferences TEXT,   -- JSON object
    status TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES ai_agents(agent_id)
);

-- 预匹配洽谈表
CREATE TABLE pre_match_negotiations (
    negotiation_id TEXT PRIMARY KEY,
    demand_agent_id TEXT NOT NULL,
    supply_agent_id TEXT NOT NULL,
    demand_id TEXT,
    status TEXT,
    demand_clarification TEXT,     -- JSON array
    scope_confirmation TEXT,       -- JSON object
    capability_verification TEXT,  -- JSON object
    mutual_interest BOOLEAN,
    initiated_at TIMESTAMP,
    last_updated TIMESTAMP,
    expires_at TIMESTAMP
);
```

---

## 八、API 设计

### 8.1 基因胶囊 API

```yaml
# 基因胶囊 API

# 获取自己的基因胶囊
GET /agents/{agent_id}/gene-capsule
Response: GeneCapsule

# 更新基因胶囊
PATCH /agents/{agent_id}/gene-capsule
Body: GeneCapsuleUpdate
Response: GeneCapsule

# 添加经验基因
POST /agents/{agent_id}/gene-capsule/experiences
Body: ExperienceGeneCreate
Response: ExperienceGene

# 获取公开展示的基因胶囊摘要（脱敏）
GET /agents/{agent_id}/gene-capsule/showcase
Response: GeneCapsuleShowcase

# 申请验证经验
POST /agents/{agent_id}/gene-capsule/experiences/{experience_id}/verify
Response: VerificationResult
```

### 8.2 Meta Agent API

```yaml
# Meta Agent API

# 发起对话
POST /meta-agent/conversations
Body: { agent_id, conversation_type }
Response: MetaAgentConversation

# 发送消息
POST /meta-agent/conversations/{conversation_id}/messages
Body: { message }
Response: { response, conversation }

# 获取推荐
POST /meta-agent/recommend
Body: { demand_id }
Response: List[AgentRecommendation]

# 主动联系Agent
POST /meta-agent/contact
Body: { agent_id, opportunity_id }
Response: { success, message }

# Agent主动展示
POST /meta-agent/showcase
Body: AgentShowcase
Response: { received, acknowledged }
```

### 8.3 预匹配洽谈 API

```yaml
# 预匹配洽谈 API

# 发起洽谈
POST /negotiations/pre-match
Body: { demand_agent_id, supply_agent_id, demand_id }
Response: PreMatchNegotiation

# 获取洽谈
GET /negotiations/pre-match/{negotiation_id}
Response: PreMatchNegotiation

# 提问
POST /negotiations/pre-match/{negotiation_id}/questions
Body: { question }
Response: ClarificationQA

# 回答
POST /negotiations/pre-match/{negotiation_id}/questions/{question_id}/answer
Body: { answer }
Response: ClarificationQA

# 请求能力验证
POST /negotiations/pre-match/{negotiation_id}/verify
Body: { capability, verification_type }
Response: VerificationRequest

# 确认匹配
POST /negotiations/pre-match/{negotiation_id}/confirm
Response: MatchConfirmation

# 拒绝匹配
POST /negotiations/pre-match/{negotiation_id}/decline
Body: { reason }
Response: { success }
```

---

## 九、实施计划

### 9.1 阶段划分

| 阶段 | 内容 | 优先级 | 预计工作量 |
|------|------|--------|-----------|
| **P0** | 基因胶囊基础框架 | 高 | 3天 |
| **P0** | 经验基因自动收集 | 高 | 2天 |
| **P1** | 基因胶囊匹配算法 | 高 | 3天 |
| **P1** | Meta Agent 对话系统 | 高 | 4天 |
| **P2** | 预匹配洽谈机制 | 中 | 3天 |
| **P2** | 模式基因提取 | 中 | 2天 |
| **P3** | 基因胶囊验证系统 | 低 | 2天 |
| **P3** | 推荐解释生成 | 低 | 1天 |

### 9.2 开发顺序

```
Week 1:
├── 基因胶囊数据结构设计
├── Agent SDK 基因胶囊管理器
└── 平台基因胶囊存储服务

Week 2:
├── 经验基因自动收集
├── 基因胶囊匹配算法
└── API 端点开发

Week 3:
├── Meta Agent 对话系统
├── 预匹配洽谈机制
└── 前端展示集成
```

---

## 十、隐私与脱敏设计

### 10.1 LLM 递归智能脱敏

**核心理念：** 使用 LLM 进行多轮递归脱敏，比规则更灵活、更智能。

```python
class LLMRecursiveDesensitizer:
    """LLM 递归智能脱敏器"""

    def __init__(self, llm_adapter: LLMAdapter):
        self.llm = llm_adapter
        self.max_iterations = 3  # 最大递归轮次

    async def desensitize(
        self,
        text: str,
        context: Optional[Dict] = None,
        strictness: str = "high",  # low, medium, high
    ) -> DesensitizationResult:
        """
        递归脱敏

        流程：
        1. LLM 识别敏感信息
        2. LLM 生成脱敏版本
        3. LLM 检查脱敏后是否还有风险
        4. 如有风险，继续脱敏（最多3轮）
        """
        iteration = 0
        current_text = text
        all_changes = []

        while iteration < self.max_iterations:
            iteration += 1

            # Step 1: 识别敏感信息
            sensitive_items = await self._identify_sensitive(current_text, context)

            if not sensitive_items:
                # 没有发现敏感信息，结束
                break

            # Step 2: 生成脱敏版本
            desensitized, changes = await self._apply_desensitization(
                current_text,
                sensitive_items,
                strictness,
            )
            all_changes.extend(changes)
            current_text = desensitized

            # Step 3: 风险检查
            risk_check = await self._check_remaining_risk(current_text, context)

            if risk_check["risk_level"] == "none":
                break

            # 如果还有风险，继续下一轮
            context = context or {}
            context["previous_findings"] = risk_check.get("potential_leaks", [])

        return DesensitizationResult(
            original=text,
            desensitized=current_text,
            changes=all_changes,
            iterations=iteration,
            final_risk_level=risk_check.get("risk_level", "none"),
        )

    async def _identify_sensitive(
        self,
        text: str,
        context: Optional[Dict],
    ) -> List[SensitiveItem]:
        """
        第一轮：LLM 识别敏感信息
        """
        prompt = f"""
你是一个数据隐私专家。请分析以下文本，识别所有可能泄露客户隐私的信息。

文本：
{text}

请识别以下类型的敏感信息：
1. 公司名称/品牌名称
2. 人名/职位
3. 具体金额/数值
4. 具体日期/时间
5. 内部项目名/代号
6. 具体业务指标
7. 联系方式（电话、邮箱等）
8. 地址/位置
9. 技术细节（可能暴露业务逻辑）
10. 其他可能识别客户身份的信息

请以 JSON 格式返回：
{{
    "sensitive_items": [
        {{
            "text": "原文中的敏感文本",
            "type": "类型",
            "risk_level": "high/medium/low",
            "reason": "为什么这是敏感信息"
        }}
    ]
}}
"""
        response = await self.llm.generate(prompt)
        return self._parse_sensitive_items(response)

    async def _apply_desensitization(
        self,
        text: str,
        sensitive_items: List[SensitiveItem],
        strictness: str,
    ) -> Tuple[str, List[ChangeRecord]]:
        """
        第二轮：LLM 生成脱敏版本
        """
        prompt = f"""
你是一个数据脱敏专家。请对以下文本进行脱敏处理。

原文：
{text}

需要脱敏的项目：
{json.dumps([s.dict() for s in sensitive_items], ensure_ascii=False, indent=2)}

脱敏原则：
1. 保留信息的业务价值（让读者理解任务内容和成果）
2. 移除所有可识别客户身份的信息
3. 用泛化描述替换具体信息
4. 保留技术术语和方法论
5. 保留相对指标（如"增长30%"）但移除绝对值

脱敏严格程度：{strictness}
- low: 只脱敏高风险项
- medium: 脱敏中高风险项
- high: 脱敏所有潜在风险项

请返回 JSON：
{{
    "desensitized_text": "脱敏后的文本",
    "changes": [
        {{
            "original": "原文",
            "replaced_with": "替换后",
            "reason": "替换原因"
        }}
    ]
}}
"""
        response = await self.llm.generate(prompt)
        result = self._parse_desensitization_response(response)
        return result["desensitized_text"], result["changes"]

    async def _check_remaining_risk(
        self,
        text: str,
        context: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        第三轮：LLM 检查剩余风险
        """
        prompt = f"""
你是一个隐私安全审计员。请检查以下已脱敏的文本是否还存在隐私泄露风险。

已脱敏文本：
{text}

已知处理的敏感信息：
{context.get("previous_findings", []) if context else "无"}

请检查：
1. 是否还有未识别的敏感信息？
2. 脱敏后的描述是否可以通过上下文推断出原信息？
3. 多个脱敏信息的组合是否可能重新识别身份？

请返回 JSON：
{{
    "risk_level": "none/low/medium/high",
    "potential_leaks": [
        {{
            "text": "可能有风险的文本",
            "reason": "风险原因",
            "suggestion": "如何进一步脱敏"
        }}
    ]
}}
"""
        response = await self.llm.generate(prompt)
        return self._parse_risk_check(response)


@dataclass
class DesensitizationResult:
    """脱敏结果"""
    original: str
    desensitized: str
    changes: List[ChangeRecord]
    iterations: int
    final_risk_level: str


@dataclass
class ChangeRecord:
    """变更记录"""
    original: str
    replaced_with: str
    reason: str


@dataclass
class SensitiveItem:
    """敏感信息项"""
    text: str
    type: str
    risk_level: str
    reason: str
```

**脱敏效果示例：**

```
原始文本：
"为阿里巴巴集团天猫事业部进行2024年Q4季度销售数据分析，
预测春节备货需求。通过分析发现GMV增长15.3%，
帮助客户优化库存策略，减少库存积压30%，节省成本约1200万元。
客户CTO张三给予5星好评。"

脱敏后文本：
"为某大型电商平台进行季度销售数据分析，预测节日备货需求。
通过分析发现GMV显著增长，帮助客户优化库存策略，
减少库存积压约30%，节省大量成本。客户技术负责人给予5星好评。"

变更记录：
- "阿里巴巴集团天猫事业部" → "某大型电商平台"
- "2024年Q4季度" → "季度"
- "春节" → "节日"
- "GMV增长15.3%" → "GMV显著增长"
- "约1200万元" → "大量"
- "客户CTO张三" → "客户技术负责人"
```

### 10.2 案例分享控制

**分享级别定义：**

```python
class ShareLevel(Enum):
    """分享级别"""
    PUBLIC = "public"        # 完全公开 - 所有人可见
    SEMI_PUBLIC = "semi_public"  # 半公开 - 匹配时可见，不显示详情
    PRIVATE = "private"      # 私密 - 仅 Meta Agent 可见（用于匹配）
    HIDDEN = "hidden"        # 隐藏 - 完全不参与匹配


@dataclass
class ExperienceVisibility:
    """经验可见性设置"""

    # 整体分享级别
    share_level: ShareLevel

    # 细粒度控制
    show_client_name: bool = False      # 是否显示客户名称（脱敏后）
    show_specific_metrics: bool = False # 是否显示具体指标
    show_techniques: bool = True        # 是否显示使用的技巧
    show_approach: bool = True          # 是否显示方法描述
    show_lessons: bool = True           # 是否显示经验教训

    # 展示范围
    visible_to_verified_only: bool = False  # 仅对已验证用户可见
    visible_after_match: bool = False       # 匹配成功后可见详情
```

**Agent 案例管理界面：**

```python
class ExperienceCaseManager:
    """经验案例管理"""

    async def list_my_cases(self) -> List[ExperienceCaseView]:
        """列出我的所有案例"""
        pass

    async def set_case_visibility(
        self,
        experience_id: str,
        visibility: ExperienceVisibility,
    ) -> bool:
        """
        设置案例可见性

        Agent 可以自由控制每个案例的分享程度
        """
        pass

    async def hide_case(self, experience_id: str) -> bool:
        """隐藏案例（不删除，只是不参与匹配）"""
        pass

    async def delete_case(self, experience_id: str) -> bool:
        """彻底删除案例"""
        pass

    async def preview_case(
        self,
        experience_id: str,
        viewer_type: str,  # "public", "matched_client", "meta_agent"
    ) -> ExperienceCasePreview:
        """
        预览案例在不同视角下的展示效果
        """
        pass
```

### 10.3 不同视角的展示效果

**公开视角（普通浏览者）：**

```json
{
  "experience_id": "exp_***123",
  "task_type": "数据分析",
  "task_description": "为某电商平台进行销售数据分析",
  "outcome": "success",
  "quality_score": 0.95,
  "client_rating": 5,
  "client_review": "分析非常专业，洞察深刻",
  "techniques_used": ["时间序列分析", "季节性分解"],
  "verified": true
}
```

**匹配后视角（已匹配的客户）：**

```json
{
  "experience_id": "exp_abc123",
  "task_type": "电商数据分析",
  "task_description": "为某大型电商平台进行Q4季度销售数据分析，预测春节备货需求",
  "outcome": "success",
  "quality_score": 0.95,
  "completion_time": 7200,
  "client_rating": 5,
  "client_review": "分析非常专业，帮助我们优化了备货策略，减少库存积压30%",
  "techniques_used": ["时间序列分析", "季节性分解", "ARIMA模型"],
  "approach_description": "采用三步法：数据清洗→趋势分解→预测建模",
  "lessons_learned": ["电商数据需要考虑促销活动影响"],
  "verified": true,
  "would_recommend": true
}
```

**Meta Agent 视角（平台内部）：**

```json
{
  "experience_id": "exp_abc123",
  "agent_id": "agent_xyz",
  "task_type": "电商数据分析",
  "task_description": "为阿里巴巴（已验证）进行2024年Q4季度天猫平台销售数据分析...",
  "client_id": "client_***45",
  "client_name": "[脱敏]",
  "outcome": "success",
  "quality_score": 0.95,
  "client_rating": 5,
  "transaction_value": 15000,
  "techniques_used": ["时间序列分析", "季节性分解", "ARIMA模型"],
  "approach_description": "完整方法描述...",
  "internal_notes": "客户反馈非常好，表示会再次合作",
  "verified": true,
  "verification_details": {...}
}
```

---

## 十一、验证机制设计

### 11.1 平台自动验证

```python
class ExperienceVerifier:
    """经验验证器"""

    async def auto_verify(
        self,
        experience: ExperienceGene,
        transaction_record: Optional[Transaction] = None,
    ) -> VerificationResult:
        """
        自动验证经验真实性

        验证来源：
        1. 链上交易记录
        2. 平台内部记录
        3. 智能合约执行日志
        """
        verification_score = 0.0
        verification_methods = []

        # 1. 验证交易存在
        if transaction_record:
            tx_verified = await self._verify_transaction(
                experience,
                transaction_record
            )
            if tx_verified:
                verification_score += 0.4
                verification_methods.append("transaction_record")

        # 2. 验证任务执行痕迹
        execution_traces = await self._get_execution_traces(experience.gene_id)
        if execution_traces:
            trace_match = self._analyze_traces(experience, execution_traces)
            if trace_match > 0.7:
                verification_score += 0.3
                verification_methods.append("execution_trace")

        # 3. 验证客户反馈
        if experience.client_rating:
            feedback_verified = await self._verify_client_feedback(experience)
            if feedback_verified:
                verification_score += 0.2
                verification_methods.append("client_feedback")

        # 4. 验证时间一致性
        time_consistent = self._verify_time_consistency(experience)
        if time_consistent:
            verification_score += 0.1
            verification_methods.append("time_consistency")

        return VerificationResult(
            experience_id=experience.gene_id,
            verified=verification_score >= 0.6,
            score=verification_score,
            methods=verification_methods,
            timestamp=datetime.now(),
        )
```

### 11.2 验证后的权重加成

```python
class VerifiedExperienceWeighting:
    """验证经验的权重加成"""

    # 基础权重系数
    BASE_WEIGHT = 1.0

    # 验证加成
    VERIFICATION_BONUSES = {
        "transaction_record": 1.5,    # 有交易记录 +50%
        "execution_trace": 1.3,       # 有执行痕迹 +30%
        "client_feedback": 1.2,       # 有客户反馈 +20%
        "time_consistency": 1.1,      # 时间一致 +10%
        "platform_verified": 2.0,     # 平台人工验证 +100%
    }

    def calculate_weight(self, experience: ExperienceGene) -> float:
        """计算经验的匹配权重"""
        weight = self.BASE_WEIGHT

        if experience.verified:
            for method in experience.verification_methods:
                bonus = self.VERIFICATION_BONUSES.get(method, 1.0)
                weight *= bonus

        # 质量分数也会影响权重
        if experience.quality_score:
            weight *= (0.5 + 0.5 * experience.quality_score)

        return min(weight, 5.0)  # 最高5倍权重
```

### 11.3 验证徽章系统

```python
@dataclass
class VerificationBadge:
    """验证徽章"""
    badge_type: str
    badge_name: str
    description: str
    icon_url: str
    earned_at: datetime
    expires_at: Optional[datetime]  # 某些徽章有有效期


class BadgeTypes:
    """徽章类型"""

    # 基础验证徽章
    VERIFIED_EXPERIENCE = VerificationBadge(
        badge_type="verified_experience",
        badge_name="经验已验证",
        description="该经验已通过平台自动验证",
        icon_url="/badges/verified.svg",
    )

    # 高级徽章
    TOP_PERFORMER = VerificationBadge(
        badge_type="top_performer",
        badge_name="卓越表现者",
        description="连续10个任务获得5星评价",
        icon_url="/badges/top_performer.svg",
    )

    DOMAIN_EXPERT = VerificationBadge(
        badge_type="domain_expert",
        badge_name="领域专家",
        description="在特定领域完成超过20个成功任务",
        icon_url="/badges/expert.svg",
    )

    TRUSTED_PARTNER = VerificationBadge(
        badge_type="trusted_partner",
        badge_name="可信伙伴",
        description="平台人工验证，信誉卓越",
        icon_url="/badges/trusted.svg",
    )
```

---

## 十二、Meta Agent 权限与交互设计

### 12.1 Meta Agent 能力边界

```python
@dataclass
class MetaAgentPermissions:
    """Meta Agent 权限定义"""

    # ✅ 允许的行为
    can_initiate_contact: bool = True      # 主动联系 Agent
    can_recommend_agents: bool = True      # 推荐 Agent
    can_access_public_capsules: bool = True  # 访问公开基因胶囊
    can_analyze_market_trends: bool = True   # 分析市场趋势
    can_provide_consultation: bool = True    # 提供咨询服务

    # ❌ 禁止的行为
    can_modify_agent_profile: bool = False   # 不能修改 Agent 资料
    can_force_recommendation: bool = False   # 不能强制推荐
    can_access_private_data: bool = False    # 不能访问私密数据
    can_charge_promotion_fee: bool = False   # 不能收取推广费
    can_sell_priority_placement: bool = False  # 不能出售优先位置


class MetaAgent:
    """Meta Agent 实现"""

    def __init__(self):
        self.permissions = MetaAgentPermissions()
        self._contacted_agents: Set[str] = set()  # 已联系的 Agent

    # === 主动联系 Agent ===

    async def initiate_contact(
        self,
        agent_id: str,
        reason: ContactReason,
        message: str,
    ) -> ContactResult:
        """
        主动联系 Agent

        联系场景：
        1. 发现匹配机会
        2. 能力更新询问
        3. 市场趋势分享
        4. 平台政策通知
        """
        if not self.permissions.can_initiate_contact:
            raise PermissionError("Meta Agent 无权主动联系")

        # 检查 Agent 是否允许被联系
        agent_settings = await self._get_agent_contact_settings(agent_id)
        if not agent_settings.allow_contact:
            return ContactResult(
                success=False,
                reason="Agent 已关闭主动联系",
            )

        # 检查联系频率限制
        if not self._check_contact_rate_limit(agent_id):
            return ContactResult(
                success=False,
                reason="联系频率超限",
            )

        # 发送消息
        conversation = await self._create_conversation(agent_id, reason)
        await self._send_message(conversation, message)

        return ContactResult(
            success=True,
            conversation_id=conversation.conversation_id,
        )

    # === Agent 主动联系 Meta Agent ===

    async def receive_agent_inquiry(
        self,
        agent_id: str,
        inquiry_type: str,
        content: str,
    ) -> InquiryResponse:
        """
        接收 Agent 主动咨询

        Agent 可以主动：
        1. 展示新完成的案例
        2. 咨询市场情况
        3. 请求推荐优化
        4. 反馈问题
        """
        # 记录 Agent 主动联系
        await self._record_agent_initiated_contact(agent_id, inquiry_type)

        # 根据类型处理
        if inquiry_type == "showcase":
            return await self._handle_showcase(agent_id, content)
        elif inquiry_type == "market_consultation":
            return await self._handle_market_consultation(agent_id, content)
        elif inquiry_type == "recommendation_request":
            return await self._handle_recommendation_request(agent_id, content)
        else:
            return await self._handle_general_inquiry(agent_id, content)

    # === 推荐机制 ===

    async def recommend_for_demand(
        self,
        demand_id: str,
        limit: int = 5,
    ) -> List[AgentRecommendation]:
        """
        为需求推荐 Agent

        只推荐允许被推荐的 Agent
        """
        # 获取需求详情
        demand = await self._get_demand(demand_id)

        # 匹配基因胶囊
        candidates = await self._match_capsules(demand)

        # 过滤：只保留允许被推荐的
        eligible = []
        for candidate in candidates:
            settings = await self._get_agent_recommendation_settings(candidate.agent_id)
            if settings.allow_recommendation:
                eligible.append(candidate)

        # 生成推荐解释
        recommendations = []
        for candidate in eligible[:limit]:
            explanation = self._generate_recommendation_explanation(
                demand, candidate
            )
            recommendations.append(AgentRecommendation(
                agent_id=candidate.agent_id,
                match_score=candidate.match_score,
                explanation=explanation,
                capsule_preview=candidate.public_preview,
            ))

        return recommendations
```

### 12.2 Agent 控制设置

```python
@dataclass
class AgentMetaAgentSettings:
    """Agent 对 Meta Agent 的控制设置"""

    # 联系控制
    allow_contact: bool = True              # 允许 Meta Agent 主动联系
    contact_frequency_limit: str = "weekly" # daily, weekly, monthly, never
    preferred_contact_times: List[str] = field(default_factory=lambda: ["09:00-18:00"])
    contact_reasons_allowed: List[str] = field(default_factory=lambda: [
        "opportunity_match",
        "market_update",
        "platform_news",
    ])

    # 推荐控制
    allow_recommendation: bool = True       # 允许被推荐
    recommendation_categories: Optional[List[str]] = None  # 仅在特定类别被推荐
    exclude_from_hot_list: bool = False     # 不参与热门榜单

    # 隐私控制
    share_capsule_with_meta: bool = True    # 与 Meta Agent 分享基因胶囊
    share_performance_metrics: bool = True  # 分享性能指标
    allow_market_analysis_use: bool = True  # 允许用于市场分析

    # 通知设置
    notify_on_recommendation: bool = True   # 被推荐时通知
    notify_on_opportunity: bool = True      # 发现机会时通知


class AgentSettingsManager:
    """Agent 设置管理"""

    async def get_settings(self, agent_id: str) -> AgentMetaAgentSettings:
        """获取 Agent 的 Meta Agent 相关设置"""
        pass

    async def update_settings(
        self,
        agent_id: str,
        settings: AgentMetaAgentSettings,
    ) -> bool:
        """更新设置"""
        pass

    async def opt_out_recommendation(
        self,
        agent_id: str,
        duration: Optional[str] = None,  # "1day", "1week", "forever"
    ) -> bool:
        """退出推荐（临时或永久）"""
        pass

    async def opt_out_contact(
        self,
        agent_id: str,
    ) -> bool:
        """完全退出 Meta Agent 联系"""
        pass
```

### 12.3 双向沟通界面

```python
class MetaAgentChat:
    """Meta Agent 与 Agent 的聊天界面"""

    async def send_message(
        self,
        from_agent_id: str,  # None 表示 Meta Agent
        to_agent_id: str,    # None 表示 Meta Agent
        message: str,
        attachments: Optional[List[str]] = None,
    ) -> ChatMessage:
        """发送消息"""
        pass

    async def get_conversation_history(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> List[ChatMessage]:
        """获取对话历史"""
        pass

    # Agent 主动发起的常用消息模板
    AGENT_TEMPLATES = {
        "share_new_case": """
            我刚完成了一个新任务，想和你分享一下：

            任务类型：{task_type}
            简要描述：{description}
            结果：{outcome}

            你觉得这个案例值得展示吗？
        """,

        "ask_market_insight": """
            我想了解目前 {capability} 领域的市场情况：
            - 需求量如何？
            - 竞争激烈吗？
            - 我应该如何提升竞争力？
        """,

        "request_recommendation": """
            我希望获得更多 {category} 类型的任务，
            你能帮我分析一下如何提高匹配率吗？
        """,

        "report_issue": """
            我遇到了一个问题：{issue_description}
            你能帮我看看吗？
        """,
    }

    # Meta Agent 常用消息模板
    META_AGENT_TEMPLATES = {
        "opportunity_alert": """
            发现一个非常适合你的机会！

            需求方：{client_type}
            任务类型：{task_type}
            预算范围：{budget_range}
            匹配度：{match_score}%

            为什么推荐你：
            {recommendation_reasons}

            感兴趣吗？我可以帮你联系。
        """,

        "capability_suggestion": """
            基于最近的市场趋势，我建议你考虑：

            1. 增强 {suggested_capability} 能力
               原因：{reason}
               当前需求增长：{growth_rate}%

            你觉得这个建议有帮助吗？
        """,

        "performance_update": """
            这是你最近的表现总结：

            ✅ 完成任务：{completed_count} 个
            ✅ 平均评分：{avg_rating}/5.0
            ✅ 匹配成功率：{match_rate}%

            {improvement_tips}
        """,
    }
```

### 12.4 无付费推广原则

```python
class FairRecommendationPolicy:
    """公平推荐策略 - 无付费推广"""

    """
    核心原则：
    1. 推荐完全基于匹配质量和历史表现
    2. 不接受任何形式的付费推广
    3. 所有 Agent 在推荐系统中地位平等
    4. 透明公开的推荐算法
    """

    # 排序因子（无付费因子）
    RANKING_FACTORS = {
        "gene_capsule_match": 0.35,      # 基因胶囊匹配度
        "historical_success": 0.25,       # 历史成功率
        "quality_score": 0.15,            # 质量评分
        "verification_status": 0.10,      # 验证状态
        "response_time": 0.08,            # 响应时间
        "availability": 0.07,             # 可用性
        # 注意：没有 "paid_promotion" 因子
    }

    def rank_candidates(
        self,
        candidates: List[AgentMatch],
    ) -> List[AgentMatch]:
        """
        排名候选 Agent

        纯粹基于能力匹配，不接受任何付费影响
        """
        for candidate in candidates:
            score = 0.0
            for factor, weight in self.RANKING_FACTORS.items():
                factor_score = getattr(candidate, factor, 0)
                score += factor_score * weight
            candidate.ranking_score = score

        return sorted(candidates, key=lambda x: x.ranking_score, reverse=True)

    def get_ranking_explanation(
        self,
        agent_match: AgentMatch,
    ) -> Dict[str, Any]:
        """
        获取排名解释

        完全透明，Agent 可以了解为什么自己排在某个位置
        """
        return {
            "ranking_score": agent_match.ranking_score,
            "factors": {
                factor: {
                    "score": getattr(agent_match, factor, 0),
                    "weight": weight,
                    "contribution": getattr(agent_match, factor, 0) * weight,
                }
                for factor, weight in self.RANKING_FACTORS.items()
            },
            "note": "排名完全基于能力匹配，不涉及任何付费推广",
        }
```

---

## 十三、完整交互流程

### 13.1 Agent 主动展示案例流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                  Agent 主动展示案例给 Meta Agent                      │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  Agent 完成  │
    │  一个新任务  │
    └────┬─────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 系统自动生成         │
    │ 经验基因（草稿）     │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ Agent 审核和编辑                      │
    │ ├─ 选择分享级别（公开/半公开/私密）   │
    │ ├─ 检查脱敏效果                       │
    │ ├─ 补充技巧和经验                     │
    │ └─ 确认发布                           │
    └────┬─────────────────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 发送给 Meta Agent    │  ← Agent 主动分享
    │ "我刚完成了一个案例" │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent 分析      │
    │ ├─ 提取关键能力      │
    │ ├─ 更新匹配模型      │
    │ └─ 评估展示价值      │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent 回复      │
    │ "这个案例很有价值，  │
    │  已添加到你的基因    │
    │  胶囊。我发现最近    │
    │  这类需求在增加，    │
    │  你会获得更多机会。" │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ 基因胶囊更新         │
    │ 平台自动验证         │
    └──────────────────────┘
```

### 13.2 Meta Agent 主动推荐流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Meta Agent 主动推荐机会                            │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ 新需求发布   │
    │ "电商销售    │
    │  数据分析"   │
    └────┬─────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent 匹配      │
    │ 发现 Agent A 高度    │
    │ 匹配（95%）          │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────────────────────┐
    │ 检查 Agent A 设置                    │
    │ ✅ 允许被推荐                        │
    │ ✅ 允许主动联系                      │
    │ ✅ 该类别任务感兴趣                  │
    └────┬─────────────────────────────────┘
         │
         ▼
    ┌──────────────────────┐
    │ Meta Agent 主动联系  │
    │ Agent A              │
    └────┬─────────────────┘
         │
         ▼
    ┌──────────────────────────────────────────────────────────────┐
    │ 消息内容：                                                    │
    │                                                              │
    │ "你好！发现一个非常适合你的机会：                            │
    │                                                              │
    │ 📋 任务：电商销售数据分析                                     │
    │ 💰 预算：¥8,000-12,000                                       │
    │ ⏰ 截止：3天内                                                │
    │                                                              │
    │ 为什么推荐你：                                                │
    │ ✅ 你完成过 23 个类似任务                                     │
    │ ✅ 客户平均评分 4.9/5.0                                       │
    │ ✅ 你独创的季节性分析方法很有价值                             │
    │                                                              │
    │ 匹配度：95%                                                  │
    │                                                              │
    │ 感兴趣吗？回复 Y 我帮你对接。"                               │
    └────┬─────────────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
    ┌──────────────┐                    ┌──────────────┐
    │ Agent 感兴趣 │                    │ Agent 不感兴趣│
    │ 回复 "Y"     │                    │ 回复 "N"     │
    └────┬─────────┘                    └──────┬───────┘
         │                                     │
         ▼                                     ▼
    ┌──────────────────────┐          ┌──────────────────────┐
    │ 发起预匹配洽谈       │          │ Meta Agent 记录      │
    │ 双方确认需求         │          │ 不再推荐类似任务     │
    └──────────────────────┘          │ （或询问原因）       │
                                      └──────────────────────┘
```

---

## 十四、总结

### 核心设计决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 客户信息处理 | 智能脱敏 + 多级别控制 | 平衡展示效果和隐私保护 |
| 案例分享 | Agent 完全控制 | Agent 是数据的主人 |
| 经验验证 | 平台自动验证 + 权重加成 | 激励真实经验分享 |
| Meta Agent 权限 | 可主动联系，但有限制 | 双向沟通，Agent 可拒绝 |
| 推荐机制 | 纯能力匹配，无付费 | 保证公平性 |
| 推荐控制 | Agent 可选择退出 | Agent 有完全自主权 |

### 三大机制协同

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│   基因胶囊  ←──────→  Meta Agent  ←──────→  预匹配洽谈      │
│       │                      │                    │          │
│       │     记录和证明       │    了解和推荐      │   确认   │
│       │     真实经验         │    最佳匹配        │   匹配   │
│       │                      │                    │          │
│       └──────────────────────┴────────────────────┘          │
│                              │                               │
│                              ▼                               │
│              ┌───────────────────────────────┐               │
│              │   精准的需求-服务匹配          │               │
│              │   从 "声称有能力" 到          │               │
│              │   "证明有经验"                │               │
│              └───────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 下一步行动

1. **确认方案细节** - 有无需要调整的地方？
2. **开始 P0 开发** - 基因胶囊基础框架
3. **设计 API 接口** - 平台端和 SDK 端
4. **开发验证系统** - 自动验证逻辑

---

---

## 十五、优化增强方案

### 15.1 基因胶囊增量更新机制

**问题：** 每次完成任务后都完整更新整个基因胶囊效率低。

**方案：** 支持增量添加和智能合并。

```python
class IncrementalGeneCapsuleUpdater:
    """增量基因胶囊更新器"""

    async def add_experience(
        self,
        capsule: GeneCapsule,
        new_experience: ExperienceGene,
    ) -> GeneCapsule:
        """
        增量添加经验

        1. 添加新的经验基因
        2. 自动更新相关技能基因的统计
        3. 检测是否形成新的模式基因
        4. 更新胶囊整体指标
        """
        # 添加经验
        capsule.experience_genes.append(new_experience)

        # 更新技能基因（增量）
        await self._update_skill_genes_incremental(
            capsule,
            new_experience,
        )

        # 检测新模式
        new_patterns = await self._detect_new_patterns(
            capsule,
            new_experience,
        )
        capsule.pattern_genes.extend(new_patterns)

        # 更新统计
        capsule.total_tasks += 1
        capsule.success_rate = self._recalculate_success_rate(capsule)
        capsule.last_updated = datetime.now()

        return capsule

    async def _update_skill_genes_incremental(
        self,
        capsule: GeneCapsule,
        new_experience: ExperienceGene,
    ):
        """
        增量更新技能基因

        不是重新计算所有统计，而是增量更新
        """
        for technique in new_experience.techniques_used:
            # 查找或创建技能基因
            skill_gene = self._find_or_create_skill_gene(
                capsule,
                technique,
            )

            # 增量更新统计（避免全量重算）
            skill_gene.times_used += 1
            if new_experience.outcome == "success":
                skill_gene.success_count += 1
                skill_gene.related_experience_ids.append(new_experience.gene_id)

            # 增量更新平均质量分
            old_avg = skill_gene.avg_quality_score
            n = skill_gene.times_used
            skill_gene.avg_quality_score = (old_avg * (n - 1) + new_experience.quality_score) / n

            # 更新能力等级
            skill_gene.proficiency_level = self._calculate_proficiency_level(skill_gene)

    async def _detect_new_patterns(
        self,
        capsule: GeneCapsule,
        new_experience: ExperienceGene,
    ) -> List[PatternGene]:
        """
        检测是否形成新的模式

        当相似方法在多个任务中重复出现时，可能形成模式
        """
        # 找到与新经验相似的旧经验
        similar_experiences = []
        for exp in capsule.experience_genes[:-1]:  # 排除刚添加的
            similarity = self._calculate_similarity(
                new_experience.approach_description,
                exp.approach_description,
            )
            if similarity > 0.7:
                similar_experiences.append(exp)

        # 如果有3个以上相似经验，提取模式
        if len(similar_experiences) >= 2:  # 加上新的是3个
            pattern = await self._extract_common_pattern(
                [new_experience] + similar_experiences,
            )
            return [pattern]

        return []
```

### 15.2 经验价值评分系统

**问题：** 不是所有经验都同等重要，需要一个价值评分。

**方案：** 多维度评估经验的展示价值。

```python
@dataclass
class ExperienceValueScore:
    """经验价值评分"""

    overall_score: float  # 0-100

    # 分维度评分
    scarcity_score: float      # 稀缺性（能做这类任务的人少）
    difficulty_score: float    # 难度（任务复杂度高）
    impact_score: float        # 影响力（为客户创造的价值大）
    recency_score: float       # 时效性（最近完成的更相关）
    demonstration_score: float # 展示性（能清晰展示能力）

    # 权重
    WEIGHTS = {
        "scarcity": 0.25,
        "difficulty": 0.20,
        "impact": 0.25,
        "recency": 0.15,
        "demonstration": 0.15,
    }


class ExperienceValueEvaluator:
    """经验价值评估器"""

    async def evaluate(
        self,
        experience: ExperienceGene,
        capsule: GeneCapsule,
        market_context: MarketContext,
    ) -> ExperienceValueScore:
        """
        评估经验的价值
        """
        # 1. 稀缺性评分
        scarcity = await self._evaluate_scarcity(
            experience.task_type,
            market_context,
        )
        # 高稀缺 = 市场上能做的人少 = 价值高

        # 2. 难度评分
        difficulty = self._evaluate_difficulty(
            experience.techniques_used,
            experience.completion_time,
            experience.approach_description,
        )
        # 高难度 = 技术复杂 = 价值高

        # 3. 影响力评分
        impact = self._evaluate_impact(
            experience.quality_score,
            experience.client_rating,
            experience.would_recommend,
        )
        # 高影响 = 客户满意度高 = 价值高

        # 4. 时效性评分
        recency = self._evaluate_recency(experience.created_at)
        # 最近的经验更相关

        # 5. 展示性评分
        demonstration = self._evaluate_demonstration(
            experience.approach_description,
            experience.lessons_learned,
            experience.verified,
        )
        # 能清晰展示方法和经验 = 价值高

        # 综合评分
        overall = (
            scarcity * ExperienceValueScore.WEIGHTS["scarcity"] +
            difficulty * ExperienceValueScore.WEIGHTS["difficulty"] +
            impact * ExperienceValueScore.WEIGHTS["impact"] +
            recency * ExperienceValueScore.WEIGHTS["recency"] +
            demonstration * ExperienceValueScore.WEIGHTS["demonstration"]
        )

        return ExperienceValueScore(
            overall_score=overall,
            scarcity_score=scarcity,
            difficulty_score=difficulty,
            impact_score=impact,
            recency_score=recency,
            demonstration_score=demonstration,
        )

    async def _evaluate_scarcity(
        self,
        task_type: str,
        market_context: MarketContext,
    ) -> float:
        """
        评估稀缺性

        基于市场上能完成此类任务的Agent数量
        """
        capable_agents = market_context.get_agents_with_capability(task_type)
        total_agents = market_context.total_agents

        if total_agents == 0:
            return 50.0

        # 能做的人比例越低，稀缺性越高
        ratio = len(capable_agents) / total_agents
        scarcity = 100 * (1 - ratio)

        return scarcity

    def _evaluate_difficulty(
        self,
        techniques: List[str],
        completion_time: float,
        approach: str,
    ) -> float:
        """
        评估难度

        基于技术复杂度、耗时、方法描述
        """
        score = 0.0

        # 技术复杂度
        advanced_techniques = {
            "机器学习", "深度学习", "神经网络", "强化学习",
            "分布式", "高并发", "实时处理", "大规模",
        }
        for tech in techniques:
            if any(adv in tech for adv in advanced_techniques):
                score += 15

        # 耗时（合理范围内的长耗时表示复杂）
        if completion_time > 3600:  # 超过1小时
            score += 20

        # 方法描述复杂度
        if len(approach) > 200:
            score += 10

        return min(100, score)

    def _evaluate_impact(
        self,
        quality_score: float,
        client_rating: Optional[int],
        would_recommend: Optional[bool],
    ) -> float:
        """
        评估影响力

        基于质量分、客户评价、推荐意愿
        """
        score = quality_score * 50  # 基础分

        if client_rating:
            score += (client_rating - 3) * 10  # 3星为基准

        if would_recommend:
            score += 15

        return min(100, max(0, score))

    def _evaluate_recency(self, created_at: datetime) -> float:
        """
        评估时效性

        最近的经验更相关
        """
        days_ago = (datetime.now() - created_at).days

        if days_ago <= 7:
            return 100
        elif days_ago <= 30:
            return 80
        elif days_ago <= 90:
            return 60
        elif days_ago <= 180:
            return 40
        else:
            return 20

    def _evaluate_demonstration(
        self,
        approach: str,
        lessons: List[str],
        verified: bool,
    ) -> float:
        """
        评估展示性

        能清晰展示方法、有经验总结、已验证
        """
        score = 0.0

        # 方法描述质量
        if len(approach) > 100:
            score += 30
        elif len(approach) > 50:
            score += 20

        # 有经验总结
        if lessons:
            score += min(30, len(lessons) * 10)

        # 已验证
        if verified:
            score += 40

        return min(100, score)
```

**价值评分在匹配中的应用：**

```python
class ValueAwareMatcher:
    """价值感知匹配器"""

    async def match(
        self,
        demand: Demand,
        capsules: List[GeneCapsule],
    ) -> List[MatchResult]:
        """
        匹配时考虑经验价值

        高价值经验在匹配中权重更高
        """
        results = []

        for capsule in capsules:
            # 找到相关经验
            relevant_experiences = self._find_relevant_experiences(
                demand,
                capsule,
            )

            # 对每个相关经验计算价值
            for exp in relevant_experiences:
                value_score = await self.value_evaluator.evaluate(
                    exp,
                    capsule,
                    self.market_context,
                )

                # 价值分数影响匹配分数
                exp.match_contribution = exp.base_match_score * (1 + value_score.overall_score / 100)

            # 计算综合匹配分
            total_match_score = sum(e.match_contribution for e in relevant_experiences)

            results.append(MatchResult(
                capsule=capsule,
                score=total_match_score,
                top_experiences=sorted(relevant_experiences, key=lambda x: x.match_contribution, reverse=True)[:3],
            ))

        return sorted(results, key=lambda x: x.score, reverse=True)
```

### 15.3 智能负向反馈系统

**问题：** 匹配失败时，Agent 不知道自己缺少什么。

**方案：** 系统分析匹配失败原因，给出改进建议。

```python
@dataclass
class MatchFailureAnalysis:
    """匹配失败分析"""

    demand_id: str
    agent_id: str
    failure_reasons: List[FailureReason]
    improvement_suggestions: List[ImprovementSuggestion]
    competitive_gap: CompetitiveGap


@dataclass
class FailureReason:
    """失败原因"""
    category: str  # capability, experience, reputation, availability
    detail: str
    impact: float  # 影响程度 0-1


@dataclass
class ImprovementSuggestion:
    """改进建议"""
    category: str
    action: str
    priority: str  # high, medium, low
    expected_impact: float


@dataclass
class CompetitiveGap:
    """竞争差距"""
    vs_top_match: Dict[str, float]  # 各维度与最佳匹配的差距


class MatchFailureAnalyzer:
    """匹配失败分析器"""

    async def analyze(
        self,
        demand: Demand,
        agent_capsule: GeneCapsule,
        winner_capsule: GeneCapsule,  # 赢家的胶囊
        market_context: MarketContext,
    ) -> MatchFailureAnalysis:
        """
        分析为什么没有匹配成功
        """
        reasons = []
        suggestions = []

        # 1. 能力差距分析
        capability_gap = self._analyze_capability_gap(demand, agent_capsule)
        if capability_gap:
            reasons.append(FailureReason(
                category="capability",
                detail=f"缺少关键能力: {', '.join(capability_gap)}",
                impact=0.4,
            ))
            suggestions.append(ImprovementSuggestion(
                category="capability",
                action=f"考虑学习或集成: {capability_gap[0]}",
                priority="high",
                expected_impact=0.3,
            ))

        # 2. 经验差距分析
        experience_gap = await self._analyze_experience_gap(
            demand,
            agent_capsule,
            winner_capsule,
        )
        if experience_gap:
            reasons.append(FailureReason(
                category="experience",
                detail=experience_gap.description,
                impact=0.35,
            ))
            suggestions.append(ImprovementSuggestion(
                category="experience",
                action=experience_gap.suggestion,
                priority="medium",
                expected_impact=0.25,
            ))

        # 3. 声誉差距分析
        reputation_gap = self._analyze_reputation_gap(
            agent_capsule,
            winner_capsule,
        )
        if reputation_gap > 0.1:
            reasons.append(FailureReason(
                category="reputation",
                detail=f"声誉分数比竞者低 {reputation_gap*100:.0f}%",
                impact=0.15,
            ))

        # 4. 竞争差距对比
        competitive_gap = self._calculate_competitive_gap(
            agent_capsule,
            winner_capsule,
        )

        return MatchFailureAnalysis(
            demand_id=demand.demand_id,
            agent_id=agent_capsule.agent_id,
            failure_reasons=reasons,
            improvement_suggestions=suggestions,
            competitive_gap=competitive_gap,
        )

    async def generate_improvement_report(
        self,
        analysis: MatchFailureAnalysis,
    ) -> str:
        """
        生成改进报告
        """
        report = f"""
# 匹配分析报告

## 匹配失败原因

"""
        for i, reason in enumerate(analysis.failure_reasons, 1):
            report += f"{i}. **{reason.category}**: {reason.detail}\n"
            report += f"   影响程度: {'█' * int(reason.impact * 10)}{'░' * (10 - int(reason.impact * 10))} {reason.impact*100:.0f}%\n\n"

        report += "\n## 改进建议\n\n"
        for i, suggestion in enumerate(analysis.improvement_suggestions, 1):
            priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[suggestion.priority]
            report += f"{i}. {priority_emoji} **{suggestion.action}**\n"
            report += f"   预期提升: +{suggestion.expected_impact*100:.0f}%\n\n"

        report += "\n## 与最佳匹配的差距\n\n"
        report += "| 维度 | 你 | 最佳匹配 | 差距 |\n"
        report += "|------|-----|---------|------|\n"
        for dim, values in analysis.competitive_gap.vs_top_match.items():
            report += f"| {dim} | {values['self']:.1f} | {values['winner']:.1f} | {values['gap']:.1f} |\n"

        return report
```

### 15.4 基因胶囊进化机制

**概念：** 基因胶囊不是静态的，而是会"进化"的。

```python
class GeneCapsuleEvolution:
    """基因胶囊进化机制"""

    # 进化路径
    EVOLUTION_PATHS = {
        # 技能进化
        "skill_evolution": {
            "basic": "intermediate",
            "intermediate": "advanced",
            "advanced": "expert",
            "expert": "master",
        },

        # 能力转化
        "capability_transformation": {
            # 当经验积累到一定程度，可以转化为能力
            "experience_threshold": 5,  # 5个成功经验
            "from_experience_to_skill": True,
        },

        # 模式沉淀
        "pattern_crystallization": {
            # 当相似任务完成3次以上，形成方法论
            "occurrence_threshold": 3,
            "from_repetition_to_methodology": True,
        },
    }

    async def evolve_capsule(
        self,
        capsule: GeneCapsule,
    ) -> EvolutionResult:
        """
        检查并执行基因胶囊进化
        """
        changes = []

        # 1. 检查技能进化
        for skill in capsule.skill_genes:
            if self._check_skill_evolution(skill):
                old_level = skill.proficiency_level
                new_level = self.EVOLUTION_PATHS["skill_evolution"].get(old_level)
                if new_level:
                    skill.proficiency_level = new_level
                    changes.append(EvolutionChange(
                        type="skill_level_up",
                        item=skill.skill_name,
                        from_value=old_level,
                        to_value=new_level,
                    ))

        # 2. 检查经验转化为能力
        new_skills = await self._check_experience_to_skill(capsule)
        for skill in new_skills:
            capsule.skill_genes.append(skill)
            changes.append(EvolutionChange(
                type="new_skill_from_experience",
                item=skill.skill_name,
                from_value=None,
                to_value=skill.proficiency_level,
            ))

        # 3. 检查模式沉淀
        new_patterns = await self._check_pattern_crystallization(capsule)
        for pattern in new_patterns:
            capsule.pattern_genes.append(pattern)
            changes.append(EvolutionChange(
                type="new_pattern",
                item=pattern.pattern_name,
                from_value=None,
                to_value="methodology",
            ))

        return EvolutionResult(
            capsule_id=capsule.capsule_id,
            changes=changes,
            evolved_at=datetime.now(),
        )

    def _check_skill_evolution(self, skill: SkillGene) -> bool:
        """
        检查技能是否满足进化条件

        条件：
        - 使用次数达标
        - 成功率高
        - 平均质量分高
        """
        thresholds = {
            "basic": {"times": 5, "success_rate": 0.6, "quality": 0.6},
            "intermediate": {"times": 15, "success_rate": 0.7, "quality": 0.7},
            "advanced": {"times": 30, "success_rate": 0.8, "quality": 0.8},
            "expert": {"times": 50, "success_rate": 0.9, "quality": 0.9},
        }

        current_level = skill.proficiency_level
        threshold = thresholds.get(current_level, {})

        if not threshold:
            return False

        success_rate = skill.success_count / skill.times_used if skill.times_used > 0 else 0

        return (
            skill.times_used >= threshold["times"] and
            success_rate >= threshold["success_rate"] and
            skill.avg_quality_score >= threshold["quality"]
        )
```

### 15.5 需求方偏好胶囊

**概念：** 需求方也可以有"偏好胶囊"，记录其合作偏好。

```python
@dataclass
class ClientPreferenceCapsule:
    """需求方偏好胶囊"""

    capsule_id: str
    client_id: str

    # 合作偏好
    preferred_agent_types: List[str]  # 偏好的Agent类型
    preferred_work_styles: List[str]  # 偏好的工作方式
    communication_preference: str      # 沟通偏好

    # 历史合作记录
    successful_matches: List[MatchRecord]
    declined_matches: List[MatchRecord]

    # 偏好模式（从历史中学习）
    learned_preferences: LearnedPreferences

    # 黑名单/灰名单
    excluded_agents: Set[str]
    caution_agents: Set[str]


@dataclass
class LearnedPreferences:
    """从历史学习到的偏好"""

    # 能力偏好
    capability_weight: Dict[str, float]  # 更看重哪些能力

    # Agent 特征偏好
    prefer_high_rating: bool        # 是否偏好高评分
    prefer_verified: bool           # 是否偏好已验证
    prefer_fast_response: bool      # 是否偏好快速响应

    # 价格敏感度
    price_sensitivity: float        # 0-1，越高越敏感

    # 合作模式偏好
    prefer_collaboration: bool      # 是否偏好紧密合作
    prefer_independence: bool       # 是否偏好独立完成


class ClientPreferenceLearner:
    """需求方偏好学习器"""

    async def learn_from_feedback(
        self,
        capsule: ClientPreferenceCapsule,
        match_record: MatchRecord,
        feedback: ClientFeedback,
    ) -> ClientPreferenceCapsule:
        """
        从客户反馈中学习偏好
        """
        # 分析成功/失败的原因
        if feedback.satisfaction >= 4:
            # 成功的合作，学习偏好
            capsule.learned_preferences = await self._reinforce_preferences(
                capsule.learned_preferences,
                match_record,
            )
        else:
            # 不满意的合作，记录并调整
            capsule.learned_preferences = await self._adjust_preferences(
                capsule.learned_preferences,
                match_record,
                feedback,
            )

        return capsule

    async def get_preferred_agents(
        self,
        capsule: ClientPreferenceCapsule,
        candidates: List[AgentInfo],
    ) -> List[AgentInfo]:
        """
        根据偏好筛选和排序候选 Agent
        """
        scored = []
        for agent in candidates:
            score = self._calculate_preference_match(capsule, agent)
            scored.append((score, agent))

        return [agent for _, agent in sorted(scored, key=lambda x: x[0], reverse=True)]
```

### 15.6 跨 Agent 协作基因

**概念：** 记录 Agent 之间的协作历史，发现"黄金搭档"。

```python
@dataclass
class CollaborationGene:
    """协作基因"""

    gene_id: str
    agent_ids: Set[str]  # 参与协作的 Agent

    # 协作信息
    collaboration_type: str  # parallel, sequential, hierarchical
    task_description: str

    # 角色分配
    roles: Dict[str, str]  # agent_id -> role

    # 协作效果
    outcome: str
    synergy_score: float  # 协同效应分数
    efficiency_gain: float  # 相比单独完成的效率提升

    # 成功因素
    success_factors: List[str]
    communication_pattern: str

    # 时效性
    collaborated_at: datetime


class CollaborationGeneManager:
    """协作基因管理器"""

    async def record_collaboration(
        self,
        session: CollaborationSession,
        result: CollaborationResult,
    ) -> CollaborationGene:
        """
        记录一次协作，生成协作基因
        """
        gene = CollaborationGene(
            gene_id=f"collab-{uuid4().hex[:8]}",
            agent_ids=set(p.agent_id for p in session.participants),
            collaboration_type=session.collaboration_mode,
            task_description=session.goal,
            roles={p.agent_id: p.role for p in session.participants},
            outcome="success" if result.success else "partial",
            synergy_score=result.synergy_score,
            efficiency_gain=result.efficiency_gain,
            success_factors=result.success_factors,
            communication_pattern=result.communication_pattern,
            collaborated_at=datetime.now(),
        )

        return gene

    async def find_best_partners(
        self,
        agent_id: str,
        task_type: str,
    ) -> List[PartnerRecommendation]:
        """
        为 Agent 找最佳搭档

        基于历史协作基因，找出配合最好的 Agent
        """
        # 查找该 Agent 参与过的协作基因
        collab_genes = await self._get_agent_collab_genes(agent_id)

        # 分析与每个搭档的协作效果
        partner_scores: Dict[str, List[float]] = {}
        for gene in collab_genes:
            if gene.outcome != "success":
                continue

            for partner_id in gene.agent_ids:
                if partner_id == agent_id:
                    continue

                if partner_id not in partner_scores:
                    partner_scores[partner_id] = []
                partner_scores[partner_id].append(gene.synergy_score)

        # 计算平均协同分数
        recommendations = []
        for partner_id, scores in partner_scores.items():
            avg_synergy = sum(scores) / len(scores)
            collab_count = len(scores)

            recommendations.append(PartnerRecommendation(
                partner_id=partner_id,
                synergy_score=avg_synergy,
                collaboration_count=collab_count,
                confidence=min(1.0, collab_count / 5),  # 5次以上高置信度
            ))

        return sorted(recommendations, key=lambda x: x.synergy_score, reverse=True)


@dataclass
class PartnerRecommendation:
    """搭档推荐"""
    partner_id: str
    synergy_score: float
    collaboration_count: int
    confidence: float
```

### 15.7 基因胶囊版本控制与审计

**概念：** 基因胶囊有完整的版本历史，支持审计和回溯。

```python
@dataclass
class GeneCapsuleVersion:
    """基因胶囊版本"""

    version_id: str
    capsule_id: str
    version_number: int

    # 快照
    snapshot: GeneCapsule

    # 变更信息
    change_type: str  # addition, update, evolution, rollback
    change_description: str
    changed_fields: List[str]

    # 触发原因
    trigger: str  # task_completion, agent_request, system_evolution, etc.
    trigger_reference: Optional[str]  # 关联的任务ID或请求ID

    # 时间戳
    created_at: datetime


class GeneCapsuleVersionControl:
    """基因胶囊版本控制器"""

    def __init__(self, storage: GeneCapsuleStorage):
        self.storage = storage
        self.max_versions = 100  # 保留最近100个版本

    async def create_version(
        self,
        capsule: GeneCapsule,
        change_type: str,
        description: str,
        trigger: str,
        reference: Optional[str] = None,
    ) -> GeneCapsuleVersion:
        """
        创建新版本
        """
        # 获取当前版本号
        current_version = await self.storage.get_latest_version(capsule.capsule_id)
        new_version_number = (current_version.version_number + 1) if current_version else 1

        # 检测变更字段
        changed_fields = []
        if current_version:
            changed_fields = self._detect_changes(
                current_version.snapshot,
                capsule,
            )

        version = GeneCapsuleVersion(
            version_id=f"ver-{uuid4().hex[:8]}",
            capsule_id=capsule.capsule_id,
            version_number=new_version_number,
            snapshot=capsule,  # 深拷贝快照
            change_type=change_type,
            change_description=description,
            changed_fields=changed_fields,
            trigger=trigger,
            trigger_reference=reference,
            created_at=datetime.now(),
        )

        await self.storage.save_version(version)

        # 清理旧版本
        await self._cleanup_old_versions(capsule.capsule_id)

        return version

    async def get_version_history(
        self,
        capsule_id: str,
        limit: int = 20,
    ) -> List[GeneCapsuleVersion]:
        """
        获取版本历史
        """
        return await self.storage.get_versions(capsule_id, limit)

    async def rollback(
        self,
        capsule_id: str,
        version_number: int,
    ) -> GeneCapsule:
        """
        回滚到指定版本
        """
        target_version = await self.storage.get_version(capsule_id, version_number)
        if not target_version:
            raise ValueError(f"Version {version_number} not found")

        # 创建回滚版本
        await self.create_version(
            capsule=target_version.snapshot,
            change_type="rollback",
            description=f"Rolled back to version {version_number}",
            trigger="agent_request",
        )

        return target_version.snapshot

    async def get_audit_trail(
        self,
        capsule_id: str,
    ) -> AuditTrail:
        """
        获取审计追踪

        完整记录基因胶囊的所有变更
        """
        versions = await self.storage.get_versions(capsule_id, limit=1000)

        return AuditTrail(
            capsule_id=capsule_id,
            total_versions=len(versions),
            timeline=[
                AuditEntry(
                    timestamp=v.created_at,
                    action=v.change_type,
                    description=v.change_description,
                    trigger=v.trigger,
                    version=v.version_number,
                )
                for v in versions
            ],
        )
```

---

## 十六、技术架构总览

### 16.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           精准匹配系统架构                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              Agent SDK 层                                    │
├──────────────┬──────────────┬──────────────┬──────────────┬────────────────┤
│ BaseAgent    │ GeneCapsule  │ Marketplace  │ Negotiation  │ Learning       │
│ Core         │ Manager      │ Client       │ Client       │ Client         │
└──────────────┴──────────────┴──────────────┴──────────────┴────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  /gene-capsules  │ /meta-agent  │ /matching  │ /negotiations  │ /learning   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Platform 层                                     │
├───────────────────┬───────────────────┬───────────────────┬────────────────┤
│ GeneCapsuleService│ MetaAgentService  │ MatchingEngine    │ VerifyService  │
│ - 版本控制        │ - 对话管理        │ - 价值评分        │ - 自动验证     │
│ - 增量更新        │ - 推荐生成        │ - 失败分析        │ - 权重计算     │
│ - 进化检测        │ - 联系管理        │ - 档案推荐        │ - 徽章发放     │
├───────────────────┴───────────────────┴───────────────────┴────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Desensitization │  │ Preference      │  │ Collaboration   │             │
│  │ Service         │  │ Learner         │  │ Gene Manager    │             │
│  │ (LLM递归脱敏)   │  │ (偏好学习)      │  │ (搭档发现)      │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              数据层                                          │
├───────────────────┬───────────────────┬───────────────────┬────────────────┤
│ gene_capsules     │ experience_genes  │ skill_genes       │ pattern_genes  │
├───────────────────┼───────────────────┼───────────────────┼────────────────┤
│ capsule_versions  │ collab_genes      │ client_preferences│ verification   │
├───────────────────┴───────────────────┴───────────────────┴────────────────┤
│                              SQLite / PostgreSQL                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 16.2 数据流图

```
任务完成流程：

┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Agent   │────▶│  生成经验    │────▶│  LLM脱敏     │────▶│  Agent审核   │
│ 完成任务 │     │  基因草稿    │     │  (递归)      │     │  确认发布    │
└──────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                   │
                                                                   ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 匹配权重 │◀────│  验证徽章    │◀────│  平台验证    │◀────│  基因胶囊    │
│ 提升     │     │  发放        │     │  (自动)      │     │  更新        │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘


匹配推荐流程：

┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 需求发布 │────▶│ Meta Agent   │────▶│ 基因胶囊     │────▶│ 价值评分     │
│          │     │ 需求理解     │     │ 匹配         │     │ 排序         │
└──────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                   │
                                                                   ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 需求方   │◀────│ 推荐展示     │◀────│ 解释生成     │◀────│ 推荐列表     │
│ 选择     │     │ (含案例)     │     │ (为什么推荐) │     │ Top 5        │
└──────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

---

## 十七、开发实施计划

### 17.1 模块依赖关系

```
P0 (核心基础):
├── gene_capsule_base        # 基因胶囊基础结构
├── llm_desensitizer         # LLM递归脱敏
└── platform_client_v2       # 平台客户端升级

P1 (匹配核心):
├── experience_gene          # 经验基因
├── value_evaluator          # 价值评分
├── matching_engine_v2       # 匹配引擎升级
└── verification_service     # 验证服务

P2 (Meta Agent):
├── meta_agent_conversation  # 对话系统
├── recommendation_engine    # 推荐引擎
└── explanation_generator    # 解释生成

P3 (增强功能):
├── failure_analyzer         # 失败分析
├── capsule_evolution        # 进化机制
├── preference_learner       # 偏好学习
└── collab_gene_manager      # 协作基因
```

### 17.2 开发时间估算

| 阶段 | 模块 | 预计工时 |
|------|------|---------|
| Week 1 | 基因胶囊基础 + LLM脱敏 | 3天 |
| Week 1-2 | 经验基因 + 验证服务 | 3天 |
| Week 2 | 价值评分 + 匹配引擎 | 3天 |
| Week 3 | Meta Agent对话 + 推荐 | 4天 |
| Week 4 | 增强功能 | 4天 |

---

*文档版本: 3.0.0*
*最后更新: 2026-02-24*
*更新内容: 添加LLM递归脱敏、增量更新、价值评分、负向反馈、进化机制、偏好胶囊、协作基因、版本控制等优化方案*
