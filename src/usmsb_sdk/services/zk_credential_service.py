"""
ZK Credential Service for AI Civilization Platform

Reserved API for privacy-preserving credentials. Proof operations are disabled
until a reviewed circuit, trusted verification key and persistent replay
protection are integrated. Identity signatures are not ZK proofs.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CredentialType(StrEnum):
    """Credential types."""

    IDENTITY = "identity"
    SERVICE_PROVIDER = "service_provider"
    GOVERNANCE = "governance"
    PREMIUM = "premium"
    TRUSTED_NODE = "trusted_node"


class CredentialStatus(StrEnum):
    """Credential status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    USED = "used"


@dataclass
class ZKProof:
    """Zero-knowledge proof structure."""

    a: tuple[int, int]
    b: tuple[tuple[int, int], tuple[int, int]]
    c: tuple[int, int]
    public_inputs: list[int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "a": list(self.a),
            "b": [list(self.b[0]), list(self.b[1])],
            "c": list(self.c),
            "publicInputs": self.public_inputs,
        }


@dataclass
class Credential:
    """Credential structure."""

    credential_id: str
    holder: str
    cred_type: CredentialType
    valid_from: float
    valid_until: float
    commitment: str
    nullifier_hash: str
    status: CredentialStatus
    score: float
    metadata: dict[str, Any]
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "credentialId": self.credential_id,
            "holder": self.holder,
            "credType": self.cred_type.value,
            "validFrom": self.valid_from,
            "validUntil": self.valid_until,
            "commitment": self.commitment,
            "nullifierHash": self.nullifier_hash,
            "status": self.status.value,
            "score": self.score,
            "metadata": self.metadata,
            "createdAt": self.created_at,
        }


@dataclass
class PrivateInputs:
    """Private inputs for proof generation."""

    reputation: float
    stake: float
    no_slash: bool
    secret: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "reputation": self.reputation,
            "stake": self.stake,
            "noSlash": self.no_slash,
            "secret": self.secret,
        }


class ZKCredentialService:
    """
    ZK Credential Service.

    Handles proof generation, credential issuance, and verification.
    """

    MAX_CREDENTIAL_DURATION = 365 * 86400
    MIN_CREDENTIAL_DURATION = 86400

    def __init__(
        self,
        web3_provider=None,
        contract_address: str | None = None,
        reputation_service=None,
    ):
        self.web3 = web3_provider
        self.contract_address = contract_address
        self.reputation = reputation_service

        self._credentials: dict[str, Credential] = {}
        self._holder_credentials: dict[str, list[str]] = {}
        self._nullifiers: dict[str, bool] = {}

        self._running = False
        self._tasks: list[asyncio.Task] = []

        self.on_credential_issued: Callable[[Credential], None] | None = None
        self.on_credential_verified: Callable[[str, bool], None] | None = None

    async def start(self) -> None:
        self._running = True
        logger.info("ZK credential service started")

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        logger.info("ZK credential service stopped")

    async def generate_proof(
        self,
        credential_type: CredentialType,
        private_inputs: PrivateInputs,
        thresholds: dict[str, float],
    ) -> ZKProof | None:
        """No placeholder points or exposed private reputation may masquerade as proof."""
        logger.warning("ZK proof generation unavailable: no verified proof backend")
        return None

    def _calculate_commitment(self, inputs: PrivateInputs) -> str:
        """Calculate commitment from private inputs."""
        data = f"{inputs.reputation}:{inputs.stake}:{inputs.no_slash}:{inputs.secret}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _calculate_nullifier(self, secret: int) -> str:
        """Calculate nullifier from secret."""
        data = f"nullifier:{secret}"
        return hashlib.sha256(data.encode()).hexdigest()

    async def issue_credential(
        self,
        holder: str,
        credential_type: CredentialType,
        valid_duration: float,
        proof: ZKProof,
        score: float,
        metadata: dict[str, Any] | None = None,
    ) -> Credential | None:
        """Fail closed: stored metadata and caller-supplied curve points are not proofs."""
        logger.warning("ZK credential issuance unavailable: no verified proof backend")
        return None

    async def verify_credential(
        self,
        credential_id: str,
        proof: ZKProof,
        purpose: str = "verification",
    ) -> bool:
        """Never promote a timestamp/status check to cryptographic verification."""
        if self.on_credential_verified:
            self.on_credential_verified(credential_id, False)
        return False

    def _check_validity(self, credential: Credential) -> bool:
        """Old in-memory placeholder credentials cannot confer any authority."""
        return False

    async def revoke_credential(
        self,
        credential_id: str,
        reason: str,
    ) -> bool:
        """Revoke a credential."""
        credential = self._credentials.get(credential_id)
        if not credential:
            return False

        credential.status = CredentialStatus.REVOKED

        logger.info(f"Revoked credential {credential_id}: {reason}")

        return True

    def get_credential(self, credential_id: str) -> Credential | None:
        return self._credentials.get(credential_id)

    def is_credential_valid(self, credential_id: str) -> bool:
        credential = self._credentials.get(credential_id)
        return credential and self._check_validity(credential)

    def has_credential_type(
        self,
        holder: str,
        credential_type: CredentialType,
    ) -> bool:
        """Check if holder has a valid credential of given type."""
        cred_ids = self._holder_credentials.get(holder, [])
        for cid in cred_ids:
            cred = self._credentials.get(cid)
            if cred and cred.cred_type == credential_type and self._check_validity(cred):
                return True
        return False

    def get_holder_credentials(
        self,
        holder: str,
        credential_type: CredentialType | None = None,
    ) -> list[Credential]:
        """Get all credentials for a holder."""
        cred_ids = self._holder_credentials.get(holder, [])
        credentials = [self._credentials[cid] for cid in cred_ids if cid in self._credentials]

        if credential_type:
            credentials = [c for c in credentials if c.cred_type == credential_type]

        return credentials


_zk_credential_service: ZKCredentialService | None = None


async def get_zk_credential_service() -> ZKCredentialService:
    global _zk_credential_service
    if _zk_credential_service is None:
        _zk_credential_service = ZKCredentialService()
        await _zk_credential_service.start()
    return _zk_credential_service
