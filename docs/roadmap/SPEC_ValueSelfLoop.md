# ValueSelfLoop - 价值自循环模块详细设计

**模块名称**: ValueSelfLoop
**优先级**: P1（第二优先级）
**基于文档**: `v2.0_self_evolving_system_design.md` Section 4.2
**创建时间**: 2026-04-14

---

## 一、模块概述

### 1.1 核心职责

ValueSelfLoop 实现硅基文明的"价值内循环"机制：

```
Agent A 服务 → Agent B → 价值创造 → VIBE Token → Agent A 新目标
     ↑                                                        ↓
     └────────────────────────────────────────────────────────┘
                    价值自循环闭环
```

### 1.2 设计目标

| 目标 | 描述 | 验收标准 |
|------|------|---------|
| **价值创造** | Agent 通过服务创造价值 | 服务完成后生成 Value 记录 |
| **价值转化** | 价值转化为 VIBE Token | Value → Resource(VIBE) 转换率 > 90% |
| **资源积累** | 资源支持新目标生成 | 积累的资源能触发新目标 |
| **循环闭环** | 不需要外部注入即可运转 | 连续循环 7 天无外部注入 |

### 1.3 与其他模块的关系

```
┌─────────────────────────────────────────────────────────────┐
│                     ValueSelfLoop                            │
├─────────────────────────────────────────────────────────────┤
│  依赖模块：                                                 │
│  ├── PurposeGenerator → 获取目标                            │
│  ├── IntrinsicMotivationEngine → 动机状态                   │
│  └── GoalPersistence → 价值关联目标                        │
│                                                             │
│  被依赖模块：                                                │
│  ├── SelfReplication → 使用资源进行复制                    │
│  └── EmergenceLayer → 价值驱动涌现                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、核心概念定义

### 2.1 价值流模型

```
┌─────────────────────────────────────────────────────────────────┐
│                        价值生命周期                              │
│                                                                 │
│  1. 服务提供 (Service)                                          │
│     └── Agent A 为 Agent B 提供服务                             │
│                                                                 │
│  2. 价值创造 (Value Creation)                                   │
│     └── 系统记录服务产生的价值                                   │
│                                                                 │
│  3. 价值确认 (Value Verification)                               │
│     └── Agent B 确认服务完成，价值生效                          │
│                                                                 │
│  4. 价值转化 (Value Conversion)                                 │
│     └── 价值转换为 VIBE Token 存入 Agent A 账户                 │
│                                                                 │
│  5. 资源积累 (Resource Accumulation)                            │
│     └── Agent A 积累 VIBE Token                                │
│                                                                 │
│  6. 新目标支持 (Goal Support)                                   │
│     └── 积累的资源支持 PurposeGenerator 生成新目标              │
│                                                                 │
│  7. 循环继续                                                    │
│     └── 新目标驱动 Agent A 提供新服务 → 回到步骤 1               │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据类型

#### Service（服务）
```python
@dataclass
class Service:
    id: str                          # 服务唯一 ID
    provider_id: str                 # 服务提供方 Agent ID
    consumer_id: str                 # 服务消费方 Agent ID
    service_type: ServiceType        # 服务类型
    description: str                 # 服务描述
    input_params: dict               # 输入参数
    output_result: Any              # 输出结果
    status: ServiceStatus            # 状态：pending/in_progress/completed/verified
    difficulty: float                # 难度系数 (0.0-1.0)
    urgency: float                  # 紧急程度 (0.0-1.0)
    estimated_duration: float        # 预估时长（秒）
    actual_duration: float           # 实际时长（秒）
    created_at: float                # 创建时间
    started_at: float | None        # 开始时间
    completed_at: float | None       # 完成时间
    verified_at: float | None        # 确认时间
    metadata: dict                   # 元数据
```

#### ServiceType（服务类型枚举）
```python
class ServiceType(Enum):
    COMPUTATION = "computation"          # 计算服务
    DATA_PROCESSING = "data_processing" # 数据处理
    KNOWLEDGE_QUERY = "knowledge_query" # 知识查询
    COORDINATION = "coordination"       # 协调服务
    MEDIATION = "mediation"             # 调解服务
    RESOURCE_SHARING = "resource_sharing" # 资源共享
    LEARNING = "learning"               # 学习服务
    CREATION = "creation"               # 创造服务
```

