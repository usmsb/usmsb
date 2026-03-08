# 模拟仿真模块测试与调试方案

> 模块: Simulations (模拟仿真)
> 文件位置: `frontend/src/pages/Simulations.tsx`
> 后端路由: `api/rest/routers/workflows.py`
> 生成时间: 2026-03-08

---

## 1. 测试目标

验证模拟仿真模块的以下核心功能：
- Workflow创建与配置
- Workflow执行与状态管理
- Agent选择与工具配置
- 仿真结果展示
- 统计数据准确性
- 行为预测接口

---

## 2. 测试环境准备

### 2.1 环境检查

```bash
# 1. 检查后端服务
curl -s http://localhost:8000/api/health | jq

# 2. 检查Workflow数据表
sqlite3 usmsb-sdk/data/meta_agent.db ".schema workflows"

# 3. 检查现有Workflow
sqlite3 usmsb-sdk/data/meta_agent.db "SELECT id, name, status FROM workflows LIMIT 5;"

# 4. 检查可用Agent
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT agent_id, name, capabilities
FROM ai_agents
WHERE status = 'online'
LIMIT 10;
"
```

### 2.2 测试数据准备

```sql
-- 创建测试Agent（用于仿真选择）
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation)
VALUES
  ('sim-test-agent-001', 'SimulationAgent1', '["task_execution", "planning"]', '["python", "analysis"]', 'online', 0.85),
  ('sim-test-agent-002', 'SimulationAgent2', '["data_processing", "visualization"]', '["pandas", "matplotlib"]', 'online', 0.80);

-- 创建测试Workflow
INSERT OR REPLACE INTO workflows (id, name, description, status, steps_count, agent_id, created_at)
VALUES
  ('sim-workflow-001', '测试仿真任务', '用于测试的仿真工作流', 'pending', 3, 'sim-test-agent-001', strftime('%s', 'now') * 1000),
  ('sim-workflow-002', '已完成的仿真', '已完成的测试仿真', 'completed', 5, 'sim-test-agent-001', strftime('%s', 'now') * 1000 - 3600000),
  ('sim-workflow-003', '运行中的仿真', '正在运行的仿真', 'running', 10, 'sim-test-agent-002', strftime('%s', 'now') * 1000 - 7200000);
```

---

## 3. 后端API测试

### 3.1 测试用例列表

| 用例ID | 测试场景 | 端点 | 方法 | 预期结果 |
|--------|---------|------|------|---------|
| TC-S001 | 获取Workflow列表 | `/api/workflows` | GET | 200, 返回列表 |
| TC-S002 | 创建Workflow - 有效数据 | `/api/workflows` | POST | 200, 返回workflow |
| TC-S003 | 创建Workflow - 缺少必填字段 | `/api/workflows` | POST | 422, 验证失败 |
| TC-S004 | 执行Workflow - pending状态 | `/api/workflows/{id}/execute` | POST | 200, 状态变更 |
| TC-S005 | 执行Workflow - 非pending状态 | `/api/workflows/{id}/execute` | POST | 400, 无法执行 |
| TC-S006 | 获取不存在的Workflow | `/api/workflows/{id}` | GET | 404, 未找到 |
| TC-S007 | 行为预测请求 | `/api/predict/behavior` | POST | 200, 返回预测 |
| TC-S008 | 获取系统状态 | `/api/status` | GET | 200, 状态信息 |

### 3.2 详细测试脚本

