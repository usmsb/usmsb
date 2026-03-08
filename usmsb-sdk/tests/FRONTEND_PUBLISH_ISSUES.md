# 前端发布功能问题分析报告

> 分析时间: 2026-03-08
> 影响页面: PublishDemand.tsx, PublishService.tsx
> **状态: ✅ 已修复**

---

## 修复摘要

| 问题 | 状态 | 修复方式 |
|------|------|----------|
| agent_id 字段名错误 | ✅ 已修复 | 修改前端代码使用 `agent_id \|\| id` |
| 质押不足 | ✅ 已修复 | 为用户钱包添加 500 VIBE 质押 |

---

## 问题1: 发布需求报错 422 - agent_id 字段缺失

### 错误信息
```json
{
    "detail": [{
        "type": "missing",
        "loc": ["body", "agent_id"],
        "msg": "Field required"
    }]
}
```

### 根本原因

**前端代码问题** (`PublishDemand.tsx` line 93-94):
```typescript
const agentId = agents[0].id  // ← 使用错误的字段名
await createDemand({
    agent_id: agentId,  // ← agentId 是 undefined
    ...
})
```

**后端返回数据格式**:
- `/api/agents` 返回的 agent 对象使用 `agent_id` 作为主键
- 前端错误地使用 `agents[0].id` 访问，但字段名实际是 `agent_id`
- 导致 `agentId = undefined`

### 解决方案

**方案A: 修改前端代码** (推荐)
```typescript
// PublishDemand.tsx line 93
const agentId = agents[0].agent_id  // 使用正确的字段名
```

**方案B: 修改后端Schema**
- 将 `DemandCreate` schema 中的 `agent_id` 设为可选
- 后端从认证信息中获取 agent_id（endpoint 已经这样做了）

### 修复文件
- `frontend/src/pages/PublishDemand.tsx` - line 93

---

## 问题2: 发布服务报错 403 - 质押不足 + agent_id undefined

### 错误信息
```json
{
    "error": {
        "code": "INSUFFICIENT_STAKE",
        "message": "This action requires a minimum stake of 100 VIBE. Current stake: 0 VIBE.",
        "required": 100,
        "current": 0
    }
}
```

请求URL: `/api/agents/undefined/services`

### 根本原因

**双重问题**:

1. **agent_id undefined** (同问题1)
   - 前端代码 (`PublishService.tsx` line 94):
     ```typescript
     const agentId = agents[0].id  // ← 错误字段名
     await api.post(`/agents/${agentId}/services`, ...)  // ← URL变成 /agents/undefined/services
     ```

2. **质押不足**
   - 服务发布需要最低 100 VIBE 质押
   - 当前用户/agent 的质押为 0

### 解决方案

**修复1: 修改前端代码**
```typescript
// PublishService.tsx line 94
const agentId = agents[0].agent_id  // 使用正确的字段名
```

**修复2: 确保用户有足够质押**
- 测试账号需要先进行质押操作
- 或在测试数据准备脚本中添加质押记录

### 修复文件
- `frontend/src/pages/PublishService.tsx` - line 94
- `scripts/prepare_test_data.py` - 确保 agent_wallets 表有足够的 staked_amount

---

## 后端Schema分析

### DemandCreate Schema
```python
class DemandCreate(BaseModel):
    agent_id: str  # ← 必填字段
    title: str
    description: str = ""
    ...
```

### 服务发布要求
```python
@router.post("/agents/{agent_id}/services")
async def register_agent_service(
    agent_id: str,
    service: AgentServiceCreate,
    user: Dict[str, Any] = Depends(require_stake_unified(100))  # ← 需要100 VIBE质押
):
```

---

## 修复优先级

| 优先级 | 问题 | 修复文件 | 复杂度 |
|--------|------|----------|--------|
| P0 | agent_id 字段名错误 | PublishDemand.tsx, PublishService.tsx | 低 |
| P1 | 质押不足 | 需要测试数据准备或质押操作 | 中 |

---

## 建议的修复步骤

1. **修改前端代码** - 统一使用 `agent_id` 字段名
2. **测试验证** - 确保修改后能正确获取 agent_id
3. **质押测试数据** - 为测试账号添加足够的质押金额

---

## 代码修改详情

### PublishDemand.tsx (line 93)
```diff
- const agentId = agents[0].id
+ const agentId = agents[0].agent_id
```

### PublishService.tsx (line 94)
```diff
- const agentId = agents[0].id
+ const agentId = agents[0].agent_id
```