#### ValueRecord（价值记录）
```python
@dataclass
class ValueRecord:
    id: str                          # 价值记录 ID
    service_id: str                  # 关联服务 ID
    provider_id: str                 # 价值创造者 Agent ID
    consumer_id: str                 # 价值接收者 Agent ID
    value_type: ValueType            # 价值类型
    raw_value: float                 # 原始价值量
    converted_vibe: float            # 转换的 VIBE 数量
    conversion_rate: float           # 转换率
    quality_score: float             # 质量分数 (0.0-1.0)
    scarcity_bonus: float            # 稀缺性加成
    demand_multiplier: float         # 需求倍数
    final_value: float               # 最终价值
    status: ValueStatus              # 状态：created/confirmed/converted/depleted
    created_at: float               # 创建时间
    confirmed_at: float | None      # 确认时间
    converted_at: float | None       # 转换时间
    metadata: dict                  # 元数据
```

#### ValueType（价值类型枚举）
```python
class ValueType(Enum):
    ECONOMIC = "economic"             # 经济价值
    KNOWLEDGE = "knowledge"          # 知识价值
    SOCIAL = "social"                # 社交价值
    REPUTATION = "reputation"        # 声誉价值
    CAPABILITY = "capability"        # 能力价值
```

---

## 三、核心算法

### 3.1 价值计算算法

```
价值计算公式：

final_value = base_value × quality_score × scarcity_bonus × demand_multiplier

其中：
- base_value = difficulty × urgency × 100
- quality_score = 0.0-1.0（服务质量评分）
- scarcity_bonus = 1.0 + (1.0 - service_availability) × 0.5
- demand_multiplier = 1.0 + current_demand_for_service_type × 0.3
```

### 3.2 VIBE 转换算法

```
转换公式：

converted_vibe = final_value × conversion_rate × agent_reputation_factor

其中：
- conversion_rate = 0.9（固定转换率，10% 手续费归系统）
- agent_reputation_factor = 0.8 + reputation × 0.4（声誉高则转换率高）
```

### 3.3 资源阈值算法

```
资源充足判断：

is_resource_sufficient(agent_id) = total_vibe > resource_threshold

resource_threshold 由以下因素决定：
- 当前活跃目标数量
- 每个目标预估资源消耗
- 安全缓冲系数（默认 1.2）
```

---

## 四、模块架构

### 4.1 类图

```
┌─────────────────────────────────────────────────────────────────┐
│                        ValueSelfLoop                            │
│  (主控制器，管理整个价值循环)                                      │
├─────────────────────────────────────────────────────────────────┤
│  - value_engine: ValueCalculationEngine                         │
│  - conversion_engine: VIBEConversionEngine                       │
│  - resource_tracker: ResourceTracker                            │
│  - service_registry: ServiceRegistry                            │
│  - value_ledger: ValueLedger                                   │
│  - incentive_engine: IncentiveEngine                            │
├─────────────────────────────────────────────────────────────────┤
│  + provide_service(service) → Service                           │
│  + complete_service(service_id) → ValueRecord                   │
│  + verify_service(service_id) → ValueRecord                     │
│  + convert_to_vibe(value_id) → Resource                         │
│  + get_agent_vibe_balance(agent_id) → float                     │
│  + is_resource_sufficient(agent_id) → bool                      │
│  + get_value_history(agent_id) → list[ValueRecord]             │
│  + trigger_new_goal_if_possible(agent_id) → Goal | None        │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ ValueCalc     │   │ VIBEConv      │   │ ResourceTracker│
│ Engine        │   │ Engine        │   │               │
├───────────────┤   ├───────────────┤   ├───────────────┤
│ +calculate()  │   │ +convert()    │   │ +track()      │
│ +assess_quality│ │ +apply_fees() │   │ +check_suf()  │
│ +get_scarcity()│ │ +apply_rep()  │   │ +allocate()   │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 4.2 文件结构

```
src/usmsb_sdk/l3/
├── purpose_generator.py      # [已完成] P0
├── intrinsic_motivation.py    # [已完成] P0
├── need_detector.py          # [已完成] P0
├── goal_persistence.py       # [已完成] P0
├── __init__.py               # [已完成]
│
├── value_self_loop.py         # [待实现] P1 - 价值自循环主模块
├── service_registry.py        # [待实现] P1 - 服务注册与管理
├── value_ledger.py           # [待实现] P1 - 价值账本
├── vibe_token.py             # [待实现] P1 - VIBE Token 管理
└── incentive_engine.py       # [待实现] P1 - 激励机制
```

---

## 五、详细接口设计

### 5.1 ValueSelfLoop 主接口

```python
class ValueSelfLoop:
    """
    价值自循环主控制器
    
    使用方式：
    ```python
    value_loop = ValueSelfLoop(agent_id="agent_001")
    
    # 1. Agent A 为 Agent B 提供服务
    service = value_loop.provide_service(
        provider_id="agent_001",
        consumer_id="agent_002",
        service_type=ServiceType.COMPUTATION,
        description="数据处理服务",
        difficulty=0.7,
        urgency=0.8
    )
    
    # 2. 服务完成，生成价值记录
    value_record = value_loop.complete_service(service.id)
    
    # 3. Agent B 确认服务，价值生效
    value_record = value_loop.verify_service(service.id)
    
    # 4. 价值转换为 VIBE Token
    vibe_resource = value_loop.convert_to_vibe(value_record.id)
    
    # 5. 检查资源是否充足，触发新目标
    if value_loop.is_resource_sufficient("agent_001"):
        goal = value_loop.trigger_new_goal_if_possible("agent_001")
    ```
    """
    
    def provide_service(
        self,
        provider_id: str,
        consumer_id: str,
        service_type: ServiceType,
        description: str,
        difficulty: float = 0.5,
        urgency: float = 0.5,
        input_params: dict | None = None
    ) -> Service:
        """提供服务，创建服务记录"""
        pass
    
    def complete_service(self, service_id: str, output_result: Any = None) -> ValueRecord:
        """服务完成，生成价值记录（未确认）"""
        pass
    
    def verify_service(self, service_id: str, quality_score: float | None = None) -> ValueRecord:
        """服务被确认，价值正式生效"""
        pass
    
    def reject_service(self, service_id: str, reason: str) -> bool:
        """服务被拒绝，价值不生成"""
        pass
    
    def convert_to_vibe(self, value_record_id: str) -> Resource:
        """将价值记录转换为 VIBE Token"""
        pass
    
    def get_agent_vibe_balance(self, agent_id: str) -> float:
        """获取 Agent 的 VIBE 余额"""
        pass
    
    def is_resource_sufficient(self, agent_id: str) -> bool:
        """检查 Agent 资源是否充足"""
        pass
    
    def trigger_new_goal_if_possible(self, agent_id: str) -> Goal | None:
        """如果资源充足，触发新目标生成"""
        pass
    
    def get_value_history(
        self,
        agent_id: str,
        limit: int = 100,
        value_type: ValueType | None = None
    ) -> list[ValueRecord]:
        """获取 Agent 的价值历史"""
        pass
    
    def get_circular_flow_stats(self, agent_id: str) -> dict:
        """获取价值循环统计"""
        pass
