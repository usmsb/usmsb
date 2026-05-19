# MetaAgent `start()` 重构设计方案

**日期**：2026-05-19
**状态**：待实施
**问题**：`start()` 做了 30+ 件事，混在一起；且 `main.py` 没有调用它

---

## 一、现状问题

### 1. `main.py` 没有调用 `start()`

```python
# main.py 只调用了这个：
await meta_agent._init_components()   # 只初始化基础组件
```

而 `start()` 包含的以下功能**全部未启用**：
- `StrategyRouter`（LLM 双轨策略路由）
- `L4Agent`（自我意识）
- `L5CollectiveIntelligence`（集体智能）
- `AutonomousLoop`（自主运行循环）
- `MetaAgentService`（精准匹配服务）
- `EvolutionEngine`（进化引擎）
- `SmartRecall`（智能召回）
- `GuardianDaemon`（守护进程）
- `_main_loop`（主循环）

### 2. `start()` 职责不清

当前 `start()` 做了四类事情：

| 类别 | 内容 | 应该在哪里 |
|------|------|----------|
| **初始化** | 注册工具、skills、LLM、DB | `_init_*()` |
| **启动** | SessionManager.start()、GoalEngine.start() | `_init_*()` 或 `_start_*()` |
| **运行时** | `_main_loop_task`、GuardianDaemon | `_start_runtime()` |
| **混杂** | EvolutionEngine、SmartRecall、ErrorLearning | `_init_learning()` |

---

## 二、重构方案

### 最终结构

```
agent.start()
  ├── _init_core()          # 基础组件（必须）
  ├── _init_advanced()      # 高级 AI 能力（可选）
  ├── _init_learning()      # 学习与进化系统（可选）
  └── _start_runtime()      # 启动后台任务（最后，永远运行）
```

### `_init_core()` — 基础组件（必须）

```python
async def _init_core(self):
    """必须初始化的基础组件，核心聊天功能依赖于此。"""
    # 1. Session 管理
    await self.session_manager.start()
    
    # 2. 底层组件初始化（LLM、向量KB、Context、Memory、Permission 等）
    await self._init_components()
    
    # 3. 工具注册（100+ 工具）
    await self._register_default_tools()
    
    # 4. Skills 加载
    await self.skills_manager.load_skills()
    await self._register_npm_skill()
    await self._register_git_skill()
    
    # 5. OpenHarness 集成
    await self._init_openharness()
    
    # 6. SkillsManager 标准初始化
    self.skills_manager.set_tool_registry(self.tool_registry)
    self.skills_manager.load_skills_from_directory(skills_dir)
    
    # 7. TaskExecutor（基础版本，无进度持久化）
    self.task_executor = TaskExecutor(self)
```

**无外部依赖**，任何场景下都可以安全调用。

---

### `_init_advanced()` — 高级 AI 能力（可选）

```python
async def _init_advanced(self):
    """高级 AI 能力，需要完整 LLM 支持。"""
    # 1. P2P 网络（Agent 发现）
    await self._init_p2p_network()
    
    # 2. StrategyRouter（LLM 双轨策略路由）⭐
    await self._init_strategy_router()
    
    # 3. L4 自我意识 Agent ⭐
    await self._init_l4_agent()
    
    # 4. L5 集体智能 ⭐
    await self._init_l5_collective()
    
    # 5. L3 自主运行循环（依赖 L4）⭐
    await self._init_autonomous_loop()
    
    # 6. MCP Gateway
    await self._init_mcp_gateway()
    
    # 7. A2A Agent 注册
    await self._register_a2a_agent()
    
    # 8. Platform Client + GeneCapsule
    await self._init_platform_client()
```

**依赖 LLM**，如果 LLM 初始化失败，这些组件会跳过初始化（non-critical）。

---

### `_init_learning()` — 学习与进化系统（可选）

```python
async def _init_learning(self):
    """学习、进化、记忆增强系统。"""
    # 1. 目标引擎启动
    await self.goal_engine.start()
    
    # 2. 进化引擎
    self.evolution_engine = EvolutionEngine(
        self.llm_manager, self.knowledge_base, self.conversation_manager,
    )
    await self.evolution_engine.start()
    
    # 3. 智能召回
    if self.config.smart_recall_enabled:
        self.smart_recall = IntelligentRecall(...)
    
    # 4. 错误驱动学习
    self.error_learning = ErrorDrivenLearning(...)
    
    # 5. TaskExecutor 进度持久化
    if self.task_executor:
        task_db_path = self.config.database.path.replace(".db", "_tasks.db")
        self.task_executor.init_progress_store(task_db_path)
```

