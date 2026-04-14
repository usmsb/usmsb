"""
PerformanceTracker - 性能追踪系统

完整的性能监控：
- Agent 性能指标
- 任务执行追踪
- 资源使用监控
- 瓶颈识别
"""

import uuid
import time
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class PerformanceMetric:
    """性能指标"""
    id: str
    agent_id: str
    metric_type: str  # latency, throughput, success, error, resource
    value: float
    unit: str
    timestamp: float
    metadata: dict = field(default_factory=dict)


@dataclass
class TaskExecution:
    """任务执行记录"""
    task_id: str
    agent_id: str
    task_type: str
    started_at: float
    completed_at: float | None = None
    status: str = "running"  # running, completed, failed, timeout
    result: Any = None
    error: str | None = None


@dataclass
class AgentPerformanceReport:
    """Agent 性能报告"""
    agent_id: str
    period_start: float
    period_end: float
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    success_rate: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    throughput: float  # tasks per minute
    resource_usage: dict
    bottlenecks: list[str]


class PerformanceTracker:
    """
    性能追踪器
    
    完整的性能监控解决方案。
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/performance_tracker.db"
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()
        
        # 内存缓存
        self._active_tasks: dict[str, TaskExecution] = {}
        self._recent_metrics: deque = deque(maxlen=10000)
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 性能指标表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp REAL NOT NULL,
                metadata TEXT DEFAULT '{}'
            )
        """)
        
        # 任务执行表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_executions (
                task_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                started_at REAL NOT NULL,
                completed_at REAL,
                status TEXT NOT NULL,
                result TEXT,
                error TEXT
            )
        """)
        
        # 资源使用表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_usage (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_metrics ON metrics(agent_id, timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_tasks ON task_executions(agent_id, started_at)")
        
        conn.commit()
        conn.close()
    
    def record_metric(
        self,
        agent_id: str,
        metric_type: str,
        value: float,
        unit: str = "",
        metadata: dict = None
    ) -> str:
        """记录性能指标"""
        metric = PerformanceMetric(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            metric_type=metric_type,
            value=value,
            unit=unit,
            timestamp=datetime.now().timestamp(),
            metadata=metadata or {}
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO metrics (id, agent_id, metric_type, value, unit, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            metric.id,
            metric.agent_id,
            metric.metric_type,
            metric.value,
            metric.unit,
            metric.timestamp,
            str(metric.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        self._recent_metrics.append(metric)
        return metric.id
    
    def start_task(self, task_id: str, agent_id: str, task_type: str) -> None:
        """开始任务追踪"""
        task = TaskExecution(
            task_id=task_id,
            agent_id=agent_id,
            task_type=task_type,
            started_at=datetime.now().timestamp()
        )
        self._active_tasks[task_id] = task
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO task_executions (task_id, agent_id, task_type, started_at, status)
            VALUES (?, ?, ?, ?, 'running')
        """, (task_id, agent_id, task_type, task.started_at))
        
        conn.commit()
        conn.close()
    
    def complete_task(
        self,
        task_id: str,
        status: str = "completed",
        result: Any = None,
        error: str | None = None
    ) -> None:
        """完成任务追踪"""
        if task_id not in self._active_tasks:
            return
        
        task = self._active_tasks[task_id]
        task.completed_at = datetime.now().timestamp()
        task.status = status
        task.result = result
        task.error = error
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE task_executions
            SET completed_at = ?, status = ?, result = ?, error = ?
            WHERE task_id = ?
        """, (task.completed_at, status, str(result) if result else None, error, task_id))
        
        conn.commit()
        conn.close()
        
        del self._active_tasks[task_id]
        
        # 记录延迟指标
        if task.completed_at and task.started_at:
            latency = task.completed_at - task.started_at
            self.record_metric(
                agent_id=task.agent_id,
                metric_type="latency",
                value=latency,
                unit="seconds",
                metadata={"task_type": task.task_type, "status": status}
            )
    
    def record_resource_usage(
        self,
        agent_id: str,
        resource_type: str,
        value: float
    ) -> None:
        """记录资源使用"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO resource_usage (id, agent_id, resource_type, value, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), agent_id, resource_type, value, datetime.now().timestamp()))
        
        conn.commit()
        conn.close()
    
    def get_agent_performance(
        self,
        agent_id: str,
        period_hours: int = 24
    ) -> AgentPerformanceReport:
        """获取 Agent 性能报告"""
        cutoff = datetime.now().timestamp() - period_hours * 3600
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 任务统计
        cursor.execute("""
            SELECT 
                COUNT(*),
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END),
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
            FROM task_executions
            WHERE agent_id = ? AND started_at > ?
        """, (agent_id, cutoff))
        
        total, completed, failed = cursor.fetchone()
        total = total or 0
        completed = completed or 0
        failed = failed or 0
        
        # 延迟统计
        cursor.execute("""
            SELECT value FROM metrics
            WHERE agent_id = ? AND metric_type = 'latency' AND timestamp > ?
            ORDER BY value
        """, (agent_id, cutoff))
        
        latencies = [row[0] for row in cursor.fetchall()]
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99_latency = latencies[int(len(latencies) * 0.99)] if latencies else 0
        
        # 吞吐量
        throughput = total / (period_hours * 60) if period_hours > 0 else 0
        
        # 资源使用
        cursor.execute("""
            SELECT resource_type, AVG(value), MAX(value)
            FROM resource_usage
            WHERE agent_id = ? AND timestamp > ?
            GROUP BY resource_type
        """, (agent_id, cutoff))
        
        resource_usage = {}
        for resource_type, avg_val, max_val in cursor.fetchall():
            resource_usage[resource_type] = {"avg": avg_val, "max": max_val}
        
        conn.close()
        
        # 瓶颈识别
        bottlenecks = self._identify_bottlenecks(
            agent_id, total, completed, avg_latency, resource_usage
        )
        
        return AgentPerformanceReport(
            agent_id=agent_id,
            period_start=cutoff,
            period_end=datetime.now().timestamp(),
            total_tasks=total,
            completed_tasks=completed,
            failed_tasks=failed,
            success_rate=completed / total if total > 0 else 0,
            avg_latency=avg_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            throughput=throughput,
            resource_usage=resource_usage,
            bottlenecks=bottlenecks
        )
    
    def _identify_bottlenecks(
        self,
        agent_id: str,
        total_tasks: int,
        completed_tasks: int,
        avg_latency: float,
        resource_usage: dict
    ) -> list[str]:
        """识别瓶颈"""
        bottlenecks = []
        
        # 成功率瓶颈
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        if success_rate < 0.8:
            bottlenecks.append(f"Low success rate: {success_rate:.1%}")
        
        # 延迟瓶颈
        if avg_latency > 60:  # > 1 minute
            bottlenecks.append(f"High latency: {avg_latency:.1f}s avg")
        elif avg_latency > 300:  # > 5 minutes
            bottlenecks.append(f"Critical latency: {avg_latency:.1f}s avg")
        
        # 资源瓶颈
        for resource_type, usage in resource_usage.items():
            if usage["avg"] > 0.9:  # > 90% usage
                bottlenecks.append(f"High {resource_type}: {usage['avg']:.1%} avg")
        
        return bottlenecks
    
    def get_all_agents_summary(self, period_hours: int = 24) -> dict:
        """获取所有 Agent 性能摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT agent_id FROM task_executions
            WHERE started_at > ?
        """, (datetime.now().timestamp() - period_hours * 3600,))
        
        agents = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        summaries = {}
        for agent_id in agents:
            report = self.get_agent_performance(agent_id, period_hours)
            summaries[agent_id] = {
                "total_tasks": report.total_tasks,
                "success_rate": report.success_rate,
                "avg_latency": report.avg_latency,
                "bottlenecks": report.bottlenecks
            }
        
        return summaries
    
    def get_metrics_trend(
        self,
        agent_id: str,
        metric_type: str,
        hours: int = 24
    ) -> list[dict]:
        """获取指标趋势"""
        cutoff = datetime.now().timestamp() - hours * 3600
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, value FROM metrics
            WHERE agent_id = ? AND metric_type = ? AND timestamp > ?
            ORDER BY timestamp
        """, (agent_id, metric_type, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"timestamp": row[0], "value": row[1]} for row in rows]
