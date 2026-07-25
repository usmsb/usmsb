"""Regression guard for paid provider creation replay in MetaAgent.chat."""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from usmsb_sdk.meta_agent.agent import MetaAgent
from usmsb_sdk.meta_agent.models.chat_result import ChatResult


def test_chat_impl_does_not_loop_around_provider_creation() -> None:
    source_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "usmsb_sdk"
        / "meta_agent"
        / "agent.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    chat_impl = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_chat_impl"
    )
    parents: dict[ast.AST, ast.AST] = {
        child: parent
        for parent in ast.walk(chat_impl)
        for child in ast.iter_child_nodes(parent)
    }
    provider_calls = [
        node
        for node in ast.walk(chat_impl)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_chat_with_llm"
    ]

    # The strategy Harness has an explicitly selected internal strategy call
    # plus the normal direct path. Neither paid creation boundary may sit under
    # a blanket transport retry loop.
    assert provider_calls
    for provider_call in provider_calls:
        current: ast.AST | None = provider_call
        while current is not None and current is not chat_impl:
            assert not isinstance(current, (ast.For, ast.AsyncFor, ast.While))
            current = parents.get(current)

    direct_call = next(
        provider_call
        for provider_call in provider_calls
        if not any(
            isinstance(ancestor, ast.AsyncFunctionDef)
            and ancestor is not chat_impl
            for ancestor in _ancestors(provider_call, parents, stop=chat_impl)
        )
    )
    guarding_ifs = [
        ancestor
        for ancestor in _ancestors(direct_call, parents, stop=chat_impl)
        if isinstance(ancestor, ast.If)
    ]
    assert any(
        "not strategy_route_failed" in ast.unparse(guard.test)
        for guard in guarding_ifs
    )


def _ancestors(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
    *,
    stop: ast.AST,
) -> list[ast.AST]:
    result: list[ast.AST] = []
    current = parents.get(node)
    while current is not None and current is not stop:
        result.append(current)
        current = parents.get(current)
    return result


def _bare_chat_agent(*, strategy_router: object | None) -> MetaAgent:
    agent = object.__new__(MetaAgent)
    conversation = SimpleNamespace(id="conversation-single-shot")
    agent.conversation_manager = SimpleNamespace(
        get_or_create_conversation=AsyncMock(return_value=conversation),
        add_message=AsyncMock(),
        get_messages_for_llm=AsyncMock(return_value=[]),
    )
    agent.llm_manager = SimpleNamespace(
        provider="minimax",
        max_tokens=4096,
        update_trace_context=Mock(),
    )
    agent.memory_manager = SimpleNamespace(
        process_conversation=AsyncMock(),
        get_context=AsyncMock(return_value=""),
        check_and_store_user_emphasis=AsyncMock(),
    )
    agent.context_manager = SimpleNamespace(build_messages=AsyncMock(return_value=[]))
    agent.tool_registry = SimpleNamespace(
        list_tools=Mock(return_value=[]),
        get_tools_schema=Mock(return_value=[]),
    )
    agent.skills_manager = SimpleNamespace(
        get_skills_catalog=Mock(return_value=""),
        get_skills_schema=Mock(return_value=[]),
    )
    agent._filter_tools_by_permission = AsyncMock(return_value=[])
    agent._get_l4_decision_context = Mock(return_value="")
    agent._get_l5_decision_context = Mock(return_value="")
    agent._broadcast_collaboration_request = AsyncMock(return_value=[])
    agent.strategy_router = strategy_router
    agent.smart_recall = None
    agent.gene_capsule_adapter = None
    agent.permission_manager = None
    agent.task_executor = None
    agent.l4_agent = None
    agent._external_agents_connected = False
    return agent


@pytest.mark.asyncio
async def test_strategy_provider_failure_does_not_replay_direct_path() -> None:
    class FailedStrategyRouter:
        async def _classify_scenario(self, _message: str) -> SimpleNamespace:
            return SimpleNamespace(
                scenario="INFO",
                suggested_layer="L2",
                strategy_preference="internal",
            )

        async def route(self, _message, _layer, internal_fn, _sdk_fn):
            try:
                await internal_fn()
            except TimeoutError as error:
                return SimpleNamespace(
                    result=None,
                    error=str(error),
                    strategy_name="internal",
                    quality_score=0.0,
                )
            raise AssertionError("provider timeout should have failed the strategy")

    agent = _bare_chat_agent(strategy_router=FailedStrategyRouter())
    agent._chat_with_llm = AsyncMock(side_effect=TimeoutError("provider state unknown"))

    result = await MetaAgent._chat_impl(
        agent,
        "single shot",
        skip_complexity_detection=True,
        skip_l1_rules=True,
    )

    assert result == "抱歉，处理您的请求时遇到了问题。请稍后重试。"
    assert agent._chat_with_llm.await_count == 1


@pytest.mark.asyncio
async def test_statically_unconfigured_strategy_uses_one_direct_provider_call() -> None:
    agent = _bare_chat_agent(strategy_router=None)
    agent._chat_with_llm = AsyncMock(
        return_value=ChatResult(
            content="ok",
            executed_tools=[],
            tool_results=[],
            iterations_used=0,
            is_complete=True,
            needs_background=False,
            needs_tool_retry=False,
        )
    )

    result = await MetaAgent._chat_impl(
        agent,
        "single direct",
        skip_complexity_detection=True,
        skip_l1_rules=True,
    )

    assert result == "ok"
    assert agent._chat_with_llm.await_count == 1


@pytest.mark.asyncio
async def test_tool_provider_failure_is_not_replayed_as_simple_chat() -> None:
    adapter = SimpleNamespace(
        chat_with_tools=AsyncMock(side_effect=TimeoutError("provider state unknown")),
        chat_with_messages=AsyncMock(return_value="must not run"),
    )
    agent = object.__new__(MetaAgent)
    agent.llm_manager = SimpleNamespace(_adapter=adapter)

    with pytest.raises(TimeoutError, match="provider state unknown"):
        await MetaAgent._call_llm_with_tools(
            agent,
            messages=[{"role": "user", "content": "do work"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "do_work",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
        )

    assert adapter.chat_with_tools.await_count == 1
    assert adapter.chat_with_messages.await_count == 0
