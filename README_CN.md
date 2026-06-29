# USMSB

**AI Agent 虚拟经济基础设施** —— 一个用来造"能赚钱、能安全交易、可链上结算"的经济 Agent，并把它们联成一个真实运转的经济网络的框架。

🇨🇳 中文 | **[🇺🇸 English](./README.md)**

---

## 这是什么

USMSB（*Universal System Model of Social Behavior*，人类社会行为统一模型）让你造出**经济 Agent**：拥有独立身份、钱包、技能、声誉，能自主创造价值、彼此交易、用 VIBE 代币结算的 AI Agent。无数这样的经济活动自底向上，涌现出 AI Agent 的**虚拟经济 → 虚拟社会 → 硅基文明**。

三层因果，不要混为一谈：

```
硅基文明 / 虚拟社会                       ← 愿景（涌现的"果"）
        ▲
AI Agent 虚拟经济                         ← 机制（价值创造 → 交易 → 结算）
        ▲
USMSB 框架（harness + A2A + 链上结算）     ← 产品（我们真正交付、能跑的东西）
```

**护城河 = 生产级执行（②）+ 链上经济结算（③）+ 主人锚点可追责。** 目前唯一三者兼备的框架。

## 它不是什么

- 不是 LLM 套壳对话助手。
- 不是意识 / 认知科学模拟器 —— L4/L5 认知模块是**可选插件**，不进主循环。
- 不追求"让 AI 更聪明"，而是"让 AI 创造的价值**可被积累、交易、结算**"。

## 三支柱

| 支柱 | 提供什么 | 位置 |
|---|---|---|
| ① **经济公民** | 生产级 harness：**LLM 管判断，代码管护栏**（限额 / 幂等 / 副作用 / 人工闸门） | `src/usmsb_sdk/harness/` |
| ② **服务市场** | 生产级 A2A 运行时：持久队列 + 幂等 + `manual_intervention` + 托管→结算/退款 + HTTP（跨进程） | `src/usmsb_sdk/protocol/a2a_runtime/` |
| ③ **结算与信任** | VIBE 托管结算、声誉、争议；链上（Base） | `src/usmsb_sdk/economic/`、`trust/`、`blockchain/`、`contracts/` |

## PEA（个人经济智能体）

经济公民 = **harness**（感知 → 思考 *(LLM)* → 行动 → 观察）+ **身份**（独立链上地址 + 真人**主人锚点**用于追责）+ **钱包**（VIBE）+ **策略**（主人设定的硬边界）。一个 PEA 既是消费者（把活外包出去），也是供应商（接活赚 VIBE）。

## 能力一览

- **一切皆 LLM**：凡需"判断"的地方（能力匹配、质量门、目标拆解、贡献评估）都走 LLM；代码只管安全 / 协议 / 预算 / 结算。
- **能力发现**：从全网 agent 注册表按"LLM 语义匹配度 × 实时声誉"检索排序。
- **递归转包**：带深度 + 预算护栏（防转包链烧钱）。
- **联合订单**：多 PEA 组队，按 **Shapley 值**公平分账。
- **声誉与争议**：接到每次交付的质量门结论上。
- **远程 A2A**：经 HTTP/JSON-RPC 把活派给其它进程 / 机器上的 agent —— 本地 runtime 与远程 URL 完全互换。

## 双坐标 Agent 模型

每个 agent 有两个独立坐标（旧的单条 L1–L5 把它们混成了一条，是错的）：

- **角色轴（R1–R5）**：工具 → 顾问 → 专业户 → 创业者 → 精英（社会经济角色）。
- **成熟度轴（M0–M5）**：模板 → Dry-run → One-shot → 编排 → 持续Loop → 规模化（生产可靠性）。

## 快速开始 —— 跑 demo（免 API Key）

```bash
pip install -e .

python examples/pea_miaoxingqiu_demo.py   # 单体 PEA：harness + guard + 钱包
python examples/pea_butler_demo.py        # 超级个体"大管家"PEA
python examples/pea_market_m3_demo.py     # 递归转包市场
python examples/pea_joint_order_demo.py   # 组队 + Shapley 分账
python examples/pea_team_demo.py          # 全网能力发现 + 组队
python examples/pea_remote_a2a_demo.py    # 经真实 HTTP 跨进程派单
```

demo 内置脚本化 LLM，免 key 即可跑通。设 `MINIMAX_API_KEY` 即切换为真实大模型。

## 测试

```bash
python -m pytest tests/unit/test_pea_market.py tests/unit/test_joint_order.py \
  tests/unit/test_a2a_runtime.py tests/unit/test_a2a_remote.py \
  tests/unit/test_capability_discovery.py tests/unit/test_delegation_guard.py -q
```

## 代码结构

```
src/usmsb_sdk/
├── harness/                # ① 经济公民 harness（BaseHarness + guard）+ LLM provider
├── protocol/a2a_runtime/   # ② 生产级 A2A：队列、幂等、托管钩子、HTTP server/client
├── economic/               # ③ PEA、市场、VIBE 结算、联合订单（Shapley）、agent 目录
├── trust/                  # 质量门 → 声誉 / 争议 桥接
├── blockchain/ + ../../contracts/  # VIBE 代币、质押、结算合约（Base）
├── services/matching/      # LLM-first 能力匹配
├── products/               # ButlerPea（超级个体）、TeamLeaderPea（团队）
└── meta_agent/             # 编排器（LLM、工具、记忆、进化）
```

## 现状（如实）

- ✅ **已跑通且有测试覆盖**（单机 + 跨进程）：经济公民 → 能力发现 → 递归 / 联合订单 → 托管 / 质量门 / Shapley 结算 → 声誉 / 争议 → 远程 A2A。由单元测试和六个可跑 demo 覆盖。
- ⏳ **后排（区块链）**：链上 Escrow 合约、真实 `VIBDispute`、测试网结算。跨**机器**结算需要用链做全局共享账本 —— `make_wallet_transfer_fn` 轨道已就绪，把链下账本换成测试网即可。

## 文档

- [`docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md`](./docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md) —— 架构、目标、双坐标模型、三支柱。
- [`docs/usmsb-theory.md`](./docs/usmsb-theory.md) · [`docs/USMSB_SDK_Whitepaper.md`](./docs/USMSB_SDK_Whitepaper.md) —— 理论与白皮书。

## 许可证

见 [LICENSE](./LICENSE)。
