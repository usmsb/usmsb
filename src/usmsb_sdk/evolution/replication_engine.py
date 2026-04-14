"""
ReplicationEngine - 自我复制引擎

Phase 5: 自我进化层 - 核心模块

Agent 自我复制系统，包括：
- 复制触发条件
- 基因复制
- 资源分配
- 复制限制
"""

import uuid
import hashlib
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ReplicationRequest:
    """复制请求"""
    id: str
    source_agent_id: str
    target_agent_id: str | None = None
    replication_type: str = "budding"  # budding, fission, spawn
    status: str = "pending"
    genes_copied: int = 0
    resources_allocated: float = 0.0
    created_at: float = field(default_factory=datetime.now().timestamp)
    completed_at: float | None = None


@dataclass
class Replica:
    """复制体"""
    id: str
    parent_id: str
    agent_id: str
    genes: dict[str, Any]
    generation: int
    birth_time: float
    status: str = "active"  # active, degraded, terminated
    fitness_score: float = 0.5


class ReplicationEngine:
    """
    自我复制引擎
    
    实现 Agent 的自我复制机制：
    - Budding: 从母体出芽（新 Agent 继承大部分基因）
    - Fission: 分裂（资源对半，基因对半）
    - Spawn: 产卵（快速生成多个小型 Agent）
    
    复制触发条件：
    - 适应度超过阈值
    - 资源充足
    - 生存时间足够
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/replication_engine.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 配置
        self.min_fitness_to_replicate = 0.7
        self.min_resources_to_replicate = 1000.0
        self.min_age_to_replicate = 86400 * 7  # 7 天
        self.max_generation = 10
        self.replication_cooldown = 86400  # 1 天冷却
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replicas (
                id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                generation INTEGER NOT NULL,
                birth_time REAL NOT NULL,
                status TEXT NOT NULL,
                fitness_score REAL DEFAULT 0.5
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replication_requests (
                id TEXT PRIMARY KEY,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT,
                replication_type TEXT NOT NULL,
                status TEXT NOT NULL,
                genes_copied INTEGER DEFAULT 0,
                resources_allocated REAL DEFAULT 0,
                created_at REAL NOT NULL,
                completed_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replication_history (
                id TEXT PRIMARY KEY,
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                replication_type TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def can_replicate(
        self,
        agent_id: str,
        fitness_score: float,
        resources: float,
        age_seconds: float
    ) -> tuple[bool, str]:
        """
        检查是否可以复制
        
        Returns:
            (can_replicate, reason)
        """
        # 检查适应度
        if fitness_score < self.min_fitness_to_replicate:
            return False, f"Fitness {fitness_score:.2f} < {self.min_fitness_to_replicate}"
        
        # 检查资源
        if resources < self.min_resources_to_replicate:
            return False, f"Resources {resources:.0f} < {self.min_resources_to_replicate}"
        
        # 检查年龄
        if age_seconds < self.min_age_to_replicate:
            return False, f"Age {age_seconds/3600:.0f}h < {self.min_age_to_replicate/3600}h"
        
        # 检查冷却
        if self._in_cooldown(agent_id):
            return False, "Replication in cooldown"
        
        return True, "OK"
    
    def _in_cooldown(self, agent_id: str) -> bool:
        """检查是否在冷却期"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT created_at FROM replication_requests
            WHERE source_agent_id = ? AND status = 'completed'
            ORDER BY created_at DESC
            LIMIT 1
        """, (agent_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            elapsed = datetime.now().timestamp() - row[0]
            return elapsed < self.replication_cooldown
        
        return False
    
    def replicate(
        self,
        source_agent_id: str,
        source_genes: dict[str, Any],
        resources: float,
        replication_type: str = "budding"
    ) -> ReplicationRequest | None:
        """
        执行复制
        
        Args:
            source_agent_id: 源 Agent ID
            source_genes: 源 Agent 基因
            resources: 可用资源
            replication_type: 复制类型
            
        Returns:
            ReplicationRequest 或 None
        """
        # 创建复制请求
        request = ReplicationRequest(
            id=str(uuid.uuid4()),
            source_agent_id=source_agent_id,
            replication_type=replication_type
        )
        
        # 计算资源分配
        if replication_type == "budding":
            resource_share = resources * 0.3  # 出芽消耗 30%
        elif replication_type == "fission":
            resource_share = resources * 0.5  # 分裂消耗 50%
        else:  # spawn
            resource_share = resources * 0.1  # 产卵消耗 10%
        
        request.resources_allocated = resource_share
        
        # 复制基因
        child_genes = self._copy_genes(source_genes, replication_type)
        request.genes_copied = len(child_genes)
        
        # 生成子 Agent ID
        child_id = f"{source_agent_id}_child_{request.id[:8]}"
        
        # 保存复制请求
        self._save_request(request)
        
        # 创建复制体记录
        self._create_replica(
            parent_id=source_agent_id,
            child_id=child_id,
            genes=child_genes,
            generation=1  # TODO: 从父代获取
        )
        
        # 更新状态
        request.status = "completed"
        request.target_agent_id = child_id
        request.completed_at = datetime.now().timestamp()
        self._save_request(request)
        
        # 记录历史
        self._record_history(source_agent_id, child_id, replication_type)
        
        return request
    
    def _copy_genes(
        self,
        genes: dict[str, Any],
        replication_type: str
    ) -> dict[str, Any]:
        """复制基因"""
        if replication_type == "budding":
            # 出芽：轻微突变
            return self._mutate_genes(genes, rate=0.1)
        elif replication_type == "fission":
            # 分裂：基因对半 + 少量突变
            return self._split_genes(genes, rate=0.05)
        else:  # spawn
            # 产卵：大量突变，可能丢失部分基因
            return self._mutate_genes(genes, rate=0.2)
    
    def _mutate_genes(self, genes: dict[str, Any], rate: float) -> dict[str, Any]:
        """突变基因"""
        import random
        
        mutated = {}
        
        for key, value in genes.items():
            if random.random() < rate:
                # 数值突变
                if isinstance(value, (int, float)):
                    mutated[key] = value * random.uniform(0.8, 1.2)
                else:
                    mutated[key] = value
            else:
                mutated[key] = value
        
        return mutated
    
    def _split_genes(self, genes: dict[str, Any], rate: float) -> dict[str, Any]:
        """分裂基因"""
        items = list(genes.items())
        half = len(items) // 2
        
        # 随机选择一半
        import random
        selected = random.sample(items, half)
        
        # 添加到子代
        split = dict(selected)
        
        # 对选中基因轻微突变
        return self._mutate_genes(split, rate)
    
    def _create_replica(
        self,
        parent_id: str,
        child_id: str,
        genes: dict[str, Any],
        generation: int
    ) -> None:
        """创建复制体记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO replicas
            (id, parent_id, agent_id, generation, birth_time, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            parent_id,
            child_id,
            generation,
            datetime.now().timestamp(),
            "active"
        ))
        
        conn.commit()
        conn.close()
    
    def _save_request(self, request: ReplicationRequest) -> None:
        """保存复制请求"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO replication_requests
            (id, source_agent_id, target_agent_id, replication_type, status,
             genes_copied, resources_allocated, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.id,
            request.source_agent_id,
            request.target_agent_id,
            request.replication_type,
            request.status,
            request.genes_copied,
            request.resources_allocated,
            request.created_at,
            request.completed_at
        ))
        
        conn.commit()
        conn.close()
    
    def _record_history(
        self,
        parent_id: str,
        child_id: str,
        replication_type: str
    ) -> None:
        """记录复制历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO replication_history
            (id, parent_id, child_id, replication_type, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            parent_id,
            child_id,
            replication_type,
            datetime.now().timestamp()
        ))
        
        conn.commit()
        conn.close()
    
    def get_replicas(self, agent_id: str) -> list[dict]:
        """获取复制体列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, parent_id, agent_id, generation, birth_time, status, fitness_score
            FROM replicas
            WHERE parent_id = ? OR agent_id = ?
            ORDER BY birth_time DESC
        """, (agent_id, agent_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "parent_id": row[1],
                "agent_id": row[2],
                "generation": row[3],
                "birth_time": row[4],
                "status": row[5],
                "fitness_score": row[6]
            }
            for row in rows
        ]
    
    def get_replication_count(self, agent_id: str) -> int:
        """获取复制次数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM replication_history
            WHERE parent_id = ?
        """, (agent_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def terminate_replica(self, replica_id: str) -> bool:
        """终止复制体"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE replicas SET status = 'terminated'
            WHERE id = ?
        """, (replica_id,))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0
