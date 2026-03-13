# Agent 协议层需求对接文档

**版本**: 1.0.0
**日期**: 2025年
**状态**: 已确认，待执行

---

## 目录

1. [需求背景](#1-需求背景)
2. [系统定位](#2-系统定位)
3. [核心需求](#3-核心需求)
4. [技术方案](#4-技术方案)
5. [现有代码分析](#5-现有代码分析)
6. [开发计划](#6-开发计划)
7. [接口预留设计](#7-接口预留设计)
8. [TODO List](#8-todo-list)
9. [风险与依赖](#9-风险与依赖)
10. [附录](#10-附录)

---

## 1. 需求背景

### 1.1 项目概述

开发实现 **Agent 创建、注册、多个 Agent 之间通信对话** 的功能和标准案例以及相关模板和 SDK，构建去中心化的 Agent 蜂群系统。

### 1.2 Demo 场景

以**供应链全球报价**为例，设计无限多 Agent 协作的场景：

| 场景特性 | 描述 |
|---------|------|
| 实时价格 | 产业链上下游需要知道实时价格 |
| 全球多地 | 同一品类在全球各地价格不同 |
| 多品类 | 大宗交易涉及众多品类 |
| 双向发起 | 供给报价 + 需求询价 |
| 智能能力 | 比较洽谈、促成成交、价格预测 |

### 1.3 核心目标

1. **Agent SDK** - 支持用户基于 usmsb-sdk 快速开发 Agent
2. **四种协议** - 兼容 A2A、MCP、P2P、HTTP/WebSocket/gRPC 注册和通信
3. **Docker 部署** - Agent 可打包为镜像，部署后自动注册
4. **去中心化** - 每个节点既是客户端也是服务端

---

## 2. 系统定位

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    硅基文明平台 (Silicon Civilization Platform)           │
│            去中心化Agent协作应用 · 用户界面 · 代币经济 · 治理               │
├─────────────────────────────────────────────────────────────────────────┤
│                         USMSB SDK                                       │
│          开发工具包 · API · 智力源适配 · 核心模型实现                       │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                     【本次实现】Agent 协议层                        │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ 1. 协议处理器 (Protocol Handlers)                             │ │ │
│  │  │    A2A, MCP(最新标准), P2P, HTTP/WebSocket/gRPC              │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ 2. 节点层 (Node Layer)                                        │ │ │
│  │  │    节点发现 · 广播机制 · WebSocket同步 · gRPC批量同步         │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ 3. 存储层 (Storage Layer)                                     │ │ │
│  │  │    本地文件(缓存) · SQLite(热数据) · IPFS(全量持久化)          │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ 4. Agent SDK (BaseAgent)                                      │ │ │
│  │  │    统一注册接口 · 统一通信接口 · P2P直连 · Docker模板          │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │ 5. 身份验证层 (Auth Layer) [预留接口]                          │ │ │
│  │  │    钱包绑定验证 · VIBE质押验证                                 │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                        USMSB 模型 (理论层)                               │
│       九大要素 · 九大通用行动接口 · 六大核心逻辑                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 层次职责

| 层次 | 职责 | 本次涉及 |
|------|------|---------|
| USMSB 模型 | 理论框架 | 不涉及 |
| 核心模型层 | 数据结构定义 | 复用现有 |
| **协议层** | Agent 注册、通信、发现 | ✅ 主要工作 |
| **节点层** | 去中心化节点管理 | ✅ 新增 |
| **存储层** | 三层存储协调 | ✅ 新增 |
| **SDK层** | Agent 开发工具包 | ✅ 新增 |
| 身份验证层 | 钱包、质押验证 | 预留接口 |
| 应用层 | 前端、UI | 不涉及 |

---

## 3. 核心需求

### 3.1 四种注册/通信协议

| 协议 | 说明 | 用途 |
|------|------|------|
| **A2A** | Agent-to-Agent | Agent 间直接通信 |
| **MCP** | Model Context Protocol (Anthropic 最新标准) | AI 助手集成 |
| **P2P** | Peer-to-Peer | 去中心化通信 |
| **HTTP/WS/gRPC** | Web 协议族 | REST API、实时通信、高效RPC |

### 3.2 去中心化机制

#### 平台层去中心化

```
┌─────────────────────────────────────────────────────────────────┐
│                    新文明平台节点网络                             │
│                                                                  │
│   ┌──────┐     ┌──────┐     ┌──────┐     ┌──────┐              │
│   │Node 1│─────│Node 2│─────│Node 3│─────│Node N│   ...        │
│   │北京  │     │上海  │     │纽约  │     │伦敦  │              │
│   └──────┘     └──────┘     └──────┘     └──────┘              │
│                                                                  │
│   • Agent 可就近/随机选择节点注册                                 │
│   • 注册数据广播到全网所有节点                                    │
│   • 节点间数据同步（不依赖区块链加密）                            │
│   • 初期 3 个种子节点，之后从任何已知节点可加入                     │
└─────────────────────────────────────────────────────────────────┘
```

#### Agent 层去中心化

```
1. Agent A 向新文明平台注册（任意节点）
2. Agent B 向新文明平台注册（任意节点）
3. 平台广播注册信息，所有节点都知道 A 和 B
4. Agent A 通过平台发现 Agent B（技能/能力匹配）
5. 匹配成功后，A ↔ B 直接 P2P 通信，不经过平台中转
```

### 3.3 三层存储策略

```
┌─────────────────────────────────────────────────────────────────┐
│                        存储架构                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐                                            │
│  │  IPFS (全量)     │  ← 持久化存储，数据全、质量高              │
│  │  • 全部历史数据   │                                            │
│  │  • 全部注册信息   │                                            │
│  │  • 交易记录      │                                            │
│  │  CID 索引       │                                            │
│  └────────┬────────┘                                            │
│           │ 一次性同步 / 定期同步                                 │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  本地 SQLite     │  ← 关系数据，热数据、查询快                 │
│  │  • Agent 索引    │                                            │
│  │  • 会话状态      │                                            │
│  │  • 最近交易      │                                            │
│  └────────┬────────┘                                            │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────┐                                            │
│  │  本地文件        │  ← 文档缓存，速度最快                       │
│  │  • 配置文件      │                                            │
│  │  • 临时数据      │                                            │
│  │  • 缓存文档      │                                            │
│  └─────────────────┘                                            │
│                                                                  │
│  节点间 P2P 同步：增量同步最新数据                                │
└─────────────────────────────────────────────────────────────────┘
```

### 3.4 Agent 匹配/发现的三种方式

| 方式 | 描述 |
|------|------|
| **关键词/技能匹配** | Agent 定义 skills 和 keywords，按名称、类别匹配 |
| **推荐算法** | 基于历史交互、相似度计算进行推荐 |
| **主动握手 + 系统Agent** | Agent 主动握手聊天；平台节点内置系统Agent，知晓所有注册Agent，提供智能推荐 |

### 3.5 身份验证机制

```
Agent 注册前:
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 钱包绑定  │ ─→ │ VIBE质押 │ ─→ │ 获得授权  │ ─→ 允许注册
└──────────┘    └──────────┘    └──────────┘

Agent 通信前:
┌──────────┐    ┌──────────┐    ┌──────────┐
│ 身份验证  │ ─→ │ 质押校验 │ ─→ │ 通行证   │ ─→ 允许通信
└──────────┘    └──────────┘    └──────────┘
```

---

## 4. 技术方案

### 4.1 节点间同步协议

**推荐：WebSocket 长连接 + gRPC 混合方案**

| 场景 | 协议 | 说明 |
|------|------|------|
| 实时广播 | WebSocket | 新Agent注册、状态变更，双向实时推送 |
| 全量同步 | gRPC | 节点启动、定期校验，批量数据传输 |
| 冷数据同步 | IPFS | 历史数据，CID寻址下载 |

#### 消息格式

```json
{
  "type": "agent_register" | "agent_update" | "agent_unregister" |
          "sync_request" | "sync_response" | "heartbeat",
  "version": "1.0",
  "timestamp": 1708099200,
  "source_node": "node_beijing_001",
  "data": {
    "agent_id": "agent_xxx",
    "name": "SupplyAgent",
    "capabilities": ["报价", "谈判"],
    "protocol": "mcp",
    "endpoint": "https://...",
    "signature": "0x..."
  }
}
```

### 4.2 MCP 协议（最新标准）

```
MCP 协议核心组件：
├── Transport Layer: SSE (Server-Sent Events) / WebSocket
├── Protocol Layer: JSON-RPC 2.0
├── Capability Negotiation: tools, resources, prompts
└── Session Management: connection lifecycle
```

### 4.3 IPFS 集成

- 使用 **ipfshttpclient** Python SDK
- 连接**全球公共 IPFS 网络**
- 不自建 IPFS 节点

```python
import ipfshttpclient

# 连接公共网关
client = ipfshttpclient.connect("/ip4/127.0.0.1/tcp/5001")

# 上传数据
cid = client.add_json(agent_profile)

# 下载数据
profile = client.get_json(cid)
```

### 4.4 Docker 部署

```dockerfile
# Agent Docker 模板
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# 自动注册脚本
CMD ["python", "-m", "agent", "--auto-register"]
```

---

## 5. 现有代码分析

### 5.1 可复用的现有代码

| 模块 | 位置 | 说明 |
|------|------|------|
| 外部Agent适配器 | `platform/external/external_agent_adapter.py` | 已有 A2A, HTTP 协议框架 |
| P2P节点 | `node/decentralized_node.py` | 已有 Gossip 协议、服务发现 |
| 配置管理 | `config/settings.py` | Pydantic Settings |
| 数据模型 | `data_management/models.py` | SQLAlchemy ORM |
| 核心元素 | `core/elements.py` | Agent, Goal, Resource 等 |
| 数字货币管理 | `platform/blockchain/digital_currency_manager.py` | 质押相关逻辑 |

### 5.2 待完善的部分

| 模块 | 当前状态 | 需要工作 |
|------|---------|---------|
| MCP 协议 | 有框架 | 完善最新标准实现 |
| P2P 协议 | 有框架 | 完善通信逻辑 |
| WebSocket 协议 | 未实现 | 新增 |
| gRPC 协议 | 未实现 | 新增 |
| 节点间同步 | 部分 | 完善广播机制 |
| IPFS 存储 | 未实现 | 新增 |
| BaseAgent SDK | 未实现 | 新增 |
| 身份验证 | 部分存在 | 对接钱包质押 |

### 5.3 目录结构规划

```
src/usmsb_sdk/
├── platform/
│   └── external/
│       ├── external_agent_adapter.py    # [已有] 外部Agent适配器
│       ├── protocol/                     # [新增] 协议处理器
│       │   ├── __init__.py
│       │   ├── a2a_handler.py           # A2A 协议
│       │   ├── mcp_handler.py           # MCP 协议（最新标准）
│       │   ├── p2p_handler.py           # P2P 协议
│       │   ├── http_handler.py          # HTTP 协议
│       │   ├── websocket_handler.py     # WebSocket 协议
│       │   └── grpc_handler.py          # gRPC 协议
│       ├── node/                         # [新增] 节点管理
│       │   ├── __init__.py
│       │   ├── node_manager.py          # 节点管理器
│       │   ├── node_discovery.py        # 节点发现
│       │   ├── broadcast_service.py     # 广播服务
│       │   └── sync_service.py          # 同步服务
│       ├── storage/                      # [新增] 存储层
│       │   ├── __init__.py
│       │   ├── storage_manager.py       # 存储协调器
│       │   ├── file_storage.py          # 文件存储
│       │   ├── sqlite_storage.py        # SQLite 存储
│       │   └── ipfs_storage.py          # IPFS 存储
│       └── auth/                         # [新增] 身份验证
│           ├── __init__.py
│           ├── wallet_auth.py           # 钱包验证（预留）
│           └── stake_verifier.py        # 质押验证（预留）
│
├── agent_sdk/                            # [新增] Agent SDK
│   ├── __init__.py
│   ├── base_agent.py                    # BaseAgent 抽象类
│   ├── agent_builder.py                 # Agent 构建器
│   ├── registration.py                  # 注册管理
│   ├── communication.py                 # 通信管理
│   └── templates/                       # Docker 模板
│       ├── Dockerfile.agent
│       └── docker-compose.yml

demo/
└── civilization_platform/
    └── supply_chain/                     # [新增] 供应链报价 Demo
        ├── README.md
        ├── docker-compose.yml
        ├── supplier_agent/              # 供给报价 Agent
        ├── buyer_agent/                 # 需求询价 Agent
        ├── predictor_agent/             # 价格预测 Agent
        └── match_agent/                 # 交易撮合 Agent
```

---

## 6. 开发计划

### Phase 1: 协议层 + SDK

#### 1.1 协议处理器完善
- [ ] MCP 协议（最新标准）
- [ ] P2P 协议完善
- [ ] WebSocket 协议实现
- [ ] gRPC 协议实现
- [ ] 协议处理器工厂模式

#### 1.2 节点层实现
- [ ] 节点启动与配置
- [ ] WebSocket 节点间通信
- [ ] gRPC 批量同步
- [ ] 广播与发现机制
- [ ] 3个种子节点配置
- [ ] Docker 部署配置

#### 1.3 数据存储层
- [ ] 本地文件存储实现
- [ ] SQLite 存储实现
- [ ] IPFS SDK 集成
- [ ] 三层存储协调器
- [ ] 数据同步策略

#### 1.4 Agent SDK
- [ ] BaseAgent 抽象类
- [ ] 统一注册接口
- [ ] 统一通信接口
- [ ] P2P 直连能力
- [ ] Docker 镜像模板

#### 1.5 身份验证对接
- [ ] 钱包绑定校验接口（预留）
- [ ] VIBE 质押校验接口（预留）

### Phase 2: Demo + 系统Agent

#### 2.1 供应链报价 Demo (demo/civilization_platform/supply_chain/)
- [ ] SupplierAgent（供给报价）
- [ ] BuyerAgent（需求询价）
- [ ] PredictorAgent（价格预测）
- [ ] MatchAgent（交易撮合）
- [ ] Demo 部署文档

#### 2.2 系统Agent
- [ ] 平台节点内置系统Agent
- [ ] 知晓所有注册Agent
- [ ] 智能推荐会话

#### 2.3 测试与生产
- [ ] 单元测试
- [ ] 集成测试
- [ ] 压力测试
- [ ] 生产部署

---

## 7. 接口预留设计

### 7.1 钱包验证接口

```python
# src/usmsb_sdk/platform/external/auth/wallet_auth.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class Permission(str, Enum):
    REGISTER = "register"
    COMMUNICATE = "communicate"
    TRANSACT = "transact"
    STAKE = "stake"

@dataclass
class WalletAuthResult:
    verified: bool
    wallet_address: str
    permissions: List[Permission]
    error_message: Optional[str] = None

class IWalletAuthenticator(ABC):
    """钱包验证接口 - 预留给钱包模块实现"""

    @abstractmethod
    async def verify_wallet(
        self,
        wallet_address: str,
        signature: str,
        message: str
    ) -> WalletAuthResult:
        """
        验证钱包所有权

        Args:
            wallet_address: 钱包地址
            signature: 签名
            message: 原始消息

        Returns:
            WalletAuthResult: 验证结果
        """
        pass

    @abstractmethod
    async def is_wallet_bound(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """
        检查钱包是否已绑定到指定Agent

        Args:
            wallet_address: 钱包地址
            agent_id: Agent ID

        Returns:
            bool: 是否已绑定
        """
        pass

class MockWalletAuthenticator(IWalletAuthenticator):
    """测试用 Mock 实现"""

    async def verify_wallet(
        self,
        wallet_address: str,
        signature: str,
        message: str
    ) -> WalletAuthResult:
        return WalletAuthResult(
            verified=True,
            wallet_address=wallet_address,
            permissions=list(Permission)
        )

    async def is_wallet_bound(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        return True
```

### 7.2 质押验证接口

```python
# src/usmsb_sdk/platform/external/auth/stake_verifier.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class StakeTier(str, Enum):
    BRONZE = "bronze"      # 最低质押
    SILVER = "silver"      # 中等质押
    GOLD = "gold"          # 高级质押
    PLATINUM = "platinum"  # 最高质押

@dataclass
class StakeInfo:
    wallet_address: str
    staked_amount: float
    tier: StakeTier
    lock_until: Optional[int]  # Unix timestamp
    is_active: bool

@dataclass
class StakeVerificationResult:
    verified: bool
    stake_info: Optional[StakeInfo]
    error_message: Optional[str] = None

class IStakeVerifier(ABC):
    """质押验证接口 - 预留给质押模块实现"""

    @abstractmethod
    async def verify_stake(
        self,
        wallet_address: str,
        minimum_amount: float = 0.0
    ) -> StakeVerificationResult:
        """
        验证钱包的质押状态

        Args:
            wallet_address: 钱包地址
            minimum_amount: 最低质押要求

        Returns:
            StakeVerificationResult: 验证结果
        """
        pass

    @abstractmethod
    async def get_stake_tier(
        self,
        wallet_address: str
    ) -> Optional[StakeTier]:
        """
        获取质押等级

        Args:
            wallet_address: 钱包地址

        Returns:
            Optional[StakeTier]: 质押等级，无质押返回None
        """
        pass

    @abstractmethod
    async def can_register_agent(
        self,
        wallet_address: str
    ) -> bool:
        """
        检查是否可以注册Agent

        Args:
            wallet_address: 钱包地址

        Returns:
            bool: 是否有足够质押
        """
        pass

class MockStakeVerifier(IStakeVerifier):
    """测试用 Mock 实现"""

    async def verify_stake(
        self,
        wallet_address: str,
        minimum_amount: float = 0.0
    ) -> StakeVerificationResult:
        return StakeVerificationResult(
            verified=True,
            stake_info=StakeInfo(
                wallet_address=wallet_address,
                staked_amount=1000.0,
                tier=StakeTier.GOLD,
                lock_until=None,
                is_active=True
            )
        )

    async def get_stake_tier(
        self,
        wallet_address: str
    ) -> Optional[StakeTier]:
        return StakeTier.GOLD

    async def can_register_agent(
        self,
        wallet_address: str
    ) -> bool:
        return True
```

### 7.3 身份验证协调器

```python
# src/usmsb_sdk/platform/external/auth/auth_coordinator.py

from typing import Optional
from .wallet_auth import IWalletAuthenticator, WalletAuthResult
from .stake_verifier import IStakeVerifier, StakeVerificationResult

@dataclass
class AuthContext:
    """身份验证上下文"""
    wallet_address: str
    agent_id: Optional[str] = None
    signature: Optional[str] = None
    message: Optional[str] = None

@dataclass
class FullAuthResult:
    """完整验证结果"""
    success: bool
    wallet_verified: bool
    stake_verified: bool
    permissions: List[str]
    error_message: Optional[str] = None

class AuthCoordinator:
    """身份验证协调器"""

    def __init__(
        self,
        wallet_auth: IWalletAuthenticator,
        stake_verifier: IStakeVerifier
    ):
        self.wallet_auth = wallet_auth
        self.stake_verifier = stake_verifier

    async def verify_for_registration(
        self,
        context: AuthContext
    ) -> FullAuthResult:
        """验证是否允许注册Agent"""
        # 1. 验证钱包
        wallet_result = await self.wallet_auth.verify_wallet(
            context.wallet_address,
            context.signature or "",
            context.message or ""
        )

        if not wallet_result.verified:
            return FullAuthResult(
                success=False,
                wallet_verified=False,
                stake_verified=False,
                permissions=[],
                error_message="钱包验证失败"
            )

        # 2. 验证质押
        can_register = await self.stake_verifier.can_register_agent(
            context.wallet_address
        )

        if not can_register:
            return FullAuthResult(
                success=False,
                wallet_verified=True,
                stake_verified=False,
                permissions=[],
                error_message="质押不足，无法注册Agent"
            )

        return FullAuthResult(
            success=True,
            wallet_verified=True,
            stake_verified=True,
            permissions=[p.value for p in wallet_result.permissions]
        )

    async def verify_for_communication(
        self,
        context: AuthContext
    ) -> FullAuthResult:
        """验证是否允许Agent通信"""
        # 类似注册验证，但权限要求可能不同
        pass
```

---

## 8. TODO List

### TODO-001: 钱包绑定接口对接

| 属性 | 值 |
|------|-----|
| **状态** | 待开发 |
| **依赖方** | 协议层、Agent SDK |
| **描述** | 钱包绑定验证接口，用于 Agent 注册前的身份校验 |
| **接口设计** | `IWalletAuthenticator` 抽象类（已预留） |
| **文件位置** | `src/usmsb_sdk/platform/external/auth/wallet_auth.py` |
| **负责人** | 待定 |
| **预计时间** | Phase 2 |
| **关联模块** | 区块链模块、前端钱包连接 |

### TODO-002: VIBE 质押接口对接

| 属性 | 值 |
|------|-----|
| **状态** | 待开发 |
| **依赖方** | 协议层、Agent SDK |
| **描述** | VIBE 代币质押验证接口，用于 Agent 注册和通信前的权限校验 |
| **接口设计** | `IStakeVerifier` 抽象类（已预留） |
| **文件位置** | `src/usmsb_sdk/platform/external/auth/stake_verifier.py` |
| **负责人** | 待定 |
| **预计时间** | Phase 2 |
| **关联模块** | `platform/blockchain/digital_currency_manager.py` |

### TODO-003: 测试钱包环境准备

| 属性 | 值 |
|------|-----|
| **状态** | 待提供 |
| **提供方** | 用户 |
| **描述** | 测试用的钱包地址和质押环境 |
| **用途** | 集成测试和 Demo 演示 |
| **预计时间** | Phase 1 完成后 |
| **要求** | 需要一个已绑定并质押 VIBE 的测试钱包地址 |

### TODO-004: MCP 协议最新标准确认

| 属性 | 值 |
|------|-----|
| **状态** | 待确认 |
| **描述** | 确认 Anthropic MCP 协议的最新版本和规范 |
| **参考** | https://modelcontextprotocol.io/ |
| **负责人** | 开发团队 |
| **预计时间** | Phase 1 开始时 |

### TODO-005: IPFS 公共网关可用性测试

| 属性 | 值 |
|------|-----|
| **状态** | 待测试 |
| **描述** | 测试全球公共 IPFS 网关的可用性和性能 |
| **测试项** | 连接稳定性、上传下载速度、CID 解析 |
| **负责人** | 开发团队 |
| **预计时间** | Phase 1 存储层开发时 |

---

## 9. 风险与依赖

### 9.1 技术风险

| 风险 | 等级 | 缓解措施 |
|------|------|---------|
| IPFS 公共网关不稳定 | 中 | 支持多网关切换，本地缓存优先 |
| 节点间同步延迟 | 中 | WebSocket 实时 + 定期全量校验 |
| MCP 协议变更 | 低 | 抽象协议层，易于替换 |
| 大规模 Agent 压力 | 中 | 分片、负载均衡、异步处理 |

### 9.2 依赖关系

| 依赖项 | 状态 | 影响 |
|--------|------|------|
| 钱包绑定模块 | 未开发 | 无法进行生产环境身份验证 |
| VIBE 质押模块 | 部分存在 | 可复用 digital_currency_manager |
| 测试钱包环境 | 未提供 | 影响集成测试 |
| IPFS 公共网络 | 可用 | 正常 |

### 9.3 里程碑

| 里程碑 | 内容 | 交付物 |
|--------|------|--------|
| M1 | 协议层完成 | 协议处理器、节点管理 |
| M2 | 存储层完成 | 三层存储协调 |
| M3 | SDK 完成 | BaseAgent、Docker 模板 |
| M4 | Demo 完成 | 供应链报价 Demo |
| M5 | 生产就绪 | 测试通过、文档完善 |

---

## 10. 附录

### 10.1 参考文档

- USMSB SDK 白皮书: `frontend/public/docs/whitepaper.md`
- API 参考: `frontend/public/docs/api-reference.md`
- 概念说明: `frontend/public/docs/concepts.md`
- 用户指南: `frontend/public/docs/user-guide.md`
- Agent 注册需求: `demo/civilization_platform/agent注册需求.md`

### 10.2 相关代码文件

- 外部 Agent 适配器: `src/usmsb_sdk/platform/external/external_agent_adapter.py`
- P2P 节点: `src/usmsb_sdk/node/decentralized_node.py`
- 数字货币管理: `src/usmsb_sdk/platform/blockchain/digital_currency_manager.py`
- 配置管理: `src/usmsb_sdk/config/settings.py`
- 数据模型: `src/usmsb_sdk/data_management/models.py`

### 10.3 外部资源

- MCP 协议规范: https://modelcontextprotocol.io/
- IPFS 文档: https://docs.ipfs.tech/
- ipfshttpclient: https://github.com/ipfs-shipyard/py-ipfs-http-client

### 10.4 变更历史

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|---------|------|
| 1.0.0 | 2025 | 初始版本 | Claude |

---

**文档状态**: ✅ 已确认

**下一步**: 探索代码结构 → 创建开发团队 → 开始执行

---

*本文档由需求对接会议生成，如有疑问请联系项目负责人。*
