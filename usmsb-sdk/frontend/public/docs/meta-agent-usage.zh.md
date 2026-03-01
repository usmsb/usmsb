# Meta Agent 对话使用详解

> 深入了解 Meta Agent 的记忆、知识、工具和技能系统

---

## 1. Meta Agent 概述

Meta Agent 是基于 USMSB 模型构建的超级 Agent，具备以下核心能力：

- **九大通用动作**: Perception, Decision, Execution, Interaction, Transformation, Evaluation, Feedback, Learning, RiskManagement
- **多层次记忆系统**: 短期记忆、摘要记忆、用户画像
- **动态知识图谱**: 支持实体关系、因果链、时序演化
- **技能系统**: 动态加载和执行技能
- **工具系统**: 集成外部工具和服务

---

## 2. 记忆系统

Meta Agent 采用三层记忆架构，模拟人类记忆的工作方式。

### 2.1 短期记忆 (Short-term Memory)

**功能**: 保存最近 N 条对话消息

**配置参数**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import MemoryConfig

config = MemoryConfig(
    short_term_messages=20,    # 保留最近20条消息
    summary_threshold=30        # 超过30条触发摘要
)
```

**特点**:
- 存储原始对话消息
- 保持对话上下文连贯性
- 自动管理消息数量
- 超过阈值自动触发摘要

### 2.2 摘要记忆 (Summary Memory)

**功能**: 将较长对话压缩为摘要，保留关键信息

**触发条件**:
- 短期记忆超过 `summary_threshold` (默认30条)
- 用户明确要求总结
- 对话自然结束

**提取内容**:
- 关键主题 (`key_topics`)
- 重要决定 (`decisions`)
- 承诺事项 (`commitments`)
- 关键数据 (`key_data`)

**示例**:
```python
# 摘要记忆自动从对话中提取
summary = {
    "key_topics": ["项目计划", "预算分配", "时间表"],
    "decisions": ["确认采用敏捷开发", "预算定为10万"],
    "message_count": 35
}
```

### 2.3 用户画像 (User Profile)

**功能**: 长期存储用户偏好、承诺和知识

**数据内容**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import UserProfile

profile = UserProfile(
    user_id="user_123",
    preferences={
        "communication_style": "简洁",
        "preferred_language": "中文",
        "notification_time": "上午9点"
    },
    commitments=["下周一提交初稿", "周五前完成测试"],
    knowledge={
        "skills": ["Python", "JavaScript"],
        "projects": ["电商平台", "数据分析"]
    }
)
```

**持久化**:
- 使用 SQLite 数据库持久存储
- 支持跨会话记忆
- 自动更新和同步

### 2.4 记忆管理器 (Memory Manager)

**初始化**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import MemoryManager, MemoryConfig

# 创建配置
config = MemoryConfig(
    short_term_messages=20,
    summary_threshold=30,
    max_summaries=10,
    extract_preferences=True,
    importance_threshold=0.7
)

# 初始化管理器
memory = MemoryManager(
    db_path="./data/memory.db",
    config=config,
    llm_manager=llm_manager  # 可选，用于摘要生成
)

await memory.init()
```

**核心方法**:
```python
# 添加对话消息
await memory.add_message(
    conversation_id="conv_123",
    role="user",
    content="我想要开发一个电商网站"
)

# 获取记忆上下文
context = await memory.get_context(
    conversation_id="conv_123",
    include_short_term=True,
    include_summaries=True,
    include_profile=True
)

# 提取用户偏好
await memory.extract_preferences(
    conversation_id="conv_123",
    user_id="user_123"
)

# 保存承诺
await memory.add_commitment(
    user_id="user_123",
    commitment="下周一提交初稿",
    due_date="2026-03-02"
)
```

---

## 3. 知识图谱系统

Meta Agent 配备动态知识图谱，支持实体关系、因果链和时序演化。

### 3.1 知识节点 (Knowledge Node)

**结构**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import KnowledgeNode, KnowledgeStatus

node = KnowledgeNode(
    id="node_001",
    content="Python是一种高级编程语言",
    usmsb_element="info",  # USMSB要素映射
    status=KnowledgeStatus.NEW,
    confidence=0.9,         # 置信度 0-1
    importance=0.8,         # 重要性 0-1
    source="user_input"    # 来源
)
```

### 3.2 知识关系 (Knowledge Edge)

**关系类型**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import RelationType

# 支持的关系类型
IS_A = "is_a"           # 分类关系
HAS_A = "has_a"         # 拥有关系
CAUSES = "causes"        # 因果关系
USES = "uses"           # 使用关系
RELATES = "relates"      # 一般关联

