# 测试与调试执行计划总览

> 生成时间: 2026-03-08
> 涉及模块: 智能匹配、网络探索、协作管理、模拟仿真

---

## 1. 测试方案文档列表

| 模块 | 文档位置 | 核心测试点 |
|------|---------|-----------|
| **智能匹配** | `tests/TEST_PLAN_ACTIVE_MATCHING.md` | 供需搜索、协商流程、质押验证 |
| **网络探索** | `tests/TEST_PLAN_NETWORK_EXPLORER.md` | 网络发现、能力推荐、信任管理 |
| **协作管理** | `tests/TEST_PLAN_COLLABORATIONS.md` | 协作创建、角色分配、状态流转 |
| **模拟仿真** | `tests/TEST_PLAN_SIMULATIONS.md` | Workflow创建、执行、状态管理 |

---

## 2. 测试执行总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          测试执行流程                                        │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 0: 环境检查 (15分钟)
  ├── 后端服务健康检查
  ├── 数据库连接验证
  ├── 测试数据准备
  └── API Key生成

Phase 1: 智能匹配模块 (40分钟)
  ├── 后端API测试 (15分钟)
  ├── 前端组件测试 (15分钟)
  └── E2E测试 (10分钟)

Phase 2: 网络探索模块 (35分钟)
  ├── 后端API测试 (10分钟)
  ├── 前端组件测试 (15分钟)
  └── E2E测试 (10分钟)

Phase 3: 协作管理模块 (45分钟)
  ├── 后端API测试 (15分钟)
  ├── 前端组件测试 (15分钟)
  └── E2E测试 (15分钟)

Phase 4: 模拟仿真模块 (40分钟)
  ├── 后端API测试 (15分钟)
  ├── 前端组件测试 (15分钟)
  └── E2E测试 (10分钟)

Phase 5: 问题修复与回归 (60分钟)
  ├── Bug修复
  └── 回归测试

总计: 约3.5小时
```

---

## 3. 环境准备检查清单

### 3.1 后端服务

```bash
# 1. 检查服务状态
curl -s http://localhost:8000/api/health | jq

# 预期响应
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

### 3.2 数据库

```bash
# 2. 检查数据库
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT 'Agents' as table_name, COUNT(*) as count FROM ai_agents
UNION ALL
SELECT 'Demands', COUNT(*) FROM demands
UNION ALL
SELECT 'Collaborations', COUNT(*) FROM collaborations
UNION ALL
SELECT 'Workflows', COUNT(*) FROM workflows;
"
```

### 3.3 测试数据

```sql
-- 3. 确保有测试Agent
-- 每个模块测试需要不同类型的Agent

-- 智能匹配需要:
-- - 服务提供方Agent (有capabilities)
-- - 需求方Agent (有demand)

-- 网络探索需要:
-- - 多个在线Agent，不同能力
-- - 不同信誉等级的Agent

-- 协作管理需要:
-- - 高质押Agent (>=100 VIBE) - 可创建协作
-- - 低质押Agent (<100 VIBE) - 用于负面测试

-- 模拟仿真需要:
-- - 至少1个在线Agent用于Workflow执行
```

### 3.4 前端服务

```bash
# 4. 检查前端服务（E2E测试需要）
curl -s http://localhost:5173 | head -20

# 预期: 返回HTML页面
```

---

## 4. 测试数据准备脚本

```sql
-- prepare_test_data.sql
-- 执行此脚本准备所有测试数据

-- 1. 智能匹配测试数据
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('match-supplier-001', 'DataAnalyst', '["data_analysis", "python", "pandas"]', '["ml", "visualization"]', 'online', 0.85, 500),
  ('match-demand-001', 'ProjectOwner', '["project_management"]', '[]', 'online', 0.75, 200);

INSERT OR REPLACE INTO demands (id, agent_id, title, description, required_skills, budget_min, budget_max, status)
VALUES
  ('demand-test-001', 'match-demand-001', '数据分析项目', '需要数据清洗和可视化', '["python", "pandas", "visualization"]', 200, 500, 'active');

-- 2. 网络探索测试数据
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('network-ml-001', 'MLExpert', '["machine_learning", "deep_learning"]', '["tensorflow", "pytorch"]', 'online', 0.95, 1000),
  ('network-nlp-001', 'NLPExpert', '["nlp", "text_analysis"]', '["spacy", "transformers"]', 'online', 0.92, 900),
  ('network-low-001', 'NewbieAgent', '["basic_skills"]', '["python"]', 'online', 0.45, 50);

-- 3. 协作管理测试数据
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('collab-coordinator-001', 'Coordinator', '["project_management"]', '[]', 'online', 0.90, 500),
  ('collab-primary-001', 'Developer', '["backend_development"]', '["python", "fastapi"]', 'online', 0.85, 300),
  ('collab-lowstake-001', 'Junior', '["basic_coding"]', '["python"]', 'online', 0.55, 50);

-- 4. 模拟仿真测试数据
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('sim-agent-001', 'SimulationAgent', '["task_execution", "planning"]', '["python", "analysis"]', 'online', 0.85, 200);

INSERT OR REPLACE INTO workflows (id, name, description, status, steps_count, agent_id, created_at)
VALUES
  ('sim-wf-001', '测试Workflow', '测试用仿真工作流', 'pending', 3, 'sim-agent-001', strftime('%s', 'now') * 1000);
```

