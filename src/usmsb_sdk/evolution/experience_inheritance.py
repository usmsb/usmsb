"""
ExperienceInheritance - 经验传承系统

核心功能：
- 经验提取和压缩
- 从成功 Agent 传承经验到新 Agent
- 跨 Agent 能力传递
- 经验版本控制
"""

import uuid
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InheritedExperience:
    """传承的经验"""
    id: str
    source_agent_id: str
    target_agent_id: str
    capability: str
    knowledge_blob: str  # JSON 压缩的经验
    inheritance_type: str  # direct, distilled, encoded
    confidence: float
    applied_at: float | None = None
    effectiveness: float = 0.0  # 应用后评估


@dataclass
class ExperienceSnapshot:
    """经验快照"""
    agent_id: str
    timestamp: float
    capabilities: dict  # capability -> performance
    successful_tasks: list[dict]  # 成功的任务记录
    learned_patterns: list[str]  # 学到的模式
    optimization_tips: list[str]  # 优化技巧


class ExperienceInheritance:
    """
    经验传承系统
    
    实现：
    - 经验提取：从成功执行中提取模式
    - 经验压缩：将大量经验压缩成可传承的知识
    - 经验传递：将经验传递给新 Agent
    - 效果追踪：评估传承效果
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/experience_inheritance.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 传承记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inheritances (
                id TEXT PRIMARY KEY,
                source_agent_id TEXT NOT NULL,
                target_agent_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                knowledge_blob TEXT NOT NULL,
                inheritance_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                applied_at REAL,
                effectiveness REAL DEFAULT 0.0,
                created_at REAL NOT NULL
            )
        """)
        
        # 经验快照表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_snapshots (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                capabilities TEXT NOT NULL,
                successful_tasks TEXT NOT NULL,
                learned_patterns TEXT NOT NULL,
                optimization_tips TEXT NOT NULL
            )
        """)
        
        # 传承效果评估表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inheritance_evaluations (
                id TEXT PRIMARY KEY,
                inheritance_id TEXT NOT NULL,
                task_success_rate REAL NOT NULL,
                efficiency_improvement REAL NOT NULL,
                quality_improvement REAL NOT NULL,
                evaluated_at REAL NOT NULL,
                FOREIGN KEY (inheritance_id) REFERENCES inheritances(id)
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON inheritances(source_agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_target ON inheritances(target_agent_id)")
        
        conn.commit()
        conn.close()
    
    def extract_experience(
        self,
        agent_id: str,
        successful_tasks: list[dict],
        failed_tasks: list[dict] = None
    ) -> ExperienceSnapshot:
        """
        从任务执行中提取经验
        
        Args:
            agent_id: Agent ID
            successful_tasks: 成功的任务列表
            failed_tasks: 失败的任务列表
            
        Returns:
            ExperienceSnapshot: 提取的经验快照
        """
        # 分析成功任务，提取模式
        learned_patterns = self._extract_patterns(successful_tasks)
        
        # 从失败中提取教训
        optimization_tips = self._extract_optimizations(failed_tasks or [])
        
        # 评估能力水平
        capabilities = self._evaluate_capabilities(successful_tasks)
        
        # 创建快照
        snapshot = ExperienceSnapshot(
            agent_id=agent_id,
            timestamp=datetime.now().timestamp(),
            capabilities=capabilities,
            successful_tasks=successful_tasks[:10],  # 只保留最近 10 个
            learned_patterns=learned_patterns,
            optimization_tips=optimization_tips
        )
        
        # 持久化
        self._save_snapshot(snapshot)
        
        return snapshot
    
    def _extract_patterns(self, tasks: list[dict]) -> list[str]:
        """从成功任务中提取模式"""
        patterns = []
        
        # 简化实现：基于任务类型聚类
        task_types = defaultdict(list)
        for task in tasks:
            task_type = task.get("type", "unknown")
            task_types[task_type].append(task)
        
        for task_type, type_tasks in task_types.items():
            if len(type_tasks) >= 2:
                patterns.append(f"TaskType:{task_type} - {len(type_tasks)} successes")
        
        return patterns
    
    def _extract_optimizations(self, failed_tasks: list[dict]) -> list[str]:
        """从失败任务中提取教训"""
        tips = []
        
        for task in failed_tasks:
            error = task.get("error", "")
            if error:
                tips.append(f"Avoid: {error[:100]}")
        
        return tips
    
    def _evaluate_capabilities(self, tasks: list[dict]) -> dict:
        """评估能力水平"""
        capabilities = defaultdict(lambda: {"success": 0, "total": 0, "avg_quality": 0})
        
        for task in tasks:
            cap = task.get("capability", "general")
            capabilities[cap]["total"] += 1
            if task.get("success"):
                capabilities[cap]["success"] += 1
            capabilities[cap]["avg_quality"] += task.get("quality", 0.5)
        
        # 计算成功率
        result = {}
        for cap, stats in capabilities.items():
            if stats["total"] > 0:
                result[cap] = {
                    "success_rate": stats["success"] / stats["total"],
                    "avg_quality": stats["avg_quality"] / stats["total"]
                }
        
        return result
    
    def _save_snapshot(self, snapshot: ExperienceSnapshot) -> None:
        """保存快照"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO experience_snapshots
            (id, agent_id, timestamp, capabilities, successful_tasks, learned_patterns, optimization_tips)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            snapshot.agent_id,
            snapshot.timestamp,
            json.dumps(snapshot.capabilities),
            json.dumps(snapshot.successful_tasks),
            json.dumps(snapshot.learned_patterns),
            json.dumps(snapshot.optimization_tips)
        ))
        
        conn.commit()
        conn.close()
    
    def create_inheritance(
        self,
        source_agent_id: str,
        target_agent_id: str,
        capability: str,
        snapshot: ExperienceSnapshot,
        inheritance_type: str = "distilled"
    ) -> str:
        """
        创建经验传承
        
        Args:
            source_agent_id: 源 Agent
            target_agent_id: 目标 Agent
            capability: 能力类型
            snapshot: 经验快照
            inheritance_type: 传承类型 (direct, distilled, encoded)
            
        Returns:
            str: 传承 ID
        """
        # 压缩经验
        knowledge_blob = self._compress_snapshot(snapshot)
        
        # 计算置信度
        confidence = self._calculate_inheritance_confidence(snapshot, capability)
        
        inheritance_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO inheritances
            (id, source_agent_id, target_agent_id, capability, knowledge_blob, inheritance_type, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inheritance_id,
            source_agent_id,
            target_agent_id,
            capability,
            knowledge_blob,
            inheritance_type,
            confidence,
            datetime.now().timestamp()
        ))
        
        conn.commit()
        conn.close()
        
        return inheritance_id
    
    def _compress_snapshot(self, snapshot: ExperienceSnapshot) -> str:
        """压缩经验快照"""
        # 简化实现：直接 JSON
        # 实际可以用更复杂的压缩算法
        
        compressed = {
            "caps": snapshot.capabilities,
            "patterns": snapshot.learned_patterns,
            "tips": snapshot.optimization_tips,
            "ts": snapshot.timestamp
        }
        
        return json.dumps(compressed)
    
    def _calculate_inheritance_confidence(
        self,
        snapshot: ExperienceSnapshot,
        capability: str
    ) -> float:
        """计算传承置信度"""
        cap_stats = snapshot.capabilities.get(capability, {})
        
        success_rate = cap_stats.get("success_rate", 0.5)
        avg_quality = cap_stats.get("avg_quality", 0.5)
        
        # 置信度 = 成功率 × 0.7 + 质量 × 0.3
        confidence = success_rate * 0.7 + avg_quality * 0.3
        
        return min(1.0, max(0.0, confidence))
    
    def apply_inheritance(self, inheritance_id: str) -> InheritedExperience | None:
        """应用经验传承"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, source_agent_id, target_agent_id, capability, knowledge_blob,
                   inheritance_type, confidence, created_at
            FROM inheritances
            WHERE id = ?
        """, (inheritance_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # 更新应用时间
        cursor.execute("""
            UPDATE inheritances
            SET applied_at = ?
            WHERE id = ?
        """, (datetime.now().timestamp(), inheritance_id))
        
        conn.commit()
        conn.close()
        
        return InheritedExperience(
            id=row[0],
            source_agent_id=row[1],
            target_agent_id=row[2],
            capability=row[3],
            knowledge_blob=row[4],
            inheritance_type=row[5],
            confidence=row[6],
            applied_at=datetime.now().timestamp()
        )
    
    def get_inherited_knowledge(self, agent_id: str) -> list[dict]:
        """获取 Agent 继承的知识"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, source_agent_id, capability, inheritance_type, confidence,
                   knowledge_blob, applied_at, effectiveness
            FROM inheritances
            WHERE target_agent_id = ?
            ORDER BY applied_at DESC
        """, (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "source": row[1],
                "capability": row[2],
                "type": row[3],
                "confidence": row[4],
                "knowledge": json.loads(row[5]),
                "applied_at": row[6],
                "effectiveness": row[7]
            }
            for row in rows
        ]
    
    def evaluate_inheritance(
        self,
        inheritance_id: str,
        task_success_rate: float,
        efficiency_improvement: float,
        quality_improvement: float
    ) -> None:
        """评估传承效果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 记录评估
        cursor.execute("""
            INSERT INTO inheritance_evaluations
            (id, inheritance_id, task_success_rate, efficiency_improvement, quality_improvement, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            inheritance_id,
            task_success_rate,
            efficiency_improvement,
            quality_improvement,
            datetime.now().timestamp()
        ))
        
        # 更新传承效果
        overall = (task_success_rate + efficiency_improvement + quality_improvement) / 3
        cursor.execute("""
            UPDATE inheritances
            SET effectiveness = ?
            WHERE id = ?
        """, (overall, inheritance_id))
        
        conn.commit()
        conn.close()
    
    def get_best_performing_agents(
        self,
        capability: str = None,
        limit: int = 5
    ) -> list[dict]:
        """获取最佳表现 Agent（用于传承）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if capability:
            cursor.execute("""
                SELECT agent_id, capabilities
                FROM experience_snapshots
                WHERE capabilities LIKE ?
                GROUP BY agent_id
            """, (f"%{capability}%",))
        else:
            cursor.execute("""
                SELECT agent_id, COUNT(*) as snap_count
                FROM experience_snapshots
                GROUP BY agent_id
                ORDER BY snap_count DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"agent_id": row[0], "data": row[1]} for row in rows]
    
    def get_inheritance_chain(self, agent_id: str) -> list[dict]:
        """获取 Agent 的传承链"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取该 Agent 作为源和目标的所有传承
        cursor.execute("""
            SELECT 
                i.id, i.source_agent_id, i.target_agent_id, i.capability, 
                i.inheritance_type, i.confidence, i.effectiveness, i.created_at
            FROM inheritances i
            WHERE i.source_agent_id = ? OR i.target_agent_id = ?
            ORDER BY i.created_at
        """, (agent_id, agent_id))
        
        rows = cursor.fetchall()
        conn.close()
        
        chain = []
        for row in rows:
            role = "source" if row[1] == agent_id else "target"
            chain.append({
                "id": row[0],
                "from": row[1],
                "to": row[2],
                "capability": row[3],
                "type": row[4],
                "confidence": row[5],
                "effectiveness": row[6],
                "created_at": row[7],
                "role": role
            })
        
        return chain
