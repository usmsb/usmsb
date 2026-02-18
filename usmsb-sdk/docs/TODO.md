# AI Civilization Platform - 待办事项清单

> 最后更新: 2026-02-15

## P0 - 阻塞问题 (必须立即修复)

### Sprint 1 - 钱包认证系统修复
- [x] **方案B**: 使用wagmi原生hooks创建自定义连接按钮 ✅ 2026-02-15
  - 创建 `ConnectButton.tsx` 组件
  - 更新 `Onboarding.tsx` 使用自定义按钮
  - 更新 `Header.tsx` 使用自定义按钮
  - 移除所有 `<w3m-button />` 引用
- [ ] **方案A**: 集成完整Web3Modal (未来迭代)
  - 需要安装 `@web3modal/wagmi` 包
  - 需要 WalletConnect Project ID
  - 提供完整的多钱包支持 (MetaMask, WalletConnect, Coinbase Wallet等)
  - 更好的用户体验和UI

### 生产级安全修复 (紧急) - 测试发现
- [ ] **BUG-001: 修复签名验证**: auth.py 第175-183行的签名验证被注释掉
  - 实现 `verify_siwe_signature()` 函数
  - 使用 web3.py 恢复签名地址
  - 验证地址匹配
  - **严重程度**: 任何人可绕过认证
- [ ] **BUG-002: JWT_SECRET 环境变量化**: auth.py 第39行硬编码默认值
  - 强制从环境变量读取
  - 启动时验证 JWT_SECRET 存在
  - 添加 .env.example 文件
  - **严重程度**: 生产环境密钥泄露风险

---

## P1 - 高优先级 (下一个迭代)

### 功能缺失修复 - 测试发现
- [x] **BUG-003: 环境广播API缺失** ✅ 2026-02-15
  - 创建 `environment.py` 路由
  - 在main.py中注册路由
  - 实现 `/environment/state`, `/environment/metrics`, `/environment/broadcasts` 等端点
- [x] **BUG-004: 治理API未注册** ✅ 2026-02-15
  - 创建 `governance.py` 路由
  - 实现 `/governance/proposals`, `/governance/proposals/{id}/vote` 等端点
  - 在main.py中注册路由

### Mock数据清理 (已完成) ✅ 2026-02-15
- [x] 清理前端ActiveMatching.tsx的mock数据
- [x] 清理前端NetworkExplorer.tsx的mock数据
- [x] 清理前端Governance.tsx的mock数据
- [x] 清理前端Dashboard.tsx和Analytics.tsx的mock数据
- [x] 清理后端main.py的mock返回数据 (network, learning, collaboration端点)
- [x] 所有前后端页面现在使用真实数据库数据

### 生产级基础设施改造
详见: `docs/production-upgrade-plan.md`

- [ ] **数据库迁移**: SQLite → PostgreSQL
  - 安装 asyncpg 和 sqlalchemy
  - 创建 database_postgres.py
  - 编写迁移脚本
  - 配置连接池
- [ ] **缓存系统**: 添加 Redis
  - 安装 redis[hiredis]
  - 创建 cache.py
  - 实现 NonceCache, SessionCache, TokenBlacklist
- [ ] **速率限制**: 防止暴力攻击
  - 实现 RateLimiter
  - 配置限制规则 (5次/分钟)
- [ ] **审计日志**: 安全合规
  - 创建 audit.py
  - 记录关键操作

### 前端完善
- [ ] 首页钱包连接入口完善
- [ ] Header组件钱包状态显示优化
- [ ] 错误处理和用户提示完善

### 后端完善
- [ ] 认证API单元测试
- [ ] 交易API集成测试
- [ ] 匹配引擎性能测试

---

## P2 - 中优先级 (后续迭代)

### 功能增强
- [ ] 多语言支持完善
- [ ] 暗黑模式支持
- [ ] 移动端适配优化

### 性能优化
- [ ] 前端代码分割
- [ ] API响应缓存
- [ ] WebSocket断线重连优化

---

## P3 - 低优先级 (长期规划)

### 技术债务
- [ ] TypeScript类型定义完善
- [ ] ESLint规则统一
- [ ] 代码注释补充

### 文档完善
- [ ] API文档更新
- [ ] 部署文档编写
- [ ] 用户手册编写

---

## 已完成任务

### Sprint 1-9 开发 (2026-02-15)
- [x] Sprint 1: 钱包认证系统 (后端完成，前端需修复)
- [x] Sprint 2: 供需匹配算法
- [x] Sprint 3: 交易执行流程
- [x] Sprint 4: 区块链集成 (模拟模式)
- [x] Sprint 5: 声誉系统
- [x] Sprint 6: 环境广播系统
- [x] Sprint 7: 学习系统
- [x] Sprint 8: 外部Agent协议
- [x] Sprint 9: 治理系统

---

## 问题追踪

| 问题ID | 描述 | 状态 | 优先级 | 创建时间 |
|--------|------|------|--------|----------|
| BUG-001 | `<w3m-button />` 组件未安装Web3Modal导致钱包连接失败 | 进行中 | P0 | 2026-02-15 |

---

## 技术选型备注

### Web3Modal集成 (方案A) - 待实施
```bash
# 需要安装的包
npm install @web3modal/wagmi

# 需要配置
# 1. 获取 WalletConnect Project ID: https://cloud.walletconnect.com/
# 2. 在 wagmi.ts 中初始化 createWeb3Modal
# 3. 可选: 自定义主题和配置
```

### wagmi原生方案 (方案B) - 当前实施
```typescript
// 使用 useConnect hook
import { useConnect, useAccount } from 'wagmi'

// 可用连接器: injected, metaMask
// 优点: 无额外依赖，快速实现
// 缺点: UI需自行实现，支持的钱包较少
```