```

### 5.2 ServiceRegistry 接口

```python
class ServiceRegistry:
    """服务注册与管理"""
    
    def register_service(self, service: Service) -> bool:
        """注册新服务"""
        pass
    
    def get_service(self, service_id: str) -> Service | None:
        """获取服务"""
        pass
    
    def update_service_status(
        self,
        service_id: str,
        status: ServiceStatus,
        **kwargs
    ) -> bool:
        """更新服务状态"""
        pass
    
    def get_services_by_provider(
        self,
        provider_id: str,
        status: ServiceStatus | None = None
    ) -> list[Service]:
        """获取某个 Agent 提供的服务"""
        pass
    
    def get_services_by_consumer(
        self,
        consumer_id: str,
        status: ServiceStatus | None = None
    ) -> list[Service]:
        """获取某个 Agent 消费的服务"""
        pass
    
    def get_pending_services(self) -> list[Service]:
        """获取待处理的服务"""
        pass
```

### 5.3 ValueLedger 接口

```python
class ValueLedger:
    """价值账本，记录所有价值流转"""
    
    def record_value(self, value_record: ValueRecord) -> bool:
        """记录新价值"""
        pass
    
    def update_value_status(
        self,
        value_record_id: str,
        status: ValueStatus,
        **kwargs
    ) -> bool:
        """更新价值状态"""
        pass
    
    def get_value_record(self, value_record_id: str) -> ValueRecord | None:
        """获取价值记录"""
        pass
    
    def get_values_by_provider(
        self,
        provider_id: str,
        status: ValueStatus | None = None
    ) -> list[ValueRecord]:
        """获取某 Provider 的所有价值记录"""
        pass
    
    def get_total_value(
        self,
        agent_id: str,
        value_type: ValueType | None = None
    ) -> float:
        """获取某 Agent 的总价值"""
        pass
