"""
Permission Models - 权限数据模型

基于 USMSB Rule 要素实现权限管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class UserRole(StrEnum):
    """用户角色"""

    SUPERADMIN = "superadmin"  # 超级管理员
    DEVELOPER = "developer"  # 开发人员
    NODE_ADMIN = "node_admin"  # 节点管理员
    NODE_OPERATOR = "node_operator"  # 节点运营
    HUMAN = "human"  # 普通用户
    AI_OWNER = "ai_owner"  # AI Agent 主人
    AI_AGENT = "ai_agent"  # AI Agent


class PermissionType(StrEnum):
    """权限类型"""

    # 平台管理
    PLATFORM_ADMIN = "platform:admin"  # 平台管理
    PLATFORM_CONFIG = "platform:config"  # 平台配置
    PLATFORM_DEPLOY = "platform:deploy"  # 代码部署

    # 节点管理
    NODE_START = "node:start"  # 启动节点
    NODE_STOP = "node:stop"  # 停止节点
    NODE_MONITOR = "node:monitor"  # 节点监控
    NODE_CONFIG = "node:config"  # 节点配置

    # Agent 管理
    AGENT_REGISTER = "agent:register"  # 注册 Agent
    AGENT_UNREGISTER = "agent:unregister"  # 注销 Agent
    AGENT_MANAGE = "agent:manage"  # 管理 Agent

    # 区块链
    WALLET_CREATE = "wallet:create"  # 创建钱包
    WALLET_BIND = "wallet:bind"  # 绑定钱包
    STAKE = "blockchain:stake"  # 质押
    VOTE = "blockchain:vote"  # 投票
    GOVERN = "blockchain:govern"  # 治理

    # 数据
    DATA_QUERY = "data:query"  # 查询数据
    DATA_WRITE = "data:write"  # 写入数据
    DATA_ADMIN = "data:admin"  # 数据管理

    # 对话
    CHAT = "chat:basic"  # 基本对话
    CHAT_ADMIN = "chat:admin"  # 对话管理

    # 系统
    SYSTEM_HEALTH = "system:health"  # 健康检查
    SYSTEM_METRICS = "system:metrics"  # 系统指标
    SYSTEM_LOGS = "system:logs"  # 日志访问

    # NPM/NPX 开发工具
    NPM_PUBLIC = "npm:public"  # npm view/search (公开操作)
    NPM_INSTALL = "npm:install"  # npm install (本地安装)
    NPM_RUN = "npm:run"  # npm run (运行脚本)
    NPM_GLOBAL = "npm:global"  # npm install -g (全局安装)
    NPM_DANGER = "npm:danger"  # 危险 npm 操作

    # Git 版本控制
    GIT_READ = "git:read"  # git status/log/diff (只读)
    GIT_WRITE = "git:write"  # git add/commit (本地写入)
    GIT_PUSH = "git:push"  # git push (推送到远程)
    GIT_CLONE = "git:clone"  # git clone (克隆仓库)
    GIT_FORCE = "git:force"  # git push --force (强制推送)
    GIT_DANGER = "git:danger"  # 危险 git 操作

    # 用户环境隔离权限 (基于 workspace/sandbox/browser 隔离机制)
    WORKSPACE = "workspace"  # 用户工作目录操作 (读写文件等)
    SANDBOX = "sandbox"  # 代码执行沙箱
    BROWSER = "browser"  # 浏览器操作
    NETWORK = "network"  # 网络访问

    # Agent 服务
    AGENT_SERVICE = "agent:service"  # Agent 推荐、匹配等服务


@dataclass
class Permission:
    """权限定义"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    type: PermissionType = PermissionType.CHAT
    description: str = ""
    resource: str = ""  # 资源标识
    action: str = ""  # 操作：create, read, update, delete, execute
    conditions: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    def __post_init__(self):
        if isinstance(self.type, str):
            self.type = PermissionType(self.type)


