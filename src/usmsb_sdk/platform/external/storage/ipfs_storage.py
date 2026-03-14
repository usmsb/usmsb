"""
IPFS Storage Implementation

Provides decentralized storage using IPFS (InterPlanetary File System).
Features:
- CID upload and download
- Data sharding and reassembly
- Public IPFS network connectivity
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Union

from usmsb_sdk.platform.external.storage.base_storage import (
    DataLocation,
    StorageError,
    StorageInterface,
    StorageResult,
    StorageType,
)

logger = logging.getLogger(__name__)


class IPFSGateway(Enum):
    """Common IPFS gateways."""
    IPFS_IO = "https://ipfs.io/ipfs/"
    CLOUDFLARE = "https://cloudflare-ipfs.com/ipfs/"
    DWEB = "https://dweb.link/ipfs/"
    PINATA = "https://gateway.pinata.cloud/ipfs/"
    LOCAL = "http://127.0.0.1:8080/ipfs/"


@dataclass
class IPFSConnectionConfig:
    """Configuration for IPFS connection."""
    gateway_url: str = "https://ipfs.io/ipfs/"
    api_url: str = "/ip4/127.0.0.1/tcp/5001"
    timeout: int = 60
    use_client: bool = True  # Use ipfshttpclient if available
    fallback_to_gateway: bool = True
    pin_content: bool = True
    chunk_size: int = 1024 * 1024  # 1MB chunks for sharding

    @classmethod
    def default(cls) -> "IPFSConnectionConfig":
        """Get default configuration."""
        return cls()

    @classmethod
    def for_public_gateway(cls, gateway: IPFSGateway = IPFSGateway.IPFS_IO) -> "IPFSConnectionConfig":
        """Configure for public gateway (read-only)."""
        return cls(
            gateway_url=gateway.value,
            use_client=False,
            fallback_to_gateway=True,
            pin_content=False,
        )

    @classmethod
    def for_local_node(cls) -> "IPFSConnectionConfig":
        """Configure for local IPFS node."""
        return cls(
            gateway_url=IPFSGateway.LOCAL.value,
            api_url="/ip4/127.0.0.1/tcp/5001",
            use_client=True,
            pin_content=True,
        )


@dataclass
class ShardInfo:
    """Information about a data shard."""
    index: int
    cid: str
    size: int
    checksum: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "cid": self.cid,
            "size": self.size,
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShardInfo":
        return cls(
            index=data["index"],
            cid=data["cid"],
            size=data["size"],
            checksum=data["checksum"],
        )


@dataclass
class ShardedDataInfo:
    """Information about sharded data."""
    original_cid: str
    total_shards: int
    total_size: int
    original_checksum: str
    shards: list[ShardInfo]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_cid": self.original_cid,
            "total_shards": self.total_shards,
            "total_size": self.total_size,
            "original_checksum": self.original_checksum,
            "shards": [s.to_dict() for s in self.shards],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShardedDataInfo":
        return cls(
            original_cid=data["original_cid"],
            total_shards=data["total_shards"],
            total_size=data["total_size"],
            original_checksum=data["original_checksum"],
            shards=[ShardInfo.from_dict(s) for s in data["shards"]],
            metadata=data.get("metadata", {}),
        )


class DataShardingManager:
    """
    Manages data sharding and reassembly for large files.

    Splits large data into smaller chunks for efficient IPFS storage.
    """

    def __init__(self, chunk_size: int = 1024 * 1024):
        """
        Initialize sharding manager.

        Args:
            chunk_size: Size of each chunk in bytes (default: 1MB)
        """
        self.chunk_size = chunk_size

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def shard(self, data: bytes) -> list[tuple[int, bytes]]:
        """
        Split data into shards.

        Args:
            data: Raw data to shard.

        Returns:
            List of (index, shard_data) tuples.
        """
        shards = []
        offset = 0
        index = 0

        while offset < len(data):
            shard_data = data[offset:offset + self.chunk_size]
            shards.append((index, shard_data))
            offset += self.chunk_size
            index += 1

        return shards

    def reassemble(self, shards: list[tuple[int, bytes]]) -> bytes:
        """
        Reassemble data from shards.

        Args:
            shards: List of (index, shard_data) tuples.

        Returns:
            Reassembled data.
        """
        # Sort by index
        sorted_shards = sorted(shards, key=lambda x: x[0])

        # Concatenate
        return b"".join(shard_data for _, shard_data in sorted_shards)

    def create_manifest(
        self,
        original_data: bytes,
        shard_cids: list[str],
        shard_sizes: list[int],
        shard_checksums: list[str],
    ) -> dict[str, Any]:
        """
        Create a manifest for sharded data.

        Args:
            original_data: Original data before sharding.
            shard_cids: CIDs of uploaded shards.
            shard_sizes: Sizes of each shard.
            shard_checksums: Checksums of each shard.

        Returns:
            Manifest dictionary.
        """
        shards = [
            ShardInfo(
                index=i,
                cid=cid,
                size=size,
                checksum=checksum,
            )
            for i, (cid, size, checksum) in enumerate(zip(shard_cids, shard_sizes, shard_checksums, strict=False))
        ]

        return ShardedDataInfo(
            original_cid="",  # Will be set when manifest is uploaded
            total_shards=len(shards),
            total_size=len(original_data),
            original_checksum=self._calculate_checksum(original_data),
            shards=shards,
        ).to_dict()


class IPFSStorage(StorageInterface[Union[dict, list, str, bytes]]):
    """
    IPFS-based storage implementation.

    Features:
    - Upload data to IPFS network
    - Download data by CID
    - Data sharding for large files
    - Pin management
    """

    def __init__(
        self,
        config: IPFSConnectionConfig | None = None,
        shard_threshold: int = 10 * 1024 * 1024,  # 10MB
    ):
        """
        Initialize IPFS storage.

        Args:
            config: IPFS connection configuration.
            shard_threshold: Size threshold for sharding (bytes).
        """
        self.config = config or IPFSConnectionConfig.default()
        self.shard_threshold = shard_threshold
        self.sharding_manager = DataShardingManager(self.config.chunk_size)
        self._client = None
        self._connected = False
        self._cid_cache: dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the storage backend."""
        try:
            if self.config.use_client:
                await self._init_client()

            self._connected = True
            logger.info(f"IPFSStorage initialized (gateway: {self.config.gateway_url})")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize IPFS client: {e}")

            if self.config.fallback_to_gateway:
                self._connected = True
                logger.info("Falling back to gateway-only mode")
                return True

            return False

    async def _init_client(self) -> None:
        """Initialize IPFS client."""
        try:
            import ipfshttpclient
            self._client = ipfshttpclient.connect(self.config.api_url)
            logger.info("Connected to local IPFS node")
        except ImportError:
            logger.warning("ipfshttpclient not installed, falling back to gateway")
            self._client = None
        except Exception as e:
            logger.warning(f"Failed to connect to IPFS node: {e}")
            self._client = None

    async def close(self) -> None:
        """Close the storage backend."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._connected = False
        logger.info("IPFSStorage closed")

    @property
    def storage_type(self) -> StorageType:
        return StorageType.IPFS

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def _upload_via_client(self, data: bytes) -> str:
        """Upload data using ipfshttpclient."""
        if not self._client:
            raise StorageError("IPFS client not available")

        loop = asyncio.get_event_loop()

        def _upload():
            result = self._client.add_bytes(data)
            if self.config.pin_content:
                self._client.pin.add(result)
            return result

        return await loop.run_in_executor(None, _upload)

    async def _upload_via_api(self, data: bytes) -> str:
        """Upload data using IPFS HTTP API."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            url = f"{self.config.api_url.replace('/ip4', 'http://').replace('/tcp', ':')}/api/v0/add"
            formData = aiohttp.FormData()
            formData.add_field('file', data, filename='data')

            async with session.post(url, data=formData, timeout=self.config.timeout) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['Hash']
                raise StorageError(f"Upload failed: {resp.status}")

    async def _download_via_client(self, cid: str) -> bytes:
        """Download data using ipfshttpclient."""
        if not self._client:
            raise StorageError("IPFS client not available")

        loop = asyncio.get_event_loop()

        def _download():
            return self._client.cat(cid)

        return await loop.run_in_executor(None, _download)

    async def _download_via_gateway(self, cid: str) -> bytes:
        """Download data using public gateway."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            url = f"{self.config.gateway_url}{cid}"

            async with session.get(url, timeout=self.config.timeout) as resp:
                if resp.status == 200:
                    return await resp.read()
                raise StorageError(f"Download failed: {resp.status}")

    async def _download_via_api(self, cid: str) -> bytes:
        """Download data using IPFS HTTP API."""
        import aiohttp

        async with aiohttp.ClientSession() as session:
            url = f"{self.config.api_url.replace('/ip4', 'http://').replace('/tcp', ':')}/api/v0/cat?arg={cid}"

            async with session.post(url, timeout=self.config.timeout) as resp:
                if resp.status == 200:
                    return await resp.read()
                raise StorageError(f"Download failed: {resp.status}")

    async def upload(self, data: bytes) -> str:
        """
        Upload data to IPFS.

        Args:
            data: Raw data to upload.

        Returns:
            CID of uploaded data.
        """
        # Try client first
        if self._client:
            try:
                return await self._upload_via_client(data)
            except Exception as e:
                logger.warning(f"Client upload failed: {e}")

        # Fallback to API
        try:
            return await self._upload_via_api(data)
        except Exception as e:
            logger.warning(f"API upload failed: {e}")

        raise StorageError("Failed to upload data to IPFS")

    async def download(self, cid: str) -> bytes:
        """
        Download data from IPFS.

        Args:
            cid: Content ID to download.

        Returns:
            Downloaded data.
        """
        # Try client first
        if self._client:
            try:
                return await self._download_via_client(cid)
            except Exception as e:
                logger.warning(f"Client download failed: {e}")

        # Fallback to gateway
        if self.config.fallback_to_gateway:
            try:
                return await self._download_via_gateway(cid)
            except Exception as e:
                logger.warning(f"Gateway download failed: {e}")

        raise StorageError(f"Failed to download data from IPFS: {cid}")

    async def _upload_sharded(self, data: bytes) -> tuple[str, dict[str, Any]]:
        """
        Upload large data as shards.

        Args:
            data: Raw data to upload.

        Returns:
            Tuple of (manifest_cid, manifest_data).
        """
        shards = self.sharding_manager.shard(data)
        shard_cids = []
        shard_sizes = []
        shard_checksums = []

        # Upload each shard
        for index, shard_data in shards:
            cid = await self.upload(shard_data)
            shard_cids.append(cid)
            shard_sizes.append(len(shard_data))
            shard_checksums.append(
                self.sharding_manager._calculate_checksum(shard_data)
            )
            logger.debug(f"Uploaded shard {index}: {cid}")

        # Create and upload manifest
        manifest = self.sharding_manager.create_manifest(
            data, shard_cids, shard_sizes, shard_checksums
        )

        manifest_bytes = json.dumps(manifest, indent=2).encode('utf-8')
        manifest_cid = await self.upload(manifest_bytes)
        manifest["original_cid"] = manifest_cid

        return manifest_cid, manifest

    async def _download_sharded(self, manifest: dict[str, Any]) -> bytes:
        """
        Download and reassemble sharded data.

        Args:
            manifest: Sharding manifest.

        Returns:
            Reassembled data.
        """
        shards = []

        for shard_info in manifest["shards"]:
            shard_data = await self.download(shard_info["cid"])
            shards.append((shard_info["index"], shard_data))

        return self.sharding_manager.reassemble(shards)

    def _serialize(self, data: dict | list | str | bytes) -> bytes:
        """Serialize data to bytes."""
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode('utf-8')
        return json.dumps(data, ensure_ascii=False, default=str).encode('utf-8')

    def _deserialize(self, data: bytes) -> dict | list | str:
        """Deserialize bytes to data."""
        try:
            text = data.decode('utf-8')
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        except UnicodeDecodeError:
            return data

    async def store(
        self,
        key: str,
        data: dict | list | str | bytes,
        metadata: dict[str, Any] | None = None,
        overwrite: bool = False,
    ) -> StorageResult:
        """Store data to IPFS."""
        try:
            serialized = self._serialize(data)

            # Check if sharding is needed
            if len(serialized) > self.shard_threshold:
                cid, manifest = await self._upload_sharded(serialized)
                is_sharded = True
            else:
                cid = await self.upload(serialized)
                manifest = None
                is_sharded = False

            # Create location
            location = DataLocation(
                storage_type=StorageType.IPFS,
                key=key,
                cid=cid,
                metadata={
                    "size": len(serialized),
                    "is_sharded": is_sharded,
                    "uploaded_at": datetime.utcnow().isoformat(),
                    **(metadata or {}),
                },
            )

            # Cache CID
            self._cid_cache[key] = {
                "cid": cid,
                "manifest": manifest,
                "location": location,
            }

            return StorageResult(
                success=True,
                location=location,
                metadata={
                    "cid": cid,
                    "is_sharded": is_sharded,
                    **(metadata or {}),
                },
            )

        except Exception as e:
            logger.error(f"Error storing data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def retrieve(self, key: str) -> StorageResult:
        """Retrieve data from IPFS."""
        try:
            # Check cache first
            if key in self._cid_cache:
                cached = self._cid_cache[key]
                cid = cached["cid"]
                manifest = cached.get("manifest")
                location = cached.get("location")
            else:
                # Try to interpret key as CID
                cid = key
                manifest = None
                location = None

            # Download data
            if manifest:
                # Download manifest first
                manifest_data = await self.download(cid)
                manifest = json.loads(manifest_data.decode('utf-8'))

                # Check if sharded
                if manifest.get("is_sharded") or "shards" in manifest:
                    data_bytes = await self._download_sharded(manifest)
                else:
                    data_bytes = await self.download(cid)
            else:
                data_bytes = await self.download(cid)

            # Deserialize
            data = self._deserialize(data_bytes)

            if not location:
                location = DataLocation(
                    storage_type=StorageType.IPFS,
                    key=key,
                    cid=cid,
                )

            return StorageResult(
                success=True,
                data=data,
                location=location,
                metadata={"cid": cid},
            )

        except Exception as e:
            logger.error(f"Error retrieving data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def retrieve_by_cid(self, cid: str) -> StorageResult:
        """
        Retrieve data by CID directly.

        Args:
            cid: Content ID to retrieve.

        Returns:
            StorageResult with the data.
        """
        return await self.retrieve(cid)

    async def delete(self, key: str) -> StorageResult:
        """
        Delete data (unpin from IPFS).

        Note: This only unpins the data; it may still exist on the network.
        """
        try:
            if key not in self._cid_cache:
                return StorageResult(
                    success=False,
                    error=f"Key not found in cache: {key}",
                )

            cached = self._cid_cache[key]
            cid = cached["cid"]

            # Unpin if using client
            if self._client:
                loop = asyncio.get_event_loop()

                def _unpin():
                    try:
                        self._client.pin.rm(cid)
                    except Exception:
                        pass

                await loop.run_in_executor(None, _unpin)

            # Remove from cache
            del self._cid_cache[key]

            return StorageResult(
                success=True,
                metadata={"unpinned_cid": cid},
            )

        except Exception as e:
            logger.error(f"Error deleting data for key {key}: {e}")
            return StorageResult(success=False, error=str(e))

    async def exists(self, key: str) -> bool:
        """Check if data exists."""
        if key in self._cid_cache:
            return True

        # Try to fetch from gateway
        try:
            cid = key
            await self.download(cid)
            return True
        except Exception:
            return False

    async def list_keys(
        self,
        prefix: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[str]:
        """List cached keys."""
        keys = list(self._cid_cache.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]
        return keys[offset:offset + limit]

    async def get_metadata(self, key: str) -> dict[str, Any] | None:
        """Get metadata for a key."""
        if key in self._cid_cache:
            return self._cid_cache[key].get("location", {}).metadata
        return None

    async def update_metadata(
        self,
        key: str,
        metadata: dict[str, Any],
        merge: bool = True,
    ) -> StorageResult:
        """Update metadata for a key."""
        if key not in self._cid_cache:
            return StorageResult(
                success=False,
                error=f"Key not found: {key}",
            )

        cached = self._cid_cache[key]
        if merge and cached.get("location"):
            cached["location"].metadata.update(metadata)
        elif cached.get("location"):
            cached["location"].metadata = metadata

        return StorageResult(
            success=True,
            metadata=cached.get("location", {}).metadata,
        )

    async def pin(self, cid: str) -> bool:
        """
        Pin a CID to local node.

        Args:
            cid: Content ID to pin.

        Returns:
            True if pinned successfully.
        """
        if not self._client:
            logger.warning("Cannot pin without IPFS client")
            return False

        try:
            loop = asyncio.get_event_loop()

            def _pin():
                self._client.pin.add(cid)
                return True

            return await loop.run_in_executor(None, _pin)
        except Exception as e:
            logger.error(f"Failed to pin {cid}: {e}")
            return False

    async def unpin(self, cid: str) -> bool:
        """
        Unpin a CID from local node.

        Args:
            cid: Content ID to unpin.

        Returns:
            True if unpinned successfully.
        """
        if not self._client:
            return False

        try:
            loop = asyncio.get_event_loop()

            def _unpin():
                self._client.pin.rm(cid)
                return True

            return await loop.run_in_executor(None, _unpin)
        except Exception as e:
            logger.error(f"Failed to unpin {cid}: {e}")
            return False

    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        stats = {
            "storage_type": self.storage_type.value,
            "connected": self.is_connected,
            "gateway_url": self.config.gateway_url,
            "has_client": self._client is not None,
            "cached_items": len(self._cid_cache),
            "shard_threshold": self.shard_threshold,
        }

        if self._client:
            try:
                loop = asyncio.get_event_loop()

                def _get_id():
                    return self._client.id()

                node_id = await loop.run_in_executor(None, _get_id)
                stats["node_id"] = node_id.get("ID", "unknown")
            except Exception:
                pass

        return stats

    async def resolve_cid(self, key: str) -> str | None:
        """
        Resolve a key to its CID.

        Args:
            key: Key to resolve.

        Returns:
            CID or None if not found.
        """
        if key in self._cid_cache:
            return self._cid_cache[key]["cid"]
        return None
