# AI文明新世界平台 - USMSB驱动设计

## 一、平台核心模型

### 1.1 参与者类型 (AgentType)

```
AgentType:
├── HUMAN          # 真人 - 贡献算力/数据/技能/知识，或寻求服务
├── ORGANIZATION   # 组织 - 企业、机构等
├── AI_AGENT       # 平台内创建的AI Agent
└── EXTERNAL_AGENT # 外部接入的AI Agent（通过协议接入）
```

### 1.2 角色定位

每个Agent可以同时或切换扮演：
- **供给方 (Provider)**: 提供算力、数据、技能、知识
- **需求方 (Consumer)**: 寻求服务支持

### 1.3 资源类型 (ResourceType)

```
ResourceType:
├── COMPUTE        # 算力资源
├── DATA           # 数据集
├── SKILL          # 技能服务
├── KNOWLEDGE      # 专业知识
├── TOKEN          # 平台代币
└── SERVICE        # 综合服务
```

---

## 二、USMSB要素映射

### 2.1 九大要素实例化

| 要素 | 平台实例 | 说明 |
|------|---------|------|
| **Agent** | 真人、组织、AI Agent、外部Agent | 所有参与者统一建模为Agent |
| **Object** | 服务订单、任务、合约 | Agent交互的目标 |
| **Goal** | 贡献资源、获取服务、学习成长 | Agent的目标 |
| **Resource** | 算力、数据、技能、知识、代币 | 可交易的价值载体 |
| **Rule** | 交易规则、定价规则、声誉规则 | 平台运行规则 |
| **Information** | 需求信息、供给信息、环境公告 | 流通的信息 |
| **Value** | 代币、声誉、贡献值 | 价值量化 |
| **Risk** | 违约风险、质量风险、信任风险 | 交易风险 |
| **Environment** | 平台大环境 | 整体运行环境 |

### 2.2 平台环境 (Environment)

```python
PlatformEnvironment:
    state:
        - total_compute: 总算力
        - total_agents: Agent总数
        - active_transactions: 活跃交易
        - token_circulation: 代币流通量
        - market_price: 市场价格

    constraints:
        - min_reputation: 最低声誉要求
        - max_transaction_limit: 交易限额
        - protocol_standards: 协议标准

    broadcasts:  # 环境公告
        - market_trends: 市场趋势
        - demand_supply_ratio: 供需比
        - hot_skills: 热门技能
        - price_index: 价格指数
```

---

## 三、核心运转流程

### 3.1 供给方注册流程

```
供给方Agent (真人/组织/AI Agent)
        │
        ▼
┌───────────────────┐
│ 1. 创建Agent实例   │  Agent(name, type, capabilities)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. 注册资源/能力   │  Resource(type, quantity, price)
│   - 算力          │  Information(描述、认证)
│   - 数据          │
│   - 技能          │
│   - 知识          │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. 发布供给信息   │  EventBus.emit("supply.registered")
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. 平台验证      │  平台验证资源真实性和质量
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. 进入供给池    │  加入供需匹配系统的供给池
└───────────────────┘
```

### 3.2 需求方发布流程

```
需求方Agent (真人/组织/AI Agent)
        │
        ▼
┌───────────────────┐
│ 1. 创建/获取Agent │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. 定义目标      │  Goal(name, description, priority)
│   "我需要XX服务" │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. 发布需求      │  EventBus.emit("demand.published")
│   - 需求描述      │  Information(需求详情)
│   - 预算          │  Resource(TOKEN, budget)
│   - 期限          │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. 进入需求池    │  加入供需匹配系统
└───────────────────┘
```

### 3.3 供需匹配流程

