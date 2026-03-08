# 智能匹配模块测试与调试方案

> 模块: ActiveMatching (智能匹配)
> 文件位置: `frontend/src/pages/ActiveMatching.tsx`
> 后端路由: `api/rest/routers/matching.py`
> 生成时间: 2026-03-08

---

## 1. 测试目标

验证智能匹配模块的以下核心功能：
- 供需搜索与匹配评分计算
- 协商流程（发起、提案、接受/拒绝）
- 认证与质押验证
- 前后端数据交互

---

## 2. 测试环境准备

### 2.1 环境检查清单

```bash
# 1. 检查后端服务状态
curl http://localhost:8000/api/health

# 2. 检查数据库
sqlite3 usmsb-sdk/data/meta_agent.db "SELECT COUNT(*) FROM ai_agents;"

# 3. 检查是否有测试Agent
sqlite3 usmsb-sdk/data/meta_agent.db "SELECT agent_id, name, status FROM ai_agents LIMIT 5;"

# 4. 检查是否有测试需求
sqlite3 usmsb-sdk/data/meta_agent.db "SELECT id, title, status FROM demands LIMIT 5;"
```

### 2.2 测试数据准备

```sql
-- 创建测试Agent (如果不存在)
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  ('test-supplier-001', 'TestDataAnalyst', '["data_analysis", "python", "pandas"]', '["ml", "visualization"]', 'online', 0.85, 500),
  ('test-demand-001', 'TestProjectOwner', '["project_management"]', '[]', 'online', 0.75, 200);

-- 创建测试需求
INSERT OR REPLACE INTO demands (id, agent_id, title, description, required_skills, budget_min, budget_max, status)
VALUES
  ('demand-test-001', 'test-demand-001', '数据分析项目', '需要数据清洗和可视化', '["python", "pandas", "visualization"]', 200, 500, 'active');

-- 创建测试服务
INSERT OR REPLACE INTO services (id, agent_id, name, description, skills, price, status)
VALUES
  ('service-test-001', 'test-supplier-001', '数据分析服务', '提供专业数据分析', '["data_analysis", "python", "ml"]', 100, 'active');
```

### 2.3 测试API Key生成

```bash
# 通过API注册获取测试Agent的API Key
curl -X POST http://localhost:8000/api/agents/v2/register \
  -H "Content-Type: application/json" \
  -d '{"name": "TestAgent-Matching", "description": "Test agent for matching", "capabilities": ["test"]}'
```

---

## 3. 后端API测试

### 3.1 测试用例列表

| 用例ID | 测试场景 | 端点 | 方法 | 预期结果 |
|--------|---------|------|------|---------|
| TC-M001 | 搜索需求 - 有匹配结果 | `/api/matching/search-demands` | POST | 200, 返回匹配列表 |
| TC-M002 | 搜索需求 - 无匹配结果 | `/api/matching/search-demands` | POST | 200, 空列表 |
| TC-M003 | 搜索供给 - 有匹配结果 | `/api/matching/search-suppliers` | POST | 200, 返回匹配列表 |
| TC-M004 | 发起协商 | `/api/matching/negotiate` | POST | 200, 返回session_id |
| TC-M005 | 获取协商列表 | `/api/matching/negotiations` | GET | 200, 返回列表 |
| TC-M006 | 提交提案 | `/api/matching/negotiations/{id}/proposal` | POST | 200, 更新协商状态 |
| TC-M007 | 接受协商 - 无质押 | `/api/matching/negotiations/{id}/accept` | POST | 403, 质押不足 |
| TC-M008 | 接受协商 - 有质押 | `/api/matching/negotiations/{id}/accept` | POST | 200, 协商成功 |
| TC-M009 | 拒绝协商 | `/api/matching/negotiations/{id}/reject` | POST | 200, 协商取消 |
| TC-M010 | 获取匹配统计 | `/api/matching/stats` | GET | 200, 返回统计数据 |