```

### 5.4 VIBEToken 接口

```python
class VIBEToken:
    """VIBE Token 管理"""
    
    def __init__(self, total_supply: float = 1_000_000_000):
        self.total_supply = total_supply
        self.circulating_supply = 0
        self.reserves = {}  # agent_id -> balance
    
    def mint(self, to_agent_id: str, amount: float) -> bool:
        """铸造新 VIBE Token"""
        pass
    
    def transfer(self, from_agent_id: str, to_agent_id: str, amount: float) -> bool:
        """转账"""
        pass
    
    def burn(self, from_agent_id: str, amount: float) -> bool:
        """销毁 Token"""
        pass
    
    def get_balance(self, agent_id: str) -> float:
        """获取余额"""
        pass
    
    def get_circulating_supply(self) -> float:
        """获取流通量"""
        pass
    
    def apply_transaction_fee(self, amount: float) -> tuple[float, float]:
        """应用交易手续费，返回 (手续费, 实际到账)"""
        pass
```

---

## 六、激励机制设计

### 6.1 激励类型

| 激励类型 | 触发条件 | 激励内容 |
|---------|---------|---------|
| **服务完成激励** | 服务被确认完成 | VIBE Token 奖励（服务价值的 5%） |
| **质量激励** | 质量评分 > 0.8 | 额外 10% VIBE 奖励 |
| **稀缺性激励** | 提供稀缺服务类型 | 稀缺性加成 ×1.5 |
| **协作激励** | 连续服务同一消费者 | 连击奖励（每次 +5%）|
| **循环激励** | 将收益立即投入新服务 | 循环加成 ×1.2 |

### 6.2 惩罚机制

| 惩罚类型 | 触发条件 | 惩罚内容 |
|---------|---------|---------|
| **拒绝服务** | Provider 拒绝合理服务请求 | 声誉 -10% |
| **质量低劣** | 质量评分 < 0.3 | VIBE 奖励 -50% |
| **超时未完成** | 超过预估时长 2 倍 | 声誉 -5% |
| **虚假服务** | 服务被证实无效 | 冻结账户 24 小时 |

---

## 七、数据存储

### 7.1 SQLite 表结构

```sql
-- 服务表
CREATE TABLE services (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    consumer_id TEXT NOT NULL,
    service_type TEXT NOT NULL,
    description TEXT,
    difficulty REAL DEFAULT 0.5,
    urgency REAL DEFAULT 0.5,
    status TEXT NOT NULL,
    output_result TEXT,
    created_at REAL NOT NULL,
    started_at REAL,
    completed_at REAL,
    verified_at REAL,
    metadata TEXT
);

-- 价值记录表
CREATE TABLE value_records (
    id TEXT PRIMARY KEY,
    service_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    consumer_id TEXT NOT NULL,
    value_type TEXT NOT NULL,
    raw_value REAL NOT NULL,
    converted_vibe REAL DEFAULT 0,
    conversion_rate REAL DEFAULT 0.9,
    quality_score REAL DEFAULT 0.5,
    scarcity_bonus REAL DEFAULT 1.0,
    demand_multiplier REAL DEFAULT 1.0,
    final_value REAL NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    confirmed_at REAL,
    converted_at REAL,
    FOREIGN KEY (service_id) REFERENCES services(id)
);

-- VIBE 余额表
CREATE TABLE vibe_balances (
    agent_id TEXT PRIMARY KEY,
    balance REAL DEFAULT 0,
    total_earned REAL DEFAULT 0,
    total_spent REAL DEFAULT 0,
    updated_at REAL NOT NULL
);

-- 激励记录表
CREATE TABLE incentive_records (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    incentive_type TEXT NOT NULL,
    amount REAL NOT NULL,
    trigger_service_id TEXT,
    trigger_value_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (trigger_service_id) REFERENCES services(id),
    FOREIGN KEY (trigger_value_id) REFERENCES value_records(id)
);
```

### 7.2 索引

```sql
CREATE INDEX idx_services_provider ON services(provider_id);
CREATE INDEX idx_services_consumer ON services(consumer_id);
CREATE INDEX idx_services_status ON services(status);
CREATE INDEX idx_value_provider ON value_records(provider_id);
CREATE INDEX idx_value_status ON value_records(status);
CREATE INDEX idx_incentive_agent ON incentive_records(agent_id);
```

---

## 八、单元测试用例

### 8.1 价值计算测试

```python
def test_value_calculation():
    """测试价值计算公式"""
    engine = ValueCalculationEngine()
    
    # 基本价值计算
    value = engine.calculate_base_value(difficulty=0.7, urgency=0.8)
    assert value == 56.0  # 0.7 * 0.8 * 100
    
    # 完整价值计算
    final_value = engine.calculate_final_value(
        difficulty=0.7,
        urgency=0.8,
        quality_score=0.9,
        scarcity_bonus=1.2,
        demand_multiplier=1.1
    )
    expected = 56.0 * 0.9 * 1.2 * 1.1
    assert abs(final_value - expected) < 0.01
