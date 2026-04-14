# -*- coding: utf-8 -*-
"""
EvoMap Memory Graph 演示

展示经验图谱和 GDI 评分系统。

运行方式：
    python examples/evomap_memory_graph_demo.py
"""

import sys
sys.path.insert(0, 'src')

print("\n" + "=" * 70)
print("EvoMap Memory Graph - 经验图谱演示")
print("=" * 70)

from usmsb_sdk.evolution.evo_map import MemoryGraph, GDIScorer, ExperienceGeneDB
from usmsb_sdk.evolution.evo_map import GeneRecommendation
import uuid

print("\n[1] MemoryGraph - 经验图谱")
print("-" * 50)

# 创建内存图谱
mg = MemoryGraph()

# 模拟记录经验
print("  记录经验...")

test_cases = [
    ("coding_error", "gene_fix_loop", True, 0.9),
    ("coding_error", "gene_fix_loop", True, 0.85),
    ("coding_error", "gene_fix_class", False, 0.3),
    ("coding_error", "gene_fix_class", False, 0.25),
    ("design_pattern", "gene_apply_singleton", True, 0.8),
    ("design_pattern", "gene_apply_observer", True, 0.75),
    ("optimization", "gene_profile", True, 0.95),
    ("optimization", "gene_cache", True, 0.7),
]

for signal, gene_name, success, score in test_cases:
    mg.record_experience(
        signal=signal,
        gene_id=gene_name + "_" + signal,
        gene_name=gene_name,
        success=success,
        outcome_score=score
    )

print(f"  记录了 {len(test_cases)} 条经验")

# 查询推荐
print("\n[2] 基因推荐")
print("-" * 50)

for signal in ["coding_error", "design_pattern", "optimization"]:
    print(f"\n  信号: '{signal}'")
    
    recs = mg.get_gene_recommendation(signal, limit=5)
    
    if recs:
        for rec in recs:
            ban_status = " [BANNED]" if rec.is_banned else ""
            print(f"    - {rec.gene_name}: score={rec.score:.3f}, "
                  f"success_rate={rec.success_rate:.2%}, attempts={rec.total_attempts}{ban_status}")
    else:
        print(f"    (无数据)")

# 信号统计
print("\n[3] 信号统计")
print("-" * 50)

for signal in ["coding_error", "design_pattern", "optimization"]:
    stats = mg.get_signal_stats(signal)
    print(f"  {signal}:")
    print(f"    总尝试: {stats['total_attempts']}")
    print(f"    总成功: {stats['total_successes']}")
    print(f"    成功率: {stats['overall_success_rate']:.2%}")

# Genetic Drift 测试
print("\n[4] Genetic Drift 探索/利用平衡")
print("-" * 50)

print("  运行 10 次 Genetic Drift 测试 (signal='coding_error'):")
import random
random.seed(42)

shuffle_count = 0
for i in range(10):
    recs = mg.get_gene_recommendation("coding_error", limit=5)
    sorted_recs = sorted(recs, key=lambda x: x.score, reverse=True)
    if [r.gene_id for r in recs] != [r.gene_id for r in sorted_recs]:
        shuffle_count += 1

print(f"  探索触发次数: {shuffle_count}/10")

# GDI 评分
print("\n[5] GDI 评分系统")
print("-" * 50)

gdi = GDIScorer()

test_genes = [
    {"name": "new_gene_0d", "usage": 5, "success": 4, "age": 0},
    {"name": "mid_gene_30d", "usage": 20, "success": 15, "age": 30},
    {"name": "old_gene_90d", "usage": 50, "success": 30, "age": 90},
    {"name": "high_conf_gene", "usage": 30, "success": 28, "age": 15, "confidence": 0.95},
    {"name": "low_conf_gene", "usage": 30, "success": 10, "age": 15, "confidence": 0.3},
]

print("\n  基因 GDI 分数:")
for gene in test_genes:
    gdi_score = gdi.calculate_gdi(
        gene_id=gene["name"],
        confidence=gene.get("confidence", 0.5),
        blast_radius_files=10,
        blast_radius_lines=100,
        usage_count=gene["usage"],
        success_count=gene["success"],
        validator_count=3,
        positive_feedback=2,
        age_days=gene["age"]
    )
    
    intrinsic = gdi._intrinsic_quality_score(gene.get("confidence", 0.5), 10, 100)
    usage = gdi._usage_score(gene["usage"], gene["success"])
    social = gdi._social_score(3, 2)
    freshness = gdi._freshness_score(gene["age"])
    
    print(f"\n  {gene['name']}:")
    print(f"    GDI 总分: {gdi_score:.4f}")
    print(f"    - 内在质量 (35%): {intrinsic:.4f}")
    print(f"    - 使用指标 (30%): {usage:.4f}")
    print(f"    - 社交信号 (20%): {social:.4f}")
    print(f"    - 新鲜度 (15%): {freshness:.4f}")

# Experience Gene DB
print("\n[6] ExperienceGeneDB - 经验基因数据库")
print("-" * 50)

db = ExperienceGeneDB()

from usmsb_sdk.evolution.evo_map import ExperienceGene
from datetime import datetime

gene = ExperienceGene(
    id=str(uuid.uuid4()),
    task_type="coding_error",
    task_keywords=["loop", "infinite", "while"],
    solution_template="while True: ...",
    quality_score=0.85,
    usage_count=10,
    created_at=datetime.now().timestamp(),
    updated_at=datetime.now().timestamp(),
    gene_category="repair",
    trigger_signals=["coding_error", "loop_issue"],
    validation_commands=["pytest", "lint"],
    blast_radius_files=2,
    blast_radius_lines=15,
    confidence=0.8
)

db.save_gene(gene, trigger_signal="coding_error")
print(f"  保存基因: {gene.id[:20]}...")
print(f"  触发信号: {gene.trigger_signals}")

recs = db.get_recommendations("coding_error", limit=5)
print(f"\n  推荐结果:")
for rec in recs[:3]:
    print(f"    - {rec.gene_name}: score={rec.score:.3f}")

gdi_score = db.get_gene_gdi(gene.id)
print(f"\n  GDI 分数: {gdi_score:.4f}")

print("\n" + "=" * 70)
print("EvoMap Memory Graph 演示完成！")
print("=" * 70)
