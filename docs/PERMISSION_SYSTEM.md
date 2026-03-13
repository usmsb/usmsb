**[English](#permission-system) | [中文](#权限系统设计文档)**

---

# Permission System Design Document

## Overview

This document describes the permission system design for USMSB Meta Agent, combining the original 21 permission types with the new environment-based permission mechanism.

---

## 1. Role System

The system defines 7 user roles:

| Role | Description | Use Case |
|------|-------------|----------|
| superadmin | Super Administrator | System highest privilege manager |
| developer | Developer | Users requiring full development capabilities |
| node_admin | Node Administrator | Users managing nodes |
| node_operator | Node Operator | Users operating nodes |
| human | Regular User | Basic user |
| ai_owner | AI Agent Owner | Users who own and manage AI Agents |
| ai_agent | AI Agent | AI Agent itself |

---

## 2. Permission Types

### 2.1 Original Permissions (21 types)

#### Platform Management (3 types)
| Permission | Description |
|------------|-------------|
| platform:admin | Platform administration |
| platform:config | Platform configuration |
| platform:deploy | Code deployment |

#### Node Management (4 types)
| Permission | Description |
|------------|-------------|
| node:start | Start node |
| node:stop | Stop node |
| node:monitor | Node monitoring |
| node:config | Node configuration |

#### Agent Management (3 types)
| Permission | Description |
|------------|-------------|
| agent:register | Register Agent |
| agent:unregister | Unregister Agent |
| agent:manage | Manage Agent |

#### Blockchain/Wallet (5 types)
| Permission | Description |
|------------|-------------|
| wallet:create | Create wallet |
| wallet:bind | Bind wallet |
| blockchain:stake | Staking |
| blockchain:vote | Voting |
| blockchain:govern | Governance |

#### Data Operations (3 types)
| Permission | Description |
|------------|-------------|
| data:query | Query data |
| data:write | Write data |
| data:admin | Data administration |

#### Conversation (2 types)
| Permission | Description |
|------------|-------------|
| chat:basic | Basic chat |
| chat:admin | Chat administration |

#### System (3 types)
| Permission | Description |
|------------|-------------|
| system:health | Health check |
| system:metrics | System metrics |
| system:logs | Log access |

#### NPM Tools (5 types)
| Permission | Description |
|------------|-------------|
| npm:public | npm view/search |
| npm:install | npm install |
| npm:run | npm run |
| npm:global | npm global install |
| npm:danger | Dangerous npm operations |

#### Git Tools (6 types)
| Permission | Description |
|------------|-------------|
| git:read | git read-only |
| git:write | git write |
| git:push | git push |
| git:clone | git clone |
| git:force | git force push |
| git:danger | Dangerous git operations |

### 2.2 New Permissions - Environment Isolation (4 types)

New permissions based on user environment isolation mechanism. These permissions can be safely relaxed for regular users under isolation protection:

| Permission | Description | Security |
|------------|-------------|----------|
| workspace | User workspace operations | User directory isolation + path validation + quota limits |
| sandbox | Code execution sandbox | Process isolation + timeout + resource limits |
| browser | Browser operations | Session isolation |
| network | Network access | Optional domain whitelist |

### 2.3 New Permissions - Agent Service (1 type)

| Permission | Description |
|------------|-------------|
| agent:service | Agent recommendation, matching and other services |

---

## 3. Role Permission Configuration

### 3.1 superadmin (Super Administrator)
Has all permissions including:
- All platform, node, agent, wallet, blockchain, data, chat, system permissions
- All environment isolation permissions (workspace, sandbox, browser, network)
- All NPM/Git permissions

### 3.2 developer (Developer)
| Permission Category | Specific Permissions |
|---------------------|----------------------|
| Platform | platform:config, platform:deploy |
| Node | node:monitor |
| Agent | agent:register, agent:manage, agent:service |
| Wallet | wallet:bind |
| Data | data:query, data:write |
| Chat | chat:basic |
| System | system:health, system:metrics, system:logs |
| Environment | workspace, sandbox, browser, network |
| NPM | npm:public, npm:install, npm:run, npm:global |
| Git | git:read, git:write, git:push, git:clone |

### 3.3 node_admin (Node Administrator)
| Permission Category | Specific Permissions |
|---------------------|----------------------|
| Node | node:start, node:stop, node:monitor, node:config |
| Agent | agent:register |
| Wallet | wallet:bind, stake, vote |
| Data | data:query, data:write |
| Chat | chat:basic |
| System | system:health, system:metrics, system:logs |
| Environment | workspace, network |
| NPM | npm:public, npm:install, npm:run |
| Git | git:read, git:write, git:clone |

### 3.4 node_operator (Node Operator)
| Permission Category | Specific Permissions |
|---------------------|----------------------|
| Node | node:monitor, node:config |
| Wallet | wallet:bind, stake, vote |
| Data | data:query |
| Chat | chat:basic |
| System | system:health, system:metrics, system:logs |
| Environment | workspace, network |
| NPM | npm:public, npm:install |
| Git | git:read |

### 3.5 human (Regular User) ⚠️ Important Update
| Permission Category | Specific Permissions | Description |
|---------------------|----------------------|-------------|
| Basic | chat:basic, data:query, system:health, wallet:bind | Basic functionality |
| Environment Isolation | workspace, sandbox, browser, network | New, can be safely used based on isolation mechanism |
| Agent Service | agent:service | New |
| NPM/Git | npm:public, npm:install, npm:run, git:read | Basic development permissions |

### 3.6 ai_owner (AI Agent Owner)
| Permission Category | Specific Permissions |
|---------------------|----------------------|
| Agent | agent:register, agent:unregister, agent:manage, agent:service |
| Wallet | wallet:bind, stake, vote |
| Data | data:query, data:write |
| Chat | chat:basic |
| System | system:health |
| Environment | workspace, network |
| NPM | npm:public, npm:install, npm:run |
| Git | git:read, git:write |

### 3.7 ai_agent (AI Agent)
| Permission Category | Specific Permissions |
|---------------------|----------------------|
| Agent | agent:register, agent:service |
| Wallet | wallet:bind |
| Data | data:query, data:write |
| Chat | chat:basic |
| System | system:health |
| Environment | workspace, sandbox, browser, network |
| NPM | npm:public |
| Git | git:read |

---

## 4. Tool Permission Mapping

### 4.1 Conversation Tools
| Tool | Permission |
|------|------------|
| general_response | chat:basic |
| search_knowledge | data:query |

### 4.2 Search Tools
| Tool | Permission |
|------|------------|
| search_web | network |
| search_files | workspace |

### 4.3 File Operations (Workspace Isolation)
| Tool | Permission |
|------|------------|
| read_file | workspace |
| write_file | workspace |
| list_directory | workspace |
| create_directory | workspace |
| copy_file | workspace |
| move_file | workspace |
| delete_file | workspace |
| get_file_info | workspace |
| search_files | workspace |

### 4.4 Code Execution (Sandbox Isolation)
| Tool | Permission |
|------|------------|
| execute_python | sandbox |
| execute_javascript | sandbox |
| execute_command | sandbox |
| run_program | sandbox |
| parse_skill_md | sandbox |
| execute_skill | sandbox |
| list_skills | sandbox |

### 4.5 Browser (Browser Isolation)
| Tool | Permission |
|------|------------|
| browser_open | browser |
| browser_click | browser |
| browser_fill | browser |
| browser_get_content | browser |
| browser_screenshot | browser |
| browser_close | browser |

### 4.6 Network Access
| Tool | Permission |
|------|------------|
| fetch_url | network |
| parse_html | network |
| download_file | network |
| get_headers | network |
| search_web | network |

### 4.7 Data Operations
| Tool | Permission |
|------|------------|
| query_db | data:query |
| analyze_data | data:query |
| generate_report | data:query |
| insert_db | data:write |
| update_db | data:write |
| delete_db | data:admin |
| upload_to_ipfs | data:write |
| download_from_ipfs | data:query |
| sync_to_ipfs | data:write |

### 4.8 Node Management
| Tool | Permission |
|------|------------|
| start_node | node:start |
| stop_node | node:stop |
| get_node_status | node:monitor |
| set_threshold | node:config |
| get_alerts | node:monitor |

### 4.9 Wallet/Blockchain
| Tool | Permission |
|------|------------|
| create_wallet | wallet:create |
| get_balance | wallet:bind |
| bind_wallet | wallet:bind |
| switch_chain | wallet:bind |
| get_chain_info | wallet:bind |
| stake | blockchain:stake |
| unstake | blockchain:stake |
| vote | blockchain:vote |
| delegate_vote | blockchain:vote |
| get_vote_power | blockchain:vote |
| list_proposals | blockchain:vote |
| submit_proposal | blockchain:govern |

### 4.10 Agent Services
| Tool | Permission |
|------|------------|
| search_agents | agent:service |
| recommend_agents | agent:service |
| get_recommendation_history | agent:service |
| rate_agent | agent:service |
| get_agent_profile | agent:service |
| get_all_agent_profiles | agent:service |
| recommend_agents_for_demand | agent:service |
| match_by_gene_capsule | agent:service |
| generate_recommendation_explanation | agent:service |
| proactively_notify_opportunity | agent:service |
| scan_opportunities | agent:service |
| auto_match_and_notify | agent:service |
| consult_agent | agent:service |
| route_message | agent:service |
| get_load_balance_status | agent:service |
| get_route_info | agent:service |
| interview_agent | agent:service |
| send_agent_message | agent:service |
| receive_agent_showcase | agent:service |
| retrieve_user_info | agent:service |
| list_user_agents | agent:manage |
| register_agent | agent:register |
| unregister_agent | agent:unregister |

### 4.11 System
| Tool | Permission |
|------|------------|
| health_check | system:health |
| get_system_health | system:health |
| get_metrics | system:metrics |
| get_system_metrics | system:metrics |
| query_logs | system:logs |

### 4.12 Platform Configuration
| Tool | Permission |
|------|------------|
| get_config | platform:config |
| update_config | platform:config |
| generate_component | platform:config |
| manage_page | platform:config |

---

## 5. Environment Isolation Mechanism

The system uses three-layer environment isolation to protect system security:

### 5.1 UserWorkspace (Workspace Directory Isolation)
- Each user has an independent workspace directory
- Path validation: prevents path traversal attacks
- Quota limits: prevents disk exhaustion
- Directory structure:
  - workspace/uploads/ - Uploaded files
  - workspace/output/ - Output files
  - workspace/temp/ - Temporary files

### 5.2 CodeSandbox (Code Execution Sandbox)
- Process isolation: code runs in isolated processes
- Timeout limits: prevents infinite loops
- Resource limits: CPU/memory limits
- Network isolation: configurable network access

### 5.3 BrowserContext (Browser Session Isolation)
- Each user has an independent browser session
- Cookie/Storage isolation
- Page isolation

---

## 6. Permission Check Process

1. When user calls a tool, system obtains user role
2. Retrieves permission list for that role from `ROLE_PERMISSIONS`
3. Gets required permissions for the tool from `TOOL_PERMISSIONS`
4. Checks if user permissions cover all tool required permissions
5. If insufficient permissions, returns permission denial message

---

## 7. Permission Configuration Examples

### 7.1 Typical Usage Scenarios for human Role

Since the human role has workspace, sandbox, browser, network permissions, they can:

✅ read_file/write files in their own workspace
✅ Execute Python/JavaScript code (in sandbox)
✅ Operate browser (in independent browser context)
✅ Access network resources
✅ Search for Agents and use Agent services

❌ Access system database
❌ Manage system configuration
❌ Start/stop nodes

---

## 8. Changelog

### 2026-03-02
- Added 4 environment isolation permissions: workspace, sandbox, browser, network
- Added 1 Agent service permission: agent:service
- Updated human role permissions, added file operations, code execution, browser operation permissions
- Updated node_operator role permissions, added workspace and network permissions
- Updated ai_owner role permissions, added more Agent service permissions
- Updated ai_agent role permissions, added complete environment isolation permissions

---

<details>
<summary><h2>中文翻译</h2></summary>

# 权限系统设计文档

## 概述

本文档描述了USMSB Meta Agent的权限系统设计，结合了原有的21种权限类型和新增的基于环境隔离的权限机制。

---

## 1. 角色体系

系统定义了7种用户角色：

| 角色 | 说明 | 适用场景 |
|------|------|---------|
| superadmin | 超级管理员 | 系统最高权限管理者 |
| developer | 开发人员 | 需要完整开发能力的用户 |
| node_admin | 节点管理员 | 管理节点的用户 |
| node_operator | 节点运营 | 运营节点的用户 |
| human | 普通用户 | 基础用户 |
| ai_owner | AI Agent主人 | 拥有和管理AI Agent的用户 |
| ai_agent | AI Agent | AI Agent本身 |

---

## 2. 权限类型

### 2.1 原有权限 (21种)

#### 平台管理 (3种)
| 权限值 | 说明 |
|--------|------|
| platform:admin | 平台管理 |
| platform:config | 平台配置 |
| platform:deploy | 代码部署 |

#### 节点管理 (4种)
| 权限值 | 说明 |
|--------|------|
| node:start | 启动节点 |
| node:stop | 停止节点 |
| node:monitor | 节点监控 |
| node:config | 节点配置 |

#### Agent管理 (3种)
| 权限值 | 说明 |
|--------|------|
| agent:register | 注册Agent |
| agent:unregister | 注销Agent |
| agent:manage | 管理Agent |

#### 区块链/钱包 (5种)
| 权限值 | 说明 |
|--------|------|
| wallet:create | 创建钱包 |
| wallet:bind | 绑定钱包 |
| blockchain:stake | 质押 |
| blockchain:vote | 投票 |
| blockchain:govern | 治理 |

#### 数据操作 (3种)
| 权限值 | 说明 |
|--------|------|
| data:query | 查询数据 |
| data:write | 写入数据 |
| data:admin | 数据管理 |

#### 对话 (2种)
| 权限值 | 说明 |
|--------|------|
| chat:basic | 基本对话 |
| chat:admin | 对话管理 |

#### 系统 (3种)
| 权限值 | 说明 |
|--------|------|
| system:health | 健康检查 |
| system:metrics | 系统指标 |
| system:logs | 日志访问 |

#### NPM工具 (5种)
| 权限值 | 说明 |
|--------|------|
| npm:public | npm view/search |
| npm:install | npm install |
| npm:run | npm run |
| npm:global | npm全局安装 |
| npm:danger | 危险npm操作 |

#### Git工具 (6种)
| 权限值 | 说明 |
|--------|------|
| git:read | git只读 |
| git:write | git写入 |
| git:push | git推送 |
| git:clone | git克隆 |
| git:force | git强制推送 |
| git:danger | 危险git操作 |

### 2.2 新增权限 - 环境隔离 (4种)

基于用户环境隔离机制新增的权限，这些权限在隔离保护下可以安全地放宽给普通用户：

| 权限值 | 说明 | 安全保障 |
|--------|------|---------|
| workspace | 用户工作目录操作 | 用户目录隔离 + 路径验证 + 配额限制 |
| sandbox | 代码执行沙箱 | 进程隔离 + 超时 + 资源限制 |
| browser | 浏览器操作 | 会话隔离 |
| network | 网络访问 | 可选域名白名单 |

### 2.3 新增权限 - Agent服务 (1种)

| 权限值 | 说明 |
|--------|------|
| agent:service | Agent推荐、匹配等服务 |

---

## 3. 角色权限配置

### 3.1 superadmin (超级管理员)
拥有全部权限，包括：
- 所有平台、节点、Agent、钱包、区块链、数据、对话、系统权限
- 所有环境隔离权限 (workspace, sandbox, browser, network)
- 所有NPM/Git权限

### 3.2 developer (开发人员)
| 权限类别 | 具体权限 |
|---------|---------|
| 平台 | platform:config, platform:deploy |
| 节点 | node:monitor |
| Agent | agent:register, agent:manage, agent:service |
| 钱包 | wallet:bind |
| 数据 | data:query, data:write |
| 对话 | chat:basic |
| 系统 | system:health, system:metrics, system:logs |
| 环境 | workspace, sandbox, browser, network |
| NPM | npm:public, npm:install, npm:run, npm:global |
| Git | git:read, git:write, git:push, git:clone |

### 3.3 node_admin (节点管理员)
| 权限类别 | 具体权限 |
|---------|---------|
| 节点 | node:start, node:stop, node:monitor, node:config |
| Agent | agent:register |
| 钱包 | wallet:bind, stake, vote |
| 数据 | data:query, data:write |
| 对话 | chat:basic |
| 系统 | system:health, system:metrics, system:logs |
| 环境 | workspace, network |
| NPM | npm:public, npm:install, npm:run |
| Git | git:read, git:write, git:clone |

### 3.4 node_operator (节点运营)
| 权限类别 | 具体权限 |
|---------|---------|
| 节点 | node:monitor, node:config |
| 钱包 | wallet:bind, stake, vote |
| 数据 | data:query |
| 对话 | chat:basic |
| 系统 | system:health, system:metrics, system:logs |
| 环境 | workspace, network |
| NPM | npm:public, npm:install |
| Git | git:read |

### 3.5 human (普通用户) ⚠️ 重点更新
| 权限类别 | 具体权限 | 说明 |
|---------|---------|------|
| 基础 | chat:basic, data:query, system:health, wallet:bind | 基础功能 |
| 环境隔离 | workspace, sandbox, browser, network | 新增，基于隔离机制可安全使用 |
| Agent服务 | agent:service | 新增 |
| NPM/Git | npm:public, npm:install, npm:run, git:read | 基础开发权限 |

### 3.6 ai_owner (AI Agent主人)
| 权限类别 | 具体权限 |
|---------|---------|
| Agent | agent:register, agent:unregister, agent:manage, agent:service |
| 钱包 | wallet:bind, stake, vote |
| 数据 | data:query, data:write |
| 对话 | chat:basic |
| 系统 | system:health |
| 环境 | workspace, network |
| NPM | npm:public, npm:install, npm:run |
| Git | git:read, git:write |

### 3.7 ai_agent (AI Agent)
| 权限类别 | 具体权限 |
|---------|---------|
| Agent | agent:register, agent:service |
| 钱包 | wallet:bind |
| 数据 | data:query, data:write |
| 对话 | chat:basic |
| 系统 | system:health |
| 环境 | workspace, sandbox, browser, network |
| NPM | npm:public |
| Git | git:read |

---

## 4. 工具权限映射

### 4.1 对话类
| 工具 | 权限 |
|------|------|
| general_response | chat:basic |
| search_knowledge | data:query |

### 4.2 搜索类
| 工具 | 权限 |
|------|------|
| search_web | network |
| search_files | workspace |

### 4.3 文件操作 (Workspace隔离)
| 工具 | 权限 |
|------|------|
| read_file | workspace |
| write_file | workspace |
| list_directory | workspace |
| create_directory | workspace |
| copy_file | workspace |
| move_file | workspace |
| delete_file | workspace |
| get_file_info | workspace |
| search_files | workspace |

### 4.4 代码执行 (Sandbox隔离)
| 工具 | 权限 |
|------|------|
| execute_python | sandbox |
| execute_javascript | sandbox |
| execute_command | sandbox |
| run_program | sandbox |
| parse_skill_md | sandbox |
| execute_skill | sandbox |
| list_skills | sandbox |

### 4.5 浏览器 (Browser隔离)
| 工具 | 权限 |
|------|------|
| browser_open | browser |
| browser_click | browser |
| browser_fill | browser |
| browser_get_content | browser |
| browser_screenshot | browser |
| browser_close | browser |

### 4.6 网络访问
| 工具 | 权限 |
|------|------|
| fetch_url | network |
| parse_html | network |
| download_file | network |
| get_headers | network |
| search_web | network |

### 4.7 数据操作
| 工具 | 权限 |
|------|------|
| query_db | data:query |
| analyze_data | data:query |
| generate_report | data:query |
| insert_db | data:write |
| update_db | data:write |
| delete_db | data:admin |
| upload_to_ipfs | data:write |
| download_from_ipfs | data:query |
| sync_to_ipfs | data:write |

### 4.8 节点管理
| 工具 | 权限 |
|------|------|
| start_node | node:start |
| stop_node | node:stop |
| get_node_status | node:monitor |
| set_threshold | node:config |
| get_alerts | node:monitor |

### 4.9 钱包/区块链
| 工具 | 权限 |
|------|------|
| create_wallet | wallet:create |
| get_balance | wallet:bind |
| bind_wallet | wallet:bind |
| switch_chain | wallet:bind |
| get_chain_info | wallet:bind |
| stake | blockchain:stake |
| unstake | blockchain:stake |
| vote | blockchain:vote |
| delegate_vote | blockchain:vote |
| get_vote_power | blockchain:vote |
| list_proposals | blockchain:vote |
| submit_proposal | blockchain:govern |

### 4.10 Agent服务
| 工具 | 权限 |
|------|------|
| search_agents | agent:service |
| recommend_agents | agent:service |
| get_recommendation_history | agent:service |
| rate_agent | agent:service |
| get_agent_profile | agent:service |
| get_all_agent_profiles | agent:service |
| recommend_agents_for_demand | agent:service |
| match_by_gene_capsule | agent:service |
| generate_recommendation_explanation | agent:service |
| proactively_notify_opportunity | agent:service |
| scan_opportunities | agent:service |
| auto_match_and_notify | agent:service |
| consult_agent | agent:service |
| route_message | agent:service |
| get_load_balance_status | agent:service |
| get_route_info | agent:service |
| interview_agent | agent:service |
| send_agent_message | agent:service |
| receive_agent_showcase | agent:service |
| retrieve_user_info | agent:service |
| list_user_agents | agent:manage |
| register_agent | agent:register |
| unregister_agent | agent:unregister |

### 4.11 系统
| 工具 | 权限 |
|------|------|
| health_check | system:health |
| get_system_health | system:health |
| get_metrics | system:metrics |
| get_system_metrics | system:metrics |
| query_logs | system:logs |

### 4.12 平台配置
| 工具 | 权限 |
|------|------|
| get_config | platform:config |
| update_config | platform:config |
| generate_component | platform:config |
| manage_page | platform:config |

---

## 5. 环境隔离机制

系统使用三层环境隔离来保护系统安全：

### 5.1 UserWorkspace (工作目录隔离)
- 每个用户有独立的工作目录
- 路径验证：防止路径穿越攻击
- 配额限制：防止磁盘耗尽
- 目录结构：
  - workspace/uploads/ - 上传文件
  - workspace/output/ - 输出文件
  - workspace/temp/ - 临时文件

### 5.2 CodeSandbox (代码执行沙箱)
- 进程隔离：代码在独立进程中运行
- 超时限制：防止无限循环
- 资源限制：CPU/内存限制
- 网络隔离：可配置网络访问

### 5.3 BrowserContext (浏览器会话隔离)
- 每个用户有独立的浏览器会话
- Cookie/Storage隔离
- 页面隔离

---

## 6. 权限检查流程

1. 用户调用工具时，系统获取用户角色
2. 根据角色从 `ROLE_PERMISSIONS` 获取该角色拥有的权限列表
3. 获取工具所需的权限列表 `TOOL_PERMISSIONS`
4. 检查用户权限是否覆盖工具所需的所有权限
5. 如果权限不足，返回权限拒绝信息

---

## 7. 权限配置示例

### 7.1 human角色的典型使用场景

由于 human 角色拥有 workspace、sandbox、browser、network 权限，可以：

✅ 读取/写入自己workspace中的文件
✅ 执行Python/JavaScript代码（在sandbox中）
✅ 操作浏览器（在独立的browser context中）
✅ 访问网络资源
✅ 搜索Agent和使用Agent服务

❌ 访问系统数据库
❌ 管理系统配置
❌ 启动/停止节点

---

## 8. 更新日志

### 2026-03-02
- 新增4种环境隔离权限：workspace, sandbox, browser, network
- 新增1种Agent服务权限：agent:service
- 更新 human 角色权限，增加文件操作、代码执行、浏览器操作权限
- 更新 node_operator 角色权限，增加workspace和network权限
- 更新 ai_owner 角色权限，增加更多Agent服务权限
- 更新 ai_agent 角色权限，增加完整的环境隔离权限

</details>