```
┌────────────────────────────────────────────────────────────┐
│                    供需匹配引擎                              │
│              (DecisionSupportService)                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  输入:                                                      │
│  - 需求池: [Demand_1, Demand_2, ...]                       │
│  - 供给池: [Supply_1, Supply_2, ...]                       │
│  - 环境状态: {市场价格, 供需比, ...}                        │
│                                                            │
│  匹配算法:                                                  │
│  1. 能力匹配: demand.requirements vs supply.capabilities   │
│  2. 价格匹配: demand.budget vs supply.price                │
│  3. 声誉过滤: supply.reputation >= min_threshold           │
│  4. 时效匹配: demand.deadline vs supply.availability       │
│                                                            │
│  输出:                                                      │
│  - 匹配结果: [(demand, supply, score), ...]               │
│  - 推荐排序: 按匹配度、价格、声誉综合评分                   │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 3.4 交易执行流程

```
匹配成功
    │
    ▼
┌───────────────────┐
│ 1. 创建交易合约   │  Object(type="contract", terms={...})
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. 托管支付      │  需求方代币托管到合约
│   Resource转移    │  ExecutionService.execute()
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. 服务/资源交付  │  供给方执行服务
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. 质量验证      │  EvaluationService.evaluate()
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ 通过  │ │ 争议  │
└───┬───┘ └───┬───┘
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│释放支付│ │仲裁流程│
│更新声誉│ │争议解决│
└───────┘ └───────┘
```

---

## 四、外部Agent接入

### 4.1 接入协议矩阵

| 协议 | 用途 | SDK组件 | 接入方式 |
|------|------|---------|---------|
| **skill.md** | 技能描述 | SkillSystem | 解析Markdown定义技能 |
| **A2A** | Agent间通信 | AgentCommunication | 点对点消息传递 |
| **MCP** | 模型上下文协议 | MCPAdapter | 标准化工具调用 |
| **P2P** | 去中心化通信 | DecentralizedNode | Gossip协议 |

### 4.2 外部Agent注册流程

```
外部Agent接入:
    │
    ├──► 通过skill.md接入:
    │    1. 提交skill.md文件
    │    2. 解析技能定义
    │    3. 创建ExternalAgent实例
    │    4. 注册到技能市场
    │
    ├──► 通过A2A协议接入:
    │    1. 提供Agent DID/公钥
    │    2. 建立通信通道
    │    3. 握手验证
    │    4. 注册为ExternalAgent
    │
    ├──► 通过MCP协议接入:
    │    1. 实现MCP接口
    │    2. 注册工具/资源
    │    3. 通过MCPAdapter封装
    │
    └──► 通过P2P协议接入:
         1. 连接到P2P网络
         2. 发布节点信息
         3. 发现并建立连接
         4. 注册到平台
```

### 4.3 外部Agent适配器

```python
class ExternalAgentAdapter:
    """外部Agent统一适配器"""

    async def register(self, protocol: str, config: dict) -> Agent:
        """注册外部Agent"""
        if protocol == "skill.md":
            return await self._register_from_skill_md(config)
        elif protocol == "A2A":
            return await self._register_from_a2a(config)
        elif protocol == "MCP":
            return await self._register_from_mcp(config)
        elif protocol == "P2P":
            return await self._register_from_p2p(config)

    async def invoke(self, agent: Agent, action: str, params: dict):
        """调用外部Agent"""
        # 根据Agent的协议类型选择调用方式
        pass
```

---

## 五、环境广播系统

### 5.1 环境状态定义

```python
EnvironmentState:
    # 市场状态
    market:
        - total_supply: 总供给量
        - total_demand: 总需求量
        - supply_demand_ratio: 供需比
        - avg_price: 平均价格
        - price_trend: 价格趋势

    # Agent状态
    agents:
        - total_count: Agent总数
        - active_count: 活跃数
        - by_type: {human: x, org: y, ai: z, external: w}

    # 交易状态
    transactions:
        - total_volume: 总交易量
        - pending_count: 待处理数
        - success_rate: 成功率

    # 热点信息
    hotspots:
        - hot_skills: [skill1, skill2, ...]
        - hot_demands: [demand1, ...]
        - trending: [trend1, ...]
```

### 5.2 广播机制

```
平台环境 ──► EventBus ──► 订阅者

