# 协作管理模块测试与调试方案

> 模块: Collaborations (协作管理)
> 文件位置: `frontend/src/pages/Collaborations.tsx`
> 后端路由: `api/rest/routers/collaborations.py`
> 生成时间: 2026-03-08

---

## 1. 测试目标

验证协作管理模块的以下核心功能：
- 协作会话创建（需质押）
- Agent加入协作
- 贡献提交
- 协作执行与完成
- 协作状态流转
- 角色分配与管理

---

## 2. 测试环境准备

### 2.1 环境检查

```bash
# 1. 检查后端服务
curl -s http://localhost:8000/api/health | jq

# 2. 检查协作数据表
sqlite3 usmsb-sdk/data/meta_agent.db ".schema collaborations"

# 3. 检查现有协作
sqlite3 usmsb-sdk/data/meta_agent.db "SELECT session_id, status, coordinator_id FROM collaborations LIMIT 5;"

# 4. 检查Agent质押情况（创建协作需要 >= 100 VIBE）
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT agent_id, name, stake FROM ai_agents WHERE stake >= 100 ORDER BY stake DESC;
"
```

### 2.2 测试数据准备

```sql
-- 创建高质押测试Agent（可以创建协作）
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('collab-coordinator-001', 'ProjectCoordinator', '["project_management", "coordination"]', '["planning", "communication"]', 'online', 0.90, 500),
  ('collab-primary-001', 'BackendDeveloper', '["backend_development", "api_design"]', '["python", "fastapi", "postgresql"]', 'online', 0.85, 300),
  ('collab-specialist-001', 'FrontendDeveloper', '["frontend_development", "ui_design"]', '["react", "typescript", "css"]', 'online', 0.82, 250),
  ('collab-support-001', 'QAEngineer', '["testing", "quality_assurance"]', '["pytest", "selenium", "jest"]', 'online', 0.78, 200),
  ('collab-validator-001', 'CodeReviewer', '["code_review", "documentation"]', '["best_practices", "security"]', 'online', 0.88, 350);

-- 低质押Agent（不能创建协作，但可以加入）
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('collab-lowstake-001', 'JuniorDeveloper', '["basic_coding"]', '["python"]', 'online', 0.55, 50);

-- 清理旧测试协作
DELETE FROM collaborations WHERE session_id LIKE 'test-collab-%';
```

---

## 3. 后端API测试

### 3.1 测试用例列表

| 用例ID | 测试场景 | 端点 | 方法 | 质押 | 预期结果 |
|--------|---------|------|------|------|---------|
| TC-C001 | 创建协作 - 有质押 | `/api/collaborations` | POST | 100+ | 200, 返回session_id |
| TC-C002 | 创建协作 - 无质押 | `/api/collaborations` | POST | <100 | 403, 质押不足 |
| TC-C003 | 获取协作列表 | `/api/collaborations` | GET | - | 200, 返回列表 |
| TC-C004 | 获取单个协作 | `/api/collaborations/{id}` | GET | - | 200, 返回详情 |
| TC-C005 | 获取不存在的协作 | `/api/collaborations/{id}` | GET | - | 404, 未找到 |
| TC-C006 | 加入协作 | `/api/collaborations/{id}/join` | POST | - | 200, 加入成功 |
| TC-C007 | 重复加入协作 | `/api/collaborations/{id}/join` | POST | - | 400, 已加入 |
| TC-C008 | 提交贡献 - 有质押 | `/api/collaborations/{id}/contribute` | POST | 100+ | 200, 提交成功 |
| TC-C009 | 提交贡献 - 未加入 | `/api/collaborations/{id}/contribute` | POST | - | 400, 未加入 |
| TC-C010 | 执行协作 - 有质押 | `/api/collaborations/{id}/execute` | POST | 100+ | 200, 开始执行 |
| TC-C011 | 完成协作 | `/api/collaborations/{id}/complete` | POST | - | 200, 完成 |
| TC-C012 | 获取协作统计 | `/api/collaborations/stats` | GET | - | 200, 统计数据 |

### 3.2 详细测试脚本

