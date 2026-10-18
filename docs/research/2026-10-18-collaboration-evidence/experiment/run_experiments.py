"""Deterministic offline falsification study; no SDK imports or network access.

Run from any working directory. --check recomputes every trial and compares
the three generated artifacts without writing. Truth is used only by the
simulator/scorer, except the explicitly oracle-supplied drift-envelope ablation.
"""

import argparse
import hashlib
import json
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

# The Windows bundled/isolated Python does not add the script directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evidence_bounds import Evidence, confidence_box, gain_bounds, wilson_interval

SEED = 20261018
REPEATS = 400
CHECKPOINTS = (32, 128, 512, 2048, 4096)
DELTA = 0.05


@dataclass(frozen=True)
class Case:
    name: str
    historical: tuple[tuple[float, float], ...]
    current: tuple[tuple[float, float], ...]
    weights: tuple[float, float] = (0.5, 0.5)
    old_weights: tuple[float, float] = (0.5, 0.5)
    costs: tuple[float, ...] = (0.0, 0.0)
    missing_failures: bool = False
    adaptive_goal: bool = False
    oracle_drift: bool = False


CASES = (
    Case("stable_gain", ((0.45, 0.45), (0.85, 0.70)),
         ((0.45, 0.45), (0.85, 0.70)), (0.75, 0.25), (0.75, 0.25), (0, 0.05)),
    Case("selective_missing", ((0.6, 0.6), (0.35, 0.35)),
         ((0.6, 0.6), (0.35, 0.35)), missing_failures=True),
    Case("revised_goal", ((0.5, 0.5), (0.9, 0.1), (0.1, 0.9)),
         ((0.5, 0.5), (0.9, 0.1), (0.1, 0.9)),
         (0, 1), (1, 0), (0, 0, 0)),
    Case("stale_environment", ((0.5, 0.5), (0.85, 0.85)),
         ((0.5, 0.5), (0.25, 0.25)), oracle_drift=True),
    Case("small_gain", ((0.5, 0.5), (0.54, 0.54)),
         ((0.5, 0.5), (0.54, 0.54))),
    Case("adaptive_null", ((0.5, 0.5),) * 3, ((0.5, 0.5),) * 3,
         costs=(0, 0, 0), adaptive_goal=True),
)


def choose_completed(evidence, weights, costs):
    scores = []
    for book, cost in zip(evidence, costs):
        means = book.completed_means()
        if any(value is None and w != 0 for value, w in zip(means, weights)):
            scores.append(float("-inf"))
        else:
            scores.append(sum(w * (value or 0) for value, w in zip(means, weights)) - cost)
    # Exact ties retain the earlier index, with the baseline at index zero.
    return max(range(len(scores)), key=scores.__getitem__)


def choose_certificate(boxes, weights, costs):
    lower = [0.0]
    lower.extend(
        gain_bounds(boxes[k], boxes[0], weights, costs[k], costs[0])[0]
        for k in range(1, len(boxes))
    )
    return max(range(len(lower)), key=lower.__getitem__)


def true_gain(case, choice, weights):
    return (
        sum(w * (v - b) for w, v, b in zip(weights, case.current[choice], case.current[0]))
        - case.costs[choice] + case.costs[0]
    )


def misses_truth(boxes, truth):
    return any(
        not lo - 1e-12 <= value <= hi + 1e-12
        for box, means in zip(boxes, truth) for (lo, hi), value in zip(box, means)
    )