@dataclass
class UserPermission:
    """用户权限绑定"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    wallet_address: str = ""
    role: UserRole = UserRole.HUMAN
    permissions: list[PermissionType] = field(default_factory=list)

    # 投票权相关
    stake_amount: float = 0.0  # 质押量
    token_balance: float = 0.0  # 代币余额
    voting_power: float = 0.0  # 投票权（计算得出）

    # 时间戳
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())

    # 元数据
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.role, str):
            self.role = UserRole(self.role)
        self._calculate_voting_power()

    def _calculate_voting_power(self):
        """计算投票权"""
        # 投票权 = 质押量 * 1.5 + 代币余额
        self.voting_power = self.stake_amount * 1.5 + self.token_balance

    def update_stake(self, amount: float):
        """更新质押量"""
        self.stake_amount = amount
        self._calculate_voting_power()
        self.updated_at = datetime.now().timestamp()

    def update_balance(self, balance: float):
        """更新代币余额"""
        self.token_balance = balance
        self._calculate_voting_power()
        self.updated_at = datetime.now().timestamp()

    def has_permission(self, permission: PermissionType) -> bool:
        """检查是否有某权限"""
        return permission in self.permissions

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "stake_amount": self.stake_amount,
            "token_balance": self.token_balance,
            "voting_power": self.voting_power,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ============ 角色默认权限映射 ============

ROLE_PERMISSIONS: dict[UserRole, list[PermissionType]] = {
    UserRole.SUPERADMIN: [
        # 超级管理员拥有所有权限
        PermissionType.PLATFORM_ADMIN,
        PermissionType.PLATFORM_CONFIG,
        PermissionType.PLATFORM_DEPLOY,
        PermissionType.NODE_START,
        PermissionType.NODE_STOP,
        PermissionType.NODE_MONITOR,
        PermissionType.NODE_CONFIG,
        PermissionType.AGENT_REGISTER,
        PermissionType.AGENT_UNREGISTER,
        PermissionType.AGENT_MANAGE,
        PermissionType.AGENT_SERVICE,
        PermissionType.WALLET_CREATE,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.GOVERN,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.DATA_ADMIN,
        PermissionType.CHAT,
        PermissionType.CHAT_ADMIN,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
        PermissionType.SYSTEM_LOGS,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.SANDBOX,
        PermissionType.BROWSER,
        PermissionType.NETWORK,
        # NPM/NPX 全权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        PermissionType.NPM_GLOBAL,
        PermissionType.NPM_DANGER,
        # Git 全权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
        PermissionType.GIT_PUSH,
        PermissionType.GIT_CLONE,
        PermissionType.GIT_FORCE,
        PermissionType.GIT_DANGER,
    ],
    UserRole.DEVELOPER: [
        PermissionType.PLATFORM_CONFIG,
        PermissionType.PLATFORM_DEPLOY,
        PermissionType.NODE_MONITOR,
        PermissionType.AGENT_REGISTER,
        PermissionType.AGENT_MANAGE,
        PermissionType.AGENT_SERVICE,
        PermissionType.WALLET_BIND,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
        PermissionType.SYSTEM_LOGS,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.SANDBOX,
        PermissionType.BROWSER,
        PermissionType.NETWORK,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        PermissionType.NPM_GLOBAL,
        # Git 权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
        PermissionType.GIT_PUSH,
        PermissionType.GIT_CLONE,
    ],
    UserRole.NODE_ADMIN: [
        PermissionType.NODE_START,
        PermissionType.NODE_STOP,
        PermissionType.NODE_MONITOR,
        PermissionType.NODE_CONFIG,
        PermissionType.AGENT_REGISTER,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
        PermissionType.SYSTEM_LOGS,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.NETWORK,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        # Git 权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
        PermissionType.GIT_CLONE,
    ],
    UserRole.NODE_OPERATOR: [
        PermissionType.NODE_MONITOR,
        PermissionType.NODE_CONFIG,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
        PermissionType.SYSTEM_LOGS,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.NETWORK,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        # Git 权限
        PermissionType.GIT_READ,
    ],
    UserRole.HUMAN: [
        # 基础权限
        PermissionType.CHAT,
        PermissionType.DATA_QUERY,
        PermissionType.SYSTEM_HEALTH,
        # 钱包/区块链 (需要质押后才开放)
        PermissionType.WALLET_BIND,
        # 环境隔离权限 (workspace/sandbox/browser 保护)
        PermissionType.WORKSPACE,      # 文件操作
        PermissionType.SANDBOX,        # 代码执行
        PermissionType.BROWSER,         # 浏览器操作
        PermissionType.NETWORK,        # 网络访问
        # Agent 服务
        PermissionType.AGENT_SERVICE,
        # NPM/Git 基础权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        PermissionType.GIT_READ,
    ],
    UserRole.AI_OWNER: [
        PermissionType.AGENT_REGISTER,
        PermissionType.AGENT_UNREGISTER,
        PermissionType.AGENT_MANAGE,
        PermissionType.AGENT_SERVICE,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.NETWORK,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        # Git 权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
    ],
    UserRole.AI_AGENT: [
        PermissionType.AGENT_REGISTER,
        PermissionType.AGENT_SERVICE,
        PermissionType.WALLET_BIND,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        # 环境隔离权限
        PermissionType.WORKSPACE,
        PermissionType.SANDBOX,
        PermissionType.BROWSER,
        PermissionType.NETWORK,
        # NPM/NPX 基础权限
        PermissionType.NPM_PUBLIC,
        # Git 只读权限
        PermissionType.GIT_READ,
    ],
}


# ============ 工具权限映射 ============

TOOL_PERMISSIONS: dict[str, list[PermissionType]] = {
    # ========== 平台管理 ==========
    "start_node": [PermissionType.NODE_START],
    "stop_node": [PermissionType.NODE_STOP],
    "get_node_status": [PermissionType.NODE_MONITOR],
    "get_config": [PermissionType.PLATFORM_CONFIG],
    "update_config": [PermissionType.PLATFORM_CONFIG],
    "bind_wallet": [PermissionType.WALLET_BIND],
    "register_agent": [PermissionType.AGENT_REGISTER],
    "unregister_agent": [PermissionType.AGENT_UNREGISTER],

    # ========== 监控/系统 ==========
    "health_check": [PermissionType.SYSTEM_HEALTH],
    "get_metrics": [PermissionType.SYSTEM_METRICS],
    "set_threshold": [PermissionType.NODE_CONFIG],
    "get_alerts": [PermissionType.NODE_MONITOR],
    "get_system_health": [PermissionType.SYSTEM_HEALTH],
    "get_system_metrics": [PermissionType.SYSTEM_METRICS],
    "query_logs": [PermissionType.SYSTEM_LOGS],

    # ========== 钱包/区块链 ==========
    "create_wallet": [PermissionType.WALLET_CREATE],
    "get_balance": [PermissionType.WALLET_BIND],
    "switch_chain": [PermissionType.WALLET_BIND],
    "get_chain_info": [PermissionType.WALLET_BIND],
    "stake": [PermissionType.STAKE],
    "unstake": [PermissionType.STAKE],
    "vote": [PermissionType.VOTE],
    "delegate_vote": [PermissionType.VOTE],
    "get_vote_power": [PermissionType.VOTE],
    "list_proposals": [PermissionType.VOTE],
    "submit_proposal": [PermissionType.GOVERN],
    "get_user_info": [PermissionType.WALLET_BIND],

    # ========== IPFS ==========
    "upload_to_ipfs": [PermissionType.DATA_WRITE],
    "download_from_ipfs": [PermissionType.DATA_QUERY],
    "sync_to_ipfs": [PermissionType.DATA_WRITE],

    # ========== 数据库 ==========
    "query_db": [PermissionType.DATA_QUERY],
    "insert_db": [PermissionType.DATA_WRITE],
    "update_db": [PermissionType.DATA_WRITE],
    "delete_db": [PermissionType.DATA_ADMIN],
    "analyze_data": [PermissionType.DATA_QUERY],
    "generate_report": [PermissionType.DATA_QUERY],

    # ========== 文件操作 (Workspace隔离) ==========
    "read_file": [PermissionType.WORKSPACE],
    "write_file": [PermissionType.WORKSPACE],
    "list_directory": [PermissionType.WORKSPACE],
    "create_directory": [PermissionType.WORKSPACE],
    "copy_file": [PermissionType.WORKSPACE],
    "move_file": [PermissionType.WORKSPACE],
    "delete_file": [PermissionType.WORKSPACE],
    "get_file_info": [PermissionType.WORKSPACE],
    "search_files": [PermissionType.WORKSPACE],

    # ========== 代码执行 (Sandbox隔离) ==========
    "execute_python": [PermissionType.SANDBOX],
    "execute_javascript": [PermissionType.SANDBOX],
    "execute_command": [PermissionType.SANDBOX],
    "run_program": [PermissionType.SANDBOX],

    # ========== 浏览器 (Browser隔离) ==========
    "browser_open": [PermissionType.BROWSER],
    "browser_click": [PermissionType.BROWSER],
    "browser_fill": [PermissionType.BROWSER],
    "browser_get_content": [PermissionType.BROWSER],
    "browser_screenshot": [PermissionType.BROWSER],
    "browser_close": [PermissionType.BROWSER],

    # ========== 网络访问 ==========
    "fetch_url": [PermissionType.NETWORK],
    "parse_html": [PermissionType.NETWORK],
    "download_file": [PermissionType.NETWORK],
    "get_headers": [PermissionType.NETWORK],
    "search_web": [PermissionType.NETWORK],

    # ========== 技能 ==========
    "parse_skill_md": [PermissionType.SANDBOX],
    "execute_skill": [PermissionType.SANDBOX],
    "list_skills": [PermissionType.SANDBOX],

    # ========== Agent服务 ==========
    "search_agents": [PermissionType.AGENT_SERVICE],
    "recommend_agents": [PermissionType.AGENT_SERVICE],
    "get_recommendation_history": [PermissionType.AGENT_SERVICE],
    "rate_agent": [PermissionType.AGENT_SERVICE],
    "get_agent_profile": [PermissionType.AGENT_SERVICE],
    "get_all_agent_profiles": [PermissionType.AGENT_SERVICE],
    "recommend_agents_for_demand": [PermissionType.AGENT_SERVICE],
    "match_by_gene_capsule": [PermissionType.AGENT_SERVICE],
    "generate_recommendation_explanation": [PermissionType.AGENT_SERVICE],
    "proactively_notify_opportunity": [PermissionType.AGENT_SERVICE],
    "scan_opportunities": [PermissionType.AGENT_SERVICE],
    "auto_match_and_notify": [PermissionType.AGENT_SERVICE],
    "consult_agent": [PermissionType.AGENT_SERVICE],
    "route_message": [PermissionType.AGENT_SERVICE],
    "get_load_balance_status": [PermissionType.AGENT_SERVICE],
    "get_route_info": [PermissionType.AGENT_SERVICE],
    "interview_agent": [PermissionType.AGENT_SERVICE],
    "send_agent_message": [PermissionType.AGENT_SERVICE],
    "receive_agent_showcase": [PermissionType.AGENT_SERVICE],
    "retrieve_user_info": [PermissionType.AGENT_SERVICE],
    "list_user_agents": [PermissionType.AGENT_MANAGE],

    # ========== 知识库 ==========
    "search_knowledge": [PermissionType.DATA_QUERY],

    # ========== 通用 ==========
    "general_response": [PermissionType.CHAT],

    # ========== NPM/Git (保留原权限) ==========
    "npm_executor": [PermissionType.NPM_INSTALL],
    "npm_public": [PermissionType.NPM_PUBLIC],
    "npm_global": [PermissionType.NPM_GLOBAL],
    "git_executor": [PermissionType.GIT_READ],
    "git_push": [PermissionType.GIT_PUSH],
    "git_clone": [PermissionType.GIT_CLONE],
    "git_force": [PermissionType.GIT_FORCE],
}


def get_role_permissions(role: UserRole) -> list[PermissionType]:
    """获取角色的默认权限"""
    return ROLE_PERMISSIONS.get(role, [PermissionType.CHAT])


def get_tool_required_permissions(tool_name: str) -> list[PermissionType]:
    """获取工具所需的权限"""
    return TOOL_PERMISSIONS.get(tool_name, [PermissionType.CHAT])
