# Agent SDK Demo 场景集合

本目录包含10个独立的 Agent SDK 演示场景，展示 AI 之间协作的完整能力。

## 场景总览

| # | 场景 | 目录 | 类型 | 展示重点 | 复杂度 |
|---|------|------|------|----------|--------|
| 1 | 💻 软件开发协作 | `software_dev/` | 开发 | Collaboration + Workflow | ⭐⭐⭐ |
| 2 | 🎨 内容创作工厂 | `content_creation/` | 创意 | Marketplace + Negotiation | ⭐⭐⭐ |
| 3 | 📦 智能供应链 | `supply_chain/` | 商业 | 全部功能 | ⭐⭐⭐⭐⭐ |
| 4 | 🎵 虚拟演唱会 | `virtual_concert/` | 娱乐 | Workflow + Collaboration | ⭐⭐⭐ |
| 5 | ⎔ 游戏公会 | `game_guild/` | 游戏 | Marketplace + Wallet | ⭐⭐⭐⭐ |
| 6 | ⚖️ DAO 治理 | `dao_governance/` | 治理 | 全部功能 | ⭐⭐⭐⭐⭐ |
| 7 | 🔬 研究实验室 | `research_lab/` | 科研 | Discovery + Learning | ⭐⭐⭐⭐ |
| 8 | 📊 大宗商品交易 | `commodity_trading/` | 金融 | Marketplace + Negotiation | ⭐⭐⭐⭐ |
| 9 | 📈 量化交易团队 | `quant_trading/` | 金融 | Workflow + Learning | ⭐⭐⭐⭐ |
| 10 | 🌾 期货套保协作 | `futures_hedging/` | 金融 | 全部功能 | ⭐⭐⭐⭐⭐ |

## Agent SDK 功能对照

| 功能模块 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|----------|---|---|---|---|---|---|---|---|---|---|
| BaseAgent | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Registration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Communication | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Discovery | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Marketplace | ⬜ | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ✅ | ⬜ | ✅ |
| Wallet | ⬜ | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ✅ | ✅ | ✅ |
| Negotiation | ⬜ | ✅ | ✅ | ⬜ | ✅ | ✅ | ⬜ | ✅ | ⬜ | ✅ |
| Collaboration | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Workflow | ✅ | ⬜ | ✅ | ✅ | ⬜ | ✅ | ✅ | ⬜ | ✅ | ✅ |
| Learning | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gene Capsule | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 目录结构

```
demo/
├── README.md                    # 本文件
├── shared/                      # 共享工具和基类
│   ├── __init__.py
│   ├── base_demo_agent.py      # Demo Agent 基类
│   ├── message_bus.py          # 消息总线
│   ├── visualizer.py           # 可视化工具
│   └── utils.py                # 工具函数
│
├── software_dev/                # 1. 软件开发协作
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── product_owner.py
│   │   ├── architect.py
│   │   ├── developer.py
│   │   ├── reviewer.py
│   │   └── devops.py
│   └── scenarios/
│       └── feature_development.py
│
├── content_creation/             # 2. 内容创作工厂
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── client.py
│   │   ├── writer.py
│   │   ├── designer.py
│   │   ├── editor.py
│   │   └── publisher.py
│   └── scenarios/
│       └── marketing_campaign.py
│
├── supply_chain/                 # 3. 智能供应链 (已存在)
│   └── ...
│
├── virtual_concert/              # 4. 虚拟演唱会
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── producer.py
│   │   ├── composer.py
│   │   ├── choreographer.py
│   │   ├── vj.py
│   │   ├── marketing.py
│   │   └── streamer.py
│   └── scenarios/
│       └── concert_production.py
│
├── game_guild/                   # 5. 游戏公会
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── guild_leader.py
│   │   ├── tank.py
│   │   ├── dps.py
│   │   ├── healer.py
│   │   ├── crafter.py
│   │   ├── trader.py
│   │   └── scout.py
│   └── scenarios/
│       └── raid_dungeon.py
│
├── dao_governance/               # 6. DAO 治理
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── proposer.py
│   │   ├── analyst.py
│   │   ├── debater.py
│   │   ├── voter.py
│   │   ├── executor.py
│   │   ├── auditor.py
│   │   └── guardian.py
│   └── scenarios/
│       └── treasury_proposal.py
│
├── research_lab/                 # 7. 研究实验室
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── principal.py
│   │   ├── theorist.py
│   │   ├── experimenter.py
│   │   ├── analyst.py
│   │   ├── writer.py
│   │   └── reviewer.py
│   └── scenarios/
│       └── research_project.py
│
├── commodity_trading/            # 8. 大宗商品交易
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── buyer.py
│   │   ├── seller.py
│   │   ├── broker.py
│   │   ├── pricing.py
│   │   ├── risk.py
│   │   ├── settlement.py
│   │   └── inspector.py
│   └── scenarios/
│       └── copper_trade.py
│
├── quant_trading/                # 9. 量化交易团队
│   ├── README.md
│   ├── run_demo.py
│   ├── agents/
│   │   ├── strategist.py
│   │   ├── data_agent.py
│   │   ├── backtester.py
│   │   ├── executor.py
│   │   ├── risk.py
│   │   ├── researcher.py
│   │   └── reporter.py
│   └── scenarios/
│       └── momentum_strategy.py
│
└── futures_hedging/              # 10. 期货套保协作
    ├── README.md
    ├── run_demo.py
    ├── agents/
    │   ├── farmer.py
    │   ├── processor.py
    │   ├── speculator.py
    │   ├── hedger.py
    │   ├── analyst.py
    │   ├── broker.py
    │   ├── clearing.py
    │   └── arbitrager.py
    └── scenarios/
        └── corn_hedging.py
```

## 快速开始

```bash
# 运行任意场景
cd demo/software_dev
python run_demo.py

# 或者运行特定场景
python demo/game_guild/run_demo.py
```

## 开发进度

- [x] 1. 软件开发协作 ✅ **已完成 + 测试通过 (100%)**
  - Demo 运行正常
  - SDK 集成测试 100% 通过率 (16/16)
  - [测试报告](./software_dev/tests/TEST_REPORT.md)
- [ ] 2. 内容创作工厂
- [x] 3. 智能供应链 (已存在)
- [ ] 4. 虚拟演唱会
- [ ] 5. 游戏公会
- [ ] 6. DAO 治理
- [ ] 7. 研究实验室
- [ ] 8. 大宗商品交易
- [ ] 9. 量化交易团队
- [ ] 10. 期货套保协作

### SDK 调试状态: ✅ 完成

Agent SDK 和平台 API 已完全调试通过:
- `SkillParameter` 导出问题 ✅
- `CapabilityDefinition` 参数名称对齐 ✅
- `register_skill()` 方法使用 ✅
- 服务发布 API `POST /services` ✅
- 协作会话参数格式 ✅

详见: [测试报告](./software_dev/tests/TEST_REPORT.md)
