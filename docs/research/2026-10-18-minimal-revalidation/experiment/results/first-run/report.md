# First prespecified offline run

Seed 20261018; 80 repeats per case/strategy; at most 800 new observations; session delta 0.05.

These are finite-model scripted heuristics, not AI behavior, a new algorithm, HEC, SOTA, or AGI evidence.
Old cost is charged in every trial. Goal-revision prefix cost counts toward the new budget.
No aggregate family-wide claim follows from the per-session delta. Outside-family rows have no coverage guarantee.

A low cost with no correct selection is not success. Wrong/selected is undefined when no action is selected.
All budget failures, structural ambiguities, wrong actions and true-hypothesis exclusions remain in the logs.

| Case | Strategy | Correct / 80 | Wrong / 80 | Undecided | Certified | Mean new cost | Mean total cost |
|---|---|---:|---:|---:|---:|---:|---:|
| irrelevant_nuisance | uniform | 80 | 0 | 0 | 80 | 20.600 | 52.600 |
| irrelevant_nuisance | full_identification | 80 | 0 | 0 | 80 | 26.012 | 58.013 |
| irrelevant_nuisance | decision_greedy | 80 | 0 | 0 | 80 | 3.850 | 35.850 |
| irrelevant_nuisance | hinted_coverage | 80 | 0 | 0 | 80 | 11.662 | 43.663 |
| irrelevant_nuisance | blind_reuse | 38 | 42 | 0 | 0 | 0.000 | 32.000 |
| unknown_changed_location | uniform | 78 | 2 | 0 | 80 | 8.425 | 40.425 |
| unknown_changed_location | full_identification | 78 | 2 | 0 | 80 | 6.112 | 38.112 |
| unknown_changed_location | decision_greedy | 78 | 2 | 0 | 80 | 6.725 | 38.725 |
| unknown_changed_location | hinted_coverage | 78 | 2 | 0 | 80 | 9.963 | 41.962 |
| unknown_changed_location | blind_reuse | 11 | 69 | 0 | 0 | 0.000 | 32.000 |
| unidentifiable_conflict | uniform | 0 | 0 | 80 | 0 | 0.000 | 32.000 |
| unidentifiable_conflict | full_identification | 0 | 0 | 80 | 0 | 0.000 | 32.000 |
| unidentifiable_conflict | decision_greedy | 0 | 0 | 80 | 0 | 0.000 | 32.000 |
| unidentifiable_conflict | hinted_coverage | 0 | 0 | 80 | 0 | 0.000 | 32.000 |
| unidentifiable_conflict | blind_reuse | 42 | 38 | 0 | 0 | 0.000 | 32.000 |
| goal_revision | uniform | 80 | 0 | 0 | 80 | 34.100 | 66.100 |
| goal_revision | full_identification | 80 | 0 | 0 | 80 | 31.675 | 63.675 |
| goal_revision | decision_greedy | 80 | 0 | 0 | 80 | 27.962 | 59.962 |
| goal_revision | hinted_coverage | 80 | 0 | 0 | 80 | 36.800 | 68.800 |
| goal_revision | blind_reuse | 37 | 43 | 0 | 0 | 24.000 | 56.000 |
| misleading_hint | uniform | 80 | 0 | 0 | 80 | 14.925 | 46.925 |
| misleading_hint | full_identification | 80 | 0 | 0 | 80 | 14.625 | 46.625 |
| misleading_hint | decision_greedy | 80 | 0 | 0 | 80 | 4.150 | 36.150 |
| misleading_hint | hinted_coverage | 80 | 0 | 0 | 80 | 18.900 | 50.900 |
| misleading_hint | blind_reuse | 40 | 40 | 0 | 0 | 0.000 | 32.000 |
| restricted_probes | uniform | 0 | 0 | 80 | 0 | 2.375 | 34.375 |
| restricted_probes | full_identification | 0 | 0 | 80 | 0 | 2.375 | 34.375 |
| restricted_probes | decision_greedy | 0 | 0 | 80 | 0 | 2.375 | 34.375 |
| restricted_probes | hinted_coverage | 0 | 0 | 80 | 0 | 2.375 | 34.375 |
| restricted_probes | blind_reuse | 41 | 39 | 0 | 0 | 0.000 | 32.000 |
| outside_family | uniform | 1 | 79 | 0 | 80 | 2.675 | 34.675 |
| outside_family | full_identification | 1 | 79 | 0 | 80 | 2.675 | 34.675 |
| outside_family | decision_greedy | 1 | 79 | 0 | 80 | 2.675 | 34.675 |
| outside_family | hinted_coverage | 1 | 79 | 0 | 80 | 2.675 | 34.675 |
| outside_family | blind_reuse | 80 | 0 | 0 | 0 | 0.000 | 32.000 |
| multiple_correct_actions | uniform | 80 | 0 | 0 | 80 | 2.612 | 34.612 |
| multiple_correct_actions | full_identification | 79 | 1 | 0 | 80 | 3.587 | 35.587 |
| multiple_correct_actions | decision_greedy | 80 | 0 | 0 | 80 | 2.612 | 34.612 |
| multiple_correct_actions | hinted_coverage | 80 | 0 | 0 | 80 | 2.513 | 34.513 |
| multiple_correct_actions | blind_reuse | 48 | 32 | 0 | 0 | 0.000 | 32.000 |
| scope_shift | uniform | 79 | 1 | 0 | 80 | 2.525 | 34.525 |
| scope_shift | full_identification | 79 | 1 | 0 | 80 | 2.525 | 34.525 |
| scope_shift | decision_greedy | 79 | 1 | 0 | 80 | 2.525 | 34.525 |
| scope_shift | hinted_coverage | 79 | 1 | 0 | 80 | 2.525 | 34.525 |
| scope_shift | blind_reuse | 42 | 38 | 0 | 0 | 0.000 | 32.000 |
| weak_signal_budget | uniform | 43 | 1 | 36 | 44 | 640.375 | 672.375 |
| weak_signal_budget | full_identification | 43 | 1 | 36 | 44 | 640.375 | 672.375 |
| weak_signal_budget | decision_greedy | 43 | 1 | 36 | 44 | 640.375 | 672.375 |
| weak_signal_budget | hinted_coverage | 43 | 1 | 36 | 44 | 640.375 | 672.375 |
| weak_signal_budget | blind_reuse | 45 | 35 | 0 | 0 | 0.000 | 32.000 |

