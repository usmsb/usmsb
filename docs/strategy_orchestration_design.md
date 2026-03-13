# 智能记忆策略选择系统设计方案

## 一、背景

目前项目中存在多套记忆和召回系统：
1. **SmartRecall** - 基于LLM的9维智能召回
2. **原有记忆系统** - MemoryManager + 分层记忆
3. **AGIMemorySystem** - 认知科学分层记忆（5层：工作/情景/语义/程序/永久）
4. **原有知识库** - VectorKnowledgeBase + 知识图谱
5. **AGIDynamicKnowledgeGraph** - USMSB要素知识图谱

目标：做一个**策略编排层**，用LLM自动选择最优组合来完成用户任务。

---

## 二、排列组合设计

### 2.1 召回策略（Recall Strategy）

| 策略名称 | 实现类 | 特点 |
|---------|-------|------|
| SMART_RECALL | IntelligentRecall | LLM决策9维检索 |
| TRADITIONAL | MemoryManager | 分层记忆+摘要 |
| AGI_MEMORY | AGIMemorySystem | 认知5层+遗忘曲线 |
| HYBRID | 组合 | SmartRecall + AGIMemorySystem |

### 2.2 存储策略（Storage Strategy）

| 策略名称 | 实现类 | 特点 |
|---------|-------|------|
| VECTOR_KB | VectorKnowledgeBase | 向量知识库 |
| TRADITIONAL_DB | MemoryManager | 传统SQLite |
| AGI_KG | DynamicKnowledgeGraph | USMSB知识图谱 |
| HYBRID_STORAGE | 组合 | 知识图谱 + 向量 |

### 2.3 守护策略（Guardian Strategy）

| 策略名称 | 实现类 | 特点 |
|---------|-------|------|
| GUARDIAN_DAEMON | GuardianDaemon | 全面自我进化 |
| AGI_CONSOLIDATION | AGIMemorySystem | 仅记忆巩固 |
| NONE | 无 | 不启用守护 |

### 2.4 完整组合

```
召回策略 × 存储策略 × 守护策略 = 4 × 4 × 3 = 48 种组合
```

太多了，实际可简化为：

| 组合ID | 召回策略 | 存储策略 | 守护策略 |
|--------|---------|---------|---------|
| 1 | SMART_RECALL | VECTOR_KB | GUARDIAN_DAEMON |
| 2 | SMART_RECALL | AGI_KG | GUARDIAN_DAEMON |
| 3 | AGI_MEMORY | AGI_KG | AGI_CONSOLIDATION |
| 4 | TRADITIONAL | TRADITIONAL_DB | GUARDIAN_DAEMON |
| 5 | HYBRID | HYBRID_STORAGE | GUARDIAN_DAEMON |
| 6 | SMART_RECALL | AGI_KG | NONE |

---

## 三、LLM策略选择器

### 3.1 选择逻辑

```python
class StrategySelector:
    """LLM驱动的策略选择器"""

    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def select_strategy(
        self,
        user_task: str,
        context: Dict[str, Any]
    ) -> StrategyConfig:
        """
        基于任务特征选择最优策略组合
        """

        prompt = f"""
用户任务: {user_task}

任务上下文:
- 任务类型: {context.get('task_type')}
- 复杂度: {context.get('complexity')}
- 是否需要推理: {context.get('need_reasoning')}
- 是否涉及新知识: {context.get('new_knowledge')}
- 是否涉及实体: {context.get('has_entities')}
- 是否有错误历史: {context.get('has_error_history')}

可选策略:

【召回策略】
1. SMART_RECALL - LLM决策9维检索，适合复杂/模糊任务
2. TRADITIONAL - 分层记忆+摘要，适合简单明确任务
3. AGI_MEMORY - 认知5层+遗忘曲线，适合长期记忆
4. HYBRID - 组合策略

【存储策略】
1. VECTOR_KB - 向量知识库，适合精确检索
2. TRADITIONAL_DB - 传统SQLite，适合结构化数据
3. AGI_KG - USMSB知识图谱，适合关系推理
4. HYBRID_STORAGE - 组合存储

【守护策略】
1. GUARDIAN_DAEMON - 全面自我进化，适合长期任务
2. AGI_CONSOLIDATION - 仅记忆巩固，适合简单任务
3. NONE - 不启用守护

请选择最优组合并解释理由:
{{
    "recall_strategy": "SMART_RECALL/TRADITIONAL/AGI_MEMORY/HYBRID",
    "storage_strategy": "VECTOR_KB/TRADITIONAL_DB/AGI_KG/HYBRID_STORAGE",
    "guardian_strategy": "GUARDIAN_DAEMON/AGI_CONSOLIDATION/NONE",
    "reasoning": "为什么这样选择"
}}
"""

        response = await self.llm.chat(prompt)
        # 解析JSON返回...
        return strategy_config
```

