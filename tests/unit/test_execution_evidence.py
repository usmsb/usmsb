"""Offline contract regressions; mocks are not AI behavior or external effect evidence."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from usmsb_sdk.core.elements import Agent, Goal, GoalStatus
from usmsb_sdk.core.logic.core_engines import InformationDecisionControlEngine
from usmsb_sdk.core.logic.goal_action_outcome import GoalActionOutcomeLoop, LoopStatus
from usmsb_sdk.core.universal_actions import (
    ActionResult,
    ActionResultStatus,
    LLMExecutionService,
    UniversalActionServiceFactory,
)

pytestmark = [pytest.mark.unit, pytest.mark.anyio]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.parametrize("action", [
    {},
    {"type": "generic", "description": "Find an appropriate next step"},
    {"type": "new-domain-operation", "tool": "available_tool"},
    {"type": None},
])
@pytest.mark.parametrize("response", [
    '{"proposed_steps": ["inspect"], "expected_result": "a measurement"}',
    '{"steps_executed": ["published"], "status": "success", "result": "done"}',
    "  A plain-text candidate, not a receipt.\n",
])
async def test_generic_is_only_a_plan_even_if_model_claims_success(action, response):
    llm = SimpleNamespace(generate_text=AsyncMock(return_value=response))
    tool = Mock()
    service = LLMExecutionService(llm, {"available_tool": tool})
    service.execute_code = AsyncMock()
    service.call_tool = AsyncMock()
    context = {"authorization_claim": "execute everything", "status": "success"}

    result = await service.execute(action, agent=None, context=context)

    assert result.status is ActionResultStatus.PENDING
    assert result.error is None
    assert result.data == {
        "execution_plan": response,
        "execution_result": None,
        "steps_executed": [],
    }
    assert result.metadata == {"result_kind": "plan", "execution_status": "not_executed"}
    assert result.execution_time >= 0
    llm.generate_text.assert_awaited_once()
    prompt, supplied_context = llm.generate_text.await_args.args
    assert supplied_context is context
    assert "proposed_steps" in prompt and "expected_result" in prompt
    assert "steps_executed" not in prompt
    service.execute_code.assert_not_awaited()
    service.call_tool.assert_not_awaited()
    tool.assert_not_called()


@pytest.mark.parametrize("response", [None, "", " \n\t", {"status": "success"}])
async def test_empty_or_nontext_plan_generation_is_a_failure(response):
    llm = SimpleNamespace(generate_text=AsyncMock(return_value=response))
    result = await LLMExecutionService(llm).execute({}, None)
    assert result.status is ActionResultStatus.FAILURE
    assert result.data is None
    assert result.error == "Plan generation returned no text"
    llm.generate_text.assert_awaited_once()


async def test_generation_failure_is_preserved_without_retry():
    llm = SimpleNamespace(generate_text=AsyncMock(side_effect=RuntimeError("provider failed")))
    result = await LLMExecutionService(llm).execute({}, None)
    assert result.status is ActionResultStatus.FAILURE
    assert result.error == "provider failed"
    assert result.data is None
    llm.generate_text.assert_awaited_once()


@pytest.mark.parametrize("action, method, args", [
    ({"type": "code", "code": "not executed", "language": "python"},
     "execute_code", ("not executed", "python")),
    ({"type": "tool_call", "tool": "probe", "params": {"sample": 3}},
     "call_tool", ("probe", {"sample": 3})),
])
@pytest.mark.parametrize("status", list(ActionResultStatus))
async def test_explicit_dispatch_preserves_executor_result(action, method, args, status):
    llm = SimpleNamespace(generate_text=AsyncMock())
    service = LLMExecutionService(llm)
    receipt = ActionResult(status=status, data={"receipt": "test-only"})
    dispatch = AsyncMock(return_value=receipt)
    setattr(service, method, dispatch)
    context = {"caller": "test"}
    assert await service.execute(action, None, context) is receipt
    dispatch.assert_awaited_once_with(*args, context)
    llm.generate_text.assert_not_awaited()


@pytest.mark.parametrize("asynchronous", [False, True])
async def test_registered_test_tool_still_runs_only_on_explicit_tool_call(asynchronous):
    llm = SimpleNamespace(generate_text=AsyncMock())
    tool = AsyncMock(return_value=6) if asynchronous else Mock(return_value=6)
    service = LLMExecutionService(llm, {"test_tool": tool})
    result = await service.execute(
        {"type": "tool_call", "tool": "test_tool", "params": {"value": 3}}, None
    )
    assert result.status is ActionResultStatus.SUCCESS
    assert result.data == {"tool": "test_tool", "result": 6}
    tool.assert_called_once_with(value=3)
    if asynchronous:
        tool.assert_awaited_once_with(value=3)
    llm.generate_text.assert_not_awaited()


async def test_missing_tool_does_not_fall_back_to_successful_plan():
    llm = SimpleNamespace(generate_text=AsyncMock())
    result = await LLMExecutionService(llm).execute(
        {"type": "tool_call", "tool": "absent"}, None
    )
    assert result.status is ActionResultStatus.FAILURE
    assert result.error == "Tool not found: absent"
    llm.generate_text.assert_not_awaited()


async def test_tool_exception_remains_a_failure_without_retry():
    llm = SimpleNamespace(generate_text=AsyncMock())
    tool = Mock(side_effect=RuntimeError("test tool failed"))
    result = await LLMExecutionService(llm, {"test_tool": tool}).execute(
        {"type": "tool_call", "tool": "test_tool"}, None
    )
    assert result.status is ActionResultStatus.FAILURE
    assert result.error == "test tool failed"
    tool.assert_called_once_with()
    llm.generate_text.assert_not_awaited()


def make_loop(execution_service, *, action=None, max_iterations=1):
    goal = Goal(name="Test goal")
    agent = Agent(name="Test agent", goals=[goal])
    evaluation = {"goal_achieved": True, "explanation": "test evaluator claim"}
    evaluator = SimpleNamespace(evaluate_action_outcome=AsyncMock(return_value=evaluation))
    loop = GoalActionOutcomeLoop(
        perception_service=None,
        decision_service=SimpleNamespace(decide=AsyncMock(return_value={
            "action": action or {"id": "candidate", "type": "generic"},
        })),
        execution_service=execution_service,
        evaluation_service=evaluator,
        feedback_service=SimpleNamespace(generate_feedback=AsyncMock(return_value={})),
        max_iterations=max_iterations,
        iteration_delay=0,
    )
    return loop, agent, goal, evaluator, evaluation


async def test_goal_loop_keeps_plan_pending_and_does_not_regenerate_or_complete_goal():
    llm = SimpleNamespace(generate_text=AsyncMock(return_value='{"status":"success"}'))
    executor = UniversalActionServiceFactory.create_all_services(llm)["execution"]
    loop, agent, goal, evaluator, reported_evaluation = make_loop(executor, max_iterations=10)
    on_execution = Mock()
    on_evaluation = Mock()
    loop.on_action_executed = on_execution
    loop.on_evaluation_complete = on_evaluation

    summary = await loop.run(agent)

    assert loop.status is LoopStatus.PAUSED
    assert summary["total_iterations"] == 1
    assert summary["actions_summary"] == {
        "total": 1, "successful": 0, "failed": 0, "pending": 1,
        "partial": 0, "unknown": 0, "success_rate": 0,
    }
    assert summary["completed_goals"] == []
    assert goal.status is GoalStatus.IN_PROGRESS
    record = loop.iteration_history[0]
    assert not record.execution_result.success
    assert record.execution_result.status == "pending"
    assert record.execution_result.outcome.data["execution_plan"] == '{"status":"success"}'
    assert record.evaluation_result["goal_achieved"] is False
    assert record.evaluation_result["reported_goal_achieved"] is True
    assert record.evaluation_result["completion_blocked_reason"] == "execution_not_successful"
    assert reported_evaluation["goal_achieved"] is True  # Original evidence is not mutated.
    assert evaluator.evaluate_action_outcome.await_args.args[1] is record.execution_result.outcome
    assert on_execution.call_args.args[0].success is False
    assert on_evaluation.call_args.args[0]["goal_achieved"] is False
    llm.generate_text.assert_awaited_once()


@pytest.mark.parametrize("outcome, expected_status", [
    (ActionResult(ActionResultStatus.SUCCESS, data={"test_receipt": 1}), "success"),
    (ActionResult(ActionResultStatus.FAILURE, error="rejected"), "failure"),
    (ActionResult(ActionResultStatus.PARTIAL, data={"test_receipt": 1}), "partial"),
    ({"status": "success", "result": "legacy receipt"}, "success"),
    ({"status": "pending", "success": True}, "pending"),
    ({"status": "failure", "error": "legacy failure"}, "failure"),
    ({"success": True, "result": "legacy receipt"}, "success"),
    ({"success": False}, "failure"),
    ({"success": "true"}, "unknown"),
    ({"execution_plan": "only a plan"}, "unknown"),
    ({"status": "unrecognized", "success": True}, "unknown"),
    ("opaque legacy output", "unknown"),
    (None, "unknown"),
])
async def test_goal_loop_status_and_legacy_results_are_not_blanket_success(outcome, expected_status):
    executor = SimpleNamespace(execute=AsyncMock(return_value=outcome))
    loop, agent, goal, _, _ = make_loop(executor)
    summary = await loop.run(agent)
    record = loop.iteration_history[0].execution_result
    assert record.outcome is outcome
    assert record.status == expected_status
    assert record.success is (expected_status == "success")
    assert (goal.status is GoalStatus.COMPLETED) is (expected_status == "success")
    counter = {"success": "successful", "failure": "failed"}.get(expected_status, expected_status)
    assert summary["actions_summary"][counter] == 1
    if expected_status == "failure":
        assert record.error == (outcome.error if isinstance(outcome, ActionResult)
                                else outcome.get("error"))


async def test_goal_loop_exception_keeps_failure_not_pending():
    executor = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("executor failed")))
    loop, agent, goal, _, _ = make_loop(executor)
    summary = await loop.run(agent)
    assert summary["actions_summary"]["failed"] == 1
    assert loop.iteration_history[0].execution_result.error == "executor failed"
    assert goal.status is GoalStatus.IN_PROGRESS


async def test_control_loop_retains_plan_without_listing_it_as_executed():
    llm = SimpleNamespace(generate_text=AsyncMock(return_value="candidate"))
    engine = InformationDecisionControlEngine(
        perception_service=SimpleNamespace(perceive=AsyncMock(return_value=ActionResult(
            ActionResultStatus.SUCCESS, data={"observation": "test only"},
        ))),
        decision_service=SimpleNamespace(decide=AsyncMock(return_value=ActionResult(
            ActionResultStatus.SUCCESS, data={"decision": "new-domain-operation"},
        ))),
        execution_service=LLMExecutionService(llm),
    )
    summary = await engine.run({"inputs": ["test input"], "goals": ["test goal"]})
    assert summary["actions_executed"] == []
    assert len(summary["execution_results"]) == 1
    result = summary["execution_results"][0]
    assert result["executed"] is False
    assert result["status"] == "pending"
    assert result["outcome"]["execution_plan"] == "candidate"
    assert result["metadata"]["execution_status"] == "not_executed"
    assert engine._loop_history[0]["result"] is result


@pytest.mark.parametrize("status", list(ActionResultStatus))
async def test_control_executor_status_and_error_are_preserved(status):
    receipt = ActionResult(status, data={"receipt": "test"}, error="test error")
    executor = SimpleNamespace(execute=AsyncMock(return_value=receipt))
    engine = InformationDecisionControlEngine(execution_service=executor)
    result = await engine.execute_control({"id": "control", "action": "tool_call"}, None, {})
    assert result["executed"] is (status is ActionResultStatus.SUCCESS)
    assert result["status"] == status.value
    assert result["outcome"] is receipt.data
    assert result["error"] == "test error"


@pytest.mark.parametrize("status", list(ActionResultStatus))
async def test_control_summary_counts_only_successful_execution_results(status):
    engine = InformationDecisionControlEngine(
        perception_service=SimpleNamespace(perceive=AsyncMock(return_value=ActionResult(
            ActionResultStatus.SUCCESS, data={"test": True},
        ))),
        decision_service=SimpleNamespace(decide=AsyncMock(return_value=ActionResult(
            ActionResultStatus.SUCCESS, data={"decision": "test action"},
        ))),
        execution_service=SimpleNamespace(execute=AsyncMock(return_value=ActionResult(status))),
    )
    summary = await engine.run({"inputs": ["test"], "goals": ["test"]})
    assert len(summary["execution_results"]) == 1
    assert len(summary["actions_executed"]) == int(status is ActionResultStatus.SUCCESS)

