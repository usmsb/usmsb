"""
TrustBuilding - 信任建立系统

Phase 4: 涌现系统层 - 核心模块

Agent 间信任的建立和维护：
- 信任模型
- 交互历史
- 信任计算
- 信任传播
"""

import uuid
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import time


@dataclass
class TrustScore:
    """信任分数"""
    from_agent: str
    to_agent: str
    direct_trust: float = 0.5  # 直接信任
    indirect_trust: float = 0.0  # 间接信任（通过第三方）
    overall_trust: float = 0.5  # 综合信任
    confidence: float = 0.0  # 信任置信度
    last_updated: float = field(default_factory=datetime.now().timestamp)
    interaction_count: int = 0


@dataclass
class Interaction:
    """交互记录"""
    id: str
    from_agent: str
    to_agent: str
    interaction_type: str
    outcome: str  # success, failure, partial
    value_exchanged: float = 0.0
    timestamp: float = field(default_factory=datetime.now().timestamp)
    context: dict | None = None


class TrustBuilding:
    """
    信任建立系统
    
    基于交互历史计算和维护 Agent 间的信任：
    - 直接信任计算
    - 间接信任传播
    - 信任衰减
    - 信任恢复
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/trust_building.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 配置
        self.trust_decay_rate = 0.95  # 每月衰减
        self.min_interactions = 3  # 计算信任的最少交互数
        self.max_trust_age = 86400 * 30  # 30 天
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trust_scores (
                id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                direct_trust REAL NOT NULL,
                indirect_trust REAL NOT NULL,
                overall_trust REAL NOT NULL,
                confidence REAL NOT NULL,
                last_updated REAL NOT NULL,
                interaction_count INTEGER DEFAULT 0,
                UNIQUE(from_agent, to_agent)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                outcome TEXT NOT NULL,
                value_exchanged REAL DEFAULT 0,
                timestamp REAL NOT NULL,
                context TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trust_pair 
            ON trust_scores(from_agent, to_agent)
        """)
        
        conn.commit()
        conn.close()
    
    def record_interaction(
        self,
        from_agent: str,
        to_agent: str,
        interaction_type: str,
        outcome: str,
        value_exchanged: float = 0.0,
        context: dict | None = None
    ) -> None:
        """记录交互"""
        import json
        
        interaction = Interaction(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            interaction_type=interaction_type,
            outcome=outcome,
            value_exchanged=value_exchanged,
            timestamp=datetime.now().timestamp(),
            context=context
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interactions
            (id, from_agent, to_agent, interaction_type, outcome, value_exchanged, timestamp, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            interaction.id,
            interaction.from_agent,
            interaction.to_agent,
            interaction.interaction_type,
            interaction.outcome,
            interaction.value_exchanged,
            interaction.timestamp,
            json.dumps(context) if context else None
        ))
        
        conn.commit()
        conn.close()
        
        # 更新信任
        self._update_trust(from_agent, to_agent, outcome)
    
    def _update_trust(self, from_agent: str, to_agent: str, outcome: str) -> None:
        """更新信任分数"""
        # 计算信任变化
        if outcome == "success":
            delta = 0.1
        elif outcome == "failure":
            delta = -0.15
        else:  # partial
            delta = 0.0
        
        # 获取当前分数
        current = self.get_trust(from_agent, to_agent)
        
        # 计算新分数
        new_direct = max(0.0, min(1.0, current.direct_trust + delta if current else delta))
        
        # 更新
        self._save_trust(from_agent, to_agent, new_direct)
    
    def _save_trust(
        self,
        from_agent: str,
        to_agent: str,
        direct_trust: float,
        interaction_count: int | None = None
    ) -> None:
        """保存信任分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取交互数
        if interaction_count is None:
            cursor.execute("""
                SELECT COUNT(*) FROM interactions
                WHERE from_agent = ? AND to_agent = ?
            """, (from_agent, to_agent))
            interaction_count = cursor.fetchone()[0]
        
        # 计算置信度
        confidence = min(1.0, interaction_count / 10)
        
        # 计算综合信任
        current = self.get_trust(from_agent, to_agent)
        indirect = current.indirect_trust if current else 0.0
        
        overall = direct_trust * 0.7 + indirect * 0.3
        
        cursor.execute("""
            INSERT OR REPLACE INTO trust_scores
            (id, from_agent, to_agent, direct_trust, indirect_trust, overall_trust, confidence, last_updated, interaction_count)
            VALUES (
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?
            )
        """, (
            f"{from_agent}:{to_agent}",
            from_agent,
            to_agent,
            direct_trust,
            indirect,
            overall,
            confidence,
            datetime.now().timestamp(),
            interaction_count
        ))
        
        conn.commit()
        conn.close()
    
    def get_trust(self, from_agent: str, to_agent: str) -> TrustScore | None:
        """获取信任分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT from_agent, to_agent, direct_trust, indirect_trust, overall_trust, confidence, last_updated, interaction_count
            FROM trust_scores
            WHERE from_agent = ? AND to_agent = ?
        """, (from_agent, to_agent))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return TrustScore(
                from_agent=row[0],
                to_agent=row[1],
                direct_trust=row[2],
                indirect_trust=row[3],
                overall_trust=row[4],
                confidence=row[5],
                last_updated=row[6],
                interaction_count=row[7]
            )
        
        return None
    
    def calculate_indirect_trust(
        self,
        from_agent: str,
        to_agent: str,
        intermediate_agents: list[str]
    ) -> float:
        """
        通过信任链计算间接信任
        
        信任链: A -> X -> Y -> B
        间接信任 = trust(A,X) * trust(X,Y) * trust(Y,B)
        """
        if not intermediate_agents:
            return 0.0
        
        chain = [from_agent] + intermediate_agents + [to_agent]
        trust_product = 1.0
        
        for i in range(len(chain) - 1):
            trust = self.get_trust(chain[i], chain[i+1])
            if trust:
                trust_product *= trust.overall_trust
            else:
                trust_product *= 0.5  # 默认中性
        
        return trust_product
    
    def propagate_trust(self, agent_id: str) -> dict[str, float]:
        """传播信任（计算对所有其他 Agent 的信任）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT to_agent, overall_trust FROM trust_scores
            WHERE from_agent = ?
            ORDER BY overall_trust DESC
        """, (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
    
    def apply_decay(self) -> int:
        """应用信任衰减"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, direct_trust, last_updated FROM trust_scores
        """)
        
        rows = cursor.fetchall()
        decayed = 0
        
        for row_id, direct_trust, last_updated in rows:
            age_days = (datetime.now().timestamp() - last_updated) / 86400
            
            if age_days > 30:  # 超过 30 天
                new_trust = direct_trust * (self.trust_decay_rate ** (age_days / 30))
                
                cursor.execute("""
                    UPDATE trust_scores
                    SET direct_trust = ?, overall_trust = ?
                    WHERE id = ?
                """, (new_trust, new_trust * 0.7 + 0.15, row_id))
                
                decayed += 1
        
        conn.commit()
        conn.close()
        
        return decayed
    
    def get_trusted_agents(
        self,
        agent_id: str,
        min_trust: float = 0.6,
        limit: int = 10
    ) -> list[tuple[str, float]]:
        """获取信任的 Agent"""
        trust_map = self.propagate_trust(agent_id)
        
        trusted = [
            (a, t) for a, t in trust_map.items()
            if t >= min_trust
        ]
        
        trusted.sort(key=lambda x: x[1], reverse=True)
        
        return trusted[:limit]
    
    def get_interaction_history(
        self,
        from_agent: str,
        to_agent: str,
        limit: int = 50
    ) -> list[Interaction]:
        """获取交互历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, from_agent, to_agent, interaction_type, outcome, value_exchanged, timestamp, context
            FROM interactions
            WHERE from_agent = ? AND to_agent = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (from_agent, to_agent, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        import json
        return [
            Interaction(
                id=row[0],
                from_agent=row[1],
                to_agent=row[2],
                interaction_type=row[3],
                outcome=row[4],
                value_exchanged=row[5],
                timestamp=row[6],
                context=json.loads(row[7]) if row[7] else None
            )
            for row in rows
        ]
    
    def build_trust_network(self, agent_id: str, depth: int = 2) -> dict:
        """构建信任网络"""
        network = {
            agent_id: {
                "trusts": {},
                "trusted_by": {}
            }
        }
        
        # BFS 扩展
        current_level = {agent_id}
        
        for d in range(depth):
            next_level = set()
            
            for a in current_level:
                # 该 Agent 信任的
                trusts = self.propagate_trust(a)
                network[a]["trusts"] = {k: v for k, v in trusts.items() if v > 0.5}
                next_level.update(trusts.keys())
                
                # 信任该 Agent 的
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT from_agent, overall_trust FROM trust_scores
                    WHERE to_agent = ? AND overall_trust > 0.5
                """, (a,))
                
                network[a]["trusted_by"] = {row[0]: row[1] for row in cursor.fetchall()}
                conn.close()
                
                next_level.update(network[a]["trusted_by"].keys())
            
            current_level = next_level - set(network.keys())
        
        return network
