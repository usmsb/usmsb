"""
Permission Models - 权限数据模型

基于 USMSB Rule 要素实现权限管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class UserRole(str, Enum):
    """用户角色"""

    SUPERADMIN = "superadmin"  # 超级管理员
    DEVELOPER = "developer"  # 开发人员
    NODE_ADMIN = "node_admin"  # 节点管理员
    NODE_OPERATOR = "node_operator"  # 节点运营
    HUMAN = "human"  # 普通用户
    AI_OWNER = "ai_owner"  # AI Agent 主人
    AI_AGENT = "ai_agent"  # AI Agent


class PermissionType(str, Enum):
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


@dataclass
class Permission:
    """权限定义"""

    id: str = field(default_factory=lambda: str(uuid4())[:8])
    name: str = ""
    type: PermissionType = PermissionType.CHAT
    description: str = ""
    resource: str = ""  # 资源标识
    action: str = ""  # 操作：create, read, update, delete, execute
    conditions: Dict[str, Any] = field(default_factory=dict)
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
    permissions: List[PermissionType] = field(default_factory=list)

    # 投票权相关
    stake_amount: float = 0.0  # 质押量
    token_balance: float = 0.0  # 代币余额
    voting_power: float = 0.0  # 投票权（计算得出）

    # 时间戳
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

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

    def to_dict(self) -> Dict[str, Any]:
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

ROLE_PERMISSIONS: Dict[UserRole, List[PermissionType]] = {
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
        PermissionType.WALLET_BIND,
        PermissionType.DATA_QUERY,
        PermissionType.DATA_WRITE,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
        PermissionType.SYSTEM_LOGS,
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
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        PermissionType.SYSTEM_METRICS,
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
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        # Git 权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
    ],
    UserRole.HUMAN: [
        PermissionType.WALLET_CREATE,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        # NPM/NPX 基础权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        # Git 基础权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
        PermissionType.GIT_CLONE,
    ],
    UserRole.AI_OWNER: [
        PermissionType.AGENT_REGISTER,
        PermissionType.AGENT_MANAGE,
        PermissionType.WALLET_BIND,
        PermissionType.STAKE,
        PermissionType.VOTE,
        PermissionType.DATA_QUERY,
        PermissionType.CHAT,
        # NPM/NPX 权限
        PermissionType.NPM_PUBLIC,
        PermissionType.NPM_INSTALL,
        PermissionType.NPM_RUN,
        # Git 权限
        PermissionType.GIT_READ,
        PermissionType.GIT_WRITE,
    ],
    UserRole.AI_AGENT: [
        PermissionType.WALLET_BIND,
        PermissionType.DATA_QUERY,
        PermissionType.CHAT,
        PermissionType.SYSTEM_HEALTH,
        # NPM/NPX 基础权限
        PermissionType.NPM_PUBLIC,
        # Git 只读权限
        PermissionType.GIT_READ,
    ],
}


# ============ 工具权限映射 ============

TOOL_PERMISSIONS: Dict[str, List[PermissionType]] = {
    # 平台管理
    "start_node": [PermissionType.NODE_START],
    "stop_node": [PermissionType.NODE_STOP],
    "get_node_status": [PermissionType.NODE_MONITOR],
    "get_config": [PermissionType.PLATFORM_CONFIG],
    "update_config": [PermissionType.PLATFORM_CONFIG],
    "bind_wallet": [PermissionType.WALLET_BIND],
    "register_agent": [PermissionType.AGENT_REGISTER],
    "unregister_agent": [PermissionType.AGENT_UNREGISTER],
    # 监控
    "health_check": [PermissionType.SYSTEM_HEALTH],
    "get_metrics": [PermissionType.SYSTEM_METRICS],
    "set_threshold": [PermissionType.NODE_CONFIG],
    "get_alerts": [PermissionType.NODE_MONITOR],
    # 区块链
    "create_wallet": [PermissionType.WALLET_CREATE],
    "get_balance": [PermissionType.WALLET_BIND],
    "stake": [PermissionType.STAKE],
    "unstake": [PermissionType.STAKE],
    "vote": [PermissionType.VOTE],
    "submit_proposal": [PermissionType.GOVERN],
    "switch_chain": [PermissionType.WALLET_BIND],
    "get_chain_info": [PermissionType.WALLET_BIND],
    # IPFS
    "upload_to_ipfs": [PermissionType.DATA_WRITE],
    "download_from_ipfs": [PermissionType.DATA_QUERY],
    "sync_to_ipfs": [PermissionType.DATA_WRITE],
    # 数据库
    "query_db": [PermissionType.DATA_QUERY],
    "insert_db": [PermissionType.DATA_WRITE],
    "update_db": [PermissionType.DATA_WRITE],
    "delete_db": [PermissionType.DATA_ADMIN],
    "analyze_data": [PermissionType.DATA_QUERY],
    "generate_report": [PermissionType.DATA_QUERY],
    # 前端
    "generate_component": [PermissionType.PLATFORM_CONFIG],
    "manage_page": [PermissionType.PLATFORM_CONFIG],
    "call_api": [PermissionType.DATA_QUERY],
    # 治理
    "get_user_info": [PermissionType.WALLET_BIND],
    "list_user_agents": [PermissionType.AGENT_MANAGE],
    "delegate_vote": [PermissionType.VOTE],
    "get_vote_power": [PermissionType.VOTE],
    "list_proposals": [PermissionType.VOTE],
    # NPM/NPX 开发工具
    "npm_executor": [PermissionType.NPM_INSTALL],
    "npm_public": [PermissionType.NPM_PUBLIC],
    "npm_global": [PermissionType.NPM_GLOBAL],
    # Git 版本控制工具
    "git_executor": [PermissionType.GIT_READ],
    "git_push": [PermissionType.GIT_PUSH],
    "git_clone": [PermissionType.GIT_CLONE],
    "git_force": [PermissionType.GIT_FORCE],
    # 通用
    "general_response": [PermissionType.CHAT],
}


def get_role_permissions(role: UserRole) -> List[PermissionType]:
    """获取角色的默认权限"""
    return ROLE_PERMISSIONS.get(role, [PermissionType.CHAT])


def get_tool_required_permissions(tool_name: str) -> List[PermissionType]:
    """获取工具所需的权限"""
    return TOOL_PERMISSIONS.get(tool_name, [PermissionType.CHAT])
