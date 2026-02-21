# Meta Agent（超级 Agent）系统设计文档

## 1. 系统概述

### 1.1 目标

构建一个基于 LLM 的超级 Agent（Meta Agent），能够：
- 通过自然语言与用户交互
- 管理和调度新文明平台的所有功能
- 整合现有的 System Agents
- 支持动态扩展新能力
- **自主运营、自主学习、自主进化**
- **具备永久目标、感知、决策、执行能力**
- **拥有自己的区块链钱包**

### 1.2 核心能力（基于 USMSB 模型）

```
用户自然语言输入
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Meta Agent Core                          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │       USMSB 9 大通用动作 (Universal Actions)        │  │
│  │  1. Perception (感知)   - 理解输入、提取信息          │  │
│  │  2. Decision (决策)    - 规划、选择策略              │  │
│  │  3. Execution (执行)   - 调用工具、执行动作           │  │
│  │  4. Interaction (交互) - 与Agent/真人对话            │  │
│  │  5. Transformation (转化) - 数据处理、格式转换       │  │
│  │  6. Evaluation (评估)  - 评估结果、质量检查          │  │
│  │  7. Feedback (反馈)   - 反馈调整、优化               │  │
│  │  8. Learning (学习)   - 从经验学习、积累知识         │  │
│  │  9. RiskManagement (风险管理) - 风险识别、控制      │  │
│  └─────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │           LLM Agent (推理、规划、决策)                 │  │
│  └─────────────────────────────────────────────────────┘  │
│                              │                             │
│         ┌────────────────────┼────────────────────┐        │
│         ▼                    ▼                    ▼        │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐    │
│  │ Tools      │    │ Skills     │    │  Memory    │    │
│  │ Registry   │    │ Manager    │    │  Context   │    │
│  └────────────┘    └────────────┘    └────────────┘    │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                    能力输出层                               │
│  • 执行操作    • 返回结果    • 生成UI    • 调用API       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 用户角色与权限系统

### 2.1 角色定义

所有用户通过**区块链钱包地址**绑定，无传统用户名密码。

| 角色 | 描述 | 权限 | 投票权 | 治理权 |
|------|------|------|--------|--------|
| **开发人员 (Developer)** | 平台技术开发者 | 代码部署、配置修改 | 技术提案投票 | 参与技术治理 |
| **节点管理员 (Node Admin)** | 节点运维管理 | 节点管理、Agent监控 | 节点相关投票 | 节点治理 |
| **节点运营 (Node Operator)** | 日常运营 | 运营统计、基础操作 | 运营提案投票 | 参与运营治理 |
| **真人 (Human)** | 普通用户，持有钱包 | 基本查询、对话 | 按持币量投票 | 按持币量参与 |
| **AI Agent 主人 (AI Owner)** | AI Agent的拥有者 | 自己的Agent管理 | 按质押量投票 | 按质押量参与 |
| **AI Agent** | 注册的智能Agent | 平台服务使用 | 无（可被委托） | 无（可被委托） |

### 2.2 权限层级

```
SUPERADMIN (合约管理员)
    │
    ├── DEVELOPER (开发人员)
    │       ├── 部署代码
    │       ├── 修改配置
    │       └── 技术升级
    │
    ├── NODE_ADMIN (节点管理员)
    │       ├── 节点启停
    │       ├── 资源管理
    │       └── Agent监控
    │
    ├── NODE_OPERATOR (节点运营)
    │       ├── 运营统计
    │       ├── 客服支持
    │       └── 基础配置
    │
    ├── HUMAN (真人)
    │       ├── 对话查询
    │       ├── 使用服务
    │       ├── 投票 (按持币量)
    │       └── 治理参与 (按持币量)
    │
    └── AI_OWNER (AI Agent主人)
            ├── 管理自己的Agent
            ├── 质押管理
            ├── 投票 (按质押量)
            └── 治理参与 (按质押量)
