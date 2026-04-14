# Phase 0: 协议整合层详细设计

**Phase**: Phase 0
**优先级**: P0
**创建时间**: 2026-04-14

---

## 一、模块概述

### 1.1 核心目标

协议整合层是 USMSB 的"连接器"，负责：

```
┌─────────────────────────────────────────────────────────────┐
│                    USMSB Agent                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Protocol Integration Layer              │   │
│  ├───────────┬───────────┬───────────┬─────────────────┤   │
│  │ MCP       │ A2A      │ x402      │ HTTP/REST       │   │
│  │ Gateway   │ Adapter   │ Router    │                 │   │
│  └───────────┴───────────┴───────────┴─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
              ↓                ↓              ↓
        ┌─────────┐       ┌─────────┐   ┌─────────┐
        │ LLM     │       │ Agent   │   │ Payment │
        │ Tools   │       │ Network │   │ Network │
        └─────────┘       └─────────┘   └─────────┘
```

### 1.2 三大协议

| 协议 | 全称 | 用途 | 地位 |
|------|------|------|------|
| **MCP** | Model Context Protocol | Agent ↔ 工具/LLM | 能力增强 |
| **A2A** | Agent-to-Agent Protocol | Agent ↔ Agent 通信 | 协作基础 |
| **x402** | eXactly 402 | Agent ↔ Agent 支付 | 价值流转 |

### 1.3 设计目标

| 目标 | 描述 | 验收标准 |
|------|------|---------|
| MCP Gateway | 标准化工件工具调用 | 支持 Anthropic/OpenAI/Local LLM |
| A2A Adapter | Agent 间通信 | 支持发现、协商、任务协作 |
| x402 Router | 机器微支付 | 支持 HTTP 402 协议 |

---

## 二、MCP Gateway

### 2.1 功能

```
MCP Gateway = LLM ↔ 工具的标准接口

功能：
1. 工具注册：第三方工具注册到 USMSB
2. 工具发现：Agent 发现所需工具
3. 工具调用：标准化调用外部工具
4. 结果处理：标准化返回结果格式
```

### 2.2 接口设计

```python
class MCPTool:
    """MCP 工具"""
    id: str
    name: str
    description: str
    input_schema: dict  # JSON Schema
    output_schema: dict
    category: str
    provider: str


class MCPGateway:
    """MCP 网关"""
    
    def register_tool(self, tool: MCPTool) -> bool:
        """注册工具"""
        pass
    
    def discover_tools(self, query: str) -> list[MCPTool]:
        """发现工具"""
        pass
    
    def call_tool(self, tool_id: str, params: dict) -> Any:
        """调用工具"""
        pass
    
    def get_tool_schema(self, tool_id: str) -> dict:
        """获取工具 schema"""
        pass
```

---

## 三、A2A Adapter

### 3.1 功能

```
A2A Adapter = Agent ↔ Agent 通信协议

功能：
1. Agent Card：发布自身能力描述
2. 发现服务：发现其他 Agent
3. 任务协作：跨 Agent 任务分解与执行
4. 消息交换：点对点消息
```

### 3.2 Agent Card

```python
@dataclass
class AgentCard:
    """Agent 能力描述卡"""
    id: str                           # Agent ID
    name: str                         # Agent 名称
    description: str                 # 描述
    version: str                      # 版本
    capabilities: list[str]           # 能力列表
    skills: list[dict]              # 技能详情
    endpoints: dict                  # 端点
    authentication: str              # 认证方式
    metadata: dict                   # 元数据
```

### 3.3 A2A Message

