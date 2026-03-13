"""
Authentication Coordinator Module

Provides coordinated authentication verification combining wallet and stake verification.
"""

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from usmsb_sdk.platform.external.auth.base_auth import (
    AuthContext,
    FullAuthResult,
    Permission,
)
from usmsb_sdk.platform.external.auth.wallet_auth import (
    IWalletAuthenticator,
    MockWalletAuthenticator,
    WalletAuthResult,
)
from usmsb_sdk.platform.external.auth.stake_verifier import (
    IStakeVerifier,
    MockStakeVerifier,
    StakeVerificationResult,
    MINIMUM_STAKE_FOR_REGISTRATION,
)


# Constants
SESSION_DURATION_HOURS = 24 * 7  # 7 days
MAX_SESSION_DURATION_HOURS = 24 * 30  # 30 days


@dataclass
class SessionInfo:
    """
    Information about an authenticated session.

    Attributes:
        session_id: Unique session identifier
        session_token: Token for session authentication
        wallet_address: Authenticated wallet address
        agent_id: Associated agent ID if any
        did: Decentralized identifier
        permissions: Granted permissions
        created_at: When session was created
        expires_at: When session expires
        last_activity: Last activity timestamp
        is_valid: Whether session is currently valid
    """
    session_id: str
    session_token: str
    wallet_address: str
    agent_id: Optional[str] = None
    did: Optional[str] = None
    permissions: List[Permission] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=SESSION_DURATION_HOURS))
    last_activity: datetime = field(default_factory=datetime.now)
    is_valid: bool = True


@dataclass
class VerificationContext:
    """
    Context for coordinated verification.

    Attributes:
        auth_context: Base authentication context
        require_stake: Whether stake verification is required
        minimum_stake: Minimum required stake amount
        require_agent_binding: Whether agent binding is required
        agent_id: Specific agent ID to verify binding for
        session_duration_hours: Custom session duration
    """
    auth_context: AuthContext
    require_stake: bool = True
    minimum_stake: float = MINIMUM_STAKE_FOR_REGISTRATION
    require_agent_binding: bool = False
    agent_id: Optional[str] = None
    session_duration_hours: int = SESSION_DURATION_HOURS


