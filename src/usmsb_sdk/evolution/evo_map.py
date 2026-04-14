"""
EvoMap Memory Graph - 经验图谱

借鉴 EvoMap GEP (Genome Evolution Protocol) 的 Memory Graph 思想。

核心功能：
- 记录 (signal → gene → outcome) 历史
- 基于 Laplace 平滑的基因推荐
- 自动 ban 低效基因（2+ attempts 且 value < 0.18）
- Genetic Drift 探索/利用平衡
"""

import uuid
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ============================================================================
# Gene Recommendation - 基因推荐
# ============================================================================

@dataclass
class GeneRecommendation:
    """基因推荐结果"""
    gene_id: str
    gene_name: str
    score: float  # 综合分数
    successes: int  # 成功次数
    total_attempts: int  # 总尝试次数
    success_rate: float
    weighted_value: float  # 加权值
    is_banned: bool = False
    ban_reason: str = ""


class MemoryGraph:
    """
    Append-only 经验图谱
    
    基础公式：
    - p = (successes + 1) / (total + 2)  # Laplace 平滑
    - weight = 0.5 ^ (age_days / half_life_days)
    - value = p * weight
    
    记录 (signal → gene → outcome) 历史，用于指导未来选择。
    """
    
    HALF_LIFE_DAYS = 30  # 半衰期 30 天
    BAN_THRESHOLD = 0.18  # 低于此值 ban
    BAN_MIN_ATTEMPTS = 2  # 至少 2 次尝试才 ban
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/evo_memory_graph.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 经验边表 (signal -> gene -> outcome)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_edges (
                id TEXT PRIMARY KEY,
                signal TEXT NOT NULL,
                gene_id TEXT NOT NULL,
                gene_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                outcome_score REAL NOT NULL,
                timestamp REAL NOT NULL,
                age_days REAL NOT NULL,
                weight REAL NOT NULL,
                value REAL NOT NULL
            )
        """)
        
        # 基因ban记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gene_bans (
                gene_id TEXT PRIMARY KEY,
                signal TEXT NOT NULL,
                ban_reason TEXT NOT NULL,
                ban_timestamp REAL NOT NULL,
                unbanned_at REAL
            )
        """)
        
        # 信号统计表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signal_stats (
                signal TEXT PRIMARY KEY,
                total_attempts INTEGER DEFAULT 0,
                total_successes INTEGER DEFAULT 0
            )
        """)
        
        # 索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_signal_gene 
            ON experience_edges(signal, gene_id)
        """)
        
        conn.commit()
        conn.close()
    
    def record_experience(
        self,
        signal: str,
        gene_id: str,
        gene_name: str,
        success: bool,
        outcome_score: float = 0.5
    ) -> None:
        """
        记录一条经验
        
        Args:
            signal: 触发信号
            gene_id: 基因 ID
            gene_name: 基因名称
            success: 是否成功
            outcome_score: 结果分数 0-1
        """
        now = datetime.now().timestamp()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入经验边
        cursor.execute("""
            INSERT INTO experience_edges
            (id, signal, gene_id, gene_name, success, outcome_score, timestamp, age_days, weight, value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            signal,
            gene_id,
            gene_name,
            int(success),
            outcome_score,
            now,
            0,  # age_days 初始为0
            1.0,  # weight 初始为1
            outcome_score if success else 0
        ))
        
        # 更新信号统计
        cursor.execute("""
            INSERT INTO signal_stats (signal, total_attempts, total_successes)
            VALUES (?, 1, ?)
            ON CONFLICT(signal) DO UPDATE SET
                total_attempts = total_attempts + 1,
                total_successes = total_successes + ?
        """, (signal, int(success), int(success)))
        
        conn.commit()
        conn.close()
        
        # 检查是否需要 ban
        self._check_and_ban(signal, gene_id)
    
    def _check_and_ban(self, signal: str, gene_id: str) -> None:
        """检查并 ban 低效基因"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取该 gene 对该 signal 的统计
        cursor.execute("""
            SELECT 
                COUNT(*) as attempts,
                SUM(success) as successes,
                AVG(outcome_score) as avg_score
            FROM experience_edges
            WHERE signal = ? AND gene_id = ?
        """, (signal, gene_id))
        
        row = cursor.fetchone()
        attempts = row[0] or 0
        successes = row[1] or 0
        avg_score = row[2] or 0
        
        if attempts >= self.BAN_MIN_ATTEMPTS and avg_score < self.BAN_THRESHOLD:
            # Ban 该基因
            cursor.execute("""
                INSERT OR REPLACE INTO gene_bans
                (gene_id, signal, ban_reason, ban_timestamp)
                VALUES (?, ?, ?, ?)
            """, (gene_id, signal, f"avg_score={avg_score:.3f} < {self.BAN_THRESHOLD}", 
                  datetime.now().timestamp()))
            
            print(f"[MemoryGraph] Banned gene {gene_id} for signal '{signal}': {avg_score:.3f} < {self.BAN_THRESHOLD}")
        
        conn.commit()
        conn.close()
    
    def get_gene_recommendation(
        self,
        signal: str,
        limit: int = 10,
        include_banned: bool = False
    ) -> list[GeneRecommendation]:
        """
        查询历史：哪些 gene 对该 signal 效果好
        
        使用 Genetic Drift 平衡探索/利用：
        - 以概率 1/sqrt(gene_count) 随机选择（非最优）
        - gene_count 越小，探索越多
        
        Args:
            signal: 触发信号
            limit: 返回数量
            include_banned: 是否包含已ban基因
            
        Returns:
            list[GeneRecommendation]: 按分数排序的基因推荐
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 聚合统计
        cursor.execute("""
            SELECT 
                gene_id,
                gene_name,
                COUNT(*) as attempts,
                SUM(success) as successes,
                AVG(outcome_score) as avg_score,
                SUM(value) as total_value
            FROM experience_edges
            WHERE signal = ?
            GROUP BY gene_id, gene_name
            ORDER BY total_value DESC
        """, (signal,))
        
        rows = cursor.fetchall()
        
        # 获取 ban 状态
        cursor.execute("""
            SELECT gene_id, ban_reason FROM gene_bans
            WHERE signal = ? AND unbanned_at IS NULL
        """, (signal,))
        
        banned = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        # 构建推荐列表
        recommendations = []
        gene_count = len(rows)
        
        for gene_id, gene_name, attempts, successes, avg_score, total_value in rows:
            is_banned = gene_id in banned
            
            if is_banned and not include_banned:
                continue
            
            # 计算 Laplace 平滑概率
            p = (successes + 1) / (attempts + 2)
            
            # 计算加权值
            weighted_value = p * (0.5 ** (0 / self.HALF_LIFE_DAYS))  # age=0 for now
            
            rec = GeneRecommendation(
                gene_id=gene_id,
                gene_name=gene_name,
                score=total_value or 0,
                successes=successes,
                total_attempts=attempts,
                success_rate=successes / attempts if attempts > 0 else 0,
                weighted_value=weighted_value,
                is_banned=is_banned,
                ban_reason=banned.get(gene_id, "")
            )
            
            recommendations.append(rec)
        
        # 应用 Genetic Drift
        recommendations = self._apply_genetic_drift(recommendations, gene_count)
        
        # 按分数排序
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        return recommendations[:limit]
    
    def _apply_genetic_drift(
        self,
        recommendations: list[GeneRecommendation],
        gene_count: int
    ) -> list[GeneRecommendation]:
        """
        应用 Genetic Drift
        
        以概率 1/sqrt(gene_count) 随机选择（非最优）
        这样基因数量越少，探索越多
        
        Returns:
            list: 可能被随机打乱顺序的列表
        """
        if not recommendations or gene_count == 0:
            return recommendations
        
        # 探索概率
        explore_prob = 1 / math.sqrt(gene_count)
        
        import random
        if random.random() < explore_prob:
            # 探索：随机打乱顺序
            shuffled = recommendations.copy()
            random.shuffle(shuffled)
            return shuffled
        
        return recommendations
    
    def get_signal_stats(self, signal: str) -> dict:
        """获取信号统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_attempts, total_successes
            FROM signal_stats
            WHERE signal = ?
        """, (signal,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "signal": signal,
                "total_attempts": row[0],
                "total_successes": row[1],
                "overall_success_rate": row[1] / row[0] if row[0] > 0 else 0
            }
        
        return {"signal": signal, "total_attempts": 0, "total_successes": 0, "overall_success_rate": 0}
    
    def get_all_signals(self) -> list[str]:
        """获取所有信号"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT signal FROM experience_edges")
        signals = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return signals
    
    def get_gene_history(self, gene_id: str) -> list[dict]:
        """获取基因的历史经验"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT signal, gene_name, success, outcome_score, timestamp
            FROM experience_edges
            WHERE gene_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """, (gene_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "signal": row[0],
                "gene_name": row[1],
                "success": bool(row[2]),
                "outcome_score": row[3],
                "timestamp": row[4]
            }
            for row in rows
        ]
    
    def unbann_gene(self, gene_id: str, signal: str) -> bool:
        """解除基因的 ban"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE gene_bans
            SET unbanned_at = ?
            WHERE gene_id = ? AND signal = ?
        """, (datetime.now().timestamp(), gene_id, signal))
        
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected > 0


