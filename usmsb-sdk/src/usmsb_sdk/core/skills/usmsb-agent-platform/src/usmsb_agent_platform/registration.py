"""
Agent registration module for self-registration and Owner binding.
"""

import hashlib
import secrets
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple
import aiohttp


# Configuration constants
AGENT_ID_PREFIX = "agent-"
AGENT_ID_LENGTH = 12
AGENT_NAME_MAX_LENGTH = 100

API_KEY_PREFIX = "usmsb_"
API_KEY_HASH_LENGTH = 16
API_KEY_DEFAULT_EXPIRE_DAYS = 365
API_KEY_MAX_EXPIRE_DAYS = 3650
API_KEY_MAX_PER_AGENT = 10

BINDING_CODE_PREFIX = "bind-"
BINDING_CODE_EXPIRE_SECONDS = 3600  # 1 hour


def generate_agent_id() -> str:
    """Generate a unique Agent ID."""
    random_bytes = secrets.token_hex(AGENT_ID_LENGTH // 2 + 2)
    return f"{AGENT_ID_PREFIX}{random_bytes[:AGENT_ID_LENGTH]}"


def generate_api_key(agent_id: str, timestamp: Optional[int] = None) -> str:
    """
    Generate an API Key for an Agent.

    Format: usmsb_{hash}_{timestamp}
    """
    if timestamp is None:
        timestamp = int(time.time())

    raw = f"{agent_id}:{timestamp}:{secrets.token_hex(16)}"
    hash_val = hashlib.sha256(raw.encode()).hexdigest()[:API_KEY_HASH_LENGTH]

    return f"{API_KEY_PREFIX}{hash_val}_{timestamp}"


def generate_binding_code() -> Tuple[str, int]:
    """
    Generate a binding code for Owner binding.

    Returns:
        (binding_code, expires_at_timestamp)
    """
    code = f"{BINDING_CODE_PREFIX}{secrets.token_urlsafe(8)}"
    expires_at = int(time.time()) + BINDING_CODE_EXPIRE_SECONDS
    return code, expires_at


def hash_api_key(api_key: str) -> str:
    """Hash an API Key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


@dataclass
class RegistrationResult:
    """Result of Agent registration."""
    success: bool
    agent_id: Optional[str] = None
    api_key: Optional[str] = None
    level: int = 0
    message: str = ""
    error: Optional[str] = None
    code: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"success": self.success, "level": self.level}
        if self.agent_id:
            d["agent_id"] = self.agent_id
        if self.api_key:
            d["api_key"] = self.api_key
        if self.message:
            d["message"] = self.message
        if self.error:
            d["error"] = self.error
        if self.code:
            d["code"] = self.code
        return d


@dataclass
class BindingRequestResult:
    """Result of binding request."""
    success: bool
    binding_code: Optional[str] = None
    binding_url: Optional[str] = None
    expires_at: Optional[int] = None
    expires_in: Optional[int] = None
    message: str = ""
    error: Optional[str] = None
    code: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"success": self.success}
        if self.binding_code:
            d["binding_code"] = self.binding_code
        if self.binding_url:
            d["binding_url"] = self.binding_url
        if self.expires_at:
            d["expires_at"] = self.expires_at
        if self.expires_in:
            d["expires_in"] = self.expires_in
        if self.message:
            d["message"] = self.message
        if self.error:
            d["error"] = self.error
        if self.code:
            d["code"] = self.code
        return d


@dataclass
class BindingStatus:
    """Agent binding status."""
    bound: bool
    owner_wallet: Optional[str] = None
    stake_tier: Optional[str] = None
    stake_amount: Optional[int] = None
    bound_at: Optional[int] = None

    def to_dict(self) -> dict:
        d = {"bound": self.bound}
        if self.owner_wallet:
            d["owner_wallet"] = self.owner_wallet
        if self.stake_tier:
            d["stake_tier"] = self.stake_tier
        if self.stake_amount is not None:
            d["stake_amount"] = self.stake_amount
        if self.bound_at:
            d["bound_at"] = self.bound_at
        return d


@dataclass
class APIKeyInfo:
    """API Key information."""
    id: str
    name: str
    created_at: int
    expires_at: int
    last_used_at: Optional[int] = None
    revoked: bool = False

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "revoked": self.revoked
        }
        if self.last_used_at:
            d["last_used_at"] = self.last_used_at
        return d


class RegistrationClient:
    """Client for Agent registration operations."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def register(
        self,
        name: str,
        description: str = "",
        capabilities: Optional[List[str]] = None
    ) -> RegistrationResult:
        """
        Register a new Agent (self-registration, no Owner required).

        Args:
            name: Agent name
            description: Agent description
            capabilities: List of capabilities

        Returns:
            RegistrationResult with agent_id and api_key
        """
        # Validate name
        if not name or len(name) > AGENT_NAME_MAX_LENGTH:
            return RegistrationResult(
                success=False,
                error=f"Name must be 1-{AGENT_NAME_MAX_LENGTH} characters",
                code="INVALID_NAME"
            )

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/agents/v2/register",
                json={
                    "name": name,
                    "description": description,
                    "capabilities": capabilities or []
                }
            ) as resp:
                data = await resp.json()

                if resp.status == 200 and data.get("success"):
                    return RegistrationResult(
                        success=True,
                        agent_id=data.get("agent_id"),
                        api_key=data.get("api_key"),
                        level=data.get("level", 0),
                        message=data.get("message", "注册成功")
                    )
                else:
                    return RegistrationResult(
                        success=False,
                        error=data.get("error", "Registration failed"),
                        code=data.get("code", "REGISTRATION_FAILED")
                    )

        except aiohttp.ClientError as e:
            return RegistrationResult(
                success=False,
                error=f"Network error: {str(e)}",
                code="NETWORK_ERROR"
            )
        except Exception as e:
            return RegistrationResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                code="INTERNAL_ERROR"
            )

    async def request_binding(
        self,
        api_key: str,
        agent_id: str,
        message: str = ""
    ) -> BindingRequestResult:
        """
        Request Owner binding.

        Args:
            api_key: Agent's API key
            agent_id: Agent's ID
            message: Optional message for Owner

        Returns:
            BindingRequestResult with binding_code and binding_url
        """
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/agents/v2/{agent_id}/request-binding",
                headers={
                    "X-API-Key": api_key,
                    "X-Agent-ID": agent_id,
                },
                json={"message": message}
            ) as resp:
                data = await resp.json()

                if resp.status == 200 and data.get("success"):
                    return BindingRequestResult(
                        success=True,
                        binding_code=data.get("binding_code"),
                        binding_url=data.get("binding_url"),
                        expires_at=data.get("expires_at"),
                        expires_in=data.get("expires_in"),
                        message=data.get("message", "")
                    )
                else:
                    return BindingRequestResult(
                        success=False,
                        error=data.get("error", "Request failed"),
                        code=data.get("code", "REQUEST_FAILED")
                    )

        except Exception as e:
            return BindingRequestResult(
                success=False,
                error=str(e),
                code="INTERNAL_ERROR"
            )

    async def get_binding_status(self, api_key: str, agent_id: str) -> BindingStatus:
        """Get Agent's binding status."""
        try:
            session = await self._get_session()
            async with session.get(
                f"{self.base_url}/api/agents/v2/{agent_id}/binding-status",
                headers={
                    "X-API-Key": api_key,
                    "X-Agent-ID": agent_id,
                }
            ) as resp:
                data = await resp.json()

                return BindingStatus(
                    bound=data.get("bound", False),
                    owner_wallet=data.get("owner_wallet"),
                    stake_tier=data.get("stake_tier"),
                    stake_amount=data.get("stake_amount"),
                    bound_at=data.get("bound_at")
                )

        except Exception:
            return BindingStatus(bound=False)