class AuthCoordinator:
    """
    Coordinates wallet and stake verification for complete authentication.

    This class orchestrates the authentication flow by combining:
    1. Wallet signature verification
    2. Stake amount verification
    3. Session management
    """

    def __init__(
        self,
        wallet_authenticator: Optional[IWalletAuthenticator] = None,
        stake_verifier: Optional[IStakeVerifier] = None,
        session_duration_hours: int = SESSION_DURATION_HOURS
    ):
        """
        Initialize the authentication coordinator.

        Args:
            wallet_authenticator: Wallet authentication provider
            stake_verifier: Stake verification provider
            session_duration_hours: Default session duration
        """
        self._wallet_auth = wallet_authenticator or MockWalletAuthenticator()
        self._stake_verifier = stake_verifier or MockStakeVerifier()
        self._session_duration = min(session_duration_hours, MAX_SESSION_DURATION_HOURS)
        self._sessions: Dict[str, SessionInfo] = {}  # session_id -> info
        self._token_to_session: Dict[str, str] = {}  # token -> session_id

    async def initialize(self) -> bool:
        """
        Initialize the coordinator and all providers.

        Returns:
            True if all providers initialized successfully
        """
        wallet_init = await self._wallet_auth.initialize()
        stake_init = await self._stake_verifier.initialize()
        return wallet_init and stake_init

    async def shutdown(self) -> bool:
        """
        Shutdown the coordinator and all providers.

        Returns:
            True if all providers shut down successfully
        """
        wallet_shutdown = await self._wallet_auth.shutdown()
        stake_shutdown = await self._stake_verifier.shutdown()
        return wallet_shutdown and stake_shutdown

    def is_ready(self) -> bool:
        """Check if the coordinator is ready."""
        return self._wallet_auth.is_ready() and self._stake_verifier.is_ready()

    async def verify_for_registration(
        self,
        context: VerificationContext
    ) -> FullAuthResult:
        """
        Perform full verification for agent registration.

        This verifies:
        1. Wallet ownership via signature
        2. Sufficient stake for registration
        3. Capacity to register new agent

        Args:
            context: Verification context with all required data

        Returns:
            FullAuthResult with complete verification status
        """
        if not self.is_ready():
            return FullAuthResult(
                success=False,
                error_code="NOT_INITIALIZED",
                error_message="Auth coordinator not initialized"
            )

        # Step 1: Verify wallet
        wallet_result = await self._verify_wallet(context.auth_context)
        if not wallet_result.success:
            return FullAuthResult(
                success=False,
                wallet_auth=wallet_result,
                error_code="WALLET_VERIFICATION_FAILED",
                error_message=wallet_result.error_message
            )

        # Step 2: Verify stake
        stake_result = await self._verify_stake(
            context.auth_context.wallet_address,
            context.minimum_stake
        )

        # For registration, we need sufficient stake AND capacity
        if not stake_result.can_register:
            return FullAuthResult(
                success=False,
                wallet_auth=wallet_result,
                stake_verification=stake_result,
                error_code="REGISTRATION_NOT_ALLOWED",
                error_message=(
                    f"Cannot register agent: active_agents={stake_result.active_agents}, "
                    f"max_agents={stake_result.max_agents}"
                )
            )

        # Step 3: Create session
        session = await self._create_session(
            wallet_result,
            stake_result,
            context.auth_context.agent_id,
            context.session_duration_hours
        )

        # Build combined permissions
        permissions = self._calculate_permissions(
            wallet_result,
            stake_result
        )

        return FullAuthResult(
            success=True,
            wallet_auth=wallet_result,
            stake_verification=stake_result,
            agent_id=context.auth_context.agent_id,
            session_token=session.session_token,
            permissions=permissions,
            valid_until=session.expires_at
        )

    async def verify_for_communication(
        self,
        context: VerificationContext
    ) -> FullAuthResult:
        """
        Perform verification for agent communication.

        This verifies:
        1. Wallet ownership via signature
        2. Minimum stake (if required)
        3. Agent binding (if required)

        Args:
            context: Verification context with all required data

        Returns:
            FullAuthResult with verification status
        """
        if not self.is_ready():
            return FullAuthResult(
                success=False,
                error_code="NOT_INITIALIZED",
                error_message="Auth coordinator not initialized"
            )

        # Step 1: Verify wallet
        wallet_result = await self._verify_wallet(context.auth_context)
        if not wallet_result.success:
            return FullAuthResult(
                success=False,
                wallet_auth=wallet_result,
                error_code="WALLET_VERIFICATION_FAILED",
                error_message=wallet_result.error_message
            )

        # Step 2: Verify stake if required
        stake_result = None
        if context.require_stake:
            stake_result = await self._verify_stake(
                context.auth_context.wallet_address,
                context.minimum_stake
            )
            if not stake_result.success:
                return FullAuthResult(
                    success=False,
                    wallet_auth=wallet_result,
                    stake_verification=stake_result,
                    error_code="INSUFFICIENT_STAKE",
                    error_message=stake_result.error_message
                )

        # Step 3: Verify agent binding if required
        if context.require_agent_binding and context.agent_id:
            is_bound = await self._wallet_auth.is_wallet_bound(
                context.auth_context.wallet_address,
                context.agent_id
            )
            if not is_bound:
                return FullAuthResult(
                    success=False,
                    wallet_auth=wallet_result,
                    stake_verification=stake_result,
                    agent_id=context.agent_id,
                    error_code="AGENT_NOT_BOUND",
                    error_message=f"Wallet not bound to agent {context.agent_id}"
                )

        # Step 4: Create or extend session
        session = await self._create_session(
            wallet_result,
            stake_result,
            context.agent_id,
            context.session_duration_hours
        )

        # Build combined permissions
        permissions = self._calculate_permissions(
            wallet_result,
            stake_result
        )

        return FullAuthResult(
            success=True,
            wallet_auth=wallet_result,
            stake_verification=stake_result,
            agent_id=context.agent_id,
            session_token=session.session_token,
            permissions=permissions,
            valid_until=session.expires_at
        )

    async def validate_session(
        self,
        session_token: str
    ) -> Optional[SessionInfo]:
        """
        Validate a session token and return session info.

        Args:
            session_token: The session token to validate

        Returns:
            SessionInfo if valid, None otherwise
        """
        session_id = self._token_to_session.get(session_token)
        if not session_id:
            return None

        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check expiration
        if datetime.now() > session.expires_at:
            await self.invalidate_session(session_token)
            return None

        # Update last activity
        session.last_activity = datetime.now()
        return session

    async def invalidate_session(
        self,
        session_token: str
    ) -> bool:
        """
        Invalidate a session.

        Args:
            session_token: The session token to invalidate

        Returns:
            True if session was invalidated
        """
        session_id = self._token_to_session.get(session_token)
        if not session_id:
            return False

        if session_id in self._sessions:
            self._sessions[session_id].is_valid = False
            del self._sessions[session_id]

        del self._token_to_session[session_token]
        return True

    async def invalidate_all_sessions(
        self,
        wallet_address: str
    ) -> int:
        """
        Invalidate all sessions for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            Number of sessions invalidated
        """
        wallet_address = wallet_address.lower()
        count = 0

        tokens_to_remove = []
        for token, session_id in self._token_to_session.items():
            session = self._sessions.get(session_id)
            if session and session.wallet_address == wallet_address:
                tokens_to_remove.append(token)

        for token in tokens_to_remove:
            if await self.invalidate_session(token):
                count += 1

        return count

    # Private helper methods

    async def _verify_wallet(
        self,
        context: AuthContext
    ) -> WalletAuthResult:
        """Verify wallet using the wallet authenticator."""
        return await self._wallet_auth.verify_wallet_with_context(context)

    async def _verify_stake(
        self,
        wallet_address: str,
        minimum_amount: float
    ) -> StakeVerificationResult:
        """Verify stake using the stake verifier."""
        return await self._stake_verifier.verify_stake(
            wallet_address,
            minimum_amount
        )

    async def _create_session(
        self,
        wallet_result: WalletAuthResult,
        stake_result: Optional[StakeVerificationResult],
        agent_id: Optional[str],
        duration_hours: int
    ) -> SessionInfo:
        """Create a new authenticated session."""
        session_id = secrets.token_hex(16)
        session_token = self._generate_session_token(
            session_id,
            wallet_result.wallet_address
        )

        permissions = self._calculate_permissions(wallet_result, stake_result)

        session = SessionInfo(
            session_id=session_id,
            session_token=session_token,
            wallet_address=wallet_result.wallet_address,
            agent_id=agent_id,
            did=wallet_result.did,
            permissions=permissions,
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=duration_hours),
            last_activity=datetime.now(),
            is_valid=True
        )

        self._sessions[session_id] = session
        self._token_to_session[session_token] = session_id

        return session

    def _generate_session_token(
        self,
        session_id: str,
        wallet_address: str
    ) -> str:
        """Generate a secure session token."""
        data = f"{session_id}:{wallet_address}:{datetime.now().timestamp()}:{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_permissions(
        self,
        wallet_result: WalletAuthResult,
        stake_result: Optional[StakeVerificationResult]
    ) -> List[Permission]:
        """Calculate combined permissions based on verification results."""
        permissions = [Permission.READ]  # Base permission

        if wallet_result.is_verified:
            permissions.append(Permission.WRITE)

        if stake_result and stake_result.success:
            stake_permission = Permission.from_stake_amount(stake_result.stake_amount)
            if stake_permission not in permissions:
                permissions.append(stake_permission)

            # Add execute permission for sufficient stake
            if stake_result.stake_amount >= 1000:
                permissions.append(Permission.EXECUTE)

        return list(set(permissions))

    # Testing utilities

    def get_active_sessions(self) -> List[SessionInfo]:
        """Get all active sessions - useful for testing."""
        return [
            s for s in self._sessions.values()
            if s.is_valid and datetime.now() <= s.expires_at
        ]

    def clear_all_sessions(self) -> None:
        """Clear all sessions - useful for testing."""
        self._sessions.clear()
        self._token_to_session.clear()

    @property
    def wallet_authenticator(self) -> IWalletAuthenticator:
        """Get the wallet authenticator instance."""
        return self._wallet_auth

    @property
    def stake_verifier(self) -> IStakeVerifier:
        """Get the stake verifier instance."""
        return self._stake_verifier
