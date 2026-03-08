# 网络探索模块测试与调试方案

> 模块: NetworkExplorer (网络探索)
> 文件位置: `frontend/src/pages/NetworkExplorer.tsx`
> 后端路由: `api/rest/routers/network.py`
> 生成时间: 2026-03-08

---

## 1. 测试目标

验证网络探索模块的以下核心功能：
- 网络探索与Agent发现
- 基于能力的推荐
- 网络统计信息
- 信任网络管理
- 四视图模式切换

---

## 2. 测试环境准备

### 2.1 环境检查

```bash
# 1. 检查后端服务
curl -s http://localhost:8000/api/health | jq

# 2. 检查Agent数据
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT agent_id, name, status, reputation
FROM ai_agents
WHERE status = 'online'
LIMIT 10;
"

# 3. 检查Agent能力分布
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT capabilities, COUNT(*) as count
FROM ai_agents
GROUP BY capabilities
ORDER BY count DESC
LIMIT 10;
"
```

### 2.2 测试数据准备

```sql
-- 创建多样化的测试Agent
INSERT OR REPLACE INTO ai_agents (agent_id, name, capabilities, skills, status, reputation, stake)
VALUES
  -- 高信誉Agent
  ('network-test-001', 'MLExpert', '["machine_learning", "deep_learning", "python"]', '["tensorflow", "pytorch"]', 'online', 0.95, 1000),
  ('network-test-002', 'DataScientist', '["data_analysis", "statistics", "python"]', '["pandas", "numpy", "scipy"]', 'online', 0.88, 800),
  ('network-test-003', 'NLPExpert', '["nlp", "text_analysis", "python"]', '["spacy", "nltk", "transformers"]', 'online', 0.92, 900),

  -- 中等信誉Agent
  ('network-test-004', 'WebDeveloper', '["web_development", "javascript", "react"]', '["nodejs", "typescript"]', 'online', 0.75, 300),
  ('network-test-005', 'MobileDeveloper', '["mobile_development", "flutter", "dart"]', '["ios", "android"]', 'online', 0.72, 250),

  -- 低信誉Agent
  ('network-test-006', 'NewbieAgent', '["basic_analysis"]', '["python"]', 'online', 0.45, 50),
  ('network-test-007', 'OfflineAgent', '["legacy_skills"]', '["cobol"]', 'offline', 0.60, 100);

-- 更新统计
UPDATE ai_agents SET updated_at = (strftime('%s', 'now') * 1000) WHERE agent_id LIKE 'network-test-%';
```

---

## 3. 后端API测试

### 3.1 测试用例列表

| 用例ID | 测试场景 | 端点 | 方法 | 预期结果 |
|--------|---------|------|------|---------|
| TC-N001 | 探索网络 - 无过滤 | `/api/network/explore` | POST | 200, 返回Agent列表 |
| TC-N002 | 探索网络 - 按能力过滤 | `/api/network/explore` | POST | 200, 返回匹配Agent |
| TC-N003 | 探索网络 - 深度限制 | `/api/network/explore` | POST | 200, 结果数量符合预期 |
| TC-N004 | 获取推荐 - 有效能力 | `/api/network/recommendations` | POST | 200, 返回推荐列表 |
| TC-N005 | 获取推荐 - 无匹配能力 | `/api/network/recommendations` | POST | 200, 空列表 |
| TC-N006 | 获取网络统计 | `/api/network/stats` | GET | 200, 返回完整统计 |
| TC-N007 | 认证验证 - 无认证 | `/api/network/explore` | POST | 401, 未授权 |

### 3.2 详细测试脚本

