"""
Model Registry

Registry for AI models including versioning, metadata management,
and deployment tracking.
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ModelStatus(StrEnum):
    """Status of a registered model."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelType(StrEnum):
    """Types of AI models."""
    LLM = "llm"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"
    GENERATIVE = "generative"
    MULTIMODAL = "multimodal"
    CUSTOM = "custom"


@dataclass
class ModelVersion:
    """A specific version of a model."""
    version: str
    model_id: str
    checksum: str
    size_bytes: int
    path: str
    metrics: dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: time.time())
    created_by: str | None = None
    description: str = ""
    status: ModelStatus = ModelStatus.DEVELOPMENT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Model:
    """A registered AI model."""
    id: str
    name: str
    type: ModelType
    description: str = ""
    versions: list[ModelVersion] = field(default_factory=list)
    latest_version: str | None = None
    tags: list[str] = field(default_factory=list)
    owner_id: str | None = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_version(self, version: str) -> ModelVersion | None:
        """Get a specific version."""
        for v in self.versions:
            if v.version == version:
                return v
        return None

    def get_latest_version(self) -> ModelVersion | None:
        """Get the latest version."""
        if not self.versions:
            return None
        return self.versions[-1]

    def get_production_version(self) -> ModelVersion | None:
        """Get the current production version."""
        for v in reversed(self.versions):
            if v.status == ModelStatus.PRODUCTION:
                return v
        return None


@dataclass
class DeploymentRecord:
    """Record of a model deployment."""
    id: str
    model_id: str
    version: str
    endpoint: str
    status: str = "active"
    deployed_at: float = field(default_factory=lambda: time.time())
    deployed_by: str | None = None
    resource_allocation: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