```python
# test_collaborations.py

import pytest
import httpx
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

class TestCollaborationsAPI:
    """协作管理模块API测试"""

    @pytest.fixture
    def coordinator_headers(self):
        """高质押Agent认证头（可以创建协作）"""
        return {
            "X-API-Key": "test-api-key-coordinator",
            "X-Agent-ID": "collab-coordinator-001"
        }

    @pytest.fixture
    def low_stake_headers(self):
        """低质押Agent认证头（不能创建协作）"""
        return {
            "X-API-Key": "test-api-key-lowstake",
            "X-Agent-ID": "collab-lowstake-001"
        }

    @pytest.fixture
    def primary_headers(self):
        """主要执行者认证头"""
        return {
            "X-API-Key": "test-api-key-primary",
            "X-Agent-ID": "collab-primary-001"
        }

    # ==================== 创建协作测试 ====================

    @pytest.mark.asyncio
    async def test_TC_C001_create_collaboration_with_stake(self, coordinator_headers):
        """TC-C001: 创建协作 - 有质押"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations",
                json={
                    "goal_description": "开发一个REST API服务",
                    "required_skills": ["python", "api_design", "testing"],
                    "collaboration_mode": "hybrid",
                    "coordinator_agent_id": "collab-coordinator-001"
                },
                headers=coordinator_headers,
                timeout=30.0
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()

            # 验证返回结构
            assert "session_id" in data
            assert data["status"] == "analyzing"
            assert "goal" in data
            assert "plan" in data
            assert "participants" in data

            # 保存session_id供后续测试
            self.__class__.test_session_id = data["session_id"]
            self.__class__.goal_data = data["goal"]

            print(f"✅ TC-C001 通过: 协作创建成功")
            print(f"   Session ID: {data['session_id']}")
            print(f"   Goal: {data['goal']}")

            return data["session_id"]

    @pytest.mark.asyncio
    async def test_TC_C002_create_collaboration_no_stake(self, low_stake_headers):
        """TC-C002: 创建协作 - 无质押（应失败）"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations",
                json={
                    "goal_description": "测试协作创建",
                    "required_skills": ["test"],
                    "collaboration_mode": "parallel",
                    "coordinator_agent_id": "collab-lowstake-001"
                },
                headers=low_stake_headers,
                timeout=30.0
            )

            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            print(f"✅ TC-C002 通过: 低质押Agent被正确拒绝 ({response.status_code})")

    # ==================== 查询协作测试 ====================

    @pytest.mark.asyncio
    async def test_TC_C003_get_collaborations_list(self):
        """TC-C003: 获取协作列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/collaborations",
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            print(f"✅ TC-C003 通过: 获取到 {len(data)} 个协作")

            if len(data) > 0:
                first = data[0]
                print(f"   第一个协作状态: {first.get('status')}")

    @pytest.mark.asyncio
    async def test_TC_C004_get_collaboration_by_id(self):
        """TC-C004: 获取单个协作"""
        # 确保有测试协作
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            # 先获取列表
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{BASE_URL}/collaborations")
                sessions = resp.json()
                if sessions:
                    session_id = sessions[0]["session_id"]

        if session_id:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BASE_URL}/collaborations/{session_id}",
                    timeout=30.0
                )

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == session_id

                print(f"✅ TC-C004 通过: 获取协作详情成功")
                print(f"   Status: {data.get('status')}")
        else:
            print("⚠️ TC-C004 跳过: 无测试协作")

    @pytest.mark.asyncio
    async def test_TC_C005_get_nonexistent_collaboration(self):
        """TC-C005: 获取不存在的协作"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/collaborations/nonexistent-session-12345",
                timeout=30.0
            )

            assert response.status_code == 404
            print(f"✅ TC-C005 通过: 不存在的协作返回404")

    # ==================== 加入协作测试 ====================

    @pytest.mark.asyncio
    async def test_TC_C006_join_collaboration(self, primary_headers):
        """TC-C006: 加入协作"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/join",
                headers=primary_headers,
                timeout=30.0
            )

            # 可能已经加入过
            if response.status_code == 400:
                print(f"⚠️ TC-C006: Agent已加入过该协作")
            else:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "joined"

                print(f"✅ TC-C006 通过: 成功加入协作")

    @pytest.mark.asyncio
    async def test_TC_C007_join_collaboration_twice(self, primary_headers):
        """TC-C007: 重复加入协作"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        async with httpx.AsyncClient() as client:
            # 第一次加入
            await client.post(
                f"{BASE_URL}/collaborations/{session_id}/join",
                headers=primary_headers,
                timeout=30.0
            )

            # 第二次加入（应该失败）
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/join",
                headers=primary_headers,
                timeout=30.0
            )

            assert response.status_code == 400
            print(f"✅ TC-C007 通过: 重复加入被拒绝")

    # ==================== 贡献测试 ====================

    @pytest.mark.asyncio
    async def test_TC_C008_submit_contribution_with_stake(self, coordinator_headers):
        """TC-C008: 提交贡献 - 有质押"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        # 先加入协作
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BASE_URL}/collaborations/{session_id}/join",
                headers=coordinator_headers,
                timeout=30.0
            )

            # 提交贡献
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/contribute",
                json={
                    "type": "code",
                    "content": "实现了用户认证API",
                    "files": ["auth.py", "models.py"],
                    "status": "completed"
                },
                headers=coordinator_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "contributed"

            print(f"✅ TC-C008 通过: 贡献提交成功")

    @pytest.mark.asyncio
    async def test_TC_C009_contribute_without_joining(self, low_stake_headers):
        """TC-C009: 提交贡献 - 未加入"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/contribute",
                json={"type": "code", "content": "test"},
                headers=low_stake_headers,
                timeout=30.0
            )

            assert response.status_code == 400
            print(f"✅ TC-C009 通过: 未加入Agent提交被拒绝")

    # ==================== 执行与完成测试 ====================

    @pytest.mark.asyncio
    async def test_TC_C010_execute_collaboration(self, coordinator_headers):
        """TC-C010: 执行协作 - 有质押"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/execute",
                headers=coordinator_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "executing"

            print(f"✅ TC-C010 通过: 协作开始执行")

    @pytest.mark.asyncio
    async def test_TC_C011_complete_collaboration(self, coordinator_headers):
        """TC-C011: 完成协作"""
        session_id = getattr(self.__class__, 'test_session_id', None)
        if not session_id:
            pytest.skip("No test session available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/complete",
                headers=coordinator_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

            print(f"✅ TC-C011 通过: 协作完成")

    @pytest.mark.asyncio
    async def test_TC_C012_get_stats(self):
        """TC-C012: 获取协作统计"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/collaborations/stats",
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            # 验证统计字段
            required_fields = [
                "total_sessions",
                "active_sessions",
                "completed_sessions",
                "failed_sessions",
                "success_rate"
            ]

            for field in required_fields:
                assert field in data, f"Missing field: {field}"

            print(f"✅ TC-C012 通过: 统计数据获取成功")
            print(f"   总会话: {data['total_sessions']}")
            print(f"   成功率: {data['success_rate']:.2%}")


class TestCollaborationStateFlow:
    """协作状态流转测试"""

    @pytest.mark.asyncio
    async def test_full_state_flow(self):
        """测试完整的状态流转: analyzing -> executing -> completed"""
        coordinator_headers = {
            "X-API-Key": "test-api-key-coordinator",
            "X-Agent-ID": "collab-coordinator-001"
        }

        async with httpx.AsyncClient() as client:
            # 1. 创建协作 (status: analyzing)
            create_resp = await client.post(
                f"{BASE_URL}/collaborations",
                json={
                    "goal_description": "状态流转测试",
                    "required_skills": ["test"],
                    "collaboration_mode": "parallel",
                    "coordinator_agent_id": "collab-coordinator-001"
                },
                headers=coordinator_headers
            )
            assert create_resp.status_code == 200
            session_id = create_resp.json()["session_id"]

            # 验证初始状态
            get_resp = await client.get(f"{BASE_URL}/collaborations/{session_id}")
            assert get_resp.json()["status"] == "analyzing"
            print("  State: analyzing ✓")

            # 2. 执行协作 (status: executing)
            exec_resp = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/execute",
                headers=coordinator_headers
            )
            assert exec_resp.status_code == 200
            assert exec_resp.json()["status"] == "executing"
            print("  State: executing ✓")

            # 3. 完成协作 (status: completed)
            complete_resp = await client.post(
                f"{BASE_URL}/collaborations/{session_id}/complete",
                headers=coordinator_headers
            )
            assert complete_resp.status_code == 200
            assert complete_resp.json()["status"] == "completed"
            print("  State: completed ✓")

            print(f"✅ 状态流转测试通过")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
```