```python
@dataclass
class A2AMessage:
    """A2A 消息"""
    id: str
    type: A2AMessageType  # task, query, response, error
    from_agent: str
    to_agent: str | None  # None = broadcast
    payload: dict
    timestamp: float
    reply_to: str | None


class A2MAdapter:
    """A2A 适配器"""
    
    def publish_card(self, card: AgentCard) -> bool:
        """发布 Agent Card"""
        pass
    
    def discover_agents(self, query: dict) -> list[AgentCard]:
        """发现 Agent"""
        pass
    
    def send_message(self, message: A2AMessage) -> bool:
        """发送消息"""
        pass
    
    def receive_message(self) -> A2AMessage | None:
        """接收消息"""
        pass
    
    def delegate_task(self, task: dict, target_agent: str) -> str:
        """委托任务"""
        pass
```

---

## 四、x402 Router

### 4.1 功能

```
x402 Router = 机器间微支付

x402 = HTTP 402 Payment Header
用于：
1. 支付路由：根据金额选择最优支付路径
2. 多币种支持：USDC/VIBE/ETH 等
3. 支付验证：验证支付成功
4. 退款处理：异常情况退款
```

### 4.2 接口设计

```python
@dataclass
class PaymentRequest:
    """支付请求"""
    from_address: str
    to_address: str
    amount: float
    currency: str  # USDC, VIBE, ETH
    memo: str
    max_fee: float


@dataclass
class PaymentResult:
    """支付结果"""
    success: bool
    transaction_hash: str | None
    fee_paid: float
    error: str | None


class x402Router:
    """x402 路由"""
    
    def pay(self, request: PaymentRequest) -> PaymentResult:
        """发起支付"""
        pass
    
    def verify_payment(self, tx_hash: str) -> bool:
        """验证支付"""
        pass
    
    def get_balance(self, address: str, currency: str) -> float:
        """查询余额"""
        pass
    
    def refund(self, original_tx: str) -> PaymentResult:
        """退款"""
        pass
```

---

## 五、文件结构

```
src/usmsb_sdk/
├── protocol/                      # 协议整合层
│   ├── __init__.py
│   ├── mcp_gateway.py           # MCP 网关
│   ├── mcp_registry.py           # 工具注册
│   ├── mcp_client.py            # MCP 客户端
│   ├── a2a_adapter.py          # A2A 适配器
│   ├── a2a_card.py             # Agent Card
│   ├── a2a_federation.py        # 任务联邦
│   ├── x402_router.py           # x402 路由
│   ├── x402_handler.py          # HTTP 402 处理
│   └── multi_wallet.py          # 多币种钱包
│
└── l3/                          # [已完成] L3 模块
    └── ...
```

---

## 六、实现顺序

```
Step 1: multi_wallet.py
        └── 多币种钱包基础（被其他模块依赖）

Step 2: x402_router.py
        └── 支付路由

Step 3: a2a_card.py
        └── Agent Card 定义

Step 4: a2a_adapter.py
        └── Agent 通信适配器

Step 5: mcp_registry.py
        └── 工具注册

Step 6: mcp_gateway.py
        └── MCP 网关

Step 7: 集成测试
        └── 完整协议栈测试
```

---

## 七、验收标准

| 模块 | 验收条件 | 测试 |
|------|---------|------|
| multi_wallet | 支持 USDC/VIBE/ETH 余额查询 | `test_balance_query` |
| x402_router | 支持支付发起和验证 | `test_payment_flow` |
| a2a_card | Agent Card 正确发布 | `test_card_publish` |
| a2a_adapter | Agent 间消息发送接收 | `test_message_exchange` |
| mcp_registry | 工具正确注册和发现 | `test_tool_discovery` |
| mcp_gateway | 工具调用返回正确结果 | `test_tool_call` |

---

## 八、技术选型

| 组件 | 选型 | 说明 |
|------|------|------|
| MCP SDK | `mcp-sdk` (待定) | 官方 SDK |
| A2A SDK | 自行实现 | 基于 JSON-RPC 2.0 |
| x402 | `x402-sdk` (待定) | 官方 SDK |
| 多币种 | web3.py | Ethereum 交互 |

---

*下一步: Phase 1 - USMSB Core 激活*
