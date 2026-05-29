"""
Tests for Google A2A Types
"""

import pytest

from usmsb_sdk.protocol.types.google_a2a import (
    TaskState, Role, MessageType, Part, Message,
    TaskStatus, Artifact, Task, AgentCard,
    AgentCapabilities, AgentProvider, AgentSkill,
    SendMessageRequest, GetTaskRequest, CancelTaskRequest,
)


class TestTaskState:
    """Test TaskState enum"""

    def test_task_states(self):
        """测试所有任务状态"""
        assert TaskState.SUBMITTED.value == "submitted"
        assert TaskState.WORKING.value == "working"
        assert TaskState.COMPLETED.value == "completed"
        assert TaskState.FAILED.value == "failed"
        assert TaskState.CANCELED.value == "canceled"
        assert TaskState.INPUT_REQUIRED.value == "input-required"
        assert TaskState.REJECTED.value == "rejected"
        assert TaskState.AUTH_REQUIRED.value == "auth-required"


class TestRole:
    """Test Role enum"""

    def test_roles(self):
        """测试角色"""
        assert Role.USER.value == "user"
        assert Role.AGENT.value == "agent"


class TestPart:
    """Test Part"""

    def test_create_part(self):
        """测试创建片段"""
        part = Part(text="Hello")
        assert part.text == "Hello"
        assert part.has_content() is True

        part2 = Part(data={"key": "value"})
        assert part2.data == {"key": "value"}
        assert part2.has_content() is True

        part3 = Part()
        assert part3.has_content() is False


class TestMessage:
    """Test Message"""

    def test_create_message(self):
        """测试创建消息"""
        message = Message(
            message_id="msg-001",
            context_id="ctx-001",
            role=Role.USER,
            parts=[Part(text="Hello")],
        )
        assert message.message_id == "msg-001"
        assert message.role == Role.USER
        assert len(message.parts) == 1


class TestTaskStatus:
    """Test TaskStatus"""

    def test_create_status(self):
        """测试创建状态"""
        status = TaskStatus(state=TaskState.WORKING)
        assert status.state == TaskState.WORKING


class TestTask:
    """Test Task"""

    def test_create_task(self):
        """测试创建任务"""
        task = Task(
            id="task-001",
            context_id="ctx-001",
            status=TaskStatus(state=TaskState.SUBMITTED),
        )
        assert task.id == "task-001"
        assert task.status.state == TaskState.SUBMITTED
        assert len(task.artifacts) == 0
        assert len(task.history) == 0


class TestAgentCard:
    """Test AgentCard"""

    def test_create_agent_card(self):
        """测试创建 AgentCard"""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
            version="1.0",
            provider=AgentProvider(organization="TestOrg"),
            capabilities=AgentCapabilities(streaming=True),
        )
        assert card.name == "Test Agent"
        assert card.version == "1.0"
        assert card.capabilities.streaming is True

    def test_agent_card_serialization(self):
        """测试 AgentCard 序列化"""
        card = AgentCard(
            name="Test Agent",
            description="A test agent",
        )
        data = card.model_dump()
        assert data["name"] == "Test Agent"

        card2 = AgentCard.model_validate(data)
        assert card2.name == card.name


class TestRequests:
    """Test Request types"""

    def test_send_message_request(self):
        """测试 SendMessageRequest"""
        req = SendMessageRequest(
            message=Message(
                message_id="msg-001",
                role=Role.USER,
                parts=[Part(text="Hello")],
            )
        )
        assert req.message.message_id == "msg-001"

    def test_get_task_request(self):
        """测试 GetTaskRequest"""
        req = GetTaskRequest(task_id="task-001")
        assert req.task_id == "task-001"

    def test_cancel_task_request(self):
        """测试 CancelTaskRequest"""
        req = CancelTaskRequest(task_id="task-001")
        assert req.task_id == "task-001"
