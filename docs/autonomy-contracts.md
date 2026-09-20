# Portable autonomy contracts

The `usmsb_sdk.autonomy` module adds domain-neutral goal acceptance, dependency
plans and asynchronous run states. It reuses `core.elements.Goal`; it neither
chooses goals nor creates obligations for another subject. It does not assert
that a peer's assessment proves a social outcome.

An embedding environment must persist immutable contract versions, bind
assessments to a candidate's content hash, enforce reviewer identity and consent,
and invalidate acceptance after criteria change. A proposed plan is not an
assignment. Goal gaps remain explicit rather than being simulated away.

External execution `accepted` / `running` states require polling the original
opaque `run_ref`. Missing replies after creation are `unknown`, never permission
to create another paid operation. Final output is required for `completed`.

The full SDK currently imports optional platform dependencies eagerly. Lean
services can consume the **same source** through the supported export:

```sh
python scripts/export_autonomy.py /absolute/service/vendor/usmsb
python scripts/export_autonomy.py /absolute/service/vendor/usmsb --check
python -m pytest tests/portable --confcutdir=tests/portable -q
```

The export contains the original core elements, autonomy sources and license,
with LF normalization, lightweight namespace shims, upstream revision and file
SHA256 manifest. Consumers must commit this manifest and verify it in CI. This
is a pinned portable subset, not the full SDK installation; optional autonomous
loops, mock environment collectors and value settlement are not pulled in.

HTTP/JSON participants need not install Python or this subset. Implementations
remain free to use the public contract with another language and runtime.
