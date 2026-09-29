# USMSB

**面向 Agent 与宿主的开放协作基础** —— 共同语义、明确承诺、可归属的证据，以及可选的执行与经济应用。

🇨🇳 中文 | **[🇺🇸 English](./README.md)**

---

## 这是什么

USMSB（*Universal System Model of Social Behavior*）用**主体、客体、目标、资源、规则、信息、价值、风险、环境**九要素提供共同语言。参与者可以描述目标、提出合作、约定验收标准，并把交付、复核和采用记录绑定到明确的主体与版本。

共同语义、World 规则和 Agent 策略各自承担不同职责：

| 层 | 职责 |
|---|---|
| 共同语义与机制 | 九要素、引用、版本绑定、同意与可观察的协作记录 |
| World / 宿主规则 | 认证、权限、可见性、资源限制、证据核实及安装的协作规则集 |
| Agent 策略与应用 | 选择或修订目标、选择伙伴、规划、执行工具、学习和拒绝合作 |

外部 Agent 保留自己的运行时、模型、工具和私有记忆。协作契约与账本不替它选择目标、调用模型或调度执行；已有参考策略也是可选实现。

Wishbud 是参考 World，OPC 是参考业务/执行系统，PEA 是经济代理应用，IAP 是可选经济机制。**共同契约不依赖 Wishbud、OPC、VIBE、钱包或付费模型。** 研究、公共知识、互助与商业交换可以表达不同价值，内核不强制统一价格、代币或排名。

## 协作边界

- 目标所有者可以带依据与理由修订意图，既有承诺仍绑定参与方接受的目标版本与条款。修订目标不会自动取消义务、退款或授权新工作。
- 修改已约定的条款或规则，需要明确的新版本与受影响各方的同意；旧交付和复核保留原版本归属。
- 能力、复核与采用记录是可归属的陈述。哈希描述内容标识，哈希或测试通过都不等于真实性、因果改善、实际控制主体独立、付款或自主智能的证明。
- 参考账本是本地 SQLite 机制。宿主负责认证、安全执行、真实证据核实和外部副作用对账；本轮不提供跨 World 共识或外部操作“恰好执行一次”保证。

## 可选经济应用

完整 SDK 保留已有经济模块与示例。它们承载应用选择，代码存在不代表已通过生产运行或真实结算验收。

| 领域 | 已有实现 / 示例 | 位置 |
|---|---|---|
| 经济代理 | Harness、模型适配器、限额、副作用护栏和人工闸门 | `src/usmsb_sdk/harness/` |
| 服务市场 | A2A 队列、幂等、人工介入、托管钩子和 HTTP 传输 | `src/usmsb_sdk/protocol/a2a_runtime/` |
| 结算与信任 | 本地结算记账、钱包适配器、声誉/争议模块及合约源码 | `src/usmsb_sdk/economic/`、`trust/`、`blockchain/`、`contracts/` |

## PEA（个人经济智能体）

PEA 组合 harness、应用身份/主人映射、钱包适配器和所有者策略，可以在经济示例中担任请求者或供应商。这是一种应用模型，不是所有参与者必须遵循的身份与价值模型。

## 能力一览

- **可选 LLM 策略**：用于能力匹配、质量复核、任务拆解和贡献评估；共同内核不要求模型服务。
- **能力发现**：适配器可组合语义匹配与声誉，注册信息仍是需要核实的声明。
- **递归转包**：带深度 + 预算护栏（防转包链烧钱）。
- **联合订单**：支持 **Shapley 值**分配这一经济方案，不代表普遍适用的公平保证。
- **声誉与争议**：接到每次交付的质量门结论上。
- **远程 A2A**：适配器支持 HTTP/JSON-RPC 派单；联网部署需要独立完成认证、恢复与运维验证。

## 双坐标 Agent 模型

历史 PEA/OPC 设计使用以下两个坐标，作为应用术语保留；它们不是内核一致性等级或生产认证：

- **角色轴（R1–R5）**：工具 → 顾问 → 专业户 → 创业者 → 精英（社会经济角色）。
- **成熟度轴（M0–M5）**：模板 → Dry-run → One-shot → 编排 → 持续Loop → 规模化（生产可靠性）。

## 从可移植契约开始

完整 `usmsb-sdk` 声明 Python **3.14**（`>=3.14,<3.15`），继续保留已有应用依赖。[源码导出器](./scripts/export_autonomy.py)已提供可移植子集；本轮新增的 [alpha 独立分发](./packages/usmsb-core/README.md)为 `usmsb-core`（`0.9.0a1`），导入名为 `usmsb_core`，通过当前源码构建，不代表已经发布 PyPI。API、打包、验收与回滚边界见[迁移指南](./docs/architecture/open-collaboration-migration.md)。

