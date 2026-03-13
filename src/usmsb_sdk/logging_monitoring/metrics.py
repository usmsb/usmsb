"""
Metrics Collection and Reporting

Comprehensive metrics collection, aggregation, and reporting system.
"""

import asyncio
import logging
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SUMMARY = "summary"


@dataclass
class MetricValue:
    """A single metric value."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "unit": self.unit,
        }


@dataclass
class MetricSeries:
    """A time series of metric values."""
    name: str
    metric_type: MetricType
    values: List[Tuple[float, float]] = field(default_factory=list)  # (timestamp, value)
    tags: Dict[str, str] = field(default_factory=dict)
    unit: Optional[str] = None
    max_size: int = 1000

    def add_value(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add a value to the series."""
        ts = timestamp or time.time()
        self.values.append((ts, value))
        if len(self.values) > self.max_size:
            self.values.pop(0)

    def get_latest(self) -> Optional[float]:
        """Get the latest value."""
        if self.values:
            return self.values[-1][1]
        return None

    def get_stats(self) -> Dict[str, float]:
        """Get statistics for the series."""
        if not self.values:
            return {}

        vals = [v[1] for v in self.values]
        return {
            "count": len(vals),
            "min": min(vals),
            "max": max(vals),
            "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "std": statistics.stdev(vals) if len(vals) > 1 else 0,
            "sum": sum(vals),
        }


class Counter:
    """A counter metric that only increases."""

    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.value = 0
        self.tags = tags or {}
        self.series = MetricSeries(name, MetricType.COUNTER, tags=self.tags)

    def increment(self, amount: float = 1) -> float:
        """Increment the counter."""
        self.value += amount
        self.series.add_value(self.value)
        return self.value

    def decrement(self, amount: float = 1) -> float:
        """Decrement the counter (use with caution)."""
        self.value = max(0, self.value - amount)
        self.series.add_value(self.value)
        return self.value

    def reset(self) -> None:
        """Reset the counter."""
        self.value = 0
        self.series.add_value(0)

    def get_value(self) -> float:
        """Get current value."""
        return self.value


class Gauge:
    """A gauge metric that can go up or down."""

    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.value = 0.0
        self.tags = tags or {}
        self.series = MetricSeries(name, MetricType.GAUGE, tags=self.tags)

    def set(self, value: float) -> float:
        """Set the gauge value."""
        self.value = value
        self.series.add_value(value)
        return self.value

    def increment(self, amount: float = 1) -> float:
        """Increment the gauge."""
        return self.set(self.value + amount)

    def decrement(self, amount: float = 1) -> float:
        """Decrement the gauge."""
        return self.set(self.value - amount)

    def get_value(self) -> float:
        """Get current value."""
        return self.value