def simulate(case, seed):
    rng = random.Random(seed)
    k_count = len(case.historical)
    sums = [[0.0, 0.0] for _ in range(k_count)]
    observed = [[0, 0] for _ in range(k_count)]
    methods = ["baseline_only", "completed_only", "frozen_goal", "vector_certificate"]
    if case.oracle_drift:
        methods.append("drift_envelope")
    first = {name: None for name in methods}
    ever_nonpositive = {name: False for name in methods}
    coverage = {"vector_certificate": False}
    if case.oracle_drift:
        coverage["drift_envelope"] = False
    snapshots = []
    for n in range(1, CHECKPOINTS[-1] + 1):
        for k, means in enumerate(case.historical):
            for j, mean in enumerate(means):
                value = float(rng.random() < mean)
                visible = not (case.missing_failures and k != 0 and value == 0)
                if visible:
                    sums[k][j] += value
                    observed[k][j] += 1
        if n not in CHECKPOINTS:
            continue
        evidence = [
            Evidence(n, tuple(total), tuple(count))
            for total, count in zip(sums, observed)
        ]
        weights = case.weights
        if case.adaptive_goal:
            means = [e.completed_means() for e in evidence]
            dimension = max(
                range(2), key=lambda j: max(means[k][j] - means[0][j] for k in range(1, k_count))
            )
            weights = tuple(float(j == dimension) for j in range(2))
        boxes = [confidence_box(e, k_count, DELTA, (0, 0)) for e in evidence]
        choices = {
            "baseline_only": 0,
            "completed_only": choose_completed(evidence, weights, case.costs),
            "frozen_goal": choose_completed(evidence, case.old_weights, case.costs),
            "vector_certificate": choose_certificate(boxes, weights, case.costs),
        }
        coverage["vector_certificate"] |= misses_truth(boxes, case.current)
        if case.oracle_drift:
            # A declared sensitivity assumption, NOT a drift-learning algorithm.
            drift_boxes = [
                confidence_box(e, k_count, DELTA, (0, 0) if k == 0 else (0.60, 0.60))
                for k, e in enumerate(evidence)
            ]
            choices["drift_envelope"] = choose_certificate(drift_boxes, weights, case.costs)
            coverage["drift_envelope"] |= misses_truth(drift_boxes, case.current)
        for name, choice in choices.items():
            if choice and first[name] is None:
                first[name] = n
            ever_nonpositive[name] |= choice != 0 and true_gain(case, choice, weights) <= 1e-12
        snapshots.append({
            "n_per_candidate": n, "weights": weights, "choices": choices,
            "observed_per_candidate_dimension": [list(e.observed) for e in evidence],
        })
    return {
        "case": case.name,
        "seed": seed,
        "enrollments": k_count * CHECKPOINTS[-1],
        "coverage_failure_any_checkpoint": coverage,
        "snapshots": snapshots,
        "methods": {
            name: {
                "choice": choices[name],
                "gain": round(true_gain(case, choices[name], weights), 12),
                "first_switch_n_per_candidate": first[name],
                "ever_nonpositive_switch": ever_nonpositive[name],
            }
            for name in methods
        },
    }


def summarize(records):
    summary = {}
    for case in CASES:
        rows = [row for row in records if row["case"] == case.name]
        methods = {}
        for name in rows[0]["methods"]:
            outcomes = [row["methods"][name] for row in rows]
            nonpositive = sum(o["choice"] != 0 and o["gain"] <= 0 for o in outcomes)
            first = [o["first_switch_n_per_candidate"] for o in outcomes
                     if o["first_switch_n_per_candidate"] is not None]
            methods[name] = {
                "positive_switches": sum(o["choice"] != 0 and o["gain"] > 0 for o in outcomes),
                "harmful_switches": sum(o["choice"] != 0 and o["gain"] < 0 for o in outcomes),
                "nonpositive_switches": nonpositive,
                "nonpositive_switch_rate_wilson95": wilson_interval(nonpositive, len(rows)),
                "baseline": sum(o["choice"] == 0 for o in outcomes),
                "mean_final_expected_gain": statistics.mean(o["gain"] for o in outcomes),
                "ever_nonpositive_switches": sum(o["ever_nonpositive_switch"] for o in outcomes),
                "median_first_switch_n_conditional_on_switch": statistics.median(first) if first else None,
            }
        summary[case.name] = {
            "repeats": len(rows),
            "enrollments_per_repeat": len(case.historical) * CHECKPOINTS[-1],
            "coverage_failures": {
                name: sum(row["coverage_failure_any_checkpoint"][name] for row in rows)
                for name in rows[0]["coverage_failure_any_checkpoint"]
            },
            "methods": methods,
        }
    return summary