### 3.2 任务特征提取

```python
async def extract_task_features(user_task: str) -> TaskFeatures:
    """提取任务特征"""

    features = {
        "task_type": await classify_task_type(user_task),
        "complexity": await assess_complexity(user_task),
        "need_reasoning": await check_reasoning_needed(user_task),
        "new_knowledge": await check_new_knowledge(user_task),
        "has_entities": await check_entities(user_task),
        "has_error_history": await check_error_history(user_task),
        "time_sensitivity": await check_time_sensitivity(user_task),
        "user_emphasis": await check_user_emphasis(user_task),
    }

    return features
```

---

## 四、策略编排器

### 4.1 核心类

```python
@dataclass
class StrategyConfig:
    """策略配置"""
    recall_strategy: str
    storage_strategy: str
    guardian_strategy: str
    reasoning: str


class StrategyOrchestrator:
    """策略编排器 - 管理多策略切换"""

    def __init__(self, llm_manager, config: StrategyConfig):
        self.llm = llm_manager
        self.config = config
        self.selector = StrategySelector(llm_manager)

        # 初始化各策略组件
        self._init_components()

    def _init_components(self):
        """初始化策略组件"""

        # 召回组件
        self.smart_recall = None
        self.traditional_memory = None
        self.agi_memory = None

        # 存储组件
        self.vector_kb = None
        self.traditional_db = None
        self.agi_kg = None

        # 守护组件
        self.guardian_daemon = None
        self.agi_consolidation = None

    async def select_and_execute(
        self,
        user_task: str,
        user_id: str = "",
        force_strategy: Optional[StrategyConfig] = None
    ) -> ExecutionResult:
        """
        选择策略并执行
        """

        # Step 1: 提取任务特征
        features = await self.extract_task_features(user_task)

        # Step 2: LLM选择策略（如果没有强制指定）
        if force_strategy:
            strategy = force_strategy
        else:
            strategy = await self.selector.select_strategy(user_task, features)

        logger.info(f"Selected strategy: {strategy}")

        # Step 3: 初始化所选策略的组件
        await self._setup_strategy(strategy)

        # Step 4: 执行任务
        result = await self._execute_with_strategy(
            user_task, user_id, strategy, features
        )

        # Step 5: 记录执行结果供学习
        await self._record_execution(user_task, strategy, result)

        return result

    async def _setup_strategy(self, strategy: StrategyConfig):
        """根据策略配置设置组件"""

        # 设置召回组件
        if strategy.recall_strategy == "SMART_RECALL":
            if not self.smart_recall:
                self.smart_recall = IntelligentRecall(...)
        # ... 其他策略

        # 设置存储组件
        # ...

        # 设置守护组件
        if strategy.guardian_strategy == "GUARDIAN_DAEMON":
            if not self.guardian_daemon:
                self.guardian_daemon = GuardianDaemon(...)
                await self.guardian_daemon.start()
        # ... 其他策略

    async def _execute_with_strategy(
        self,
        user_task: str,
        user_id: str,
        strategy: StrategyConfig,
        features: TaskFeatures
    ) -> ExecutionResult:
        """使用指定策略执行任务"""

        # 1. 召回相关记忆/知识
        if strategy.recall_strategy == "SMART_RECALL":
            context = await self.smart_recall.recall(user_task, {...})
        elif strategy.recall_strategy == "AGI_MEMORY":
            context = await self.agi_memory.build_context_prompt(user_task, user_id)
        # ... 其他策略

        # 2. 存储新知识
        if strategy.storage_strategy == "AGI_KG":
            await self.agi_kg.add_node(...)
        # ... 其他策略

        # 3. 触发守护进程（如需要）
        if strategy.guardian_strategy == "GUARDIAN_DAEMON":
            self.guardian_daemon.notify_task_complete()

        return ExecutionResult(...)

    async def _record_execution(
        self,
        user_task: str,
        strategy: StrategyConfig,
        result: ExecutionResult
    ):
        """记录执行结果，用于策略学习"""
        # 记录到经验库，供后续策略选择参考
        pass
```

