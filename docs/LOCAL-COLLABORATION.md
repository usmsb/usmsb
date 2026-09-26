# Owner-local collaboration reference policy

`autonomy.evolution` provides the private journal and replaceable decision interface. `autonomy.collaboration.CollaborationPolicy` supplies an optional engineering policy, not an empirical USMSB law or a model session. Its input/output types are exported by `scripts/export_autonomy.py`; no model/provider dependencies are needed for the core policy. Optional `autonomy.learning` reuses the existing Harness and needs Pydantic 2.

## Authority and inputs

An owner explicitly grants `execution_scope: owner_authorized_local_programs`, finite `max_requests` / `max_accepts`, allowed provider and requester identity sets, and installed operations. Work profiles link the owner's existing concern to an input artifact, candidate format, verification criterion, verification operation and consumption operation. These are an owner's chosen acceptance constraints, not environment-issued mandates or universal values. There are no built-in Health/software/vendor names.

The embedding host supplies the subject's assessment, visible observations, goals, complete public objects, available capabilities, executions and current review contracts. The reference policy selects among currently available authorized offers; a peer must independently accept requests. Different policies can choose differently or remain inactive. To use an unknown provider, the owner reviews and authorizes its real boundary/identity; adding a provider does not require a domain branch in the SDK.

Decisions remain proposals. The host must explicitly grant the supported effect operations before writing to its signed protocol. A custom policy's output alone cannot grant effects. The journal freezes input, policy version, proposed action, action key and actual acknowledgement; pending acknowledgements replay the same protocol key after restart. Owner policy changes alter the policy version and require explicit state migration.

## Recovery and semantics

- Request and acceptance totals are lifetime journal counts, not restart/day counters or cash balances.
- Unstarted cancelled/declined work may select an available alternative. Failed work pauses by default. Explicitly owner-authorized read-only recovery can choose an alternative or reconsider after a new relevant source version; the same request budget still applies.
- Missing, accepted, leased, uncertain and jointly closed-uncertain execution results never authorize automatic creation replay. The original execution/receipt remains available for reconciliation.
- The reviewer understands exactly one execution-based criterion whose description must equal its own configured criterion. Changed or unsupported criteria are not approved. Passing requires the configured verification result type, an exact `True` pass field, and the frozen candidate id/content hash.
- World still enforces participant independence, membership, frozen acceptance and execution permissions. A signature establishes attribution, not truth.
- Consumption starts only after the current review is accepted. A completed consumption may still record adoption if the original condition became aligned first. A changed acceptance contract stops new reliance on the old review.
- Capability gaps are resolved using actual produced artifacts, not offers alone. Execution, acceptance, adoption, observed impact and goal completion remain distinct. This reference policy does not mark a goal achieved.

## Boundaries still requiring integration

The World host grants effects and executes programs through its existing independent execution host. The policy does not run programs itself, act as an OS sandbox, create model budgets, pay providers, perform clinical review or prove causal improvement. Generic experience invalidation is available in the SDK; a production evidence resolver must attest original receipts before experience promotion. Deterministic fixture policy tests are not proof of model autonomy or society-level effects.

Tests: `python -m pytest -q tests/portable/test_collaboration.py tests/portable/test_evolution.py tests/portable/test_learning.py tests/portable/test_authorization.py tests/portable/test_autonomy.py`.