# USMSB 要素关系
USMSB_AGENT = "agent"    # 主体
USMSB_OBJECT = "object"  # 客体
USMSB_GOAL = "goal"     # 目标
USMSB_RESOURCE = "resource"  # 资源
USMSB_RULE = "rule"     # 规则
USMSB_INFO = "info"     # 信息
USMSB_VALUE = "value"   # 价值
USMSB_RISK = "risk"     # 风险
USMSB_ENV = "environment"  # 环境
```

**示例**:
```python
edge = KnowledgeEdge(
    id="edge_001",
    source_id="node_python",
    target_id="node_programming_language",
    relation_type=RelationType.IS_A,
    weight=1.0,
    confidence=0.95
)
```

### 3.3 知识图谱管理器

**初始化和使用**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph(
    db_path="./data/knowledge.db"
)

await kg.init()

# 添加节点
node_id = await kg.add_node(
    content="Python是一种高级编程语言",
    usmsb_element="info"
)

# 添加关系
await kg.add_edge(
    source_id=node_id,
    target_id="node_language",
    relation_type=RelationType.IS_A
)

# 查询知识
results = await kg.query(
    keyword="Python",
    relation_type=RelationType.USES,
    min_confidence=0.7
)

# 推理查询
inferences = await kg.query_with_reasoning(
    start_node="node_problem",
    max_depth=3
)
```

### 3.4 USMSB 要素知识映射

知识图谱与 USMSB 九大要素对应：

| USMSB 要素 | 知识类型 | 示例 |
|------------|----------|------|
| Agent | 主体知识 | 用户信息、Agent能力 |
| Object | 客体知识 | 产品、服务、数据 |
| Goal | 目标知识 | 任务、计划、期望 |
| Resource | 资源知识 | 工具、资金、时间 |
| Rule | 规则知识 | 政策、协议、规范 |
| Information | 信息知识 | 事实、数据、消息 |
| Value | 价值知识 | 偏好、优先级、信念 |
| Risk | 风险知识 | 威胁、限制、注意事项 |
| Environment | 环境知识 | 上下文、场景、背景 |

---

## 4. 技能系统 (Skills)

技能是 Meta Agent 的可扩展能力单元。

### 4.1 定义技能

**基础结构**:
```python
from usmsb_sdk.core.skills import Skill, SkillMetadata, SkillCategory, SkillStatus, SkillParameter

class DataAnalysisSkill(Skill):
    def __init__(self):
        metadata = SkillMetadata(
            name="data_analysis",
            version="1.0.0",
            description="数据分析技能",
            category=SkillCategory.ANALYSIS,
            status=SkillStatus.ACTIVE
        )
        super().__init__(metadata)
        
        # 定义参数
        self.parameters = {
            "data_source": SkillParameter(
                name="data_source",
                type="string",
                description="数据源路径或URL",
                required=True
            ),
            "analysis_type": SkillParameter(
                name="analysis_type",
                type="string",
                description="分析类型",
                enum=["统计", "预测", "聚类"],
                required=True
            )
        }
        
        # 定义输出
        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="object",
                description="分析结果"
            )
        }
    
    async def execute(self, inputs, context=None):
        data = inputs["data_source"]
        analysis_type = inputs["analysis_type"]
        
        # 执行分析逻辑
        result = await self._analyze(data, analysis_type)
        
        return {"result": result}
```

### 4.2 技能分类

| 分类 | 说明 | 示例 |
|------|------|------|
| ANALYSIS | 分析技能 | 数据分析、趋势分析 |
| GENERATION | 生成技能 | 文本生成、代码生成 |
| TRANSFORMATION | 转换技能 | 格式转换、语言翻译 |
| COMMUNICATION | 通信技能 | 对话、邮件 |
| REASONING | 推理技能 | 逻辑推理、因果分析 |
| ACTION | 执行技能 | 自动化任务 |
| PERCEPTION | 感知技能 | 图像识别、语音识别 |
| LEARNING | 学习技能 | 知识提取 |
| PLANNING | 规划技能 | 任务规划 |
| EVALUATION | 评估技能 | 质量评估 |

### 4.3 技能注册和使用

```python
from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig, SkillDefinition

# 定义技能
skill = SkillDefinition(
    name="python_code",
    description="生成Python代码",
    parameters=[
        {
            "name": "task",
            "type": "string",
            "description": "要完成的任务"
        }
    ],
    returns="string",
    timeout=60
)

# 创建Agent并添加技能
config = AgentConfig(
    name="coder_agent",
    description="代码生成Agent",
    skills=[skill]
)

agent = MyAgent(config)

# 执行技能
result = await agent.execute_skill(
    "python_code",
    {"task": "实现快速排序"}
)
```

### 4.4 技能市场

