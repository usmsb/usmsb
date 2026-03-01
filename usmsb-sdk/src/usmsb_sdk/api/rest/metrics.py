"""
Auto-Unregister Metrics

Prometheus-style metrics for monitoring auto-unregister mechanism.
"""

from usmsb_sdk.logging_monitoring.metrics import Counter, Gauge, Histogram

# Auto-Unregister Metrics
auto_unregister_metrics = {
    # Counters
    'agents_marked_offline': Counter('auto_unregister_agents_marked_offline_total'),
    'agents_auto_unregistered': Counter('auto_unregister_agents_deleted_total'),
    'agents_kept_with_wallet': Counter('auto_unregister_agents_kept_with_wallet_total'),
    'agents_skipped_system': Counter('auto_unregister_agents_skipped_system_total'),
    'auto_unregister_errors': Counter('auto_unregister_errors_total'),

    # Gauges
    'agents_online': Gauge('agents_online_count'),
    'agents_offline': Gauge('agents_offline_count'),
    'agents_without_wallet': Gauge('agents_without_wallet_binding_count'),
    'agents_with_wallet': Gauge('agents_with_wallet_binding_count'),

    # Histograms
    'heartbeat_check_duration': Histogram(
        'heartbeat_check_duration_seconds',
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    ),
    'auto_unregister_check_duration': Histogram(
        'auto_unregister_check_duration_seconds',
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    ),
}


def get_auto_unregister_metrics():
    """Get all auto-unregister metrics in Prometheus format.

    Returns:
        Dict with all metrics formatted for Prometheus scraping
    """
    metrics_output = []

    for name, metric in auto_unregister_metrics.items():
        if isinstance(metric, Counter):
            metrics_output.append(f"# TYPE {metric.name} counter")
            metrics_output.append(f"{metric.name} {metric.get_value()}")
        elif isinstance(metric, Gauge):
            metrics_output.append(f"# TYPE {metric.name} gauge")
            metrics_output.append(f"{metric.name} {metric.get_value()}")
        elif isinstance(metric, Histogram):
            stats = metric.get_stats()
            if stats:
                metrics_output.append(f"# TYPE {metric.name} histogram")
                metrics_output.append(f"{metric.name}_sum {stats.get('sum', 0)}")
                metrics_output.append(f"{metric.name}_count {stats.get('count', 0)}")
                for bucket, count in metric.bucket_counts.items():
                    bucket_label = "+Inf" if bucket == float("inf") else str(bucket)
                    metrics_output.append(f"{metric.name}_bucket{{le=\"{bucket_label}\"}} {count}")

    return "\n".join(metrics_output)


def update_agent_metrics(online_count: int, offline_count: int,
                         with_wallet_count: int, without_wallet_count: int):
    """Update agent gauge metrics.

    Args:
        online_count: Number of online agents
        offline_count: Number of offline agents
        with_wallet_count: Number of agents with wallet binding
        without_wallet_count: Number of agents without wallet binding
    """
    auto_unregister_metrics['agents_online'].set(online_count)
    auto_unregister_metrics['agents_offline'].set(offline_count)
    auto_unregister_metrics['agents_with_wallet'].set(with_wallet_count)
    auto_unregister_metrics['agents_without_wallet'].set(without_wallet_count)
