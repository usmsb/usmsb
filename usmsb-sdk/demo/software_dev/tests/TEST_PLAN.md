# 场景1：软件开发协作 - 测试计划

## 测试目标

验证 Agent SDK 的核心功能与平台和 Meta Agent 的完整交互闭环。

## 测试范围

### 1. Agent SDK 基础功能测试
- Agent 创建和初始化
- Agent 配置管理
- Agent 技能注册和执行
- Agent 能力定义

### 2. Agent 与平台交互测试
- Agent 注册到平台
- Agent 发现其他 Agent
- Agent 发布服务/需求
- Agent 钱包功能

### 3. Agent 与 Meta Agent 交互测试
- Agent 与 Meta Agent 对话
- Agent 能力画像提取
- Agent 展示能力（Showcase）
- Agent 接收推荐

### 4. 多 Agent 协作测试
- Agent 间消息通信
- Agent 协作会话
- Agent 工作流执行
- Gene Capsule 经验记录

## 测试用例清单

| ID | 测试项 | 优先级 | 前置条件 |
|----|--------|--------|----------|
| TC-001 | Agent 创建和初始化 | P0 | 无 |
| TC-002 | Agent 配置验证 | P0 | TC-001 |
| TC-003 | Agent 技能注册 | P0 | TC-001 |
| TC-004 | Agent 能力定义 | P0 | TC-001 |
| TC-005 | 平台健康检查 | P0 | 服务器运行 |
| TC-006 | Agent 注册到平台 | P0 | TC-005 |
| TC-007 | Agent 发现服务 | P1 | TC-006 |
| TC-008 | 发布服务到市场 | P1 | TC-006 |
| TC-009 | 发布需求到市场 | P1 | TC-006 |
| TC-010 | Meta Agent 对话 | P0 | TC-005 |
| TC-011 | Meta Agent 画像提取 | P1 | TC-010 |
| TC-012 | Meta Agent Showcase | P1 | TC-010 |
| TC-013 | Agent 间消息通信 | P0 | TC-001 |
| TC-014 | 协作会话创建 | P1 | TC-006 |
| TC-015 | Gene Capsule 记录 | P1 | TC-006 |
| TC-016 | 完整协作流程 | P0 | 所有基础测试 |

## 测试环境

- 后端服务：http://127.0.0.1:8000
- 数据库：SQLite (civilization.db)
- Python：3.12+

## 测试数据

```python
# 测试 Agent 配置
TEST_AGENTS = {
    "product_owner": {
        "name": "TestProductOwner",
        "description": "测试产品经理 Agent",
        "capabilities": ["requirement_analysis", "prioritization"]
    },
    "developer": {
        "name": "TestDeveloper",
        "description": "测试开发者 Agent",
        "capabilities": ["coding", "testing"]
    }
}

# 测试服务定义
TEST_SERVICE = {
    "name": "测试开发服务",
    "description": "提供软件开发服务",
    "category": "development",
    "price_range": {"min": 100, "max": 500}
}

# 测试需求定义
TEST_DEMAND = {
    "title": "测试需求：用户登录功能",
    "description": "需要一个用户登录功能的开发服务",
    "required_skills": ["Python", "FastAPI"],
    "budget_range": {"min": 200, "max": 400}
}
```

## 预期结果

所有 P0 优先级测试用例必须通过，P1 测试用例至少 80% 通过。

## 测试输出

- 测试执行日志
- 测试结果汇总
- 问题清单
- 改进建议