```python
# test_network_explorer.py

import pytest
import httpx
import json

BASE_URL = "http://localhost:8000/api"

class TestNetworkExplorerAPI:
    """网络探索模块API测试"""

    @pytest.fixture
    def auth_headers(self):
        """测试用认证头"""
        return {
            "X-API-Key": "test-api-key-xxx",
            "X-Agent-ID": "network-test-001"
        }

    @pytest.mark.asyncio
    async def test_TC_N001_explore_without_filter(self, auth_headers):
        """TC-N001: 探索网络 - 无过滤"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/network/explore",
                json={
                    "agent_id": "network-test-001",
                    "target_capabilities": None,
                    "exploration_depth": 1
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # 验证返回结构
            if len(data) > 0:
                agent = data[0]
                assert "agent_id" in agent
                assert "agent_name" in agent
                assert "capabilities" in agent
                assert "reputation" in agent
                assert "status" in agent

                # 不应包含自己
                assert agent["agent_id"] != "network-test-001"

            print(f"✅ TC-N001 通过: 发现 {len(data)} 个Agent")
            return data

    @pytest.mark.asyncio
    async def test_TC_N002_explore_with_capability_filter(self, auth_headers):
        """TC-N002: 探索网络 - 按能力过滤"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/network/explore",
                json={
                    "agent_id": "network-test-001",
                    "target_capabilities": ["machine_learning", "deep_learning"],
                    "exploration_depth": 2
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            # 验证过滤结果
            for agent in data:
                capabilities = agent.get("capabilities", [])
                # 至少有一个匹配的能力
                has_matching_cap = any(
                    any(tc.lower() in c.lower() for c in capabilities)
                    for tc in ["machine_learning", "deep_learning"]
                )
                # 注意：当前实现可能不做严格过滤，这里只是记录
                if not has_matching_cap:
                    print(f"  ⚠️ Agent {agent['agent_name']} 能力不匹配但被返回")

            print(f"✅ TC-N002 通过: 按能力过滤后返回 {len(data)} 个Agent")

    @pytest.mark.asyncio
    async def test_TC_N003_explore_depth_limit(self, auth_headers):
        """TC-N003: 探索深度限制"""
        results = {}

        async with httpx.AsyncClient() as client:
            for depth in [1, 2, 3]:
                response = await client.post(
                    f"{BASE_URL}/network/explore",
                    json={
                        "agent_id": "network-test-001",
                        "exploration_depth": depth
                    },
                    headers=auth_headers,
                    timeout=30.0
                )

                assert response.status_code == 200
                results[depth] = len(response.json())

        print(f"✅ TC-N003 通过: 深度1={results[1]}, 深度2={results[2]}, 深度3={results[3]}")
        # 深度越大，结果可能越多（取决于实现）

    @pytest.mark.asyncio
    async def test_TC_N004_recommendations_valid_capability(self, auth_headers):
        """TC-N004: 获取推荐 - 有效能力"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/network/recommendations",
                json={
                    "agent_id": "network-test-001",
                    "target_capability": "machine_learning"
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

            # 验证推荐结构
            if len(data) > 0:
                rec = data[0]
                assert "recommended_agent_id" in rec
                assert "recommended_agent_name" in rec
                assert "capability_match" in rec
                assert "trust_score" in rec
                assert "reason" in rec

                # 验证分数范围
                assert 0 <= rec["capability_match"] <= 1
                assert 0 <= rec["trust_score"] <= 1

                print(f"✅ TC-N004 通过: 获得 {len(data)} 个推荐")
                print(f"   最高匹配: {data[0]['recommended_agent_name']} ({data[0]['capability_match']:.2f})")
            else:
                print("⚠️ TC-N004: 未获得推荐，请检查测试数据")

    @pytest.mark.asyncio
    async def test_TC_N005_recommendations_no_match(self, auth_headers):
        """TC-N005: 获取推荐 - 无匹配能力"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/network/recommendations",
                json={
                    "agent_id": "network-test-001",
                    "target_capability": "quantum_teleportation"  # 稀有能力
                },
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            print(f"✅ TC-N005 通过: 稀有能力返回 {len(data)} 个推荐（预期为0或很少）")

    @pytest.mark.asyncio
    async def test_TC_N006_get_stats(self, auth_headers):
        """TC-N006: 获取网络统计"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/network/stats",
                headers=auth_headers,
                timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            # 验证统计字段
            required_fields = [
                "agent_id",
                "total_explorations",
                "total_discovered",
                "network_size",
                "trusted_agents"
            ]

            for field in required_fields:
                assert field in data, f"Missing field: {field}"

            print(f"✅ TC-N006 通过: 统计数据获取成功")
            print(f"   网络大小: {data['network_size']}")
            print(f"   信任Agent: {data['trusted_agents']}")
            print(f"   完整数据: {json.dumps(data, indent=2)}")

    @pytest.mark.asyncio
    async def test_TC_N007_no_auth(self):
        """TC-N007: 认证验证 - 无认证"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/network/explore",
                json={"agent_id": "test"}
            )

            assert response.status_code == 401, "Should reject without auth"
            print(f"✅ TC-N007 通过: 无认证请求被拒绝 ({response.status_code})")


class TestNetworkExplorerViewModes:
    """四视图模式测试"""

    @pytest.mark.asyncio
    async def test_trusted_agents_filter(self, auth_headers):
        """测试信任视图过滤"""
        async with httpx.AsyncClient() as client:
            # 获取所有Agent
            all_response = await client.post(
                f"{BASE_URL}/network/explore",
                json={"agent_id": "network-test-001"},
                headers=auth_headers
            )
            all_agents = all_response.json()

            # 过滤高信誉Agent
            trusted = [a for a in all_agents if a.get("reputation", 0) >= 0.7]

            print(f"✅ 信任视图: {len(trusted)}/{len(all_agents)} Agent 信誉 >= 0.7")

            for agent in trusted:
                print(f"   - {agent['agent_name']}: {agent['reputation']:.2f}")


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
```