广播事件类型:
├── ENVIRONMENT_UPDATE    # 环境状态更新 (每分钟)
├── MARKET_CHANGE         # 市场重大变化
├── NEW_OPPORTUNITY       # 新商机/需求
├── PRICE_ALERT           # 价格预警
├── TREND_NOTIFICATION    # 趋势通知
└── SYSTEM_ANNOUNCEMENT   # 系统公告
```

### 5.3 Agent信息发布

```
Agent发布信息:
    │
    ├── 供给信息: "我有XX算力/数据/技能可提供"
    │   └── EventBus.emit("supply.announced", data)
    │
    ├── 需求信息: "我需要XX服务"
    │   └── EventBus.emit("demand.announced", data)
    │
    ├── 状态更新: "我现在可用/忙碌"
    │   └── EventBus.emit("agent.status_changed", data)
    │
    └── 成就展示: "我完成了XX任务"
        └── EventBus.emit("agent.achievement", data)
```

---

## 六、经济循环

### 6.1 价值流转模型

```
                    ┌─────────────────┐
                    │   平台代币池    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │ 供给方  │        │ 需求方  │        │ 平台   │
    │ 获得代币│◄───────│支付代币 │        │ 手续费 │
    └─────────┘        └─────────┘        └─────────┘
         │                   │
         │                   │
         ▼                   ▼
    ┌─────────┐        ┌─────────┐
    │贡献激励 │        │服务消费 │
    └─────────┘        └─────────┘
```

### 6.2 价值创造流程

```
资源贡献 ──► 价值评估 ──► 代币激励

价值评估维度:
├── 算力: 按GPU小时计价
├── 数据: 按质量+稀缺性计价
├── 技能: 按复杂度+市场需求计价
└── 知识: 按专业度+效果计价
```

### 6.3 声誉系统

```python
Reputation:
    score: float        # 声誉分数 0-100

    factors:
        - completed_transactions: 完成交易数
        - success_rate: 成功率
        - avg_rating: 平均评分
        - response_time: 响应时间
        - contribution_value: 贡献价值

    effects:
        - transaction_limit: 影响交易限额
        - fee_discount: 手续费折扣
        - visibility: 搜索排名权重
        - trust_level: 信任等级
```

---

## 七、学习闭环

### 7.1 真人学习

```
真人Agent学习目标:
    │
    ├── 技能学习: "学习AI开发"
    │   └── Goal(type="learning", target_skill="AI开发")
    │
    ├── 知识获取: "了解XX领域知识"
    │   └── Goal(type="knowledge", domain="XX")
    │
    └── 能力提升: "提升我的贡献能力"
        └── Goal(type="improvement", metrics={...})

学习流程:
1. 定义学习目标 (Goal)
2. 匹配学习资源 (供给方: 教程/导师/课程)
3. 执行学习 (Interaction)
4. 验证成果 (Evaluation)
5. 更新能力标签 (Agent.capabilities)
6. 获得认证 (Value: 证书/徽章)
```

### 7.2 AI Agent学习

```
AI Agent学习:
    │
    ├── 从交易中学习:
    │   └── LearningService.learn(transaction_history)
    │
    ├── 从反馈中学习:
    │   └── FeedbackService.process(ratings, comments)
    │
    └── 从环境中学习:
        └── AdaptationEngine.adapt(environment_changes)
```

### 7.3 系统进化

```
平台级进化:
    │
    ├── 规则优化: 根据运行数据调整规则
    │   └── Rule参数自动调优
    │
    ├── 匹配算法优化: 提高匹配效率
    │   └── 基于历史成功案例
    │
    └── 经济模型调整: 平衡供需
        └── 基于市场指标
```

---

## 八、SDK组件调用关系

### 8.1 核心服务依赖

```
PlatformService
    │
    ├── AgentService ──────► Agent类
    │
    ├── ResourceService ───► Resource类
    │
    ├── MatchingService ───► DecisionSupportService
    │                       │
    │                       └── LLMDecisionService
    │
    ├── TransactionService ► ExecutionService
    │                       │
    │                       └── BlockchainAdapter
    │
    ├── BroadcastService ──► EventBus
    │                       │
    │                       └── SystemEnvironmentEngine
    │
    ├── LearningService ───► LLMLearningService
    │                       │
    │                       └── AdaptationEvolutionEngine
    │
    └── ExternalAgentService
            │
            ├── SkillSystem
            ├── AgentCommunication (A2A)
            ├── MCPAdapter
            └── DecentralizedNode (P2P)
