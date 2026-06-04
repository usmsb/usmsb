import asyncio
from types import SimpleNamespace

from usmsb_sdk.l1.rule_engine import (
    Action,
    ActionType,
    Condition,
    ConditionType,
    Rule,
    RuleEngine,
    Stimulus,
)
from usmsb_sdk.l5.l5_collective import L5CollectiveIntelligence
from usmsb_sdk.meta_agent.agent import MetaAgent
from usmsb_sdk.meta_agent.knowledge.vector_store import VectorKnowledgeBase
from usmsb_sdk.meta_agent.llm.manager import LLMManager


def test_l1_rule_scope_can_bypass_internal_structured_prompts():
    engine = RuleEngine("test")
    engine.add_rule(
        Rule(
            name="identity",
            condition=Condition(ConditionType.PATTERN, r"自我介绍|你是谁"),
            action=Action(ActionType.RESPOND, response="identity response"),
            priority=100,
            metadata={"allowed_sources": ["user"], "allowed_task_types": ["chat"]},
        )
    )

    user_response = asyncio.run(
        engine.react(Stimulus(text="你是谁", source="user", metadata={"task_type": "chat"}))
    )
    assert user_response.rule_name == "identity"

    internal_response = asyncio.run(
        engine.react(
            Stimulus(
                text="禁止自我介绍。只输出 JSON。",
                source="skill",
                metadata={"task_type": "structured_skill"},
            )
        )
    )
    assert internal_response.rule_name != "identity"

    bypassed_response = asyncio.run(
        engine.react(Stimulus(text="你是谁", source="user", metadata={"bypass_l1": True}))
    )
    assert bypassed_response.rule_name == "bypassed"
    assert bypassed_response.action_result == ""


class SequencedLLMManager(LLMManager):
    def __init__(self, responses):
        super().__init__(
            SimpleNamespace(
                provider="local",
                model="test",
                api_key=None,
                base_url=None,
                temperature=0.0,
                max_tokens=1024,
            )
        )
        self.responses = list(responses)

    async def generate(self, prompt, system_prompt=None, **kwargs):
        return self.responses.pop(0)


def test_llm_manager_generate_json_repairs_invalid_output():
    manager = SequencedLLMManager([
        "not json",
        '{"title": "ok", "score": 100}',
    ])

    result = asyncio.run(
        manager.generate_json(
            system_prompt="Return JSON.",
            user_prompt="Create object.",
            schema={"type": "object", "required": ["title", "score"]},
            retries=1,
            return_metadata=True,
        )
    )

    assert result["data"] == {"title": "ok", "score": 100}
    assert result["attempts"] == 2
    assert result["errors"]


def test_vector_knowledge_base_compatibility_methods(tmp_path):
    store = VectorKnowledgeBase(db_path=str(tmp_path / "kb.db"))
    asyncio.run(
        store.add_knowledge(
            "OPC business plan quality feedback",
            metadata={"document_id": "doc-1", "success": True, "user_emphasized": True},
            source="doc-1",
            category="feedback",
        )
    )

    results = asyncio.run(store.search_knowledge_base("business plan", top_k=1))
    assert results
    assert results[0].id
    assert "business plan" in results[0].content
    assert results[0].success is True
    assert results[0].user_emphasized is True

    doc_results = asyncio.run(store.search_in_document("doc-1", "quality", top_k=1))
    assert doc_results
    assert doc_results[0].source == "doc-1"


class FakeSkillManager:
    async def activate_skill(self, skill_name, include_scripts=False, include_references=True):
        return {
            "instructions": "Return a JSON object with title and score.",
            "references_content": {"case.md": "Good outputs include concrete decisions."},
        }


class FakeLLMManager:
    async def generate_json(self, **kwargs):
        return {
            "data": {"title": "structured result", "score": 95},
            "raw": '{"title": "structured result", "score": 95}',
            "attempts": 1,
            "errors": [],
        }


class FakeVectorStore:
    def __init__(self):
        self.items = []

    async def add_knowledge(self, content, metadata=None, source="unknown", category="general"):
        self.items.append((content, metadata, source, category))
        return "kid"


class FakeL5:
    def __init__(self):
        self.events = []

    async def learn_from_feedback(self, **kwargs):
        self.events.append(kwargs)
        return {"stored": True}


def test_meta_agent_execute_structured_skill_uses_sdk_feedback_path():
    agent = MetaAgent()
    agent.skills_manager = FakeSkillManager()
    agent.llm_manager = FakeLLMManager()
    agent.smart_recall = None
    agent.l5_collective = FakeL5()
    agent.vector_kb = FakeVectorStore()
    agent.error_learning = None
    agent.l4_agent = None

    result = asyncio.run(
        agent.execute_structured_skill(
            skill_name="decision_flow",
            user_prompt="Generate a plan.",
            schema={"type": "object", "required": ["title", "score"]},
            wallet_address="user-1",
        )
    )

    assert result["type"] == "structured"
    assert result["data"]["score"] == 95
    assert agent.l5_collective.events
    assert agent.vector_kb.items


def test_l5_collective_learns_from_feedback_without_members():
    collective = L5CollectiveIntelligence("feedback-test")
    result = asyncio.run(
        collective.learn_from_feedback(
            event_type="business_plan_review",
            input={"seed": "project"},
            output={"plan": "draft"},
            feedback={"committee": "approved"},
            quality_score=0.9,
            tags=["opc", "business_plan"],
            source_agent="agent-1",
        )
    )

    assert result["stored"] is True
    assert result["source_agent"] == "agent-1"
    assert collective.collective_memory.stats["total_memories"] == 1
    assert "high_quality_feedback" in collective.collective_self.identity.shared_traits