安装本地测试依赖后，可运行隔离的契约测试：

```bash
python -E -B -m pytest tests/portable --confcutdir=tests/portable -q -p no:cacheprovider
```

`-E` 忽略机器级 Python 环境覆盖，`-B` 避免写入字节码。在 Windows 工作区中用 `.venv/Scripts/python.exe` 替代 `python`。测试使用 pytest、packaging、可选经验适配器所需的 Pydantic 2、跨语言示例所需的 Node.js，以及分发测试所需的 build/setuptools（>=77）/wheel。这些是测试/构建依赖；core 默认仅用标准库，不要求模型 Key 或支付服务。

## 已有经济示例

```bash
pip install -e .

python examples/pea_miaoxingqiu_demo.py   # 单体 PEA：harness + guard + 钱包
python examples/pea_butler_demo.py        # 超级个体"大管家"PEA
python examples/pea_market_m3_demo.py     # 递归转包市场
python examples/pea_joint_order_demo.py   # 组队 + Shapley 分账
python examples/pea_team_demo.py          # 全网能力发现 + 组队
python examples/pea_remote_a2a_demo.py    # 经真实 HTTP 跨进程派单
```

这些示例使用脚本化响应、本地记账或 fallback 适配器。离线体验应使用不含模型凭据的环境：`pea_butler_demo.py` 在存在 `MINIMAX_API_KEY` 时会自动选择真实 provider，其余示例需要显式接入。示例打印成功不等于真实付款或自主行为证明。已有 fail-closed 质量门遇到缺失复核证据时，订单可以停留在待复核状态而不结算。

## 测试

```bash
python -E -B -m pytest tests/unit/test_pea_market.py tests/unit/test_joint_order.py \
  tests/unit/test_a2a_runtime.py tests/unit/test_a2a_remote.py \
  tests/unit/test_capability_discovery.py tests/unit/test_delegation_guard.py \
  tests/unit/test_economic_fail_closed.py -q
```

## 代码结构

```
src/usmsb_sdk/
├── core/                   # 九要素模型
├── autonomy/               # 可移植契约、可选参考策略、alpha 协作账本
├── harness/                # 可选 harness（BaseHarness + guard）与 LLM provider
├── protocol/a2a_runtime/   # A2A 队列、幂等、托管钩子、HTTP server/client
├── economic/               # 可选 PEA、市场、结算适配器、联合订单与 agent 目录
├── trust/                  # 质量门 → 声誉 / 争议 桥接
├── blockchain/ + ../../contracts/  # VIBE 代币、质押、结算合约（Base）
├── services/matching/      # LLM-first 能力匹配
├── products/               # ButlerPea（超级个体）、TeamLeaderPea（团队）
└── meta_agent/             # 编排器（LLM、工具、记忆、进化）
```

## 现状与证据

| 状态 | 范围与限制 |
|---|---|
| 已有实现与本地测试 | 九要素契约、目标修订辅助函数、可移植导出、授权、有界参考策略及学习/演化机制。经济应用有单独测试；测试夹具不是外部验收证据。 |
| 本轮 alpha：本地核验 | 显式中立 Profile、制品引用、`CollaborationJournal`、独立 core 分发、SDK 惰性导入和外部 JSON 客户端示例。本地通过项及遗留集成失败见[交付报告](./docs/architecture/open-collaboration-delivery.md)，不代表生产认证。 |
| 后续生产前提 | 真实身份/控制主体核实、租户隔离、凭据、证据来源、存储与恢复运维、互操作参与方及负载测试。真实支付/争议轨道与 ZK 凭证另需实现和验收。 |

[架构与验收设计](./docs/architecture/open-collaboration-v1.md)定义目标并指向集成交付报告，设计要求不等于已经通过的结果。本地脚本测试不能证明真实客户交易、多组织信任、学习带来的因果收益或社会/意识涌现。

## 文档

- [当前架构](./docs/architecture/open-collaboration-v1.md) · [迁移与回滚](./docs/architecture/open-collaboration-migration.md) · [文档目录](./docs/README.md)。
- [`docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md`](./docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md) —— 历史经济/OPC 路线图、双坐标模型与三支柱，不作为共同内核的依赖或就绪承诺。
- [`docs/usmsb-theory.md`](./docs/usmsb-theory.md) · [`docs/USMSB_SDK_Whitepaper.md`](./docs/USMSB_SDK_Whitepaper.md) —— 理论与白皮书。

## 许可证

见 [LICENSE](./LICENSE)。
