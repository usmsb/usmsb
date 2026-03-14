"""
Compute Resource Adapter

Abstract interface and implementations for compute resource management.
Supports GPU, CPU, and distributed compute resources.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class ComputeType(StrEnum):
    """Types of compute resources."""
    CPU = "cpu"
    GPU = "gpu"
    TPU = "tpu"
    DISTRIBUTED = "distributed"


class ResourceStatus(StrEnum):
    """Status of a compute resource."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class JobStatus(StrEnum):
    """Status of a compute job."""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ComputeSpec:
    """Compute resource specifications."""
    cpu_cores: int = 1
    cpu_memory_gb: float = 4.0
    gpu_count: int = 0
    gpu_type: str | None = None
    gpu_memory_gb: float = 0.0
    storage_gb: float = 100.0
    network_bandwidth_mbps: float = 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "cpu_cores": self.cpu_cores,
            "cpu_memory_gb": self.cpu_memory_gb,
            "gpu_count": self.gpu_count,
            "gpu_type": self.gpu_type,
            "gpu_memory_gb": self.gpu_memory_gb,
            "storage_gb": self.storage_gb,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
        }


@dataclass
class ComputeResource:
    """A compute resource node."""
    id: str
    name: str
    type: ComputeType
    spec: ComputeSpec
    status: ResourceStatus = ResourceStatus.AVAILABLE
    endpoint: str | None = None
    owner_id: str | None = None
    price_per_hour: float = 0.0
    utilized: float = 0.0  # 0.0 to 1.0
    created_at: float = field(default_factory=lambda: time.time())
    metadata: dict[str, Any] = field(default_factory=dict)

    def available_spec(self) -> ComputeSpec:
        """Get available (non-utilized) specs."""
        utilization_factor = 1.0 - self.utilized
        return ComputeSpec(
            cpu_cores=int(self.spec.cpu_cores * utilization_factor),
            cpu_memory_gb=self.spec.cpu_memory_gb * utilization_factor,
            gpu_count=int(self.spec.gpu_count * utilization_factor),
            gpu_type=self.spec.gpu_type,
            gpu_memory_gb=self.spec.gpu_memory_gb * utilization_factor,
            storage_gb=self.spec.storage_gb * utilization_factor,
            network_bandwidth_mbps=self.spec.network_bandwidth_mbps * utilization_factor,
        )

    def can_allocate(self, required: ComputeSpec) -> bool:
        """Check if resource can allocate required specs."""
        available = self.available_spec()
        return (
            available.cpu_cores >= required.cpu_cores
            and available.cpu_memory_gb >= required.cpu_memory_gb
            and available.gpu_count >= required.gpu_count
            and available.gpu_memory_gb >= required.gpu_memory_gb
        )


@dataclass
class ComputeJob:
    """A compute job."""
    id: str
    name: str
    owner_id: str
    required_spec: ComputeSpec
    command: str | None = None
    docker_image: str | None = None
    environment: dict[str, str] = field(default_factory=dict)
    input_data: str | None = None
    output_path: str | None = None
    status: JobStatus = JobStatus.QUEUED
    resource_id: str | None = None
    priority: int = 0
    created_at: float = field(default_factory=lambda: time.time())
    started_at: float | None = None
    completed_at: float | None = None
    result: Any | None = None
    error: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Allocation:
    """Resource allocation record."""
    id: str
    resource_id: str
    job_id: str
    allocated_spec: ComputeSpec
    started_at: float
    duration_seconds: float | None = None
    cost: float = 0.0
    status: str = "active"