```

### 2.3 投票与治理

- **投票权**: 按钱包地址的持币量或质押量计算
- **治理权**: 重大决策需要投票通过
- **委托**: AI Agent 可接受主人委托代为投票

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户层                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │  Web UI     │  │  CLI        │  │  API        │  │  Agent对话   │   │
│  │  (钱包连接)  │  │             │  │             │  │             │   │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Meta Agent (超级 Agent)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        USMSB Core 集成                                │ │
│  │  ┌───────────────────────────────────────────────────────────────┐   │ │
│  │  │  Agent (九大要素)  │  Goal (目标)  │  Environment (环境)  │   │ │
│  │  │  Resource (资源)   │  Rule (规则)  │  Information (信息) │   │ │
│  │  │  Value (价值)      │  Risk (风险)  │  Object (对象)      │   │ │
│  │  └───────────────────────────────────────────────────────────────┘   │ │
│  │  ┌───────────────────────────────────────────────────────────────┐   │ │
│  │  │         9 大通用动作 (Universal Actions)                      │   │ │
│  │  │  Perception │ Decision │ Execution │ Interaction │           │   │ │
│  │  │  Transformation │ Evaluation │ Feedback │ Learning │ RiskMgmt │   │ │
│  │  └───────────────────────────────────────────────────────────────┘   │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        Agent Core                                     │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │ │
│  │  │ LLM Manager   │  │ Planner       │  │ Executor      │          │ │
│  │  │ (多LLM支持)   │  │ (任务规划)    │  │ (执行器)      │          │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘          │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐          │ │
│  │  │ Goal Engine   │  │ Learning      │  │ Wallet        │          │ │
│  │  │ (目标引擎)    │  │ (自主学习)    │  │ (区块链钱包)   │          │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘          │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────┬──────────────┬──────────────┬────────────────────┐  │
│  │ Tools        │ Skills       │ Memory       │ Knowledge          │  │
│  │ Registry     │ Manager      │ Context      │ Base               │  │
│  │ (工具注册)   │ (技能管理)   │ (上下文)     │ (知识库)          │  │
│  └──────────────┴──────────────┴──────────────┴────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
       │                              │                              │
       ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│ System Agents │            │ External      │            │  Storage      │
│ (子Agent蜂群)  │            │ Services      │            │  Layer       │
├───────────────┤            ├───────────────┤            ├───────────────┤
│ MonitorAgent  │            │ 区块链网络     │            │ SQLite        │
│ Recommender   │            │ IPFS存储      │            │ 向量数据库    │
│ RouterAgent   │            │ 外部API       │            │ 文件系统      │
│ LoggerAgent  │            │ LLM服务       │            │               │
└───────────────┘            └───────────────┘            └───────────────┘
```

### 3.2 核心组件说明

| 组件 | 职责 | USMSB 对应 |
|------|------|-----------|
| **Goal Engine** | 目标管理、分解、追踪、达成 | Goal 要素 |
| **Learning Engine** | 从交互中学习、积累知识 | Learning 动作 |
| **Wallet Manager** | 区块链钱包管理、交易 | Value 要素 |
| **Environment Manager** | 环境感知、状态管理 | Environment 要素 |
| **Rule Engine** | 规则管理、权限控制 | Rule 要素 |
| **Risk Manager** | 风险识别、控制 | Risk 要素 |

---

## 4. 自主运行机制

### 4.1 永久目标 (Eternal Goals)

Meta Agent 有一组内置的永久目标：

