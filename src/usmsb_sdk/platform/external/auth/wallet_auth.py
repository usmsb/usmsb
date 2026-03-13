"""
Wallet Authentication Module

Provides wallet signature verification and wallet-agent binding interfaces.
"""

from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Set

from usmsb_sdk.platform.external.auth.base_auth import (
    AuthContext,
    BaseAuthResult,
    IAuthProvider,
    Permission,
    WalletAuthResult,
)


@dataclass
class WalletBinding:
    """
    Represents a binding between a wallet and an agent.

    Attributes:
        wallet_address: The wallet address
        agent_id: The bound agent identifier
        bound_at: When the binding was created
        binding_type: Type of binding (owner, operator, etc.)
        permissions: Permissions granted to this binding
        is_active: Whether the binding is currently active
    """
    wallet_address: str
    agent_id: str
    bound_at: datetime = field(default_factory=datetime.now)
    binding_type: str = "owner"
    permissions: Permission = Permission.OWNER
    is_active: bool = True


class IWalletAuthenticator(IAuthProvider):
    """
    Abstract interface for wallet authentication.

    Provides methods for verifying wallet signatures and
    managing wallet-agent bindings.
    """

    @abstractmethod
    async def verify_wallet(
        self,
        wallet_address: str,
        signature: str,
        message: str
    ) -> WalletAuthResult:
        """
        Verify wallet ownership by validating a cryptographic signature.

        Args:
            wallet_address: The wallet address to verify
            signature: The cryptographic signature
            message: The message that was signed

        Returns:
            WalletAuthResult with verification status
        """
        pass

    @abstractmethod
    async def verify_wallet_with_context(
        self,
        context: AuthContext
    ) -> WalletAuthResult:
        """
        Verify wallet using an authentication context.

        Args:
            context: Authentication context with all required data

        Returns:
            WalletAuthResult with verification status
        """
        pass

    @abstractmethod
    async def is_wallet_bound(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """
        Check if a wallet is bound to a specific agent.

        Args:
            wallet_address: The wallet address to check
            agent_id: The agent identifier

        Returns:
            True if wallet is bound to the agent
        """
        pass

    @abstractmethod
    async def bind_wallet_to_agent(
        self,
        wallet_address: str,
        agent_id: str,
        binding_type: str = "owner"
    ) -> WalletBinding:
        """
        Create a binding between a wallet and an agent.

        Args:
            wallet_address: The wallet address
            agent_id: The agent identifier
            binding_type: Type of binding (owner, operator, etc.)

        Returns:
            WalletBinding representing the created binding
        """
        pass

    @abstractmethod
    async def unbind_wallet_from_agent(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """
        Remove a binding between a wallet and an agent.

        Args:
            wallet_address: The wallet address
            agent_id: The agent identifier

        Returns:
            True if unbinding successful
        """
        pass

    @abstractmethod
    async def get_wallet_bindings(
        self,
        wallet_address: str
    ) -> list[WalletBinding]:
        """
        Get all agent bindings for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            List of WalletBinding objects
        """
        pass

    @abstractmethod
    async def get_agent_bindings(
        self,
        agent_id: str
    ) -> list[WalletBinding]:
        """
        Get all wallet bindings for an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            List of WalletBinding objects
        """
        pass

    @abstractmethod
    async def generate_did(self, wallet_address: str) -> str:
        """
        Generate a decentralized identifier (DID) for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            DID string
        """
        pass

    @abstractmethod
    async def validate_nonce(
        self,
        wallet_address: str,
        nonce: str
    ) -> bool:
        """
        Validate a nonce for replay protection.

        Args:
            wallet_address: The wallet address
            nonce: The nonce to validate

        Returns:
            True if nonce is valid and unused
        """
        pass


class MockWalletAuthenticator(IWalletAuthenticator):
    """
    Mock implementation of IWalletAuthenticator for testing.

    This implementation stores all data in memory and performs
    simplified signature verification suitable for testing.
    """

    def __init__(self):
        """Initialize the mock authenticator."""
        self._initialized: bool = False
        self._bindings: Dict[str, Set[str]] = {}  # wallet -> set of agent_ids
        self._agent_bindings: Dict[str, Set[str]] = {}  # agent -> set of wallets
        self._binding_details: Dict[tuple, WalletBinding] = {}  # (wallet, agent) -> binding
        self._used_nonces: Set[str] = set()
        self._did_counter: int = 0

    async def initialize(self) -> bool:
        """Initialize the mock authenticator."""
        self._initialized = True
        return True

    async def shutdown(self) -> bool:
        """Shutdown the mock authenticator."""
        self._initialized = False
        return True

    def is_ready(self) -> bool:
        """Check if the provider is ready."""
        return self._initialized

    async def verify_wallet(
        self,
        wallet_address: str,
        signature: str,
        message: str
    ) -> WalletAuthResult:
        """
        Mock verification - accepts any non-empty signature.

        In production, this would use web3.py or similar to verify
        the cryptographic signature.
        """
        if not self._initialized:
            return WalletAuthResult(
                success=False,
                error_code="NOT_INITIALIZED",
                error_message="Authenticator not initialized"
            )

        # Normalize address
        wallet_address = wallet_address.lower()

        # Mock verification - accept any non-empty signature
        if not signature or not message:
            return WalletAuthResult(
                success=False,
                wallet_address=wallet_address,
                is_verified=False,
                error_code="INVALID_SIGNATURE",
                error_message="Signature or message is empty"
            )

        # Generate DID
        did = await self.generate_did(wallet_address)

        return WalletAuthResult(
            success=True,
            wallet_address=wallet_address,
            is_verified=True,
            did=did,
            permissions=Permission.READ,
            expires_at=datetime.now() + timedelta(hours=24)
        )

    async def verify_wallet_with_context(
        self,
        context: AuthContext
    ) -> WalletAuthResult:
        """Verify wallet using authentication context."""
        if not context.signature or not context.message:
            return WalletAuthResult(
                success=False,
                wallet_address=context.wallet_address,
                is_verified=False,
                error_code="MISSING_CREDENTIALS",
                error_message="Signature or message missing from context"
            )

        return await self.verify_wallet(
            context.wallet_address,
            context.signature,
            context.message
        )

    async def is_wallet_bound(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """Check if wallet is bound to agent."""
        wallet_address = wallet_address.lower()
        return (
            wallet_address in self._bindings and
            agent_id in self._bindings[wallet_address]
        )

    async def bind_wallet_to_agent(
        self,
        wallet_address: str,
        agent_id: str,
        binding_type: str = "owner"
    ) -> WalletBinding:
        """Create a binding between wallet and agent."""
        wallet_address = wallet_address.lower()

        # Initialize sets if needed
        if wallet_address not in self._bindings:
            self._bindings[wallet_address] = set()
        if agent_id not in self._agent_bindings:
            self._agent_bindings[agent_id] = set()

        # Create binding
        self._bindings[wallet_address].add(agent_id)
        self._agent_bindings[agent_id].add(wallet_address)

        binding = WalletBinding(
            wallet_address=wallet_address,
            agent_id=agent_id,
            binding_type=binding_type,
            permissions=Permission.OWNER if binding_type == "owner" else Permission.EXECUTE
        )

        self._binding_details[(wallet_address, agent_id)] = binding
        return binding

    async def unbind_wallet_from_agent(
        self,
        wallet_address: str,
        agent_id: str
    ) -> bool:
        """Remove binding between wallet and agent."""
        wallet_address = wallet_address.lower()

        if wallet_address in self._bindings:
            self._bindings[wallet_address].discard(agent_id)
        if agent_id in self._agent_bindings:
            self._agent_bindings[agent_id].discard(wallet_address)

        if (wallet_address, agent_id) in self._binding_details:
            del self._binding_details[(wallet_address, agent_id)]
            return True
        return False

    async def get_wallet_bindings(
        self,
        wallet_address: str
    ) -> list[WalletBinding]:
        """Get all agent bindings for a wallet."""
        wallet_address = wallet_address.lower()
        bindings = []

        if wallet_address in self._bindings:
            for agent_id in self._bindings[wallet_address]:
                key = (wallet_address, agent_id)
                if key in self._binding_details:
                    bindings.append(self._binding_details[key])

        return bindings

    async def get_agent_bindings(
        self,
        agent_id: str
    ) -> list[WalletBinding]:
        """Get all wallet bindings for an agent."""
        bindings = []

        if agent_id in self._agent_bindings:
            for wallet_address in self._agent_bindings[agent_id]:
                key = (wallet_address, agent_id)
                if key in self._binding_details:
                    bindings.append(self._binding_details[key])

        return bindings

    async def generate_did(self, wallet_address: str) -> str:
        """Generate a DID for a wallet."""
        wallet_address = wallet_address.lower()
        self._did_counter += 1
        return f"did:usmsb:{wallet_address[:8]}:{self._did_counter}"

    async def validate_nonce(
        self,
        wallet_address: str,
        nonce: str
    ) -> bool:
        """Validate a nonce for replay protection."""
        if nonce in self._used_nonces:
            return False
        self._used_nonces.add(nonce)
        return True

    def clear_all_bindings(self) -> None:
        """Clear all bindings - useful for testing."""
        self._bindings.clear()
        self._agent_bindings.clear()
        self._binding_details.clear()

    def clear_used_nonces(self) -> None:
        """Clear used nonces - useful for testing."""
        self._used_nonces.clear()
