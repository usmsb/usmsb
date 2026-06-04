# Structured Skill Execution and L5 Feedback PR Notes

## Purpose

This change improves MetaAgent reliability for business-critical structured
tasks such as OPC business plan generation. It keeps the work inside the USMSB
SDK instead of forcing downstream applications to bypass MetaAgent with direct
LLM calls.

## What Changed

- Added L1 rule scoping and bypass support via `Stimulus.metadata`.
  - Rules can now declare `allowed_sources`, `blocked_sources`,
    `allowed_task_types`, or `blocked_task_types` in `Rule.metadata`.
  - Internal structured prompts can set `bypass_l1=True` so identity/help rules
    do not intercept prompts that contain phrases such as "do not introduce
    yourself".
- Added `LLMManager.generate()` as a stable universal async generation API.
- Added `LLMManager.generate_json()` for structured JSON tasks.
  - Extracts JSON from plain text or code fences.
  - Supports lightweight schema checks.
  - Supports sync/async custom validators.
  - Retries with a repair prompt when output is not valid JSON.
- Added `VectorKnowledgeBase` compatibility methods used by SmartRecall.
  - `search_knowledge_base()`
  - `search_in_document()`
  - Convenience `SearchResult` fields such as `id`, `content`, `importance`,
    `success`, and `user_emphasized`.
- Added `MetaAgent.execute_structured_skill()`.
  - Loads skill instructions.
  - Injects SmartRecall, L4, and L5 context.
  - Calls `LLMManager.generate_json()`.
  - Records structured execution feedback through `learn_from_feedback()`.
- Added `MetaAgent.learn_from_feedback()` and
  `L5CollectiveIntelligence.learn_from_feedback()`.
  - Stores feedback into L5 collective memory.
  - Stores feedback in vector knowledge.
  - Forwards success/failure lessons to the experience DB when available.
  - Forwards feedback to L4 self-learning when available.
- L5 initialization now passes the MetaAgent LLM manager into L5 and registers
  the local L4 agent as a member when available.

## OPC Integration Example

Downstream OPC business plan generation can use:

```python
result = await opc_meta_agent.execute_structured_skill(
    skill_name="decision_flow",
    user_prompt=business_plan_prompt,
    schema={
        "type": "object",
        "required": ["title", "summary", "budget_total", "risk_level", "sections"],
    },
    validator=validate_business_plan_json,
    wallet_address=user.id,
    context={
        "session_id": decision_session.id,
        "material_ids": material_ids,
        "domain": "opc_business_decision",
    },
    retries=2,
    max_tokens=32768,
    temperature=0.4,
)

plan_json = result["data"]
```

After committee review, user confirmation, or execution feedback, OPC can feed
outcomes back into USMSB:

```python
await opc_meta_agent.learn_from_feedback(
    event_type="business_plan_review",
    input={"plan_id": plan.id, "materials": material_ids},
    output=plan_json,
    feedback={"committee_action": "approved", "quality_gate": validation},
    quality_score=validation["score"] / 100,
    tags=["opc", "business_plan", "decision_flow"],
    user_id=user.id,
)
```

## Verification

Commands run locally:

```bash
~/anaconda3/bin/python -m compileall \
  src/usmsb_sdk/l1/rule_engine.py \
  src/usmsb_sdk/meta_agent/llm/manager.py \
  src/usmsb_sdk/meta_agent/knowledge/vector_store.py \
  src/usmsb_sdk/meta_agent/agent.py \
  src/usmsb_sdk/l5/l5_collective.py \
  tests/unit/test_structured_skill_execution.py

~/anaconda3/bin/python -m pytest tests/unit/test_structured_skill_execution.py -q
~/anaconda3/bin/python -m pytest \
  tests/unit/test_smart_recall.py \
  tests/unit/test_l5_collective.py \
  tests/unit/test_strategy_router.py -q
~/anaconda3/bin/python -m pytest tests/unit/test_meta_agent_refactor.py -q
```

Results:

- New structured skill tests: `5 passed`.
- Related SmartRecall/L5/StrategyRouter tests: `99 passed`.
- MetaAgent refactor tests: `15 passed`.