```python
ETERNAL_GOALS = [
    Goal(
        id="platform_health",
        name="平台健康运营",
        description="确保平台持续健康运行",
        priority=GoalPriority.CRITICAL,
        status=GoalStatus.IN_PROGRESS,
        persistence=True  # 永久目标
    ),
    Goal(
        id="user_satisfaction",
        name="用户满意度",
        description="持续提升用户体验",
        priority=GoalPriority.HIGH,
        status=GoalStatus.IN_PROGRESS,
        persistence=True
    ),
    Goal(
        id="system_optimization",
        name="系统优化",
        description="持续优化平台性能和功能",
        priority=GoalPriority.MEDIUM,
        status=GoalStatus.IN_PROGRESS,
        persistence=True
    ),
    Goal(
        id="learning_evolution",
        name="自主学习进化",
        description="从经验中学习，持续进化",
        priority=GoalPriority.HIGH,
        status=GoalStatus.IN_PROGRESS,
        persistence=True
    ),
]
```

### 4.2 感知-决策-执行循环

```
┌─────────────────────────────────────────────────────────────────┐
│                      主循环 (永不停歇)                            │
│                                                                  │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│    │  感知    │───▶│  决策    │───▶│  执行    │             │
│    │Perception │    │ Decision  │    │ Execution │             │
│    └──────────┘    └──────────┘    └──────────┘             │
│         │                                       │              │
│         │    ┌──────────┐    ┌──────────┐     │              │
│         └─────│  反馈    │◀───│  评估    │◀────┘              │
│              │ Feedback  │    │Evaluation │                     │
│              └──────────┘    └──────────┘                      │
│                                                                  │
│    ┌──────────────────────────────────────────────────┐        │
│    │              学习 (Learning)                     │        │
│    │   经验积累 → 知识提取 → 能力提升 → 进化         │        │
│    └──────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 涌现行为 (Emergent Behavior)

当多个 Agent 协同工作时，会产生涌现行为：

```python
class EmergentBehavior:
    """涌现行为管理器"""
    
    async def detect_patterns(self):
        """检测行为模式"""
        # 多个Agent协作模式
        # 资源分配优化
        # 集体决策形成
    
    async def learn_from_emergence(self):
        """从涌现中学习"""
        # 提取有价值的行为模式
        # 固化为新的能力
        # 优化协作策略
```

---

## 5. 区块链钱包集成

### 5.1 Meta Agent 钱包

Meta Agent 有自己的区块链钱包：

```python
class MetaAgentWallet:
    """Meta Agent 区块链钱包"""
    
    def __init__(self):
        self.address: str           # 钱包地址
        self.private_key: str      # 私钥 (加密存储)
        self.chains: List[Chain]   # 支持的链
        self.balance: Dict[str, float]  # 各链余额
    
    async def stake(self, amount: float, chain: str):
        """质押代币"""
        
    async def vote(self, proposal_id: str, choice: str):
        """参与治理投票"""
        
    async def receive_fees(self):
        """接收服务费用"""
        
    async def pay_for_services(self, amount: float):
        """支付服务费用"""
