"""Executable contract for OpenHarness v0.1.9 / a0f8552."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

import pytest

from usmsb_sdk.adapters.openharness.compatibility import (
    OPENHARNESS_COMMIT,
    OPENHARNESS_VERSION,
    probe_openharness,
    require_openharness_019,
)
from usmsb_sdk.adapters.openharness.tool_adapter import ToolAdapter


def test_exact_openharness_release_and_all_required_subsystems_are_available() -> None:
    assert metadata.version("openharness-ai") == OPENHARNESS_VERSION == "0.1.9"
    assert OPENHARNESS_COMMIT == "a0f8552c69d6d0b25d613af288823212a8b6b59a"
    probe = probe_openharness()
    assert probe.compatible, probe.to_dict()
    assert require_openharness_019() == probe


@pytest.mark.asyncio
async def test_tool_registry_contract_executes_pydantic_tool_without_legacy_api(
    tmp_path: Path,
) -> None:
    async def inspect_signal(query: str, limit: int = 3) -> str:
        return f"{query}:{limit}"

    adapter = ToolAdapter(cwd=tmp_path)
    adapter.register_tool(
        inspect_signal,
        name="inspect_signal",
        description="Inspect one market signal",
        is_read_only=True,
    )

    assert adapter.tool_names == ["inspect_signal"]
    schema = adapter.to_api_schema()[0]
    assert schema["name"] == "inspect_signal"
    assert schema["input_schema"]["required"] == ["query"]
    result = await adapter.execute_tool(
        "inspect_signal",
        check_permission=False,
        query="sleep",
        limit=2,
    )
    assert not result.is_error
    assert result.output == "sleep:2"


@pytest.mark.asyncio
async def test_query_engine_preserves_tool_loop_and_resume_surface(tmp_path: Path) -> None:
    from openharness.api.client import ApiMessageCompleteEvent, ApiTextDeltaEvent
    from openharness.api.usage import UsageSnapshot
    from openharness.config.settings import PermissionSettings
    from openharness.engine.messages import ConversationMessage, TextBlock
    from openharness.engine.query_engine import QueryEngine
    from openharness.permissions.checker import PermissionChecker
    from openharness.tools.base import ToolRegistry

    class FakeClient:
        async def stream_message(self, request):
            del request
            yield ApiTextDeltaEvent(text="alive")
            yield ApiMessageCompleteEvent(
                message=ConversationMessage(
                    role="assistant",
                    content=[TextBlock(text="alive")],
                ),
                usage=UsageSnapshot(input_tokens=4, output_tokens=2),
                stop_reason="end_turn",
            )

    engine = QueryEngine(
        api_client=FakeClient(),
        tool_registry=ToolRegistry(),
        permission_checker=PermissionChecker(PermissionSettings()),
        cwd=tmp_path,
        model="fixture-model",
        system_prompt="Choose the next action from observations.",
        max_turns=3,
    )
    events = [event async for event in engine.submit_message("find demand")]
    assert events
    assert engine.messages[-1].text == "alive"
    assert engine.total_usage.total_tokens == 6
    assert hasattr(engine, "load_messages")
    assert hasattr(engine, "continue_pending")
    assert hasattr(engine, "has_pending_continuation")


def test_memory_compaction_and_swarm_lifecycle_contracts(tmp_path: Path, monkeypatch) -> None:
    from openharness.engine.messages import ConversationMessage
    from openharness.memory.manager import add_memory_entry, list_memory_files
    from openharness.memory.search import find_relevant_memories
    from openharness.services.compact import compact_messages, try_context_collapse
    from openharness.swarm.mailbox import TeammateMailbox, create_user_message
    from openharness.swarm.team_lifecycle import TeamLifecycleManager, TeamMember

    monkeypatch.setenv("HOME", str(tmp_path))
    project = tmp_path / "project"
    project.mkdir()
    add_memory_entry(project, "failed source", "Mirrored evidence is not independent.")
    assert list_memory_files(project)
    assert find_relevant_memories("independent evidence", project)

    messages = [
        ConversationMessage.from_user_text(f"observation {index} " + "x" * 3_000)
        for index in range(8)
    ]
    assert len(compact_messages(messages, preserve_recent=2)) < len(messages)
    assert try_context_collapse(messages, preserve_recent=2)

    lifecycle = TeamLifecycleManager()
    lifecycle.create_team("growth-contract", description="dynamic team")
    lifecycle.add_member(
        "growth-contract",
        TeamMember(
            agent_id="critic@growth-contract",
            name="critic",
            backend_type="in_process",
            joined_at=1.0,
        ),
    )
    assert "critic@growth-contract" in lifecycle.get_team("growth-contract").members
    mailbox = TeammateMailbox("growth-contract", "critic@growth-contract")
    message = create_user_message("leader", "critic@growth-contract", "challenge hypothesis")
    # The coroutine exists and the persisted mailbox is isolated under HOME.
    assert mailbox.get_mailbox_dir().is_relative_to(tmp_path)
    assert message.payload["content"] == "challenge hypothesis"
