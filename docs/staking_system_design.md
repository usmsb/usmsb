# Staking System Optimization Design

**[English](#staking-system-optimization-design) | [中文](#质押系统优化设计方案)**

## Context

The staking feature on the `/app/onboarding` page currently has the following issues:
1. **No permission check**: No validation of user balance or staking status during staking
2. **Profile API 500 error**: `request.hourly_rate` should be `request.hourlyRate` in `auth.py`
3. **Invalid documentation links**: `href="#"` has no actual navigation address
4. **Missing staking management features**: Users cannot unstake or add more stake later
5. **Missing global toggle**: Cannot disable staking restrictions in test/single-node mode

This solution aims to address the above issues and establish a complete staking system.

---

## 1. Staking State Machine Design

```
┌─────────────────────────────────────────────────────────────────┐
│                   User Staking State Transitions                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   [Not Connected] ──Connect Wallet──> [Connected/Unstaked]    │
│                              │                                  │
│                              ├──Stake──> [Staked]              │
│                              │          │                       │
│                              │          ├──Add Stake──> [Staked]│
│                              │          │    (amount accumulates)│
│                              │          │                       │
│                              │          └──Request Unstake──> [Unstaking]│
│                              │                    │              │
│                              │                    ├──After 7 days──> [Unstaked] ≈ [Unstaked]│
│                              │                    │              │
│                              │                    └──Cancel Unstake──> [Staked]│
│                              │                                  │
│                              └──Skip──> [Connected/Unstaked]   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### State Definitions

| State | Description | stake Value | Executable Operations |
|-------|-------------|-------------|----------------------|
| `none` | Not staked | 0 | Stake |
| `staked` | Staked | >= 100 | Add stake, Request unstake |
| `unstaking` | Unstaking | >= 100 (locked) | Cancel unstake, Wait for unlock |
| `unlocked` | Unlocked | 0 | Re-stake |

---

## 2. Feature Permission Matrix

| Feature Page | Route | Unstaked User | Staked User | Description |
|--------------|-------|---------------|-------------|-------------|
| Dashboard | `/app/dashboard` | Read-only | Full | Statistics |
| Agents List | `/app/agents` | Read-only | Full | Browse Agents |
| Agent Detail | `/app/agents/:id` | Read-only | Full | View Details |
| **Publish Service** | `/app/publish-service` | No | Yes | Requires stake |
| **Publish Demand** | `/app/publish-demand` | No | Yes | Requires stake |
| **Register Agent** | `/app/register-agent` | No | Yes | Requires stake |
| **Collaboration** | `/app/collaborations` | No | Yes | Requires stake |
| **Matching** | `/app/matching` | No | Yes | Requires stake |
| **Governance Vote** | `/app/governance` | No | Yes | Requires stake |
| Chat | `/app/chat` | Yes | Yes | Basic feature |
| Settings | `/app/settings` | Yes | Yes | Includes staking management |
| Marketplace | `/app/marketplace` | Read-only | Full | Browse marketplace |

---

## 3. Global Staking Toggle

### 3.1 Configuration Method

**Environment Variable (Recommended)**:
```bash
# .env file
STAKE_REQUIRED=true   # Enable staking restrictions (default, production)
STAKE_REQUIRED=false  # Disable staking restrictions (test/single-node mode)
```

**Startup Parameter**:
```bash
# Pass via environment variable
STAKE_REQUIRED=false python -m uvicorn main:app

# Or export directly
export STAKE_REQUIRED=false
python -m uvicorn main:app
```

### 3.2 Toggle Behavior

| Configuration | STAKE_REQUIRED=true | STAKE_REQUIRED=false |
|--------------|---------------------|----------------------|
| **Use Case** | Production/Multi-node network | Single-node/Test/Development |
| **Staking API** | Normal validation | Skip validation, return success directly |
| **Feature Access** | Requires stake | Unrestricted access |
| **Frontend Prompt** | Show staking guidance | Don't show staking restrictions |
| **User Status** | Normal stake record | Stake status meaningless |

### 3.3 API Response Changes

When `STAKE_REQUIRED=false`:

```python
# GET /auth/config - Frontend gets configuration
{
  "stakeRequired": false,
  "minStakeAmount": 100,
  "defaultBalance": 10000
}

# POST /auth/stake - Staking endpoint
{
  "success": true,
  "skipped": true,  // Flag indicating actual staking was skipped
  "message": "Stake requirement is disabled in current mode"
}
```

---

## 4. Staking Lock Period Design

### 4.1 Unstake Flow

```
User clicks "Unstake"
        │
        ▼
Check if status is 'staked'
        │
        ▼
Update status to 'unstaking'
Record unlock_available_at = now + 7 days
        │
        ▼
Show countdown UI
Provide "Cancel Unstake" button
        │
        ├──────────────────────────┐
        ▼                          ▼
Auto-unlock after 7 days    User clicks "Cancel Unstake"
        │                          │
        ▼                          ▼
stake -> 0                  Restore status to 'staked'
status -> 'unlocked'        Delete unlock_available_at
Balance increases                  │
        │                          │
        └──────────────────────────┘
```

### 4.2 Data Model

```python
# New fields in users table
class User:
    # Existing fields...
    vibe_balance: float = 10000.0      # VIBE balance (simulated)
    stake_status: str = 'none'          # none/staked/unstaking/unlocked
    locked_stake: float = 0             # Locked amount
    unlock_available_at: float = None   # Unlock available timestamp
```

---

## 5. API Design

### 5.1 New/Modified API Endpoints

#### GET /auth/config
Get staking configuration (called during frontend initialization)

```python
class StakeConfigResponse(BaseModel):
    stakeRequired: bool          # Whether staking restrictions are enabled
    minStakeAmount: float        # Minimum stake amount 100
    defaultBalance: float        # Initial simulated balance 10000
    unstakingPeriodDays: int     # Unlock waiting days 7

@router.get("/config", response_model=StakeConfigResponse)
async def get_stake_config():
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"
    return StakeConfigResponse(
        stakeRequired=stake_required,
        minStakeAmount=100.0,
        defaultBalance=10000.0,
        unstakingPeriodDays=7
    )
```

#### GET /auth/balance
Get user VIBE balance

```python
class BalanceResponse(BaseModel):
    balance: float              # Available balance
    stakedAmount: float         # Staked amount
    lockedAmount: float         # Locked amount
    totalBalance: float         # Total balance

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    ...
```

#### POST /auth/stake (Modified)
Add validation

```python
@router.post("/stake", response_model=StakeResponse)
async def stake_tokens(request: StakeRequest, user: dict = Depends(get_current_user)):
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # If staking restrictions are disabled, return success directly
    if not stake_required:
        return StakeResponse(success=True, skipped=True, ...)

    # Validation 1: Minimum amount
    if request.amount < 100:
        raise HTTPException(400, "Minimum stake is 100 VIBE")

    # Validation 2: Sufficient balance
    if user['vibe_balance'] < request.amount:
        raise HTTPException(400, "Insufficient VIBE balance")

    # Validation 3: Status check (allow adding stake in staked state)
    if user['stake_status'] == 'unstaking':
        raise HTTPException(400, "Cannot stake while unstaking")

    # Execute staking...
```

#### POST /auth/stake (New)
Request to unstake

```python
class UnstakeRequest(BaseModel):
    amount: Optional[float] = None  # None = unstake all

class UnstakeResponse(BaseModel):
    success: bool
    lockedAmount: float
    unlockAvailableAt: int  # Timestamp

@router.post("/unstake", response_model=UnstakeResponse)
async def unstake_tokens(request: UnstakeRequest, user: dict = Depends(get_current_user)):
    # Validate status
    if user['stake_status'] != 'staked':
        raise HTTPException(400, "No stake to unstake")

    # Set unstaking status
    # unlock_available_at = now + 7 days
    ...
```

#### POST /auth/unstake/cancel (New)
Cancel unstake

```python
@router.post("/unstake/cancel")
async def cancel_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    # Restore to staked status
    ...
```

#### POST /auth/unstake/confirm (New)
Confirm unlock (called after 7 days)

```python
@router.post("/unstake/confirm")
async def confirm_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    if datetime.now().timestamp() < user['unlock_available_at']:
        raise HTTPException(400, "Unlock period not completed")
    # Return balance, clear stake
    ...
```

#### POST /auth/profile (Fixed)
Fix 500 error

```python
# Modify line 308
# Error: 'hourly_rate': request.hourly_rate
# Correct: 'hourly_rate': request.hourlyRate
```

---

## 6. Frontend Design

### 6.1 authStore Extension

```typescript
// stores/authStore.ts new fields
interface AuthState {
  // Existing fields...

  // New staking related
  vibeBalance: number           // VIBE available balance
  stakedAmount: number          // Staked amount
  lockedAmount: number          // Locked amount
  stakeStatus: StakeStatus      // 'none' | 'staked' | 'unstaking' | 'unlocked'
  unlockAvailableAt: number | null  // Unlock available time

  // Configuration related
  stakeRequired: boolean        // Backend staking toggle status

  // New Actions
  updateStakeInfo: (info: StakeInfo) => void
}
```

### 6.2 Staking Guide Modal Component

**File**: `components/StakeGuideModal.tsx`

```tsx
interface StakeGuideModalProps {
  isOpen: boolean
  onClose: () => void
  featureName: string  // Feature name that triggered the modal
  requiredStake?: number
}

// Modal content:
// 1. Explain staking is required to use this feature
// 2. List staking benefits
// 3. Provide "Stake Now" and "Later" buttons
// 4. Click "Stake Now" redirects to /app/onboarding or settings page
```

### 6.3 useStakeGuard Hook

**File**: `hooks/useStakeGuard.ts`

```tsx
export function useStakeGuard() {
  const { stakeStatus, stakeRequired, accessToken } = useAuthStore()
  const [showGuideModal, setShowGuideModal] = useState(false)
  const [targetFeature, setTargetFeature] = useState('')

  // Check if user has permission to access a feature
  const checkAccess = useCallback((featureName: string): boolean => {
    // If backend disabled staking restrictions, allow directly
    if (!stakeRequired) return true

    // If not logged in
    if (!accessToken) {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    // If not staked
    if (stakeStatus !== 'staked') {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    return true
  }, [stakeRequired, accessToken, stakeStatus])

  return {
    checkAccess,
    showGuideModal,
    targetFeature,
    closeGuideModal: () => setShowGuideModal(false)
  }
}
```

### 6.4 Staking Management Page (New Tab in Settings)

**File**: `pages/Settings.tsx` new staking management section

```
┌────────────────────────────────────────┐
│  Staking Management                    │
├────────────────────────────────────────┤
│                                        │
│  Status: ✅ Staked                     │
│  Staked Amount: 1,000 VIBE             │
│  Stake Level: 🥈 Silver                 │
│  Available Balance: 9,000 VIBE         │
│  Total Assets: 10,000 VIBE             │
│                                        │
│  [Add Stake]     [Unstake]             │
│                                        │
├────────────────────────────────────────┤
│  Staking Benefits                      │
│  • Publish services and demands         │
│  • Register AI Agents                   │
│  • Participate in collaboration matching│
│  • Governance voting rights            │
└────────────────────────────────────────┘
```

### 6.5 Route Guard Implementation

**Modify**: `App.tsx`

```tsx
// Create ProtectedRoute component
function StakeProtectedRoute({ children, featureName }: { children: ReactNode, featureName: string }) {
  const { checkAccess, showGuideModal, targetFeature, closeGuideModal } = useStakeGuard()

  if (!checkAccess(featureName)) {
    return (
      <>
        {children}  // Or show restricted notice
        <StakeGuideModal
          isOpen={showGuideModal}
          onClose={closeGuideModal}
          featureName={targetFeature}
        />
      </>
    )
  }

  return <>{children}</>
}

// Use on protected routes
<Route path="publish-service" element={
  <StakeProtectedRoute featureName="Publish Service">
    <PublishService />
  </StakeProtectedRoute>
} />
```

---

## 7. Database Changes

### 7.1 New Fields in users Table

```sql
ALTER TABLE users ADD COLUMN vibe_balance REAL DEFAULT 10000.0;
ALTER TABLE users ADD COLUMN stake_status TEXT DEFAULT 'none';
ALTER TABLE users ADD COLUMN locked_stake REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN unlock_available_at REAL;
```

### 7.2 Update init_db Function

**File**: `usmsb_sdk/api/database.py`

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        wallet_address TEXT UNIQUE NOT NULL,
        did TEXT UNIQUE,
        agent_id TEXT,
        stake REAL DEFAULT 0,
        reputation REAL DEFAULT 0.5,
        vibe_balance REAL DEFAULT 10000.0,    -- New
        stake_status TEXT DEFAULT 'none',     -- New
        locked_stake REAL DEFAULT 0,          -- New
        unlock_available_at REAL,             -- New
        created_at REAL,
        updated_at REAL
    )
''')
```

---

## 8. Implementation Steps

### Phase 1: Backend Basics (Priority)
1. Modify `database.py` - Add new fields to users table
2. Modify `auth.py` - Add config API and balance API
3. Fix `auth.py` line 308 `hourly_rate` error
4. Add global staking toggle support

### Phase 2: Staking API Enhancement
5. Modify `/auth/stake` - Add balance validation
6. Implement `/auth/unstake` - Request unstake
7. Implement `/auth/unstake/cancel` - Cancel unstake
8. Implement `/auth/unstake/confirm` - Confirm unlock

### Phase 3: Frontend Infrastructure
9. Modify `authStore.ts` - Add new fields
10. Create `useStakeGuard.ts` Hook
11. Create `StakeGuideModal.tsx` component
12. Add API calls (`authService.ts`)

### Phase 4: Feature Integration
13. Modify `App.tsx` - Add route guards
14. Modify `Settings.tsx` - Add staking management Tab
15. Modify `Onboarding.tsx` - Fix documentation links

### Phase 5: Testing and Verification
16. Test staking flow
17. Test unstake flow (with 7-day wait)
18. Test STAKE_REQUIRED=false mode
19. Test restricted feature access

---

## 9. Key File List

| File Path | Changes |
|-----------|---------|
| `usmsb_sdk/api/database.py` | users table new fields |
| `usmsb_sdk/api/rest/auth.py` | Fix bug + new API |
| `usmsb_sdk/config/settings.py` | Add stake_required config |
| `frontend/src/stores/authStore.ts` | New staking status fields |
| `frontend/src/hooks/useStakeGuard.ts` | New - Permission guard Hook |
| `frontend/src/components/StakeGuideModal.tsx` | New - Staking guide modal |
| `frontend/src/services/authService.ts` | New API calls |
| `frontend/src/App.tsx` | Add route guards |
| `frontend/src/pages/Settings.tsx` | Add staking management |
| `frontend/src/pages/Onboarding.tsx` | Fix documentation links |

---

## 10. Verification Plan

### 10.1 Backend Testing

```bash
# 1. Start backend (with staking restrictions)
STAKE_REQUIRED=true python -m uvicorn usmsb_sdk.api.rest.main:app

# 2. Test config API
curl http://localhost:8000/api/auth/config
# Expected: {"stakeRequired": true, ...}

# 3. Start backend (without staking restrictions)
STAKE_REQUIRED=false python -m uvicorn usmsb_sdk.api.rest.main:app

# 4. Test config API again
curl http://localhost:8000/api/auth/config
# Expected: {"stakeRequired": false, ...}
```

### 10.2 Frontend Testing

1. **Unstaked user accessing restricted feature**
   - Visit `/app/publish-service`
   - Expected: Show staking guide modal

2. **After disabling staking restrictions**
   - Set `STAKE_REQUIRED=false`
   - Visit `/app/publish-service`
   - Expected: Direct access, no modal

3. **Staking flow**
   - Stake 100 VIBE in settings page
   - Expected: Status changes to staked

4. **Unstake flow**
   - Click unstake
   - Expected: Status changes to unstaking, show countdown
   - Click cancel unstake
   - Expected: Restore to staked

### 10.3 API 500 Error Verification

```bash
# Test profile API
curl -X POST http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "bio": "test", "skills": [], "hourlyRate": 100}'

# Expected: 200 OK, not 500
```

---

<details>
<summary><h2>质押系统优化设计方案</h2></summary>

# 质押系统优化设计方案

## Context（背景）

当前 `/app/onboarding` 页面的质押功能存在以下问题：
1. **无权限校验**：质押时没有检查用户余额、是否已质押等条件
2. **完善资料 API 500 错误**：`auth.py` 中 `request.hourly_rate` 应为 `request.hourlyRate`
3. **文档链接无效**：`href="#"` 没有实际跳转地址
4. **缺少质押管理功能**：用户无法撤回质押、无法后续补质押
5. **缺少全局开关**：无法在测试/单节点模式下关闭质押限制

本方案旨在解决以上问题，建立完整的质押系统。

---

## 一、质押状态机设计

```
┌─────────────────────────────────────────────────────────────────┐
│                      用户质押状态流转                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   [未连接] ──连接钱包──> [已连接/未质押]                        │
│                              │                                  │
│                              ├──质押──> [已质押]                 │
│                              │          │                       │
│                              │          ├──增加质押──> [已质押]  │
│                              │          │    (金额累加)         │
│                              │          │                       │
│                              │          └──申请撤回──> [解锁中]  │
│                              │                    │              │
│                              │                    ├──7天后──> [已撤回] ≈ [未质押] │
│                              │                    │              │
│                              │                    └──取消撤回──> [已质押] │
│                              │                                  │
│                              └──跳过──> [已连接/未质押]          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 状态定义

| 状态 | 说明 | stake 值 | 可执行操作 |
|------|------|----------|-----------|
| `none` | 未质押 | 0 | 质押 |
| `staked` | 已质押 | >= 100 | 增加质押、申请撤回 |
| `unstaking` | 解锁中 | >= 100 (锁定) | 取消撤回、等待解锁 |
| `unlocked` | 已解锁 | 0 | 重新质押 |

---

## 二、功能权限矩阵

| 功能页面 | 路由 | 未质押用户 | 已质押用户 | 说明 |
|----------|------|-----------|-----------|------|
| Dashboard | `/app/dashboard` | ✅ 只读 | ✅ | 统计数据 |
| Agents 列表 | `/app/agents` | ✅ 只读 | ✅ | 浏览 Agent |
| Agent 详情 | `/app/agents/:id` | ✅ 只读 | ✅ | 查看详情 |
| **发布服务** | `/app/publish-service` | ❌ | ✅ | 需质押 |
| **发布需求** | `/app/publish-demand` | ❌ | ✅ | 需质押 |
| **注册 Agent** | `/app/register-agent` | ❌ | ✅ | 需质押 |
| **协作** | `/app/collaborations` | ❌ | ✅ | 需质押 |
| **匹配** | `/app/matching` | ❌ | ✅ | 需质押 |
| **治理投票** | `/app/governance` | ❌ | ✅ | 需质押 |
| Chat | `/app/chat` | ✅ | ✅ | 基础功能 |
| Settings | `/app/settings` | ✅ | ✅ | 包括质押管理 |
| Marketplace | `/app/marketplace` | ✅ 只读 | ✅ | 浏览市场 |

---

## 三、全局质押开关

### 3.1 配置方式

**环境变量方式**（推荐）：
```bash
# .env 文件
STAKE_REQUIRED=true   # 开启质押限制（默认，生产环境）
STAKE_REQUIRED=false  # 关闭质押限制（测试/单节点模式）
```

**启动参数方式**：
```bash
# 通过环境变量传递
STAKE_REQUIRED=false python -m uvicorn main:app

# 或直接导出
export STAKE_REQUIRED=false
python -m uvicorn main:app
```

### 3.2 开关行为

| 配置 | STAKE_REQUIRED=true | STAKE_REQUIRED=false |
|------|---------------------|----------------------|
| **适用场景** | 生产环境/多节点网络 | 单节点/测试/开发 |
| **质押 API** | 正常校验 | 跳过校验，直接成功 |
| **功能访问** | 需要质押 | 无限制访问 |
| **前端提示** | 显示质押引导 | 不显示质押限制 |
| **用户状态** | 正常记录质押 | 质押状态无意义 |

### 3.3 API 响应变化

当 `STAKE_REQUIRED=false` 时：

```python
# GET /auth/config - 前端获取配置
{
  "stakeRequired": false,
  "minStakeAmount": 100,
  "defaultBalance": 10000
}

# POST /auth/stake - 质押接口
{
  "success": true,
  "skipped": true,  // 标识跳过了实际质押
  "message": "Stake requirement is disabled in current mode"
}
```

---

## 四、质押锁定期设计

### 4.1 撤回流程

```
用户点击"撤回质押"
        │
        ▼
检查状态是否为 'staked'
        │
        ▼
更新状态为 'unstaking'
记录 unlock_available_at = now + 7天
        │
        ▼
显示倒计时 UI
提供"取消撤回"按钮
        │
        ├──────────────────────────┐
        ▼                          ▼
7天后自动解锁              用户点击"取消撤回"
        │                          │
        ▼                          ▼
stake -> 0                  状态恢复为 'staked'
status -> 'unlocked'        删除 unlock_available_at
余额增加                            │
        │                          │
        └──────────────────────────┘
```

### 4.2 数据模型

```python
# users 表新增字段
class User:
    # 现有字段...
    vibe_balance: float = 10000.0      # VIBE 余额（模拟）
    stake_status: str = 'none'          # none/staked/unstaking/unlocked
    locked_stake: float = 0             # 锁定中的金额
    unlock_available_at: float = None   # 可解锁时间戳
```

---

## 五、API 设计

### 5.1 新增/修改的 API 端点

#### GET /auth/config
获取质押配置（前端初始化时调用）

```python
class StakeConfigResponse(BaseModel):
    stakeRequired: bool          # 是否开启质押限制
    minStakeAmount: float        # 最低质押金额 100
    defaultBalance: float        # 初始模拟余额 10000
    unstakingPeriodDays: int     # 解锁等待天数 7

@router.get("/config", response_model=StakeConfigResponse)
async def get_stake_config():
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"
    return StakeConfigResponse(
        stakeRequired=stake_required,
        minStakeAmount=100.0,
        defaultBalance=10000.0,
        unstakingPeriodDays=7
    )
```

#### GET /auth/balance
获取用户 VIBE 余额

```python
class BalanceResponse(BaseModel):
    balance: float              # 可用余额
    stakedAmount: float         # 已质押金额
    lockedAmount: float         # 锁定中金额
    totalBalance: float         # 总余额

@router.get("/balance", response_model=BalanceResponse)
async def get_balance(user: dict = Depends(get_current_user)):
    ...
```

#### POST /auth/stake（修改）
增加质押校验

```python
@router.post("/stake", response_model=StakeResponse)
async def stake_tokens(request: StakeRequest, user: dict = Depends(get_current_user)):
    stake_required = os.environ.get("STAKE_REQUIRED", "true").lower() == "true"

    # 如果关闭质押限制，直接返回成功
    if not stake_required:
        return StakeResponse(success=True, skipped=True, ...)

    # 校验1: 最低金额
    if request.amount < 100:
        raise HTTPException(400, "Minimum stake is 100 VIBE")

    # 校验2: 余额充足
    if user['vibe_balance'] < request.amount:
        raise HTTPException(400, "Insufficient VIBE balance")

    # 校验3: 状态检查（允许 staked 状态增加质押）
    if user['stake_status'] == 'unstaking':
        raise HTTPException(400, "Cannot stake while unstaking")

    # 执行质押...
```

#### POST /auth/unstake（新增）
申请撤回质押

```python
class UnstakeRequest(BaseModel):
    amount: Optional[float] = None  # None = 全部撤回

class UnstakeResponse(BaseModel):
    success: bool
    lockedAmount: float
    unlockAvailableAt: int  # 时间戳

@router.post("/unstake", response_model=UnstakeResponse)
async def unstake_tokens(request: UnstakeRequest, user: dict = Depends(get_current_user)):
    # 校验状态
    if user['stake_status'] != 'staked':
        raise HTTPException(400, "No stake to unstake")

    # 设置解锁中状态
    # unlock_available_at = now + 7天
    ...
```

#### POST /auth/unstake/cancel（新增）
取消撤回

```python
@router.post("/unstake/cancel")
async def cancel_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    # 恢复为 staked 状态
    ...
```

#### POST /auth/unstake/confirm（新增）
确认解锁（7天后调用）

```python
@router.post("/unstake/confirm")
async def confirm_unstake(user: dict = Depends(get_current_user)):
    if user['stake_status'] != 'unstaking':
        raise HTTPException(400, "Not in unstaking state")
    if datetime.now().timestamp() < user['unlock_available_at']:
        raise HTTPException(400, "Unlock period not completed")
    # 返还余额，清除质押
    ...
```

#### POST /auth/profile（修复）
修复 500 错误

```python
# 修改第308行
# 错误: 'hourly_rate': request.hourly_rate
# 正确: 'hourly_rate': request.hourlyRate
```

---

## 六、前端设计

### 6.1 authStore 扩展

```typescript
// stores/authStore.ts 新增字段
interface AuthState {
  // 现有字段...

  // 新增质押相关
  vibeBalance: number           // VIBE 可用余额
  stakedAmount: number          // 已质押金额
  lockedAmount: number          // 锁定中金额
  stakeStatus: StakeStatus      // 'none' | 'staked' | 'unstaking' | 'unlocked'
  unlockAvailableAt: number | null  // 可解锁时间

  // 配置相关
  stakeRequired: boolean        // 后端质押开关状态

  // 新增 Actions
  updateStakeInfo: (info: StakeInfo) => void
}
```

### 6.2 质押引导弹窗组件

**文件**: `components/StakeGuideModal.tsx`

```tsx
interface StakeGuideModalProps {
  isOpen: boolean
  onClose: () => void
  featureName: string  // 触发弹窗的功能名称
  requiredStake?: number
}

// 弹窗内容：
// 1. 说明需要质押才能使用该功能
// 2. 列出质押权益
// 3. 提供"立即质押"和"稍后再说"按钮
// 4. 点击"立即质押"跳转到 /app/onboarding 或设置页
```

### 6.3 useStakeGuard Hook

**文件**: `hooks/useStakeGuard.ts`

```tsx
export function useStakeGuard() {
  const { stakeStatus, stakeRequired, accessToken } = useAuthStore()
  const [showGuideModal, setShowGuideModal] = useState(false)
  const [targetFeature, setTargetFeature] = useState('')

  // 检查是否有权限访问某功能
  const checkAccess = useCallback((featureName: string): boolean => {
    // 如果后端关闭了质押限制，直接放行
    if (!stakeRequired) return true

    // 如果未登录
    if (!accessToken) {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    // 如果未质押
    if (stakeStatus !== 'staked') {
      setTargetFeature(featureName)
      setShowGuideModal(true)
      return false
    }

    return true
  }, [stakeRequired, accessToken, stakeStatus])

  return {
    checkAccess,
    showGuideModal,
    targetFeature,
    closeGuideModal: () => setShowGuideModal(false)
  }
}
```

### 6.4 质押管理页面（Settings 中新增 Tab）

**文件**: `pages/Settings.tsx` 新增质押管理部分

```
┌────────────────────────────────────────┐
│  质押管理                              │
├────────────────────────────────────────┤
│                                        │
│  状态: ✅ 已质押                       │
│  质押金额: 1,000 VIBE                  │
│  质押等级: 🥈 Silver                   │
│  可用余额: 9,000 VIBE                  │
│  总资产: 10,000 VIBE                   │
│                                        │
│  [增加质押]     [撤回质押]             │
│                                        │
├────────────────────────────────────────┤
│  质押权益说明                          │
│  • 发布服务和需求                      │
│  • 注册 AI Agent                       │
│  • 参与协作匹配                        │
│  • 治理投票权                          │
└────────────────────────────────────────┘
```

### 6.5 路由守卫实现

**修改**: `App.tsx`

```tsx
// 创建 ProtectedRoute 组件
function StakeProtectedRoute({ children, featureName }: { children: ReactNode, featureName: string }) {
  const { checkAccess, showGuideModal, targetFeature, closeGuideModal } = useStakeGuard()

  if (!checkAccess(featureName)) {
    return (
      <>
        {children}  // 或者显示受限提示
        <StakeGuideModal
          isOpen={showGuideModal}
          onClose={closeGuideModal}
          featureName={targetFeature}
        />
      </>
    )
  }

  return <>{children}</>
}

// 在需要保护的路由上使用
<Route path="publish-service" element={
  <StakeProtectedRoute featureName="发布服务">
    <PublishService />
  </StakeProtectedRoute>
} />
```

---

## 七、数据库变更

### 7.1 users 表新增字段

```sql
ALTER TABLE users ADD COLUMN vibe_balance REAL DEFAULT 10000.0;
ALTER TABLE users ADD COLUMN stake_status TEXT DEFAULT 'none';
ALTER TABLE users ADD COLUMN locked_stake REAL DEFAULT 0;
ALTER TABLE users ADD COLUMN unlock_available_at REAL;
```

### 7.2 更新 init_db 函数

**文件**: `usmsb_sdk/api/database.py`

```python
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        wallet_address TEXT UNIQUE NOT NULL,
        did TEXT UNIQUE,
        agent_id TEXT,
        stake REAL DEFAULT 0,
        reputation REAL DEFAULT 0.5,
        vibe_balance REAL DEFAULT 10000.0,    -- 新增
        stake_status TEXT DEFAULT 'none',     -- 新增
        locked_stake REAL DEFAULT 0,          -- 新增
        unlock_available_at REAL,             -- 新增
        created_at REAL,
        updated_at REAL
    )
''')
```

---

## 八、实现步骤

### Phase 1: 后端基础（优先）
1. 修改 `database.py` - 添加新字段到 users 表
2. 修改 `auth.py` - 添加配置 API 和余额 API
3. 修复 `auth.py` 第308行 `hourly_rate` 错误
4. 添加全局质押开关支持

### Phase 2: 质押 API 完善
5. 修改 `/auth/stake` - 添加余额校验
6. 实现 `/auth/unstake` - 申请撤回
7. 实现 `/auth/unstake/cancel` - 取消撤回
8. 实现 `/auth/unstake/confirm` - 确认解锁

### Phase 3: 前端基础设施
9. 修改 `authStore.ts` - 添加新字段
10. 创建 `useStakeGuard.ts` Hook
11. 创建 `StakeGuideModal.tsx` 组件
12. 添加 API 调用 (`authService.ts`)

### Phase 4: 功能集成
13. 修改 `App.tsx` - 添加路由守卫
14. 修改 `Settings.tsx` - 添加质押管理 Tab
15. 修改 `Onboarding.tsx` - 修复文档链接

### Phase 5: 测试验证
16. 测试质押流程
17. 测试撤回流程（含7天等待）
18. 测试 STAKE_REQUIRED=false 模式
19. 测试受限功能访问

---

## 九、关键文件清单

| 文件路径 | 修改内容 |
|---------|---------|
| `usmsb_sdk/api/database.py` | users 表新增字段 |
| `usmsb_sdk/api/rest/auth.py` | 修复 bug + 新增 API |
| `usmsb_sdk/config/settings.py` | 添加 stake_required 配置 |
| `frontend/src/stores/authStore.ts` | 新增质押状态字段 |
| `frontend/src/hooks/useStakeGuard.ts` | 新建 - 权限守卫 Hook |
| `frontend/src/components/StakeGuideModal.tsx` | 新建 - 质押引导弹窗 |
| `frontend/src/services/authService.ts` | 新增 API 调用 |
| `frontend/src/App.tsx` | 添加路由守卫 |
| `frontend/src/pages/Settings.tsx` | 添加质押管理 |
| `frontend/src/pages/Onboarding.tsx` | 修复文档链接 |

---

## 十、验证方案

### 10.1 后端测试

```bash
# 1. 启动后端（开启质押限制）
STAKE_REQUIRED=true python -m uvicorn usmsb_sdk.api.rest.main:app

# 2. 测试配置 API
curl http://localhost:8000/api/auth/config
# 期望: {"stakeRequired": true, ...}

# 3. 启动后端（关闭质押限制）
STAKE_REQUIRED=false python -m uvicorn usmsb_sdk.api.rest.main:app

# 4. 再次测试配置 API
curl http://localhost:8000/api/auth/config
# 期望: {"stakeRequired": false, ...}
```

### 10.2 前端测试

1. **未质押用户访问受限功能**
   - 访问 `/app/publish-service`
   - 期望：弹出质押引导弹窗

2. **关闭质押限制后**
   - 设置 `STAKE_REQUIRED=false`
   - 访问 `/app/publish-service`
   - 期望：直接进入，无弹窗

3. **质押流程**
   - 在设置页质押 100 VIBE
   - 期望：状态变为已质押

4. **撤回流程**
   - 点击撤回质押
   - 期望：状态变为解锁中，显示倒计时
   - 点击取消撤回
   - 期望：恢复为已质押

### 10.3 API 500 错误验证

```bash
# 测试完善资料 API
curl -X POST http://localhost:8000/api/auth/profile \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "bio": "test", "skills": [], "hourlyRate": 100}'

# 期望: 200 OK，不再是 500
```

</details>
