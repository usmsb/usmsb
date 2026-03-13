"""
Dataset Catalog

Catalog for managing datasets including metadata, quality metrics,
access control, and lineage tracking.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DatasetStatus(str, Enum):
    """Status of a dataset."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    VALIDATING = "validating"
    ERROR = "error"
    ARCHIVED = "archived"


class DatasetType(str, Enum):
    """Types of datasets."""
    TABULAR = "tabular"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    TIME_SERIES = "time_series"
    GRAPH = "graph"
    MULTIMODAL = "multimodal"


class AccessLevel(str, Enum):
    """Access levels for datasets."""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    PRIVATE = "private"


@dataclass
class QualityMetrics:
    """Quality metrics for a dataset."""
    completeness: float = 1.0  # Percentage of non-null values
    accuracy: float = 1.0  # Percentage of accurate values
    consistency: float = 1.0  # Percentage of consistent values
    timeliness: float = 1.0  # Recency score
    validity: float = 1.0  # Percentage of valid values
    uniqueness: float = 1.0  # Percentage of unique records

    @property
    def overall_score(self) -> float:
        """Calculate overall quality score."""
        return (
            self.completeness +
            self.accuracy +
            self.consistency +
            self.timeliness +
            self.validity +
            self.uniqueness
        ) / 6