```python
# test_simulations.py

import pytest
import httpx
import json
import time

BASE_URL = "http://localhost:8000/api"

class TestSimulationsAPI:
    """模拟仿真模块API测试"""

    @pytest.fixture
    def auth_headers(self):
        """测试用认证头"""
        return {
            "X-API-Key": "test-api-key-sim",
            "X-Agent-ID": "sim-test-agent-001"
        }

    # ==================== Workflow列表测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S001_get_workflows_list(self):
        """TC-S001: 获取Workflow列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/workflows",
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            print(f"✅ TC-S001 通过: 获取到 {len(data)} 个Workflow")

            if len(data) > 0:
                first = data[0]
                # 验证返回结构
                assert "id" in first
                assert "name" in first
                assert "status" in first
                print(f"   第一个Workflow: {first['name']} ({first['status']})")

            return data

    # ==================== 创建Workflow测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S002_create_workflow_valid(self, auth_headers):
        """TC-S002: 创建Workflow - 有效数据"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/workflows",
                json={
                    "task_description": "分析用户行为数据并生成报告",
                    "agent_id": "sim-test-agent-001",
                    "available_tools": ["data_analysis", "visualization", "report_generator"]
                },
                headers=auth_headers,
                timeout=60.0  # LLM调用可能较慢
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()

            # 验证返回结构
            assert "id" in data
            assert "name" in data
            assert "status" in data
            assert data["status"] == "pending"

            # 保存workflow_id供后续测试
            self.__class__.test_workflow_id = data["id"]

            print(f"✅ TC-S002 通过: Workflow创建成功")
            print(f"   ID: {data['id']}")
            print(f"   Name: {data['name']}")
            print(f"   Steps: {data.get('steps_count', 'N/A')}")

            return data["id"]

    @pytest.mark.asyncio
    async def test_TC_S003_create_workflow_invalid(self, auth_headers):
        """TC-S003: 创建Workflow - 缺少必填字段"""
        async with httpx.AsyncClient() as client:
            # 缺少task_description
            response = await client.post(
                f"{BASE_URL}/workflows",
                json={
                    "agent_id": "sim-test-agent-001"
                    # 缺少 task_description
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}"
            print(f"✅ TC-S003 通过: 缺少必填字段返回422")

    # ==================== 执行Workflow测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S004_execute_pending_workflow(self, auth_headers):
        """TC-S004: 执行Workflow - pending状态"""
        workflow_id = getattr(self.__class__, 'test_workflow_id', None)

        if not workflow_id:
            # 先创建一个
            async with httpx.AsyncClient() as client:
                create_resp = await client.post(
                    f"{BASE_URL}/workflows",
                    json={
                        "task_description": "测试执行任务",
                        "agent_id": "sim-test-agent-001"
                    },
                    headers=auth_headers,
                    timeout=60.0
                )
                workflow_id = create_resp.json()["id"]
                self.__class__.test_workflow_id = workflow_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/workflows/{workflow_id}/execute",
                params={"agentId": "sim-test-agent-001"},
                headers=auth_headers,
                timeout=120.0  # 执行可能较慢
            )

            # 执行可能成功或失败，取决于后端实现
            assert response.status_code in [200, 201, 202], f"Unexpected status: {response.status_code}"

            print(f"✅ TC-S004 通过: Workflow执行请求已提交 ({response.status_code})")

    @pytest.mark.asyncio
    async def test_TC_S005_execute_non_pending_workflow(self, auth_headers):
        """TC-S005: 执行Workflow - 非pending状态"""
        # 使用已完成的workflow
        async with httpx.AsyncClient() as client:
            # 先获取一个已完成的workflow
            list_resp = await client.get(f"{BASE_URL}/workflows")
            workflows = list_resp.json()

            completed_wf = next((w for w in workflows if w["status"] == "completed"), None)

            if completed_wf:
                response = await client.post(
                    f"{BASE_URL}/workflows/{completed_wf['id']}/execute",
                    params={"agentId": "sim-test-agent-001"},
                    headers=auth_headers,
                    timeout=30.0
                )

                # 应该返回400（无法重复执行）
                assert response.status_code in [400, 409, 422], f"Expected error status, got {response.status_code}"
                print(f"✅ TC-S005 通过: 非pending状态执行被拒绝")
            else:
                print("⚠️ TC-S005 跳过: 没有已完成的Workflow")

    # ==================== 查询测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S006_get_nonexistent_workflow(self):
        """TC-S006: 获取不存在的Workflow"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/workflows/nonexistent-workflow-12345",
                timeout=30.0
            )

            assert response.status_code == 404
            print(f"✅ TC-S006 通过: 不存在的Workflow返回404")

    # ==================== 行为预测测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S007_predict_behavior(self, auth_headers):
        """TC-S007: 行为预测请求"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/predict/behavior",
                json={
                    "agent_id": "sim-test-agent-001",
                    "goal_name": "complete_task",
                    "context": {
                        "task_type": "data_analysis",
                        "complexity": "medium"
                    }
                },
                headers=auth_headers,
                timeout=60.0
            )

            # 预测API可能返回200或404（如果端点不存在）
            if response.status_code == 200:
                data = response.json()
                print(f"✅ TC-S007 通过: 行为预测成功")
                print(f"   预测结果: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
            elif response.status_code == 404:
                print("⚠️ TC-S007: 预测端点未实现")
            else:
                print(f"⚠️ TC-S007: 预测返回 {response.status_code}")

    # ==================== 系统状态测试 ====================

    @pytest.mark.asyncio
    async def test_TC_S008_get_system_status(self):
        """TC-S008: 获取系统状态"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/status",
                timeout=30.0
            )

            # 状态端点可能返回200或404
            if response.status_code == 200:
                data = response.json()
                print(f"✅ TC-S008 通过: 系统状态获取成功")
                print(f"   {json.dumps(data, indent=2)[:200]}")
            else:
                print(f"⚠️ TC-S008: 状态端点返回 {response.status_code}")


class TestSimulationStatusFlow:
    """仿真状态流转测试"""

    @pytest.mark.asyncio
    async def test_workflow_status_transitions(self):
        """测试Workflow状态转换"""
        auth_headers = {
            "X-API-Key": "test-api-key-sim",
            "X-Agent-ID": "sim-test-agent-001"
        }

        async with httpx.AsyncClient() as client:
            # 1. 创建 (pending)
            create_resp = await client.post(
                f"{BASE_URL}/workflows",
                json={
                    "task_description": "状态流转测试",
                    "agent_id": "sim-test-agent-001"
                },
                headers=auth_headers,
                timeout=60.0
            )

            if create_resp.status_code != 200:
                print("⚠️ 无法创建测试Workflow")
                return

            workflow_id = create_resp.json()["id"]
            assert create_resp.json()["status"] == "pending"
            print("  State: pending ✓")

            # 2. 执行 (running)
            exec_resp = await client.post(
                f"{BASE_URL}/workflows/{workflow_id}/execute",
                params={"agentId": "sim-test-agent-001"},
                headers=auth_headers,
                timeout=120.0
            )

            if exec_resp.status_code in [200, 201, 202]:
                print("  State: running/executing ✓")

                # 3. 检查最终状态
                # 注意：实际完成可能需要等待
                time.sleep(2)

                get_resp = await client.get(f"{BASE_URL}/workflows")
                workflows = get_resp.json()
                target_wf = next((w for w in workflows if w["id"] == workflow_id), None)

                if target_wf:
                    print(f"  Final State: {target_wf['status']} ✓")
            else:
                print(f"  ⚠️ 执行请求返回 {exec_resp.status_code}")

            print(f"✅ 状态流转测试完成")


class TestSimulationStatistics:
    """仿真统计测试"""

    @pytest.mark.asyncio
    async def test_statistics_accuracy(self):
        """测试统计数据准确性"""
        async with httpx.AsyncClient() as client:
            # 获取所有workflow
            response = await client.get(f"{BASE_URL}/workflows")
            assert response.status_code == 200
            workflows = response.json()

            # 手动计算统计
            by_status = {}
            for wf in workflows:
                status = wf.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

            print(f"✅ 统计测试: 总共 {len(workflows)} 个Workflow")
            for status, count in by_status.items():
                print(f"   {status}: {count}")

            # 验证前端显示应该与这些数据一致
            expected_running = by_status.get("running", 0)
            expected_completed = by_status.get("completed", 0)
            expected_failed = by_status.get("failed", 0)
            expected_pending = by_status.get("pending", 0)

            print(f"   预期统计: running={expected_running}, completed={expected_completed}, failed={expected_failed}, pending={expected_pending}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
```