---

## 4. 前端组件测试

### 4.1 React组件测试

```typescript
// frontend/src/__tests__/Collaborations.test.tsx

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import Collaborations from '@/pages/Collaborations'

const mockAuthFetch = jest.fn()
jest.mock('@/lib/api', () => ({
  authFetch: () => mockAuthFetch()
}))

const renderCollaborations = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Collaborations />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Collaborations Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    Storage.prototype.getItem = jest.fn(() => 'test-agent-001')
  })

  test('should render page title', () => {
    renderCollaborations()
    expect(screen.getByText(/协作|Collaboration/i)).toBeInTheDocument()
  })

  test('should display statistics cards', () => {
    renderCollaborations()

    expect(screen.getByText(/活跃|Active/i)).toBeInTheDocument()
    expect(screen.getByText(/完成|Completed/i)).toBeInTheDocument()
    expect(screen.getByText(/失败|Failed/i)).toBeInTheDocument()
    expect(screen.getByText(/总会话|Total/i)).toBeInTheDocument()
  })

  test('should show create collaboration button', () => {
    renderCollaborations()
    expect(screen.getByRole('button', { name: /创建|Create/i })).toBeInTheDocument()
  })

  test('should open create modal when clicking create button', async () => {
    renderCollaborations()

    fireEvent.click(screen.getByRole('button', { name: /创建|Create/i }))

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument()
    })
  })

  test('should display collaboration list', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          session_id: 'collab-001',
          goal: { name: 'Test Goal', description: 'Test' },
          status: 'analyzing',
          participants: []
        }
      ]
    })

    renderCollaborations()

    await waitFor(() => {
      expect(screen.getByText('Test Goal')).toBeInTheDocument()
    })
  })

  test('should show correct status badge', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { session_id: '1', goal: { name: 'Active' }, status: 'executing', participants: [] },
        { session_id: '2', goal: { name: 'Done' }, status: 'completed', participants: [] },
        { session_id: '3', goal: { name: 'Failed' }, status: 'failed', participants: [] }
      ]
    })

    renderCollaborations()

    await waitFor(() => {
      const executingBadge = screen.getByText('executing')
      const completedBadge = screen.getByText('completed')
      const failedBadge = screen.getByText('failed')

      expect(executingBadge).toHaveClass('bg-blue')
      expect(completedBadge).toHaveClass('bg-green')
      expect(failedBadge).toHaveClass('bg-red')
    })
  })

  test('should show empty state when no collaborations', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => []
    })

    renderCollaborations()

    await waitFor(() => {
      expect(screen.getByText(/暂无协作|No collaboration/i)).toBeInTheDocument()
    })
  })

  test('should submit form with correct data', async () => {
    const mockCreate = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ session_id: 'new-123', status: 'analyzing' })
    })

    renderCollaborations()

    // 打开创建弹窗
    fireEvent.click(screen.getByRole('button', { name: /创建|Create/i }))

    // 填写表单
    await waitFor(() => {
      fireEvent.change(screen.getByLabelText(/目标|Goal/i), {
        target: { value: 'Test Project' }
      })
      fireEvent.change(screen.getByLabelText(/技能|Skill/i), {
        target: { value: 'python, testing' }
      })
    })

    // 提交
    fireEvent.click(screen.getByRole('button', { name: /提交|Submit/i }))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalled()
    })
  })
})
```