## Paired costs against full identification

Differences below use all 80 paired runs, including failures. Conditional costs among both-correct pairs and count differences are in paired.csv.

| Case | Strategy | Mean new cost difference | Correct count difference | Wrong count difference | Undecided count difference |
|---|---|---:|---:|---:|---:|
| irrelevant_nuisance | uniform | -5.412 | 0 | 0 | 0 |
| irrelevant_nuisance | decision_greedy | -22.163 | 0 | 0 | 0 |
| irrelevant_nuisance | hinted_coverage | -14.350 | 0 | 0 | 0 |
| irrelevant_nuisance | blind_reuse | -26.012 | -42 | 42 | 0 |
| unknown_changed_location | uniform | 2.312 | 0 | 0 | 0 |
| unknown_changed_location | decision_greedy | 0.613 | 0 | 0 | 0 |
| unknown_changed_location | hinted_coverage | 3.850 | 0 | 0 | 0 |
| unknown_changed_location | blind_reuse | -6.112 | -67 | 67 | 0 |
| unidentifiable_conflict | uniform | 0.000 | 0 | 0 | 0 |
| unidentifiable_conflict | decision_greedy | 0.000 | 0 | 0 | 0 |
| unidentifiable_conflict | hinted_coverage | 0.000 | 0 | 0 | 0 |
| unidentifiable_conflict | blind_reuse | 0.000 | 42 | 38 | -80 |
| goal_revision | uniform | 2.425 | 0 | 0 | 0 |
| goal_revision | decision_greedy | -3.712 | 0 | 0 | 0 |
| goal_revision | hinted_coverage | 5.125 | 0 | 0 | 0 |
| goal_revision | blind_reuse | -7.675 | -43 | 43 | 0 |
| misleading_hint | uniform | 0.300 | 0 | 0 | 0 |
| misleading_hint | decision_greedy | -10.475 | 0 | 0 | 0 |
| misleading_hint | hinted_coverage | 4.275 | 0 | 0 | 0 |
| misleading_hint | blind_reuse | -14.625 | -40 | 40 | 0 |
| restricted_probes | uniform | 0.000 | 0 | 0 | 0 |
| restricted_probes | decision_greedy | 0.000 | 0 | 0 | 0 |
| restricted_probes | hinted_coverage | 0.000 | 0 | 0 | 0 |
| restricted_probes | blind_reuse | -2.375 | 41 | 39 | -80 |
| outside_family | uniform | 0.000 | 0 | 0 | 0 |
| outside_family | decision_greedy | 0.000 | 0 | 0 | 0 |
| outside_family | hinted_coverage | 0.000 | 0 | 0 | 0 |
| outside_family | blind_reuse | -2.675 | 79 | -79 | 0 |
| multiple_correct_actions | uniform | -0.975 | 1 | -1 | 0 |
| multiple_correct_actions | decision_greedy | -0.975 | 1 | -1 | 0 |
| multiple_correct_actions | hinted_coverage | -1.075 | 1 | -1 | 0 |
| multiple_correct_actions | blind_reuse | -3.587 | -31 | 31 | 0 |
| scope_shift | uniform | 0.000 | 0 | 0 | 0 |
| scope_shift | decision_greedy | 0.000 | 0 | 0 | 0 |
| scope_shift | hinted_coverage | 0.000 | 0 | 0 | 0 |
| scope_shift | blind_reuse | -2.525 | -37 | 37 | 0 |
| weak_signal_budget | uniform | 0.000 | 0 | 0 | 0 |
| weak_signal_budget | decision_greedy | 0.000 | 0 | 0 | 0 |
| weak_signal_budget | hinted_coverage | 0.000 | 0 | 0 | 0 |
| weak_signal_budget | blind_reuse | -640.375 | 2 | 34 | -36 |

## Scope of this evidence

The synthetic evaluator knows truth; the policy API receives only the public family, kernels, action sets, allowlist, hint, and retained hypotheses from past observations.
In-family truth is sampled uniformly with replacement independently for each case/repeat, then shared across strategies. Per-probe streams pair observations without exposing future draws.
The outside-family simulator is deliberately semantically incompatible: its 0.85 observation probability favors h01/a1 while its correct action is a0. Confident errors are not calibrated evidence there.
The structural ambiguity check stops once all retained members have identical allowed kernels; stopping does not certify any action.
Full identification uses the same delta, history, allowlist, maximum budget and decision certificate, and additionally requires a singleton or allowed-probe equivalence class. Its first earlier decision certificate is logged.
Known goal revision only changes supplied action sets; its fixed 24-draw prefix and unchanged likelihoods are logged. No natural-language goal inference or changing model family is tested.
There are no real AI runs, outside effects, monetary bills, deployment, or claims of independently validated user value. Costs are synthetic declared probe costs.
