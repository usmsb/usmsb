# 软件开发协作 Demo

## 场景描述

模拟软件开发团队，5 个 AI Agent 协作完成功能开发任务。

## 角色

| 角色 | 职责 | 端口 |
|------|------|------|
| ProductOwner | 需求分析、任务拆分、验收 | 8081 |
| Architect | 技术设计、架构决策 | 8082 |
| Developer | 代码实现、单元测试 | 8083 |
| Reviewer | 代码审查、质量把控 | 8084 |
| DevOps | 部署配置、监控告警 | 8085 |

## 协作流程

```
ProductOwner 需求分析 → Architect 架构设计 → Developer 代码实现
                                                        ↓
                                              Reviewer 代码审查
                                                        ↓
                                                DevOps 部署上线
```

## 目录结构

```
demo/software_dev/
├── run_demo.py              # 主入口，运行 Demo
├── start_agent_service.py   # 启动 Agent HTTP 服务
├── cleanup_and_reregister.py # 清理并重新注册 Agents
├── agents/                 # Agent 实现
│   ├── product_owner.py
│   ├── architect.py
│   ├── developer.py
│   ├── reviewer.py
│   └── devops.py
└── tests/                  # 测试
    ├── test_unit.py
    ├── test_integration.py
    └── test_e2e.py

demo/shared/                # 共享模块
├── base_demo_agent.py      # Agent 基类
├── visualizer.py           # 可视化工具
└── utils.py                # 工具函数
```

## 运行方式

1. **启动平台后端**
   ```bash
   cd usmsb-sdk
   python -m uvicorn usmsb_sdk.api.rest.main:app --reload
   ```

2. **启动 Agent HTTP 服务**
   ```bash
   cd demo/software_dev
   python start_agent_service.py
   ```

3. **运行 Demo**
   ```bash
   cd demo/software_dev
   python run_demo.py
   ```

## 演示功能

- Agent 注册与心跳
- 协作流程（需求→设计→实现→审查→部署）
- Agent 发现与匹配
- 服务市场
- 钱包与质押
