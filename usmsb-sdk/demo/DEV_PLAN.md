# Demo 场景开发计划

## 开发策略
- 先开发一个场景，调试通 SDK 后再开发其他场景
- 每个场景独立可运行
- 统一使用 shared/ 目录下的基础设施

## 开发顺序

### 第一批（当前）
- [x] shared/ - 共享基础设施
- [x] 1. software_dev/ - 软件开发协作 ✅ **已完成**

### 第二批（待SDK调通后）
- [ ] 2. content_creation/ - 内容创作工厂
- [ ] 5. game_guild/ - 游戏公会

### 第三批
- [ ] 4. virtual_concert/ - 虚拟演唱会
- [ ] 7. research_lab/ - 研究实验室

### 第四批
- [ ] 8. commodity_trading/ - 大宗商品交易
- [ ] 9. quant_trading/ - 量化交易团队
- [ ] 10. futures_hedging/ - 期货套保协作

### 第五批（复杂场景）
- [ ] 3. supply_chain/ - 智能供应链（已有，需升级）
- [ ] 6. dao_governance/ - DAO 治理

---

## 场景 1：软件开发协作 详细设计

### 场景描述
模拟一个软件开发团队，5个 AI Agent 协作完成一个功能开发任务。

### 角色

| 角色 | 职责 | 主要技能 |
|------|------|----------|
| ProductOwner | 需求分析、任务拆分、验收 |需求分析、优先级排序 |
| Architect | 技术设计、架构决策 | 架构设计、技术选型 |
| Developer | 代码实现、单元测试 | 编码、测试、调试 |
| Reviewer | 代码审查、质量把控 | 代码评审、最佳实践 |
| DevOps | 部署配置、监控告警 | CI/CD、监控部署 |

### 协作流程

```
1. ProductOwner 发布需求
   ↓
2. Architect 设计方案，拆分任务
   ↓
3. Developer 领取任务，实现代码
   ↓
4. Developer 提交代码给 Reviewer
   ↓
5. Reviewer 审查代码，反馈意见
   ↓
6. (如需修改) Developer 修改代码 → 回到步骤4
   ↓
7. 审查通过 → DevOps 部署
   ↓
8. 完成任务，记录经验到 Gene Capsule
```

### 展示的 Agent SDK 功能

- [x] BaseAgent - 基础 Agent 类
- [x] Registration - Agent 注册
- [x] Communication - Agent 间通信
- [x] Discovery - 发现其他 Agent
- [x] Collaboration - 协作会话
- [x] Workflow - 工作流编排
- [x] Gene Capsule - 经验记录
- [x] Learning - 学习优化

### 文件结构

```
software_dev/
├── README.md              # 场景说明
├── run_demo.py            # 运行入口
├── agents/
│   ├── __init__.py
│   ├── product_owner.py   # 产品经理 AI
│   ├── architect.py       # 架构师 AI
│   ├── developer.py       # 开发者 AI
│   ├── reviewer.py        # 代码审查 AI
│   └── devops.py          # 运维 AI
├── scenarios/
│   ├── __init__.py
│   └── feature_development.py  # 功能开发场景
└── workflow/
    ├── __init__.py
    └── dev_workflow.py    # 开发工作流定义
```

### 预期输出

运行 `python run_demo.py` 后，应该看到：

```
🚀 软件开发协作 Demo 启动
============================================================

➕ ProductOwner 加入团队
➕ Architect 加入团队
➕ Developer 加入团队
➕ Reviewer 加入团队
➕ DevOps 加入团队

📋 ProductOwner 发布需求: "用户登录功能"
💬 ProductOwner → Architect: 需求文档...
💬 Architect → Developer: 技术设计...
💬 Developer → Reviewer: 代码提交...
💬 Reviewer → Developer: 审查反馈...
💬 Developer → Reviewer: 修改后代码...
✅ 审查通过
💬 Reviewer → DevOps: 部署请求...
✅ DevOps 部署完成

============================================================
📊 场景摘要: 软件开发协作
============================================================
  消息总数: 15
  事件总数: 8
  Agent 数量: 5

  Agent 状态:
    - ProductOwner: completed
    - Architect: completed
    - Developer: completed
    - Reviewer: completed
    - DevOps: completed
============================================================
```

---

## 其他场景简要设计（待开发）

### 场景 2：内容创作工厂
- 角色：Client, Writer, Designer, Editor, Publisher
- 流程：需求发布 → 创作中 → 审核修改 → 发布
- 重点：Marketplace, Negotiation

### 场景 3：智能供应链
- 角色：Buyer, Supplier, Matchmaker, Negotiator, Logistics, Quality, Finance
- 流程：需求发布 → 匹配 → 洽谈 → 物流 → 质检 → 结算
- 重点：全部功能

### 场景 4：虚拟演唱会
- 角色：Producer, Composer, Choreographer, VJ, Marketing, Streamer
- 流程：策划 → 创作 → 排练 → 宣传 → 直播
- 重点：Workflow, Collaboration

### 场景 5：游戏公会
- 角色：GuildLeader, Tank, DPS, Healer, Crafter, Trader, Scout
- 流程：目标设定 → 组队 → 打副本 → 分配战利品 → 交易
- 重点：Marketplace, Wallet, Collaboration

### 场景 6：DAO 治理
- 角色：Proposer, Analyst, Debater, Voter, Executor, Auditor, Guardian
- 流程：提案 → 分析 → 辩论 → 投票 → 执行 → 审计
- 重点：全部功能

### 场景 7：研究实验室
- 角色：Principal, Theorist, Experimenter, Analyst, Writer, Reviewer
- 流程：课题 → 假设 → 实验 → 分析 → 论文 → 评审
- 重点：Discovery, Learning, Gene Capsule

### 场景 8：大宗商品交易
- 角色：Buyer, Seller, Broker, Pricing, Risk, Settlement, Inspector
- 流程：需求/供应发布 → 报价 → 匹配 → 洽谈 → 质检 → 结算
- 重点：Marketplace, Negotiation, Wallet

### 场景 9：量化交易团队
- 角色：Strategist, DataAgent, Backtester, Executor, Risk, Researcher, Reporter
- 流程：策略设计 → 数据获取 → 回测 → 执行 → 风控 → 报告
- 重点：Workflow, Learning

### 场景 10：期货套保协作
- 角色：Farmer, Processor, Speculator, Hedger, Analyst, Broker, Clearing, Arbitrager
- 流程：套保需求 → 方案设计 → 市场分析 → 建仓 → 持仓管理 → 到期交割
- 重点：全部功能
