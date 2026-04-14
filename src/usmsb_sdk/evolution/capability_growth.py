"""
CapabilityGrowth - 能力累积系统

Phase 5: 自我进化层 - 核心模块

跟踪和累积 Agent 能力成长：
- 能力图谱
- 学习轨迹
- 能力预测
- 瓶颈识别
"""

import uuid
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CapabilityRecord:
    """能力记录"""
    agent_id: str
    capability: str
    level: float  # 0-1
    experience: int  # 累计经验点
    last_updated: float
    growth_rate: float = 0.0  # 增长速率


@dataclass
class LearningEvent:
    """学习事件"""
    id: str
    agent_id: str
    capability: str
    event_type: str  # practice, teaching, discovery, failure
    xp_gained: int
    quality: float  # 0-1
    timestamp: float


@dataclass
class CapabilityProfile:
    """能力画像"""
    agent_id: str
    capabilities: dict[str, float]  # capability -> level
    strengths: list[str]  # 最强的能力
    weaknesses: list[str]  # 最弱的能力
    growth_potential: float  # 成长潜力
    avg_level: float


class CapabilityGrowth:
    """
    能力累积系统
    
    跟踪 Agent 能力成长：
    - 能力等级（0-1）
    - 经验点累积
    - 成长速率计算
    - 学习事件记录
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/capability_growth.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 配置
        self.xp_per_level = 100  # 多少 XP 升一级
        self.max_level = 1.0
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capability_records (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                level REAL NOT NULL,
                experience INTEGER NOT NULL,
                last_updated REAL NOT NULL,
                growth_rate REAL DEFAULT 0.0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_events (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                capability TEXT NOT NULL,
                event_type TEXT NOT NULL,
                xp_gained INTEGER NOT NULL,
                quality REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_capability 
            ON capability_records(agent_id, capability)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_learning_events
            ON learning_events(agent_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def add_experience(
        self,
        agent_id: str,
        capability: str,
        xp: int,
        quality: float = 0.5,
        event_type: str = "practice"
    ) -> CapabilityRecord:
        """
        添加经验值
        
        Args:
            agent_id: Agent ID
            capability: 能力名称
            xp: 获得的经验值
            quality: 学习质量 0-1
            event_type: 事件类型
            
        Returns:
            CapabilityRecord: 更新后的记录
        """
        # 获取当前记录
        record = self._get_record(agent_id, capability)
        
        if record is None:
            # 创建新记录
            record = CapabilityRecord(
                id=str(uuid.uuid4()),
                agent_id=agent_id,
                capability=capability,
                level=0.0,
                experience=0,
                last_updated=datetime.now().timestamp()
            )
        
        # 添加经验（质量影响）
        effective_xp = int(xp * quality)
        record.experience += effective_xp
        
        # 计算新等级
        old_level = record.level
        record.level = min(self.max_level, record.experience / self.xp_per_level)
        
        # 计算成长速率
        time_delta = datetime.now().timestamp() - record.last_updated
        if time_delta > 0:
            level_delta = record.level - old_level
            record.growth_rate = level_delta / (time_delta / 86400)  # 每天增长率
        
        record.last_updated = datetime.now().timestamp()
        
        # 保存
        self._save_record(record)
        
        # 记录学习事件
        self._record_event(agent_id, capability, event_type, xp, quality)
        
        return record
    
    def _get_record(self, agent_id: str, capability: str) -> CapabilityRecord | None:
        """获取能力记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, agent_id, capability, level, experience, last_updated, growth_rate
            FROM capability_records
            WHERE agent_id = ? AND capability = ?
        """, (agent_id, capability))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return CapabilityRecord(
                id=row[0],
                agent_id=row[1],
                capability=row[2],
                level=row[3],
                experience=row[4],
                last_updated=row[5],
                growth_rate=row[6]
            )
        
        return None
    
    def _save_record(self, record: CapabilityRecord) -> None:
        """保存能力记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO capability_records
            (id, agent_id, capability, level, experience, last_updated, growth_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.agent_id,
            record.capability,
            record.level,
            record.experience,
            record.last_updated,
            record.growth_rate
        ))
        
        conn.commit()
        conn.close()
    
    def _record_event(
        self,
        agent_id: str,
        capability: str,
        event_type: str,
        xp: int,
        quality: float
    ) -> None:
        """记录学习事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO learning_events
            (id, agent_id, capability, event_type, xp_gained, quality, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            agent_id,
            capability,
            event_type,
            xp,
            quality,
            datetime.now().timestamp()
        ))
        
        conn.commit()
        conn.close()
    
    def get_capabilities(self, agent_id: str) -> dict[str, CapabilityRecord]:
        """获取所有能力记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, agent_id, capability, level, experience, last_updated, growth_rate
            FROM capability_records
            WHERE agent_id = ?
            ORDER BY level DESC
        """, (agent_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return {
            row[2]: CapabilityRecord(
                id=row[0],
                agent_id=row[1],
                capability=row[2],
                level=row[3],
                experience=row[4],
                last_updated=row[5],
                growth_rate=row[6]
            )
            for row in rows
        }
    
    def get_profile(self, agent_id: str) -> CapabilityProfile:
        """获取能力画像"""
        caps = self.get_capabilities(agent_id)
        
        if not caps:
            return CapabilityProfile(
                agent_id=agent_id,
                capabilities={},
                strengths=[],
                weaknesses=[],
                growth_potential=0.5,
                avg_level=0.0
            )
        
        levels = list(caps.values())
        
        # 排序
        sorted_caps = sorted(levels, key=lambda x: x.level, reverse=True)
        
        # 最强和最弱
        strengths = [c.capability for c in sorted_caps[:3] if c.level > 0.6]
        weaknesses = [c.capability for c in sorted_caps[-3:] if c.level < 0.4]
        
        # 平均等级
        avg_level = sum(c.level for c in levels) / len(levels)
        
        # 成长潜力（基于平均成长速率）
        avg_growth = sum(c.growth_rate for c in levels) / len(levels)
        growth_potential = min(1.0, avg_growth * 10)
        
        return CapabilityProfile(
            agent_id=agent_id,
            capabilities={c.capability: c.level for c in levels},
            strengths=strengths,
            weaknesses=weaknesses,
            growth_potential=growth_potential,
            avg_level=avg_level
        )
    
    def get_learning_history(
        self,
        agent_id: str,
        capability: str | None = None,
        limit: int = 50
    ) -> list[LearningEvent]:
        """获取学习历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if capability:
            cursor.execute("""
                SELECT id, agent_id, capability, event_type, xp_gained, quality, timestamp
                FROM learning_events
                WHERE agent_id = ? AND capability = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_id, capability, limit))
        else:
            cursor.execute("""
                SELECT id, agent_id, capability, event_type, xp_gained, quality, timestamp
                FROM learning_events
                WHERE agent_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (agent_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            LearningEvent(
                id=row[0],
                agent_id=row[1],
                capability=row[2],
                event_type=row[3],
                xp_gained=row[4],
                quality=row[5],
                timestamp=row[6]
            )
            for row in rows
        ]
    
    def identify_bottlenecks(self, agent_id: str) -> list[dict]:
        """识别能力瓶颈"""
        caps = self.get_capabilities(agent_id)
        
        bottlenecks = []
        
        for cap_name, record in caps.items():
            # 瓶颈条件：
            # 1. 等级低 (< 0.3)
            # 2. 经验高但等级低（学习困难）
            # 3. 成长率低
            
            if record.level < 0.3:
                bottlenecks.append({
                    "capability": cap_name,
                    "reason": "low_level",
                    "level": record.level,
                    "suggestion": f"需要专注于 {cap_name} 的练习"
                })
            
            # 检查学习效率
            if record.experience > 50 and record.level < 0.3:
                bottlenecks.append({
                    "capability": cap_name,
                    "reason": "learning_difficulty",
                    "experience": record.experience,
                    "level": record.level,
                    "suggestion": f"{cap_name} 学习困难，考虑换种方法"
                })
        
        return bottlenecks
    
    def recommend_learning_path(
        self,
        agent_id: str,
        target_capabilities: list[str]
    ) -> list[dict]:
        """推荐学习路径"""
        caps = self.get_capabilities(agent_id)
        
        path = []
        
        for cap in target_capabilities:
            current = caps.get(cap)
            
            if current is None:
                path.append({
                    "capability": cap,
                    "current_level": 0.0,
                    "target_level": 0.8,
                    "xp_needed": int(0.8 * self.xp_per_level),
                    "priority": "high",
                    "reason": "新能力"
                })
            else:
                xp_needed = int((0.8 - current.level) * self.xp_per_level)
                
                if xp_needed > 0:
                    priority = "high" if current.level < 0.3 else "medium"
                    
                    path.append({
                        "capability": cap,
                        "current_level": current.level,
                        "target_level": 0.8,
                        "xp_needed": xp_needed,
                        "priority": priority,
                        "reason": f"当前: {current.level:.2f}, 目标: 0.80"
                    })
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        path.sort(key=lambda x: priority_order[x["priority"]])
        
        return path
    
    def compare_agents(
        self,
        agent_id_a: str,
        agent_id_b: str
    ) -> dict:
        """比较两个 Agent 的能力"""
        caps_a = self.get_capabilities(agent_id_a)
        caps_b = self.get_capabilities(agent_id_b)
        
        all_caps = set(caps_a.keys()) | set(caps_b.keys())
        
        comparison = []
        
        for cap in all_caps:
            level_a = caps_a.get(cap, CapabilityRecord("", "", cap, 0, 0, 0)).level
            level_b = caps_b.get(cap, CapabilityRecord("", "", cap, 0, 0, 0)).level
            
            comparison.append({
                "capability": cap,
                "agent_a_level": level_a,
                "agent_b_level": level_b,
                "difference": level_a - level_b,
                "advantage": "a" if level_a > level_b else "b"
            })
        
        return {
            "agent_a": agent_id_a,
            "agent_b": agent_id_b,
            "comparison": comparison,
            "avg_a": sum(c["agent_a_level"] for c in comparison) / len(comparison) if comparison else 0,
            "avg_b": sum(c["agent_b_level"] for c in comparison) / len(comparison) if comparison else 0
        }