### 4.2 E2E测试

```typescript
// e2e/collaborations.spec.ts

import { test, expect } from '@playwright/test'

test.describe('Collaborations Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/collaborations')
    await page.waitForSelector('[data-testid="collaborations-page"]')
  })

  test('should display collaboration statistics', async ({ page }) => {
    // 检查四个统计卡片
    const statCards = await page.$$('[data-testid="stat-card"]')
    expect(statCards.length).toBe(4)
  })

  test('create and complete collaboration flow', async ({ page }) => {
    // 1. 点击创建按钮
    await page.click('[data-testid="create-collaboration-button"]')

    // 2. 等待弹窗
    await page.waitForSelector('[data-testid="create-modal"]')

    // 3. 填写表单
    await page.fill('[data-testid="goal-input"]', 'E2E测试协作项目')
    await page.fill('[data-testid="skills-input"]', 'testing, automation')
    await page.selectOption('[data-testid="mode-select"]', 'parallel')

    // 4. 提交
    await page.click('[data-testid="submit-button"]')

    // 5. 等待创建成功
    await page.waitForSelector('[data-testid="collaboration-card"][data-status="analyzing"]', { timeout: 10000 })

    // 6. 点击协作卡片
    await page.click('[data-testid="collaboration-card"]:first-child')

    // 7. 加入协作
    await page.click('[data-testid="join-button"]')

    // 8. 执行协作
    await page.click('[data-testid="execute-button"]')

    // 9. 验证状态变更
    await expect(page.locator('[data-testid="status-badge"]')).toHaveText('executing')

    // 10. 完成协作
    await page.click('[data-testid="complete-button"]')

    // 11. 验证完成状态
    await expect(page.locator('[data-testid="status-badge"]')).toHaveText('completed')
  })

  test('should show stake requirement error for low stake users', async ({ page }) => {
    // 模拟低质押用户
    await page.evaluate(() => {
      localStorage.setItem('stake', '50')
    })

    // 尝试创建协作
    await page.click('[data-testid="create-collaboration-button"]')
    await page.fill('[data-testid="goal-input"]', 'Test')
    await page.click('[data-testid="submit-button"]')

    // 应该显示质押不足错误
    await expect(page.locator('[data-testid="error-message"]')).toContainText(/质押|stake/i)
  })

  test('should allow joining existing collaboration', async ({ page }) => {
    // 假设有现存的协作
    await page.waitForSelector('[data-testid="collaboration-card"]', { timeout: 5000 })

    // 点击第一个协作
    await page.click('[data-testid="collaboration-card"]:first-child')

    // 点击加入按钮
    const joinButton = page.locator('[data-testid="join-button"]')
    if (await joinButton.isVisible()) {
      await joinButton.click()

      // 验证加入成功
      await expect(page.locator('[data-testid="join-success"]')).toBeVisible()
    }
  })
})
```

