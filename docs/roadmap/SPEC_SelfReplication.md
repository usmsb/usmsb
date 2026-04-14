# SelfReplication - 自我复制模块详细设计

**模块名称**: SelfReplication
**优先级**: P2
**基于文档**: `v2.0_self_evolving_system_design.md`
**创建时间**: 2026-04-14

---

## 一、模块概述

### 1.1 核心职责

SelfReplication 实现硅基生命的"自我复制"能力：

```
高适应度 Agent → 自我复制 → 子 Agent（略有变异）→ 新目标追求
     ↑                                                              ↓
     └──────────────────────────────────────────────────────────────┘
                        适应度验证循环
```

### 1.2 设计目标

| 目标 | 描述 | 验收标准 |
|------|------|---------|
| **自我复制** | Agent 能复制自身 | 复制后功能完整 |
| **能力继承** | 子 Agent 继承父 Agent 能力 | 80%+ 能力保留 |
| **变异机制** | 子 Agent 有轻微变异 | 5-15% 变异率 |
| **适应度验证** | 低适应度 Agent 不复制 | 适应度 < 阈值时禁止复制 |
| **资源消耗** | 复制消耗资源 | 资源不足时禁止复制 |

---

## 二、核心概念

### 2.1 复制类型

```python
class ReplicationType(Enum):
    ASEXUAL = "asexual"    # 无性繁殖：完全复制
    SEXUAL = "sexual"     # 有性繁殖：两个 Agent 交换基因
    CLONING = "cloning"   # 克隆：精确复制
    VARIANT = "variant"    # 变异复制：带有突变的复制
```

### 2.2 适应度计算

```python
def calculate_fitness(agent: Agent) -> float:
    """
    适应度计算公式
    
    fitness = w1 × value_created + w2 × collaboration_count + 
             w3 × learning_progress + w4 × resource_efficiency
    
    权重：
    - value_created: 30% - 创造的价值
    - collaboration_count: 20% - 协作次数
    - learning_progress: 30% - 学习进度
    - resource_efficiency: 20% - 资源效率
    """
    pass
```

### 2.3 复制触发条件

```python
class ReplicationTrigger:
    """复制触发条件"""
    
    MIN_FITNESS = 0.6        # 最低适应度（低于此值不复制）
    MIN_RESOURCE = 100.0      # 最低资源（低于此值不复制）
    MIN_AGE = 3600           # 最小年龄（秒）
    COOLDOWN = 86400         # 复制冷却时间（秒）
    MAX_POPULATION = 1000    # 最大种群数量
```

---

## 三、核心算法

### 3.1 复制流程

```
1. 适应度检查
   └── fitness >= MIN_FITNESS?
   
2. 资源检查
   └── resource >= MIN_RESOURCE?
   
3. 年龄检查
   └── age >= MIN_AGE?
   
4. 冷却检查
   └── last_replication >= COOLDOWN?
   
5. 种群检查
   └── population < MAX_POPULATION?
   
6. 执行复制
   ├── 创建子 Agent
   ├── 继承能力
   ├── 应用变异
   └── 消耗资源
```

### 3.2 变异机制

```python
class MutationEngine:
    """变异引擎"""
    
    MUTATION_RATE = 0.1  # 10% 变异率
    
    def mutate_capability(self, capability: str) -> str:
        """能力变异"""
        # 5% 概率：能力增强
        # 5% 概率：能力减弱
        # 90% 概率：能力不变
        pass
    
    def mutate_goal_priority(self, priority: int) -> int:
        """目标优先级变异"""
        # ±10% 随机调整
        pass
    
    def mutate_strategy(self, strategy: dict) -> dict:
        """策略变异"""
        # 随机调整策略参数
        pass
```

---

## 四、模块接口

### 4.1 SelfReplication 主接口

```python
class SelfReplication:
    """自我复制引擎"""
    
    def can_replicate(self, agent_id: str) -> tuple[bool, str]:
        """
        检查是否可以复制
        
        Returns:
            (can_replicate, reason)
        """
        pass
    
    def replicate(
        self,
        parent_id: str,
        replication_type: ReplicationType = ReplicationType.VARIANT
    ) -> Agent | None:
        """执行复制"""
        pass
    
    def calculate_fitness(self, agent_id: str) -> float:
        """计算适应度"""
        pass
    
    def apply_mutation(self, child: Agent) -> Agent:
        """应用变异"""
        pass
    
    def inherit_capabilities(
        self,
        parent: Agent,
        child: Agent,
        inheritance_rate: float = 0.8
    ) -> Agent:
        """继承能力"""
        pass
```

---

## 五、数据结构

### 5.1 复制记录

```python
@dataclass
class ReplicationRecord:
    id: str
    parent_id: str
    child_id: str
    replication_type: ReplicationType
    fitness_at_replication: float
    mutation_applied: list[str]
    inherited_capabilities: list[str]
    resource_cost: float
    timestamp: float
```

---

## 六、验收标准

| 功能 | 验收条件 | 测试方法 |
|------|---------|---------|
| 适应度计算 | 正确计算 4 个维度 | `test_fitness_calculation` |
| 复制触发 | 条件检查正确 | `test_replication_trigger` |
| 能力继承 | 80%+ 能力保留 | `test_capability_inheritance` |
| 变异机制 | 5-15% 变异率 | `test_mutation_rate` |
| 资源消耗 | 复制后资源正确扣除 | `test_resource_cost` |

---

*文档版本: 1.0*
*下一步: EmergenceLayer (Phase 3)*
