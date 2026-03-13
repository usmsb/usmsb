# Meta Agent Permission Control Design Document

**[English](#meta-agent-permission-control-design-document) | [中文](#meta-agent-权限控制设计文档)**

---

## 1. Overview

This document describes the permission control design of Meta Agent in multi-user environments, covering user identity authentication, resource isolation, tool execution permissions, data access control, etc. Special focus on security management of npm/npx, git and other development tools.

---

## 2. Existing Permission System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Existing Permission Control Components              │
├─────────────────────────────────────────────────────────────────┤
│  1. PermissionManager (permission/manager.py)                  │
│     - User role management (UserRole)                          │
│     - Permission check (PermissionType)                        │
│     - Tool access control                                      │
│                                                                  │
│  2. SessionManager (session/session_manager.py)                 │
│     - User session lifecycle management                         │
│     - Session isolation (one session per wallet address)       │
│                                                                  │
│  3. UserSession (session/user_session.py)                      │
│     - Workspace isolation                                      │
│     - Sandbox isolation                                        │
│     - Browser context isolation                                │
│     - Database isolation                                       │
│     - IPFS isolation                                           │
│                                                                  │
│  4. ToolRegistry (tools/registry.py)                           │
│     - requires_session flag                                    │
│     - required_permissions list                                │
│     - security_level                                           │
│                                                                  │
│  5. Security (tools/security.py)                               │
│     - ALLOWED_COMMANDS whitelist                               │
│     - SecurityLevel                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Permission Control Points

### 3.1 User Identity & Authentication

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Wallet Address Verification** | Verify user owns the wallet address | ❌ Not implemented | 🔴 High |
| **Anonymous User Restrictions** | What operations can unbound users do | ⚠️ Partially implemented | 🟡 Medium |
| **Multi-wallet Binding** | Can one user bind multiple wallets | ❌ Not implemented | 🟡 Medium |
| **Session Hijacking Prevention** | Prevent session from being accessed by others | ⚠️ Basic exists | 🟡 Medium |

### 3.2 Conversation Context Isolation

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Conversation History Access** | Users can only access their own history | ✅ Implemented | - |
| **Memory Context** | User profile/preferences only visible to owner | ⚠️ Partially implemented | 🟡 Medium |
| **Smart Recall Scope** | Recall only searches user's own memory | ⚠️ Partially implemented | 🟡 Medium |
| **Cross-user Message Injection** | Prevent message pollution to other users | ❌ Not implemented | 🔴 High |

### 3.3 Tool Execution Permissions

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Session Requirement Check** | Tools requiring session must provide one | ✅ Implemented | - |
| **Permission Check** | Check tool permissions based on PermissionType | ⚠️ Framework exists, not integrated | 🟡 Medium |
| **Blacklist Commands** | Commands outside whitelist in security.py | ⚠️ Partially implemented | 🟡 Medium |
| **Command Execution Path** | Prevent accessing other user directories | ⚠️ Basic exists | 🟡 Medium |
| **High-risk Operation Confirmation** | Delete/format operations require confirmation | ❌ Not implemented | 🔴 High |

### 3.4 Resource Quotas

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Session Count Limit** | Max sessions per user | ❌ Not implemented | 🟡 Medium |
| **API Call Frequency** | Max calls per minute | ❌ Not implemented | 🟡 Medium |
| **Code Execution Time** | Max timeout | ⚠️ Has config | 🟢 Low |
| **Memory Limit** | Max sandbox memory | ⚠️ Has config | 🟢 Low |
| **Storage Space Limit** | User workspace size | ❌ Not implemented | 🟡 Medium |
| **Bandwidth Limit** | IPFS/browser traffic | ❌ Not implemented | 🟡 Medium |

### 3.5 Sensitive Operations Control

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Delete Operations** | Delete files/database records | ❌ Not implemented | 🔴 High |
| **Format Operations** | Clear workspace/database | ❌ Not implemented | 🔴 High |
| **Network Requests** | Allowed network request scope | ⚠️ Has whitelist | 🟡 Medium |
| **External Command Execution** | Shell command execution | ⚠️ Whitelist | 🟡 Medium |
| **Sensitive Info Access** | View API Key/password | ❌ Not implemented | 🔴 High |
| **System Operations** | Modify config/restart service | ❌ Not implemented | 🔴 High |

### 3.6 Data Access Control

| Control Point | Description | Current Status | Risk Level |
|---------------|-------------|----------------|------------|
| **Vector Database** | User knowledge base isolation | ⚠️ Partially implemented | 🟡 Medium |
| **Conversation Database** | User conversation record isolation | ✅ Implemented | 🟢 Low |
| **User Profile** | User preference/settings isolation | ⚠️ Partially implemented | 🟡 Medium |
| **Experience Learning** | User learning experience isolation | ❌ Not implemented | 🟡 Medium |

### 3.7 Roles & Permission Levels

| Role | Current Permissions | Needs Additional Control |
|------|---------------------|-------------------------|
| **SUPERADMIN** | All permissions | Requires 2FA |
| **DEVELOPER** | Deploy/config permissions | Requires approval process |
| **NODE_ADMIN** | Node management permissions | Requires staking |
| **HUMAN** | Basic operation permissions | Requires wallet verification |
| **Anonymous** | Very limited permissions | Needs strict restrictions |

---

## 4. npm/npx Command Permission Control Design

### 4.1 Permission Requirements Analysis

npm/npx commands are core development tools with special characteristics:

| Characteristic | Risk | Impact |
|----------------|------|--------|
| **Network Access** | May access malicious packages | Security/privacy |
| **Disk Write** | Install packages to local directory | Space/filesystem |
| **Code Execution** | Package may contain malicious code | Server compromised |
| **Dependency Install** | May install large number of packages | DoS attack |
| **Global Install** | Affects system environment | System security |

### 4.2 Permission Scenario Levels

```
┌─────────────────────────────────────────────────────────────────┐
│              npm/npx Permission Scenario Levels                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 1: Read-only Operations (Lowest Risk)               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - npm view <package>      View package info                   │
│  - npm search <keyword>    Search packages                     │
│  - npm ls                  List installed packages             │
│  - npm outdated            Check outdated packages             │
│                                                                  │
│  Permission: Can execute without wallet, but rate limited      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 2: Local Development Operations (Medium Risk)       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - npm install <package>     Install to project               │
│  - npm run <script>          Run script                       │
│  - npx <command>             Execute npx command              │
│  - npm init                  Initialize project                │
│                                                                  │
│  Permission: Requires wallet + workspace permission            │
│  Restriction: Only within user workspace directory            │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 3: System-level Operations (High Risk)             │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - npm install -g <package>  Global install                   │
│  - npm install -g <package>  Global uninstall                 │
│  - npm config edit           Edit global config               │
│                                                                  │
│  Permission: SUPERADMIN/DEVELOPER only                        │
│  Requires:     Confirmation + operation log                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 4: Dynamic Skill Registration (Highest Risk)       │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - Wrap npx command as system Skill                           │
│  - Execute user-defined npm commands                          │
│                                                                  │
│  Permission: SUPERADMIN only                                  │
│  Requires:     Code review + sandbox execution                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Permission Control Strategy

```python
# npm/npx Permission Configuration
NPM_PERMISSION_CONFIG = {
    # 1. Basic permission requirements
    "require_wallet": True,              # Requires wallet binding
    "require_workspace": True,           # Requires workspace

    # 2. Operation restrictions
    "allowed_operations": {
        # Public operations (no wallet required)
        "public": ["view", "search", "ls", "outdated", "info"],
        # Operations requiring wallet
        "wallet": ["install", "uninstall", "run", "init", "test", "build"],
        # Operations requiring admin
        "admin": ["install -g", "uninstall -g", "config edit"],
    },

    # 3. Workspace restrictions
    "workspace_restriction": {
        "enabled": True,
        "allowed_paths": ["$WORKSPACE", "$TEMP"],  # User workspace
        "blocked_paths": ["/", "/etc", "/usr", "/var"],
    },

    # 4. Resource limits
    "resource_limits": {
        "max_install_size_mb": 500,          # Max 500MB per install
        "max_total_packages": 1000,           # Max packages
        "max_daily_installs": 50,             # Max daily installs
        "command_timeout": 300,               # Timeout
    },

    # 5. Security checks
    "security_checks": {
        "scan_packages": True,                # Scan before install
        "block_known_malicious": True,        # Block known malicious
        "sandbox_execution": True,            # Sandbox execution
    },
}
```

### 4.4 Permission Matrix

| Operation | Anonymous | HUMAN | DEVELOPER | SUPERADMIN |
|-----------|-----------|-------|-----------|------------|
| npm view | ✅ (rate limited) | ✅ | ✅ | ✅ |
| npm search | ✅ (rate limited) | ✅ | ✅ | ✅ |
| npm install | ❌ | ✅ (workspace only) | ✅ | ✅ |
| npm run | ❌ | ✅ (workspace only) | ✅ | ✅ |
| npx | ❌ | ✅ (whitelist) | ✅ | ✅ |
| npm install -g | ❌ | ❌ | ✅ | ✅ |
| Register as Skill | ❌ | ❌ | ❌ | ✅ |

---

## 5. git Command Permission Control Design

### 5.1 Permission Requirements Analysis

git commands involve version control with special characteristics:

| Characteristic | Risk | Impact |
|----------------|------|--------|
| **Code Repository Access** | May clone malicious repository | Security/privacy |
| **Remote Operations** | push/pull to remote | Data leakage/overwrite |
| **Credential Management** | Involves SSH/GitHub tokens | Credential leakage |
| **History Operations** | May view sensitive commits | Information leakage |

### 5.2 Permission Scenario Levels

```
┌─────────────────────────────────────────────────────────────────┐
│              git Permission Scenario Levels                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 1: Local Read-only Operations (Lowest Risk)          │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                       │
│  - git status           View status                             │
│  - git log              View log                               │
│  - git diff             View diff                              │
│  - git show             View commit                            │
│  - git branch           View branches                          │
│                                                                  │
│  Permission: Requires workspace permission                     │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 2: Local Write Operations (Medium Risk)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - git init                Initialize repository               │
│  - git add                 Stage files                         │
│  - git commit              Commit changes                      │
│  - git checkout            Checkout branch/file                │
│  - git branch (create)     Create branch                      │
│                                                                  │
│  Permission: Requires wallet + workspace write permission       │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 3: Remote Operations (High Risk)                    │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - git clone           Clone repository                        │
│  - git fetch           Fetch remote updates                    │
│  - git pull            Pull remote updates                    │
│  - git push                                                     │
│  - git remote          Manage remote repositories              │
│                                                                  │
│  Permission: Requires wallet + remote push credential verification + network whitelist
│  Restriction: Only specific remote repositories allowed        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Scenario 4: Dangerous Operations (Highest Risk)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                     │
│  - git reset --hard     Hard reset                             │
│  - git push --force     Force push                            │
│  - git filter-branch   History rewrite                        │
│  - git rm --cached     Remove from index                      │
│                                                                  │
│  Permission: Requires confirmation + audit log                 │
│  Requires:     Pre-operation prompt + backup                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Permission Control Strategy

```python
# git Permission Configuration
GIT_PERMISSION_CONFIG = {
    # 1. Basic permission requirements
    "require_wallet": True,              # Requires wallet binding
    "require_workspace": True,           # Requires workspace

    # 2. Operation restrictions
    "allowed_operations": {
        # Workspace operations (requires wallet)
        "workspace": [
            "status", "log", "diff", "show", "branch",
            "add", "commit", "checkout", "switch", "merge",
            "stash", "stash pop", "init"
        ],
        # Remote operations (requires extra verification)
        "remote": ["clone", "fetch", "pull", "push", "remote"],
        # Dangerous operations (requires confirmation)
        "dangerous": [
            "reset --hard", "reset --mixed",
            "push --force", "filter-branch"
        ],
    },

    # 3. Remote repository whitelist
    "remote_whitelist": {
        "enabled": True,
        "allowed_domains": [
            "github.com",
            "gitlab.com",
            "bitbucket.org",
        ],
        "blocked_patterns": [
            "*internal-secret*",
            "*credentials*",
        ],
    },

    # 4. Credential handling
    "credential_handling": {
        "store_locally": False,           # Don't store locally
        "use_agent": True,                # Use ssh-agent
        "require_explicit": True,          # Requires explicit each time
    },

    # 5. Network restrictions
    "network_restrictions": {
        "allowed_protocols": ["https", "ssh"],
        "blocked_ports": [22],            # Limit non-standard SSH
        "rate_limit": {
            "push_per_hour": 10,
            "clone_per_day": 20,
        },
    },
}
```

### 5.4 Permission Matrix

| Operation | Anonymous | HUMAN | DEVELOPER | SUPERADMIN |
|-----------|-----------|-------|-----------|------------|
| git status | ❌ | ✅ | ✅ | ✅ |
| git log | ❌ | ✅ | ✅ | ✅ |
| git diff | ❌ | ✅ | ✅ | ✅ |
| git add | ❌ | ✅ | ✅ | ✅ |
| git commit | ❌ | ✅ | ✅ | ✅ |
| git checkout | ❌ | ✅ | ✅ | ✅ |
| git init | ❌ | ✅ (workspace) | ✅ | ✅ |
| git clone | ❌ | ✅ (whitelist) | ✅ | ✅ |
| git pull | ❌ | ✅ (whitelist) | ✅ | ✅ |
| git push | ❌ | ❌ | ✅ (whitelist) | ✅ |
| git reset --hard | ❌ | ❌ | ⚠️ Confirm | ✅ |
| git push --force | ❌ | ❌ | ❌ | ⚠️ Confirm |

---

## 6. Development Tools Permission Summary

### 6.1 npm vs git Permission Comparison

| Dimension | npm/npx | git |
|-----------|---------|-----|
| **Core Risk** | Malicious packages/code execution | Code leakage/remote overwrite |
| **Network Dependency** | High (needs npm registry) | Medium (optional offline) |
| **Storage Impact** | Large (install many packages) | Small (only repository) |
| **Permission Required** | Workspace + wallet | Workspace + wallet |
| **Dangerous Operations** | Global install | Force push/reset |
| **Most Used** | install, run | status, log, add, commit |

### 6.2 Unified Permission Model

```
┌─────────────────────────────────────────────────────────────────┐
│           Unified Permission Model for Development Tools         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Authentication Layer                                        │
│     ├── Wallet binding verification                             │
│     ├── Session Token verification                              │
│     └── Anonymous user basic quota                             │
│                                                                  │
│  2. Authorization Layer                                         │
│     ├── Role permissions (ROLE_PERMISSIONS)                    │
│     ├── Operation permissions (TOOL_PERMISSIONS)               │
│     └── Resource permissions (workspace/sandbox)               │
│                                                                  │
│  3. Access Control Layer                                        │
│     ├── Path restrictions (whitelist/blacklist)                 │
│     ├── Network restrictions (domain/protocol whitelist)       │
│     └── Credential management (keys/tokens)                    │
│                                                                  │
│  4. Quota Layer                                                 │
│     ├── Rate limits (per minute/hour)                          │
│     ├── Resource limits (memory/disk/time)                     │
│     └── Quota limits (operation count/size)                    │
│                                                                  │
│  5. Audit Layer                                                 │
│     ├── Operation logs (who, when, where)                      │
│     ├── Change tracking (version/content)                       │
│     └── Anomaly detection (unusual patterns/frequent errors)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Risks from Missing Permission Control

| Risk Type | Scenario Description | Impact | Related Tools |
|-----------|---------------------|--------|---------------|
| **Data Leakage** | User A accesses User B's workspace | Privacy leak | npm, git |
| **Resource Exhaustion** | Unlimited anonymous calls cause service unavailable | DoS attack | npm |
| **Privilege Escalation** | Regular user gains admin via vulnerability | System compromised | npm |
| **Session Hijacking** | Attacker gets other user's session | Impersonation | All |
| **Command Injection** | Execute dangerous system commands via tools | Server hacked | npm, git |
| **Malicious Code** | Install npm package with malicious code | Server compromised | npm |
| **Repository Overwrite** | Force push to others' repository | Code loss | git |
| **Credential Leakage** | GitHub Token obtained by other users | Account stolen | git |

---

## 8. Recommended Implementation Priority

### 8.1 High Priority (P0 - Security Vulnerabilities)

| # | Function | Description | Related Tools |
|---|----------|-------------|---------------|
| 1 | Workspace path isolation | Prevent ../ escape | npm, git |
| 2 | npm global install restriction | Prevent system compromise | npm |
| 3 | git force push restriction | Prevent repository destruction | git |
| 4 | Credential isolation | Prevent credential leakage | git |
| 5 | Anonymous user strict restrictions | Prevent resource exhaustion | npm, git |

### 8.2 Medium Priority (P1 - Feature Completion)

| # | Function | Description | Related Tools |
|---|----------|-------------|---------------|
| 6 | Permission system integration | Integrate PermissionManager into tool execution | npm, git |
| 7 | Operation audit logs | Log all sensitive operations | npm, git |
| 8 | Network domain whitelist | Limit accessible remote repositories | npm, git |
| 9 | Resource quota limits | Limit disk/memory/frequency | npm |
| 10 | Operation confirmation mechanism | Secondary confirmation for dangerous ops | npm, git |

### 8.3 Low Priority (P2 - Experience Optimization)

| # | Function | Description |
|---|----------|-------------|
| 11 | Permission application process | Users can apply for higher permissions |
| 12 | Operation preview | Show impact before dangerous operations |
| 13 | Batch authorization | Batch manage user permissions |
| 14 | Permission usage report | Show permission usage |

---

## 9. Next Action Plan

### 9.1 Immediate Execution

1. **Improve npm/npx permission configuration**
   - Add `NPM_OPERATION` permission type in `permission/models.py`
   - Implement workspace path check
   - Restrict global installs

2. **Improve git permission configuration**
   - Add `GIT_OPERATION` permission type in `permission/models.py`
   - Implement remote repository whitelist
   - Restrict dangerous operations

3. **Integrate permission checks into tool execution**
   - Add permission validation in `ToolRegistry.execute()`
   - Implement role-based tool filtering

### 9.2 Subsequent Iterations

1. Implement complete audit log system
2. Implement resource quota limits
3. Implement operation confirmation mechanism
4. Improve anonymous user restrictions

---

## 10. Related Files

- `permission/manager.py` - Permission manager
- `permission/models.py` - Permission model definitions
- `session/session_manager.py` - Session manager
- `session/user_session.py` - User session
- `tools/registry.py` - Tool registry
- `tools/security.py` - Security checks
- `core/skills/npm_skill.py` - npm skill
- `core/skills/git_skill.py` - git skill

---

*Document version: 1.0*
*Created: 2026-02-26*

<details>
<summary><h2>中文翻译</h2></summary>

# Meta Agent 权限控制设计文档

## 一、概述

本文档详细描述 Meta Agent 在多用户环境下的权限控制设计，涵盖用户身份认证、资源隔离、工具执行权限、数据访问控制等方面。特别关注 npm/npx、git 等开发工具的安全管控。

---

## 二、现有权限系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    现有权限控制组件                               │
├─────────────────────────────────────────────────────────────────┤
│  1. PermissionManager (permission/manager.py)                   │
│     - 用户角色管理 (UserRole)                                    │
│     - 权限校验 (PermissionType)                                  │
│     - 工具访问控制                                               │
│                                                                  │
│  2. SessionManager (session/session_manager.py)                 │
│     - 用户会话生命周期管理                                        │
│     - 会话隔离 (每个钱包地址一个会话)                             │
│                                                                  │
│  3. UserSession (session/user_session.py)                       │
│     - 工作空间隔离 (workspace)                                   │
│     - 沙箱隔离 (sandbox)                                        │
│     - 浏览器隔离 (browser_context)                               │
│     - 数据库隔离 (db)                                            │
│     - IPFS 隔离 (ipfs_client)                                   │
│                                                                  │
│  4. ToolRegistry (tools/registry.py)                           │
│     - requires_session 标志                                     │
│     - required_permissions 列表                                  │
│     - security_level 等级                                        │
│                                                                  │
│  5. Security (tools/security.py)                                │
│     - ALLOWED_COMMANDS 白名单                                    │
│     - SecurityLevel 等级                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、需要控制权限的地方详细清单

### 3.1 用户身份与认证

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **钱包地址验证** | 验证用户是否持有该钱包地址 | ❌ 未实现 | 🔴 高 |
| **匿名用户限制** | 未绑定钱包的用户可以做哪些操作 | ⚠️ 部分实现 | 🟡 中 |
| **多钱包绑定** | 一个用户能否绑定多个钱包 | ❌ 未实现 | 🟡 中 |
| **会话劫持防护** | 防止会话被其他用户获取 | ⚠️ 有基础 | 🟡 中 |

### 3.2 对话上下文隔离

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **对话历史访问** | 用户只能访问自己的对话历史 | ✅ 已实现 | - |
| **记忆上下文** | 用户画像/偏好只对所属用户可见 | ⚠️ 部分实现 | 🟡 中 |
| **智能召回范围** | 召回时只检索用户自己的记忆 | ⚠️ 部分实现 | 🟡 中 |
| **跨用户消息注入** | 防止用户消息污染其他用户上下文 | ❌ 未实现 | 🔴 高 |

### 3.3 工具执行权限

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **Session 需求检查** | 工具需要 session 时必须提供 | ✅ 已实现 | - |
| **权限校验** | 基于 PermissionType 检查工具权限 | ⚠️ 有框架未集成 | 🟡 中 |
| **黑名单命令** | security.py 中白名单外的命令 | ⚠️ 部分实现 | 🟡 中 |
| **命令执行路径** | 防止访问其他用户目录 | ⚠️ 有基础 | 🟡 中 |
| **高危操作确认** | 删除/格式化等操作需确认 | ❌ 未实现 | 🔴 高 |

**按工具分类的权限要求**：

| 工具类别 | 示例工具 | 隔离需求 | 权限需求 |
|----------|----------|----------|----------|
| **用户专属** | read_file, write_file, execute_python, browser_* | ✅ UserSession | 需权限 |
| **全局操作** | web_search, health_check | ❌ 无需session | 公开 |
| **区块链** | stake, vote, get_balance | ✅ 需钱包验证 | 需签名 |
| **开发工具** | npm_executor, git_executor | ✅ UserSession | 需权限 |

### 3.4 资源使用配额

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **会话数量限制** | 单用户最大会话数 | ❌ 未实现 | 🟡 中 |
| **API 调用频率** | 每分钟最大调用次数 | ❌ 未实现 | 🟡 中 |
| **代码执行时间** | 最大超时限制 | ⚠️ 有配置 | 🟢 低 |
| **内存使用限制** | 沙箱最大内存 | ⚠️ 有配置 | 🟢 低 |
| **存储空间限制** | 用户工作空间大小 | ❌ 未实现 | 🟡 中 |
| **带宽限制** | IPFS/浏览器流量 | ❌ 未实现 | 🟡 中 |

### 3.5 敏感操作控制

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **删除操作** | 删除文件/数据库记录 | ❌ 未实现 | 🔴 高 |
| **格式化操作** | 清空工作空间/数据库 | ❌ 未实现 | 🔴 高 |
| **网络请求** | 允许发送的网络请求范围 | ⚠️ 有白名单 | 🟡 中 |
| **外部命令执行** | shell 命令执行 | ⚠️ 白名单 | 🟡 中 |
| **敏感信息访问** | API Key/密码查看 | ❌ 未实现 | 🔴 高 |
| **系统操作** | 修改配置/重启服务 | ❌ 未实现 | 🔴 高 |

### 3.6 数据访问控制

| 权限控制点 | 说明 | 当前状态 | 风险等级 |
|------------|------|----------|----------|
| **向量数据库** | 用户知识库隔离 | ⚠️ 部分实现 | 🟡 中 |
| **对话数据库** | 用户对话记录隔离 | ✅ 已实现 | 🟢 低 |
| **用户画像** | 用户偏好/设置隔离 | ⚠️ 部分实现 | 🟡 中 |
| **体验学习** | 用户学习经验隔离 | ❌ 未实现 | 🟡 中 |

### 3.7 角色与权限级别

| 角色 | 当前权限 | 需要额外控制 |
|------|----------|--------------|
| **SUPERADMIN** | 所有权限 | 需二次验证 |
| **DEVELOPER** | 部署/配置权限 | 需审批流程 |
| **NODE_ADMIN** | 节点管理权限 | 需质押要求 |
| **HUMAN** | 基本操作权限 | 需钱包验证 |
| **匿名用户** | 极有限权限 | 需严格限制 |

---

## 四、npm/npx 命令权限控制设计

### 4.1 权限需求分析

npm/npx 命令是开发环境的核心工具，具有以下特殊性：

| 特性 | 风险 | 影响 |
|------|------|------|
| **网络访问** | 可能访问恶意包 | 安全/隐私 |
| **磁盘写入** | 安装包到本地目录 | 空间占用/文件系统 |
| **代码执行** | 包可能含恶意代码 | 服务器被控 |
| **依赖安装** | 可能安装大量包 | DoS攻击 |
| **全局安装** | 影响系统环境 | 系统安全 |

### 4.2 权限场景分级

```
┌─────────────────────────────────────────────────────────────────┐
│                    npm/npx 权限场景分级                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 1: 只读操作 (最低风险)                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - npm view <package>      查看包信息                            │
│  - npm search <keyword>    搜索包                                │
│  - npm ls                  列出已安装包                          │
│  - npm outdated            检查过期包                            │
│                                                                  │
│  权限要求: 无钱包也可执行，但限制频率                              │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 2: 本地开发操作 (中等风险)                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - npm install <package>     安装到项目                          │
│  - npm run <script>          运行脚本                            │
│  - npx <command>             执行 npx 命令                       │
│  - npm init                  初始化项目                         │
│                                                                  │
│  权限要求: 需钱包绑定 + 工作空间权限                              │
│  限制:     仅限用户工作空间目录内                                 │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 3: 系统级操作 (高风险)                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - npm install -g <package>  全局安装                            │
│  - npm install -g <package>  全局卸载                            │
│  - npm config edit           修改全局配置                        │
│                                                                  │
│  权限要求: 仅 SUPERADMIN/DEVELOPER                               │
│  需要:     二次确认 + 操作日志                                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 4: 动态 Skill 注册 (最高风险)                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - 将 npx 命令封装为系统 Skill                                   │
│  - 执行用户定义的 npm 命令                                        │
│                                                                  │
│  权限要求: 仅 SUPERADMIN                                         │
│  需要:     代码审查 + 沙箱执行                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 权限控制策略

```python
# npm/npx 权限配置
NPM_PERMISSION_CONFIG = {
    # 1. 基本权限要求
    "require_wallet": True,              # 需要绑定钱包
    "require_workspace": True,           # 需要工作空间

    # 2. 操作限制
    "allowed_operations": {
        # 公开操作（无需钱包）
        "public": ["view", "search", "ls", "outdated", "info"],
        # 需要钱包的操作
        "wallet": ["install", "uninstall", "run", "init", "test", "build"],
        # 需要高级权限的操作
        "admin": ["install -g", "uninstall -g", "config edit"],
    },

    # 3. 工作空间限制
    "workspace_restriction": {
        "enabled": True,
        "allowed_paths": ["$WORKSPACE", "$TEMP"],  # 用户工作空间
        "blocked_paths": ["/", "/etc", "/usr", "/var"],
    },

    # 4. 资源限制
    "resource_limits": {
        "max_install_size_mb": 500,          # 单次安装最大500MB
        "max_total_packages": 1000,           # 最大包数量
        "max_daily_installs": 50,             # 每日最大安装次数
        "command_timeout": 300,               # 超时时间
    },

    # 5. 安全检查
    "security_checks": {
        "scan_packages": True,                # 安装前扫描
        "block_known_malicious": True,        # 阻断已知恶意包
        "sandbox_execution": True,            # 沙箱执行
    },
}
```

### 4.4 权限矩阵

| 操作 | 匿名用户 | HUMAN | DEVELOPER | SUPERADMIN |
|------|----------|-------|-----------|------------|
| npm view | ✅ (限流) | ✅ | ✅ | ✅ |
| npm search | ✅ (限流) | ✅ | ✅ | ✅ |
| npm install | ❌ | ✅ (仅workspace) | ✅ | ✅ |
| npm run | ❌ | ✅ (仅workspace) | ✅ | ✅ |
| npx | ❌ | ✅ (白名单) | ✅ | ✅ |
| npm install -g | ❌ | ❌ | ✅ | ✅ |
| 注册为Skill | ❌ | ❌ | ❌ | ✅ |

---

## 五、git 命令权限控制设计

### 5.1 权限需求分析

git 命令涉及版本控制，具有以下特殊性：

| 特性 | 风险 | 影响 |
|------|------|------|
| **代码仓库访问** | 可能克隆恶意仓库 | 安全/隐私 |
| **远程操作** | push/pull 到远程 | 数据泄露/覆盖 |
| **凭据管理** | 涉及 SSH/GitHub 令牌 | 凭据泄露 |
| **历史操作** | 可能查看敏感提交 | 信息泄露 |

### 5.2 权限场景分级

```
┌─────────────────────────────────────────────────────────────────┐
│                    git 权限场景分级                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 1: 本地只读操作 (最低风险)                                  │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - git status           查看状态                                 │
│  - git log              查看日志                                 │
│  - git diff             查看差异                                 │
│  - git show             查看提交                                 │
│  - git branch           查看分支                                 │
│                                                                  │
│  权限要求: 需工作空间权限                                        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 2: 本地写入操作 (中等风险)                                 │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - git init                初始化仓库                            │
│  - git add                 暂存文件                             │
│  - git commit              提交更改                             │
│  - git checkout            检出分支/文件                         │
│  - git branch (create)     创建分支                             │
│                                                                  │
│  权限要求: 需钱包绑定 + 工作空间写入权限                          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 3: 远程操作 (高风险)                                      │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - git clone           克隆仓库                                  │
│  - git fetch           获取远程更新                               │
│  - git pull            拉取远程更新                               │
│  - git push                                                       │
│  - git remote          管理远程仓库                               │
│                                                                  │
│  权限要求: 需钱包绑定 + 推送到远程凭据验证 + 网络白名单           │
│  限制:     仅允许特定远程仓库                                    │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  场景 4: 危险操作 (最高风险)                                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                        │
│  - git reset --hard     硬重置                                   │
│  - git push --force     强制推送                                 │
│  - git filter-branch   历史重写                                  │
│  - git rm --cached     从索引删除                                 │
│                                                                  │
│  权限要求: 需确认 + 审计日志                                     │
│  需要:     操作前提示 + 备份                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 权限控制策略

```python
# git 权限配置
GIT_PERMISSION_CONFIG = {
    # 1. 基本权限要求
    "require_wallet": True,              # 需要绑定钱包
    "require_workspace": True,           # 需要工作空间

    # 2. 操作限制
    "allowed_operations": {
        # 工作空间内操作（需钱包）
        "workspace": [
            "status", "log", "diff", "show", "branch",
            "add", "commit", "checkout", "switch", "merge",
            "stash", "stash pop", "init"
        ],
        # 远程操作（需额外验证）
        "remote": ["clone", "fetch", "pull", "push", "remote"],
        # 危险操作（需确认）
        "dangerous": [
            "reset --hard", "reset --mixed",
            "push --force", "filter-branch"
        ],
    },

    # 3. 远程仓库白名单
    "remote_whitelist": {
        "enabled": True,
        "allowed_domains": [
            "github.com",
            "gitlab.com",
            "bitbucket.org",
        ],
        "blocked_patterns": [
            "*internal-secret*",
            "*credentials*",
        ],
    },

    # 4. 凭据管理
    "credential_handling": {
        "store_locally": False,           # 不本地存储凭据
        "use_agent": True,                # 使用 ssh-agent
        "require_explicit": True,          # 每次需显式提供
    },

    # 5. 网络限制
    "network_restrictions": {
        "allowed_protocols": ["https", "ssh"],
        "blocked_ports": [22],            # 限制非标准 SSH
        "rate_limit": {
            "push_per_hour": 10,
            "clone_per_day": 20,
        },
    },
}
```

### 5.4 权限矩阵

| 操作 | 匿名用户 | HUMAN | DEVELOPER | SUPERADMIN |
|------|----------|-------|-----------|------------|
| git status | ❌ | ✅ | ✅ | ✅ |
| git log | ❌ | ✅ | ✅ | ✅ |
| git diff | ❌ | ✅ | ✅ | ✅ |
| git add | ❌ | ✅ | ✅ | ✅ |
| git commit | ❌ | ✅ | ✅ | ✅ |
| git checkout | ❌ | ✅ | ✅ | ✅ |
| git init | ❌ | ✅ (workspace) | ✅ | ✅ |
| git clone | ❌ | ✅ (白名单) | ✅ | ✅ |
| git pull | ❌ | ✅ (白名单) | ✅ | ✅ |
| git push | ❌ | ❌ | ✅ (白名单) | ✅ |
| git reset --hard | ❌ | ❌ | ⚠️ 确认 | ✅ |
| git push --force | ❌ | ❌ | ❌ | ⚠️ 确认 |

---

## 六、开发工具权限总结对比

### 6.1 npm vs git 权限对比

| 维度 | npm/npx | git |
|------|---------|-----|
| **核心风险** | 恶意包/代码执行 | 代码泄露/远程覆盖 |
| **网络依赖** | 高 (需访问 npm registry) | 中 (可选离线) |
| **存储影响** | 大 (安装大量包) | 小 (仅仓库) |
| **权限要求** | 工作空间 + 钱包 | 工作空间 + 钱包 |
| **危险操作** | 全局安装 | 强制推送/重置 |
| **最常用** | install, run | status, log, add, commit |

### 6.2 统一权限模型

```
┌─────────────────────────────────────────────────────────────────┐
│                    开发工具统一权限模型                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 身份层 (Authentication)                                     │
│     ├── 钱包绑定验证                                             │
│     ├── Session Token 验证                                       │
│     └── 匿名用户基础配额                                        │
│                                                                  │
│  2. 授权层 (Authorization)                                      │
│     ├── 角色权限 (ROLE_PERMISSIONS)                            │
│     ├── 操作权限 (TOOL_PERMISSIONS)                            │
│     └── 资源权限 (工作空间/沙箱)                                │
│                                                                  │
│  3. 访问层 (Access Control)                                     │
│     ├── 路径限制 (白名单/黑名单)                                │
│     ├── 网络限制 (域名/协议白名单)                               │
│     └── 凭据管理 (密钥/Token)                                  │
│                                                                  │
│  4. 配额层 (Quota)                                              │
│     ├── 频率限制 (每分钟/每小时)                                │
│     ├── 资源限制 (内存/磁盘/时间)                              │
│     └── 配额限制 (操作次数/大小)                                │
│                                                                  │
│  5. 审计层 (Audit)                                              │
│     ├── 操作日志 (谁、何时、何地)                               │
│     ├── 变更追踪 (版本/内容)                                   │
│     └── 异常检测 (异常模式/频繁错误)                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 七、权限控制缺失导致的风险

| 风险类型 | 场景描述 | 影响 | 关联工具 |
|----------|----------|------|----------|
| **数据泄露** | 用户A通过某些操作访问到用户B的工作空间 | 用户隐私泄露 | npm, git |
| **资源耗尽** | 匿名用户无限调用导致服务不可用 | DoS攻击 | npm |
| **权限提升** | 普通用户通过漏洞获得管理员权限 | 系统被控制 | npm |
| **会话劫持** | 攻击者获取其他用户的session | 身份冒充 | 所有 |
| **命令注入** | 通过工具执行危险系统命令 | 服务器被黑 | npm, git |
| **恶意代码** | 安装包含恶意代码的 npm 包 | 服务器被控 | npm |
| **仓库覆盖** | 强制推送到他人仓库 | 代码丢失 | git |
| **凭据泄露** | GitHub Token 被其他用户获取 | 账户被盗 | git |

---

## 八、建议实现的优先级

### 8.1 高优先级 (P0 - 安全漏洞)

| # | 功能 | 说明 | 关联工具 |
|---|------|------|----------|
| 1 | 工作空间路径隔离 | 防止 ../ 逃逸 | npm, git |
| 2 | npm 全局安装限制 | 防止系统被控 | npm |
| 3 | git 强制推送限制 | 防止仓库被破坏 | git |
| 4 | 凭据隔离 | 防止凭据泄露 | git |
| 5 | 匿名用户严格限制 | 防止资源耗尽 | npm, git |

### 8.2 中优先级 (P1 - 功能完善)

| # | 功能 | 说明 | 关联工具 |
|---|------|------|----------|
| 6 | 权限系统集成 | 将 PermissionManager 集成到工具执行 | npm, git |
| 7 | 操作审计日志 | 记录所有敏感操作 | npm, git |
| 8 | 网络域名白名单 | 限制可访问的远程仓库 | npm, git |
| 9 | 资源配额限制 | 限制磁盘/内存/频率 | npm |
| 10 | 操作确认机制 | 危险操作二次确认 | npm, git |

### 8.3 低优先级 (P2 - 体验优化)

| # | 功能 | 说明 |
|---|------|------|
| 11 | 权限申请流程 | 用户可申请更高权限 |
| 12 | 操作预览 | 危险操作前显示影响 |
| 13 | 批量授权 | 批量管理用户权限 |
| 14 | 权限使用报告 | 显示权限使用情况 |

---

## 九、下一步行动计划

### 9.1 立即执行

1. **完善 npm/npx 权限配置**
   - 在 `permission/models.py` 添加 `NPM_OPERATION` 权限类型
   - 实现工作空间路径检查
   - 限制全局安装

2. **完善 git 权限配置**
   - 在 `permission/models.py` 添加 `GIT_OPERATION` 权限类型
   - 实现远程仓库白名单
   - 限制危险操作

3. **集成权限检查到工具执行**
   - 在 `ToolRegistry.execute()` 添加权限校验
   - 实现基于角色的工具过滤

### 9.2 后续迭代

1. 实现完整的审计日志系统
2. 实现资源配额限制
3. 实现操作确认机制
4. 完善匿名用户限制

---

## 十、相关文件

- `permission/manager.py` - 权限管理器
- `permission/models.py` - 权限模型定义
- `session/session_manager.py` - 会话管理器
- `session/user_session.py` - 用户会话
- `tools/registry.py` - 工具注册表
- `tools/security.py` - 安全检查
- `core/skills/npm_skill.py` - npm 技能
- `core/skills/git_skill.py` - git 技能

---

*文档版本: 1.0*
*创建日期: 2026-02-26*

</details>
