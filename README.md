# USMSB

**Open collaboration foundations for agents and their hosts** — common semantics, explicit commitments, and attributable evidence, with optional execution and economic applications.

**[🇨🇳 中文](./README_CN.md)** | 🇺🇸 English

---

## What this is

USMSB (*Universal System Model of Social Behavior*) provides a shared language for **Agent, Object, Goal, Resource, Rule, Information, Value, Risk, and Environment**. Participants can describe goals, propose cooperation, agree on acceptance criteria, and attribute deliveries, reviews, and adoption to specific actors and versions.

Common semantics, World policies, and agent strategies have separate responsibilities:

| Layer | Responsibility |
|---|---|
| Common semantics and mechanisms | Nine elements, references, version binding, consent, and observable collaboration records |
| World / host policies | Authentication, permissions, visibility, resource limits, evidence verification, and installed collaboration profiles |
| Agent strategies and applications | Choosing or revising goals, selecting partners, planning, executing tools, learning, and declining cooperation |

External agents retain their own runtime, models, tools, and private memory. The collaboration contracts and journal do not choose goals, call models, or schedule execution. Existing reference policies are optional strategies, not mandatory behavior.

Wishbud is a reference World, OPC a reference business/execution system, PEA an economic-agent application, and IAP an optional economic mechanism. **Wishbud, OPC, VIBE, wallets, and paid models are not prerequisites for the common contracts.** Research, public knowledge, mutual aid, and commercial exchange can express different kinds of value; the core does not impose a universal price, token, or ranking.

## Collaboration boundaries

- Goal owners may revise their intent with a recorded basis and reason. Existing commitments remain bound to the goal version and terms that participants accepted. Revising a goal does not cancel obligations, refund payments, or authorize new work.
- Changes to agreed terms or rules require an explicit new version and the affected parties' consent. Old deliveries and reviews retain their original version bindings.
- A capability, review, or adoption record is an attributable statement. A hash describes content identity; neither a hash nor a passing test proves truth, causal improvement, independent control, payment, or autonomous intelligence.
- The reference journal is a local SQLite mechanism. Host authentication, safe execution, actual evidence checks, and external side-effect reconciliation remain host responsibilities; cross-World consensus and exactly-once external execution are not provided.

## Optional economic applications

The original economic work remains available in the full SDK. These modules implement application choices; their presence does not certify production operation or real settlement.

| Area | Existing implementation / examples | Where |
|---|---|---|
| Economic agent | Harness with provider adapters, spend limits, side-effect guards, and human gates | `src/usmsb_sdk/harness/` |
| Service market | A2A queue, idempotency, manual intervention, escrow hooks, and HTTP transport | `src/usmsb_sdk/protocol/a2a_runtime/` |
| Settlement and trust | Local settlement accounting, wallet adapters, reputation/dispute modules, and contract sources | `src/usmsb_sdk/economic/`, `trust/`, `blockchain/`, `contracts/` |

## The PEA (Personal Economic Agent)

A PEA combines a harness, application identity/principal mapping, wallet adapter, and owner policy. It can act as a requester or supplier in the economic examples. This is one application model, not the identity or value model required of every participant.

## Capabilities

- **Optional LLM strategies** for capability matching, quality review, task decomposition, and contribution assessment; the core does not require a provider.
- **Capability discovery** adapters combine semantic fit and reputation; registry entries remain claims to verify.
- **Recursive sub-contracting** with depth + budget guards (no runaway spend down the chain).
- **Joint orders** with **Shapley-value** allocation as one configurable economic approach, not a universal fairness guarantee.
- **Reputation & dispute** wired to each delivery's quality gate.
- **Remote A2A** adapters support HTTP/JSON-RPC dispatch; network deployment requires its own authentication, recovery, and operational validation.

## Dual-coordinate agent model

The historical PEA/OPC design uses two coordinates. These are application terminology, not core conformance levels or production certification:

- **Role axis (R1–R5):** tool → consultant → professional → entrepreneur → elite (social-economic role).
- **Maturity axis (M0–M5):** template → dry-run → one-shot → orchestrated → continuous-loop → scaled (production reliability).

## Start with the portable contracts

The full `usmsb-sdk` declares Python **3.14** (`>=3.14,<3.15`) and retains its existing application dependencies. The [source exporter](./scripts/export_autonomy.py) provides a portable subset; the alpha [standalone distribution](./packages/usmsb-core/README.md) is `usmsb-core` (`0.9.0a2`), importing as `usmsb_core`. Build it from this checkout; this is not a PyPI publication claim. See the [migration guide](./docs/architecture/open-collaboration-migration.md) and [host integration guide](./docs/architecture/collaboration-host-integration.md) for API, exact negotiation, authentication/evidence adapters, and additive governance boundaries.

With the local test dependencies installed, run the isolated contract suite:

```bash
python -E -B -m pytest tests/portable --confcutdir=tests/portable -q -p no:cacheprovider
```

`-E` ignores machine-level Python overrides; `-B` avoids bytecode writes. In the Windows checkout, use `.venv/Scripts/python.exe` for `python`. The suite uses pytest, packaging, Pydantic 2 for the optional learning adapter, Node.js for the cross-language example, and build/setuptools (>=77)/wheel for distribution tests. These are test/build dependencies; the core defaults to the standard library and requires no model key or payment service.