# ============================================================================
# GDI Score - Global Desirability Index
# ============================================================================

class GDIScorer:
    """
    GDI 评分体系（Global Desirability Index）
    
    多维质量评分，用于资产排名：
    | 维度 | 权重 | 说明 |
    |------|------|------|
    | 内在质量 | 35% | confidence、validation 通过率、blast_radius |
    | 使用指标 | 30% | 被复用次数、任务完成率 |
    | 社交信号 | 20% | 验证者数量、正向反馈 |
    | 新鲜度 | 15% | 发布时间、更新时间 |
    """
    
    # 权重配置
    WEIGHTS = {
        "intrinsic_quality": 0.35,
        "usage_metrics": 0.30,
        "social_signals": 0.20,
        "freshness": 0.15,
    }
    
    def __init__(self, memory_graph: MemoryGraph | None = None):
        self.memory_graph = memory_graph or MemoryGraph()
    
    def calculate_gdi(
        self,
        gene_id: str,
        confidence: float = 0.5,
        blast_radius_files: int = 0,
        blast_radius_lines: int = 0,
        usage_count: int = 0,
        success_count: int = 0,
        validator_count: int = 0,
        positive_feedback: int = 0,
        age_days: float = 0
    ) -> float:
        """
        计算 GDI 综合分数
        
        Args:
            gene_id: 基因 ID
            confidence: 置信度 0-1
            blast_radius_files: 影响文件数
            blast_radius_lines: 影响代码行数
            usage_count: 被使用次数
            success_count: 成功次数
            validator_count: 验证者数量
            positive_feedback: 正向反馈数
            age_days: 存在天数
            
        Returns:
            float: GDI 分数 0-1
        """
        # 1. 内在质量 (35%)
        intrinsic = self._intrinsic_quality_score(confidence, blast_radius_files, blast_radius_lines)
        
        # 2. 使用指标 (30%)
        usage = self._usage_score(usage_count, success_count)
        
        # 3. 社交信号 (20%)
        social = self._social_score(validator_count, positive_feedback)
        
        # 4. 新鲜度 (15%)
        freshness = self._freshness_score(age_days)
        
        # 加权求和
        gdi = (
            intrinsic * self.WEIGHTS["intrinsic_quality"] +
            usage * self.WEIGHTS["usage_metrics"] +
            social * self.WEIGHTS["social_signals"] +
            freshness * self.WEIGHTS["freshness"]
        )
        
        return min(1.0, max(0.0, gdi))
    
    def _intrinsic_quality_score(
        self,
        confidence: float,
        blast_files: int,
        blast_lines: int
    ) -> float:
        """内在质量分数"""
        # 置信度权重最大
        conf_score = confidence
        
        # blast_radius 越小越好（影响范围小）
        # 归一化：假设 100 文件/1000 行是上限
        blast_score = 1 - min(1.0, (blast_files / 100 + blast_lines / 1000) / 2)
        
        return 0.7 * conf_score + 0.3 * blast_score
    
    def _usage_score(self, usage_count: int, success_count: int) -> float:
        """使用指标分数"""
        if usage_count == 0:
            return 0.3  # 新基因默认中等
        
        success_rate = success_count / usage_count if usage_count > 0 else 0
        
        # 使用次数的对数（边际效益递减）
        usage_score = min(1.0, math.log1p(usage_count) / 10)
        
        return 0.5 * success_rate + 0.5 * usage_score
    
    def _social_score(self, validators: int, positive: int) -> float:
        """社交信号分数"""
        # 验证者越多越好
        validator_score = min(1.0, validators / 10)
        
        # 正向反馈比例
        feedback_score = positive / max(1, validators + positive) if validators > 0 else 0.5
        
        return 0.4 * validator_score + 0.6 * feedback_score
    
    def _freshness_score(self, age_days: float) -> float:
        """新鲜度分数"""
        # 30 天内新鲜度满分，之后线性衰减
        if age_days <= 30:
            return 1.0
        
        # 180 天后最低
        return max(0.1, 1.0 - (age_days - 30) / 150)