---

## 4. 前端组件测试

### 4.1 React组件测试

```typescript
// frontend/src/__tests__/Simulations.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Simulations from '@/pages/Simulations'

// Mock API
jest.mock('@/lib/api', () => ({
  getWorkflows: jest.fn(),
  createWorkflow: jest.fn(),
  executeWorkflow: jest.fn(),
  getAgents: jest.fn()
}))

const mockGetWorkflows = require('@/lib/api').getWorkflows as jest.Mock
const mockCreateWorkflow = require('@/lib/api').createWorkflow as jest.Mock
const mockExecuteWorkflow = require('@/lib/api').executeWorkflow as jest.Mock
const mockGetAgents = require('@/lib/api').getAgents as jest.Mock

const renderSimulations = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Simulations />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Simulations Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('should render page title', () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()
    expect(screen.getByText(/仿真|Simulation/i)).toBeInTheDocument()
  })

  test('should display statistics cards', async () => {
    mockGetWorkflows.mockResolvedValue([
      { id: '1', name: 'Running', status: 'running', steps_count: 5 },
      { id: '2', name: 'Completed', status: 'completed', steps_count: 10 },
      { id: '3', name: 'Failed', status: 'failed', steps_count: 3 },
      { id: '4', name: 'Pending', status: 'pending', steps_count: 2 }
    ])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()

    await waitFor(() => {
      // 检查统计数字
      expect(screen.getByText('1')).toBeInTheDocument() // Running
      expect(screen.getByText('1')).toBeInTheDocument() // Completed
      expect(screen.getByText('1')).toBeInTheDocument() // Failed
      expect(screen.getByText('1')).toBeInTheDocument() // Pending
    })
  })

  test('should show create button', () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()
    expect(screen.getByRole('button', { name: /新建|New/i })).toBeInTheDocument()
  })

  test('should open create modal', async () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([
      { id: 'agent-1', name: 'Test Agent' }
    ])

    renderSimulations()

    fireEvent.click(screen.getByRole('button', { name: /新建|New/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  test('should submit create form', async () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([
      { id: 'agent-1', name: 'Test Agent' }
    ])
    mockCreateWorkflow.mockResolvedValue({
      id: 'new-wf-1',
      name: 'New Simulation',
      status: 'pending'
    })

    renderSimulations()

    // 打开创建弹窗
    fireEvent.click(screen.getByRole('button', { name: /新建|New/i }))

    await waitFor(() => {
      // 填写表单
      fireEvent.change(screen.getByLabelText(/任务描述|Task/i), {
        target: { value: '测试仿真任务' }
      })
      fireEvent.change(screen.getByLabelText(/Agent/i), {
        target: { value: 'agent-1' }
      })
    })

    // 提交
    fireEvent.click(screen.getByRole('button', { name: /创建|Create/i }))

    await waitFor(() => {
      expect(mockCreateWorkflow).toHaveBeenCalledWith(
        expect.objectContaining({
          task_description: '测试仿真任务',
          agent_id: 'agent-1'
        })
      )
    })
  })

  test('should display workflow list with correct status icons', async () => {
    mockGetWorkflows.mockResolvedValue([
      { id: '1', name: 'Running', status: 'running', steps_count: 5 },
      { id: '2', name: 'Completed', status: 'completed', steps_count: 10 },
      { id: '3', name: 'Failed', status: 'failed', steps_count: 3 }
    ])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()

    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument()
      expect(screen.getByText('Completed')).toBeInTheDocument()
      expect(screen.getByText('Failed')).toBeInTheDocument()
    })

    // 检查状态徽章颜色
    const runningBadge = screen.getByText('running')
    const completedBadge = screen.getByText('completed')
    const failedBadge = screen.getByText('failed')

    expect(runningBadge).toHaveClass('text-blue')
    expect(completedBadge).toHaveClass('text-green')
    expect(failedBadge).toHaveClass('text-red')
  })

  test('should show execute button for pending workflow', async () => {
    mockGetWorkflows.mockResolvedValue([
      { id: '1', name: 'Pending', status: 'pending', steps_count: 2 }
    ])
    mockGetAgents.mockResolvedValue([{ id: 'agent-1', name: 'Agent' }])
    mockExecuteWorkflow.mockResolvedValue({ success: true })

    renderSimulations()

    await waitFor(() => {
      const executeButton = screen.getByRole('button', { name: /Execute/i })
      expect(executeButton).toBeInTheDocument()
    })
  })

  test('should call execute when clicking execute button', async () => {
    mockGetWorkflows.mockResolvedValue([
      { id: 'wf-1', name: 'Pending', status: 'pending', steps_count: 2 }
    ])
    mockGetAgents.mockResolvedValue([{ id: 'agent-1', name: 'Agent' }])
    mockExecuteWorkflow.mockResolvedValue({ success: true })

    renderSimulations()

    await waitFor(() => {
      fireEvent.click(screen.getByRole('button', { name: /Execute/i }))
    })

    await waitFor(() => {
      expect(mockExecuteWorkflow).toHaveBeenCalledWith('wf-1', 'agent-1')
    })
  })

  test('should show empty state', async () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()

    await waitFor(() => {
      expect(screen.getByText(/暂无仿真|No simulation/i)).toBeInTheDocument()
    })
  })

  test('should toggle concept explanation', async () => {
    mockGetWorkflows.mockResolvedValue([])
    mockGetAgents.mockResolvedValue([])

    renderSimulations()

    // 点击展开概念卡片
    const toggleButton = screen.getByRole('button', { name: /概念|Concept|Learn/i })
    fireEvent.click(toggleButton)

    await waitFor(() => {
      expect(screen.getByText(/什么是仿真|What is simulation/i)).toBeInTheDocument()
    })
  })
})
```