class IComputeResourceAdapter(ABC):
    """
    Abstract interface for compute resource operations.

    Provides resource discovery, allocation, job execution,
    and monitoring capabilities.
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize compute resource connection."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown compute resource connection."""
        pass

    @abstractmethod
    async def discover_resources(self) -> list[ComputeResource]:
        """Discover available compute resources."""
        pass

    @abstractmethod
    async def register_resource(
        self,
        name: str,
        spec: ComputeSpec,
        endpoint: str,
        owner_id: str | None = None,
        price_per_hour: float = 0.0,
    ) -> ComputeResource:
        """Register a new compute resource."""
        pass

    @abstractmethod
    async def unregister_resource(self, resource_id: str) -> bool:
        """Unregister a compute resource."""
        pass

    @abstractmethod
    async def get_resource(self, resource_id: str) -> ComputeResource | None:
        """Get resource by ID."""
        pass

    @abstractmethod
    async def allocate(
        self,
        resource_id: str,
        spec: ComputeSpec,
        job_id: str,
    ) -> Allocation:
        """Allocate resources on a node."""
        pass

    @abstractmethod
    async def release(self, allocation_id: str) -> bool:
        """Release an allocation."""
        pass

    @abstractmethod
    async def submit_job(
        self,
        job: ComputeJob,
        resource_id: str | None = None,
    ) -> ComputeJob:
        """Submit a compute job."""
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> ComputeJob | None:
        """Get job by ID."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        pass

    @abstractmethod
    async def get_job_logs(self, job_id: str) -> list[str]:
        """Get job logs."""
        pass

    @abstractmethod
    async def get_job_metrics(self, job_id: str) -> dict[str, Any]:
        """Get job performance metrics."""
        pass

    @abstractmethod
    async def monitor_resource(
        self,
        resource_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """Set up resource monitoring."""
        pass

    @abstractmethod
    async def stop_monitoring(self, monitor_id: str) -> bool:
        """Stop resource monitoring."""
        pass


class LocalComputeAdapter(IComputeResourceAdapter):
    """
    Local compute resource adapter.

    Uses local machine resources for compute jobs.
    Suitable for development and testing.
    """

    def __init__(self):
        """Initialize local compute adapter."""
        self._resources: dict[str, ComputeResource] = {}
        self._jobs: dict[str, ComputeJob] = {}
        self._allocations: dict[str, Allocation] = {}
        self._monitors: dict[str, Any] = {}
        self._local_resource_id: str | None = None

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize local compute adapter."""
        import multiprocessing

        # Detect local resources
        cpu_cores = multiprocessing.cpu_count()
        total_memory = 16.0  # Default, would use psutil in production
        gpu_count = 0
        gpu_type = None

        # Try to detect GPU
        try:
            import subprocess
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                gpu_count = result.stdout.count('GPU')
                gpu_type = "NVIDIA"
        except Exception:
            pass

        # Register local resource
        spec = ComputeSpec(
            cpu_cores=cpu_cores,
            cpu_memory_gb=total_memory,
            gpu_count=gpu_count,
            gpu_type=gpu_type,
            storage_gb=1000.0,
        )

        resource = ComputeResource(
            id="local_0",
            name="Local Machine",
            type=ComputeType.CPU if gpu_count == 0 else ComputeType.GPU,
            spec=spec,
            status=ResourceStatus.AVAILABLE,
            endpoint="localhost",
        )

        self._resources[resource.id] = resource
        self._local_resource_id = resource.id

        logger.info(f"Local compute adapter initialized with {cpu_cores} CPU cores, {gpu_count} GPUs")
        return True

    async def shutdown(self) -> None:
        """Shutdown local compute adapter."""
        # Cancel all running jobs
        for job in self._jobs.values():
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.CANCELLED

        self._resources.clear()
        self._jobs.clear()
        self._allocations.clear()

    async def discover_resources(self) -> list[ComputeResource]:
        """Return local resources."""
        return list(self._resources.values())

    async def register_resource(
        self,
        name: str,
        spec: ComputeSpec,
        endpoint: str,
        owner_id: str | None = None,
        price_per_hour: float = 0.0,
    ) -> ComputeResource:
        """Register a resource (limited support for local)."""
        import uuid
        resource_id = str(uuid.uuid4())[:8]

        resource = ComputeResource(
            id=resource_id,
            name=name,
            type=ComputeType.CPU if spec.gpu_count == 0 else ComputeType.GPU,
            spec=spec,
            endpoint=endpoint,
            owner_id=owner_id,
            price_per_hour=price_per_hour,
        )

        self._resources[resource_id] = resource
        return resource

    async def unregister_resource(self, resource_id: str) -> bool:
        """Unregister a resource."""
        if resource_id == self._local_resource_id:
            return False  # Can't unregister local machine

        if resource_id in self._resources:
            del self._resources[resource_id]
            return True
        return False

    async def get_resource(self, resource_id: str) -> ComputeResource | None:
        """Get resource by ID."""
        return self._resources.get(resource_id)

    async def allocate(
        self,
        resource_id: str,
        spec: ComputeSpec,
        job_id: str,
    ) -> Allocation:
        """Allocate resources."""
        import uuid

        resource = self._resources.get(resource_id)
        if not resource:
            raise ValueError(f"Resource {resource_id} not found")

        if not resource.can_allocate(spec):
            raise ValueError("Insufficient resources")

        # Update utilization
        cpu_util = spec.cpu_cores / resource.spec.cpu_cores
        resource.utilized += cpu_util * 0.5  # Simplified

        allocation = Allocation(
            id=str(uuid.uuid4())[:8],
            resource_id=resource_id,
            job_id=job_id,
            allocated_spec=spec,
            started_at=time.time(),
        )

        self._allocations[allocation.id] = allocation
        return allocation

    async def release(self, allocation_id: str) -> bool:
        """Release an allocation."""
        allocation = self._allocations.get(allocation_id)
        if not allocation:
            return False

        resource = self._resources.get(allocation.resource_id)
        if resource:
            cpu_util = allocation.allocated_spec.cpu_cores / resource.spec.cpu_cores
            resource.utilized = max(0, resource.utilized - cpu_util * 0.5)

        allocation.status = "released"
        allocation.duration_seconds = time.time() - allocation.started_at

        return True

    async def submit_job(
        self,
        job: ComputeJob,
        resource_id: str | None = None,
    ) -> ComputeJob:
        """Submit a compute job."""
        resource_id = resource_id or self._local_resource_id
        resource = self._resources.get(resource_id)

        if not resource:
            job.status = JobStatus.FAILED
            job.error = "No resource available"
            return job

        # Check if resource can handle job
        if not resource.can_allocate(job.required_spec):
            job.status = JobStatus.FAILED
            job.error = "Insufficient resources"
            return job

        # Allocate resources
        allocation = await self.allocate(resource_id, job.required_spec, job.id)
        job.resource_id = resource_id
        job.status = JobStatus.SCHEDULED

        self._jobs[job.id] = job

        # Execute job asynchronously
        asyncio.create_task(self._execute_job(job, allocation))

        return job

    async def _execute_job(self, job: ComputeJob, allocation: Allocation) -> None:
        """Execute a job."""
        try:
            job.status = JobStatus.RUNNING
            job.started_at = time.time()

            # Simulate job execution
            # In production, would use subprocess, Docker, or Kubernetes
            if job.command:
                # Execute command
                await asyncio.sleep(1)  # Placeholder

            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()
            job.result = {"status": "success"}

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = time.time()

        finally:
            await self.release(allocation.id)

    async def get_job(self, job_id: str) -> ComputeJob | None:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        job = self._jobs.get(job_id)
        if not job or job.status not in (JobStatus.QUEUED, JobStatus.SCHEDULED, JobStatus.RUNNING):
            return False

        job.status = JobStatus.CANCELLED
        job.completed_at = time.time()
        return True

    async def get_job_logs(self, job_id: str) -> list[str]:
        """Get job logs."""
        job = self._jobs.get(job_id)
        if not job:
            return []

        # Return mock logs
        return [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Job {job_id} started",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Executing task...",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Job completed",
        ]

    async def get_job_metrics(self, job_id: str) -> dict[str, Any]:
        """Get job metrics."""
        job = self._jobs.get(job_id)
        if not job:
            return {}

        return {
            "job_id": job_id,
            "status": job.status.value,
            "duration_seconds": (job.completed_at or time.time()) - (job.started_at or job.created_at),
            "cpu_cores": job.required_spec.cpu_cores,
            "gpu_count": job.required_spec.gpu_count,
        }

    async def monitor_resource(
        self,
        resource_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """Set up resource monitoring."""
        import uuid
        monitor_id = str(uuid.uuid4())[:8]

        self._monitors[monitor_id] = {
            "resource_id": resource_id,
            "callback": callback,
            "active": True,
        }

        # Start monitoring task
        asyncio.create_task(self._monitor_loop(monitor_id))

        return monitor_id

    async def _monitor_loop(self, monitor_id: str) -> None:
        """Monitoring loop."""
        while monitor_id in self._monitors and self._monitors[monitor_id]["active"]:
            monitor = self._monitors[monitor_id]
            resource = self._resources.get(monitor["resource_id"])

            if resource:
                metrics = {
                    "resource_id": resource.id,
                    "status": resource.status.value,
                    "utilization": resource.utilized,
                    "timestamp": time.time(),
                }
                monitor["callback"](metrics)

            await asyncio.sleep(5)

    async def stop_monitoring(self, monitor_id: str) -> bool:
        """Stop monitoring."""
        if monitor_id in self._monitors:
            self._monitors[monitor_id]["active"] = False
            del self._monitors[monitor_id]
            return True
        return False


class KubernetesComputeAdapter(IComputeResourceAdapter):
    """
    Kubernetes compute resource adapter.

    Interfaces with Kubernetes for container orchestration
    and distributed compute resource management.
    """

    def __init__(self):
        """Initialize Kubernetes adapter."""
        self._resources: dict[str, ComputeResource] = {}
        self._jobs: dict[str, ComputeJob] = {}
        self._allocations: dict[str, Allocation] = {}
        self._namespace = "usmsb"
        self._connected = False

    async def initialize(self, config: dict[str, Any]) -> bool:
        """Initialize Kubernetes connection."""
        try:
            # Try to import kubernetes client
            try:
                from kubernetes import client
                from kubernetes import config as k8s_config
                self._k8s_client = client
                self._k8s_config = k8s_config

                # Load config
                try:
                    k8s_config.load_kube_config()
                except Exception:
                    k8s_config.load_incluster_config()

                self._connected = True
                logger.info("Kubernetes compute adapter initialized")

            except ImportError:
                logger.warning("Kubernetes client not installed, using mock mode")
                self._connected = False

            return True

        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes adapter: {e}")
            return False

    async def shutdown(self) -> None:
        """Shutdown Kubernetes connection."""
        self._resources.clear()
        self._jobs.clear()
        self._connected = False

    async def discover_resources(self) -> list[ComputeResource]:
        """Discover Kubernetes nodes."""
        resources = []

        if self._connected:
            try:
                v1 = self._k8s_client.CoreV1Api()
                nodes = v1.list_node()

                for node in nodes.items:
                    allocatable = node.status.allocatable

                    resource = ComputeResource(
                        id=node.metadata.uid,
                        name=node.metadata.name,
                        type=ComputeType.DISTRIBUTED,
                        spec=ComputeSpec(
                            cpu_cores=int(allocatable.get('cpu', 1)),
                            cpu_memory_gb=self._parse_memory(allocatable.get('memory', '4Gi')),
                            gpu_count=0,  # Would check for GPU resources
                        ),
                        status=ResourceStatus.AVAILABLE,
                    )
                    resources.append(resource)
                    self._resources[resource.id] = resource

            except Exception as e:
                logger.error(f"Failed to discover nodes: {e}")

        return resources

    def _parse_memory(self, memory_str: str) -> float:
        """Parse Kubernetes memory string to GB."""
        memory_str = memory_str.lower()
        if memory_str.endswith('gi'):
            return float(memory_str[:-2])
        elif memory_str.endswith('mi'):
            return float(memory_str[:-2]) / 1024
        elif memory_str.endswith('ki'):
            return float(memory_str[:-2]) / (1024 * 1024)
        return float(memory_str)

    async def register_resource(
        self,
        name: str,
        spec: ComputeSpec,
        endpoint: str,
        owner_id: str | None = None,
        price_per_hour: float = 0.0,
    ) -> ComputeResource:
        """Register resource (not typically used with Kubernetes)."""
        import uuid
        resource_id = str(uuid.uuid4())[:8]

        resource = ComputeResource(
            id=resource_id,
            name=name,
            type=ComputeType.DISTRIBUTED,
            spec=spec,
            endpoint=endpoint,
            owner_id=owner_id,
            price_per_hour=price_per_hour,
        )

        self._resources[resource_id] = resource
        return resource

    async def unregister_resource(self, resource_id: str) -> bool:
        """Unregister resource."""
        if resource_id in self._resources:
            del self._resources[resource_id]
            return True
        return False

    async def get_resource(self, resource_id: str) -> ComputeResource | None:
        """Get resource by ID."""
        return self._resources.get(resource_id)

    async def allocate(
        self,
        resource_id: str,
        spec: ComputeSpec,
        job_id: str,
    ) -> Allocation:
        """Allocate resources."""
        import uuid
        allocation = Allocation(
            id=str(uuid.uuid4())[:8],
            resource_id=resource_id,
            job_id=job_id,
            allocated_spec=spec,
            started_at=time.time(),
        )
        self._allocations[allocation.id] = allocation
        return allocation

    async def release(self, allocation_id: str) -> bool:
        """Release allocation."""
        if allocation_id in self._allocations:
            self._allocations[allocation_id].status = "released"
            return True
        return False

    async def submit_job(
        self,
        job: ComputeJob,
        resource_id: str | None = None,
    ) -> ComputeJob:
        """Submit job as Kubernetes Job."""
        job.status = JobStatus.SCHEDULED
        self._jobs[job.id] = job

        if self._connected and job.docker_image:
            try:
                batch_v1 = self._k8s_client.BatchV1Api()

                # Create Kubernetes Job
                k8s_job = self._k8s_client.V1Job(
                    api_version="batch/v1",
                    kind="Job",
                    metadata=self._k8s_client.V1ObjectMeta(
                        name=f"usmsb-{job.id}",
                        namespace=self._namespace,
                    ),
                    spec=self._k8s_client.V1JobSpec(
                        template=self._k8s_client.V1PodTemplateSpec(
                            spec=self._k8s_client.V1PodSpec(
                                containers=[
                                    self._k8s_client.V1Container(
                                        name="main",
                                        image=job.docker_image,
                                        command=[job.command] if job.command else None,
                                        env=[
                                            self._k8s_client.V1EnvVar(name=k, value=v)
                                            for k, v in job.environment.items()
                                        ],
                                    )
                                ],
                                restart_policy="Never",
                            )
                        ),
                        backoff_limit=1,
                    )
                )

                batch_v1.create_namespaced_job(self._namespace, k8s_job)
                job.status = JobStatus.RUNNING
                job.started_at = time.time()

            except Exception as e:
                logger.error(f"Failed to submit Kubernetes job: {e}")
                job.status = JobStatus.FAILED
                job.error = str(e)
        else:
            # Mock execution
            job.status = JobStatus.RUNNING
            job.started_at = time.time()
            await asyncio.sleep(0.1)
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()

        return job

    async def get_job(self, job_id: str) -> ComputeJob | None:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel Kubernetes job."""
        job = self._jobs.get(job_id)
        if not job:
            return False

        if self._connected:
            try:
                batch_v1 = self._k8s_client.BatchV1Api()
                batch_v1.delete_namespaced_job(
                    name=f"usmsb-{job_id}",
                    namespace=self._namespace,
                )
            except Exception as e:
                logger.error(f"Failed to cancel Kubernetes job: {e}")

        job.status = JobStatus.CANCELLED
        job.completed_at = time.time()
        return True

    async def get_job_logs(self, job_id: str) -> list[str]:
        """Get Kubernetes job logs."""
        logs = []

        if self._connected:
            try:
                v1 = self._k8s_client.CoreV1Api()
                pods = v1.list_namespaced_pod(
                    namespace=self._namespace,
                    label_selector=f"job-name=usmsb-{job_id}",
                )

                for pod in pods.items:
                    log = v1.read_namespaced_pod_log(
                        name=pod.metadata.name,
                        namespace=self._namespace,
                    )
                    logs.extend(log.split('\n'))

            except Exception as e:
                logger.error(f"Failed to get logs: {e}")

        return logs

    async def get_job_metrics(self, job_id: str) -> dict[str, Any]:
        """Get job metrics."""
        job = self._jobs.get(job_id)
        if not job:
            return {}

        return {
            "job_id": job_id,
            "status": job.status.value,
            "duration_seconds": (job.completed_at or time.time()) - (job.started_at or job.created_at),
        }

    async def monitor_resource(
        self,
        resource_id: str,
        callback: Callable[[dict[str, Any]], None],
    ) -> str:
        """Monitor Kubernetes resource."""
        import uuid
        return str(uuid.uuid4())[:8]

    async def stop_monitoring(self, monitor_id: str) -> bool:
        """Stop monitoring."""
        return True