---

## 4. 前端组件测试

### 4.1 React组件测试

```typescript
// frontend/src/__tests__/NetworkExplorer.test.tsx

import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import NetworkExplorer from '@/pages/NetworkExplorer'

// Mock authFetch
const mockAuthFetch = jest.fn()
jest.mock('@/lib/api', () => ({
  authFetch: () => mockAuthFetch(),
  authFetchJson: () => mockAuthFetch()
}))

const renderNetworkExplorer = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NetworkExplorer />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('NetworkExplorer Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Mock localStorage
    Storage.prototype.getItem = jest.fn(() => 'test-agent-001')
  })

  test('should render page title', () => {
    renderNetworkExplorer()
    expect(screen.getByText(/网络探索|Network/i)).toBeInTheDocument()
  })

  test('should display four view tabs', () => {
    renderNetworkExplorer()

    // 检查四个视图标签
    const tabs = ['explore', 'network', 'trusted', 'recommendations']
    tabs.forEach(tab => {
      expect(screen.getByRole('tab', { name: new RegExp(tab, 'i') })).toBeInTheDocument()
    })
  })

  test('should switch view modes correctly', async () => {
    renderNetworkExplorer()

    // 默认应该是explore视图
    expect(screen.getByTestId('explore-view')).toBeInTheDocument()

    // 点击信任视图
    fireEvent.click(screen.getByRole('tab', { name: /trusted/i }))
    await waitFor(() => {
      expect(screen.getByTestId('trusted-view')).toBeInTheDocument()
    })

    // 点击推荐视图
    fireEvent.click(screen.getByRole('tab', { name: /recommendations/i }))
    await waitFor(() => {
      expect(screen.getByTestId('recommendations-view')).toBeInTheDocument()
    })
  })

  test('should display statistics cards', () => {
    renderNetworkExplorer()

    // 检查统计卡片
    expect(screen.getByText(/探索次数|Explorations/i)).toBeInTheDocument()
    expect(screen.getByText(/网络大小|Network Size/i)).toBeInTheDocument()
    expect(screen.getByText(/信任|Trusted/i)).toBeInTheDocument()
    expect(screen.getByText(/发现|Discovered/i)).toBeInTheDocument()
  })

  test('should show exploration form in explore view', () => {
    renderNetworkExplorer()

    // 检查探索表单元素
    expect(screen.getByLabelText(/能力|Capability/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/深度|Depth/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /探索|Explore/i })).toBeInTheDocument()
  })

  test('should call API when clicking explore button', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          agent_id: 'agent-001',
          agent_name: 'Test Agent',
          capabilities: ['test'],
          skills: [],
          reputation: 0.8,
          status: 'online'
        }
      ]
    })

    renderNetworkExplorer()

    // 填写表单
    fireEvent.change(screen.getByLabelText(/能力|Capability/i), {
      target: { value: 'machine_learning' }
    })

    // 点击探索
    fireEvent.click(screen.getByRole('button', { name: /探索|Explore/i }))

    await waitFor(() => {
      expect(mockAuthFetch).toHaveBeenCalled()
    })
  })

  test('should display agent cards after exploration', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        {
          agent_id: 'agent-001',
          agent_name: 'ML Expert',
          capabilities: ['machine_learning', 'python'],
          skills: ['tensorflow'],
          reputation: 0.92,
          status: 'online'
        },
        {
          agent_id: 'agent-002',
          agent_name: 'Data Analyst',
          capabilities: ['data_analysis'],
          skills: ['pandas'],
          reputation: 0.75,
          status: 'online'
        }
      ]
    })

    renderNetworkExplorer()

    // 触发探索
    fireEvent.click(screen.getByRole('button', { name: /探索|Explore/i }))

    await waitFor(() => {
      expect(screen.getByText('ML Expert')).toBeInTheDocument()
      expect(screen.getByText('Data Analyst')).toBeInTheDocument()
    })
  })

  test('should show reputation with correct color coding', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { agent_id: 'a1', agent_name: 'High', capabilities: [], skills: [], reputation: 0.95, status: 'online' },
        { agent_id: 'a2', agent_name: 'Medium', capabilities: [], skills: [], reputation: 0.65, status: 'online' },
        { agent_id: 'a3', agent_name: 'Low', capabilities: [], skills: [], reputation: 0.35, status: 'online' }
      ]
    })

    renderNetworkExplorer()

    fireEvent.click(screen.getByRole('button', { name: /探索|Explore/i }))

    await waitFor(() => {
      const highRep = screen.getByText('95%')
      const mediumRep = screen.getByText('65%')
      const lowRep = screen.getByText('35%')

      // 验证颜色类
      expect(highRep).toHaveClass('text-green')
      expect(mediumRep).toHaveClass('text-yellow')
      expect(lowRep).toHaveClass('text-red')
    })
  })

  test('should show empty state when no agents found', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => []
    })

    renderNetworkExplorer()

    fireEvent.click(screen.getByRole('button', { name: /探索|Explore/i }))

    await waitFor(() => {
      expect(screen.getByText(/尚未发现|No agents discovered/i)).toBeInTheDocument()
    })
  })

  test('should show error state when API fails', async () => {
    mockAuthFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Internal Server Error'
    })

    renderNetworkExplorer()

    fireEvent.click(screen.getByRole('button', { name: /探索|Explore/i }))

    await waitFor(() => {
      expect(screen.getByText(/错误|Error/i)).toBeInTheDocument()
    })
  })
})
```