**依赖 `_init_core()`**，需要数据库和 LLM 可用。

---

### `_start_runtime()` — 后台运行时（启动后永不返回）

```python
async def _start_runtime(self):
    """启动后台守护任务，必须是最后一步。"""
    # 1. GuardianDaemon（守护进程）
    if self.config.guardian_enabled:
        self.guardian_daemon = GuardianDaemon(...)
        await self.guardian_daemon.start()
    
    # 2. MetaAgentService（精准匹配，必须在所有组件就绪后）
    self.meta_agent_service = MetaAgentService(...)
    await self.meta_agent_service.init()
    
    # 3. 启动主循环（永远不返回）
    self._running = True
    self._main_loop_task = asyncio.create_task(self._main_loop())
    logger.info(f"Meta Agent {self.agent_id} started successfully")
```

**必须最后调用**，调用后会阻塞直到进程结束。

---

### `start()` — 统一入口

```python
async def start(self, enable_advanced: bool = True, enable_learning: bool = True):
    """
    启动 Meta Agent。
    
    Args:
        enable_advanced: 是否启用高级 AI 能力（L4/L5/StrategyRouter 等）
        enable_learning: 是否启用学习与进化系统
    """
    # Phase 1: 基础（必须）
    await self._init_core()
    
    # Phase 2: 高级（可选）
    if enable_advanced:
        await self._init_advanced()
    
    # Phase 3: 学习（可选）
    if enable_learning:
        await self._init_learning()
    
    # Phase 4: 运行时（永远最后）
    await self._start_runtime()
```

---

## 三、`main.py` 改造

### 改造前
```python
meta_agent = MetaAgent(MetaAgentConfig.from_env())
await meta_agent._init_components()  # 只初始化基础
```

### 改造后
```python
meta_agent = MetaAgent(MetaAgentConfig.from_env())
await meta_agent.start(
    enable_advanced=True,   # 启用 L4/L5/StrategyRouter
    enable_learning=True,   # 启用 Evolution/SmartRecall
)
# _start_runtime() 永远阻塞在这里，进程存活
```

---

## 四、参数化控制

通过环境变量也可以控制：

```bash
# 完整启动（默认）
python -m uvicorn usmsb_sdk.api.rest.main:app

# 仅基础模式（无高级 AI 能力）
USMSB_ENABLE_ADVANCED=false python -m uvicorn usmsb_sdk.api.rest.main:app

# 仅学习模式
USMSB_ENABLE_LEARNING=false python -m uvicorn usmsb_sdk.api.rest.main:app
```

---

## 五、关键依赖关系

```
_init_core()
  └── _init_components()
        ├── LLM Manager
        ├── Vector KB
        ├── Context Manager
        ├── Memory Manager
        ├── Conversation Manager
        ├── Knowledge Base
        ├── Wallet Manager
        └── Permission Manager

_init_advanced() 依赖 _init_core()
  ├── _init_p2p_network()         ← 独立
  ├── _init_strategy_router()      ← 依赖 LLM
  ├── _init_l4_agent()            ← 依赖 LLM
  ├── _init_l5_collective()       ← 依赖 LLM
  ├── _init_autonomous_loop()     ← 依赖 LLM + L4
  ├── _init_mcp_gateway()         ← 依赖 ToolRegistry
  ├── _register_a2a_agent()       ← 依赖 ToolRegistry
  └── _init_platform_client()     ← 独立

_init_learning() 依赖 _init_core()
  ├── GoalEngine.start()           ← 依赖 LLM
  ├── EvolutionEngine.start()      ← 依赖 LLM + KB
  ├── SmartRecall                 ← 依赖 LLM + Memory
  └── ErrorDrivenLearning         ← 依赖 LLM

_start_runtime() 依赖所有
  ├── GuardianDaemon              ← 依赖 LLM + Memory
  ├── MetaAgentService.init()     ← 依赖所有组件
  └── _main_loop()                ← 依赖所有组件
```

---

## 六、错误处理策略

每个 `_init_*()` 内部已经是 try/except，失败时打印 warning 并继续。

不会因为某个高级组件初始化失败而导致整个 Agent 无法启动。

---

## 七、实施步骤

1. 在 `agent.py` 中新增 `_init_core()`、`_init_advanced()`、`_init_learning()`、`_start_runtime()` 四个方法
2. 重构 `start()` 为统一调度器
3. 更新 `main.py` 的 lifespan，调用 `agent.start()`
4. 删除原来散落在 `start()` 里但属于 `_init_components()` 的代码（在 `_init_components()` 中已有，不需要移动）
5. 测试：基础模式 + 完整模式分别验证