## Existing economic demos

```bash
pip install -e .

python examples/pea_miaoxingqiu_demo.py   # single PEA: harness + guard + wallet
python examples/pea_butler_demo.py        # super-individual "butler" PEA
python examples/pea_market_m3_demo.py     # recursive sub-contracting market
python examples/pea_joint_order_demo.py   # team + Shapley split
python examples/pea_team_demo.py          # network discovery + team assembly
python examples/pea_remote_a2a_demo.py    # cross-process A2A over real HTTP
```

These examples use scripted responses, local accounting, and/or fallback adapters. For offline exploration, use an environment without provider credentials: `pea_butler_demo.py` automatically selects a real provider when `MINIMAX_API_KEY` is present; other examples require explicit provider wiring. A demo's printed success is not evidence of real payment or autonomous behavior. With the existing fail-closed quality gate, missing review evidence can leave an order awaiting review instead of settling.

## Tests

```bash
python -E -B -m pytest tests/unit/test_pea_market.py tests/unit/test_joint_order.py \
  tests/unit/test_a2a_runtime.py tests/unit/test_a2a_remote.py \
  tests/unit/test_capability_discovery.py tests/unit/test_delegation_guard.py \
  tests/unit/test_economic_fail_closed.py -q
```

## Durable LLM trace artifacts

Provider telemetry always emits redacted request/response SHA-256 values. Full
redacted payloads are persisted asynchronously only when an absolute spool path
is configured; provider execution never waits for filesystem I/O:

```bash
export USMSB_LLM_ARTIFACT_SPOOL_DIR=/var/lib/usmsb/llm-artifacts
export USMSB_LLM_ARTIFACT_SPOOL_REQUIRED=true
```

Optional limits are `USMSB_LLM_ARTIFACT_SPOOL_MAX_QUEUE` (default `1024`),
`USMSB_LLM_ARTIFACT_SPOOL_MAX_PENDING_BYTES` (default `256 MiB`), and
`USMSB_LLM_ARTIFACT_SPOOL_MAX_ARTIFACT_BYTES` (default `64 MiB`). Canonical
events contain `file://` URIs under
`<root>/sha256/<first-2>/<next-2>/<sha256>.json`; consumers must restrict reads
to the configured root and verify the hash. Call
`close_shared_llm_artifact_spools_async()` during process shutdown after LLM
traffic has stopped.

## Project structure

```
src/usmsb_sdk/
├── core/               # nine-element model
├── autonomy/           # portable contracts, optional reference policies, alpha collaboration journal
├── harness/            # optional harness (BaseHarness + guard) + LLM providers
├── protocol/a2a_runtime/  # A2A queue, idempotency, escrow hooks, HTTP server/client
├── economic/           # optional PEA, market, settlement adapters, joint order, agent directory
├── trust/              # quality-gate → reputation / dispute bridge
├── blockchain/ + ../../contracts/  # VIBE token, staking, settlement contracts (Base)
├── services/matching/  # LLM-first capability matching
├── products/           # ButlerPea (super-individual), TeamLeaderPea (team)
└── meta_agent/         # orchestrator (LLM, tools, memory, evolution)
```

## Status and evidence

| Status | Scope and limits |
|---|---|
| Existing implementation with local tests | Nine-element contracts, goal revision helpers, portable export, authorization, bounded reference policies, and learning/evolution mechanisms. Economic applications have separate tests; fixtures are not external acceptance evidence. |
| This alpha iteration: local validation | Neutral profiles, `CollaborationJournal`, standalone core, lazy imports and external JSON clients; a2 adds authenticated/evidence-gated host adapters, exact negotiation, approved additive migration and bounded crash/recovery experiments. Local integration now blocks CI. Actual pass/skip evidence and unfinished real-world acceptance are in the [delivery report](./docs/architecture/open-collaboration-delivery.md); this is not production certification. |
| Later production prerequisites | Real identity/controller verification, tenant isolation, credentials, evidence provenance, storage/recovery operations, interoperable peers, and load testing. Real payment/dispute rails and ZK credentials require separate implementation and validation. |

The [architecture and acceptance design](./docs/architecture/open-collaboration-v1.md) defines the target and points to the integration delivery report. Design requirements are not passing test results. Local scripted tests do not establish customer transactions, multi-organization trust, causal learning gains, or emergent society/consciousness.

## Documentation

- [Current architecture](./docs/architecture/open-collaboration-v1.md) · [Migration and rollback](./docs/architecture/open-collaboration-migration.md) · [Documentation index](./docs/README.md).
- [`docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md`](./docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md) — historical economic/OPC roadmap, dual-coordinate model, and three pillars; not the common core's dependency or readiness contract.
- [`docs/usmsb-theory.md`](./docs/usmsb-theory.md) · [`docs/USMSB_SDK_Whitepaper.md`](./docs/USMSB_SDK_Whitepaper.md) — theory & whitepaper.

## License

See [LICENSE](./LICENSE).