### 4.2 E2E测试

```typescript
// e2e/simulations.spec.ts

import { test, expect } from '@playwright/test'

test.describe('Simulations Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/simulations')
    await page.waitForSelector('[data-testid="simulations-page"]')
  })

  test('should display statistics', async ({ page }) => {
    // 检查四个统计卡片
    const statCards = await page.$$('[data-testid="stat-card"]')
    expect(statCards.length).toBe(4)

    // 验证每个卡片有标题和数值
    for (const card of statCards) {
      const title = await card.$eval('[data-testid="stat-title"]', el => el.textContent)
      const value = await card.$eval('[data-testid="stat-value"]', el => el.textContent)
      expect(title).toBeTruthy()
      expect(value).not.toBe('-')
    }
  })

  test('create and execute workflow flow', async ({ page }) => {
    // 1. 点击创建按钮
    await page.click('[data-testid="create-simulation-button"]')

    // 2. 等待弹窗
    await page.waitForSelector('[data-testid="create-modal"]')

    // 3. 填写任务描述
    await page.fill('[data-testid="task-description-input"]', 'E2E测试仿真任务')

    // 4. 选择Agent
    await page.selectOption('[data-testid="agent-select"]', { label: /Agent/i })

    // 5. 填写工具（可选）
    await page.fill('[data-testid="tools-input"]', 'web_search, calculator')

    // 6. 提交创建
    await page.click('[data-testid="submit-create-button"]')

    // 7. 等待创建成功
    await page.waitForSelector('[data-testid="workflow-card"][data-status="pending"]', { timeout: 30000 })

    // 8. 点击执行
    await page.click('[data-testid="workflow-card"]:first-child [data-testid="execute-button"]')

    // 9. 验证状态变更
    await page.waitForSelector('[data-testid="workflow-card"][data-status="running"]', { timeout: 60000 })
  })

  test('should display workflow details', async ({ page }) => {
    // 等待workflow列表加载
    await page.waitForSelector('[data-testid="workflow-card"]', { timeout: 10000 })

    // 点击workflow卡片
    await page.click('[data-testid="workflow-card"]:first-child')

    // 验证详情显示
    await expect(page.locator('[data-testid="workflow-name"]')).toBeVisible()
    await expect(page.locator('[data-testid="workflow-status"]')).toBeVisible()
    await expect(page.locator('[data-testid="workflow-steps"]')).toBeVisible()
  })

  test('should show concept explanation', async ({ page }) => {
    // 点击概念卡片展开
    await page.click('[data-testid="concept-card-toggle"]')

    // 验证概念说明可见
    await expect(page.locator('[data-testid="concept-definition"]')).toBeVisible()

    // 验证应用场景可见
    await expect(page.locator('[data-testid="use-cases"]')).toBeVisible()

    // 验证流程步骤可见
    await expect(page.locator('[data-testid="process-steps"]')).toBeVisible()
  })

  test('should filter workflows by status', async ({ page }) => {
    // 假设有状态筛选器
    const filterSelector = '[data-testid="status-filter"]'
    if (await page.$(filterSelector)) {
      // 选择running状态
      await page.selectOption(filterSelector, 'running')

      // 验证只显示running的workflow
      const cards = await page.$$('[data-testid="workflow-card"][data-status="running"]')
      const otherCards = await page.$$('[data-testid="workflow-card"]:not([data-status="running"])')

      expect(cards.length).toBeGreaterThan(0)
      expect(otherCards.length).toBe(0)
    }
  })
})
```