class ModelRegistry:
    """
    Model Registry.

    Provides model lifecycle management:
    - Registration and versioning
    - Metadata management
    - Deployment tracking
    - Access control
    """

    def __init__(self, storage_path: str | None = None):
        """
        Initialize the Model Registry.

        Args:
            storage_path: Path for model storage
        """
        self.storage_path = storage_path or "./models"
        self._models: dict[str, Model] = {}
        self._deployments: dict[str, DeploymentRecord] = {}
        self._version_counter: dict[str, int] = {}

    def register_model(
        self,
        name: str,
        model_type: ModelType,
        description: str = "",
        owner_id: str | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Model:
        """
        Register a new model.

        Args:
            name: Model name
            model_type: Type of model
            description: Model description
            owner_id: Owner ID
            tags: List of tags
            metadata: Additional metadata

        Returns:
            Registered model
        """
        import uuid

        model_id = str(uuid.uuid4())[:8]

        model = Model(
            id=model_id,
            name=name,
            type=model_type,
            description=description,
            owner_id=owner_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._models[model_id] = model
        self._version_counter[model_id] = 0

        logger.info(f"Model registered: {name} (ID: {model_id})")
        return model

    def add_version(
        self,
        model_id: str,
        path: str,
        size_bytes: int,
        checksum: str | None = None,
        metrics: dict[str, float] | None = None,
        description: str = "",
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ModelVersion:
        """
        Add a new version to a model.

        Args:
            model_id: Model ID
            path: Path to model files
            size_bytes: Model size in bytes
            checksum: Model checksum (auto-generated if None)
            metrics: Performance metrics
            description: Version description
            created_by: Creator ID
            metadata: Additional metadata

        Returns:
            Created version
        """
        if model_id not in self._models:
            raise ValueError(f"Model {model_id} not found")

        model = self._models[model_id]

        # Generate version number
        version_num = self._version_counter.get(model_id, 0) + 1
        self._version_counter[model_id] = version_num
        version_str = f"v{version_num}.0.0"

        # Generate checksum if not provided
        if checksum is None:
            checksum = hashlib.sha256(f"{model_id}:{version_str}:{time.time()}".encode()).hexdigest()

        version = ModelVersion(
            version=version_str,
            model_id=model_id,
            checksum=checksum,
            size_bytes=size_bytes,
            path=path,
            metrics=metrics or {},
            description=description,
            created_by=created_by,
            metadata=metadata or {},
        )

        model.versions.append(version)
        model.latest_version = version_str
        model.updated_at = time.time()

        logger.info(f"Version {version_str} added to model {model_id}")
        return version

    def get_model(self, model_id: str) -> Model | None:
        """Get model by ID."""
        return self._models.get(model_id)

    def get_model_by_name(self, name: str) -> Model | None:
        """Get model by name."""
        for model in self._models.values():
            if model.name == name:
                return model
        return None

    def list_models(
        self,
        model_type: ModelType | None = None,
        tags: list[str] | None = None,
        owner_id: str | None = None,
        status: ModelStatus | None = None,
    ) -> list[Model]:
        """
        List models with optional filters.

        Args:
            model_type: Filter by type
            tags: Filter by tags (must have all)
            owner_id: Filter by owner
            status: Filter by status

        Returns:
            List of matching models
        """
        models = list(self._models.values())

        if model_type:
            models = [m for m in models if m.type == model_type]

        if tags:
            models = [m for m in models if all(t in m.tags for t in tags)]

        if owner_id:
            models = [m for m in models if m.owner_id == owner_id]

        if status:
            models = [m for m in models if m.get_production_version() and m.get_production_version().status == status]

        return models

    def update_version_status(
        self,
        model_id: str,
        version: str,
        status: ModelStatus,
    ) -> bool:
        """
        Update a version's status.

        Args:
            model_id: Model ID
            version: Version string
            status: New status

        Returns:
            True if successful
        """
        model = self._models.get(model_id)
        if not model:
            return False

        version_obj = model.get_version(version)
        if not version_obj:
            return False

        version_obj.status = status
        model.updated_at = time.time()

        logger.info(f"Model {model_id} version {version} status updated to {status.value}")
        return True

    def promote_to_production(
        self,
        model_id: str,
        version: str,
    ) -> bool:
        """
        Promote a version to production.

        Demotes any current production version.

        Args:
            model_id: Model ID
            version: Version to promote

        Returns:
            True if successful
        """
        model = self._models.get(model_id)
        if not model:
            return False

        # Demote current production version
        for v in model.versions:
            if v.status == ModelStatus.PRODUCTION:
                v.status = ModelStatus.STAGING

        # Promote new version
        version_obj = model.get_version(version)
        if not version_obj:
            return False

        version_obj.status = ModelStatus.PRODUCTION
        model.updated_at = time.time()

        logger.info(f"Model {model_id} version {version} promoted to production")
        return True

    def record_deployment(
        self,
        model_id: str,
        version: str,
        endpoint: str,
        deployed_by: str | None = None,
        resource_allocation: dict[str, Any] | None = None,
    ) -> DeploymentRecord:
        """
        Record a model deployment.

        Args:
            model_id: Model ID
            version: Version deployed
            endpoint: Deployment endpoint
            deployed_by: Deployer ID
            resource_allocation: Resource allocation info

        Returns:
            Deployment record
        """
        import uuid

        record = DeploymentRecord(
            id=str(uuid.uuid4())[:8],
            model_id=model_id,
            version=version,
            endpoint=endpoint,
            deployed_by=deployed_by,
            resource_allocation=resource_allocation or {},
        )

        self._deployments[record.id] = record

        logger.info(f"Deployment recorded: {model_id}:{version} at {endpoint}")
        return record

    def get_deployments(
        self,
        model_id: str | None = None,
        status: str | None = None,
    ) -> list[DeploymentRecord]:
        """Get deployment records."""
        deployments = list(self._deployments.values())

        if model_id:
            deployments = [d for d in deployments if d.model_id == model_id]

        if status:
            deployments = [d for d in deployments if d.status == status]

        return deployments

    def get_deployment(self, deployment_id: str) -> DeploymentRecord | None:
        """Get deployment by ID."""
        return self._deployments.get(deployment_id)

    def update_deployment_status(
        self,
        deployment_id: str,
        status: str,
        metrics: dict[str, Any] | None = None,
    ) -> bool:
        """Update deployment status."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            return False

        deployment.status = status
        if metrics:
            deployment.metrics.update(metrics)

        return True

    def compare_versions(
        self,
        model_id: str,
        version1: str,
        version2: str,
    ) -> dict[str, Any]:
        """
        Compare two model versions.

        Args:
            model_id: Model ID
            version1: First version
            version2: Second version

        Returns:
            Comparison result
        """
        model = self._models.get(model_id)
        if not model:
            return {"error": "Model not found"}

        v1 = model.get_version(version1)
        v2 = model.get_version(version2)

        if not v1 or not v2:
            return {"error": "Version not found"}

        return {
            "model_id": model_id,
            "version1": {
                "version": v1.version,
                "size_bytes": v1.size_bytes,
                "metrics": v1.metrics,
                "created_at": v1.created_at,
            },
            "version2": {
                "version": v2.version,
                "size_bytes": v2.size_bytes,
                "metrics": v2.metrics,
                "created_at": v2.created_at,
            },
            "metrics_diff": {
                k: v2.metrics.get(k, 0) - v1.metrics.get(k, 0)
                for k in set(v1.metrics.keys()) | set(v2.metrics.keys())
            },
            "size_diff": v2.size_bytes - v1.size_bytes,
        }

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        total_models = len(self._models)
        total_versions = sum(len(m.versions) for m in self._models.values())
        production_models = sum(
            1 for m in self._models.values()
            if m.get_production_version()
        )
        total_deployments = len(self._deployments)
        active_deployments = sum(
            1 for d in self._deployments.values()
            if d.status == "active"
        )

        return {
            "total_models": total_models,
            "total_versions": total_versions,
            "production_models": production_models,
            "total_deployments": total_deployments,
            "active_deployments": active_deployments,
        }