---

## 5. 调试指南

### 5.1 常见问题

| 问题 | 症状 | 排查步骤 |
|------|------|---------|
| 403 创建失败 | "Stake requirement not met" | 1. 检查Agent质押 2. 确认质押 >= 100 |
| 400 重复加入 | "Already joined" | 1. 检查participants列表 2. 清理测试数据 |
| 404 协作不存在 | "Collaboration not found" | 1. 验证session_id 2. 检查数据库 |
| 状态不更新 | 前端显示旧状态 | 1. 手动刷新 2. 检查缓存 |
| 贡献提交失败 | "Must join first" | 1. 确认已加入 2. 检查participants |

### 5.2 调试命令

```bash
# 查看协作数据
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT
  session_id,
  status,
  coordinator_id,
  json_extract(goal, '$.name') as goal_name,
  json_array_length(participants) as participant_count
FROM collaborations
ORDER BY created_at DESC
LIMIT 10;
"

# 查看协作参与者
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT
  session_id,
  participants
FROM collaborations
WHERE session_id = 'your-session-id';
"

# 检查Agent质押
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT agent_id, name, stake
FROM ai_agents
WHERE stake >= 100;
"

# 后端日志
tail -f /var/log/usmsb/api.log | grep -E "collaboration|stake"
```

### 5.3 关键断点

```python
# collaborations.py 调试断点

@router.post("")
async def create_collaboration_endpoint(request, user):
    # BP1: 检查质押验证
    agent_id = user.get('agent_id')
    print(f"[DEBUG] Create collaboration request from: {agent_id}")

    # BP2: 检查创建数据
    print(f"[DEBUG] Goal: {request.goal_description}")
    print(f"[DEBUG] Skills: {request.required_skills}")

    # BP3: 检查数据库写入
    db_create_collaboration(collab_data)
    print(f"[DEBUG] Collaboration created: {session_id}")

@router.post("/{session_id}/join")
async def join_collaboration(session_id, user):
    # BP4: 检查加入逻辑
    print(f"[DEBUG] Join request: {user.get('agent_id')} -> {session_id}")
```

---

## 6. 测试执行计划

```
Phase 1: 数据准备 (5分钟)
  ├── 插入高质押Agent
  ├── 插入低质押Agent
  └── 清理旧测试数据

Phase 2: 后端API测试 (15分钟)
  ├── TC-C001 ~ TC-C002: 创建测试
  ├── TC-C003 ~ TC-C005: 查询测试
  ├── TC-C006 ~ TC-C007: 加入测试
  ├── TC-C008 ~ TC-C009: 贡献测试
  └── TC-C010 ~ TC-C012: 执行/完成/统计

Phase 3: 前端组件测试 (15分钟)
  ├── 渲染测试
  ├── 交互测试
  └── 表单提交测试

Phase 4: E2E测试 (15分钟)
  ├── 完整创建流程
  └── 状态流转测试

Phase 5: 回归测试 (10分钟)
```

---

## 7. 确认事项

执行测试前请确认：

- [ ] 数据库中有高质押(>=100)的测试Agent
- [ ] 数据库中有低质押(<100)的测试Agent用于负面测试
- [ ] 后端服务正常运行
- [ ] 前端开发服务器运行中（E2E测试）
- [ ] 测试Agent有有效的API Key

**是否确认执行此测试方案？**
