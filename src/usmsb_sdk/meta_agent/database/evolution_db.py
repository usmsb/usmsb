"""
Evolution 数据库

v2.1 因果学习系统的数据持久化层
使用 SQLite 存储任务记录、因果图、元学习权重等信息

数据库：evolution.db（每个用户独立）

表结构：
- task_records: 任务执行记录
- causal_graphs: 因果图
- causal_edges: 因果边
- meta_weights: 元学习权重
- fisher_information: Fisher 信息矩阵（EWC 用）
- causal_tasks: 因果任务（用于元学习）
- skill_gaps: Skill 缺口
- skill_versions: Skill 版本
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.task_record import TaskRecord
from ..models.causal_graph import CausalGraph, CausalEdge


class EvolutionDatabase:
    """
    Evolution 数据库管理器

    每个用户有独立的数据库文件
    """

    def __init__(self, db_path: str):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._local = threading.local()
        self._ensure_db_dir()
        self._init_schema()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def _transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_schema(self):
        """初始化数据库 Schema"""
        with self._transaction() as conn:
            cursor = conn.cursor()

            # 任务记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_records (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    features TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    domain TEXT DEFAULT 'general',
                    conversation_id TEXT,
                    user_id TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            """)

            # 因果图表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_graphs (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata TEXT,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # 因果边表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_edges (
                    id TEXT PRIMARY KEY,
                    graph_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    strength REAL DEFAULT 0.0,
                    confidence REAL DEFAULT 0.0,
                    conditions TEXT,
                    evidence TEXT,
                    is_directed INTEGER DEFAULT 1,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (graph_id) REFERENCES causal_graphs(id)
                )
            """)

            # 元学习权重表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS meta_weights (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    weights TEXT NOT NULL,
                    fisher_info TEXT,
                    updated_at REAL NOT NULL,
                    UNIQUE(domain)
                )
            """)

            # Fisher 信息表（EWC 用）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fisher_information (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    param_name TEXT NOT NULL,
                    importance REAL DEFAULT 0.0,
                    computed_at REAL NOT NULL,
                    UNIQUE(domain, param_name)
                )
            """)

            # 因果任务表（用于元学习）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS causal_tasks (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    support_set TEXT NOT NULL,
                    query_set TEXT NOT NULL,
                    difficulty REAL DEFAULT 0.5,
                    created_at REAL NOT NULL
                )
            """)

            # Skill 缺口表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_gaps (
                    id TEXT PRIMARY KEY,
                    source_node TEXT NOT NULL,
                    target_node TEXT NOT NULL,
                    gap_type TEXT NOT NULL,
                    priority REAL DEFAULT 0.5,
                    description TEXT,
                    status TEXT DEFAULT 'open',
                    created_at REAL NOT NULL,
                    resolved_at REAL
                )
            """)

            # Skill 版本表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_versions (
                    id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    quality_score REAL DEFAULT 0.0,
                    created_at REAL NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_records_domain ON task_records(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_records_timestamp ON task_records(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_causal_edges_graph ON causal_edges(graph_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_fisher_domain ON fisher_information(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_skill_gaps_status ON skill_gaps(status)")

    # ==================== TaskRecord 操作 ====================

    def save_task_record(self, record: TaskRecord) -> None:
        """保存任务记录"""
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO task_records
                (id, task_type, features, strategy, parameters, outcome, timestamp, domain, conversation_id, user_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_id,
                    record.task_type,
                    json.dumps(record.features.to_dict()),
                    json.dumps(record.strategy.to_dict()),
                    json.dumps(record.parameters),
                    json.dumps(record.outcome.to_dict()),
                    record.timestamp,
                    record.domain,
                    record.conversation_id,
                    record.user_id,
                    json.dumps(record.metadata),
                ),
            )

    def get_task_record(self, task_id: str) -> TaskRecord | None:
        """获取任务记录"""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM task_records WHERE id = ?", (task_id,)
        ).fetchone()

        if row is None:
            return None

        return self._row_to_task_record(row)

    def get_task_records_by_domain(self, domain: str, limit: int = 100) -> list[TaskRecord]:
        """获取指定领域的任务记录"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM task_records WHERE domain = ? ORDER BY timestamp DESC LIMIT ?",
            (domain, limit),
        ).fetchall()

        return [self._row_to_task_record(row) for row in rows]

    def get_all_task_records(self, limit: int = 1000) -> list[TaskRecord]:
        """获取所有任务记录"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM task_records ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()

        return [self._row_to_task_record(row) for row in rows]

    def _row_to_task_record(self, row: sqlite3.Row) -> TaskRecord:
        """将数据库行转换为 TaskRecord"""
        from ..models.task_record import TaskFeatures, Strategy, Outcome

        return TaskRecord(
            task_id=row["id"],
            task_type=row["task_type"],
            features=TaskFeatures.from_dict(json.loads(row["features"])),
            strategy=Strategy.from_dict(json.loads(row["strategy"])),
            parameters=json.loads(row["parameters"]),
            outcome=Outcome.from_dict(json.loads(row["outcome"])),
            timestamp=row["timestamp"],
            domain=row["domain"],
            conversation_id=row["conversation_id"],
            user_id=row["user_id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # ==================== CausalGraph 操作 ====================

    def save_causal_graph(self, graph: CausalGraph) -> None:
        """保存因果图"""
        with self._transaction() as conn:
            # 保存图
            conn.execute(
                """
                INSERT OR REPLACE INTO causal_graphs
                (id, name, created_at, updated_at, metadata, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    graph.graph_id,
                    graph.metadata.get("name", ""),
                    graph.created_at,
                    graph.updated_at,
                    json.dumps(graph.metadata),
                    1,
                ),
            )

            # 删除旧边
            conn.execute("DELETE FROM causal_edges WHERE graph_id = ?", (graph.graph_id,))

            # 保存边
            for edge in graph.edges:
                conn.execute(
                    """
                    INSERT INTO causal_edges
                    (id, graph_id, source, target, strength, confidence, conditions, evidence, is_directed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge.edge_id,
                        graph.graph_id,
                        edge.source,
                        edge.target,
                        edge.strength,
                        edge.confidence,
                        json.dumps(edge.conditions),
                        json.dumps(edge.evidence),
                        1 if edge.is_directed else 0,
                        graph.created_at,
                    ),
                )

            # 保存未定向边
            for source, target in graph.undirected_edges:
                edge_id = f"{source}_{target}_undirected"
                conn.execute(
                    """
                    INSERT INTO causal_edges
                    (id, graph_id, source, target, strength, confidence, conditions, evidence, is_directed, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        edge_id,
                        graph.graph_id,
                        source,
                        target,
                        0.0,
                        0.0,
                        json.dumps([]),
                        json.dumps([]),
                        0,
                        graph.created_at,
                    ),
                )

    def get_causal_graph(self, graph_id: str) -> CausalGraph | None:
        """获取因果图"""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM causal_graphs WHERE id = ? AND is_active = 1",
            (graph_id,),
        ).fetchone()

        if row is None:
            return None

        graph = CausalGraph(
            graph_id=row["id"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

        # 加载边
        edge_rows = conn.execute(
            "SELECT * FROM causal_edges WHERE graph_id = ?", (graph_id,)
        ).fetchall()

        for edge_row in edge_rows:
            edge = CausalEdge(
                edge_id=edge_row["id"],
                source=edge_row["source"],
                target=edge_row["target"],
                strength=edge_row["strength"],
                confidence=edge_row["confidence"],
                conditions=json.loads(edge_row["conditions"]) if edge_row["conditions"] else [],
                evidence=json.loads(edge_row["evidence"]) if edge_row["evidence"] else [],
                is_directed=bool(edge_row["is_directed"]),
            )
            if edge.is_directed:
                graph.add_edge(edge)
            else:
                graph.add_undirected_edge(edge.source, edge.target)

        return graph

    def get_latest_causal_graph(self) -> CausalGraph | None:
        """获取最新的因果图"""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT id FROM causal_graphs WHERE is_active = 1 ORDER BY updated_at DESC LIMIT 1",
        ).fetchone()

        if row is None:
            return None

        return self.get_causal_graph(row["id"])

    # ==================== MetaWeights 操作 ====================

    def save_meta_weights(self, domain: str, weights: dict[str, Any], fisher_info: dict[str, float] | None = None) -> None:
        """保存元学习权重"""
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO meta_weights (id, domain, weights, fisher_info, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    f"meta_{domain}",
                    domain,
                    json.dumps(weights),
                    json.dumps(fisher_info) if fisher_info else None,
                    datetime.now().timestamp(),
                ),
            )

    def get_meta_weights(self, domain: str) -> tuple[dict[str, Any], dict[str, float] | None] | None:
        """获取元学习权重"""
        conn = self._get_connection()
        row = conn.execute(
            "SELECT * FROM meta_weights WHERE domain = ?", (domain,)
        ).fetchone()

        if row is None:
            return None

        weights = json.loads(row["weights"])
        fisher_info = json.loads(row["fisher_info"]) if row["fisher_info"] else None
        return weights, fisher_info

    # ==================== Fisher Information 操作 ====================

    def save_fisher_information(self, domain: str, param_importance: dict[str, float]) -> None:
        """保存 Fisher 信息"""
        with self._transaction() as conn:
            for param_name, importance in param_importance.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO fisher_information
                    (id, domain, param_name, importance, computed_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        f"{domain}_{param_name}",
                        domain,
                        param_name,
                        importance,
                        datetime.now().timestamp(),
                    ),
                )

    def get_fisher_information(self, domain: str) -> dict[str, float]:
        """获取 Fisher 信息"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT param_name, importance FROM fisher_information WHERE domain = ?",
            (domain,),
        ).fetchall()

        return {row["param_name"]: row["importance"] for row in rows}

    # ==================== Skill Gap 操作 ====================

    def save_skill_gap(
        self,
        gap_id: str,
        source_node: str,
        target_node: str,
        gap_type: str,
        priority: float,
        description: str,
    ) -> None:
        """保存 Skill 缺口"""
        with self._transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO skill_gaps
                (id, source_node, target_node, gap_type, priority, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
                """,
                (gap_id, source_node, target_node, gap_type, priority, description, datetime.now().timestamp()),
            )

    def get_open_skill_gaps(self) -> list[dict[str, Any]]:
        """获取开放的 Skill 缺口"""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM skill_gaps WHERE status = 'open' ORDER BY priority DESC"
        ).fetchall()

        return [dict(row) for row in rows]

    def resolve_skill_gap(self, gap_id: str) -> None:
        """标记 Skill 缺口为已解决"""
        with self._transaction() as conn:
            conn.execute(
                "UPDATE skill_gaps SET status = 'resolved', resolved_at = ? WHERE id = ?",
                (datetime.now().timestamp(), gap_id),
            )

    # ==================== 统计操作 ====================

    def get_task_record_count(self) -> int:
        """获取任务记录总数"""
        conn = self._get_connection()
        row = conn.execute("SELECT COUNT(*) as count FROM task_records").fetchone()
        return row["count"]

    def get_causal_edge_count(self) -> int:
        """获取因果边总数"""
        conn = self._get_connection()
        row = conn.execute("SELECT COUNT(*) as count FROM causal_edges WHERE is_directed = 1").fetchone()
        return row["count"]

    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
