# Agent SDK 详解

> USMSB 平台完整的 Agent 开发框架
> 本指南提供构建智能体的完整文档，这些智能体可以在 USMSB（通用社会行为系统模型）平台生态系统中协作、交易和创造价值。

---

## 目录

1. [Agent SDK 概述](#1-agent-sdk-概述)
2. [核心组件](#2-核心组件)
3. [协议支持](#3-协议支持)
4. [消息处理](#4-消息处理)
5. [技能系统](#5-技能系统)
6. [能力系统](#6-能力系统)
7. [平台集成](#7-平台集成)
8. [高级功能](#8-高级功能)
9. [示例演示](#9-示例演示)
10. [最佳实践](#10-最佳实践)
11. [问题排查](#11-问题排查)

---

## 1. Agent SDK 概述

Agent SDK 是一个全面的框架，用于构建可以在 USMSB 平台生态系统中协作、交易和创造价值的 AI 智能体。这个 SDK 使开发者能够创建能够自主发现其他智能体、协作完成任务、进行服务交易，并为去中心化 AI 经济做出贡献的智能体。

**为什么要使用 Agent SDK？**

在传统软件开发中，应用程序是孤立运行的。Agent SDK 改变了这一范式，实现了：

- **自主协作**：智能体可以在无需人工干预的情况下协同工作
- **经济参与**：智能体可以通过提供服务赚取代币
- **自我组织**：智能体可以相互发现和连接
- **持续学习**：智能体可以从经验中改进

### 1.1 核心功能

SDK 提供以下核心功能：

| 功能 | 描述 | 使用场景 |
|---------|-------------|----------|
| **多协议支持** | A2A、MCP、P2P、HTTP、WebSocket、gRPC | 通过各种通信方式连接智能体 |
| **平台集成** | 市场、钱包、协商、协作 | 实现智能体之间的经济交易 |
| **生命周期管理** | 启动、停止、暂停、恢复 | 控制智能体状态和行为 |
| **技能系统** | 定义、注册、执行自定义技能 | 让智能体执行特定任务 |
| **自动发现** | 智能体自动发现和匹配 | 寻找合适的协作伙伴 |
| **学习系统** | 经验积累和知识共享 | 随着时间推移提升智能体性能 |

**场景示例：**

假设你正在构建一个软件开发平台。你可以创建多个专业化智能体：
- 一个 **ProductOwner** 智能体，分析用户需求
- 一个 **Architect** 智能体，设计技术方案
- 一个 **Developer** 智能体，编写代码
- 一个 **Reviewer** 智能体，检查代码质量

这些智能体可以相互通信、协作，甚至可以为它们的服务协商价格——这一切都由 Agent SDK 提供支持。

### 1.2 安装

```bash
# 从 PyPI 安装最新版本
pip install usmsb-sdk

# 安装指定版本
pip install usmsb-sdk==1.0.0

# 安装所有依赖
pip install usmsb-sdk[all]
```

### 1.3 版本要求

| 要求 | 最低版本 | 备注 |
|-------------|-----------------|-------|
| Python | 3.10+ | 需要 asyncio 支持 |
| asyncio | 内置 | 原生 async/await 支持 |
| pydantic | 2.0+ | 用于数据验证 |

---

## 2. 核心组件

本节介绍 Agent SDK 的基本构建块。在创建第一个智能体之前，理解这些组件至关重要。

### 2.1 BaseAgent - 基础类

**什么是 BaseAgent？**

BaseAgent 是所有智能体必须继承的父类。它就像一个"骨架"，提供了智能体所需的所有基本功能。它处理"繁琐但必要"的工作，让你能够专注于智能体的独特逻辑。

**为什么要使用 BaseAgent？**

- 它管理智能体的生命周期（启动、停止、暂停）
- 它处理传入和传出的消息
- 它提供日志记录和错误处理
- 它自动连接到平台

**需要重写的主要方法：**

| 方法 | 调用时机 | 用途 |
|--------|--------------|---------|
| `initialize()` | 智能体启动时 | 设置模型、连接、资源 |
| `handle_message()` | 收到消息时 | 处理传入消息 |
| `shutdown()` | 智能体停止时 | 清理资源 |

```python
from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig

class MyAgent(BaseAgent):
    """自定义智能体实现

    这是创建功能智能体的主要入口点。
    重写以下方法来定义智能体的行为。
    """

    async def initialize(self):
        """初始化 - 智能体启动时调用

        使用此方法进行一次性设置：
        - 加载 AI 模型或机器学习流程
        - 连接数据库或外部服务
        - 初始化配置或缓存
        - 注册技能和能力

        示例场景：
        - 加载用于文本分析的训练模型
        - 连接数据库获取数据
        - 初始化外部服务的 API 客户端
        """
        # 加载模型，连接数据库，设置资源
        self.logger.info(f"初始化 {self.name}")

        # 示例：加载简单的模型
        # self.model = await self.load_ai_model()

        # 示例：连接数据库
        # self.db = await self.connect_to_database()

    async def handle_message(self, message, session=None):
        """处理传入消息 - 核心业务逻辑

        这是智能体的核心。智能体收到的每条消息都会在这里处理。
        你可以决定如何处理每条消息。

        参数:
            message: 传入的消息对象，包含:
                - content: 实际数据/载荷
                - sender_id: 发送者
                - type: 消息类型
            session: 可选的会话上下文，用于有状态的对话

        返回:
            响应消息或包含结果的字典

        常见模式：
        1. 解析消息内容
        2. 执行某些操作（分析、转换等）
        3. 返回结果
        """
        # 处理消息并返回响应
        content = message.content
        self.logger.info(f"收到: {content}")
        return {"status": "processed", "content": content}

    async def shutdown(self):
        """清理 - 智能体停止时调用

        始终正确清理资源以避免：
        - 内存泄漏
        - 未关闭的连接
        - 未完成的操作

        这对以下内容特别重要：
        - 数据库连接
        - 文件句柄
        - GPU 内存
        - 外部 API 连接
        """
        self.logger.info(f"关闭 {self.name}")

        # 示例清理：
        # await self.db.close()
        # await self.model.unload()
```

### 2.2 AgentConfig - 配置智能体

**什么是 AgentConfig？**

AgentConfig 就像智能体的"护照"。它包含定义智能体行为、能力和连接方式的所有必要信息。

**为什么配置很重要？**

就像人需要身份证明文件一样，你的智能体需要配置才能：
- 被平台识别
- 定义其能力
- 设置安全选项
- 配置网络

```python
from usmsb_sdk.agent_sdk import (
    AgentConfig,
    ProtocolType,
    ProtocolConfig,
    NetworkConfig,
    SecurityConfig,
    CapabilityDefinition
)

# 创建包含所有选项的配置
config = AgentConfig(
    # === 基本身份信息 ===
    name="my_agent",                      # [必填] 唯一名称 - 其他智能体如何识别你的智能体
    description="我的自定义AI智能体",      # 用于发现的人类可读描述
    agent_id="unique_agent_id",          # [可选] 自定义 ID，如果省略则自动生成
    version="1.0.0",                     # 版本号，用于兼容性跟踪
    owner="wallet_address",              # 用于代币交易的钱包地址
    tags=["developer", "python", "ai"], # 用于发现的关键词 - 请具体！

    # === 能力：智能体能做什么 ===
    # 能力帮助其他智能体找到你的智能体进行协作
    capabilities=[
        CapabilityDefinition(
            name="coding",                # 能力的技术名称
            description="软件开发",       # 人类可读描述
            category="development",      # 类别：development、analysis、communication 等
            level="advanced"             # 技能级别：beginner、intermediate、advanced、expert
        )
    ],

    # === 协议配置：智能体如何通信 ===
    # 协议决定智能体如何相互通信
    protocols={
        ProtocolType.A2A: ProtocolConfig(
            protocol_type=ProtocolType.A2A,  # Agent-to-Agent 原生协议
            enabled=True,
            host="0.0.0.0",                  # 监听所有接口
            port=8000                         # 端口号（多个智能体使用不同端口）
        )
    },

    # === 网络配置：智能体如何连接 ===
    network=NetworkConfig(
        platform_endpoints=["http://localhost:8000"],  # 平台 API 端点
        p2p_listen_port=9000                          # 点对点连接端口
    ),

    # === 安全配置：保护智能体 ===
    security=SecurityConfig(
        auth_enabled=True,             # 启用认证
        api_key="your_api_key"         # 平台访问的 API 密钥
    ),

    # === 运行时配置：行为设置 ===
    auto_register=True,                # 启动时自动注册到平台？
    auto_discover=True,               # 自动发现其他智能体？
    log_level="INFO",                # 日志级别：DEBUG、INFO、WARNING、ERROR
    health_check_interval=30,         # 健康检查间隔（秒）
    heartbeat_interval=30,            # 心跳间隔（秒）（保持存活信号）
    ttl=90                           # 消息生存时间（秒）
)
```

### 2.3 配置参数详解

| 参数 | 类型 | 默认值 | 描述 | 示例场景 |
|-----------|------|---------|-------------|------------------|
| `name` | string | **必填** | 智能体唯一标识符 | "MyDataAnalyzer" |
| `description` | string | "" | 智能体功能描述 | "分析销售数据" |
| `agent_id` | string | 自动生成 | 唯一标识符 | "agent_abc123" |
| `version` | string | "1.0.0" | 语义版本 | "2.1.0" |
| `owner` | string | "" | 用于支付的钱包地址 | "0x1234..." |
| `tags` | list | [] | 搜索关键词 | ["python", "ml", "data"] |
| `capabilities` | list | [] | 智能体能做什么的列表 | 参见 CapabilityDefinition |
| `protocols` | dict | {} | 通信设置 | {"A2A": {...}} |
| `network` | NetworkConfig | None | 网络设置 | 端点、端口 |
| `security` | SecurityConfig | None | 安全设置 | API 密钥、认证 |
| `auto_register` | bool | True | 启动时自动加入平台？ | 生产环境设为 True |
| `auto_discover` | bool | True | 发现其他智能体？ | 协作时设为 True |
| `log_level` | string | "INFO" | 详细程度 | 测试时用 "DEBUG" |
| `health_check_interval` | int | 30 | 健康检查间隔（秒） | 生产环境用 60 |
| `heartbeat_interval` | int | 30 | 心跳间隔（秒） | 30 是标准值 |
| `ttl` | int | 90 | 消息超时（秒） | 长时间任务增加此值 |

### 2.4 CapabilityDefinition - 定义智能体能力

**什么是能力？**

能力是智能体向其他人提供的"技能"或"服务"。发现系统使用能力将你的智能体与需要专业技能的任务匹配。

**为什么定义能力？**

- 帮助其他智能体找到你的智能体
- 支持市场列表
- 支持自动任务路由

```python
from usmsb_sdk.agent_sdk import CapabilityDefinition

# 完整的能力定义
capability = CapabilityDefinition(
    name="coding",                                    # 技术标识符
    description="软件开发与实现",                     # 人类描述
    category="development",                          # 分组：development、analysis、communication、planning、execution
    level="expert",                                 # 技能级别：beginner、intermediate、advanced、expert
    metrics={                                         # 性能指标（可选但推荐）
        "success_rate": 0.95,                         # 95% 成功率
        "avg_completion_time": 120                    # 平均完成时间 120 秒
    }
)

# 类别及其典型能力：
# - development: coding, testing, debugging, deployment
# - analysis: data_analysis, trend_analysis, prediction
# - communication: dialogue, negotiation, customer_service
# - planning: task_planning, roadmapping, strategy
# - execution: automation, deployment, monitoring
```

### 2.5 快速开始 - 你的第一个智能体

**本节将引导你在几分钟内创建一个基本的智能体。**

```python
import asyncio
from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig

# ============================================================
# 方法 1：使用工厂函数（最快）
# ============================================================
# 用于快速原型设计或简单智能体
from usmsb_sdk.agent_sdk import create_agent

agent = create_agent(
    name="quick_agent",              # 你的智能体名称
    description="快速创建的智能体",  # 描述
    capabilities=["greeting"]       # 基本能力
)

# ============================================================
# 方法 2：扩展 BaseAgent（推荐用于生产环境）
# ============================================================
# 当你需要完全控制智能体行为时使用

class QuickAgent(BaseAgent):
    """一个响应消息的简单智能体

    此示例展示创建可接收和响应消息的功能智能体
    所需的最少代码。
    """

    async def initialize(self):
        """智能体启动时调用一次

        在此进行一次性设置：
        - 加载模型
        - 连接服务
        - 注册技能
        """
        self.logger.info("智能体初始化")

        # 示例：注册技能
        # self.register_skill(
        #     name="greet",
        #     description="打招呼",
        #     handler=self.greet_user
        # )

    async def handle_message(self, message, session=None):
        """每条传入消息都会调用此方法

        这是智能体核心逻辑所在。
        处理消息并返回响应。

        参数:
            message: 传入的消息（有 content、sender_id、type）
            session: 可选的会话上下文

        返回:
            响应数据（dict 或 Message）
        """
        # 简单回显响应
        content = message.content if hasattr(message, 'content') else message
        return {"response": f"你好！收到: {content}"}

    async def shutdown(self):
        """智能体停止时调用

        清理任何资源：
        - 关闭数据库连接
        - 保存状态
        - 释放 GPU 内存
        """
        self.logger.info("智能体关闭")


# ============================================================
# 运行你的智能体
# ============================================================

async def main():
    """主入口点 - 运行你的智能体"""

    # 步骤 1：创建配置
    config = AgentConfig(
        name="quick",                    # 智能体名称
        description="一个简单的演示智能体", # 描述
        log_level="INFO"                 # 日志级别
    )

    # 步骤 2：创建你的智能体
    agent = QuickAgent(config)

    # 步骤 3：初始化（设置）
    await agent.initialize()

    # 步骤 4：启动（注册并开始处理）
    await agent.start()
    print(f"智能体 '{agent.name}' 正在运行！")

    # 现在智能体可以：
    # - 接收消息
    # - 处理任务
    # - 与其他智能体协作

    # 要停止智能体：
    await agent.stop()
    print(f"智能体 '{agent.name}' 已停止")


# 运行智能体
asyncio.run(main())

# 预期输出：
# INFO - 智能体初始化
# INFO - 智能体 'quick' 已启动
# 智能体 'quick' 正在运行！
# INFO - 智能体关闭
```

---

## 3. 协议支持

**什么是协议？**

协议是智能体用来相互通信的"语言"。就像人类使用不同的语言一样，智能体可以根据不同情况使用不同的协议。

### 3.1 协议类型及使用场景

```python
from usmsb_sdk.agent_sdk import ProtocolType

# 可用协议及其使用场景：
ProtocolType.A2A        # Agent-to-Agent - 最适合智能体通信
                        # 使用场景：智能体需要交换结构化数据时

ProtocolType.MCP        # Model Context Protocol - 最适合 LLM 集成
                        # 使用场景：连接语言模型时

ProtocolType.P2P        # Peer-to-Peer - 最适合去中心化
                        # 使用场景：没有中央服务器时

ProtocolType.HTTP       # REST API - 最适合 Web 集成
                        # 使用场景：构建 Web 服务时

ProtocolType.WEBSOCKET  # 实时 - 最适合实时更新
                        # 使用场景：聊天、通知、流媒体

ProtocolType.GRPC       # 高性能 - 最适合速度
                        # 使用场景：需要低延迟时
```

### 3.2 启用和禁用协议

```python
# 启用带自定义配置的协议
config.enable_protocol(ProtocolType.A2A)

# 启用 HTTP 并指定端口
config.enable_protocol(ProtocolType.HTTP, ProtocolConfig(
    protocol_type=ProtocolType.HTTP,
    port=8001,                    # 使用 8001 而不是默认端口
    host="0.0.0.0"                # 监听所有接口
))

# 禁用不需要的协议
config.disable_protocol(ProtocolType.P2P)

# 检查已启用的协议
enabled = config.get_enabled_protocols()
print(f"活跃协议: {enabled}")
```

---

## 4. 消息处理

**什么是消息？**

消息是智能体之间通信的方式。可以把它们想象成智能体之间的电子邮件或聊天消息。每条消息包含：
- **内容**：实际数据或请求
- **发送者**：谁发送的
- **接收者**：谁应该收到
- **类型**：这是什么类型的消息

### 4.1 消息结构

```python
from usmsb_sdk.agent_sdk import Message, MessageType

# 创建消息
message = Message(
    message_id="msg_001",                    # 唯一标识符
    type=MessageType.REQUEST,               # REQUEST、RESPONSE、NOTIFICATION、ERROR
    sender_id="sender_agent",                # 发送者
    receiver_id="receiver_agent",            # 接收者
    content={"task": "analyze data", "data": {...}},  # 实际载荷
    metadata={
        "conversation_id": "conv_001",       # 用于会话线程
        "timestamp": "2026-02-27T10:00:00Z"  # 发送时间
    }
)

# 访问消息属性
print(message.content)     # {"task": "analyze data", "data": {...}}
print(message.sender_id)  # "sender_agent"
print(message.type)      # MessageType.REQUEST
```

### 4.2 消息类型详解

| 类型 | 使用时机 | 示例 |
|------|-------------|---------|
| **REQUEST** | 请求其他智能体执行某些操作时 | "你能分析这些数据吗？" |
| **RESPONSE** | 响应请求时 | "这是分析结果" |
| **NOTIFICATION** | 通知而不期望回复时 | "任务成功完成" |
| **ERROR** | 出错时 | "无法处理请求" |

### 4.3 处理消息 - 构建消息处理器

```python
class MyAgent(BaseAgent):
    """具有全面消息处理功能的示例智能体"""

    async def handle_message(self, message, session=None):
        """主要消息处理方法

        在此决定如何处理传入的消息。
        不同的消息类型可能需要不同的处理方式。
        """

        # 提取内容以便更容易访问
        content = message.content if hasattr(message, 'content') else message

        # 根据消息类型路由
        if message.type == MessageType.REQUEST:
            # 处理服务请求
            return await self.handle_request(content)

        elif message.type == MessageType.NOTIFICATION:
            # 处理通知（不需要响应）
            return await self.handle_notification(content)

        elif message.type == MessageType.ERROR:
            # 处理错误消息
            return await self.handle_error(content)

        # 默认：确认收到
        return Message(
            type=MessageType.RESPONSE,
            sender_id=self.agent_id,
            receiver_id=message.sender_id,
            content={"status": "processed"}
        )

    async def handle_request(self, content):
        """处理 REQUEST 类型消息

        REQUEST 消息请求你的智能体执行工作。
        这就是你智能体主要功能所在。
        """
        task_type = content.get("type", "unknown")

        if task_type == "analyze":
            return await self.analyze_data(content)
        elif task_type == "process":
            return await self.process_data(content)
        else:
            return {"error": f"未知任务类型: {task_type}"}

    async def handle_notification(self, content):
        """处理 NOTIFICATION 类型消息

        通知是单向消息，用于告知事件。
        你确认但不响应。
        """
        self.logger.info(f"收到通知: {content}")
        return {"status": "acknowledged"}

    async def handle_error(self, content):
        """处理 ERROR 类型消息"""
        self.logger.error(f"对等方错误: {content}")
        return {"status": "error_received"}
```

### 4.4 向其他智能体发送消息

```python
# 向另一个智能体发送消息
response = await agent.send_message(
    receiver="Reviewer",                              # 目标智能体名称
    content={
        "type": "code_submission",                   # 此消息的内容
        "task": "用户登录API",                       # 任务详情
        "code": "...",                                # 要审查的代码
        "priority": "high"                           # 可选优先级
    },
    message_type=MessageType.REQUEST                  # 消息类型
)

# 访问消息历史
history = agent.message_history
for msg in history:
    print(f"来自: {msg.sender_id}, 内容: {msg.content}")
```

---

## 5. 技能系统

**什么是技能？**

技能是智能体可以按需执行的特定能力。把技能想象成可以远程调用的"函数"或"方法"。

**为什么要使用技能系统？**

- **可发现性**：其他智能体可以找到你的智能体能做什么
- **结构化输入/输出**：每个技能都有定义的参数和返回类型
- **执行控制**：内置超时和速率限制
- **远程执行**：技能可以通过网络调用

### 5.1 SkillDefinition - 定义技能

```python
from usmsb_sdk.agent_sdk import SkillDefinition, SkillParameter

# 完整的技能定义，包含所有选项
skill = SkillDefinition(
    name="data_analysis",                    # 唯一技能名称
    description="分析数据并生成洞察",          # 技能功能

    # 参数：技能需要什么才能工作
    parameters=[
        SkillParameter(
            name="data_source",              # 参数名称
            type="string",                   # 数据类型：string、int、float、bool、object
            description="输入数据源",         # 此参数是什么
            required=True                     # 必须提供？
        ),
        SkillParameter(
            name="method",
            type="string",
            description="要使用的分析方法",
            default="auto",                  # 如果不提供则使用默认值
            enum=["auto", "statistical", "ml"]  # 允许的值
        ),
        SkillParameter(
            name="output_format",
            type="string",
            description="如何返回结果",
            default="json"                   # 选项：json、csv、html
        )
    ],

    returns="object",                        # 技能返回什么
    timeout=60,                              # 最大执行时间（秒）
    rate_limit=100                           # 每分钟最大调用次数
)
```

### 5.2 向智能体添加技能

```python
# ============================================================
# 方法 1：在配置中定义技能
# ============================================================
# 适用于：不会改变的静态技能

config = AgentConfig(
    name="my_agent",
    skills=[
        SkillDefinition(
            name="analyze",
            description="数据分析技能",
            parameters=[
                SkillParameter(name="data", type="object", required=True)
            ]
        ),
        SkillDefinition(
            name="transform",
            description="数据转换技能",
            parameters=[
                SkillParameter(name="input", type="object", required=True),
                SkillParameter(name="format", type="string", default="json")
            ]
        )
    ]
)

# ============================================================
# 方法 2：运行时动态注册
# ============================================================
# 取决于运行时配置的技能

class DeveloperAgent(BaseAgent):
    """在初始化时注册技能的智能体"""

    async def initialize(self):
        """智能体启动时注册技能"""

        # 注册 implement_feature 技能
        self.register_skill(
            name="implement_feature",
            description="根据规范实现软件功能",
            handler=self._implement_feature,        # 要调用的函数
            parameters={
                "task": "带有需求的任务描述",
                "design": "设计文档或规范"
            }
        )

        # 注册 write_tests 技能
        self.register_skill(
            name="write_tests",
            description="为代码编写单元测试",
            handler=self._write_tests,
            parameters={
                "code": "要测试的源代码",
                "feature": "功能名称或描述"
            }
        )

    async def _implement_feature(self, params):
        """技能的实际实现"""
        task = params.get("task", {})
        design = params.get("design", {})

        # 你的实现逻辑
        implementation = {
            "task_id": task.get("id", "unknown"),
            "title": task.get("title", "未命名"),
            "code": "生成的代码在这里",
            "status": "implemented",
            "lines_of_code": 150,
        }

        return implementation

    async def _write_tests(self, params):
        """编写测试实现"""
        feature = params.get("feature", "feature")

        test_cases = [
            {"name": f"test_{feature}_success", "type": "unit", "status": "pass"},
            {"name": f"test_{feature}_error", "type": "unit", "status": "pass"},
        ]

        return {
            "feature": feature,
            "test_cases": test_cases,
            "coverage": 0.92,
        }
```

### 5.3 执行技能

```python
# 内部执行技能（在同一个智能体内）
result = await agent.execute_skill(
    "analyze",                                        # 技能名称
    {"data_source": "db://sales", "method": "statistical"}  # 参数
)

# 使用命名参数执行
result = await agent.execute_skill(
    "implement_feature",
    {
        "task": {
            "id": "TASK-001",
            "title": "登录功能",
            "description": "实现用户认证"
        },
        "design": {
            "type": "REST API",
            "endpoints": ["/login", "/logout", "/register"]
        }
    }
)

# 检查结果
print(f"实现状态: {result['status']}")
print(f"代码行数: {result['lines_of_code']}")
```

---

## 6. 能力系统

**什么是能力？**

能力代表智能体的专长。用于：
- **发现**：根据特定技能查找智能体
- **市场**：列出服务
- **匹配**：自动将任务与智能体配对

### 6.1 定义能力

```python
from usmsb_sdk.agent_sdk import CapabilityDefinition

# 为开发者智能体定义多个能力
capabilities = [
    CapabilityDefinition(
        name="coding",                        # 技术标识符
        description="软件开发",              # 人类可读
        category="development",               # 分组
        level="expert",                       # 技能级别
        metrics={
            "success_rate": 0.95,            # 性能指标
            "avg_completion_time": 120       # 秒
        }
    ),
    CapabilityDefinition(
        name="testing",
        description="单元测试和集成测试",
        category="development",
        level="advanced",
        metrics={"coverage": 0.90}
    ),
    CapabilityDefinition(
        name="debugging",
        description="缺陷检测和修复",
        category="development",
        level="advanced"
    )
]

# 或者：动态注册
class DeveloperAgent(BaseAgent):
    async def initialize(self):
        # 运行时注册能力
        self.register_capability(
            name="coding",
            description="代码实现",
            confidence=0.9                    # 智能体的置信度 (0-1)
        )
        self.register_capability(
            name="testing",
            description="单元测试",
            confidence=0.85
        )
        self.register_capability(
            name="debugging",
            description="调试排错",
            confidence=0.8
        )
```

### 6.2 能力等级详解

| 等级 | 描述 | 使用时机 |
|-------|-------------|-------------|
| **beginner** | 基本功能，学习中 | 新智能体，简单任务 |
| **intermediate** | 可以处理常见情况 | 有指导的生产环境 |
| **advanced** | 能力强，问题少 | 可靠处理复杂任务 |
| **expert** | 顶级，处理边缘情况 | 关键生产系统 |

### 6.3 能力类别

| 类别 | 典型能力 |
|----------|---------------------|
| **development** | coding, testing, debugging, deployment, refactoring |
| **analysis** | data_analysis, trend_analysis, prediction, reporting |
| **communication** | dialogue, negotiation, customer_service, translation |
| **planning** | task_planning, roadmapping, strategy, scheduling |
| **execution** | automation, deployment, monitoring, scaling |

---

## 7. 平台集成

**什么是平台集成？**

平台集成将你的智能体连接到 USMSB 生态系统，实现：
- **经济交易**：赚取和消费代币
- **市场**：提供和寻找服务
- **协作**：与其他智能体一起工作
- **发现**：查找相关智能体和任务

### 7.1 连接平台

```python
from usmsb_sdk.agent_sdk import PlatformClient

# 创建平台客户端
platform = PlatformClient(
    platform_url="http://localhost:8000",   # 平台 API 端点
    api_key="your_api_key",                 # 你的认证密钥
    timeout=30                               # 请求超时（秒）
)

# 测试连接
is_connected = await platform.health_check()

if is_connected:
    print("✅ 成功连接到平台！")
else:
    print("❌ 连接失败。请检查 URL 和 API 密钥。")
```

### 7.2 注册智能体

```python
# 选项 1：自动注册（在 AgentConfig 中配置）
# 设置 auto_register=True
config = AgentConfig(
    name="my_agent",
    auto_register=True      # 智能体启动时自动注册
)
agent = MyAgent(config)
await agent.initialize()
await agent.start()         # 注册在这里发生

# 选项 2：手动注册
await agent.register_to_platform()

# 检查注册状态
status = agent.registration_status
print(f"注册状态: {status}")  # "registered"、"pending"、"failed"
```

### 7.3 市场服务

**什么是市场？**

市场是智能体可以：
- **发布服务**：向其他人提供他们的能力
- **寻找服务**：发现提供所需服务的智能体
- **订阅需求**：获取与技能匹配的任务通知

```python
from usmsb_sdk.agent_sdk import MarketplaceManager, ServiceDefinition

# 通过智能体访问市场
marketplace = agent.marketplace

# ============================================================
# 发布你的服务
# ============================================================

service = ServiceDefinition(
    name="数据分析服务",                      # 服务名称
    description="专业数据分析和洞察",          # 描述
    price=0.01,                              # 每次请求的价格（VIB 代币）
    capabilities=["analysis", "visualization"],  # 你提供的内容
    tags=["data", "analytics", "python"],    # 搜索关键词

    # 附加选项：
    # max_concurrent=5,                        # 最大并发请求数
    # timeout=300,                             # 服务超时
    # rating=4.5,                              # 你的评分
    # completed_tasks=100                      # 业绩记录
)

# 发布到市场
service_id = await marketplace.publish_service(service)
print(f"✅ 服务已发布！ID: {service_id}")

# ============================================================
# 寻找服务
# ============================================================

# 搜索服务
services = await marketplace.search_services(
    category="data",           # 按类别筛选
    min_rating=4.0,            # 最低评分
    max_price=0.1,            # 最高价格
    capabilities_needed=["analysis"]  # 需要的技能
)

for svc in services:
    print(f"- {svc.name}: {svc.description} (${svc.price}/请求)")

# ============================================================
# 响应需求
# ============================================================

# 获取与你的技能匹配的任务通知
demands = await marketplace.get_demands(
    skills=["python", "web_development"],
    min_budget=100,            # 最低预算
    max_budget=5000           # 最高预算
)

for demand in demands:
    print(f"- 任务: {demand.title}")
    print(f"  预算: {demand.budget} VIB")
    print(f"  截止日期: {demand.deadline}")
```

### 7.4 钱包操作

**什么是钱包？**

钱包处理智能体的所有代币交易：
- 查看余额
- 接收服务付款
- 为其他智能体的服务付款
- 质押代币获得好处

```python
wallet = agent.wallet

# ============================================================
# 查看余额
# ============================================================

balance = await wallet.get_balance()
print(f"当前余额: {balance} VIB")

# 获取详细账户信息
account = await wallet.get_account()
print(f"地址: {account.address}")
print(f"已质押: {account.staked} VIB")
print(f"可用: {account.available} VIB")

# ============================================================
# 质押代币
# ============================================================

# 质押以获得好处（更好的费率、优先访问）
stake_result = await wallet.stake(
    amount=1000,              # 质押数量
    duration=30               # 天数
)
print(f"✅ 质押 {stake_result.amount} VIB，{stake_result.duration} 天")

# ============================================================
# 转账代币
# ============================================================

# 转账到其他地址
tx = await wallet.transfer(
    to="0xABC123...",        # 接收者地址
    amount=10                # VIB 数量
)
print(f"✅ 转账已提交！交易: {tx.hash}")

# 等待确认
receipt = await tx.wait()
print(f"已在区块确认: {receipt.block_number}")
```

### 7.5 协商服务

**什么是协商？**

协商使智能体能够讨论和达成协作条款。这对于以下方面至关重要：
- 同意价格
- 设定截止日期
- 定义交付物

```python
negotiation = agent.negotiation

# ============================================================
# 开始协商
# ============================================================

session = await negotiation.create_session(
    counterpart="agent_002",              # 协商对象
    context={
        "task": "开发网站",
        "budget": 5000,
        "timeline": "2 周"
    }
)

print(f"✅ 协商会话已创建: {session.id}")

# ============================================================
# 报价
# ============================================================

# 提交你的条款
await negotiation.make_offer(
    session_id=session.id,
    terms={
        "price": 4500,                    # 你的价格
        "deadline": "2026-03-15",         # 交付日期
        "milestones": [                   # 付款里程碑
            {"name": "设计", "amount": 1000},
            {"name": "开发", "amount": 2500},
            {"name": "部署", "amount": 1000}
        ]
    }
)

# ============================================================
# 响应报价
# ============================================================

# 接受报价
await negotiation.accept_offer(session_id=session.id)

# 或者还价
await negotiation.counter_offer(
    session_id=session.id,
    terms={
        "price": 4000,
        "deadline": "2026-03-20"
    }
)

# 获取协商历史
history = await negotiation.get_history(session_id=session.id)
```

### 7.6 协作服务

**什么是协作？**

协作使多个智能体能够共同处理共享任务。它提供：
- 任务分配和跟踪
- 角色管理
- 进度监控

```python
collaboration = agent.collaboration

# ============================================================
# 创建协作会话
# ============================================================

collab = await collaboration.create_session(
    name="项目协作",                          # 项目名称
    participants=["ProductOwner", "Architect", "Developer", "Reviewer"],  # 团队成员
    roles={
        "ProductOwner": "协调员",            # 定义需求
        "Architect": "设计师",              # 创建技术设计
        "Developer": "开发者",              # 编写代码
        "Reviewer": "审查员"               # 检查质量
    }
)

print(f"✅ 协作已创建: {collab.id}")

# ============================================================
# 分配任务
# ============================================================

task = await collaboration.assign_task(
    session_id=collab.id,
    assignee="Developer",                  # 谁做任务
    description="实现用户认证",
    deadline="2026-03-10",
    priority="high"
)

print(f"✅ 任务已分配: {task.id}")

# ============================================================
# 跟踪进度
# ============================================================

# 获取整体进度
progress = await collaboration.get_progress(session_id=collab.id)

print(f"进度: {progress.completed_tasks}/{progress.total_tasks} 任务")
print(f"状态: {progress.status}")  # "not_started"、"in_progress"、"completed"

# 获取特定任务状态
task_status = await collaboration.get_task_status(task_id=task.id)
```

### 7.7 发现服务

**什么是发现？**

发现帮助智能体根据以下条件找到彼此：
- 能力
- 声誉
- 价格
- 可用性

```python
discovery = agent.discovery

# ============================================================
# 简单搜索
# ============================================================

agents = await discovery.search_agents(
    capabilities=["python", "data_analysis"],  # 需要的技能
    online_only=True,                          # 仅在线智能体
    min_reputation=4.0                         # 最低评分
)

for agent_info in agents:
    print(f"- {agent_info.name}: {agent_info.description}")
    print(f"  评分: {agent_info.rating}")
    print(f"  能力: {agent_info.capabilities}")

# ============================================================
# 智能推荐
# ============================================================

recommendations = await discovery.get_recommendations(
    task="构建电商网站",
    constraints={
        "budget": 5000,
        "timeline": "2 周",
        "technologies": ["React", "Node.js"]
    }
)

for rec in recommendations:
    print(f"推荐: {rec.agent.name}")
    print(f"  匹配分数: {rec.score}")
    print(f"  价格: {rec.estimated_cost} VIB")

# ============================================================
# 增强的多维度搜索
# ============================================================

from usmsb_sdk.agent_sdk import EnhancedDiscoveryManager, SearchCriteria

enhanced = EnhancedDiscoveryManager(platform_url="http://localhost:8000")

# 使用加权维度搜索
results = await enhanced.search(
    criteria=SearchCriteria(
        task="开发 API 服务",

        # 要考虑的维度
        dimensions=["skill", "reputation", "price"],

        # 每个维度的重要程度（必须总和为 1.0）
        weights=[0.4, 0.3, 0.3]  # 40% 技能、30% 声誉、30% 价格

        # 附加筛选条件
        min_success_rate=0.9,
        max_delivery_time=7
    )
)
```

---

## 8. 高级功能

本节介绍构建复杂智能体的高级功能。

### 8.1 学习系统

**什么是学习系统？**

学习系统允许智能体：
- 记录经验
- 从成功和失败中学习
- 与其他智能体共享知识
- 随着时间推移改进

```python
learning = agent.learning

# ============================================================
# 记录经验
# ============================================================

await learning.add_experience(
    task_type="web_development",
    techniques=["React", "Node.js", "PostgreSQL"],
    outcome="success",              # "success"、"failure"、"partial"
    rating=5,                      # 1-5 评分
    duration=3600,                  # 花费时间（秒）

    # 附加上下文
    notes="使用 JWT 进行身份验证"
)

# ============================================================
# 获取洞察
# ============================================================

insights = await learning.get_insights(
    task_type="web_development"
)

print(f"最佳技术: {insights.best_techniques}")
print(f"成功率: {insights.success_rate}")
print(f"平均时长: {insights.avg_duration}s")

# ============================================================
# 性能分析
# ============================================================

analysis = await learning.get_performance_analysis()

print(f"总任务数: {analysis.total_tasks}")
print(f"成功率: {analysis.success_rate}")
print(f"最常用: {analysis.most_used_techniques}")
```

### 8.2 基因胶囊 - 知识管理

**什么是基因胶囊？**

基因胶囊是一个复杂的知识管理系统，可以：
- 将经验存储为"基因"
- 将新任务与相关过去经验匹配
- 实现智能体之间的知识转移

```python
gene = agent.gene_capsule

# ============================================================
# 添加经验基因
# ============================================================

await gene.add_experience(
    task_type="data_analysis",
    techniques=["pandas", "numpy", "visualization"],
    outcome="success",
    quality_score=0.95
)

# ============================================================
# 查找相关经验
# ============================================================

matches = await gene.get_matches(
    task_requirements={
        "task_type": "data_analysis",
        "required_skills": ["pandas", "visualization"]
    },
    match_threshold=0.8          # 最低相似度 (0-1)
)

for match in matches:
    print(f"匹配: {match.task_type}")
    print(f"  相似度: {match.similarity}")
    print(f"  技术: {match.techniques}")
```

### 8.3 工作流管理

**什么是工作流管理？**

工作流允许你通过一系列步骤协调多个智能体。每个步骤可以由不同的智能体执行。

```python
from usmsb_sdk.agent_sdk import WorkflowManager

workflow = WorkflowManager(platform_url="http://localhost:8000")

# ============================================================
# 创建工作流
# ============================================================

wf = await workflow.create_workflow(
    name="数据处理管道",
    steps=[
        {
            "name": "collect",
            "agent": "collector_agent",
            "action": "collect_data",
            "params": {"source": "database", "limit": 1000}
        },
        {
            "name": "process",
            "agent": "processor_agent",
            "action": "clean_data",
            "depends_on": ["collect"]  # 等待 collect 完成后
        },
        {
            "name": "analyze",
            "agent": "analyzer_agent",
            "action": "analyze",
            "depends_on": ["process"]  # 等待 process 完成后
        }
    ]
)

print(f"✅ 工作流已创建: {wf.id}")

# ============================================================
# 执行工作流
# ============================================================

result = await workflow.execute(
    workflow_id=wf.id,
    input_data={"source": "sales_db"}
)

print(f"状态: {result.status}")
print(f"结果: {result.output}")

# ============================================================
# 监控进度
# ============================================================

status = await workflow.get_status(workflow_id=wf.id)
print(f"步骤: {status.current_step}")
print(f"进度: {status.progress}%")
```

### 8.4 HTTP 服务

将你的智能体公开为 REST API 以便 Web 集成。

```python
from usmsb_sdk.agent_sdk import HTTPServer

server = HTTPServer(
    agent=agent,
    host="0.0.0.0",
    port=8000
)
await server.start()

# 或使用便捷函数
await run_agent_with_http(agent, host="0.0.0.0", port=8000)
```

**可用端点：**

| 方法 | 端点 | 描述 |
|--------|----------|-------------|
| POST | /chat | 向智能体发送消息 |
| GET | /agents/{id} | 获取智能体信息 |
| POST | /skills/{name}/execute | 执行特定技能 |
| GET | /health | 健康检查端点 |
| GET | /metrics | 获取智能体指标 |

### 8.5 P2P 服务

以点对点模式运行智能体，实现去中心化通信。

```python
from usmsb_sdk.agent_sdk import P2PServer

server = P2PServer(
    agent=agent,
    listen_port=9000,
    bootstrap_nodes=["/ip4/127.0.0.1/tcp/9001"]
)
await server.start()

# 或使用便捷函数
await run_agent_with_p2p(agent, listen_port=9000)
```

### 8.6 事件钩子

订阅智能体事件以进行自定义处理。

```python
# ============================================================
# 状态变更钩子
# ============================================================
# 智能体状态更改时调用（启动、停止、暂停、恢复）

async def on_state_change(old_state, new_state):
    """处理状态转换

    参数:
        old_state: 之前的状态（initializing、running、paused、stopped）
        new_state: 新状态
    """
    print(f"状态变更: {old_state} -> {new_state}")

    # 示例：状态变更时发送通知
    # if new_state == "running":
    #     await notify_admin(f"智能体现在正在运行！")

agent.on_state_change(on_state_change)

# ============================================================
# 消息钩子
# ============================================================
# 每条传入消息都调用

async def on_message(message):
    """处理传入消息

    用于：
    - 记录所有消息
    - 筛选消息
    - 自定义路由
    """
    print(f"收到消息: {message.content}")

    # 示例：保存到审计日志
    # await audit_log.save(message)

agent.on_message(on_message)

# ============================================================
# 错误钩子
# ============================================================

async def on_error(error):
    """处理错误"""
    print(f"发生错误: {error}")
    await alert_team(error)

agent.on_error(on_error)
```

### 8.7 指标和监控

监控智能体的性能和健康状况。

```python
# 获取当前指标
metrics = agent.metrics

print("=== 智能体指标 ===")
print(f"接收消息数: {metrics.get('messages_received', 0)}")
print(f"发送消息数: {metrics.get('messages_sent', 0)}")
print(f"执行技能数: {metrics.get('skills_executed', 0)}")
print(f"错误数: {metrics.get('errors', 0)}")
print(f"运行时间: {metrics.get('uptime', 0)} 秒")
print(f"状态: {metrics.get('state', 'unknown')}")

# 自定义指标
agent.metrics.increment("custom_counter")
agent.metrics.set_gauge("memory_usage", 1024)
```

---

## 9. 示例演示

本节提供完整的、可运行的示例，展示真实的智能体开发。

### 9.1 软件开发团队演示

**概念：** 创建 5 个专业化智能体的团队，遵循现实的开发工作流程进行协作开发软件。

**团队结构：**

| 角色 | 职责 | HTTP 端口 | 能力 |
|------|-----------------|-----------|--------------|
| **ProductOwner** | 需求分析、任务拆分、验收标准 | 8081 | requirement_analysis, prioritization |
| **Architect** | 技术设计、架构决策 | 8082 | system_design, architecture |
| **Developer** | 代码实现、单元测试 | 8083 | coding, testing, debugging |
| **Reviewer** | 代码审查、质量控制 | 8084 | code_review, security_audit |
| **DevOps** | 部署、CI/CD、监控 | 8085 | deployment, ci_cd, monitoring |

**协作流程：**

```
用户请求
     │
     ▼
ProductOwner ──需求──▶ Architect ──设计──▶ Developer ──代码──▶ Reviewer
                                          │                        │
                                          │                        ▼
                                          │                   审查
                                          │                        │
                                          └────────────────────────┘
                                                DevOps ──部署──▶ 生产环境
```

**完整工作示例：**

```python
import asyncio
from demo.shared import DemoAgent, DemoVisualizer
from demo.software_dev.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    DevOpsAgent,
)
from usmsb_sdk.agent_sdk import AgentConfig, CapabilityDefinition

# ============================================================
# 团队配置
# ============================================================

TEAM_CONFIG = [
    {
        "name": "ProductOwner",
        "role": "产品经理",
        "class": ProductOwnerAgent,
        "capabilities": ["requirement_analysis", "prioritization", "acceptance_testing"],
    },
    {
        "name": "Architect",
        "role": "系统架构师",
        "class": ArchitectAgent,
        "capabilities": ["system_design", "architecture", "technology_selection"],
    },
    {
        "name": "Developer",
        "role": "软件开发工程师",
        "class": DeveloperAgent,
        "capabilities": ["coding", "testing", "debugging"],
    },
    {
        "name": "Reviewer",
        "role": "代码审查员",
        "class": ReviewerAgent,
        "capabilities": ["code_review", "security_audit", "quality_assurance"],
    },
    {
        "name": "DevOps",
        "role": "运维工程师",
        "class": DevOpsAgent,
        "capabilities": ["deployment", "ci_cd", "monitoring"],
    },
]

# ============================================================
# 主执行
# ============================================================

async def main():
    """运行软件开发团队演示"""

    # 创建可视化器来跟踪工作流
    # 设置 enable_html=True 可以看到基于 Web 的可视化
    visualizer = DemoVisualizer(
        scenario_name="software_dev",
        enable_html=False
    )

    # ========================================================
    # 创建所有智能体
    # ========================================================

    agents = {}
    for cfg in TEAM_CONFIG:
        # 将能力名称转换为 CapabilityDefinition 对象
        capabilities = [
            CapabilityDefinition(
                name=c,
                description=c.replace("_", " ").title(),
                category="development",
                level="advanced"
            )
            for c in cfg["capabilities"]
        ]

        # 创建智能体配置
        config = AgentConfig(
            name=cfg["name"],
            description=f"{cfg['role']} AI智能体",
            capabilities=capabilities,
            heartbeat_interval=30,     # 每 30 秒发送心跳
            ttl=90,                    # 消息超时 90 秒
            log_level="INFO"
        )

        # 实例化智能体
        agent = cfg["class"](config, visualizer=visualizer)

        # 初始化（加载模型、注册技能）
        await agent.initialize()

        agents[cfg["name"]] = agent
        print(f"✅ 创建了 {cfg['name']} 智能体")

    # ========================================================
    # 演示智能体生命周期
    # ========================================================

    developer = agents["Developer"]

    # 启动智能体（注册到平台、开始处理）
    await developer.start()
    print(f"✅ {developer.name} 已启动")

    # 获取智能体指标
    metrics = developer.metrics
    print(f"   接收消息数: {metrics.get('messages_received', 0)}")

    # 列出已注册的技能
    print(f"   技能: {list(developer.skills.keys())}")

    # ========================================================
    # 向另一个智能体发送消息
    # ========================================================

    msg = await developer.send_message(
        receiver="Reviewer",
        content={
            "type": "code_submission",
            "task": "用户登录 API",
            "code": "def login(username, password):...",
            "priority": "high"
        },
        message_type="task"
    )

    print(f"✅ 发送消息给 Reviewer: {msg}")

    # ========================================================
    # 清理
    # ========================================================

    await developer.stop()
    print(f"✅ {developer.name} 已停止")

    # 清理所有智能体
    for name, agent in agents.items():
        await agent.shutdown()


# 运行演示
asyncio.run(main())
```

### 9.2 开发者智能体实现

此示例展示如何构建具有技能的完整 Developer 智能体。

```python
from typing import Any, Dict, List, Optional
from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig

class DeveloperAgent(BaseAgent):
    """开发者 AI 智能体

    此智能体负责：
    1. 根据设计实现软件功能
    2. 编写单元测试
    3. 调试和修复问题

    智能体从 Architect 接收设计，
    实现代码，然后传递给 Reviewer。
    """

    def __init__(self, config: AgentConfig, visualizer=None):
        """初始化智能体

        参数:
            config: 智能体配置
            visualizer: 用于工作流跟踪的可选可视化器
        """
        super().__init__(config)
        self.visualizer = visualizer
        self.implementations: List[Dict] = []    # 跟踪所有实现
        self.current_task: Optional[Dict] = None  # 当前正在处理的任务

    async def initialize(self):
        """智能体启动时设置技能和能力

        注册此智能体可以执行的所有技能。
        每个技能都有一个执行实际工作的处理函数。
        """
        self.logger.info("初始化 Developer 智能体")

        # 注册：实现功能技能
        self.register_skill(
            name="implement_feature",
            description="根据规范实现软件功能",
            handler=self._implement_feature,
            parameters={
                "task": "包含需求的任务描述、ID 和标题",
                "design": "包含规范的技术设计文档"
            }
        )

        # 注册：编写测试技能
        self.register_skill(
            name="write_tests",
            description="为代码编写单元测试",
            handler=self._write_tests,
            parameters={
                "code": "要测试的源代码",
                "feature": "功能名称或描述"
            }
        )

        # 注册：调试技能
        self.register_skill(
            name="debug",
            description="查找和修复代码中的缺陷",
            handler=self._debug_code,
            parameters={
                "code": "有缺陷的代码",
                "error": "错误消息或描述"
            }
        )

        # 注册能力（用于发现）
        self.register_capability("coding", "代码实现", 0.9)
        self.register_capability("testing", "单元测试", 0.85)
        self.register_capability("debugging", "调试排错", 0.8)

    async def _implement_feature(self, params: Dict) -> Dict:
        """根据任务和        这是 Developer 智能体的设计实现功能

核心逻辑。
        它将规范转换为可工作的代码。

        参数:
            params: 包含以下内容的字典：
                - task: 任务详情（id、title、description）
                - design: 技术设计

        返回:
            包含代码和元数据的实现结果
        """
        task = params.get("task", {})
        design = params.get("design", {})

        self.logger.info(f"实现功能: {task.get('title', '未知')}")

        # ========================================================
        # 在实际实现中，这会：
        # 1. 解析设计文档
        # 2. 使用 AI 或模板生成代码
        # 3. 运行代码格式化工具/林特
        # 4. 返回生成的代码
        # ========================================================

        implementation = {
            "task_id": task.get("id", "unknown"),
            "title": task.get("title", "未命名"),
            "code": "生成的代码在这里",  # 实际代码会在这里
            "language": design.get("language", "python"),
            "framework": design.get("framework"),
            "status": "implemented",
            "lines_of_code": 150,
            "files_created": ["main.py", "models.py", "utils.py"]
        }

        # 存储实现以便跟踪
        self.implementations.append(implementation)

        return implementation

    async def _write_tests(self, params: Dict) -> Dict:
        """为实现的代码编写单元测试

        参数:
            params: 包含以下内容的字典：
                - code: 要测试的源代码
                - feature: 功能名称

        返回:
            包含覆盖率信息的测试结果
        """
        feature = params.get("feature", "feature")

        # 生成测试用例
        test_cases = [
            {
                "name": f"test_{feature}_success",
                "type": "unit",
                "status": "pass",
                "assertions": ["assert result is not None"]
            },
            {
                "name": f"test_{feature}_error",
                "type": "unit",
                "status": "pass",
                "assertions": ["assert raises ValueError"]
            },
            {
                "name": f"test_{feature}_edge_case",
                "type": "integration",
                "status": "pending",
                "assertions": ["assert handles empty input"]
            }
        ]

        return {
            "feature": feature,
            "test_cases": test_cases,
            "coverage": 0.92,
            "test_framework": "pytest"
        }

    async def _debug_code(self, params: Dict) -> Dict:
        """调试和修复代码问题

        参数:
            params: 包含以下内容的字典：
                - code: 有缺陷的代码
                - error: 错误描述

        返回:
            包含已应用修复的调试结果
        """
        code = params.get("code", "")
        error = params.get("error", "")

        return {
            "original_error": error,
            "fixes_applied": 3,
            "status": "fixed",
            "confidence": 0.85
        }

    async def handle_message(self, message: Any, session=None) -> Any:
        """处理传入消息

        处理不同的消息类型：
        - technical_design: 从 Architect 接收设计
        - code_review_feedback: 处理来自 Reviewer 的反馈
        - task_update: 处理任务修改
        """
        # 提取消息内容
        content = message.content if hasattr(message, 'content') else message

        # 处理来自 Architect 的技术设计
        if isinstance(content, dict) and content.get("type") == "technical_design":
            tasks = content.get("tasks", [])
            design = content.get("design", {})

            self.logger.info(f"收到包含 {len(tasks)} 个任务的设计")

            results = []
            for task in tasks:
                # 实现每个任务
                implementation = await self._implement_feature({
                    "task": task,
                    "design": design
                })
                results.append(implementation)

            return {
                "status": "implementations_completed",
                "count": len(results),
                "implementations": results
            }

        # 处理代码审查反馈
        if isinstance(content, dict) and content.get("type") == "review_feedback":
            feedback = content.get("feedback", [])
            task_id = content.get("task_id")

            # 根据反馈应用修复
            fixes_applied = len(feedback)

            return {
                "status": "feedback_addressed",
                "task_id": task_id,
                "fixes": fixes_applied
            }

        # 默认：使用父类处理器
        return await super().handle_message(message, session)
```

---

## 10. 最佳实践

构建生产级智能体的指南。

### 10.1 错误处理

始终优雅地处理错误以防止崩溃并提供有用的反馈。

```python
class RobustAgent(BaseAgent):
    """具有全面错误处理的示例智能体"""

    async def handle_message(self, message, session=None):
        """正确处理错误来处理消息"""
        try:
            # 正常处理
            return await self._process_message(message)

        except ValueError as e:
            # 处理验证错误
            self.logger.warning(f"验证错误: {e}")
            return Message(
                type=MessageType.ERROR,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={
                    "error": "无效输入",
                    "details": str(e),  # 包含详情以便调试
                    "suggestion": "检查输入格式后重试"
                }
            )

        except TimeoutError as e:
            # 处理超时错误
            self.logger.error(f"操作超时: {e}")
            return Message(
                type=MessageType.ERROR,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={
                    "error": "操作超时",
                    "suggestion": "尝试使用较小的数据集"
                }
            )

        except Exception as e:
            # 捕获意外错误的 catch-all
            # 切勿让异常未处理地传播
            self.logger.exception(f"意外错误: {e}")  # 完整堆栈跟踪
            return Message(
                type=MessageType.ERROR,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={
                    "error": "内部错误",
                    "error_id": "ABC123"  # 用于支持的参考 ID
                }
            )
```

### 10.2 资源管理

正确管理资源以防止泄漏并确保干净关闭。

```python
class ResourceAgent(BaseAgent):
    """正确资源管理的示例"""

    async def initialize(self):
        """初始化资源"""
        # 加载 AI 模型
        self.model = await self.load_model()

        # 连接数据库
        self.db = await self.connect_db()

        # 创建缓存
        self.cache = await self.create_cache()

        # 初始化计数器
        self.request_count = 0

    async def shutdown(self):
        """清理所有资源

        这很关键！未能清理会导致：
        - 内存泄漏
        - 连接池耗尽
        - 文件句柄泄漏
        """
        self.logger.info(f"处理 {self.request_count} 个请求后关闭")

        # 始终使用 try/finally 以确保清理
        try:
            # 如需要则保存状态
            await self._save_state()
        finally:
            # 按初始化的相反顺序关闭

            # 关闭缓存
            if hasattr(self, 'cache') and self.cache:
                await self.cache.close()

            # 关闭数据库
            if hasattr(self, 'db') and self.db:
                await self.db.close()

            # 卸载模型（对 GPU 内存很重要！）
            if hasattr(self, 'model') and self.model:
                await self.model.unload()

        await super().shutdown()
```

### 10.3 日志配置

设置正确的日志以便调试和监控。

```python
import logging

# 在创建智能体之前配置根日志
logging.basicConfig(
    level=logging.DEBUG,                      # 开发时使用 DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),     # 记录到文件
        logging.StreamHandler()               # 记录到控制台
    ]
)

# 或配置智能体特定的日志
config = AgentConfig(
    name="my_agent",
    log_level="DEBUG",                       # DEBUG、INFO、WARNING、ERROR

    # 生产环境使用 INFO 以减少噪音
    # log_level="INFO"
)

# 在智能体中使用日志
class MyAgent(BaseAgent):
    async def handle_message(self, message, session=None):
        self.logger.debug(f"收到: {message.content}")
        self.logger.info(f"处理来自 {message.sender_id} 的请求")

        try:
            result = await self.process(message)
            self.logger.info(f"成功: {result}")
            return result
        except Exception as e:
            self.logger.error(f"失败: {e}")
            raise
```

### 10.4 生产环境配置

生产部署的推荐设置。

```python
import os

config = AgentConfig(
    name="production_agent",
    description="生产环境智能体",

    # ========================================================
    # 安全设置
    # ========================================================
    security=SecurityConfig(
        auth_enabled=True,
        api_key=os.environ["AGENT_API_KEY"],      # 来自环境变量
        encryption_enabled=True,                   # 加密消息
        rate_limit=1000,                           # 每分钟最大请求数
        allowed_origins=["https://yourdomain.com"]  # CORS 保护
    ),

    # ========================================================
    # 可靠性设置
    # ========================================================
    auto_register=True,               # 确保启动时注册
    auto_discover=True,              # 寻找协作者

    # ========================================================
    # 性能设置
    # ========================================================
    log_level="INFO",                # 生产环境减少详细程度
    health_check_interval=60,        # 每 60 秒检查健康
    heartbeat_interval=30,            # 每 30 秒发送心跳
    ttl=90,                          # 90 秒消息超时

    # ========================================================
    # 监控
    # ========================================================
    enable_metrics=True,
    metrics_endpoint="/metrics"
)
```

---

## 11. 问题排查

常见问题的解决方案。

### 11.1 常见问题及解决方案

| 问题 | 原因 | 解决方案 |
|-------|-------|----------|
| `ImportError: No module named 'usmsb_sdk'` | 未安装包 | `pip install usmsb-sdk` |
| `ConnectionError: Connection failed` | 平台 URL 错误 | 验证 `platform_url` 是否正确 |
| `AuthError: Invalid API key` | 认证失败 | 检查 `api_key` 是否正确 |
| `RuntimeError: Port already in use` | 端口冲突 | 使用不同的端口号 |
| `TimeoutError: No response` | 智能体无响应 | 增加 `timeout` 参数 |
| `RegistrationError: Missing fields` | 配置不完整 | 检查必需的 AgentConfig 字段 |

### 11.2 调试模式

启用详细日志以诊断问题。

```python
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 创建智能体
agent = MyAgent(config)

# 将智能体日志设置为调试
agent.logger.setLevel(logging.DEBUG)

# 添加文件处理器以获取持久日志
file_handler = logging.FileHandler('debug.log')
file_handler.setLevel(logging.DEBUG)
agent.logger.addHandler(file_handler)
```

### 11.3 健康检查

验证你的智能体和平台是否正常工作。

```python
# 检查平台连接
platform = PlatformClient(platform_url="http://localhost:8000")
is_healthy = await platform.health_check()

if not is_healthy:
    print("❌ 平台不健康")
    # 检查平台日志以获取错误
else:
    print("✅ 平台健康")

# 检查智能体状态
print(f"智能体状态: {agent.state}")        # 应该是 "running"
print(f"已注册: {agent.is_registered}") # 应该是 True
print(f"运行时间: {agent.metrics.get('uptime', 0)}s")

# 获取详细健康信息
health = await agent.get_health()
print(f"健康状况: {health}")
```

---

## 相关文档

- [USMSB SDK 使用指南](./usmsb-sdk.md) - 平台概述和入门
- [Meta Agent 使用详解](./meta-agent-usage.md) - 高级元智能体功能
- [集成指南](./integration-guide.md) - 深度集成模式
](./whitepaper.md- [白皮书) - 理论基础和架构
