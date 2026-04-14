"""
EmergenceMonitor - 涌现监控系统

Phase 4: 涌现系统层 - 核心模块

监控和判断系统是否发生了涌现：
- 涌现指标
- 模式检测
- 阈值告警
- 可视化数据
"""

import uuid
import sqlite3
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EmergenceIndicator:
    """涌现指标"""
    name: str
    value: float
    threshold: float
    is_triggered: bool
    confidence: float  # 0-1
    description: str


@dataclass
class EmergenceEvent:
    """涌现事件"""
    id: str
    event_type: str  # pattern_formed, coordination_emerged, collective_behavior
    indicators: list[EmergenceIndicator]
    triggered_at: float
    description: str
    severity: str  # minor, moderate, major, critical


class EmergenceMonitor:
    """
    涌现监控系统
    
    监控多 Agent 系统的涌现现象：
    - 协调涌现检测
    - 模式形成检测
    - 集体行为检测
    - 阈值告警
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/emergence_monitor.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
        
        # 配置阈值
        self.thresholds = {
            "coordination_level": 0.7,      # 协调水平
            "pattern_complexity": 0.6,      # 模式复杂度
            "collective_coherence": 0.65,   # 集体一致性
            "efficiency_gain": 0.3,         # 效率提升
            "novelty": 0.5,                 # 新颖性
        }
        
        # 指标历史（用于趋势分析）
        self.indicator_history: deque = deque(maxlen=1000)
        
        # 当前活跃事件
        self.active_events: list[EmergenceEvent] = []
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergence_events (
                id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL,
                severity TEXT NOT NULL,
                triggered_at REAL NOT NULL,
                resolved_at REAL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                id TEXT PRIMARY KEY,
                event_id TEXT,
                name TEXT NOT NULL,
                value REAL NOT NULL,
                threshold REAL NOT NULL,
                is_triggered INTEGER NOT NULL,
                confidence REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id TEXT PRIMARY KEY,
                metric_type TEXT NOT NULL,
                value REAL NOT NULL,
                agent_count INTEGER,
                timestamp REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_metrics(
        self,
        metric_type: str,
        value: float,
        agent_count: int | None = None
    ) -> None:
        """记录系统指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO system_metrics
            (id, metric_type, value, agent_count, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            metric_type,
            value,
            agent_count,
            datetime.now().timestamp()
        ))
        
        conn.commit()
        conn.close()
    
    def check_emergence(self, system_state: dict[str, Any]) -> list[EmergenceIndicator]:
        """
        检查是否发生涌现
        
        Args:
            system_state: 系统状态，包含：
                - coordination_level: Agent 间协调水平
                - pattern_complexity: 模式复杂度
                - collective_coherence: 集体一致性
                - efficiency_gain: 效率提升（相比个体总和）
                - novelty: 新颖性（与历史行为的差异）
                
        Returns:
            list[EmergenceIndicator]: 触发指标列表
        """
        indicators = []
        
        for metric_name, threshold in self.thresholds.items():
            value = system_state.get(metric_name, 0.0)
            
            # 计算置信度（基于数据质量）
            confidence = min(1.0, system_state.get("sample_size", 10) / 50)
            
            is_triggered = value >= threshold
            
            indicator = EmergenceIndicator(
                name=metric_name,
                value=value,
                threshold=threshold,
                is_triggered=is_triggered,
                confidence=confidence,
                description=self._get_indicator_description(metric_name, value, threshold)
            )
            
            indicators.append(indicator)
            
            # 记录历史
            self.indicator_history.append({
                "name": metric_name,
                "value": value,
                "timestamp": datetime.now().timestamp()
            })
        
        # 检查是否需要触发事件
        triggered = [i for i in indicators if i.is_triggered]
        
        if len(triggered) >= 2:
            # 多个指标触发 = 可能有涌现
            event = self._create_emergence_event(triggered)
            if event:
                self.active_events.append(event)
                self._save_event(event)
        
        return indicators
    
    def _get_indicator_description(
        self,
        metric_name: str,
        value: float,
        threshold: float
    ) -> str:
        """获取指标描述"""
        descriptions = {
            "coordination_level": f"协调水平 {value:.2f} (阈值 {threshold})",
            "pattern_complexity": f"模式复杂度 {value:.2f} (阈值 {threshold})",
            "collective_coherence": f"集体一致性 {value:.2f} (阈值 {threshold})",
            "efficiency_gain": f"效率提升 {value:.2f}x (阈值 {threshold}x)",
            "novelty": f"新颖性 {value:.2f} (阈值 {threshold})",
        }
        return descriptions.get(metric_name, f"{metric_name}={value}")
    
    def _create_emergence_event(
        self,
        indicators: list[EmergenceIndicator]
    ) -> EmergenceEvent | None:
        """创建涌现事件"""
        # 计算严重程度
        triggered_count = len(indicators)
        
        if triggered_count >= 5:
            severity = "critical"
        elif triggered_count >= 4:
            severity = "major"
        elif triggered_count >= 3:
            severity = "moderate"
        else:
            severity = "minor"
        
        # 生成描述
        triggered_names = [i.name for i in indicators]
        description = f"检测到涌现: {', '.join(triggered_names)}"
        
        # 判断类型
        if "coordination_level" in triggered_names and "collective_coherence" in triggered_names:
            event_type = "coordination_emerged"
        elif "pattern_complexity" in triggered_names:
            event_type = "pattern_formed"
        else:
            event_type = "collective_behavior"
        
        return EmergenceEvent(
            id=str(uuid.uuid4()),
            event_type=event_type,
            indicators=indicators,
            triggered_at=datetime.now().timestamp(),
            description=description,
            severity=severity
        )
    
    def _save_event(self, event: EmergenceEvent) -> None:
        """保存事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO emergence_events
            (id, event_type, description, severity, triggered_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            event.id,
            event.event_type,
            event.description,
            event.severity,
            event.triggered_at
        ))
        
        # 保存指标
        for indicator in event.indicators:
            cursor.execute("""
                INSERT INTO indicators
                (id, event_id, name, value, threshold, is_triggered, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                event.id,
                indicator.name,
                indicator.value,
                indicator.threshold,
                int(indicator.is_triggered),
                indicator.confidence,
                event.triggered_at
            ))
        
        conn.commit()
        conn.close()
    
    def resolve_event(self, event_id: str) -> bool:
        """解决事件"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE emergence_events
            SET resolved_at = ?
            WHERE id = ?
        """, (datetime.now().timestamp(), event_id))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if affected > 0:
            self.active_events = [e for e in self.active_events if e.id != event_id]
        
        return affected > 0
    
    def get_active_events(self) -> list[EmergenceEvent]:
        """获取活跃事件"""
        return self.active_events
    
    def get_event_history(
        self,
        limit: int = 50,
        event_type: str | None = None
    ) -> list[dict]:
        """获取事件历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if event_type:
            cursor.execute("""
                SELECT id, event_type, description, severity, triggered_at, resolved_at
                FROM emergence_events
                WHERE event_type = ?
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (event_type, limit))
        else:
            cursor.execute("""
                SELECT id, event_type, description, severity, triggered_at, resolved_at
                FROM emergence_events
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "event_type": row[1],
                "description": row[2],
                "severity": row[3],
                "triggered_at": row[4],
                "resolved_at": row[5]
            }
            for row in rows
        ]
    
    def get_indicator_trend(
        self,
        indicator_name: str,
        window: int = 100
    ) -> dict:
        """获取指标趋势"""
        recent = [
            h for h in self.indicator_history
            if h["name"] == indicator_name
        ][-window:]
        
        if not recent:
            return {"trend": "unknown", "values": []}
        
        values = [h["value"] for h in recent]
        
        # 计算趋势
        if len(values) >= 10:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]
            
            first_avg = sum(first_half) / len(first_half)
            second_avg = sum(second_half) / len(second_half)
            
            if second_avg > first_avg * 1.1:
                trend = "increasing"
            elif second_avg < first_avg * 0.9:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "indicator": indicator_name,
            "trend": trend,
            "values": values,
            "current": values[-1] if values else 0,
            "avg": sum(values) / len(values) if values else 0,
            "std": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def calculate_coordination_level(
        self,
        interactions: list[dict]
    ) -> float:
        """计算协调水平"""
        if not interactions:
            return 0.0
        
        # 协调指标：
        # 1. 交互频率
        frequency = len(interactions) / max(1, len(set(i.get("agent_id") for i in interactions)))
        
        # 2. 交互成功率
        success = sum(1 for i in interactions if i.get("outcome") == "success")
        success_rate = success / len(interactions) if interactions else 0
        
        # 3. 响应时间一致性
        response_times = [i.get("response_time", 0) for i in interactions if "response_time" in i]
        if response_times and len(response_times) > 1:
            cv = statistics.stdev(response_times) / (sum(response_times) / len(response_times))
            consistency = max(0, 1 - cv)
        else:
            consistency = 0.5
        
        # 综合
        coordination = (success_rate * 0.5 + consistency * 0.3 + min(1.0, frequency / 10) * 0.2)
        
        return coordination
    
    def calculate_pattern_complexity(
        self,
        behavior_history: list[dict]
    ) -> float:
        """计算模式复杂度"""
        if len(behavior_history) < 10:
            return 0.0
        
        # 复杂度指标：
        # 1. 行为多样性
        unique_behaviors = len(set(b.get("behavior") for b in behavior_history))
        diversity = unique_behaviors / max(1, len(behavior_history))
        
        # 2. 序列复杂度（重复模式检测）
        sequences = self._detect_sequences(behavior_history)
        sequence_complexity = min(1.0, len(sequences) / 10)
        
        # 3. 层级深度（如果有子团队）
        hierarchy_depth = behavior_history[0].get("hierarchy_depth", 1) if behavior_history else 1
        
        complexity = (
            diversity * 0.4 +
            sequence_complexity * 0.4 +
            min(1.0, hierarchy_depth / 5) * 0.2
        )
        
        return complexity
    
    def _detect_sequences(self, behavior_history: list[dict]) -> list[str]:
        """检测重复序列"""
        if len(behavior_history) < 4:
            return []
        
        sequences = []
        behaviors = [b.get("behavior") for b in behavior_history]
        
        # 检测 2-3 长度的重复序列
        for seq_len in [2, 3]:
            seen = set()
            for i in range(len(behaviors) - seq_len):
                seq = tuple(behaviors[i:i+seq_len])
                if seq in seen:
                    if seq not in sequences:
                        sequences.append(str(seq))
                seen.add(seq)
        
        return sequences
    
    def calculate_efficiency_gain(
        self,
        individual_output: float,
        collective_output: float
    ) -> float:
        """计算效率提升"""
        if individual_output <= 0:
            return 0.0
        
        return collective_output / individual_output
    
    def get_dashboard_data(self) -> dict:
        """获取仪表盘数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 最近事件
        cursor.execute("""
            SELECT COUNT(*) FROM emergence_events
            WHERE triggered_at > ?
        """, (datetime.now().timestamp() - 86400,))
        recent_events = cursor.fetchone()[0]
        
        # 活跃事件
        cursor.execute("""
            SELECT COUNT(*) FROM emergence_events
            WHERE resolved_at IS NULL
        """)
        active_events = cursor.fetchone()[0]
        
        # 指标统计
        cursor.execute("""
            SELECT name, AVG(value), MAX(value), MIN(value)
            FROM indicators
            WHERE timestamp > ?
            GROUP BY name
        """, (datetime.now().timestamp() - 86400,))
        
        indicator_stats = {}
        for name, avg, max_val, min_val in cursor.fetchall():
            indicator_stats[name] = {"avg": avg, "max": max_val, "min": min_val}
        
        conn.close()
        
        return {
            "recent_events_24h": recent_events,
            "active_events": active_events,
            "indicator_stats": indicator_stats,
            "thresholds": self.thresholds,
            "monitor_status": "active"
        }
