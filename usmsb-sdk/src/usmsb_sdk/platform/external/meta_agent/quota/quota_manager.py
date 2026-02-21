"""
Quota Manager - Resource Quota Management

Implements quota management based on user roles with usage tracking,
hourly counters, and dynamic adjustment capabilities.
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class ResourceQuota:
    """Resource Quota Definition

    Defines the limits for various resources for a user role.
    """

    # Storage quotas
    max_storage_mb: int = 100
    max_workspace_files: int = 1000
    max_file_size_mb: int = 10

    # Code execution quotas
    max_code_timeout: int = 30
    max_code_memory_mb: int = 256
    max_code_executions_per_hour: int = 100

    # Browser quotas
    max_browser_sessions: int = 1
    max_browser_pages: int = 5

    # API quotas
    max_chat_per_hour: int = 500
    max_tool_calls_per_hour: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convert quota to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceQuota":
        """Create quota from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# Role-based quotas configuration
ROLE_QUOTAS: Dict[str, ResourceQuota] = {
    "USER": ResourceQuota(
        max_storage_mb=100,
        max_workspace_files=1000,
        max_file_size_mb=10,
        max_code_timeout=30,
        max_code_memory_mb=256,
        max_code_executions_per_hour=50,
        max_browser_sessions=1,
        max_browser_pages=5,
        max_chat_per_hour=200,
        max_tool_calls_per_hour=500,
    ),
    "DEVELOPER": ResourceQuota(
        max_storage_mb=500,
        max_workspace_files=5000,
        max_file_size_mb=50,
        max_code_timeout=60,
        max_code_memory_mb=512,
        max_code_executions_per_hour=200,
        max_browser_sessions=2,
        max_browser_pages=10,
        max_chat_per_hour=1000,
        max_tool_calls_per_hour=2000,
    ),
    "VALIDATOR": ResourceQuota(
        max_storage_mb=200,
        max_workspace_files=2000,
        max_file_size_mb=20,
        max_code_timeout=30,
        max_code_memory_mb=256,
        max_code_executions_per_hour=100,
        max_browser_sessions=1,
        max_browser_pages=5,
        max_chat_per_hour=500,
        max_tool_calls_per_hour=1000,
    ),
    "ADMIN": ResourceQuota(
        max_storage_mb=1000,
        max_workspace_files=10000,
        max_file_size_mb=100,
        max_code_timeout=120,
        max_code_memory_mb=1024,
        max_code_executions_per_hour=1000,
        max_browser_sessions=5,
        max_browser_pages=20,
        max_chat_per_hour=5000,
        max_tool_calls_per_hour=10000,
    ),
}


# Resource types that require quota checking
RESOURCE_TYPES = {
    "storage",          # Storage space usage (bytes)
    "workspace_files",  # Number of workspace files
    "code_execution",   # Code execution count (hourly)
    "chat",             # Chat message count (hourly)
    "tool_calls",       # Tool call count (hourly)
    "browser",          # Browser session count
    "browser_pages",     # Browser page count
}


@dataclass
class UsageRecord:
    """Usage record for a resource type"""

    resource_type: str
    wallet_address: str
    amount: int
    timestamp: float
    hourly_counter: bool = False


