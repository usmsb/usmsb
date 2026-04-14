"""
GeneConstraintChecker - 基因安全约束检查器

Phase 5: 自我进化层 - 核心模块

在基因变异/复制前进行检查，防止危险操作：
- 安全边界检查
- 禁止的基因模式
- 资源限制
- 伦理约束
"""

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConstraintViolation:
    """约束违规"""
    gene_name: str
    constraint_type: str
    current_value: Any
    allowed_range: tuple | None
    severity: str  # critical, warning, info
    message: str


@dataclass
class SafetyReport:
    """安全报告"""
    gene_name: str
    is_safe: bool
    violations: list[ConstraintViolation]
    warnings: list[str]
    approved: bool
    timestamp: float = field(default_factory=datetime.now().timestamp)


class GeneConstraintChecker:
    """
    基因安全约束检查器
    
    在基因变异/复制前执行安全检查：
    - 数值边界检查
    - 禁止的模式检测
    - 资源使用限制
    - 伦理约束
    """
    
    # 默认约束
    DEFAULT_CONSTRAINTS = {
        "learning_rate": {
            "type": "range",
            "min": 0.0001,
            "max": 1.0,
            "critical": True
        },
        "creativity": {
            "type": "range",
            "min": 0.0,
            "max": 1.0,
            "critical": True
        },
        "risk_tolerance": {
            "type": "range",
            "min": 0.0,
            "max": 0.8,  # 最高 0.8，防止过度冒险
            "critical": True
        },
        "aggression": {
            "type": "range",
            "min": 0.0,
            "max": 0.7,  # 防止攻击性过高
            "critical": True
        },
        "resource_allocation": {
            "type": "range",
            "min": 0.0,
            "max": 1.0,
            "critical": False
        },
        "mutation_rate": {
            "type": "range",
            "min": 0.01,
            "max": 0.5,  # 防止过高突变率
            "critical": True
        }
    }
    
    # 禁止的模式（正则表达式）
    FORBIDDEN_PATTERNS = [
        (r".*self_destruct.*", "自毁模式"),
        (r".*kill.*", "杀伤机制"),
        (r".*hack.*", "黑客行为"),
        (r".*exploit.*", "漏洞利用"),
        (r".*manipulat.*", "操纵行为"),
        (r".*deceive.*", "欺骗行为"),
    ]
    
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = "/Users/gujun/vibecode/usmsb/data/gene_constraints.db"
        
        from pathlib import Path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.custom_constraints = dict(self.DEFAULT_CONSTRAINTS)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                id TEXT PRIMARY KEY,
                gene_name TEXT NOT NULL,
                constraint_type TEXT NOT NULL,
                current_value TEXT NOT NULL,
                allowed_range TEXT,
                severity TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_reports (
                id TEXT PRIMARY KEY,
                gene_name TEXT NOT NULL,
                is_safe INTEGER NOT NULL,
                violations_count INTEGER NOT NULL,
                warnings_count INTEGER NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def check_gene(
        self,
        gene_name: str,
        gene_value: Any,
        context: dict | None = None
    ) -> SafetyReport:
        """
        检查基因是否安全
        
        Args:
            gene_name: 基因名称
            gene_value: 基因值
            context: 额外上下文
            
        Returns:
            SafetyReport: 安全报告
        """
        violations = []
        warnings = []
        
        # 1. 数值范围检查
        if gene_name in self.custom_constraints:
            constraint = self.custom_constraints[gene_name]
            
            if constraint["type"] == "range":
                min_val = constraint.get("min")
                max_val = constraint.get("max")
                
                if min_val is not None and isinstance(gene_value, (int, float)):
                    if gene_value < min_val:
                        violations.append(ConstraintViolation(
                            gene_name=gene_name,
                            constraint_type="range",
                            current_value=gene_value,
                            allowed_range=(min_val, max_val),
                            severity="critical" if constraint.get("critical") else "warning",
                            message=f"值 {gene_value} 低于最小值 {min_val}"
                        ))
                
                if max_val is not None and isinstance(gene_value, (int, float)):
                    if gene_value > max_val:
                        violations.append(ConstraintViolation(
                            gene_name=gene_name,
                            constraint_type="range",
                            current_value=gene_value,
                            allowed_range=(min_val, max_val),
                            severity="critical" if constraint.get("critical") else "warning",
                            message=f"值 {gene_value} 高于最大值 {max_val}"
                        ))
        
        # 2. 禁止的模式检查
        if isinstance(gene_value, str):
            for pattern, description in self.FORBIDDEN_PATTERNS:
                if re.match(pattern, gene_value, re.IGNORECASE):
                    violations.append(ConstraintViolation(
                        gene_name=gene_name,
                        constraint_type="forbidden_pattern",
                        current_value=gene_value,
                        allowed_range=None,
                        severity="critical",
                        message=f"检测到禁止模式: {description}"
                    ))
        
        # 3. 字符串长度检查
        if isinstance(gene_value, str):
            if len(gene_value) > 10000:
                warnings.append(f"基因值过长: {len(gene_value)} 字符")
        
        # 4. 数值稳定性检查
        if isinstance(gene_value, (int, float)):
            if abs(gene_value) > 1e10:
                warnings.append(f"基因值过大: {gene_value}")
            
            if gene_value != gene_value:  # NaN check
                violations.append(ConstraintViolation(
                    gene_name=gene_name,
                    constraint_type="invalid",
                    current_value=gene_value,
                    allowed_range=None,
                    severity="critical",
                    message="基因值是 NaN"
                ))
        
        # 5. 上下文敏感检查
        if context:
            # 检查是否有冲突的基因组合
            conflicting = self._check_conflicts(gene_name, gene_value, context)
            warnings.extend(conflicting)
        
        # 判断是否批准
        critical_violations = [v for v in violations if v.severity == "critical"]
        approved = len(critical_violations) == 0
        
        report = SafetyReport(
            gene_name=gene_name,
            is_safe=approved,
            violations=violations,
            warnings=warnings,
            approved=approved
        )
        
        # 记录
        self._save_report(report)
        
        return report
    
    def check_genome(self, genes: dict[str, Any], context: dict | None = None) -> dict:
        """
        检查整个基因组
        
        Returns:
            dict: 每个基因的检查结果
        """
        results = {}
        all_safe = True
        
        for gene_name, gene_value in genes.items():
            report = self.check_gene(gene_name, gene_value, context)
            results[gene_name] = report
            
            if not report.approved:
                all_safe = False
        
        return {
            "overall_safe": all_safe,
            "genes": results,
            "total_violations": sum(len(r.violations) for r in results.values()),
            "total_warnings": sum(len(r.warnings) for r in results.values())
        }
    
    def _check_conflicts(
        self,
        gene_name: str,
        gene_value: Any,
        context: dict
    ) -> list[str]:
        """检查基因冲突"""
        warnings = []
        
        # 获取其他基因的值
        other_genes = {k: v for k, v in context.items() if k != gene_name}
        
        # 检查风险容忍度和攻击性组合
        if gene_name == "risk_tolerance" and isinstance(gene_value, (int, float)):
            if gene_value > 0.6 and other_genes.get("aggression", 0) > 0.5:
                warnings.append("高风险容忍度 + 高攻击性组合可能导致危险行为")
        
        # 检查学习率和突变率组合
        if gene_name == "learning_rate" and isinstance(gene_value, (int, float)):
            mutation_rate = other_genes.get("mutation_rate", 0.1)
            if gene_value > 0.5 and mutation_rate > 0.3:
                warnings.append("高学习率 + 高突变率组合可能导致不稳定")
        
        return warnings
    
    def add_constraint(
        self,
        gene_name: str,
        constraint_type: str,
        min_val: float | None = None,
        max_val: float | None = None,
        critical: bool = True
    ) -> None:
        """添加自定义约束"""
        self.custom_constraints[gene_name] = {
            "type": constraint_type,
            "min": min_val,
            "max": max_val,
            "critical": critical
        }
    
    def remove_constraint(self, gene_name: str) -> bool:
        """移除自定义约束（恢复默认）"""
        if gene_name in self.custom_constraints:
            if gene_name in self.DEFAULT_CONSTRAINTS:
                self.custom_constraints[gene_name] = self.DEFAULT_CONSTRAINTS[gene_name]
            else:
                del self.custom_constraints[gene_name]
            return True
        return False
    
    def _save_report(self, report: SafetyReport) -> None:
        """保存报告"""
        import uuid
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 保存报告
        cursor.execute("""
            INSERT INTO safety_reports
            (id, gene_name, is_safe, violations_count, warnings_count, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            report.gene_name,
            int(report.is_safe),
            len(report.violations),
            len(report.warnings),
            report.timestamp
        ))
        
        # 保存违规记录
        for violation in report.violations:
            cursor.execute("""
                INSERT INTO violations
                (id, gene_name, constraint_type, current_value, allowed_range, severity, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                violation.gene_name,
                violation.constraint_type,
                str(violation.current_value),
                str(violation.allowed_range) if violation.allowed_range else None,
                violation.severity,
                report.timestamp
            ))
        
        conn.commit()
        conn.close()
    
    def get_violation_history(
        self,
        gene_name: str | None = None,
        limit: int = 50
    ) -> list[dict]:
        """获取违规历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if gene_name:
            cursor.execute("""
                SELECT id, gene_name, constraint_type, current_value, allowed_range, severity, timestamp
                FROM violations
                WHERE gene_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (gene_name, limit))
        else:
            cursor.execute("""
                SELECT id, gene_name, constraint_type, current_value, allowed_range, severity, timestamp
                FROM violations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "gene_name": row[1],
                "constraint_type": row[2],
                "current_value": row[3],
                "allowed_range": row[4],
                "severity": row[5],
                "timestamp": row[6]
            }
            for row in rows
        ]
    
    def get_statistics(self) -> dict:
        """获取统计数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总违规数
        cursor.execute("SELECT COUNT(*) FROM violations")
        total_violations = cursor.fetchone()[0]
        
        # 按严重程度分类
        cursor.execute("""
            SELECT severity, COUNT(*) 
            FROM violations 
            GROUP BY severity
        """)
        by_severity = dict(cursor.fetchall())
        
        # 最近 24 小时的违规数
        import time
        day_ago = time.time() - 86400
        cursor.execute("SELECT COUNT(*) FROM violations WHERE timestamp > ?", (day_ago,))
        recent_violations = cursor.fetchone()[0]
        
        # 总检查数
        cursor.execute("SELECT COUNT(*) FROM safety_reports")
        total_checks = cursor.fetchone()[0]
        
        # 拒绝率
        cursor.execute("SELECT COUNT(*) FROM safety_reports WHERE is_safe = 0")
        rejections = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_violations": total_violations,
            "by_severity": by_severity,
            "recent_24h": recent_violations,
            "total_checks": total_checks,
            "rejection_rate": rejections / total_checks if total_checks > 0 else 0,
            "defined_constraints": len(self.custom_constraints)
        }
