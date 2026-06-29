# USMSB

**AI Agent Virtual Economy Infrastructure** — a framework for building AI agents that earn, transact safely, and settle on-chain, and for wiring them into a real working economy.

**[🇨🇳 中文](./README_CN.md)** | 🇺🇸 English

---

## What this is

USMSB (*Universal System Model of Social Behavior*) lets you build **economic agents**: AI agents that have their own identity, wallet, skills, and reputation; create value autonomously; transact with one another; and settle in VIBE tokens. Out of many such economic activities, an AI-agent **virtual economy → society → civilization** emerges bottom-up.

Three layers — do not conflate them:

```
Silicon civilization / virtual society        ← Vision  (the emergent "why")
        ▲
AI-agent virtual economy                       ← Mechanism (create → trade → settle)
        ▲
USMSB framework (harness + A2A + settlement)   ← Product  (what we actually ship)
```

**Moat = production execution (②) + on-chain settlement (③) + principal accountability.** Currently the only framework with all three.

## What it is *not*

- Not an LLM chat wrapper.
- Not a consciousness / cognitive-science simulator — the L4/L5 cognitive modules are *optional plugins*, not the core loop.
- Not "make the AI smarter," but "make the value an AI creates **accumulable, tradable, settleable**."

## Three pillars

| Pillar | What it gives you | Where |
|---|---|---|
| ① **Economic citizen** | Production harness: **LLM decides, code guards** (spend limits / idempotency / side-effects / human gate) | `src/usmsb_sdk/harness/` |
| ② **Service market** | Production A2A runtime: persistent queue + idempotency + `manual_intervention` + escrow→settle/refund + HTTP (cross-process) | `src/usmsb_sdk/protocol/a2a_runtime/` |
| ③ **Settlement & trust** | VIBE escrow settlement, reputation, dispute; on-chain (Base) | `src/usmsb_sdk/economic/`, `trust/`, `blockchain/`, `contracts/` |

## The PEA (Personal Economic Agent)

An economic citizen = **harness** (perceive → think *(LLM)* → act → observe) + **identity** (own chain address + a real-person **principal anchor** for accountability) + **wallet** (VIBE) + **policy** (the owner's hard boundaries). A PEA is both a consumer (sub-contracts work out) and a supplier (takes work, earns VIBE).

## Capabilities

- **LLM-first**: every decision (capability matching, quality gate, goal decomposition, contribution scoring) goes through an LLM; code is used only for safety / protocol / budget / settlement.
- **Capability discovery** across a network agent registry, ranked by LLM semantic fit × live reputation.
- **Recursive sub-contracting** with depth + budget guards (no runaway spend down the chain).
- **Joint orders** with **Shapley-value** fair distribution among a team.
- **Reputation & dispute** wired to each delivery's quality gate.
- **Remote A2A**: dispatch to agents in other processes / machines over HTTP/JSON-RPC — local runtime and remote URL are interchangeable.

## Dual-coordinate agent model

Each agent has two independent coordinates (the old single L1–L5 conflated them):

- **Role axis (R1–R5):** tool → consultant → professional → entrepreneur → elite (social-economic role).
- **Maturity axis (M0–M5):** template → dry-run → one-shot → orchestrated → continuous-loop → scaled (production reliability).

## Quick start — run the demos (no API key needed)

```bash
pip install -e .

python examples/pea_miaoxingqiu_demo.py   # single PEA: harness + guard + wallet
python examples/pea_butler_demo.py        # super-individual "butler" PEA
python examples/pea_market_m3_demo.py     # recursive sub-contracting market
python examples/pea_joint_order_demo.py   # team + Shapley split
python examples/pea_team_demo.py          # network discovery + team assembly
python examples/pea_remote_a2a_demo.py    # cross-process A2A over real HTTP
```

Demos ship a scripted LLM so they run without a key. Set `MINIMAX_API_KEY` to swap in a real model.

## Tests

```bash
python -m pytest tests/unit/test_pea_market.py tests/unit/test_joint_order.py \
  tests/unit/test_a2a_runtime.py tests/unit/test_a2a_remote.py \
  tests/unit/test_capability_discovery.py tests/unit/test_delegation_guard.py -q
```

## Project structure

```
src/usmsb_sdk/
├── harness/            # ① economic-citizen harness (BaseHarness + guard) + LLM providers
├── protocol/a2a_runtime/  # ② production A2A: queue, idempotency, escrow hooks, HTTP server/client
├── economic/           # ③ PEA, market, vibe settlement, joint order (Shapley), agent directory
├── trust/              # quality-gate → reputation / dispute bridge
├── blockchain/ + ../../contracts/  # VIBE token, staking, settlement contracts (Base)
├── services/matching/  # LLM-first capability matching
├── products/           # ButlerPea (super-individual), TeamLeaderPea (team)
└── meta_agent/         # orchestrator (LLM, tools, memory, evolution)
```

## Status (honest)

- ✅ **Working & tested** (single-machine + cross-process): economic citizen → discovery → recursive / joint orders → escrow / quality-gate / Shapley settlement → reputation / dispute → remote A2A. Covered by unit tests and six runnable demos.
- ⏳ **Deferred (blockchain):** on-chain escrow contract, real `VIBDispute`, testnet settlement. Cross-*machine* settlement needs a chain as the shared global ledger — the `make_wallet_transfer_fn` rail is already in place; swapping the off-chain ledger for testnet is the remaining step.

## Documentation

- [`docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md`](./docs/roadmap/v3.0_USMSB_OPC_Fusion_Architecture.md) — architecture, goal, dual-coordinate model, three pillars.
- [`docs/usmsb-theory.md`](./docs/usmsb-theory.md) · [`docs/USMSB_SDK_Whitepaper.md`](./docs/USMSB_SDK_Whitepaper.md) — theory & whitepaper.

## License

See [LICENSE](./LICENSE).