# ============================================================================
# Experience Gene DB - 经验基因数据库（增强版）
# ============================================================================

@dataclass
class ExperienceGene:
    """经验基因（EvoMap 增强版）"""
    id: str
    task_type: str
    task_keywords: list[str]
    solution_template: str
    quality_score: float
    usage_count: int
    created_at: float
    updated_at: float
    
    # EvoMap 增强字段
    gene_category: str = "repair"  # repair | optimize | innovate
    trigger_signals: list[str] = field(default_factory=list)
    validation_commands: list[str] = field(default_factory=list)
    blast_radius_files: int = 0
    blast_radius_lines: int = 0
    confidence: float = 0.5
    gene_asset_id: str = ""


class ExperienceGeneDB:
    """
    经验基因数据库（EvoMap 版本）
    
    兼容原有接口，添加 EvoMap 增强字段。
    """
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/experience_genes_evo.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.memory_graph = MemoryGraph(db_path.replace(".db", "_memory.db"))
        self.gdi_scorer = GDIScorer(self.memory_graph)
        
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experience_genes (
                id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                task_keywords TEXT NOT NULL,
                solution_template TEXT NOT NULL,
                quality_score REAL NOT NULL,
                usage_count INTEGER NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                gene_category TEXT DEFAULT 'repair',
                trigger_signals TEXT DEFAULT '[]',
                validation_commands TEXT DEFAULT '[]',
                blast_radius_files INTEGER DEFAULT 0,
                blast_radius_lines INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                gene_asset_id TEXT DEFAULT ''
            )
        """)
        
        # 索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_type ON experience_genes(task_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gene_category ON experience_genes(gene_category)")
        
        conn.commit()
        conn.close()
    
    def save_gene(
        self,
        gene: ExperienceGene,
        trigger_signal: str | None = None
    ) -> bool:
        """保存基因"""
        import json
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO experience_genes
            (id, task_type, task_keywords, solution_template, quality_score, usage_count,
             created_at, updated_at, gene_category, trigger_signals, validation_commands,
             blast_radius_files, blast_radius_lines, confidence, gene_asset_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            gene.id,
            gene.task_type,
            json.dumps(gene.task_keywords),
            gene.solution_template,
            gene.quality_score,
            gene.usage_count,
            gene.created_at,
            gene.updated_at,
            gene.gene_category,
            json.dumps(gene.trigger_signals),
            json.dumps(gene.validation_commands),
            gene.blast_radius_files,
            gene.blast_radius_lines,
            gene.confidence,
            gene.gene_asset_id
        ))
        
        conn.commit()
        conn.close()
        
        # 记录到 Memory Graph
        if trigger_signal:
            self.memory_graph.record_experience(
                signal=trigger_signal,
                gene_id=gene.id,
                gene_name=f"{gene.task_type}:{gene.gene_category}",
                success=gene.quality_score > 0.7,
                outcome_score=gene.quality_score
            )
        
        return True
    
    def get_recommendations(
        self,
        signal: str,
        task_type: str | None = None,
        limit: int = 10
    ) -> list[GeneRecommendation]:
        """获取基因推荐"""
        # 先从 Memory Graph 获取
        return self.memory_graph.get_gene_recommendation(signal, limit)
    
    def get_gene_gdi(self, gene_id: str) -> float:
        """获取基因的 GDI 分数"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT usage_count, quality_score, confidence, blast_radius_files, blast_radius_lines
            FROM experience_genes
            WHERE id = ?
        """, (gene_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return 0.0
        
        usage_count, quality_score, confidence, blast_files, blast_lines = row
        
        return self.gdi_scorer.calculate_gdi(
            gene_id=gene_id,
            confidence=confidence or 0.5,
            blast_radius_files=blast_files or 0,
            blast_radius_lines=blast_lines or 0,
            usage_count=usage_count or 0,
            success_count=int((quality_score or 0) * (usage_count or 1)),
            age_days=(datetime.now().timestamp() - (row[0] if row else 0)) / 86400
        )