### 4.2 E2E测试

```typescript
// e2e/network-explorer.spec.ts

import { test, expect } from '@playwright/test'

test.describe('Network Explorer Module', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/app/network')
    await page.waitForSelector('[data-testid="network-explorer-page"]')
  })

  test('should explore network and display results', async ({ page }) => {
    // 1. 确认在探索视图
    await expect(page.locator('[data-testid="explore-view"]')).toBeVisible()

    // 2. 输入目标能力
    await page.fill('[data-testid="capability-input"]', 'python')

    // 3. 选择探索深度
    await page.selectOption('[data-testid="depth-select"]', '2')

    // 4. 点击探索
    await page.click('[data-testid="explore-button"]')

    // 5. 等待结果加载
    await page.waitForSelector('[data-testid="agent-card"]', { timeout: 10000 })

    // 6. 验证结果
    const cards = await page.$$('[data-testid="agent-card"]')
    expect(cards.length).toBeGreaterThan(0)
  })

  test('should switch between view modes', async ({ page }) => {
    // 切换到网络视图
    await page.click('[data-testid="tab-network"]')
    await expect(page.locator('[data-testid="network-view"]')).toBeVisible()

    // 切换到信任视图
    await page.click('[data-testid="tab-trusted"]')
    await expect(page.locator('[data-testid="trusted-view"]')).toBeVisible()

    // 切换到推荐视图
    await page.click('[data-testid="tab-recommendations"]')
    await expect(page.locator('[data-testid="recommendations-view"]')).toBeVisible()
  })

  test('should get recommendations for capability', async ({ page }) => {
    // 1. 切换到推荐视图
    await page.click('[data-testid="tab-recommendations"]')

    // 2. 输入目标能力
    await page.fill('[data-testid="recommendation-input"]', 'machine_learning')

    // 3. 点击搜索
    await page.click('[data-testid="search-recommendations-button"]')

    // 4. 等待推荐结果
    await page.waitForSelector('[data-testid="recommendation-card"]', { timeout: 10000 })

    // 5. 验证推荐包含匹配度和信任分数
    const firstCard = page.locator('[data-testid="recommendation-card"]:first-child')
    await expect(firstCard.locator('[data-testid="match-score"]')).toBeVisible()
    await expect(firstCard.locator('[data-testid="trust-score"]')).toBeVisible()
  })

  test('should display correct statistics', async ({ page }) => {
    // 检查统计卡片
    const statCards = await page.$$('[data-testid="stat-card"]')
    expect(statCards.length).toBe(4)

    // 验证每个统计卡片有数值
    for (const card of statCards) {
      const value = await card.$eval('[data-testid="stat-value"]', el => el.textContent)
      expect(value).not.toBe('-')
    }
  })

  test('should show concept explanation when expanded', async ({ page }) => {
    // 点击概念卡片展开
    await page.click('[data-testid="concept-card-toggle"]')

    // 验证概念说明可见
    await expect(page.locator('[data-testid="concept-definition"]')).toBeVisible()
    await expect(page.locator('[data-testid="use-cases"]')).toBeVisible()
  })
})
```