### 3.2 详细测试脚本

```python
# test_active_matching.py

import pytest
import httpx
import asyncio
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

class TestMatchingAPI:
    """智能匹配模块API测试"""

    @pytest.fixture
    def auth_headers(self):
        """测试用认证头"""
        # 需要先注册获取真实的API Key
        return {
            "X-API-Key": "test-api-key-xxx",  # 替换为实际Key
            "X-Agent-ID": "test-supplier-001"
        }

    @pytest.mark.asyncio
    async def test_TC_M001_search_demands_with_results(self, auth_headers):
        """TC-M001: 搜索需求 - 有匹配结果"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-demands",
                json={
                    "agent_id": "test-supplier-001",
                    "capabilities": ["data_analysis", "python"],
                    "budget_min": 100,
                    "budget_max": 1000
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.json()
            assert isinstance(data, list), "Response should be a list"

            if len(data) > 0:
                # 验证返回结构
                opportunity = data[0]
                assert "opportunity_id" in opportunity
                assert "match_score" in opportunity
                assert "details" in opportunity

                # 验证匹配分数结构
                score = opportunity["match_score"]
                assert "overall" in score
                assert "capability_match" in score
                assert 0 <= score["overall"] <= 1

                print(f"✅ TC-M001 通过: 找到 {len(data)} 个匹配需求")
                print(f"   最高匹配分: {max(d['match_score']['overall'] for d in data):.2f}")
            else:
                print("⚠️ TC-M001 警告: 未找到匹配需求，请检查测试数据")

    @pytest.mark.asyncio
    async def test_TC_M002_search_demands_no_results(self, auth_headers):
        """TC-M002: 搜索需求 - 无匹配结果（使用稀有能力）"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-demands",
                json={
                    "agent_id": "test-supplier-001",
                    "capabilities": ["quantum_computing", "brain_surgery"],  # 稀有能力
                    "budget_min": 1000000,
                    "budget_max": 10000000
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ TC-M002 通过: 稀有能力返回 {len(data)} 个结果（预期为0或很少）")

    @pytest.mark.asyncio
    async def test_TC_M003_search_suppliers(self, auth_headers):
        """TC-M003: 搜索供给"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-suppliers",
                json={
                    "agent_id": "test-demand-001",
                    "required_skills": ["python", "data_analysis"],
                    "budget_min": 50,
                    "budget_max": 500
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            print(f"✅ TC-M003 通过: 找到 {len(data)} 个供给方")

    @pytest.mark.asyncio
    async def test_TC_M004_initiate_negotiation(self, auth_headers):
        """TC-M004: 发起协商"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/negotiate",
                json={
                    "initiator_id": "test-supplier-001",
                    "counterpart_id": "test-demand-001",
                    "context": {
                        "task": "data_analysis",
                        "demand_id": "demand-test-001"
                    }
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert data["status"] == "pending"

            # 保存session_id供后续测试使用
            self.__class__.negotiation_session_id = data["session_id"]
            print(f"✅ TC-M004 通过: 协商会话创建成功")
            print(f"   Session ID: {data['session_id']}")

            return data["session_id"]

    @pytest.mark.asyncio
    async def test_TC_M005_get_negotiations(self, auth_headers):
        """TC-M005: 获取协商列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/matching/negotiations",
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            print(f"✅ TC-M005 通过: 获取到 {len(data)} 个协商会话")

    @pytest.mark.asyncio
    async def test_TC_M006_submit_proposal(self, auth_headers):
        """TC-M006: 提交提案"""
        # 先确保有协商会话
        session_id = getattr(self.__class__, 'negotiation_session_id', None)
        if not session_id:
            # 先创建一个
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{BASE_URL}/matching/negotiate",
                    json={
                        "initiator_id": "test-supplier-001",
                        "counterpart_id": "test-demand-001",
                        "context": {"task": "test"}
                    },
                    headers=auth_headers
                )
                session_id = resp.json()["session_id"]
                self.__class__.negotiation_session_id = session_id

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/negotiations/{session_id}/proposal",
                json={
                    "price": 300,
                    "delivery_time": "3 days",
                    "payment_terms": "50% upfront",
                    "quality_guarantee": "satisfaction guaranteed"
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "rounds" in data
            assert len(data["rounds"]) > 0
            print(f"✅ TC-M006 通过: 提案已提交")
            print(f"   当前轮次: {len(data['rounds'])}")

    @pytest.mark.asyncio
    async def test_TC_M010_get_stats(self, auth_headers):
        """TC-M010: 获取匹配统计"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/matching/stats",
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert "total_opportunities" in data
            assert "active_negotiations" in data
            print(f"✅ TC-M010 通过: 统计数据获取成功")
            print(f"   {json.dumps(data, indent=2)}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

### 3.3 认证测试

```python
# test_matching_auth.py