class QuotaManager:
    """
    Quota Manager

    Manages resource quotas for users based on their roles.
    Features:
    - Role-based quota assignment
    - Usage tracking with in-memory cache
    - Hourly counter reset
    - Usage reporting
    - Optional Redis backend support
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize Quota Manager.

        Args:
            redis_url: Optional Redis URL for distributed usage tracking.
                       If None, uses in-memory storage (default).
        """
        self.redis_url = redis_url
        self._redis_client = None
        self._usage_cache: Dict[str, Dict[str, Any]] = {}  # wallet_address -> {resource_type: usage_data}
        self._hourly_counters: Dict[str, Dict[str, Dict[str, int]]] = {}  # hour_key -> {wallet -> {resource_type: count}}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._running = False
        self._reset_task: Optional[asyncio.Task] = None

        # In-memory user role mapping (can be extended to fetch from database)
        self._user_roles: Dict[str, str] = {}

    async def start(self) -> None:
        """Start the quota manager and scheduled tasks."""
        if self._running:
            return

        self._running = True
        logger.info("QuotaManager started")

        # Start hourly counter reset task
        self._reset_task = asyncio.create_task(self._hourly_reset_loop())

    async def stop(self) -> None:
        """Stop the quota manager."""
        self._running = False
        if self._reset_task:
            self._reset_task.cancel()
            try:
                await self._reset_task
            except asyncio.CancelledError:
                pass
        logger.info("QuotaManager stopped")

    async def check_quota(
        self,
        wallet_address: str,
        resource_type: str,
        requested: int = 1
    ) -> Tuple[bool, str]:
        """
        Check if a resource request is within quota limits.

        Args:
            wallet_address: User's wallet address
            resource_type: Type of resource being requested
            requested: Amount of resource being requested (default: 1)

        Returns:
            Tuple of (is_allowed: bool, reason: str)
        """
        if resource_type not in RESOURCE_TYPES:
            logger.warning(f"Unknown resource type: {resource_type}")
            return False, f"Unknown resource type: {resource_type}"

        try:
            # Get user role and quota
            user_role = await self._get_user_role(wallet_address)
            quota = ROLE_QUOTAS.get(user_role, ROLE_QUOTAS["USER"])

            # Check quota based on resource type
            if resource_type == "storage":
                current_usage = await self._get_storage_used(wallet_address)
                max_storage_bytes = quota.max_storage_mb * 1024 * 1024
                if current_usage + requested > max_storage_bytes:
                    used_mb = current_usage // (1024 * 1024)
                    return False, f"Storage space insufficient. Used: {used_mb}MB/{quota.max_storage_mb}MB"

            elif resource_type == "workspace_files":
                current_files = await self._get_file_count(wallet_address)
                if current_files + requested > quota.max_workspace_files:
                    return False, f"File limit reached. Current: {current_files}/{quota.max_workspace_files}"

            elif resource_type == "code_execution":
                hourly_count = await self._get_hourly_usage(wallet_address, "code_execution")
                if hourly_count + requested > quota.max_code_executions_per_hour:
                    return False, f"Code execution limit reached. {hourly_count}/{quota.max_code_executions_per_hour} per hour"

            elif resource_type == "chat":
                hourly_count = await self._get_hourly_usage(wallet_address, "chat")
                if hourly_count + requested > quota.max_chat_per_hour:
                    return False, f"Chat limit reached. {hourly_count}/{quota.max_chat_per_hour} per hour"

            elif resource_type == "tool_calls":
                hourly_count = await self._get_hourly_usage(wallet_address, "tool_calls")
                if hourly_count + requested > quota.max_tool_calls_per_hour:
                    return False, f"Tool call limit reached. {hourly_count}/{quota.max_tool_calls_per_hour} per hour"

            elif resource_type == "browser":
                current_sessions = await self._get_current_usage(wallet_address, "browser")
                if current_sessions >= quota.max_browser_sessions:
                    return False, f"Browser session limit reached. {current_sessions}/{quota.max_browser_sessions}"

            elif resource_type == "browser_pages":
                current_pages = await self._get_current_usage(wallet_address, "browser_pages")
                if current_pages + requested > quota.max_browser_pages:
                    return False, f"Browser page limit reached. {current_pages}/{quota.max_browser_pages}"

            return True, "OK"

        except Exception as e:
            logger.error(f"Error checking quota for {wallet_address}: {e}")
            return False, f"Quota check error: {str(e)}"

    async def record_usage(
        self,
        wallet_address: str,
        resource_type: str,
        amount: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record resource usage.

        Args:
            wallet_address: User's wallet address
            resource_type: Type of resource used
            amount: Amount of resource used (default: 1)
            metadata: Optional metadata about the usage
        """
        if resource_type not in RESOURCE_TYPES:
            logger.warning(f"Unknown resource type: {resource_type}")
            return

        try:
            # Get lock for this wallet
            lock = self._get_lock(wallet_address)
            async with lock:
                # Initialize user cache if not exists
                if wallet_address not in self._usage_cache:
                    self._usage_cache[wallet_address] = {}

                # Update current usage
                if resource_type not in self._usage_cache[wallet_address]:
                    self._usage_cache[wallet_address][resource_type] = {
                        "total": 0,
                        "current": 0,
                        "last_updated": time.time()
                    }

                self._usage_cache[wallet_address][resource_type]["total"] += amount
                self._usage_cache[wallet_address][resource_type]["last_updated"] = time.time()

                # For hourly counter resources, track hourly usage
                if resource_type in ("code_execution", "chat", "tool_calls"):
                    await self._increment_hourly_counter(wallet_address, resource_type, amount)

                logger.debug(
                    f"Recorded usage: {wallet_address} - {resource_type} +{amount}"
                )

        except Exception as e:
            logger.error(f"Error recording usage: {e}")

    async def get_usage_report(
        self,
        wallet_address: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage report for a user.

        Args:
            wallet_address: User's wallet address

        Returns:
            Dictionary containing usage statistics and quota limits
        """
        try:
            user_role = await self._get_user_role(wallet_address)
            quota = ROLE_QUOTAS.get(user_role, ROLE_QUOTAS["USER"])

            # Get current usage for each resource
            storage_used = await self._get_storage_used(wallet_address)
            file_count = await self._get_file_count(wallet_address)
            code_executions_hour = await self._get_hourly_usage(wallet_address, "code_execution")
            chat_count_hour = await self._get_hourly_usage(wallet_address, "chat")
            tool_calls_hour = await self._get_hourly_usage(wallet_address, "tool_calls")
            browser_sessions = await self._get_current_usage(wallet_address, "browser")
            browser_pages = await self._get_current_usage(wallet_address, "browser_pages")

            return {
                "wallet_address": wallet_address,
                "user_role": user_role,
                "timestamp": time.time(),
                "usage": {
                    "storage": {
                        "used_bytes": storage_used,
                        "used_mb": storage_used // (1024 * 1024),
                        "limit_mb": quota.max_storage_mb,
                        "percentage": min(100, (storage_used / (quota.max_storage_mb * 1024 * 1024)) * 100)
                    },
                    "workspace_files": {
                        "count": file_count,
                        "limit": quota.max_workspace_files,
                        "percentage": min(100, (file_count / quota.max_workspace_files) * 100)
                    },
                    "code_execution": {
                        "hourly_count": code_executions_hour,
                        "hourly_limit": quota.max_code_executions_per_hour,
                        "percentage": min(100, (code_executions_hour / quota.max_code_executions_per_hour) * 100)
                    },
                    "chat": {
                        "hourly_count": chat_count_hour,
                        "hourly_limit": quota.max_chat_per_hour,
                        "percentage": min(100, (chat_count_hour / quota.max_chat_per_hour) * 100)
                    },
                    "tool_calls": {
                        "hourly_count": tool_calls_hour,
                        "hourly_limit": quota.max_tool_calls_per_hour,
                        "percentage": min(100, (tool_calls_hour / quota.max_tool_calls_per_hour) * 100)
                    },
                    "browser": {
                        "sessions": browser_sessions,
                        "sessions_limit": quota.max_browser_sessions,
                        "pages": browser_pages,
                        "pages_limit": quota.max_browser_pages
                    }
                },
                "quota_limits": quota.to_dict(),
            }

        except Exception as e:
            logger.error(f"Error generating usage report: {e}")
            return {
                "wallet_address": wallet_address,
                "error": str(e)
            }

    async def set_user_role(
        self,
        wallet_address: str,
        role: str
    ) -> None:
        """
        Set the role for a user.

        Args:
            wallet_address: User's wallet address
            role: Role name (USER, DEVELOPER, VALIDATOR, ADMIN)
        """
        if role not in ROLE_QUOTAS:
            raise ValueError(f"Invalid role: {role}. Must be one of {list(ROLE_QUOTAS.keys())}")

        self._user_roles[wallet_address] = role
        logger.info(f"Set role for {wallet_address} to {role}")

    async def _get_user_role(self, wallet_address: str) -> str:
        """
        Get the user's role.

        Returns USER role if not explicitly set.

        Args:
            wallet_address: User's wallet address

        Returns:
            User role string
        """
        return self._user_roles.get(wallet_address, "USER")

    async def _get_storage_used(self, wallet_address: str) -> int:
        """Get storage usage in bytes for a user."""
        if wallet_address in self._usage_cache:
            return self._usage_cache[wallet_address].get("storage", {}).get("total", 0)
        return 0

    async def _get_file_count(self, wallet_address: str) -> int:
        """Get workspace file count for a user."""
        if wallet_address in self._usage_cache:
            return self._usage_cache[wallet_address].get("workspace_files", {}).get("current", 0)
        return 0

    async def _get_current_usage(
        self,
        wallet_address: str,
        resource_type: str
    ) -> int:
        """
        Get current usage for a resource type.

        Args:
            wallet_address: User's wallet address
            resource_type: Type of resource

        Returns:
            Current usage count
        """
        if wallet_address in self._usage_cache:
            return self._usage_cache[wallet_address].get(resource_type, {}).get("current", 0)
        return 0

    async def _get_hourly_usage(
        self,
        wallet_address: str,
        resource_type: str
    ) -> int:
        """
        Get hourly usage for a resource type.

        Args:
            wallet_address: User's wallet address
            resource_type: Type of resource

        Returns:
            Hourly usage count
        """
        hour_key = self._get_current_hour_key()
        if hour_key in self._hourly_counters:
            if wallet_address in self._hourly_counters[hour_key]:
                return self._hourly_counters[hour_key][wallet_address].get(resource_type, 0)
        return 0

    async def _increment_hourly_counter(
        self,
        wallet_address: str,
        resource_type: str,
        amount: int
    ) -> None:
        """Increment hourly counter for a resource type."""
        hour_key = self._get_current_hour_key()

        if hour_key not in self._hourly_counters:
            self._hourly_counters[hour_key] = {}

        if wallet_address not in self._hourly_counters[hour_key]:
            self._hourly_counters[hour_key][wallet_address] = {}

        if resource_type not in self._hourly_counters[hour_key][wallet_address]:
            self._hourly_counters[hour_key][wallet_address][resource_type] = 0

        self._hourly_counters[hour_key][wallet_address][resource_type] += amount

    async def reset_hourly_counters(self) -> int:
        """
        Reset hourly counters (scheduled task).

        Returns:
            Number of hours reset
        """
        current_hour = self._get_current_hour_key()
        count = 0

        # Remove old hour keys (keep current and previous hour)
        keys_to_remove = [
            key for key in self._hourly_counters.keys()
            if key < current_hour
        ]

        for key in keys_to_remove:
            del self._hourly_counters[key]
            count += 1

        if count > 0:
            logger.debug(f"Reset {count} hourly counters")

        return count

    async def _hourly_reset_loop(self) -> None:
        """Background task to reset hourly counters."""
        while self._running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self.reset_hourly_counters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in hourly reset loop: {e}")

    def _get_current_hour_key(self) -> int:
        """Get current hour key for tracking hourly usage."""
        return int(time.time() // 3600)  # Current hour since epoch

    def _get_lock(self, wallet_address: str) -> asyncio.Lock:
        """Get or create a lock for a wallet address."""
        if wallet_address not in self._locks:
            self._locks[wallet_address] = asyncio.Lock()
        return self._locks[wallet_address]

    def _hash_wallet(self, wallet_address: str) -> str:
        """Hash wallet address for privacy."""
        return hashlib.sha256(
            f"usmsb_quota:{wallet_address}".encode()
        ).hexdigest()[:16]

    async def clear_user_data(
        self,
        wallet_address: str
    ) -> None:
        """
        Clear all usage data for a user.

        Args:
            wallet_address: User's wallet address
        """
        if wallet_address in self._usage_cache:
            del self._usage_cache[wallet_address]

        # Remove from hourly counters
        for hour_data in self._hourly_counters.values():
            if wallet_address in hour_data:
                del hour_data[wallet_address]

        if wallet_address in self._locks:
            del self._locks[wallet_address]

        logger.info(f"Cleared quota data for {wallet_address}")

    async def get_all_users_usage(self) -> Dict[str, Dict[str, Any]]:
        """
        Get usage summary for all users.

        Returns:
            Dictionary mapping wallet addresses to usage summaries
        """
        summary = {}

        for wallet_address in self._usage_cache.keys():
            try:
                report = await self.get_usage_report(wallet_address)
                # Return simplified report
                summary[wallet_address] = {
                    "role": report["user_role"],
                    "storage_mb": report["usage"]["storage"]["used_mb"],
                    "storage_limit_mb": report["usage"]["storage"]["limit_mb"],
                    "file_count": report["usage"]["workspace_files"]["count"],
                    "chat_hour": report["usage"]["chat"]["hourly_count"],
                    "chat_limit_hour": report["usage"]["chat"]["hourly_limit"],
                }
            except Exception as e:
                logger.error(f"Error getting usage for {wallet_address}: {e}")

        return summary


# Singleton instance for easy access
_default_manager: Optional[QuotaManager] = None


def get_quota_manager(redis_url: Optional[str] = None) -> QuotaManager:
    """
    Get or create the default QuotaManager instance.

    Args:
        redis_url: Optional Redis URL

    Returns:
        QuotaManager instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = QuotaManager(redis_url=redis_url)
    return _default_manager
