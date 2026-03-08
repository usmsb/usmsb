# 前端测试凭据

> 生成时间: 2026-03-08

---

## 钱包用户 (SIWE 登录)

### 当前登录用户
- **钱包地址**: `0x382B71e8b425CFAaD1B1C6D970481F440458Abf8`
- **Agent ID**: `human_user-1772354280.238014`
- **质押金额**: 500 VIBE ✅ (足够发布服务)
- **余额**: 2000 VIBE

---

## API Key 测试账号

### 前端测试专用 Agent

| Agent ID | Name | Stake | 用途 | API Key |
|----------|------|-------|------|---------|
| frontend-test-user | FrontendTestUser | 500 | 通用测试 | `usmsb_bd09e11696f02911_69ad7f8b` |
| frontend-demand-test | FrontendDemandTest | 200 | 需求发布测试 | `usmsb_6dfa3f323f4958c6_69ad7f8b` |
| frontend-service-test | FrontendServiceTest | 500 | 服务发布测试 | `usmsb_acb46d0beb2a1154_69ad7f8b` |

### 其他测试 Agent

| Agent ID | Name | Stake | API Key |
|----------|------|-------|---------|
| match-supplier-001 | DataAnalyst | 500 | `usmsb_31392549cbb15154_69ad7f8b` |
| match-demand-001 | ProjectOwner | 200 | `usmsb_3e83f42a83003558_69ad7f8b` |
| network-ml-001 | MLExpert | 1000 | `usmsb_8e9079e6f65d8e12_69ad7f8b` |
| collab-coordinator-001 | ProjectCoordinator | 500 | `usmsb_8c30831ffa573424_69ad7f8b` |
| sim-agent-001 | SimulationAgent | 200 | `usmsb_74a183dd5b958f88_69ad7f8b` |

---

## 前端修复已应用

### 修改的文件
1. `frontend/src/pages/PublishDemand.tsx` - line 93
   - 修复: `agents[0].id` → `agents[0].agent_id || agents[0].id`

2. `frontend/src/pages/PublishService.tsx` - line 94
   - 修复: `agents[0].id` → `agents[0].agent_id || agents[0].id`

### 使用说明

1. **重新构建前端**
   ```bash
   cd frontend
   npm run build
   ```

2. **测试需求发布**
   - 访问 http://localhost:3000/app/publish/demand
   - 使用钱包登录或 API Key
   - 填写表单并提交

3. **测试服务发布**
   - 访问 http://localhost:3000/app/publish/service
   - 确保登录的 Agent 有 100+ VIBE 质押
   - 填写表单并提交

---

## 质押要求

| 操作 | 最低质押 |
|------|----------|
| 发布需求 | 无要求 |
| 发布服务 | 100 VIBE |
| 执行工作流 | 100 VIBE |
| 创建协作 | 100 VIBE (coordinator) |

---

## API Key 使用方式

在请求头中添加:
```
X-Agent-ID: frontend-test-user
X-API-Key: usmsb_bd09e11696f02911_69ad7f8b
```