def deterministic_examples():
    n = 4096
    baseline = Evidence(n, (n / 2, 0), (n, 0))
    candidate = Evidence(n, (n * 0.8, 0), (n, 0))
    hidden_interval = gain_bounds(
        confidence_box(candidate, 2, DELTA, (0, 0)),
        confidence_box(baseline, 2, DELTA, (0, 0)), (0, 1),
    )
    audit_rows = []
    base = Evidence(n, (n / 2,), (n,))
    successes = int(n * 0.8)
    failures = n - successes
    for fraction in (0, 0.25, 0.5, 1):
        revealed = int(successes * fraction)
        # Failures were visible; success outcomes are pending until audited.
        e = Evidence(n, (revealed,), (failures + revealed,))
        interval = gain_bounds(
            confidence_box(e, 2, DELTA, (0,)),
            confidence_box(base, 2, DELTA, (0,)), (1,),
        )
        audit_rows.append({
            "pending_revealed_fraction": fraction,
            "extra_observations": revealed,
            "completion_interval_width": e.completion_box()[0][1] - e.completion_box()[0][0],
            "gain_interval": interval,
            "certificate": interval[0] > 0,
        })
    return {
        "unmeasured_new_goal": {
            "same_observed_statistics_in_both_worlds": True,
            "world_negative_gain": -0.4, "world_positive_gain": 0.4,
            "new_goal_gain_interval": hidden_interval,
        },
        "reveal_pending_results": audit_rows,
        "audit_assumptions": "Deterministic example, always successful free observation; not an economic value experiment.",
    }


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def render_report(summary):
    lines = [
        "# 合成实验结果（自动生成）", "",
        "生成器：experiment/run_experiments.py。不是 AI 行为、商业收益或原创性证明。", "",
        f"固定种子 {SEED}；每场景 {REPEATS} 次重复；每臂 {CHECKPOINTS[-1]} 次登记；"
        f"delta={DELTA}；检查点 {list(CHECKPOINTS)}。", "",
        "每种方法使用同一批模拟样本。表中的期望增益由模拟真值评分，未扣除学习样本与观测成本；"
        "不能据此计算实际 ROI。错误包括选择零增益候选；严格负增益另列。", "",
        "| 场景 | 方法 | 正增益切换 | 严格负增益切换 | 非正增益切换 | 留在基线 | 平均最终期望增益 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, case in summary["cases"].items():
        for method, row in case["methods"].items():
            lines.append(
                f"| {name} | {method} | {row['positive_switches']} | {row['harmful_switches']} "
                f"| {row['nonpositive_switches']} | {row['baseline']} "
                f"| {row['mean_final_expected_gain']:.4f} |"
            )
    lines += [
        "", "## 覆盖与多次查看", "",
        "| 场景 | 证据方法 | 任一检查点覆盖失败次数 / 400 |",
        "| --- | --- | ---: |",
    ]
    for name, case in summary["cases"].items():
        for method, count in case["coverage_failures"].items():
            lines.append(f"| {name} | {method} | {count} |")
    upper = wilson_interval(0, REPEATS)[1]
    lines += [
        "", f"0/400 不是错误概率为零：Wilson 95% 区间上端约 {upper:.4%}。"
        "具体频率区间与首次切换统计见 summary.json。每次重复的 0.05 预算不能冒充"
        "全部模拟重复的联合保证。", "",
        "stale_environment 中 vector_certificate 故意使用错误 D=0；"
        "drift_envelope 使用已知的 0.60 包络，它不是自动检测器。", "",
        "## 查明已有试验的待回传结果", "",
        "| 查明比例 | 新观测数 | 未知补全宽度 | 增益下界 | 增益上界 | 有正增益证据 |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in summary["examples"]["reveal_pending_results"]:
        lo, hi = row["gain_interval"]
        lines.append(
            f"| {row['pending_revealed_fraction']:.0%} | {row['extra_observations']} "
            f"| {row['completion_interval_width']:.4f} | {lo:.4f} | {hi:.4f} "
            f"| {row['certificate']} |"
        )
    lines += [
        "", "这里所有补充观测均成功且不收费，是确定性构造。区间缩小不是经济收益，"
        "不能推断现实应无限等待或无限核验。", "",
        "## 从未测量的新目标", "",
        "同一可见记录兼容增益 -0.4 与 +0.4 两个系统，新目标的证据区间为 [-1, 1]。"
        "这是不可识别构造，不是模型跑分。", "",
        "所有逐重复选择、观察数量与检查点保存在 trials.jsonl；"
        "基础代码 SHA-256 与全部汇总保存在 summary.json。", "",
    ]
    return "\n".join(lines)


def build_artifacts():
    records = []
    for case_index, case in enumerate(CASES):
        print(f"Simulating {case.name}: {REPEATS} fixed seeds", flush=True)
        records.extend(
            simulate(case, SEED + 100000 * case_index + repeat)
            for repeat in range(REPEATS)
        )
    here = Path(__file__).resolve().parent
    hashes = {
        name: hashlib.sha256((here / name).read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        for name in ("evidence_bounds.py", "run_experiments.py")
    }
    summary = {
        "study_date": "2026-10-18",
        "evidence_level": "synthetic-only",
        "protocol_commit": "2ccea6a",
        "seed": SEED, "repeats": REPEATS, "delta_per_repeat": DELTA,
        "checkpoints": CHECKPOINTS,
        "source_sha256_lf_normalized": hashes,
        "total_enrollments_random_scenarios": sum(row["enrollments"] for row in records),
        "cases": summarize(records),
        "examples": deterministic_examples(),
    }
    return {
        "summary.json": json_text(summary),
        "trials.jsonl": "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n"
            for row in records
        ),
        "report.md": render_report(summary),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="recompute, compare, do not write")
    args = parser.parse_args()
    artifacts = build_artifacts()
    target = Path(__file__).resolve().parent.parent / "results"
    if args.check:
        mismatches = [
            name for name, content in artifacts.items()
            if not (target / name).exists() or (target / name).read_bytes() != content.encode("utf-8")
        ]
        if mismatches:
            raise SystemExit("Reproduction mismatch: " + ", ".join(mismatches))
        print("PASS: all three result artifacts reproduced byte-for-byte.")
    else:
        target.mkdir(exist_ok=True)
        for name, content in artifacts.items():
            (target / name).write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {len(artifacts)} synthetic result artifacts to {target}")


if __name__ == "__main__":
    main()