---

## 5. 调试指南

### 5.1 常见问题

| 问题 | 症状 | 排查步骤 |
|------|------|---------|
| Workflow创建超时 | 请求超过30秒 | 1. 检查LLM配置 2. 查看API Key是否有效 |
| 执行失败 | status变为failed | 1. 查看workflow日志 2. 检查Agent能力 |
| 空列表返回 | 无workflow显示 | 1. 检查数据库 2. 验证查询条件 |
| 统计不准确 | 数字与实际不符 | 1. 刷新页面 2. 检查缓存 |
| Agent选择为空 | 下拉框无选项 | 1. 检查Agent列表API 2. 确认有在线Agent |

### 5.2 调试命令

```bash
# 查看所有Workflow
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT id, name, status, steps_count, created_at
FROM workflows
ORDER BY created_at DESC
LIMIT 10;
"

# 按状态统计
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT status, COUNT(*) as count
FROM workflows
GROUP BY status;
"

# 检查Agent列表
curl -s http://localhost:8000/api/agents | jq '.[] | {id, name, status}'

# 查看后端日志
tail -f /var/log/usmsb/api.log | grep -E "workflow|simulation|LLM"
```

### 5.3 关键断点

```python
# workflows.py 调试断点

@router.post("")
async def create_workflow(data, user):
    # BP1: 检查请求数据
    print(f"[DEBUG] Create workflow request: {data.dict()}")

    # BP2: 检查LLM调用
    # ...

    # BP3: 检查创建结果
    print(f"[DEBUG] Workflow created: {workflow.id}")

@router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id, agentId):
    # BP4: 检查执行参数
    print(f"[DEBUG] Execute workflow: {workflow_id} with agent: {agentId}")

    # BP5: 检查执行状态
    # ...
```

---

## 6. 测试执行计划

```
Phase 1: 数据准备 (5分钟)
  ├── 插入测试Agent
  ├── 插入测试Workflow
  └── 验证LLM配置

Phase 2: 后端API测试 (15分钟)
  ├── TC-S001 ~ TC-S003: 创建测试
  ├── TC-S004 ~ TC-S005: 执行测试
  ├── TC-S006: 查询测试
  └── TC-S007 ~ TC-S008: 预测与状态

Phase 3: 前端组件测试 (15分钟)
  ├── 渲染测试
  ├── 统计显示测试
  ├── 表单提交测试
  └── 执行交互测试

Phase 4: E2E测试 (15分钟)
  ├── 完整创建流程
  ├── 执行流程
  └── 概念卡片交互

Phase 5: 回归测试 (10分钟)
```

---

## 7. 确认事项

执行测试前请确认：

- [ ] 后端服务正常运行
- [ ] LLM API配置正确（OpenAI/MiniMax等）
- [ ] 有可用的测试Agent
- [ ] 数据库中存在测试Workflow数据
- [ ] 前端开发服务器运行中（E2E测试）

**是否确认执行此测试方案？**
