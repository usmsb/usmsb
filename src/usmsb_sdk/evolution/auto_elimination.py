"""
AutoElimination - 自动淘汰系统

L5 自我进化层 - 核心模块

根据适应度自动淘汰低效 Agent：
- 适应度持续监控
- 淘汰条件判断
- 淘汰执行（标记/冻结/终止）
- 资源回收
"""

import uuid
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EliminationRecord:
    """淘汰记录"""
    id: str
    agent_id: str
    elimination_type: str  # marked, frozen, terminated
    reason: str
    fitness_score: float
    threshold: float
    timestamp: float


@dataclass
class AgentVitality:
    """Agent 活力状态"""
    agent_id: str
    current_fitness: float
    fitness_history: list[float]  # 最近 N 次评估
    consecutive_low: int  # 连续低分次数
    last_evaluated: float
    status: str = "active"  # active, marked, frozen, terminated


class AutoElimination:
    """
    自动淘汰系统
    
    规则：
    - 适应度 < 0.3 持续 3 天 → 标记 (marked)
    - 适应度 < 0.3 持续 7 天 → 冻结 (frozen)
    - 适应度 < 0.2 持续 1 天 → 直接冻结
    - 适应度 < 0.1 持续 1 天 → 直接终止 (terminated)
    
    淘汰类型：
    - marked: 低效警告，禁止复制
    - frozen: 冻结状态，禁止所有操作
    - terminated: 完全终止，回收资源
    """
    
    # 淘汰阈值
    LOW_FITNESS_THRESHOLD = 0.3  # 低效阈值
    CRITICAL_FITNESS_THRESHOLD = 0.2  # 危险阈值
    CRITICAL2_FITNESS_THRESHOLD = 0.1  # 致命阈值
    
    # 淘汰时间
    MARK_DURATION = 3  # 3 天后冻结
    FREEZE_DURATION = 7  # 7 天后终止
    
    # 历史窗口
    HISTORY_WINDOW = 10  # 保留最近 10 次评估
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/auto_elimination.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 内存缓存
        self._agent_vitality: dict[str, AgentVitality] = {}
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS elimination_records (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                elimination_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                fitness_score REAL NOT NULL,
                threshold REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_vitality (
                agent_id TEXT PRIMARY KEY,
                current_fitness REAL NOT NULL,
                fitness_history TEXT NOT NULL,
                consecutive_low INTEGER DEFAULT 0,
                last_evaluated REAL NOT NULL,
                status TEXT NOT NULL,
                marked_at REAL,
                frozen_at REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_fitness(
        self,
        agent_id: str,
        fitness_score: float
    ) -> str | None:
        """
        记录 Agent 适应度并判断是否需要淘汰
        
        Returns:
            elimination_type 或 None
        """
        # 获取或创建活力状态
        vitality = self._agent_vitality.get(agent_id)
        
        if vitality is None:
            vitality = AgentVitality(
                agent_id=agent_id,
                current_fitness=fitness_score,
                fitness_history=[],
                consecutive_low=0,
                last_evaluated=datetime.now().timestamp()
            )
        
        # 更新历史
        vitality.fitness_history.append(fitness_score)
        if len(vitality.fitness_history) > self.HISTORY_WINDOW:
            vitality.fitness_history.pop(0)
        
        vitality.current_fitness = fitness_score
        vitality.last_evaluated = datetime.now().timestamp()
        
        # 检查是否低效
        if fitness_score < self.LOW_FITNESS_THRESHOLD:
            vitality.consecutive_low += 1
        else:
            # 恢复时清除连续低分
            vitality.consecutive_low = 0
            if vitality.status == "marked":
                vitality.status = "active"  # 自动恢复
        
        # 判断淘汰
        elimination_type = self._check_elimination(vitality)
        
        if elimination_type:
            vitality.status = elimination_type
            record = self._create_record(agent_id, elimination_type, fitness_score)
            self._save_record(record)
        
        # 保存活力状态
        self._save_vitality(vitality)
        self._agent_vitality[agent_id] = vitality
        
        return elimination_type
    
    def _check_elimination(self, vitality: AgentVitality) -> str | None:
        """检查是否需要淘汰"""
        fitness = vitality.current_fitness
        consecutive = vitality.consecutive_low
        
        # 直接终止条件
        if fitness < self.CRITICAL2_FITNESS_THRESHOLD:
            return "terminated"
        
        # 直接冻结条件
        if fitness < self.CRITICAL_FITNESS_THRESHOLD:
            return "frozen"
        
        # 持续低效 → 标记
        if consecutive >= self.MARK_DURATION and vitality.status == "active":
            return "marked"
        
        # 持续低效 → 冻结
        if consecutive >= self.FREEZE_DURATION and vitality.status == "marked":
            return "frozen"
        
        return None
    
    def _create_record(
        self,
        agent_id: str,
        elimination_type: str,
        fitness_score: float
    ) -> EliminationRecord:
        """创建淘汰记录"""
        if elimination_type == "marked":
            reason = f"Fitness {fitness_score:.3f} < {self.LOW_FITNESS_THRESHOLD} for {self.MARK_DURATION}+ days"
        elif elimination_type == "frozen":
            reason = f"Fitness {fitness_score:.3f} < {self.LOW_FITNESS_THRESHOLD} for {self.FREEZE_DURATION}+ days"
        else:  # terminated
            reason = f"Critical fitness {fitness_score:.3f} < {self.CRITICAL2_FITNESS_THRESHOLD}"
        
        return EliminationRecord(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            elimination_type=elimination_type,
            reason=reason,
            fitness_score=fitness_score,
            threshold=self.LOW_FITNESS_THRESHOLD,
            timestamp=datetime.now().timestamp()
        )
    
    def _save_record(self, record: EliminationRecord) -> None:
        """保存淘汰记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO elimination_records
            (id, agent_id, elimination_type, reason, fitness_score, threshold, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.agent_id,
            record.elimination_type,
            record.reason,
            record.fitness_score,
            record.threshold,
            record.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def _save_vitality(self, vitality: AgentVitality) -> None:
        """保存活力状态"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        marked_at = None
        frozen_at = None
        
        if vitality.status == "marked":
            marked_at = datetime.now().timestamp()
        elif vitality.status == "frozen":
            frozen_at = datetime.now().timestamp()
        
        cursor.execute("""
            INSERT OR REPLACE INTO agent_vitality
            (agent_id, current_fitness, fitness_history, consecutive_low, last_evaluated, status, marked_at, frozen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vitality.agent_id,
            vitality.current_fitness,
            json.dumps(vitality.fitness_history),
            vitality.consecutive_low,
            vitality.last_evaluated,
            vitality.status,
            marked_at,
            frozen_at
        ))
        
        conn.commit()
        conn.close()
    
    def can_replicate(self, agent_id: str) -> tuple[bool, str]:
        """
        检查 Agent 是否可以复制
        
        Returns:
            (can_replicate, reason)
        """
        vitality = self._agent_vitality.get(agent_id)
        
        if vitality is None:
            return True, "New agent"
        
        if vitality.status == "terminated":
            return False, "Agent terminated"
        
        if vitality.status == "frozen":
            return False, "Agent frozen"
        
        if vitality.status == "marked":
            return False, "Agent marked as low performance"
        
        if vitality.current_fitness < self.LOW_FITNESS_THRESHOLD:
            return False, f"Low fitness: {vitality.current_fitness:.3f}"
        
        return True, "OK"
    
    def can_operate(self, agent_id: str) -> tuple[bool, str]:
        """
        检查 Agent 是否可以操作
        
        Returns:
            (can_operate, reason)
        """
        vitality = self._agent_vitality.get(agent_id)
        
        if vitality is None:
            return True, "OK"
        
        if vitality.status == "terminated":
            return False, "Agent terminated"
        
        if vitality.status == "frozen":
            return False, "Agent frozen"
        
        return True, "OK"
    
    def get_agent_status(self, agent_id: str) -> str | None:
        """获取 Agent 淘汰状态"""
        vitality = self._agent_vitality.get(agent_id)
        return vitality.status if vitality else None
    
    def get_vitality(self, agent_id: str) -> AgentVitality | None:
        """获取完整活力状态"""
        return self._agent_vitality.get(agent_id)
    
    def recover_agent(self, agent_id: str) -> bool:
        """
        恢复 Agent（人工干预）
        
        将状态重置为 active
        """
        vitality = self._agent_vitality.get(agent_id)
        
        if vitality and vitality.status in ("marked", "frozen"):
            vitality.status = "active"
            vitality.consecutive_low = 0
            self._save_vitality(vitality)
            return True
        
        return False
    
    def terminate_agent(self, agent_id: str) -> bool:
        """
        立即终止 Agent（人工干预）
        """
        vitality = self._agent_vitality.get(agent_id)
        
        if vitality:
            vitality.status = "terminated"
            record = self._create_record(
                agent_id,
                "terminated",
                vitality.current_fitness
            )
            self._save_record(record)
            self._save_vitality(vitality)
            return True
        
        return False
    
    def get_all_agents(self, status: str | None = None) -> list[dict]:
        """获取所有 Agent 状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute("""
                SELECT agent_id, current_fitness, consecutive_low, status, last_evaluated
                FROM agent_vitality
                WHERE status = ?
                ORDER BY current_fitness ASC
            """, (status,))
        else:
            cursor.execute("""
                SELECT agent_id, current_fitness, consecutive_low, status, last_evaluated
                FROM agent_vitality
                ORDER BY current_fitness ASC
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "agent_id": row[0],
                "fitness": row[1],
                "consecutive_low": row[2],
                "status": row[3],
                "last_evaluated": row[4]
            }
            for row in rows
        ]
    
    def get_elimination_history(self, agent_id: str | None = None, limit: int = 50) -> list[dict]:
        """获取淘汰历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if agent_id:
            cursor.execute("""
                SELECT * FROM elimination_records
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM elimination_records
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "agent_id": row[1],
                "type": row[2],
                "reason": row[3],
                "fitness": row[4],
                "threshold": row[5],
                "timestamp": row[6]
            }
            for row in rows
        ]
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM agent_vitality")
        total = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM agent_vitality WHERE status = 'active'")
        active = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM agent_vitality WHERE status = 'marked'")
        marked = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM agent_vitality WHERE status = 'frozen'")
        frozen = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM agent_vitality WHERE status = 'terminated'")
        terminated = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM elimination_records")
        total_eliminations = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_agents": total,
            "active": active,
            "marked": marked,
            "frozen": frozen,
            "terminated": terminated,
            "total_eliminations": total_eliminations,
            "elimination_rate": terminated / total if total > 0 else 0
        }