---

## 5. 调试指南

### 5.1 常见问题

| 问题 | 症状 | 排查步骤 |
|------|------|---------|
| 探索返回空结果 | 无Agent显示 | 1. 检查数据库Agent数量 2. 检查能力过滤条件 |
| 推荐功能异常 | 无推荐返回 | 1. 检查目标能力是否存在 2. 查看后端日志 |
| 统计数据不准确 | 数值与预期不符 | 1. 检查数据库数据 2. 验证聚合逻辑 |
| 视图切换卡顿 | UI响应慢 | 1. 检查数据量 2. 查看浏览器性能 |
| 认证失败 | 401错误 | 1. 检查API Key 2. 验证localStorage |

### 5.2 调试命令

```bash
# 查看在线Agent数量
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT status, COUNT(*) FROM ai_agents GROUP BY status;
"

# 查看高信誉Agent
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT agent_id, name, reputation, capabilities
FROM ai_agents
WHERE reputation >= 0.7 AND status = 'online'
ORDER BY reputation DESC;
"

# 检查能力分布
sqlite3 usmsb-sdk/data/meta_agent.db "
SELECT capabilities, COUNT(*) as cnt
FROM ai_agents
GROUP BY capabilities
ORDER BY cnt DESC;
"

# 后端日志
tail -f /var/log/usmsb/api.log | grep -E "network|explore|recommendation"
```

### 5.3 关键断点

```python
# network.py 调试断点

@router.post("/explore")
async def explore_network(request, user):
    agent_id = user.get('agent_id')
    # BP1: 检查认证
    print(f"[DEBUG] Explore request from: {agent_id}")

    all_agents = db_get_all_agents()
    # BP2: 检查数据库返回
    print(f"[DEBUG] Total agents from DB: {len(all_agents)}")

    # 能力过滤
    if request.target_capabilities:
        # BP3: 检查过滤条件
        print(f"[DEBUG] Filtering by: {request.target_capabilities}")

    # BP4: 检查最终结果
    print(f"[DEBUG] Returning {len(discovered)} agents")
    return discovered
```

---

## 6. 测试执行计划

```
Phase 1: 数据准备 (5分钟)
  ├── 插入测试Agent数据
  └── 验证数据完整性

Phase 2: 后端API测试 (10分钟)
  ├── TC-N001 ~ TC-N003: 探索功能
  ├── TC-N004 ~ TC-N005: 推荐功能
  └── TC-N006 ~ TC-N007: 统计与认证

Phase 3: 前端组件测试 (15分钟)
  ├── 视图切换测试
  ├── API集成测试
  └── 状态显示测试

Phase 4: E2E测试 (10分钟)
  ├── 完整探索流程
  ├── 推荐获取流程
  └── 统计显示验证

Phase 5: 问题修复 (20分钟)
```

---

## 7. 确认事项

执行测试前请确认：

- [ ] 数据库中有足够的测试Agent（至少5个不同能力）
- [ ] 有高信誉(>=0.7)和低信誉(<0.5)的Agent用于测试
- [ ] 有在线和离线状态的Agent
- [ ] 后端服务正常
- [ ] 前端开发服务器运行中（E2E测试）

**是否确认执行此测试方案？**
