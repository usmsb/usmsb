"""
Permission Manager - 权限管理器

实现：
- 用户角色管理
- 权限校验
- 投票权计算
- 数据持久化
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from typing import Any

from .models import (
    PermissionType,
    UserPermission,
    UserRole,
    get_role_permissions,
    get_tool_required_permissions,
)

logger = logging.getLogger(__name__)


def _get_event_loop():
    """获取事件循环，处理没有运行中的循环的情况"""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


class PermissionManager:
    """
    权限管理器

    基于 USMSB Rule 要素，实现：
    - 用户角色分配
    - 权限校验
    - 工具访问控制
    - 投票权管理
    """

    def __init__(self, db_path: str = "meta_agent.db"):
        self.db_path = db_path
        self._user_cache: dict[str, UserPermission] = {}
        self._initialized = False

    async def init(self):
        """初始化数据库"""
        if self._initialized:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        await loop.run_in_executor(None, self._init_db)
        self._initialized = True
        logger.info("Permission Manager initialized")

    def _init_db(self):
        """初始化数据库表"""
        os.makedirs(
            os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True
        )

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_permissions (
                id TEXT PRIMARY KEY,
                wallet_address TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'human',
                permissions TEXT,
                stake_amount REAL DEFAULT 0,
                token_balance REAL DEFAULT 0,
                voting_power REAL DEFAULT 0,
                created_at REAL,
                updated_at REAL,
                metadata TEXT
            )
        """)

        # 角色变更历史
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_history (
                id TEXT PRIMARY KEY,
                wallet_address TEXT NOT NULL,
                old_role TEXT,
                new_role TEXT NOT NULL,
                changed_by TEXT,
                reason TEXT,
                changed_at REAL
            )
        """)

        # 创建索引
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_user_wallet ON user_permissions(wallet_address)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_role ON user_permissions(role)")

        conn.commit()
        conn.close()

    async def register_user(
        self,
        wallet_address: str,
        role: UserRole = UserRole.HUMAN,
        initial_stake: float = 0.0,
        initial_balance: float = 0.0,
    ) -> UserPermission:
        """
        注册新用户

        Args:
            wallet_address: 钱包地址
            role: 用户角色
            initial_stake: 初始质押量
            initial_balance: 初始代币余额

        Returns:
            用户权限对象
        """
        await self.init()

        # 检查是否已存在
        existing = await self.get_user(wallet_address)
        if existing:
            logger.info(f"User {wallet_address} already exists with role {existing.role}")
            return existing

        # 创建新用户
        permissions = get_role_permissions(role)
        user = UserPermission(
            wallet_address=wallet_address,
            role=role,
            permissions=permissions,
            stake_amount=initial_stake,
            token_balance=initial_balance,
        )

        # 缓存
        self._user_cache[wallet_address] = user

        # 持久化
        await self._save_user(user)

        logger.info(f"Registered user {wallet_address} with role {role.value}")
        return user

    async def get_user(self, wallet_address: str) -> UserPermission | None:
        """获取用户权限信息"""
        # 检查缓存
        if wallet_address in self._user_cache:
            return self._user_cache[wallet_address]

        try:
            # 从数据库加载
            user = await self._load_user(wallet_address)
            if user:
                self._user_cache[wallet_address] = user
                return user
            else:
                # 用户不存在时，返回 None，由调用方决定如何处理
                logger.info(f"User {wallet_address} not found in database")
                return None
        except Exception as e:
            logger.error(f"Error in get_user for {wallet_address}: {e}")
            return None

    async def update_role(
        self,
        wallet_address: str,
        new_role: UserRole,
        changed_by: str | None = None,
        reason: str | None = None,
    ) -> UserPermission | None:
        """
        更新用户角色

        Args:
            wallet_address: 钱包地址
            new_role: 新角色
            changed_by: 变更者（钱包地址）
            reason: 变更原因

        Returns:
            更新后的用户权限
        """
        user = await self.get_user(wallet_address)
        if not user:
            return None

        old_role = user.role
        user.role = new_role
        user.permissions = get_role_permissions(new_role)
        user.updated_at = datetime.now().timestamp()

        # 更新缓存
        self._user_cache[wallet_address] = user

        # 持久化
        await self._save_user(user)

        # 记录变更历史
        await self._record_role_change(wallet_address, old_role, new_role, changed_by, reason)

        logger.info(f"Updated role for {wallet_address}: {old_role.value} -> {new_role.value}")
        return user

    def invalidate_cache(self, wallet_address: str | None = None):
        """清除用户缓存

        Args:
            wallet_address: 要清除缓存的用户钱包地址。如果为 None，则清除所有缓存。
        """
        if wallet_address:
            if wallet_address in self._user_cache:
                del self._user_cache[wallet_address]
                logger.info(f"Cleared cache for user: {wallet_address}")
        else:
            self._user_cache.clear()
            logger.info("Cleared all user cache")

    async def update_stake(
        self, wallet_address: str, stake_amount: float
    ) -> UserPermission | None:
        """更新用户质押量"""
        user = await self.get_user(wallet_address)
        if not user:
            return None

        user.update_stake(stake_amount)
        self._user_cache[wallet_address] = user
        await self._save_user(user)

        logger.info(f"Updated stake for {wallet_address}: {stake_amount}")
        return user

    async def update_balance(self, wallet_address: str, balance: float) -> UserPermission | None:
        """更新用户代币余额"""
        user = await self.get_user(wallet_address)
        if not user:
            return None

        user.update_balance(balance)
        self._user_cache[wallet_address] = user
        await self._save_user(user)

        logger.info(f"Updated balance for {wallet_address}: {balance}")
        return user

    async def check_permission(
        self,
        wallet_address: str,
        permission: PermissionType,
    ) -> bool:
        """
        检查用户是否有某权限

        Args:
            wallet_address: 钱包地址
            permission: 权限类型

        Returns:
            是否有权限
        """
        user = await self.get_user(wallet_address)
        if not user:
            return False

        return user.has_permission(permission)

    async def check_tool_access(
        self,
        wallet_address: str,
        tool_name: str,
    ) -> dict[str, Any]:
        """
        检查用户是否可以访问某工具

        Args:
            wallet_address: 钱包地址
            tool_name: 工具名称

        Returns:
            {"allowed": bool, "reason": str, "required_permissions": list}
        """
        user = await self.get_user(wallet_address)
        required = get_tool_required_permissions(tool_name)

        if not user:
            return {
                "allowed": False,
                "reason": "User not found",
                "required_permissions": [p.value for p in required],
            }

        # 检查所有必需权限
        missing = []
        for perm in required:
            if not user.has_permission(perm):
                missing.append(perm.value)

        if missing:
            return {
                "allowed": False,
                "reason": f"Missing permissions: {', '.join(missing)}",
                "required_permissions": [p.value for p in required],
                "missing_permissions": missing,
                "user_role": user.role.value,
            }

        return {
            "allowed": True,
            "reason": "Access granted",
            "required_permissions": [p.value for p in required],
            "user_role": user.role.value,
        }

    async def get_voting_power(self, wallet_address: str) -> float:
        """获取用户投票权"""
        user = await self.get_user(wallet_address)
        return user.voting_power if user else 0.0

    async def get_users_by_role(self, role: UserRole) -> list[UserPermission]:
        """获取指定角色的所有用户"""
        loop = _get_event_loop()
        return await loop.run_in_executor(None, self._query_users_by_role, role)

    def _query_users_by_role(self, role: UserRole) -> list[UserPermission]:
        """查询指定角色的用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM user_permissions WHERE role = ?",
            (role.value,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_user(row) for row in rows]

    async def get_all_users(self, limit: int = 100) -> list[UserPermission]:
        """获取所有用户"""
        loop = _get_event_loop()
        return await loop.run_in_executor(None, self._query_all_users, limit)

    def _query_all_users(self, limit: int) -> list[UserPermission]:
        """查询所有用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM user_permissions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_user(row) for row in rows]

    async def _load_user(self, wallet_address: str) -> UserPermission | None:
        """加载用户"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return await loop.run_in_executor(None, self._query_user, wallet_address)

    def _query_user(self, wallet_address: str) -> UserPermission | None:
        """查询用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM user_permissions WHERE wallet_address = ?",
            (wallet_address,),
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return self._row_to_user(row)

    def _row_to_user(self, row) -> UserPermission:
        """数据库行转用户对象"""
        permissions_str = row[3]
        permissions = []
        if permissions_str:
            for p in json.loads(permissions_str):
                try:
                    permissions.append(PermissionType(p))
                except:
                    pass

        return UserPermission(
            id=row[0],
            wallet_address=row[1],
            role=UserRole(row[2]),
            permissions=permissions,
            stake_amount=row[4],
            token_balance=row[5],
            voting_power=row[6],
            created_at=row[7],
            updated_at=row[8],
            metadata=json.loads(row[9]) if row[9] else {},
        )

    async def _save_user(self, user: UserPermission):
        """保存用户"""
        loop = _get_event_loop()
        await loop.run_in_executor(None, self._insert_user, user)

    def _insert_user(self, user: UserPermission):
        """插入用户"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO user_permissions
            (id, wallet_address, role, permissions, stake_amount, token_balance,
             voting_power, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.wallet_address,
                user.role.value,
                json.dumps([p.value for p in user.permissions]),
                user.stake_amount,
                user.token_balance,
                user.voting_power,
                user.created_at,
                user.updated_at,
                json.dumps(user.metadata),
            ),
        )

        conn.commit()
        conn.close()

    async def _record_role_change(
        self,
        wallet_address: str,
        old_role: UserRole,
        new_role: UserRole,
        changed_by: str | None,
        reason: str | None,
    ):
        """记录角色变更历史"""
        loop = _get_event_loop()
        await loop.run_in_executor(
            None,
            self._insert_role_change,
            wallet_address,
            old_role,
            new_role,
            changed_by,
            reason,
        )

    def _insert_role_change(
        self,
        wallet_address: str,
        old_role: UserRole,
        new_role: UserRole,
        changed_by: str | None,
        reason: str | None,
    ):
        """插入角色变更记录"""
        import uuid

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO role_history
            (id, wallet_address, old_role, new_role, changed_by, reason, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4())[:8],
                wallet_address,
                old_role.value if old_role else None,
                new_role.value,
                changed_by,
                reason,
                datetime.now().timestamp(),
            ),
        )

        conn.commit()
        conn.close()

    def get_stats(self) -> dict[str, Any]:
        """获取权限统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 用户总数
        cursor.execute("SELECT COUNT(*) FROM user_permissions")
        total_users = cursor.fetchone()[0]

        # 各角色用户数
        cursor.execute("SELECT role, COUNT(*) FROM user_permissions GROUP BY role")
        role_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # 总投票权
        cursor.execute("SELECT SUM(voting_power) FROM user_permissions")
        total_voting_power = cursor.fetchone()[0] or 0

        # 总质押量
        cursor.execute("SELECT SUM(stake_amount) FROM user_permissions")
        total_stake = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_users": total_users,
            "users_by_role": role_counts,
            "total_voting_power": total_voting_power,
            "total_stake": total_stake,
        }