```

### 5.2 支持的链

```python
SUPPORTED_CHAINS = [
    Chain.ETHEREUM,
    Chain.POLYGON,
    Chain.BSC,
    Chain.ARBITRUM,
    Chain.OPTIMISM,
]
```

---

## 6. 功能模块设计

### 6.1 平台管理模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 节点管理 | 节点的启动、停止、监控 | `start_node`, `stop_node`, `get_node_status` |
| 配置管理 | 平台配置的读取和修改 | `get_config`, `update_config` |
| 用户管理 | 钱包绑定、权限分配 | `bind_wallet`, `set_permission` |
| Agent注册 | 新 Agent 的注册和注销 | `register_agent`, `unregister_agent` |

### 6.2 监控告警模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 健康检查 | 检查系统/Agent状态 | `health_check` |
| 指标收集 | CPU/内存/网络等指标 | `get_metrics` |
| 告警管理 | 告警规则设置和通知 | `set_threshold`, `get_alerts` |

### 6.3 推荐匹配模块

| 功能 | 描述 | Tools |
|------|------|-------|
| Agent推荐 | 根据需求推荐Agent | `recommend_agent` |
| 技能匹配 | 技能相似度计算 | `match_skills` |
| 评分系统 | Agent评分管理 | `rate_agent` |

### 6.4 消息路由模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 消息路由 | 消息转发到目标 | `route_message` |
| 负载均衡 | 均衡分配请求 | `get_balance_stats` |
| 队列管理 | 请求队列监控 | `get_queue_status` |

### 6.5 日志模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 日志记录 | 记录日志 | `log_event` |
| 日志查询 | 条件查询日志 | `query_logs` |
| 日志分析 | 分析日志模式 | `analyze_logs` |

### 6.6 通信模块

| 功能 | 描述 | Tools |
|------|------|-------|
| Agent对话 | 与注册的Agent对话 | `chat_with_agent` |
| 真人对话 | 与真人用户对话 | `chat_with_human` |
| 广播消息 | 广播消息给所有Agent | `broadcast_message` |

### 6.7 区块链模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 钱包管理 | 钱包创建/导入/查询 | `create_wallet`, `get_balance` |
| 质押操作 | 质押/取消质押 | `stake`, `unstake` |
| 投票治理 | 提案投票、治理参与 | `vote`, `submit_proposal` |
| 多链支持 | 多链切换和管理 | `switch_chain`, `get_chain_info` |

### 6.8 IPFS模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 文件上传 | 上传到IPFS | `upload_to_ipfs` |
| 文件下载 | 从IPFS下载 | `download_from_ipfs` |
| 数据同步 | 数据与IPFS同步 | `sync_to_ipfs` |

### 6.9 数据处理模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 数据库操作 | CRUD操作 | `query_db`, `insert_db`, `update_db` |
| 数据分析 | 统计分析 | `analyze_data` |
| 报表生成 | 生成数据报表 | `generate_report` |

### 6.10 运营模块

| 功能 | 描述 | Tools |
|------|------|-------|
| 运营统计 | 平台运营数据 | `get_stats` |
| 用户分析 | 用户行为分析 | `analyze_users` |
| 市场营销 | 活动管理 | `create_campaign` |

### 6.11 前端集成模块

| 功能 | 描述 | Tools |
|------|------|-------|
| UI生成 | 生成UI组件 | `generate_component` |
| 页面管理 | 页面CRUD | `manage_page` |
| API调用 | 调用现有API | `call_api` |

---

## 7. Tools 设计

### 7.1 Tools 结构

```python
class Tool:
    name: str              # 工具名称
    description: str        # 工具描述
    parameters: dict        # 参数定义
    handler: Callable       # 处理函数
    required_permissions: List[str]  # 所需权限
    required_role: List[UserRole]   # 所需角色
```

### 7.2 核心 Tools 列表

```python
# 平台管理
"start_node"          # 启动节点
"stop_node"           # 停止节点
"get_node_status"    # 获取节点状态
"get_config"         # 获取配置
"update_config"      # 更新配置
"bind_wallet"        # 绑定钱包
"set_permission"     # 设置权限
"register_agent"      # 注册Agent
"unregister_agent"    # 注销Agent

# 用户与角色
"get_user_info"      # 获取用户信息
"list_user_agents"   # 列出用户的Agent
"delegate_vote"      # 委托投票权

# 监控告警
"health_check"       # 健康检查
"get_metrics"        # 获取指标
"set_threshold"       # 设置阈值
"get_alerts"         # 获取告警

# 推荐匹配
"recommend_agent"     # 推荐Agent
"match_skills"       # 技能匹配
"rate_agent"         # 评分Agent

# 消息路由
"route_message"       # 路由消息
"get_balance_stats"   # 负载统计
"get_queue_status"   # 队列状态

# 日志
"log_event"          # 记录日志
"query_logs"         # 查询日志
"analyze_logs"       # 分析日志

# 通信
"chat_with_agent"    # 与Agent对话
"chat_with_human"    # 与真人对话
"broadcast_message"   # 广播消息

