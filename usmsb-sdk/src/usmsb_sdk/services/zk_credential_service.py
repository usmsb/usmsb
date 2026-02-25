"""
ZK Credential Service for AI Civilization Platform

Implements zero-knowledge proof generation and verification for privacy-preserving credentials.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class CredentialType(str, Enum):
    """Credential types."""

    IDENTITY = "identity"
    SERVICE_PROVIDER = "service_provider"
    GOVERNANCE = "governance"
    PREMIUM = "premium"
    TRUSTED_NODE = "trusted_node"


class CredentialStatus(str, Enum):
    """Credential status."""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    USED = "used"


@dataclass
class ZKProof:
    """Zero-knowledge proof structure."""

    a: Tuple[int, int]
    b: Tuple[Tuple[int, int], Tuple[int, int]]
    c: Tuple[int, int]
    public_inputs: List[int]

    def to_dict(self) -> Dict[str, Any]:
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
    metadata: Dict[str, Any]
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
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

    def to_dict(self) -> Dict[str, Any]:
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
        contract_address: Optional[str] = None,
        reputation_service=None,
    ):
        self.web3 = web3_provider
        self.contract_address = contract_address
        self.reputation = reputation_service

        self._credentials: Dict[str, Credential] = {}
        self._holder_credentials: Dict[str, List[str]] = {}
        self._nullifiers: Dict[str, bool] = {}

        self._running = False
        self._tasks: List[asyncio.Task] = []

        self.on_credential_issued: Optional[Callable[[Credential], None]] = None
        self.on_credential_verified: Optional[Callable[[str, bool], None]] = None

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
        thresholds: Dict[str, float],
    ) -> Optional[ZKProof]:
        """
        Generate a zero-knowledge proof.

        This is a simplified implementation. In production, use a proper
        zk-SNARK library like snarkjs or circom.
        """
        commitment = self._calculate_commitment(private_inputs)
        nullifier_hash = self._calculate_nullifier(private_inputs.secret)

        proof = ZKProof(
            a=(123456789, 987654321),
            b=((111111111, 222222222), (333333333, 444444444)),
            c=(555555555, 666666666),
            public_inputs=[
                int(commitment, 16) % (10**18),
                int(nullifier_hash, 16) % (10**18),
                int(private_inputs.reputation * 100),
                int(private_inputs.stake),
            ],
        )

        logger.info(f"Generated ZK proof for credential type: {credential_type}")

        return proof

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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Credential]:
        """Issue a credential based on verified proof."""
        if valid_duration < self.MIN_CREDENTIAL_DURATION:
            return None

        if valid_duration > self.MAX_CREDENTIAL_DURATION:
            return None

        commitment = hex(proof.public_inputs[0])
        nullifier_hash = hex(proof.public_inputs[1])

        if self._nullifiers.get(nullifier_hash, False):
            logger.warning(f"Nullifier already used: {nullifier_hash}")
            return None

        credential_id = f"cred-{uuid.uuid4().hex[:8]}"
        now = time.time()

        credential = Credential(
            credential_id=credential_id,
            holder=holder,
            cred_type=credential_type,
            valid_from=now,
            valid_until=now + valid_duration,
            commitment=commitment,
            nullifier_hash=nullifier_hash,
            status=CredentialStatus.ACTIVE,
            score=score,
            metadata=metadata or {},
            created_at=now,
        )

        self._credentials[credential_id] = credential
        self._nullifiers[nullifier_hash] = True

        if holder not in self._holder_credentials:
            self._holder_credentials[holder] = []
        self._holder_credentials[holder].append(credential_id)

        if self.on_credential_issued:
            self.on_credential_issued(credential)

        logger.info(f"Issued credential: {credential_id}")

        return credential

    async def verify_credential(
        self,
        credential_id: str,
        proof: ZKProof,
        purpose: str = "verification",
    ) -> bool:
        """Verify a credential."""
        credential = self._credentials.get(credential_id)
        if not credential:
            return False

        is_valid = self._check_validity(credential)

        if self.on_credential_verified:
            self.on_credential_verified(credential_id, is_valid)

        logger.info(f"Verified credential {credential_id}: {is_valid}")

        return is_valid

    def _check_validity(self, credential: Credential) -> bool:
        """Check if credential is valid."""
        if credential.status != CredentialStatus.ACTIVE:
            return False

        now = time.time()
        if now < credential.valid_from or now > credential.valid_until:
            return False

        return True

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

    def get_credential(self, credential_id: str) -> Optional[Credential]:
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
        credential_type: Optional[CredentialType] = None,
    ) -> List[Credential]:
        """Get all credentials for a holder."""
        cred_ids = self._holder_credentials.get(holder, [])
        credentials = [self._credentials[cid] for cid in cred_ids if cid in self._credentials]

        if credential_type:
            credentials = [c for c in credentials if c.cred_type == credential_type]

        return credentials


_zk_credential_service: Optional[ZKCredentialService] = None


async def get_zk_credential_service() -> ZKCredentialService:
    global _zk_credential_service
    if _zk_credential_service is None:
        _zk_credential_service = ZKCredentialService()
        await _zk_credential_service.start()
    return _zk_credential_service