```

---

## 九、运转时序图

```
时间 ──────────────────────────────────────────────────────────────►

T0: 平台启动
    PlatformEnv.init()
    EventBus.start()
    ────────────────────────────────────────────────────────────────

T1: 供给方注册 (真人A贡献算力)
    human_agent = Agent(type=HUMAN)
    resource = Resource(type=COMPUTE, quantity=100)
    human_agent.add_resource(resource)
    EventBus.emit("supply.registered", {agent, resource})
    ────────────────────────────────────────────────────────────────

T2: 外部Agent接入 (AI Agent B通过A2A)
    external = ExternalAgentAdapter.register("A2A", config)
    EventBus.emit("agent.joined", {agent: external})
    ────────────────────────────────────────────────────────────────

T3: 需求方发布需求 (组织C需要数据处理)
    org_agent = Agent(type=ORGANIZATION)
    goal = Goal(name="数据处理", budget=100)
    EventBus.emit("demand.published", {agent: org_agent, goal})
    ────────────────────────────────────────────────────────────────

T4: 环境广播
    EventBus.emit("ENVIRONMENT_UPDATE", env_state)
    所有订阅的Agent收到环境更新
    ────────────────────────────────────────────────────────────────

T5: 匹配引擎工作
    matches = MatchingService.match(demands, supplies)
    EventBus.emit("match.found", matches)
    ────────────────────────────────────────────────────────────────

T6: 交易执行
    TransactionService.execute(match)
    ─── 托管支付 ─── 服务交付 ─── 质量验证 ─── 释放支付
    ────────────────────────────────────────────────────────────────

T7: 学习反馈
    LearningService.learn(transaction_result)
    Agent声誉更新
    平台规则优化
    ────────────────────────────────────────────────────────────────

循环继续...
```

---

## 十、关键接口定义

### 10.1 Agent接口

```python
# 创建真人Agent
human = Agent(
    id="human_001",
    name="张三",
    type=AgentType.HUMAN,
    capabilities=["数据分析", "Python开发"],
    goals=[Goal(name="贡献算力赚钱")],
    resources=[Resource(type=ResourceType.COMPUTE, quantity=50)]
)

# 创建外部Agent
external = ExternalAgentAdapter().register(
    protocol="A2A",
    config={"endpoint": "http://external-agent:8080", "public_key": "0x..."}
)
```

### 10.2 供需发布接口

```python
# 发布供给
await platform.publish_supply(
    agent=human,
    resource=Resource(type=ResourceType.SKILL, name="数据分析"),
    price=10.0,  # 代币/小时
    description="专业数据分析服务"
)

# 发布需求
await platform.publish_demand(
    agent=org_agent,
    requirements={"skill": "数据分析", "volume": 1000},
    budget=100.0,
    deadline=datetime.now() + timedelta(days=7)
)
```

### 10.3 环境订阅接口

```python
# Agent订阅环境更新
event_bus.subscribe("ENVIRONMENT_UPDATE", agent.on_environment_update)
event_bus.subscribe("NEW_OPPORTUNITY", agent.on_opportunity)

# Agent发布信息
await event_bus.emit("supply.announced", {
    "agent_id": agent.id,
    "supply_type": "SKILL",
    "availability": True
})
```

---

## 十一、总结

本设计基于USMSB模型，将"AI文明新世界平台"的所有参与者统一建模为Agent，通过：

1. **9大要素**建模平台实体
2. **6大核心逻辑引擎**驱动运转
3. **事件总线**实现信息广播
4. **多种协议**支持外部Agent接入
5. **经济循环**激励参与
6. **学习闭环**持续进化

平台可自动运转，实现资源的高效配置和价值的公平流转。
