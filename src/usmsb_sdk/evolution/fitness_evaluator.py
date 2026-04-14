"""
FitnessEvaluator - 适应度评估器

Phase 5: 自我进化层 - 核心模块

独立适应度评估器，计算 Agent 的多维适应度。
"""

import uuid
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FitnessScore:
    """适应度分数"""
    agent_id: str
    overall_score: float  # 0-1
    value_creation: float = 0.0
    task_success: float = 0.0
    efficiency: float = 0.0
    reputation: float = 0.0
    collaboration: float = 0.0
    learning: float = 0.0
    resource_usage: float = 0.0
    stability: float = 0.0  # 稳定性
    timestamp: float = field(default_factory=datetime.now().timestamp)


@dataclass
class FitnessHistory:
    """适应度历史"""
    agent_id: str
    scores: list[FitnessScore]
    trend: str = "stable"  # improving, declining, stable
    volatility: float = 0.0  # 波动性


class FitnessEvaluator:
    """
    适应度评估器
    
    评估 Agent 在多维空间中的适应度：
    - 价值创造
    - 任务成功率
    - 效率
    - 声誉
    - 协作能力
    - 学习能力
    - 资源使用
    - 稳定性
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/fitness_evaluator.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fitness_scores (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                value_creation REAL NOT NULL,
                task_success REAL NOT NULL,
                efficiency REAL NOT NULL,
                reputation REAL NOT NULL,
                collaboration REAL NOT NULL,
                learning REAL NOT NULL,
                resource_usage REAL NOT NULL,
                stability REAL NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_fitness 
            ON fitness_scores(agent_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    def evaluate(
        self,
        agent_id: str,
        performance_data: dict[str, Any],
        historical_data: dict[str, list[float]] | None = None
    ) -> FitnessScore:
        """
        评估 Agent 适应度
        
        Args:
            agent_id: Agent ID
            performance_data: 性能数据
            historical_data: 历史数据（用于趋势计算）
            
        Returns:
            FitnessScore: 适应度分数
        """
        # 提取各维度分数
        value_creation = self._calc_value_creation(performance_data)
        task_success = self._calc_task_success(performance_data)
        efficiency = self._calc_efficiency(performance_data)
        reputation = self._calc_reputation(performance_data)
        collaboration = self._calc_collaboration(performance_data)
        learning = self._calc_learning(performance_data)
        resource_usage = self._calc_resource_usage(performance_data)
        stability = self._calc_stability(agent_id, historical_data)
        
        # 计算加权总分
        weights = {
            "value_creation": 0.20,
            "task_success": 0.20,
            "efficiency": 0.15,
            "reputation": 0.10,
            "collaboration": 0.10,
            "learning": 0.10,
            "resource_usage": 0.10,
            "stability": 0.05,
        }
        
        overall = (
            value_creation * weights["value_creation"] +
            task_success * weights["task_success"] +
            efficiency * weights["efficiency"] +
            reputation * weights["reputation"] +
            collaboration * weights["collaboration"] +
            learning * weights["learning"] +
            resource_usage * weights["resource_usage"] +
            stability * weights["stability"]
        )
        
        score = FitnessScore(
            agent_id=agent_id,
            overall_score=overall,
            value_creation=value_creation,
            task_success=task_success,
            efficiency=efficiency,
            reputation=reputation,
            collaboration=collaboration,
            learning=learning,
            resource_usage=resource_usage,
            stability=stability
        )
        
        # 保存
        self._save_score(score)
        
        return score
    
    def _calc_value_creation(self, data: dict) -> float:
        """计算价值创造分数"""
        value = data.get("total_value", 0)
        cost = data.get("total_cost", 1)
        
        if cost <= 0:
            cost = 1
        
        roi = (value - cost) / cost
        
        # 归一化到 0-1
        return min(1.0, max(0.0, (roi + 1) / 3))
    
    def _calc_task_success(self, data: dict) -> float:
        """计算任务成功率"""
        total = data.get("total_tasks", 0)
        succeeded = data.get("succeeded_tasks", 0)
        
        if total == 0:
            return 0.5
        
        return succeeded / total
    
    def _calc_efficiency(self, data: dict) -> float:
        """计算效率分数"""
        avg_time = data.get("avg_task_time", 0)
        optimal_time = data.get("optimal_time", 1)
        
        if optimal_time <= 0:
            optimal_time = 1
        
        ratio = optimal_time / avg_time if avg_time > 0 else 1
        
        return min(1.0, ratio)
    
    def _calc_reputation(self, data: dict) -> float:
        """计算声誉分数"""
        positive = data.get("positive_feedback", 0)
        negative = data.get("negative_feedback", 0)
        total = positive + negative
        
        if total == 0:
            return 0.5
        
        return positive / total
    
    def _calc_collaboration(self, data: dict) -> float:
        """计算协作分数"""
        collab_tasks = data.get("collaborative_tasks", 0)
        total = data.get("total_tasks", 1)
        
        if total == 0:
            return 0.0
        
        # 协作任务占比
        ratio = collab_tasks / total
        
        # 协作成功率
        collab_success = data.get("collaborative_success", 0)
        collab_total = data.get("collaborative_total", 1)
        
        success_rate = collab_success / collab_total if collab_total > 0 else 0
        
        return ratio * 0.5 + success_rate * 0.5
    
    def _calc_learning(self, data: dict) -> float:
        """计算学习分数"""
        improvements = data.get("performance_improvements", [])
        
        if not improvements:
            return 0.5
        
        # 平均改进率
        avg_improvement = sum(improvements) / len(improvements)
        
        # 归一化（假设 20% 改进是满分）
        return min(1.0, avg_improvement / 0.2)
    
    def _calc_resource_usage(self, data: dict) -> float:
        """计算资源使用分数"""
        used = data.get("resource_used", 0)
        available = data.get("resource_available", 1)
        
        if available <= 0:
            available = 1
        
        usage_ratio = used / available
        
        # 使用率 70% 是最优
        if usage_ratio < 0.7:
            return usage_ratio / 0.7
        else:
            return max(0, 1 - (usage_ratio - 0.7) / 0.3)
    
    def _calc_stability(
        self,
        agent_id: str,
        historical_data: dict[str, list[float]] | None
    ) -> float:
        """计算稳定性分数"""
        if historical_data is None:
            return 0.5
        
        scores = historical_data.get(agent_id, [])
        
        if len(scores) < 2:
            return 0.5
        
        # 计算变异系数（CV = std/mean）
        import statistics
        mean = statistics.mean(scores)
        
        if mean == 0:
            return 0.5
        
        std = statistics.stdev(scores)
        cv = std / mean
        
        # CV 越小越稳定
        return max(0, 1 - cv)
    
    def _save_score(self, score: FitnessScore) -> None:
        """保存分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fitness_scores
            (id, agent_id, overall_score, value_creation, task_success, efficiency,
             reputation, collaboration, learning, resource_usage, stability, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            score.agent_id,
            score.overall_score,
            score.value_creation,
            score.task_success,
            score.efficiency,
            score.reputation,
            score.collaboration,
            score.learning,
            score.resource_usage,
            score.stability,
            score.timestamp
        ))
        
        conn.commit()
        conn.close()
    
    def get_history(
        self,
        agent_id: str,
        limit: int = 30
    ) -> list[FitnessScore]:
        """获取历史分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM fitness_scores
            WHERE agent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (agent_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            FitnessScore(
                agent_id=row[1],
                overall_score=row[2],
                value_creation=row[3],
                task_success=row[4],
                efficiency=row[5],
                reputation=row[6],
                collaboration=row[7],
                learning=row[8],
                resource_usage=row[9],
                stability=row[10],
                timestamp=row[11]
            )
            for row in rows
        ]
    
    def get_trend(self, agent_id: str, window: int = 10) -> str:
        """获取趋势"""
        scores = self.get_history(agent_id, window)
        
        if len(scores) < 2:
            return "stable"
        
        recent = scores[:len(scores)//2]
        older = scores[len(scores)//2:]
        
        recent_avg = sum(s.overall_score for s in recent) / len(recent)
        older_avg = sum(s.overall_score for s in older) / len(older)
        
        diff = recent_avg - older_avg
        
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"
    
    def rank_agents(self, agent_ids: list[str]) -> list[tuple[str, float]]:
        """排名 Agent"""
        results = []
        
        for agent_id in agent_ids:
            scores = self.get_history(agent_id, limit=1)
            if scores:
                results.append((agent_id, scores[0].overall_score))
            else:
                results.append((agent_id, 0.0))
        
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