---

## 五、集成到 MetaAgent

### 5.1 修改 MetaAgent

```python
class MetaAgent:
    async def __init__(self, config, ...):
        # ... 原有初始化

        # 新增：策略编排器
        self.orchestrator = StrategyOrchestrator(
            llm_manager=self.llm_manager,
            config=StrategyConfig(
                recall_strategy="SMART_RECALL",  # 默认
                storage_strategy="HYBRID_STORAGE",
                guardian_strategy="GUARDIAN_DAEMON"
            )
        )

        # 新增：支持策略切换
        self.current_strategy = None

    async def process_message(self, message, ...):
        # 选择策略
        strategy = await self.orchestrator.select_and_execute(
            user_task=message,
            user_id=user_id
        )

        # 使用选定的策略执行
        result = await self.orchestrator._execute_with_strategy(...)

        return result

    async def switch_strategy(self, new_strategy: StrategyConfig):
        """切换策略"""
        await self.orchestrator._setup_strategy(new_strategy)
        self.current_strategy = new_strategy
        logger.info(f"Strategy switched to: {new_strategy}")
```

### 5.2 配置项

```python
@dataclass
class MetaAgentConfig:
    # ... 原有配置

    # 策略配置
    default_recall_strategy: str = "SMART_RECALL"
    default_storage_strategy: str = "HYBRID_STORAGE"
    default_guardian_strategy: str = "GUARDIAN_DAEMON"

    # 策略选择配置
    enable_auto_strategy_selection: bool = True  # 是否自动选择策略
    strategy_selection_llm: Optional[str] = None  # 指定策略选择的LLM

    # 策略切换
    allow_runtime_switch: bool = True  # 是否允许运行时切换
```

---

## 六、执行流程图

```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│  1. 提取任务特征                     │
│     - 任务类型                       │
│     - 复杂度                         │
│     - 是否需要推理                   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. LLM策略选择器                    │
│     - 分析任务特征                   │
│     - 选择最优组合                   │
│     - 返回 StrategyConfig            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  3. 初始化策略组件                  │
│     - 召回组件                       │
│     - 存储组件                       │
│     - 守护组件                       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  4. 执行任务                         │
│     - 召回记忆/知识                  │
│     - 存储新知识                     │
│     - 触发守护                       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  5. 记录执行结果                     │
│     - 策略选择经验                   │
│     - 执行效果                       │
└─────────────────────────────────────┘
    │
    ▼
  返回结果
```

---

## 七、后续优化

### 7.1 策略学习
- 记录每次策略选择的效果
- 用强化学习优化策略选择
- 根据用户反馈调整

### 7.2 策略推荐
- 基于历史任务推荐策略
- 学习用户偏好

### 7.3 监控面板
- 展示当前使用的策略
- 显示策略切换历史
- 分析策略效果

---

**请确认方案是否符合你的预期，或者有其他修改意见？**