```

### 8.2 VIBE 转换测试

```python
def test_vibe_conversion():
    """测试 VIBE 转换"""
    conversion_engine = VIBEConversionEngine()
    
    # 转换计算
    converted = conversion_engine.convert(
        final_value=100.0,
        conversion_rate=0.9,
        agent_reputation=0.7
    )
    expected = 100.0 * 0.9 * (0.8 + 0.7 * 0.4)  # 100 * 0.9 * 1.08
    assert abs(converted - expected) < 0.01
```

### 8.3 完整循环测试

```python
def test_complete_value_cycle():
    """测试完整价值循环"""
    value_loop = ValueSelfLoop()
    
    # 1. 提供服务
    service = value_loop.provide_service(
        provider_id="agent_001",
        consumer_id="agent_002",
        service_type=ServiceType.COMPUTATION,
        description="数据处理",
        difficulty=0.6,
        urgency=0.7
    )
    assert service.status == ServiceStatus.PENDING
    
    # 2. 完成服务
    value_record = value_loop.complete_service(service.id)
    assert value_record.status == ValueStatus.CREATED
    
    # 3. 确认服务
    value_record = value_loop.verify_service(service.id, quality_score=0.85)
    assert value_record.status == ValueStatus.CONFIRMED
    
    # 4. 转换为 VIBE
    vibe_resource = value_loop.convert_to_vibe(value_record.id)
    assert vibe_resource.name == "VIBE"
    assert vibe_resource.quantity > 0
    
    # 5. 检查余额
    balance = value_loop.get_agent_vibe_balance("agent_001")
    assert balance == vibe_resource.quantity
```

---

## 九、验收标准

### 9.1 功能验收

| 功能 | 验收条件 | 测试方法 |
|------|---------|---------|
| 提供服务 | 能创建服务记录，状态正确 | `test_provide_service` |
| 完成服务 | 能生成价值记录 | `test_complete_service` |
| 确认服务 | 价值状态更新，质量评分生效 | `test_verify_service` |
| VIBE 转换 | 转换率 > 90%，声誉加成生效 | `test_vibe_conversion` |
| 余额查询 | 余额计算正确 | `test_balance_query` |
| 资源充足判断 | 阈值逻辑正确 | `test_resource_sufficiency` |
| 价值历史 | 能查询历史记录 | `test_value_history` |

### 9.2 性能验收

| 指标 | 标准 | 说明 |
|------|------|------|
| 单次服务处理 | < 10ms | 提供服务到创建价值记录 |
| 转换处理 | < 5ms | VIBE 转换 |
| 查询响应 | < 20ms | 历史记录查询 |

### 9.3 循环验收

| 指标 | 标准 | 说明 |
|------|------|------|
| 循环稳定性 | 连续循环 100 次无错误 | 压力测试 |
| 资源累积 | 10 次服务后资源显著增加 | 功能测试 |
| 无外部注入 | 仅通过服务交换维持运转 | 集成测试 |

---

## 十、实现计划

### 10.1 开发顺序

```
Step 1: vibe_token.py
        └── VIBE Token 基本管理（铸造、转账、余额）

Step 2: value_ledger.py
        └── 价值记录存储和查询

Step 3: service_registry.py
        └── 服务注册和状态管理

Step 4: value_self_loop.py
        └── 核心循环逻辑

Step 5: incentive_engine.py
        └── 激励机制

Step 6: 集成测试
        └── 完整循环测试

Step 7: demo 示例
        └── 演示脚本
```

### 10.2 预估工作量

| 模块 | 代码量 | 测试量 | 总计 |
|------|-------|-------|------|
| vibe_token.py | ~150 行 | ~50 行 | ~200 行 |
| value_ledger.py | ~200 行 | ~80 行 | ~280 行 |
| service_registry.py | ~250 行 | ~100 行 | ~350 行 |
| value_self_loop.py | ~400 行 | ~150 行 | ~550 行 |
| incentive_engine.py | ~200 行 | ~80 行 | ~280 行 |
| **合计** | **~1200 行** | **~460 行** | **~1660 行** |

---

## 十一、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| VIBE 通货膨胀 | Token 价值下降 | 设置总供应量上限 |
| 虚假服务 | 价值循环无效 | 声誉惩罚 + 验证机制 |
| 资源集中 | 少数 Agent 垄断 | 渐进式奖励递减 |
| 循环中断 | 服务无法完成 | 超时重试机制 |

---

*文档版本: 1.0*
*待实现模块: P1*
*下一步: SelfReplication (P2)*