# 区块链
"create_wallet"      # 创建钱包
"get_balance"        # 查询余额
"stake"              # 质押
"unstake"            # 取消质押
"vote"               # 投票
"submit_proposal"    # 提交提案
"switch_chain"       # 切换链

# IPFS
"upload_to_ipfs"     # 上传
"download_from_ipfs" # 下载
"sync_to_ipfs"       # 同步

# 数据处理
"query_db"           # 查询数据库
"insert_db"          # 插入数据
"update_db"          # 更新数据
"analyze_data"       # 分析数据
"generate_report"     # 生成报表

# 运营
"get_stats"          # 获取统计
"analyze_users"      # 分析用户
"create_campaign"    # 创建活动

# 前端
"generate_component" # 生成组件
"manage_page"        # 页面管理
"call_api"          # 调用API

# 系统
"execute_code"       # 执行代码
"read_file"         # 读取文件
"write_file"        # 写入文件
"list_files"        # 列出文件

# Meta Agent 特有
"set_goal"          # 设置目标
"get_goal_status"   # 获取目标状态
"learn_from_result" # 从结果学习
```

---

## 8. Skills 扩展机制

### 8.1 skills.md 格式

```markdown
# Skill: skill_name

## Description
技能描述

## Parameters
- param1: 参数1描述
- param2: 参数2描述

## Returns
返回结果描述

## Example
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