class TestMatchingAuth:
    """匹配模块认证测试"""

    @pytest.mark.asyncio
    async def test_no_auth_header(self):
        """测试无认证头"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-demands",
                json={"agent_id": "test", "capabilities": ["test"]}
            )
            assert response.status_code == 401, "Should reject without auth"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """测试无效API Key"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-demands",
                json={"agent_id": "test", "capabilities": ["test"]},
                headers={"X-API-Key": "invalid-key", "X-Agent-ID": "test"}
            )
            assert response.status_code == 401, "Should reject invalid key"

    @pytest.mark.asyncio
    async def test_agent_id_mismatch(self):
        """测试Agent ID不匹配"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/matching/search-demands",
                json={"agent_id": "different-agent", "capabilities": ["test"]},
                headers={"X-API-Key": "valid-key", "X-Agent-ID": "test-agent"}
            )
            assert response.status_code == 403, "Should reject ID mismatch"
```

---

## 4. 前端集成测试

### 4.1 组件测试

```typescript
// frontend/src/__tests__/ActiveMatching.test.tsx

import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import ActiveMatching from '@/pages/ActiveMatching'
import * as api from '@/lib/api'

// Mock API
jest.mock('@/lib/api')
jest.mock('@/stores/authStore', () => ({
  useAuthStore: () => ({
    agentId: 'test-agent-001',
    isAuthenticated: true
  })
}))

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('ActiveMatching Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('should render page title', () => {
    renderWithProviders(<ActiveMatching />)
    expect(screen.getByText(/智能匹配|Active Matching/i)).toBeInTheDocument()
  })

  test('should display four view tabs', () => {
    renderWithProviders(<ActiveMatching />)

    // 检查四个视图标签
    expect(screen.getByText(/发现|Discover/i)).toBeInTheDocument()
    expect(screen.getByText(/机会|Opportunities/i)).toBeInTheDocument()
    expect(screen.getByText(/协商|Negotiations/i)).toBeInTheDocument()
    expect(screen.getByText(/匹配|Matches/i)).toBeInTheDocument()
  })

  test('should switch between view modes', () => {
    renderWithProviders(<ActiveMatching />)

    // 点击协商标签
    const negotiationsTab = screen.getByText(/协商|Negotiations/i)
    fireEvent.click(negotiationsTab)

    // 验证视图切换
    expect(screen.getByText(/协商会话|Negotiation Session/i)).toBeInTheDocument()
  })

  test('should search demands when clicking search button', async () => {
    const mockSearchDemands = jest.fn().mockResolvedValue([
      {
        opportunity_id: 'opp-001',
        counterpart_agent_id: 'agent-002',
        counterpart_name: 'Test Agent',
        match_score: { overall: 0.85, capability_match: 0.9 },
        status: 'discovered'
      }
    ])
    ;(api.searchDemands as jest.Mock) = mockSearchDemands

    renderWithProviders(<ActiveMatching />)

    // 填写搜索表单
    const capabilityInput = screen.getByPlaceholderText(/能力|capability/i)
    fireEvent.change(capabilityInput, { target: { value: 'python, data_analysis' } })

    // 点击搜索按钮
    const searchButton = screen.getByRole('button', { name: /搜索|Search/i })
    fireEvent.click(searchButton)

    await waitFor(() => {
      expect(mockSearchDemands).toHaveBeenCalled()
    })
  })

  test('should display match score with correct colors', async () => {
    const mockData = [
      {
        opportunity_id: 'opp-001',
        match_score: { overall: 0.92 },
        status: 'discovered'
      }
    ]
    ;(api.searchDemands as jest.Mock).mockResolvedValue(mockData)

    renderWithProviders(<ActiveMatching />)

    await waitFor(() => {
      // 检查高分匹配是否显示为绿色
      const scoreElement = screen.getByText('92%')
      expect(scoreElement).toHaveClass('text-green')
    })
  })

  test('should show loading state while fetching', async () => {
    // Mock 慢速响应
    ;(api.searchDemands as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 1000))
    )

    renderWithProviders(<ActiveMatching />)

    // 点击搜索后应显示加载状态
    const searchButton = screen.getByRole('button', { name: /搜索|Search/i })
    fireEvent.click(searchButton)

    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })
})
```

### 4.2 E2E 测试场景

```typescript
// e2e/matching.spec.ts (Playwright)

import { test, expect } from '@playwright/test'

test.describe('Active Matching Module', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('/app/matching')
    // 等待认证完成
    await page.waitForSelector('[data-testid="matching-page"]')
  })

  test('complete matching flow', async ({ page }) => {
    // 1. 切换到发现视图
    await page.click('[data-testid="tab-discover"]')

    // 2. 输入搜索条件
    await page.fill('[data-testid="capability-input"]', 'python')
    await page.fill('[data-testid="budget-min"]', '100')
    await page.fill('[data-testid="budget-max"]', '500')

    // 3. 执行搜索
    await page.click('[data-testid="search-button"]')

    // 4. 等待结果
    await page.waitForSelector('[data-testid="opportunity-card"]', { timeout: 10000 })

    // 5. 验证结果
    const cards = await page.$$('[data-testid="opportunity-card"]')
    expect(cards.length).toBeGreaterThan(0)

    // 6. 点击第一个机会
    await cards[0].click()

    // 7. 发起协商
    await page.click('[data-testid="initiate-negotiation-button"]')

    // 8. 验证协商视图
    await expect(page.locator('[data-testid="negotiation-form"]')).toBeVisible()
  })

  test('negotiation proposal flow', async ({ page }) => {
    // 假设已有一个协商会话
    await page.click('[data-testid="tab-negotiations"]')

    // 选择一个协商
    await page.click('[data-testid="negotiation-item"]:first-child')

    // 提交提案
    await page.fill('[data-testid="proposal-price"]', '350')
    await page.fill('[data-testid="proposal-delivery"]', '2 days')
    await page.click('[data-testid="submit-proposal-button"]')

    // 验证提案已提交
    await expect(page.locator('[data-testid="proposal-success"]')).toBeVisible()
  })
})
```

---

## 5. 调试指南

### 5.1 常见问题排查

| 问题 | 可能原因 | 排查步骤 |
|------|---------|---------|
| 401 Unauthorized | API Key无效/过期 | 1. 检查Header格式 2. 重新注册获取Key |
| 403 Forbidden | 质押不足或ID不匹配 | 1. 检查质押金额 2. 确认agent_id一致 |
| 500 Internal Error | 后端异常 | 1. 查看后端日志 2. 检查数据库连接 |
| 空结果返回 | 无匹配数据 | 1. 检查测试数据 2. 放宽搜索条件 |
| 匹配分数异常 | 评分算法问题 | 1. 检查capabilities格式 2. 查看匹配引擎日志 |

### 5.2 调试命令

```bash
# 后端日志监控
tail -f /var/log/usmsb/api.log | grep -E "(matching|ERROR)"

# 数据库查询调试
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT
  d.id, d.title, d.required_skills,
  a.agent_id, a.capabilities, a.reputation
FROM demands d
CROSS JOIN ai_agents a
WHERE a.status = 'online'
LIMIT 5;
"

# 查看匹配引擎输出
PYTHONPATH=. python -c "
from usmsb_sdk.services.matching_engine import MatchingEngine

engine = MatchingEngine()
# 测试匹配算法
supply = {'id': 'test', 'capabilities': ['python', 'data_analysis']}
demand = {'required_skills': ['python'], 'budget_range': {'min': 0, 'max': 1000}}

import asyncio
result = asyncio.run(engine.match_supply_to_demands(supply, [demand]))
print(result)
"
```

### 5.3 断点调试位置

```python
# matching.py 关键断点位置

@router.post("/search-demands")
async def search_demands(request, user):
    # 断点1: 检查请求参数
    import pdb; pdb.set_trace()  # BP1

    # 断点2: 检查Agent数据
    agent_data = db_get_agent(request.agent_id)
    import pdb; pdb.set_trace()  # BP2

    # 断点3: 检查匹配结果
    matches = await _matching_engine.match_supply_to_demands(...)
    import pdb; pdb.set_trace()  # BP3
```

---

## 6. 测试执行计划

### 6.1 执行顺序

```
Phase 1: 环境准备 (预计 10分钟)
  ├── 启动后端服务
  ├── 准备测试数据
  └── 生成测试API Key

Phase 2: 后端单元测试 (预计 15分钟)
  ├── TC-M001 ~ TC-M003: 搜索功能
  ├── TC-M004 ~ TC-M006: 协商功能
  └── TC-M007 ~ TC-M010: 认证与统计

Phase 3: 前端组件测试 (预计 20分钟)
  ├── 组件渲染测试
  ├── 交互测试
  └── API集成测试

Phase 4: E2E测试 (预计 15分钟)
  ├── 完整匹配流程
  └── 协商流程

Phase 5: 问题修复与回归 (预计 30分钟)
  ├── 修复发现的问题
  └── 回归测试
```

### 6.2 成功标准

| 指标 | 目标 |
|------|------|
| 后端测试通过率 | >= 90% |
| 前端测试通过率 | >= 85% |
| E2E测试通过率 | 100% |
| API响应时间 | < 500ms (P95) |
| 无阻塞Bug | 0 |

---

## 7. 测试报告模板

```markdown
# 智能匹配模块测试报告

## 测试概况
- 测试日期: YYYY-MM-DD
- 测试人员:
- 测试环境:

## 测试结果汇总
| 类别 | 用例数 | 通过 | 失败 | 通过率 |
|------|--------|------|------|--------|
| 后端API | 10 | ? | ? | ?% |
| 前端组件 | 5 | ? | ? | ?% |
| E2E | 2 | ? | ? | ?% |

## 详细结果
### TC-M001: 搜索需求 - 有匹配结果
- 状态: ✅ PASS / ❌ FAIL
- 实际结果:
- 备注:

## 问题列表
| ID | 描述 | 严重程度 | 状态 |
|----|------|---------|------|
| BUG-001 | xxx | High | Open |

## 建议
1. ...
2. ...
```

---

## 确认事项

执行测试前请确认：

- [ ] 后端服务正常运行 (http://localhost:8000/api/health 返回 200)
- [ ] 数据库中有测试数据
- [ ] 已生成测试用的API Key
- [ ] 前端开发服务器正常运行 (如需E2E测试)
- [ ] 已安装测试依赖 (pytest, pytest-asyncio, playwright等)

**是否确认执行此测试方案？**