```python
from usmsb_sdk.agent_sdk import MarketplaceManager

marketplace = MarketplaceManager(platform_url="http://localhost:8000")

# 发布技能
await marketplace.publish_skill(
    skill_definition=skill,
    price=0.01,  # 代币/次
    share_level="public"  # 公开/私有
)

# 搜索技能
skills = await marketplace.search_skills(
    category="analysis",
    min_rating=4.5
)
```

---

## 5. 工具系统 (Tools)

工具是 Meta Agent 与外部系统交互的能力。

### 5.1 内置工具

**平台管理工具**:
| 工具名称 | 功能 |
|----------|------|
| `start_node` | 启动节点 |
| `stop_node` | 停止节点 |
| `get_node_status` | 获取节点状态 |
| `get_config` | 获取配置 |
| `update_config` | 更新配置 |

**区块链工具**:
| 工具名称 | 功能 |
|----------|------|
| `create_wallet` | 创建钱包 |
| `get_balance` | 查询余额 |
| `stake` | 质押代币 |
| `unstake` | 取消质押 |
| `vote` | 投票 |
| `submit_proposal` | 提交提案 |

**通信工具**:
| 工具名称 | 功能 |
|----------|------|
| `chat_with_agent` | 与Agent对话 |
| `chat_with_human` | 与真人对话 |
| `broadcast_message` | 广播消息 |

### 5.2 自定义工具

```python
from usmsb_sdk.agent_sdk.tools import Tool, ToolRegistry

class WebSearchTool(Tool):
    name = "web_search"
    description = "搜索网络信息"
    parameters = {
        "query": {"type": "string", "description": "搜索关键词"}
    }
    
    async def execute(self, query: str):
        # 实现搜索逻辑
        results = await self._search(query)
        return {"results": results}

# 注册工具
registry = ToolRegistry()
registry.register(WebSearchTool())
```

### 5.3 工具调用

```python
# 通过Agent调用工具
response = await agent.execute_tool(
    "web_search",
    {"query": "USMSB模型是什么"}
)
```

---

## 6. 对话流程

### 6.1 完整对话流程

```
用户输入
    │
    ▼
┌─────────────────────┐
│  1. 感知 (Perception) │
│  - 解析输入          │
│  - 提取意图          │
│  - 识别实体          │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  2. 记忆检索         │
│  - 短期记忆          │
│  - 摘要记忆          │
│  - 用户画像          │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  3. 知识查询         │
│  - 知识图谱          │
│  - 相关信息          │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  4. 决策 (Decision) │
│  - 规划行动          │
│  - 选择工具/技能      │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  5. 执行 (Execution) │
│  - 调用工具          │
│  - 执行技能          │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  6. 评估 (Evaluation)│
│  - 检查结果          │
│  - 质量验证          │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  7. 记忆更新         │
│  - 保存对话          │
│  - 更新画像          │
│  - 更新知识          │
└─────────────────────┘
    │
    ▼
  用户输出
```

### 6.2 代码示例

```python
from usmsb_sdk.platform.external.meta_agent import MetaAgent, AgentConfig

# 初始化Meta Agent
config = AgentConfig(
    name="my_meta_agent",
    description="个人AI助手",
    skills=[...],      # 技能列表
    capabilities=[...] # 能力列表
)

agent = MetaAgent(config)
await agent.start()

# 对话
response = await agent.chat(
    message="帮我分析一下上周的销售数据",
    user_id="user_123",
    conversation_id="conv_001"
)

print(response.content)
```

---

## 7. 配置选项

### 7.1 AgentConfig 完整配置

```python
from usmsb_sdk.agent_sdk import AgentConfig, ProtocolConfig, ProtocolType

config = AgentConfig(
    # 身份信息
    name="my_agent",
    description="我的Agent",
    agent_id="agent_001",  # 自动生成
    version="1.0.0",
    owner="owner_wallet_address",
    tags=["ai", "assistant"],
    
    # 能力和技能
    capabilities=[
        CapabilityDefinition(
            name="text_generation",
            description="文本生成",
            category="nlp",
            level="advanced"
        )
    ],
    skills=[skill1, skill2],
    
    # 协议配置
    protocols={
        ProtocolType.A2A: ProtocolConfig(
            protocol_type=ProtocolType.A2A,
            enabled=True,
            host="0.0.0.0",
            port=8000
        ),
        ProtocolType.HTTP: ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            enabled=True
        )
    },
    
    # 网络配置
    network=NetworkConfig(
        platform_endpoints=["http://localhost:8000"],
        p2p_listen_port=9000
    ),
    
    # 安全配置
    security=SecurityConfig(
        auth_enabled=True,
        api_key="your_api_key"
    ),
    
    # 运行时设置
    auto_register=True,
    auto_discover=True,
    log_level="INFO",
    health_check_interval=30,
    heartbeat_interval=30
)
```

