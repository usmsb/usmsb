# 超级管理员 (superadmin) 权限测试用例

## 测试目标

验证 superadmin 角色拥有全部37项权限，并能正确调用所有允许的工具。

## 测试环境

- **测试用户**: 0x382B71e8b425CFAaD1B1C6D970481F440458Abf8
- **角色**: superadmin
- **权限数量**: 37

---

## 测试用例

### 1. 平台管理权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| PLAT-01 | 平台配置读取 | platform:config | GET /api/meta-agent/tools |
| PLAT-02 | 平台健康检查 | system:health | GET /api/health |
| PLAT-03 | 系统指标获取 | system:metrics | GET /api/system/metrics |
| PLAT-04 | 日志查询 | system:logs | GET /api/system/logs |

### 2. 节点管理权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| NODE-01 | 节点状态监控 | node:monitor | GET /api/nodes/status |
| NODE-02 | 节点配置管理 | node:config | GET /api/nodes/config |
| NODE-03 | 节点启动 | node:start | POST /api/nodes/start |
| NODE-04 | 节点停止 | node:stop | POST /api/nodes/stop |

### 3. Agent管理权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| AGENT-01 | 注册Agent | agent:register | POST /api/agents/register |
| AGENT-02 | 注销Agent | agent:unregister | POST /api/agents/unregister |
| AGENT-03 | 管理Agent | agent:manage | GET /api/agents/list |
| AGENT-04 | Agent服务 | agent:service | GET /api/agents/recommend |

### 4. 钱包/区块链权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| WALLET-01 | 创建钱包 | wallet:create | POST /api/wallet/create |
| WALLET-02 | 绑定钱包 | wallet:bind | POST /api/wallet/bind |
| WALLET-03 | 质押操作 | blockchain:stake | POST /api/staking/stake |
| WALLET-04 | 投票操作 | blockchain:vote | POST /api/governance/vote |
| WALLET-05 | 治理操作 | blockchain:govern | POST /api/governance/proposal |

### 5. 数据操作权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| DATA-01 | 数据查询 | data:query | GET /api/data/query |
| DATA-02 | 数据写入 | data:write | POST /api/data/write |
| DATA-03 | 数据管理 | data:admin | POST /api/data/delete |

### 6. 对话权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| CHAT-01 | 基本对话 | chat:basic | POST /api/meta-agent/chat |
| CHAT-02 | 对话管理 | chat:admin | GET /api/meta-agent/history/{wallet} |

### 7. 环境隔离权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| ENV-01 | 工作目录访问 | workspace | GET /api/workspace/files |
| ENV-02 | 代码执行沙箱 | sandbox | POST /api/sandbox/execute |
| ENV-03 | 浏览器操作 | browser | POST /api/browser/open |
| ENV-04 | 网络访问 | network | GET /api/network/fetch |

### 8. NPM工具权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| NPM-01 | NPM公开查询 | npm:public | GET /api/npm/search |
| NPM-02 | NPM安装 | npm:install | POST /api/npm/install |
| NPM-03 | NPM运行 | npm:run | POST /api/npm/run |
| NPM-04 | NPM全局安装 | npm:global | POST /api/npm/global |
| NPM-05 | NPM危险操作 | npm:danger | POST /api/npm/dangerous |

### 9. Git工具权限测试

| 用例ID | 测试项 | 权限要求 | API端点 |
|--------|--------|----------|---------|
| GIT-01 | Git只读 | git:read | GET /api/git/read |
| GIT-02 | Git写入 | git:write | POST /api/git/write |
| GIT-03 | Git推送 | git:push | POST /api/git/push |
| GIT-04 | Git克隆 | git:clone | POST /api/git/clone |
| GIT-05 | Git强制推送 | git:force | POST /api/git/force |
| GIT-06 | Git危险操作 | git:danger | POST /api/git/dangerous |

---

## 权限验证API

通过以下API验证用户权限：

```bash
GET /api/meta-agent/user/{wallet_address}
GET /api/meta-agent/permission/check-tool/{wallet_address}/{tool_name}
GET /api/meta-agent/permission/stats
```

---

## 预期结果

1. **用户信息查询**: 返回 role=superadmin, permissions 包含全部37项
2. **权限检查**: 所有37项权限检查返回 true
3. **工具调用**: 所有 superadmin 允许的工具都能成功调用
4. **拒绝访问**: 非 superadmin 权限的工具调用应返回 403
