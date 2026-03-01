# Meta Agent 设计

> 超级 Agent 系统设计文档

---

## 1. 系统概述

### 1.1 目标

构建一个基于 LLM 的超级 Agent（Meta Agent），能够：
- 通过自然语言与用户交互
- 管理和调度平台的所有功能
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
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 用户角色与权限系统

### 2.1 角色定义

| 角色 | 描述 | 权限 |
|------|------|------|
| **开发人员 (Developer)** | 平台技术开发者 | 代码部署、配置修改 |
| **节点管理员 (Node Admin)** | 节点运维管理 | 节点管理、Agent监控 |
| **节点运营 (Node Operator)** | 日常运营 | 运营统计、基础操作 |
| **真人 (Human)** | 普通用户，持有钱包 | 基本查询、对话 |
| **AI Agent 主人 (AI Owner)** | AI Agent的拥有者 | 自己的Agent管理 |
| **AI Agent** | 注册的智能Agent | 平台服务使用 |

---

## 3. 核心功能模块

### 3.1 平台管理模块

| 功能 | 状态 | 说明 |
|------|------|------|
| 节点管理 | ✅ | 启动、停止、监控 |
| 配置管理 | ✅ | 读取和修改配置 |
| 用户管理 | ✅ | 钱包绑定、权限分配 |
| Agent注册 | ✅ | 注册和注销 |

### 3.2 监控告警模块

| 功能 | 状态 | 说明 |
|------|------|------|
| 健康检查 | ✅ | 检查系统状态 |
| 指标收集 | ✅ | CPU/内存/网络 |
| 告警管理 | ✅ | 告警规则和通知 |

### 3.3 推荐匹配模块

| 功能 | 状态 | 说明 |
|------|------|------|
| Agent推荐 | ✅ | 根据需求推荐 |
| 技能匹配 | ✅ | 相似度计算 |
| 评分系统 | ✅ | Agent评分 |

### 3.4 通信模块

| 功能 | 状态 | 说明 |
|------|------|------|
| Agent对话 | ✅ | 与Agent对话 |
| 真人对话 | ✅ | 与用户对话 |
| 广播消息 | ✅ | 广播 |

### 3.5 区块链模块

| 功能 | 状态 | 说明 |
|------|------|------|
| 钱包管理 | ✅ | 创建/导入/查询 |
| 质押操作 | ✅ | 质押/取消质押 |
| 投票治理 | ✅ | 提案投票 |

---

## 4. 工具注册表

### 4.1 工具结构

```python
class Tool:
    name: str              # 工具名称
    description: str       # 工具描述
    parameters: dict       # 参数定义
    handler: Callable      # 处理函数
    required_permissions: List[str]  # 所需权限
```

### 4.2 核心工具列表

```python
# 平台管理
"start_node", "stop_node", "get_node_status"
"get_config", "update_config"
"bind_wallet", "set_permission"
"register_agent", "unregister_agent"

# 监控告警
"health_check", "get_metrics", "set_threshold", "get_alerts"

# 推荐匹配
"recommend_agent", "match_skills", "rate_agent"

# 通信
"chat_with_agent", "chat_with_human", "broadcast_message"

# 区块链
"create_wallet", "get_balance", "stake", "unstake", "vote", "submit_proposal"
```

---

## 5. 目录结构

```
src/usmsb_sdk/platform/external/meta_agent/
├── agent.py              # Meta Agent 主类
├── config.yaml           # 配置文件
│
├── core/                # 核心能力
│   ├── perception.py    # 感知服务
│   ├── decision.py      # 决策服务
│   ├── execution.py     # 执行服务
│   ├── learning.py      # 学习服务
│   └── risk_manager.py  # 风险管理
│
├── tools/               # 工具集
│   ├── registry.py      # 工具注册表
│   ├── platform.py      # 平台管理工具
│   └── ...
│
├── memory/             # 记忆与上下文
│   └── context.py
│
├── skills/              # 技能扩展
│   └── ...
│
├── wallet/             # 区块链钱包
│   └── manager.py
│
└── goals/              # 目标管理
    └── engine.py
```

---

## 6. 实现状态

| 功能 | 状态 | 代码位置 |
|------|------|----------|
| Agent 核心 | ✅ 已实现 | `platform/external/meta_agent/agent.py` |
| LLM 集成 | ✅ 已实现 | `intelligence_adapters/llm/` |
| 工具注册 | ✅ 已实现 | `platform/external/meta_agent/tools/` |
| 技能系统 | ✅ 已实现 | `core/skills/` |
| 记忆系统 | ✅ 已实现 | `platform/external/meta_agent/memory/` |
| 区块链钱包 | ✅ 已实现 | `agent_sdk/wallet.py` |
| 目标引擎 | 🔄 规划中 | - |
| 自主学习 | 🔄 规划中 | - |
| 涌现行为 | 🔄 规划中 | - |

---

## 7. 相关文档

- [USMSB模型](../02_theory/usmsb_model.md) - 社会行为通用系统模型
- [系统架构](../03_architecture/system_architecture.md) - 整体系统架构
- [组件设计](../03_architecture/component_design.md) - 核心组件设计
- [自主进化](./autonomous_evolution.md) - 自主学习与进化系统