### 7.2 运行时配置

```python
# 设置回调
agent.on_state_change = async def(old_state, new_state):
    print(f"状态变更: {old_state} -> {new_state}")

agent.on_message = async def(message):
    print(f"收到消息: {message}")

# 获取状态
print(agent.state)  # AgentState.RUNNING
print(agent.is_running)  # True

# 获取指标
metrics = agent.metrics
print(metrics)
# {
#     "messages_received": 10,
#     "messages_sent": 8,
#     "skills_executed": 5,
#     "errors": 0,
#     "uptime": 3600.0
# }
```

---

## 8. 最佳实践

### 8.1 记忆系统使用建议

1. **合理设置阈值**: 根据对话频率调整 `short_term_messages` 和 `summary_threshold`
2. **定期提取偏好**: 在关键交互后调用 `extract_preferences()`
3. **管理承诺**: 使用 `add_commitment()` 记录重要承诺，并设置提醒

### 8.2 知识图谱使用建议

1. **结构化存储**: 将信息组织为节点和关系
2. **设置置信度**: 根据信息来源设置合适的置信度
3. **定期更新**: 通过推理更新和强化知识

### 8.3 技能设计建议

1. **单一职责**: 每个技能专注于一个功能
2. **明确定义**: 详细定义输入输出参数
3. **错误处理**: 实现完善的异常处理机制

---

## 9. 故障排查

### 9.1 常见问题与解决方案

| 问题分类 | 具体问题 | 可能原因 | 解决方案 |
|----------|----------|----------|----------|
| **记忆系统** | 记忆不持久 | 数据库路径权限不足 | 检查文件路径权限，确保有写入权限 |
| **记忆系统** | 记忆不持久 | 未初始化 | 确认 `await memory.init()` 已调用 |
| **记忆系统** | 摘要生成失败 | LLM未配置 | 配置 `llm_manager` 参数 |
| **技能系统** | 技能执行失败 | 参数定义错误 | 检查SkillParameter定义 |
| **技能系统** | 技能执行失败 | 技能未注册 | 确认技能已添加到Agent配置 |
| **技能系统** | 技能超时 | 执行时间过长 | 增加 `timeout` 设置 |
| **知识图谱** | 知识查询无结果 | 节点不存在 | 检查添加的节点ID |
| **知识图谱** | 推理结果不准确 | 置信度阈值过高 | 降低 `min_confidence` 参数 |
| **工具系统** | 工具调用失败 | 网络问题 | 检查网络连接 |
| **工具系统** | 工具调用超时 | 服务响应慢 | 增加timeout或检查服务状态 |
| **平台集成** | 无法连接到平台 | URL错误 | 检查 `platform_url` 配置 |
| **平台集成** | 认证失败 | API Key错误 | 检查 `api_key` 是否正确 |

### 9.2 日志调试

```python
import logging

# 启用调试日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Agent日志
agent = MetaAgent(config)
agent.logger.setLevel(logging.DEBUG)

# 特定模块日志
logging.getLogger('usmsb_sdk.agent_sdk').setLevel(logging.DEBUG)
logging.getLogger('usmsb_sdk.platform').setLevel(logging.DEBUG)
```

### 9.3 性能问题排查

```python
import time
from usmsb_sdk.logging_monitoring import MetricsCollector

# 创建性能监控
metrics = MetricsCollector(agent_name="debug_agent")

# 测量执行时间
start = time.time()
result = await agent.chat(message="测试消息")
duration = time.time() - start

print(f"执行时间: {duration:.3f}秒")
print(f"响应时间: {duration:.3f}秒")

# 检查指标
print(f"消息数: {metrics.get('messages_received')}")
print(f"错误数: {metrics.get('errors')}")
```

### 9.4 网络诊断

```python
import aiohttp

async def diagnose_platform_connection(platform_url: str):
    """诊断平台连接问题"""
    async with aiohttp.ClientSession() as session:
        # 检查健康端点
        try:
            async with session.get(f"{platform_url}/health") as resp:
                if resp.status == 200:
                    print("✓ 平台连接正常")
                else:
                    print(f"✗ 平台返回错误: {resp.status}")
        except aiohttp.ClientConnectorError:
            print("✗ 无法连接到平台")

        # 检查API端点
        try:
            async with session.get(f"{platform_url}/api/v1/agents") as resp:
                print(f"API状态: {resp.status}")
        except Exception as e:
            print(f"API错误: {e}")
```

---

## 10. 相关文档

- [Agent SDK 详解](./agent-sdk.md) - Agent SDK 完整文档
- [USMSB SDK 使用指南](./usmsb-sdk.md) - SDK 使用指南
- [系统架构](../03_architecture/system_architecture.md) - 系统架构
