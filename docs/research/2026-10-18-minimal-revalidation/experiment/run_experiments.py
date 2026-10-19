#!/usr/bin/env python3
"""Offline, dependency-free paired comparisons for fixed finite Bernoulli models.

Default execution preserves the first run. --check recomputes every artifact
and compares bytes without writing results. No SDK package import, network,
model invocation, deployment, or semantic/authorization inference occurs.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SOURCE = REPO / "src/usmsb_sdk/autonomy/revalidation.py"
PROTOCOL = HERE.parent / "01-protocol.md"
SEED = 20261018
REPEATS = 80
MAX_NEW = 800
DELTA = 0.05
OLD_COUNT = 16
SCHEMA = "offline-finite-revalidation-experiment.v1"


def load_source():
    spec = importlib.util.spec_from_file_location("offline_revalidation_source", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sdk = load_source()
from scenarios import SimulatorSpec, cases  # noqa: E402
from strategies import COVERAGE_PERIOD, HINT_PERIOD, STRATEGIES, Policy, PublicScorer  # noqa: E402


def canonical(data, *, pretty=False) -> bytes:
    return (json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       indent=2 if pretty else None,
                       separators=None if pretty else (",", ":")) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stream_seed(*parts) -> int:
    return int.from_bytes(hashlib.sha256(canonical([SEED, *parts])).digest(), "big")


class Environment:
    """Private evaluator. Only draw() results enter evidence; never given to Policy.

    Per-probe streams pair the nth draw across policies, without exposing future
    outcomes. A fresh environment resets the same streams for each strategy.
    """

    def __init__(self, spec: SimulatorSpec, repeat: int):
        self.spec = spec
        self.repeat = repeat
        public = spec.public
        if spec.guarantee_applies:
            index = random.Random(stream_seed(public.case_id, repeat, "truth")).randrange(len(public.hypothesis_ids))
            self.true_id = public.hypothesis_ids[index]
            self.probabilities = public.kernels[index]
            self.acceptable = public.final_actions[index]
        else:
            self.true_id = None
            self.probabilities = spec.outside_probabilities
            self.acceptable = spec.outside_actions
        self.streams = {p: random.Random(stream_seed(public.case_id, repeat, "probe", p))
                        for p in public.probe_ids}
        self.draw_counts = dict.fromkeys(public.probe_ids, 0)
        self.indices = {p: i for i, p in enumerate(public.probe_ids)}

    def draw(self, probe: str):
        index = self.indices[probe]
        self.draw_counts[probe] += 1
        draw = self.draw_counts[probe]
        outcome = int(self.streams[probe].random() < self.probabilities[index])
        ref = f"sim/{self.spec.public.case_id}/{self.repeat:03d}/{probe}/{draw:04d}"
        return sdk.Observation(ref, probe, self.spec.public.scopes[index], outcome, ref)


def run_trial(spec: SimulatorSpec, repeat: int, strategy: str, scorer: PublicScorer) -> dict:
    public = spec.public
    environment = Environment(spec, repeat)
    model = sdk.FiniteModel.from_dict(public.model_dict())
    indices = {p: i for i, p in enumerate(public.probe_ids)}
    max_cost = OLD_COUNT * public.costs[0] + MAX_NEW * max(public.costs[indices[p]] for p in public.allowed_new)
    session = sdk.RevalidationSession(model, delta=DELTA,
                                      allowed_probes={"old_success", *public.allowed_new}, max_cost=max_cost)
    policy = Policy(strategy, scorer)
    trace = []
    costs = dict(old=0.0, revision_prefix=0.0, policy_new=0.0)
    counts = dict(old=0, revision_prefix=0, policy_new=0)
    new_count = 0
    goal_id = "goal_initial" if public.revision_prefix else "goal_final"
    goal = public.goal(final=not public.revision_prefix)
    true_ever_excluded = False
    before_revision = None
    first_decision = None
    last_retained = None
    current_evaluation = None

    def evaluate():
        nonlocal last_retained, current_evaluation
        retained = session.retained_ids
        if retained != last_retained:
            current_evaluation = session.evaluate(goal_id, goal)
            last_retained = retained
        return current_evaluation

    def register(probe: str, stage: str, reason: str):
        nonlocal new_count, true_ever_excluded
        observation = environment.draw(probe)
        prior = session.retained_ids
        if not session.observe(observation):
            raise AssertionError("Simulator produced duplicate evidence")
        if stage != "old":
            new_count += 1
        costs[stage] += public.costs[indices[probe]]
        counts[stage] += 1
        remaining = session.retained_ids
        if environment.true_id is not None and environment.true_id not in remaining:
            true_ever_excluded = True
        trace.append({"event": "observation", "stage": stage, "selection": reason,
                      "receipt": vars(observation), "new_observations": new_count,
                      "registered_cost": session.cost,
                      "eliminated": sorted(set(prior) - set(remaining)),
                      "retained_count": len(remaining)})

    for _ in range(OLD_COUNT):
        register("old_success", "old", "shared_history")
    # History has exactly the same likelihood under all joint hypotheses.
    if session.retained_ids != public.hypothesis_ids:
        raise AssertionError("Equal old kernels must not prune current alternatives")
    after_old = session.evaluate(goal_id, goal)
    for probe in public.revision_prefix:
        register(probe, "revision_prefix", "fixed_common_prefix")
    if public.revision_prefix:
        before_revision = session.evaluate(goal_id, goal)
        retained_before = session.retained_ids
        scores_before = session.log_likelihoods
        goal_id, goal = "goal_revised", public.goal()
        after_revision = session.evaluate(goal_id, goal)
        if session.retained_ids != retained_before or session.log_likelihoods != scores_before:
            raise AssertionError("Goal revision changed evidence")
        trace.append({"event": "goal_revision", "new_observations": new_count,
                      "before": before_revision, "after": after_revision,
                      "evidence_unchanged": True, "log_likelihoods": scores_before})

    def remember_decision(evaluation):
        nonlocal first_decision
        if first_decision is None and evaluation["status"] == "conditional_conclusion":
            first_decision = {"new_observations": new_count,
                              "new_cost": costs["revision_prefix"] + costs["policy_new"],
                              "common_actions": evaluation["common_actions"],
                              "retained_hypotheses": list(session.retained_ids)}

    chosen = None
    if strategy == "blind_reuse":
        remember_decision(evaluate())
        chosen, stop = public.old_action, "blind_reuse_without_certificate"
    else:
        while True:
            evaluation = evaluate()
            remember_decision(evaluation)
            identifiable_done = scorer.indistinguishable(session.retained_ids)
            if evaluation["status"] == "model_conflict":
                stop = "model_conflict"
                break
            if evaluation["status"] == "conditional_conclusion" and (
                    strategy != "full_identification" or identifiable_done):
                chosen = evaluation["common_actions"][0]
                stop = ("identified_singleton" if len(session.retained_ids) == 1 else
                        "identified_equivalence_class") if strategy == "full_identification" else "decision_certificate"
                break
            if identifiable_done:
                stop = "unidentifiable_action_conflict"
                break
            if new_count >= MAX_NEW:
                stop = "max_new_observations"
                break
            probe, reason = policy.choose(session.retained_ids)
            register(probe, "policy_new", reason)

    final = session.evaluate(goal_id, goal)
    new_cost = costs["revision_prefix"] + costs["policy_new"]
    if session.cost != costs["old"] + new_cost or new_count > MAX_NEW:
        raise AssertionError("Cost/observation accounting mismatch")
    selected = chosen is not None
    correct = selected and chosen in environment.acceptable
    certified = selected and strategy != "blind_reuse" and chosen in final["common_actions"]
    # If full identification exhausts its budget with an action certificate,
    # report both facts, but do not pretend it met its stricter stopping rule.
    return {
        "schema": SCHEMA, "case": public.case_id, "repeat": repeat, "strategy": strategy,
        "guarantee_applicable": spec.guarantee_applies,
        "scope_limit": "fixed family and correct kernels only; no semantic or authorization guarantee",
        "truth_evaluator_only": {"hypothesis": environment.true_id,
                                 "probabilities": list(environment.probabilities),
                                 "acceptable_actions": list(environment.acceptable)},
        "delta_session": DELTA, "max_cost": max_cost, "stop_reason": stop,
        "chosen_action": chosen, "action_selected": selected, "correct_selection": bool(correct),
        "wrong_selection": bool(selected and not correct), "certified_selection": bool(certified),
        "wrong_certified_selection": bool(certified and not correct),
        "true_ever_excluded": true_ever_excluded if spec.guarantee_applies else None,
        "new_observations": new_count, "stage_counts": counts, "stage_costs": costs,
        "new_cost": new_cost, "total_cost": session.cost,
        "probe_counts": environment.draw_counts,
        "after_old_evaluation": after_old, "first_final_goal_certificate": first_decision,
        "final_evaluation": final, "final_log_likelihoods": session.log_likelihoods,
        "trace": trace,
    }


def quantile(values, probability):
    values = sorted(values)
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def aggregate(spec: SimulatorSpec, strategy: str, rows: list[dict]) -> dict:
    selected = sum(row["action_selected"] for row in rows)
    wrong = sum(row["wrong_selection"] for row in rows)
    result = {
        "case": spec.public.case_id, "strategy": strategy, "repeats": len(rows),
        "guarantee_applicable": spec.guarantee_applies, "selected": selected,
        "correct_selected": sum(row["correct_selection"] for row in rows), "wrong_selected": wrong,
        "certified_selected": sum(row["certified_selection"] for row in rows),
        "wrong_certified_selected": sum(row["wrong_certified_selection"] for row in rows),
        "certificate_available": sum(row["final_evaluation"]["status"] == "conditional_conclusion" for row in rows),
        "undecided": len(rows) - selected, "selection_rate": selected / len(rows),
        "correct_selection_rate": sum(row["correct_selection"] for row in rows) / len(rows),
        "wrong_selection_rate_all": wrong / len(rows),
        "wrong_selection_rate_selected": wrong / selected if selected else None,
        "true_ever_excluded": sum(row["true_ever_excluded"] for row in rows) if spec.guarantee_applies else None,
        "stop_reasons": dict(sorted(Counter(row["stop_reason"] for row in rows).items())),
    }
    for field in ("new_observations", "new_cost", "total_cost"):
        values = [row[field] for row in rows]
        result[f"mean_{field}"] = statistics.fmean(values)
        result[f"median_{field}"] = statistics.median(values)
        result[f"p90_{field}"] = quantile(values, 0.9)
    result["mean_old_cost"] = statistics.fmean(row["stage_costs"]["old"] for row in rows)
    result["mean_revision_prefix_cost"] = statistics.fmean(row["stage_costs"]["revision_prefix"] for row in rows)
    return result


def run_case(spec: SimulatorSpec, expected_source_hash: str):
    if sha256(SOURCE.read_bytes()) != expected_source_hash:
        raise RuntimeError("SDK source changed during execution; preserve the version before running")
    scorer = PublicScorer(spec.public)
    compressed = io.BytesIO()
    summary, slim = [], {}
    # Empty filename and fixed mtime remove OS/path/time variations from gzip.
    with gzip.GzipFile(fileobj=compressed, mode="wb", filename="", mtime=0, compresslevel=9) as output:
        for strategy in STRATEGIES:
            rows = []
            for repeat in range(REPEATS):
                row = run_trial(spec, repeat, strategy, scorer)
                output.write(canonical(row))
                # Large traces are streamed; summaries keep only trial outcomes.
                rows.append({key: value for key, value in row.items() if key != "trace"})
            summary.append(aggregate(spec, strategy, rows))
            slim[strategy] = rows
    paired = []
    for strategy in STRATEGIES:
        if strategy == "full_identification":
            continue
        reference = slim["full_identification"]
        compared = slim[strategy]
        both_correct = [i for i in range(REPEATS)
                        if reference[i]["correct_selection"] and compared[i]["correct_selection"]]
        paired.append({
            "case": spec.public.case_id, "strategy": strategy, "reference": "full_identification",
            "paired_repeats": REPEATS, "both_correct_count": len(both_correct),
            "mean_new_cost_difference_all": statistics.fmean(
                row["new_cost"] - ref["new_cost"] for row, ref in zip(compared, reference, strict=True)),
            "mean_new_cost_difference_both_correct": statistics.fmean(
                compared[i]["new_cost"] - reference[i]["new_cost"] for i in both_correct) if both_correct else None,
            "correct_selection_count_difference": sum(r["correct_selection"] for r in compared) - sum(r["correct_selection"] for r in reference),
            "wrong_selection_count_difference": sum(r["wrong_selection"] for r in compared) - sum(r["wrong_selection"] for r in reference),
            "undecided_count_difference": sum(not r["action_selected"] for r in compared) - sum(not r["action_selected"] for r in reference),
        })
    return spec.public.case_id, compressed.getvalue(), summary, paired


def csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    fields = list(rows[0])
    writer = csv.DictWriter(output, fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, sort_keys=True, separators=(",", ":"))
                         if isinstance(value, dict) else value for key, value in row.items()})
    return output.getvalue().encode("utf-8")


def render_report(summary: list[dict], paired: list[dict]) -> bytes:
    lines = ["# First prespecified offline run", "",
             f"Seed {SEED}; {REPEATS} repeats per case/strategy; at most {MAX_NEW} new observations; session delta {DELTA}.", "",
             "These are finite-model scripted heuristics, not AI behavior, a new algorithm, HEC, SOTA, or AGI evidence.",
             "Old cost is charged in every trial. Goal-revision prefix cost counts toward the new budget.",
             "No aggregate family-wide claim follows from the per-session delta. Outside-family rows have no coverage guarantee.", "",
             "A low cost with no correct selection is not success. Wrong/selected is undefined when no action is selected.",
             "All budget failures, structural ambiguities, wrong actions and true-hypothesis exclusions remain in the logs.", "",
             "| Case | Strategy | Correct / 80 | Wrong / 80 | Undecided | Certified | Mean new cost | Mean total cost |", 
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in summary:
        lines.append(f"| {row['case']} | {row['strategy']} | {row['correct_selected']} | {row['wrong_selected']} | {row['undecided']} | {row['certified_selected']} | {row['mean_new_cost']:.3f} | {row['mean_total_cost']:.3f} |")
    lines += ["", "## Paired costs against full identification", "",
              "Differences below use all 80 paired runs, including failures. Conditional costs among both-correct pairs and count differences are in paired.csv.", "",
              "| Case | Strategy | Mean new cost difference | Correct count difference | Wrong count difference | Undecided count difference |",
              "|---|---|---:|---:|---:|---:|"]
    for row in paired:
        lines.append(f"| {row['case']} | {row['strategy']} | {row['mean_new_cost_difference_all']:.3f} | {row['correct_selection_count_difference']} | {row['wrong_selection_count_difference']} | {row['undecided_count_difference']} |")
    lines += ["", "## Scope of this evidence", "",
              "The synthetic evaluator knows truth; the policy API receives only the public family, kernels, action sets, allowlist, hint, and retained hypotheses from past observations.",
              "In-family truth is sampled uniformly with replacement independently for each case/repeat, then shared across strategies. Per-probe streams pair observations without exposing future draws.",
              "The outside-family simulator is deliberately semantically incompatible: its 0.85 observation probability favors h01/a1 while its correct action is a0. Confident errors are not calibrated evidence there.",
              "The structural ambiguity check stops once all retained members have identical allowed kernels; stopping does not certify any action.",
              "Full identification uses the same delta, history, allowlist, maximum budget and decision certificate, and additionally requires a singleton or allowed-probe equivalence class. Its first earlier decision certificate is logged.",
              "Known goal revision only changes supplied action sets; its fixed 24-draw prefix and unchanged likelihoods are logged. No natural-language goal inference or changing model family is tested.",
              "There are no real AI runs, outside effects, monetary bills, deployment, or claims of independently validated user value. Costs are synthetic declared probe costs.", ""]
    return "\n".join(lines).encode("utf-8")


def specification() -> dict:
    return {
        "schema": SCHEMA, "seed": SEED, "repeats": REPEATS, "max_new_observations": MAX_NEW,
        "delta_session": DELTA, "old_count": OLD_COUNT, "strategies": list(STRATEGIES),
        "coverage_period": COVERAGE_PERIOD, "forced_hint_period": HINT_PERIOD,
        "truth_sampling": "uniform with replacement per case/repeat; outside_family explicitly overridden",
        "pairing": "SHA256([seed,case,repeat,probe,probe_id]) seeds independent Python Random streams; nth draw shared across strategies",
        "stop": "shared session decision certificate; full also needs singleton/equivalence; blind explicitly bypasses certification",
        "cases": [case.to_dict() for case in cases()],
    }


def source_hashes() -> dict:
    paths = [HERE / name for name in ("run_experiments.py", "scenarios.py", "strategies.py", "test_experiment.py", "README.md")]
    paths.extend((SOURCE, PROTOCOL))
    return {path.relative_to(REPO).as_posix(): sha256(path.read_bytes()) for path in paths}


def build_artifacts(workers: int) -> dict[str, bytes]:
    before = source_hashes()
    sdk_hash = before[SOURCE.relative_to(REPO).as_posix()]
    tasks = cases()
    if workers == 1:
        outputs = [run_case(case, sdk_hash) for case in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            # map preserves declared order independently of completion order.
            outputs = list(pool.map(run_case, tasks, [sdk_hash] * len(tasks)))
    if before != source_hashes():
        raise RuntimeError("An enrolled source changed during execution; no results published")
    artifacts, summary, paired = {}, [], []
    for case_id, compressed, case_summary, case_paired in outputs:
        artifacts[f"trials/{case_id}.jsonl.gz"] = compressed
        summary.extend(case_summary)
        paired.extend(case_paired)
    artifacts["specification.json"] = canonical(specification(), pretty=True)
    artifacts["summary.json"] = canonical(summary, pretty=True)
    artifacts["summary.csv"] = csv_bytes(summary)
    artifacts["paired.csv"] = csv_bytes(paired)
    artifacts["report.md"] = render_report(summary, paired)
    artifacts["manifest.json"] = canonical({
        "schema": SCHEMA, "source_sha256": before,
        "runtime": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                    "zlib": zlib.ZLIB_VERSION, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION},
        "artifact_sha256": {name: sha256(data) for name, data in sorted(artifacts.items())},
        "trials": len(tasks) * len(STRATEGIES) * REPEATS,
        "check": "Re-execute --check with the recorded source/runtime; compare every byte including gzip and manifest.",
    }, pretty=True)
    return artifacts


def compare_artifacts(destination: Path, expected: dict[str, bytes]) -> list[str]:
    actual_names = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()}
    issues = [f"missing:{name}" for name in sorted(set(expected) - actual_names)]
    issues += [f"unexpected:{name}" for name in sorted(actual_names - set(expected))]
    issues += [f"bytes_differ:{name}" for name in sorted(actual_names & set(expected))
               if (destination / name).read_bytes() != expected[name]]
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Recompute and byte-compare; never overwrite results")
    parser.add_argument("--workers", type=int, default=4, help="Independent case processes; has no effect on result bytes")
    parser.add_argument("--results", type=Path, default=HERE / "results" / "first-run",
                        help="Must remain inside experiment/results; existing results are never overwritten")
    args = parser.parse_args()
    if not 1 <= args.workers <= 10:
        parser.error("--workers must be between 1 and 10")
    destination = args.results.resolve()
    if not destination.is_relative_to((HERE / "results").resolve()):
        parser.error("--results must be inside experiment/results")
    if args.check and not destination.is_dir():
        parser.error("--check needs an existing results directory")
    if not args.check and destination.exists() and any(destination.iterdir()):
        parser.error("Results already exist; use --check. A changed experiment needs a new version/directory.")
    artifacts = build_artifacts(args.workers)
    if args.check:
        issues = compare_artifacts(destination, artifacts)
        if issues:
            print(json.dumps({"check": "FAIL", "issues": issues}, sort_keys=True))
            return 1
        print(json.dumps({"check": "PASS", "byte_identical_artifacts": len(artifacts),
                          "trials": len(cases()) * len(STRATEGIES) * REPEATS}, sort_keys=True))
        return 0
    destination.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(artifacts.items()):
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation protects prior evidence even on races or partial runs.
        with path.open("xb") as output:
            output.write(data)
    rows = json.loads(artifacts["summary.json"])
    print(json.dumps({"run": "COMPLETE", "cases": len(cases()), "strategies": len(STRATEGIES),
                      "trials": len(cases()) * len(STRATEGIES) * REPEATS,
                      "artifacts": len(artifacts), "results": str(destination),
                      "undecided": sum(r["undecided"] for r in rows),
                      "wrong_selected": sum(r["wrong_selected"] for r in rows),
                      "note": "Totals include blind reuse and outside-family cases; inspect stratified summary."},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