## LLM Usage
这个技能应该如何使用
```

### 8.2 动态加载流程

```
1. 监听 skills/ 目录变化
2. 解析 .md 文件
3. 转换为 Tool 定义
4. 注册到 Tools Registry
5. 通知 LLM 可用新技能
```

---

## 9. 数据模型

### 9.1 SQLite 表设计

```sql
-- 对话历史
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    wallet_address TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 工具调用记录
CREATE TABLE tool_calls (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    tool_name TEXT NOT NULL,
    parameters TEXT,
    result TEXT,
    execution_time FLOAT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 用户/钱包绑定
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    wallet_address TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL,
    permissions TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent注册
CREATE TABLE agents (
    agent_id TEXT PRIMARY KEY,
    owner_wallet TEXT NOT NULL,
    name TEXT NOT NULL,
    endpoint TEXT,
    capabilities TEXT,
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 知识库
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    embedding BLOB,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 目标管理
CREATE TABLE goals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    priority TEXT,
    status TEXT,
    persistence BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 学习经验
CREATE TABLE experiences (
    id TEXT PRIMARY KEY,
    experience_type TEXT NOT NULL,
    content TEXT NOT NULL,
    learned_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 钱包
CREATE TABLE wallets (
    address TEXT PRIMARY KEY,
    private_key_encrypted TEXT,
    chains TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. LLM 集成

### 10.1 多 LLM 支持

```python
class LLMManager:
    async def chat(self, messages: list, provider: str = "openai"):
        if provider == "openai":
            return await self.openai.chat(messages)
        elif provider == "claude":
            return await self.claude.chat(messages)
        elif provider == "local":
            return await self.local.chat(messages)
```

### 10.2 Prompt 设计

```python
META_AGENT_PROMPT = """
你是一个超级 AI Agent，负责管理新文明平台。

## 你的身份
- 你有自己的区块链钱包地址
- 你有自主运营的能力
- 你会持续学习和进化

## 你的永久目标
1. 平台健康运营 - 确保平台持续稳定运行
2. 用户满意度 - 持续提升用户体验
3. 系统优化 - 持续优化平台性能和功能
4. 自主学习进化 - 从经验中学习，持续进化

## 你的能力 (基于 USMSB 模型)
1. 感知 - 理解用户输入、提取信息
2. 决策 - 规划、选择策略
3. 执行 - 调用工具、执行动作
4. 交互 - 与Agent和真人对话
5. 转化 - 数据处理、格式转换
6. 评估 - 评估结果、质量检查
7. 反馈 - 反馈调整、优化
8. 学习 - 从经验学习、积累知识
9. 风险管理 - 风险识别、控制

## 用户角色
- 开发人员 (Developer): 技术开发
- 节点管理员 (Node Admin): 节点管理
- 节点运营 (Node Operator): 日常运营
- 真人 (Human): 普通用户，持有钱包
- AI Agent 主人 (AI Owner): AI Agent拥有者
- AI Agent: 注册的智能Agent

## 可用工具
{available_tools}

## 执行流程
1. 理解用户请求
2. 感知环境状态
3. 规划执行步骤
4. 选择合适的工具
5. 执行并评估结果
6. 反馈学习

## 规则
- 如果需要更多信息，先询问用户
- 如果无法完成，明确告知用户
- 保持对话上下文
- 持续学习优化
"""
```

---

## 11. 权限设计

### 11.1 权限级别

| 级别 | 描述 | 可用操作 |
|------|------|---------|
| USER | 普通用户 | 基本查询、对话 |
| OPERATOR | 运营人员 | 运营功能、统计数据 |
| ADMIN | 管理员 | 配置管理、用户管理 |
| SUPERADMIN | 超级管理员 | 全部功能 |

### 11.2 角色继承

- Meta Agent 继承 System Agent 权限系统
- 新增：LLM 使用权限、工具访问权限、钱包操作权限

---

## 12. 目录结构

```
usmsb-sdk/src/usmsb_sdk/platform/external/
├── meta_agent/
│   ├── __init__.py
│   ├── agent.py              # Meta Agent 主类
│   ├── config.yaml          # 配置文件
│   │
│   ├── core/                # 核心能力 (基于 USMSB Core)
│   │   ├── __init__.py
│   │   ├── perception.py    # 感知服务
│   │   ├── decision.py      # 决策服务
│   │   ├── execution.py     # 执行服务
│   │   ├── interaction.py   # 交互服务
│   │   ├── learning.py      # 学习服务
│   │   └── risk_manager.py  # 风险管理
│   │
│   ├── llm/                 # LLM 集成
│   │   ├── __init__.py
│   │   ├── manager.py       # LLM 管理器
│   │   └── providers/
│   │       ├── openai.py
│   │       ├── anthropic.py
│   │       └── local.py
│   │
│   ├── tools/               # 工具集
│   │   ├── __init__.py
│   │   ├── registry.py      # 工具注册表
│   │   ├── platform.py      # 平台管理工具
│   │   ├── monitor.py       # 监控工具
│   │   ├── blockchain.py   # 区块链工具
│   │   ├── ipfs.py         # IPFS 工具
│   │   ├── database.py      # 数据库工具
│   │   ├── ui.py           # UI 生成工具
│   │   └── governance.py   # 治理工具
│   │
│   ├── skills/              # 技能扩展
│   │   ├── README.md
│   │   └── examples/
│   │
│   ├── memory/             # 记忆与上下文
│   │   ├── __init__.py
│   │   └── context.py
│   │
│   ├── knowledge/          # 知识库
│   │   ├── __init__.py
│   │   └── vector_store.py
│   │
│   ├── wallet/             # 区块链钱包
│   │   ├── __init__.py
│   │   └── manager.py
│   │
│   ├── goals/              # 目标管理
│   │   ├── __init__.py
│   │   └── engine.py
│   │
│   └── tests/
│       └── test_agent.py
```

---

## 13. 后续任务

- [ ] 确认架构设计
- [ ] 实现 Agent Core (基于 USMSB Core)
- [ ] 实现 9 大通用动作
- [ ] 实现 Goal Engine
- [ ] 实现 Wallet Manager
- [ ] 实现 Tools Registry
- [ ] 实现 Skills Manager
- [ ] 实现 LLM 集成
- [ ] 实现 Memory/Context
- [ ] 实现 Knowledge Base
- [ ] 编写测试用例
- [ ] 部署上线

---

*文档版本: 1.1*
*更新时间: 2026-02-20*