@dataclass
class DatasetVersion:
    """A specific version of a dataset."""
    version: str
    dataset_id: str
    checksum: str
    size_bytes: int
    record_count: int
    path: str
    quality_metrics: Optional[QualityMetrics] = None
    schema: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: time.time())
    created_by: Optional[str] = None
    description: str = ""
    status: DatasetStatus = DatasetStatus.READY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dataset:
    """A registered dataset."""
    id: str
    name: str
    type: DatasetType
    description: str = ""
    versions: List[DatasetVersion] = field(default_factory=list)
    latest_version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    owner_id: Optional[str] = None
    access_level: AccessLevel = AccessLevel.INTERNAL
    license: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_version(self, version: str) -> Optional[DatasetVersion]:
        """Get a specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version(self) -> Optional[DatasetVersion]:
        """Get the latest version."""
        if not self.versions:
            return None
        return self.versions[-1]


@dataclass
class AccessGrant:
    """Access grant for a dataset."""
    id: str
    dataset_id: str
    user_id: str
    access_level: AccessLevel
    granted_at: float = field(default_factory=lambda: time.time())
    granted_by: Optional[str] = None
    expires_at: Optional[float] = None


@dataclass
class LineageRecord:
    """Data lineage record."""
    id: str
    dataset_id: str
    version: str
    source_datasets: List[str]  # List of dataset_id:version
    transformation: str
    created_at: float = field(default_factory=lambda: time.time())
    created_by: Optional[str] = None


class DatasetCatalog:
    """
    Dataset Catalog.

    Provides dataset lifecycle management:
    - Registration and versioning
    - Quality metrics tracking
    - Access control
    - Lineage tracking
    - Search and discovery
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the Dataset Catalog.

        Args:
            storage_path: Path for dataset storage
        """
        self.storage_path = storage_path or "./datasets"
        self._datasets: Dict[str, Dataset] = {}
        self._access_grants: Dict[str, List[AccessGrant]] = {}
        self._lineage: Dict[str, List[LineageRecord]] = {}
        self._version_counter: Dict[str, int] = {}

    def register_dataset(
        self,
        name: str,
        dataset_type: DatasetType,
        description: str = "",
        owner_id: Optional[str] = None,
        access_level: AccessLevel = AccessLevel.INTERNAL,
        license: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dataset:
        """
        Register a new dataset.

        Args:
            name: Dataset name
            dataset_type: Type of dataset
            description: Dataset description
            owner_id: Owner ID
            access_level: Access level
            license: Dataset license
            tags: List of tags
            metadata: Additional metadata

        Returns:
            Registered dataset
        """
        import uuid

        dataset_id = str(uuid.uuid4())[:8]

        dataset = Dataset(
            id=dataset_id,
            name=name,
            type=dataset_type,
            description=description,
            owner_id=owner_id,
            access_level=access_level,
            license=license,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._datasets[dataset_id] = dataset
        self._version_counter[dataset_id] = 0
        self._access_grants[dataset_id] = []

        logger.info(f"Dataset registered: {name} (ID: {dataset_id})")
        return dataset

    def add_version(
        self,
        dataset_id: str,
        path: str,
        size_bytes: int,
        record_count: int,
        checksum: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        quality_metrics: Optional[QualityMetrics] = None,
        description: str = "",
        created_by: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DatasetVersion:
        """
        Add a new version to a dataset.

        Args:
            dataset_id: Dataset ID
            path: Path to dataset files
            size_bytes: Dataset size in bytes
            record_count: Number of records
            checksum: Dataset checksum
            schema: Dataset schema
            quality_metrics: Quality metrics
            description: Version description
            created_by: Creator ID
            metadata: Additional metadata

        Returns:
            Created version
        """
        if dataset_id not in self._datasets:
            raise ValueError(f"Dataset {dataset_id} not found")

        dataset = self._datasets[dataset_id]

        # Generate version number
        version_num = self._version_counter.get(dataset_id, 0) + 1
        self._version_counter[dataset_id] = version_num
        version_str = f"v{version_num}.0"

        # Generate checksum if not provided
        if checksum is None:
            checksum = hashlib.sha256(f"{dataset_id}:{version_str}:{time.time()}".encode()).hexdigest()

        version = DatasetVersion(
            version=version_str,
            dataset_id=dataset_id,
            checksum=checksum,
            size_bytes=size_bytes,
            record_count=record_count,
            path=path,
            schema=schema or {},
            quality_metrics=quality_metrics,
            description=description,
            created_by=created_by,
            metadata=metadata or {},
        )

        dataset.versions.append(version)
        dataset.latest_version = version_str
        dataset.updated_at = time.time()

        logger.info(f"Version {version_str} added to dataset {dataset_id}")
        return version

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID."""
        return self._datasets.get(dataset_id)

    def get_dataset_by_name(self, name: str) -> Optional[Dataset]:
        """Get dataset by name."""
        for dataset in self._datasets.values():
            if dataset.name == name:
                return dataset
        return None

    def list_datasets(
        self,
        dataset_type: Optional[DatasetType] = None,
        tags: Optional[List[str]] = None,
        owner_id: Optional[str] = None,
        access_level: Optional[AccessLevel] = None,
        status: Optional[DatasetStatus] = None,
    ) -> List[Dataset]:
        """
        List datasets with optional filters.

        Args:
            dataset_type: Filter by type
            tags: Filter by tags
            owner_id: Filter by owner
            access_level: Filter by access level
            status: Filter by status

        Returns:
            List of matching datasets
        """
        datasets = list(self._datasets.values())

        if dataset_type:
            datasets = [d for d in datasets if d.type == dataset_type]

        if tags:
            datasets = [d for d in datasets if all(t in d.tags for t in tags)]

        if owner_id:
            datasets = [d for d in datasets if d.owner_id == owner_id]

        if access_level:
            datasets = [d for d in datasets if d.access_level == access_level]

        if status:
            datasets = [
                d for d in datasets
                if d.get_latest_version()?.status == status
            ]

        return datasets

    def grant_access(
        self,
        dataset_id: str,
        user_id: str,
        access_level: AccessLevel,
        granted_by: Optional[str] = None,
        expires_at: Optional[float] = None,
    ) -> AccessGrant:
        """
        Grant access to a dataset.

        Args:
            dataset_id: Dataset ID
            user_id: User ID
            access_level: Access level to grant
            granted_by: Grantor ID
            expires_at: Expiration timestamp

        Returns:
            Access grant
        """
        import uuid

        if dataset_id not in self._datasets:
            raise ValueError(f"Dataset {dataset_id} not found")

        grant = AccessGrant(
            id=str(uuid.uuid4())[:8],
            dataset_id=dataset_id,
            user_id=user_id,
            access_level=access_level,
            granted_by=granted_by,
            expires_at=expires_at,
        )

        self._access_grants[dataset_id].append(grant)

        logger.info(f"Access granted: {access_level.value} to {user_id} for dataset {dataset_id}")
        return grant

    def check_access(
        self,
        dataset_id: str,
        user_id: str,
        required_level: AccessLevel,
    ) -> bool:
        """
        Check if user has access to dataset.

        Args:
            dataset_id: Dataset ID
            user_id: User ID
            required_level: Required access level

        Returns:
            True if access granted
        """
        dataset = self._datasets.get(dataset_id)
        if not dataset:
            return False

        # Check if public
        if dataset.access_level == AccessLevel.PUBLIC:
            return True

        # Check if owner
        if dataset.owner_id == user_id:
            return True

        # Check explicit grants
        grants = self._access_grants.get(dataset_id, [])
        for grant in grants:
            if grant.user_id == user_id:
                # Check expiration
                if grant.expires_at and grant.expires_at < time.time():
                    continue

                # Check access level hierarchy
                levels = [AccessLevel.PUBLIC, AccessLevel.INTERNAL, AccessLevel.RESTRICTED, AccessLevel.PRIVATE]
                if levels.index(grant.access_level) >= levels.index(required_level):
                    return True

        return False

    def record_lineage(
        self,
        dataset_id: str,
        version: str,
        source_datasets: List[str],
        transformation: str,
        created_by: Optional[str] = None,
    ) -> LineageRecord:
        """
        Record dataset lineage.

        Args:
            dataset_id: Dataset ID
            version: Version
            source_datasets: Source dataset IDs
            transformation: Transformation description
            created_by: Creator ID

        Returns:
            Lineage record
        """
        import uuid

        record = LineageRecord(
            id=str(uuid.uuid4())[:8],
            dataset_id=dataset_id,
            version=version,
            source_datasets=source_datasets,
            transformation=transformation,
            created_by=created_by,
        )

        if dataset_id not in self._lineage:
            self._lineage[dataset_id] = []
        self._lineage[dataset_id].append(record)

        return record

    def get_lineage(self, dataset_id: str) -> List[LineageRecord]:
        """Get lineage for a dataset."""
        return self._lineage.get(dataset_id, [])

    def get_upstream_datasets(self, dataset_id: str, version: Optional[str] = None) -> List[str]:
        """Get all upstream datasets."""
        upstream = []
        visited = set()

        def collect_upstream(did: str, ver: Optional[str]):
            if did in visited:
                return
            visited.add(did)

            records = self._lineage.get(did, [])
            for record in records:
                if version and record.version != version:
                    continue
                for source in record.source_datasets:
                    source_id = source.split(":")[0]
                    upstream.append(source)
                    collect_upstream(source_id, None)

        collect_upstream(dataset_id, version)
        return upstream

    def search_datasets(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dataset]:
        """
        Search datasets by query.

        Args:
            query: Search query
            filters: Additional filters

        Returns:
            Matching datasets
        """
        query = query.lower()
        results = []

        for dataset in self._datasets.values():
            # Search in name, description, tags
            if (
                query in dataset.name.lower()
                or query in dataset.description.lower()
                or any(query in tag.lower() for tag in dataset.tags)
            ):
                results.append(dataset)

        # Apply additional filters
        if filters:
            if "type" in filters:
                results = [d for d in results if d.type == filters["type"]]
            if "owner_id" in filters:
                results = [d for d in results if d.owner_id == filters["owner_id"]]

        return results

    def get_catalog_stats(self) -> Dict[str, Any]:
        """Get catalog statistics."""
        total_datasets = len(self._datasets)
        total_versions = sum(len(d.versions) for d in self._datasets.values())
        total_records = sum(
            v.record_count for d in self._datasets.values()
            for v in d.versions
        )
        total_size = sum(
            v.size_bytes for d in self._datasets.values()
            for v in d.versions
        )

        return {
            "total_datasets": total_datasets,
            "total_versions": total_versions,
            "total_records": total_records,
            "total_size_bytes": total_size,
            "total_size_gb": total_size / (1024 ** 3),
            "by_type": {
                t.value: sum(1 for d in self._datasets.values() if d.type == t)
                for t in DatasetType
            },
        }