class Histogram:
    """A histogram metric for distribution analysis."""

    def __init__(
        self,
        name: str,
        buckets: Optional[List[float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")]
        self.bucket_counts: Dict[float, int] = {b: 0 for b in self.buckets}
        self.sum = 0.0
        self.count = 0
        self.tags = tags or {}
        self.series = MetricSeries(name, MetricType.HISTOGRAM, tags=self.tags)
        self._values: List[float] = []

    def observe(self, value: float) -> None:
        """Observe a value."""
        self.sum += value
        self.count += 1
        self._values.append(value)

        for bucket in self.buckets:
            if value <= bucket:
                self.bucket_counts[bucket] += 1

        self.series.add_value(value)

    def get_percentile(self, percentile: float) -> Optional[float]:
        """Get a percentile value."""
        if not self._values:
            return None
        sorted_values = sorted(self._values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def get_stats(self) -> Dict[str, Any]:
        """Get histogram statistics."""
        stats = {
            "count": self.count,
            "sum": self.sum,
            "mean": self.sum / self.count if self.count > 0 else 0,
            "buckets": {str(k): v for k, v in self.bucket_counts.items()},
        }

        # Add percentiles
        for p in [50, 90, 95, 99]:
            stats[f"p{p}"] = self.get_percentile(p)

        return stats


class Timer:
    """A timer metric for measuring durations."""

    def __init__(self, name: str, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.tags = tags or {}
        self.histogram = Histogram(name, tags=self.tags)
        self._start_times: Dict[str, float] = {}

    def start(self, label: Optional[str] = None) -> str:
        """Start a timer and return a label for stopping."""
        label = label or f"{self.name}_{len(self._start_times)}"
        self._start_times[label] = time.time()
        return label

    def stop(self, label: str) -> float:
        """Stop a timer and record the duration."""
        if label not in self._start_times:
            logger.warning(f"Timer {label} not found")
            return 0.0

        duration = time.time() - self._start_times.pop(label)
        self.histogram.observe(duration)
        return duration

    def time(self, func: Callable) -> Callable:
        """Decorator to time a function."""
        def wrapper(*args, **kwargs):
            label = self.start()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                self.stop(label)
        return wrapper

    async def time_async(self, func: Callable) -> Callable:
        """Decorator to time an async function."""
        async def wrapper(*args, **kwargs):
            label = self.start()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                self.stop(label)
        return wrapper

    def get_stats(self) -> Dict[str, Any]:
        """Get timer statistics."""
        return self.histogram.get_stats()


class MetricsRegistry:
    """
    Central registry for all metrics.

    Provides a unified interface for creating and accessing metrics.
    """

    def __init__(self, namespace: str = ""):
        """
        Initialize the metrics registry.

        Args:
            namespace: Optional namespace prefix for all metrics
        """
        self.namespace = namespace
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._timers: Dict[str, Timer] = {}
        self._callbacks: List[Callable] = []

    def _get_full_name(self, name: str) -> str:
        """Get the full metric name with namespace."""
        if self.namespace:
            return f"{self.namespace}.{name}"
        return name

    def counter(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> Counter:
        """
        Get or create a counter metric.

        Args:
            name: Metric name
            tags: Optional tags

        Returns:
            Counter instance
        """
        full_name = self._get_full_name(name)
        if full_name not in self._counters:
            self._counters[full_name] = Counter(full_name, tags)
        return self._counters[full_name]

    def gauge(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> Gauge:
        """
        Get or create a gauge metric.

        Args:
            name: Metric name
            tags: Optional tags

        Returns:
            Gauge instance
        """
        full_name = self._get_full_name(name)
        if full_name not in self._gauges:
            self._gauges[full_name] = Gauge(full_name, tags)
        return self._gauges[full_name]

    def histogram(
        self,
        name: str,
        buckets: Optional[List[float]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Histogram:
        """
        Get or create a histogram metric.

        Args:
            name: Metric name
            buckets: Histogram buckets
            tags: Optional tags

        Returns:
            Histogram instance
        """
        full_name = self._get_full_name(name)
        if full_name not in self._histograms:
            self._histograms[full_name] = Histogram(full_name, buckets, tags)
        return self._histograms[full_name]

    def timer(
        self,
        name: str,
        tags: Optional[Dict[str, str]] = None,
    ) -> Timer:
        """
        Get or create a timer metric.

        Args:
            name: Metric name
            tags: Optional tags

        Returns:
            Timer instance
        """
        full_name = self._get_full_name(name)
        if full_name not in self._timers:
            self._timers[full_name] = Timer(full_name, tags)
        return self._timers[full_name]

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metric values."""
        metrics = {}

        for name, counter in self._counters.items():
            metrics[name] = {
                "type": "counter",
                "value": counter.get_value(),
                "tags": counter.tags,
            }

        for name, gauge in self._gauges.items():
            metrics[name] = {
                "type": "gauge",
                "value": gauge.get_value(),
                "tags": gauge.tags,
            }

        for name, histogram in self._histograms.items():
            metrics[name] = {
                "type": "histogram",
                "stats": histogram.get_stats(),
                "tags": histogram.tags,
            }

        for name, timer in self._timers.items():
            metrics[name] = {
                "type": "timer",
                "stats": timer.get_stats(),
                "tags": timer.tags,
            }

        return metrics

    def get_metric(self, name: str) -> Optional[Union[Counter, Gauge, Histogram, Timer]]:
        """Get a specific metric by name."""
        full_name = self._get_full_name(name)
        if full_name in self._counters:
            return self._counters[full_name]
        if full_name in self._gauges:
            return self._gauges[full_name]
        if full_name in self._histograms:
            return self._histograms[full_name]
        if full_name in self._timers:
            return self._timers[full_name]
        return None

    def register_callback(self, callback: Callable) -> None:
        """Register a callback to be called when metrics are collected."""
        self._callbacks.append(callback)

    async def collect(self) -> Dict[str, Any]:
        """Collect all metrics including callbacks."""
        metrics = self.get_all_metrics()

        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    additional = await callback()
                else:
                    additional = callback()
                metrics.update(additional)
            except Exception as e:
                logger.error(f"Metrics callback failed: {e}")

        return metrics

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        for name, counter in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            tags_str = self._format_tags(counter.tags)
            lines.append(f"{name}{tags_str} {counter.get_value()}")

        for name, gauge in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            tags_str = self._format_tags(gauge.tags)
            lines.append(f"{name}{tags_str} {gauge.get_value()}")

        for name, histogram in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            stats = histogram.get_stats()
            for bucket, count in stats.get("buckets", {}).items():
                lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
            lines.append(f"{name}_sum {stats.get('sum', 0)}")
            lines.append(f"{name}_count {stats.get('count', 0)}")

        return "\n".join(lines)

    def _format_tags(self, tags: Dict[str, str]) -> str:
        """Format tags for Prometheus export."""
        if not tags:
            return ""
        return "{" + ", ".join(f'{k}="{v}"' for k, v in tags.items()) + "}"

    def reset(self) -> None:
        """Reset all metrics."""
        for counter in self._counters.values():
            counter.reset()
        for gauge in self._gauges.values():
            gauge.set(0)


class MetricsCollector:
    """
    Collects metrics from various sources at regular intervals.
    """

    def __init__(
        self,
        registry: MetricsRegistry,
        interval: float = 60.0,
    ):
        """
        Initialize the collector.

        Args:
            registry: Metrics registry to use
            interval: Collection interval in seconds
        """
        self.registry = registry
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._collectors: List[Callable] = []

    def add_collector(self, collector: Callable) -> None:
        """Add a collector function."""
        self._collectors.append(collector)

    async def start(self) -> None:
        """Start collecting metrics."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._collect_loop())
        logger.info(f"Metrics collector started with interval {self.interval}s")

    async def stop(self) -> None:
        """Stop collecting metrics."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Metrics collector stopped")

    async def _collect_loop(self) -> None:
        """Main collection loop."""
        while self._running:
            try:
                await self._collect()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                await asyncio.sleep(self.interval)

    async def _collect(self) -> None:
        """Run all collectors."""
        for collector in self._collectors:
            try:
                if asyncio.iscoroutinefunction(collector):
                    await collector(self.registry)
                else:
                    collector(self.registry)
            except Exception as e:
                logger.error(f"Collector failed: {e}")


# Standard system metrics collector
async def collect_system_metrics(registry: MetricsRegistry) -> None:
    """Collect standard system metrics."""
    import os

    # CPU usage (simplified)
    try:
        import psutil
        cpu_gauge = registry.gauge("system.cpu_percent")
        cpu_gauge.set(psutil.cpu_percent())

        memory_gauge = registry.gauge("system.memory_percent")
        memory_gauge.set(psutil.virtual_memory().percent)

        disk_gauge = registry.gauge("system.disk_percent")
        disk_gauge.set(psutil.disk_usage("/").percent)
    except ImportError:
        pass

    # Process info
    process_count_gauge = registry.gauge("system.process_count")
    process_count_gauge.set(len(os.getpid()))


# Global metrics registry
_registry: Optional[MetricsRegistry] = None
_collector: Optional[MetricsCollector] = None


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


async def init_metrics(namespace: str = "", interval: float = 60.0) -> MetricsRegistry:
    """Initialize metrics collection."""
    global _registry, _collector

    _registry = MetricsRegistry(namespace)
    _collector = MetricsCollector(_registry, interval)
    _collector.add_collector(collect_system_metrics)
    await _collector.start()

    return _registry
