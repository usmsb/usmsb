"""
IPFS Client Module

Handles IPFS storage operations with support for multiple gateways,
automatic failover, and encryption.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import aiohttp

from .encryption import Encryption


logger = logging.getLogger(__name__)


@dataclass
class IPFSGatewayConfig:
    """IPFS Gateway Configuration."""
    url: str
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class IPFSUploadResult:
    """Result of an IPFS upload operation."""
    success: bool
    cid: Optional[str] = None
    size: int = 0
    gateway_used: Optional[str] = None
    error: Optional[str] = None


@dataclass
class IPFSDownloadResult:
    """Result of an IPFS download operation."""
    success: bool
    data: Optional[bytes] = None
    size: int = 0
    gateway_used: Optional[str] = None
    error: Optional[str] = None


@dataclass
class UserDataPackage:
    """User data package for IPFS storage."""
    metadata: Dict[str, Any]
    profile: Optional[bytes] = None  # Encrypted profile data
    knowledge: Optional[bytes] = None  # Encrypted knowledge data
    checksum: Optional[str] = None


class IPFSClient:
    """
    IPFS Client for handling user data storage.

    Features:
    - Multiple gateway support with automatic failover
    - AES-256-GCM encryption for data security
    - Key derivation from wallet signatures
    - Automatic retry on failure
    - Async operations using aiohttp

    Usage:
        client = IPFSClient()
        result = await client.upload_user_data(wallet_address, data)
        if result.success:
            print(f"Uploaded with CID: {result.cid}")
    """

    # Default public IPFS gateways
    DEFAULT_GATEWAYS = [
        "https://ipfs.io/api/v0",
        "https://gateway.pinata.cloud/ipfs",
        "https://cloudflare-ipfs.com/ipfs",
    ]

    # API endpoints
    ADD_ENDPOINT = "add"
    CAT_ENDPOINT = "cat"
    PIN_ENDPOINT = "pin/add"

    def __init__(
        self,
        gateways: Optional[List[str]] = None,
        encryption_key: Optional[bytes] = None,
        timeout: int = 30
    ):
        """
        Initialize IPFS Client.

        Args:
            gateways: List of gateway URLs to use
            encryption_key: Optional pre-derived encryption key (32 bytes)
            timeout: Default timeout for requests (seconds)
        """
        self.gateways: List[str] = gateways or self.DEFAULT_GATEWAYS
        self.encryption_key = encryption_key
        self._current_gateway_index = 0
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(f"IPFS Client initialized with {len(self.gateways)} gateways")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("IPFS Client session closed")

    def _get_gateway_config(self) -> IPFSGatewayConfig:
        """Get the current gateway configuration."""
        url = self.gateways[self._current_gateway_index]
        return IPFSGatewayConfig(url=url, timeout=self.timeout)

    def _switch_gateway(self) -> Optional[str]:
        """
        Switch to the next available gateway.

        Returns:
            The new gateway URL, or None if no more gateways available
        """
        self._current_gateway_index = (self._current_gateway_index + 1) % len(self.gateways)

        if self._current_gateway_index == 0:
            logger.warning("All gateways exhausted, starting over")
        else:
            logger.info(f"Switching to gateway {self._current_gateway_index}: {self.gateways[self._current_gateway_index]}")

        return self.gateways[self._current_gateway_index]

    async def _try_gateways(
        self,
        operation: Callable[[str], Any],
        operation_name: str
    ) -> Any:
        """
        Try the operation on all available gateways until one succeeds.

        Args:
            operation: Async function that takes gateway URL as argument
            operation_name: Description of the operation for logging

        Returns:
            Result from the first successful gateway

        Raises:
            Exception: If all gateways fail
        """
        last_error = None
        tried_gateways = []

        for attempt in range(len(self.gateways)):
            gateway = self.gateways[self._current_gateway_index]
            tried_gateways.append(gateway)

            try:
                logger.debug(f"Attempting {operation_name} on gateway: {gateway}")
                result = await operation(gateway)
                logger.info(f"{operation_name} succeeded on gateway: {gateway}")
                return result

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(f"{operation_name} failed on gateway {gateway}: {e}")
                self._switch_gateway()

                # Add delay between gateway switches
                if attempt < len(self.gateways) - 1:
                    await asyncio.sleep(1.0)

            except Exception as e:
                last_error = e
                logger.error(f"{operation_name} unexpected error on gateway {gateway}: {e}")
                self._switch_gateway()

        error_msg = f"{operation_name} failed on all gateways: {tried_gateways}"
        logger.error(error_msg)
        raise Exception(error_msg) from last_error

    async def upload_user_data(
        self,
        wallet_address: str,
        data: Dict,
        encrypt: bool = True
    ) -> IPFSUploadResult:
        """
        Upload user data to IPFS with optional encryption.

        Args:
            wallet_address: User's wallet address
            data: Dictionary containing user data (profile, knowledge, etc.)
            encrypt: Whether to encrypt the data before upload

        Returns:
            IPFSUploadResult with CID if successful
        """
        if not data:
            return IPFSUploadResult(
                success=False,
                error="No data to upload"
            )

        try:
            # Prepare data package
            package = UserDataPackage(
                metadata={
                    "version": "1.0",
                    "wallet_address": wallet_address,
                    "created_at": asyncio.get_event_loop().time(),
                    "encryption": "AES-256-GCM" if encrypt else "none",
                    "files": []
                }
            )

            # Convert data to JSON and optionally encrypt
            data_json = json.dumps(data).encode('utf-8')

            if encrypt:
                if self.encryption_key is None:
                    logger.warning("No encryption key provided, uploading without encryption")
                    package.metadata["encryption"] = "none"
                    package.checksum = self._calculate_checksum(data_json)
                else:
                    encrypted = Encryption.encrypt(data_json, self.encryption_key)
                    package.knowledge = encrypted
                    package.checksum = self._calculate_checksum(encrypted)
                    package.metadata["files"].append("knowledge.enc")
            else:
                package.knowledge = data_json
                package.checksum = self._calculate_checksum(data_json)
                package.metadata["files"].append("knowledge.json")

            # Serialize package
            package_json = json.dumps({
                "metadata": package.metadata,
                "knowledge": package.knowledge.hex() if package.knowledge else None,
                "checksum": package.checksum
            }).encode('utf-8')

            # Upload to IPFS
            cid = await self._try_gateways(
                lambda gw: self._upload_bytes(gw, package_json, f"userdata_{wallet_address[:10]}"),
                "upload_user_data"
            )

            # Get file size
            size = len(package_json)

            logger.info(f"Uploaded user data for {wallet_address} to IPFS: CID={cid}, Size={size} bytes")

            return IPFSUploadResult(
                success=True,
                cid=cid,
                size=size,
                gateway_used=self.gateways[self._current_gateway_index]
            )

        except Exception as e:
            logger.error(f"Failed to upload user data for {wallet_address}: {e}")
            return IPFSUploadResult(
                success=False,
                error=str(e)
            )

    async def download_user_data(
        self,
        wallet_address: str,
        cid: Optional[str] = None,
        decrypt: bool = True
    ) -> Optional[Dict]:
        """
        Download user data from IPFS with optional decryption.

        Args:
            wallet_address: User's wallet address (for validation)
            cid: IPFS CID to download. If None, uses stored CID
            decrypt: Whether to decrypt the data after download

        Returns:
            Decrypted user data dictionary, or None if failed
        """
        if not cid:
            cid = await self.get_user_cid(wallet_address)

        if not cid:
            logger.error(f"No CID provided for wallet {wallet_address}")
            return None

        try:
            # Download from IPFS
            data = await self._try_gateways(
                lambda gw: self._download_bytes(gw, cid),
                "download_user_data"
            )

            if not data:
                logger.error(f"No data returned from IPFS for CID {cid}")
                return None

            # Parse package
            package_data = json.loads(data)

            # Verify checksum if present
            if "checksum" in package_data and package_data["checksum"]:
                if "knowledge" in package_data and package_data["knowledge"]:
                    encrypted = bytes.fromhex(package_data["knowledge"])
                    if self._calculate_checksum(encrypted) != package_data["checksum"]:
                        logger.warning(f"Checksum mismatch for CID {cid}")

            # Decrypt if needed
            if decrypt and self.encryption_key and "knowledge" in package_data:
                encrypted = bytes.fromhex(package_data["knowledge"])
                decrypted = Encryption.decrypt(encrypted, self.encryption_key)
                return json.loads(decrypted.decode('utf-8'))

            # Return raw data
            if "knowledge" in package_data:
                return json.loads(bytes.fromhex(package_data["knowledge"]).decode('utf-8'))

            return None

        except Exception as e:
            logger.error(f"Failed to download user data for {wallet_address} from CID {cid}: {e}")
            return None

    async def get_user_cid(self, wallet_address: str) -> Optional[str]:
        """
        Get the CID for user data.

        Note: This is a placeholder. In a full implementation,
        this would query a smart contract or IPNS to get the
        published CID for the wallet address.

        Args:
            wallet_address: User's wallet address

        Returns:
            CID string or None if not found
        """
        # TODO: Implement actual CID lookup from blockchain or IPNS
        logger.debug(f"get_user_cid called for {wallet_address} - not yet implemented")
        return None

    async def publish_cid(self, wallet_address: str, cid: str) -> bool:
        """
        Publish a CID to a public registry (blockchain or IPNS).

        Note: This is a placeholder. In a full implementation,
        this would publish the CID to a smart contract or create
        an IPNS record.

        Args:
            wallet_address: User's wallet address
            cid: IPFS CID to publish

        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement actual CID publishing to blockchain or IPNS
        logger.info(f"Publishing CID {cid} for wallet {wallet_address}")
        # Placeholder - always returns True for now
        return True

    async def _upload_bytes(
        self,
        gateway: str,
        data: bytes,
        filename: str = "data"
    ) -> str:
        """
        Upload bytes to IPFS via a gateway.

        Args:
            gateway: Gateway URL to use
            data: Raw data bytes to upload
            filename: Name for the uploaded file

        Returns:
            IPFS CID of the uploaded data

        Raises:
            aiohttp.ClientError: If upload fails
        """
        session = await self._get_session()

        # Build URL for add operation
        if "/ipfs/" in gateway:
            # Use gateway-style URL
            url = gateway.replace("/ipfs/", "/api/v0/add")
        else:
            url = f"{gateway}/add"

        # Prepare multipart form data
        form_data = aiohttp.FormData()
        form_data.add_field('file', data, filename=filename)

        async with session.post(url, data=form_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientError(f"Upload failed with status {response.status}: {error_text}")

            result = await response.json()

            if "Hash" not in result:
                raise aiohttp.ClientError(f"Invalid response: {result}")

            return result["Hash"]

    async def _download_bytes(
        self,
        gateway: str,
        cid: str
    ) -> bytes:
        """
        Download bytes from IPFS via a gateway.

        Args:
            gateway: Gateway URL to use
            cid: IPFS CID to download

        Returns:
            Raw data bytes

        Raises:
            aiohttp.ClientError: If download fails
        """
        session = await self._get_session()

        # Build URL for cat operation
        if "/ipfs/" in gateway:
            url = f"{gateway}/{cid}"
        else:
            url = f"{gateway}/cat?arg={cid}"

        async with session.get(url) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientError(f"Download failed with status {response.status}: {error_text}")

            return await response.read()

    @staticmethod
    def _calculate_checksum(data: bytes) -> str:
        """
        Calculate SHA-256 checksum of data.

        Args:
            data: Data bytes

        Returns:
            Hexadecimal checksum string
        """
        import hashlib
        return hashlib.sha256(data).hexdigest()

    async def pin_cid(self, cid: str) -> bool:
        """
        Pin a CID to ensure it's not garbage collected.

        Args:
            cid: IPFS CID to pin

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._try_gateways(
                lambda gw: self._pin_on_gateway(gw, cid),
                "pin_cid"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to pin CID {cid}: {e}")
            return False

    async def _pin_on_gateway(self, gateway: str, cid: str) -> str:
        """
        Pin a CID on a specific gateway.

        Args:
            gateway: Gateway URL
            cid: IPFS CID to pin

        Returns:
            CID string

        Raises:
            aiohttp.ClientError: If pin fails
        """
        session = await self._get_session()

        if "/ipfs/" in gateway:
            url = gateway.replace("/ipfs/", "/api/v0/pin/add")
        else:
            url = f"{gateway}/pin/add"

        form_data = aiohttp.FormData()
        form_data.add_field('arg', cid)

        async with session.post(url, data=form_data) as response:
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientError(f"Pin failed with status {response.status}: {error_text}")

            result = await response.json()

            if "Pins" not in result or cid not in result.get("Pins", []):
                raise aiohttp.ClientError(f"Pin failed: {result}")

            return cid

    def set_encryption_key(self, key: bytes) -> None:
        """
        Set the encryption key for the client.

        Args:
            key: 32-byte encryption key

        Raises:
            ValueError: If key is not 32 bytes
        """
        if len(key) != 32:
            raise ValueError(f"Encryption key must be 32 bytes, got {len(key)} bytes")
        self.encryption_key = key
        logger.debug("Encryption key updated")

    def derive_and_set_key(self, signature: str) -> None:
        """
        Derive encryption key from signature and set it.

        Args:
            signature: Wallet signature string
        """
        key = Encryption.derive_key_from_signature(signature)
        self.encryption_key = key
        logger.info(f"Derived encryption key from signature (hash: {Encryption.hash_key(key)[:16]}...)")
