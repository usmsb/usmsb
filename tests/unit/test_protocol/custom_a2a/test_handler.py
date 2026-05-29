"""
Tests for CustomA2AHandler
"""

import pytest
import asyncio

from usmsb_sdk.protocol.custom_a2a import CustomA2AHandler
from usmsb_sdk.protocol.types.custom_a2a import (
    CustomAgentCard, CustomSkill, CustomTaskStatus,
)
from usmsb_sdk.protocol.types.envelope import A2AEnvelope


@pytest.fixture
def agent_card():
    """创建测试用 CustomAgentCard"""
    return CustomAgentCard(
        id="agent-001",
        name="Test Agent",
        description="A test agent",
        capabilities=["reasoning", "coding"],
        skills=[
            CustomSkill(
                id="skill-001",
                name="coding",
                description="Coding skill",
            )
        ],
        owner_wallet="0x1234",
        reputation=0.8,
    )


@pytest.fixture
def handler(agent_card):
    """创建测试用 CustomA2AHandler"""
    return CustomA2AHandler(
        agent_id="agent-001",
        agent_card=agent_card,
    )


class TestCustomA2AHandler:
    """Test CustomA2AHandler"""

    def test_init(self, handler, agent_card):
        """测试初始化"""
        assert handler.agent_id == "agent-001"
        assert handler.agent_card == agent_card

    @pytest.mark.asyncio
    async def test_handle_task_request(self, handler):
        """测试处理任务请求"""
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="task",
            payload={
                "task_id": "orig-task-001",
                "description": "Do some work",
                "input_data": {"data": "test"},
                "reward": 10.0,
                "currency": "USDC",
            },
        )

        response = await handler.handle_envelope(envelope)

        assert response is not None
        assert response.sender_id == "agent-001"
        assert response.receiver_id == "agent-002"
        assert response.message_type == "response"
        assert response.payload.get("status") == "accepted"

    @pytest.mark.asyncio
    async def test_handle_discovery(self, handler):
        """测试处理发现请求"""
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="discovery",
            payload={},
        )

        response = await handler.handle_envelope(envelope)

        assert response is not None
        assert "agent_card" in response.payload
        assert response.payload["agent_card"]["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_handle_heartbeat(self, handler):
        """测试处理心跳"""
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="heartbeat",
            payload={},
        )

        response = await handler.handle_envelope(envelope)

        assert response is not None
        assert response.payload.get("status") == "alive"

    @pytest.mark.asyncio
    async def test_accept_task(self, handler):
        """测试接受任务"""
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="task",
            payload={
                "task_id": "orig-task-001",
                "description": "Do some work",
                "input_data": {"data": "test"},
            },
        )

        response = await handler.handle_envelope(envelope)

        # 任务被接受，状态为 accepted
        assert response.payload.get("status") == "accepted"

    @pytest.mark.asyncio
    async def test_complete_task(self, handler):
        """测试完成任务 - 通过 handle_envelope"""
        # 模拟收到一个任务请求
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="task",
            payload={
                "task_id": "orig-task-001",
                "description": "Do some work",
                "input_data": {"data": "test"},
            },
        )

        response = await handler.handle_envelope(envelope)
        task_id = response.payload.get("task_id")

        # 完成任务
        success = await handler.complete_task(task_id, {"result": "done"})
        assert success is True

        # 检查任务状态
        task = await handler.get_task(task_id)
        assert task is not None
        assert task.status == CustomTaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_fail_task(self, handler):
        """测试任务失败 - 通过 handle_envelope"""
        # 模拟收到一个任务请求
        envelope = A2AEnvelope(
            sender_id="agent-002",
            receiver_id="agent-001",
            message_type="task",
            payload={
                "task_id": "orig-task-001",
                "description": "Do some work",
                "input_data": {"data": "test"},
            },
        )

        response = await handler.handle_envelope(envelope)
        task_id = response.payload.get("task_id")

        # 标记失败
        success = await handler.fail_task(task_id, "Something went wrong")
        assert success is True

        # 检查任务状态
        task = await handler.get_task(task_id)
        assert task is not None
        assert task.status == CustomTaskStatus.FAILED
        assert task.error == "Something went wrong"

    @pytest.mark.asyncio
    async def test_send_query(self, handler):
        """测试发送查询"""
        # 这只是测试发送不会抛异常
        await handler.send_query(
            to_agent="agent-002",
            query_type="agent_info",
        )
