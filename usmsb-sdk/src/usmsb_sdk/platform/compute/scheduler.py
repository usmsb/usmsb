"""
Compute Scheduler Service

Intelligent scheduling service for compute resources.
Handles job queuing, resource matching, and optimization.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from usmsb_sdk.platform.compute.adapter import (
    ComputeJob,
    ComputeResource,
    ComputeSpec,
    ComputeType,
    IComputeResourceAdapter,
    JobStatus,
    LocalComputeAdapter,
    ResourceStatus,
)

logger = logging.getLogger(__name__)


class SchedulingStrategy(str, Enum):
    """Job scheduling strategies."""
    FIFO = "fifo"  # First in, first out
    PRIORITY = "priority"  # Highest priority first
    SHORTEST_JOB = "shortest_job"  # Shortest jobs first
    FAIR_SHARE = "fair_share"  # Fair resource allocation
    COST_OPTIMIZED = "cost_optimized"  # Minimize cost
    PERFORMANCE = "performance"  # Maximize performance


@dataclass
class SchedulingConfig:
    """Scheduler configuration."""
    strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY
    max_queue_size: int = 1000
    scheduling_interval: float = 1.0  # seconds
    job_timeout: float = 3600.0  # 1 hour default
    retry_failed_jobs: bool = True
    max_retries: int = 3
    backoff_factor: float = 2.0


@dataclass
class QueueItem:
    """Item in the job queue."""
    job: ComputeJob
    enqueued_at: float = field(default_factory=lambda: time.time())
    retry_count: int = 0
    priority: int = 0


@dataclass
class SchedulerMetrics:
    """Scheduler performance metrics."""
    total_jobs_submitted: int = 0
    total_jobs_completed: int = 0
    total_jobs_failed: int = 0
    total_jobs_cancelled: int = 0
    average_wait_time: float = 0.0
    average_execution_time: float = 0.0
    queue_length: int = 0
    resources_available: int = 0


class ComputeSchedulerService:
    """
    Compute Scheduler Service.

    Provides intelligent job scheduling across compute resources:
    - Job queuing and prioritization
    - Resource matching and allocation
    - Load balancing
    - Cost optimization
    - Monitoring and metrics
    """

    def __init__(
        self,
        compute_adapter: Optional[IComputeResourceAdapter] = None,
        config: Optional[SchedulingConfig] = None,
    ):
        """
        Initialize the Compute Scheduler Service.

        Args:
            compute_adapter: Compute resource adapter
            config: Scheduler configuration
        """
        self.adapter = compute_adapter or LocalComputeAdapter()
        self.config = config or SchedulingConfig()

        # State
        self._queue: List[QueueItem] = []
        self._running_jobs: Dict[str, ComputeJob] = {}
        self._resources: Dict[str, ComputeResource] = {}
        self._metrics = SchedulerMetrics()

        # Control
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_job_started: Optional[Callable[[ComputeJob], None]] = None
        self.on_job_completed: Optional[Callable[[ComputeJob], None]] = None
        self.on_job_failed: Optional[Callable[[ComputeJob, str], None]] = None

    async def initialize(self) -> bool:
        """
        Initialize the scheduler.

        Returns:
            True if successful
        """
        # Initialize compute adapter
        success = await self.adapter.initialize({})
        if not success:
            logger.error("Failed to initialize compute adapter")
            return False

        # Discover resources
        resources = await self.adapter.discover_resources()
        for resource in resources:
            self._resources[resource.id] = resource

        logger.info(f"Compute Scheduler initialized with {len(resources)} resources")
        return True

    async def shutdown(self) -> None:
        """Shutdown the scheduler."""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # Cancel running jobs
        for job_id in list(self._running_jobs.keys()):
            await self.adapter.cancel_job(job_id)

        await self.adapter.shutdown()
        logger.info("Compute Scheduler shutdown complete")

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self._running:
            return

        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        logger.info("Scheduler stopped")

    async def submit_job(
        self,
        name: str,
        required_spec: ComputeSpec,
        owner_id: str,
        command: Optional[str] = None,
        docker_image: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        priority: int = 0,
        input_data: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> ComputeJob:
        """
        Submit a new job to the scheduler.

        Args:
            name: Job name
            required_spec: Required compute specifications
            owner_id: Owner/submitter ID
            command: Command to execute
            docker_image: Docker image to use
            environment: Environment variables
            priority: Job priority (higher = more important)
            input_data: Input data path
            output_path: Output data path

        Returns:
            Created job
        """
        import uuid

        if len(self._queue) >= self.config.max_queue_size:
            raise ValueError("Job queue is full")

        job = ComputeJob(
            id=str(uuid.uuid4())[:8],
            name=name,
            owner_id=owner_id,
            required_spec=required_spec,
            command=command,
            docker_image=docker_image,
            environment=environment or {},
            input_data=input_data,
            output_path=output_path,
            priority=priority,
            status=JobStatus.QUEUED,
        )

        # Add to queue
        queue_item = QueueItem(job=job, priority=priority)
        self._queue.append(queue_item)
        self._metrics.total_jobs_submitted += 1
        self._metrics.queue_length = len(self._queue)

        logger.info(f"Job {job.id} submitted: {name}")
        return job

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled
        """
        # Check queue
        for i, item in enumerate(self._queue):
            if item.job.id == job_id:
                self._queue.pop(i)
                item.job.status = JobStatus.CANCELLED
                self._metrics.total_jobs_cancelled += 1
                return True

        # Check running jobs
        if job_id in self._running_jobs:
            success = await self.adapter.cancel_job(job_id)
            if success:
                del self._running_jobs[job_id]
                self._metrics.total_jobs_cancelled += 1
            return success

        return False

    async def get_job(self, job_id: str) -> Optional[ComputeJob]:
        """Get job by ID."""
        # Check adapter
        job = await self.adapter.get_job(job_id)
        if job:
            return job

        # Check queue
        for item in self._queue:
            if item.job.id == job_id:
                return item.job

        return None

    async def get_queue(self) -> List[ComputeJob]:
        """Get current job queue."""
        return [item.job for item in self._queue]

    async def get_resources(self) -> List[ComputeResource]:
        """Get available resources."""
        return list(self._resources.values())

    async def get_metrics(self) -> SchedulerMetrics:
        """Get scheduler metrics."""
        self._metrics.queue_length = len(self._queue)
        self._metrics.resources_available = sum(
            1 for r in self._resources.values()
            if r.status == ResourceStatus.AVAILABLE
        )
        return self._metrics

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._schedule_jobs()
                await self._check_running_jobs()
                await asyncio.sleep(self.config.scheduling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _schedule_jobs(self) -> None:
        """Schedule jobs from queue to resources."""
        if not self._queue:
            return

        # Sort queue by strategy
        sorted_queue = self._sort_queue()

        scheduled = []

        for item in sorted_queue:
            job = item.job

            # Find matching resource
            resource = await self._find_resource(job.required_spec)

            if resource:
                # Submit job
                try:
                    submitted_job = await self.adapter.submit_job(job, resource.id)

                    if submitted_job.status in (JobStatus.SCHEDULED, JobStatus.RUNNING):
                        self._running_jobs[job.id] = submitted_job
                        scheduled.append(item)

                        if self.on_job_started:
                            self.on_job_started(submitted_job)

                        logger.info(f"Job {job.id} scheduled on resource {resource.id}")

                except Exception as e:
                    logger.error(f"Failed to schedule job {job.id}: {e}")

                    if self.config.retry_failed_jobs and item.retry_count < self.config.max_retries:
                        item.retry_count += 1
                        logger.info(f"Job {job.id} will be retried (attempt {item.retry_count})")
                    else:
                        job.status = JobStatus.FAILED
                        job.error = str(e)
                        scheduled.append(item)
                        self._metrics.total_jobs_failed += 1

                        if self.on_job_failed:
                            self.on_job_failed(job, str(e))

        # Remove scheduled jobs from queue
        for item in scheduled:
            if item in self._queue:
                self._queue.remove(item)

        self._metrics.queue_length = len(self._queue)

    def _sort_queue(self) -> List[QueueItem]:
        """Sort queue by scheduling strategy."""
        if self.config.strategy == SchedulingStrategy.FIFO:
            return self._queue.copy()

        elif self.config.strategy == SchedulingStrategy.PRIORITY:
            return sorted(self._queue, key=lambda x: x.priority, reverse=True)

        elif self.config.strategy == SchedulingStrategy.SHORTEST_JOB:
            # Estimate based on resource requirements
            return sorted(
                self._queue,
                key=lambda x: x.job.required_spec.cpu_cores + x.job.required_spec.gpu_count
            )

        elif self.config.strategy == SchedulingStrategy.FAIR_SHARE:
            # Group by owner and round-robin
            owner_queues: Dict[str, List[QueueItem]] = {}
            for item in self._queue:
                owner = item.job.owner_id
                if owner not in owner_queues:
                    owner_queues[owner] = []
                owner_queues[owner].append(item)

            # Interleave
            result = []
            max_len = max(len(q) for q in owner_queues.values()) if owner_queues else 0
            for i in range(max_len):
                for owner, queue in owner_queues.items():
                    if i < len(queue):
                        result.append(queue[i])
            return result

        return self._queue.copy()

    async def _find_resource(self, required: ComputeSpec) -> Optional[ComputeResource]:
        """Find a suitable resource for the job."""
        candidates = []

        for resource in self._resources.values():
            if resource.status != ResourceStatus.AVAILABLE:
                continue

            if not resource.can_allocate(required):
                continue

            candidates.append(resource)

        if not candidates:
            return None

        # Select best candidate (lowest utilization)
        return min(candidates, key=lambda r: r.utilized)

    async def _check_running_jobs(self) -> None:
        """Check status of running jobs."""
        completed = []

        for job_id, job in self._running_jobs.items():
            updated_job = await self.adapter.get_job(job_id)

            if updated_job:
                job.status = updated_job.status
                job.result = updated_job.result
                job.error = updated_job.error
                job.completed_at = updated_job.completed_at

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                completed.append(job_id)

                if job.status == JobStatus.COMPLETED:
                    self._metrics.total_jobs_completed += 1
                    if self.on_job_completed:
                        self.on_job_completed(job)

                elif job.status == JobStatus.FAILED:
                    self._metrics.total_jobs_failed += 1
                    if self.on_job_failed:
                        self.on_job_failed(job, job.error or "Unknown error")

        # Remove completed jobs
        for job_id in completed:
            del self._running_jobs[job_id]

        # Update metrics
        if self._metrics.total_jobs_completed > 0:
            # Would calculate from actual job times
            self._metrics.average_execution_time = 60.0  # Placeholder

    def get_resource_recommendations(
        self,
        spec: ComputeSpec,
    ) -> List[Tuple[ComputeResource, float]]:
        """
        Get resource recommendations for a specification.

        Args:
            spec: Required specifications

        Returns:
            List of (resource, score) tuples
        """
        recommendations = []

        for resource in self._resources.values():
            if resource.status != ResourceStatus.AVAILABLE:
                continue

            if not resource.can_allocate(spec):
                continue

            # Calculate score (higher is better)
            score = 1.0 - resource.utilized

            # Prefer GPU resources for GPU jobs
            if spec.gpu_count > 0 and resource.spec.gpu_count > 0:
                score += 0.5

            # Prefer lower cost
            if resource.price_per_hour > 0:
                score -= resource.price_per_hour / 100

            recommendations.append((resource, score))

        return sorted(recommendations, key=lambda x: x[1], reverse=True)