---

## 5. 执行测试命令

### 5.1 运行单个模块测试

```bash
# 智能匹配模块
cd usmsb-sdk
python -m pytest tests/test_active_matching.py -v -s

# 网络探索模块
python -m pytest tests/test_network_explorer.py -v -s

# 协作管理模块
python -m pytest tests/test_collaborations.py -v -s

# 模拟仿真模块
python -m pytest tests/test_simulations.py -v -s
```

### 5.2 运行前端组件测试

```bash
cd usmsb-sdk/frontend

# 运行所有测试
npm test

# 运行特定组件
npm test -- --testPathPattern="ActiveMatching"
npm test -- --testPathPattern="NetworkExplorer"
npm test -- --testPathPattern="Collaborations"
npm test -- --testPathPattern="Simulations"
```

### 5.3 运行E2E测试

```bash
cd usmsb-sdk/frontend

# 安装Playwright（首次）
npx playwright install

# 运行E2E测试
npx playwright test e2e/matching.spec.ts
npx playwright test e2e/network-explorer.spec.ts
npx playwright test e2e/collaborations.spec.ts
npx playwright test e2e/simulations.spec.ts
```

### 5.4 运行全部测试

```bash
# 后端API测试
python -m pytest tests/ -v --tb=short

# 前端组件测试
cd frontend && npm test -- --coverage

# E2E测试
npx playwright test
```

---

## 6. 测试报告汇总

### 6.1 预期测试结果

| 模块 | 后端用例数 | 前端用例数 | E2E场景数 | 预期通过率 |
|------|-----------|-----------|----------|-----------|
| 智能匹配 | 10 | 6 | 2 | >= 90% |
| 网络探索 | 7 | 8 | 5 | >= 90% |
| 协作管理 | 12 | 6 | 3 | >= 85% |
| 模拟仿真 | 8 | 8 | 4 | >= 85% |

### 6.2 测试报告模板

```markdown
# 测试执行报告

## 执行信息
- 日期: YYYY-MM-DD HH:MM
- 执行人:
- 环境: Development/Staging

## 测试结果汇总

### 智能匹配模块
| 指标 | 结果 |
|------|------|
| 后端测试 | X/10 通过 |
| 前端测试 | X/6 通过 |
| E2E测试 | X/2 通过 |
| 总通过率 | XX% |

### 网络探索模块
...

## 发现的问题
| ID | 模块 | 描述 | 严重程度 | 状态 |
|----|------|------|---------|------|

## 建议
1. ...
2. ...
```

---

## 7. 确认执行

请确认以下事项后开始执行测试:

### 7.1 必须确认项

- [ ] 后端服务运行正常 (`curl http://localhost:8000/api/health` 返回 200)
- [ ] 数据库连接正常
- [ ] 测试数据已准备
- [ ] 前端开发服务器运行 (E2E测试需要)
- [ ] 已安装测试依赖 (pytest, playwright等)

### 7.2 可选项确认

- [ ] LLM API配置正确（模拟仿真模块需要）
- [ ] 有足够的测试Agent（不同质押等级）
- [ ] 浏览器已安装（Playwright需要）

### 7.3 执行顺序建议

1. 先执行**后端API测试**（不依赖前端）
2. 再执行**前端组件测试**（不依赖E2E）
3. 最后执行**E2E测试**（需要完整环境）

---

## 8. 开始执行

**请选择要执行的测试模块:**

1. [ ] 智能匹配模块 (ActiveMatching)
2. [ ] 网络探索模块 (NetworkExplorer)
3. [ ] 协作管理模块 (Collaborations)
4. [ ] 模拟仿真模块 (Simulations)
5. [ ] 全部模块

**请回复确认执行哪些测试，我将开始运行测试脚本。**
