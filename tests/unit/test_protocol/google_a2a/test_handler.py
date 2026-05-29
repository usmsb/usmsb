"""
Tests for GoogleA2AHandler
"""

import pytest
import asyncio

from usmsb_sdk.protocol.google_a2a import GoogleA2AHandler
from usmsb_sdk.protocol.google_a2a.handler import SimpleAgentExecutor
from usmsb_sdk.protocol.types.google_a2a import (
    AgentCard, AgentCapabilities, AgentProvider,
    Message, Role, Part, SendMessageRequest, GetTaskRequest, CancelTaskRequest,
    TaskState,
)


@pytest.fixture
def agent_card():
    """创建测试用 AgentCard"""
    return AgentCard(
        name="Test Agent",
        description="A test agent",
        version="1.0",
        provider=AgentProvider(organization="TestOrg"),
        capabilities=AgentCapabilities(streaming=True),
    )


@pytest.fixture
def executor():
    """创建测试用执行器"""
    async def handler(msg):
        return f"Processed: {msg.parts[0].text if msg.parts else 'empty'}"

    return SimpleAgentExecutor(handler, is_async=True)


@pytest.fixture
def handler(agent_card, executor):
    """创建测试用 Handler"""
    return GoogleA2AHandler(
        agent_card=agent_card,
        agent_executor=executor,
    )


class TestGoogleA2AHandler:
    """Test GoogleA2AHandler"""

    def test_init(self, handler, agent_card):
        """测试初始化"""
        assert handler.agent_card == agent_card
        assert handler.agent_card.name == "Test Agent"

    def test_agent_card_endpoint(self, handler):
        """测试 AgentCard 端点"""
        card = handler.agent_card
        assert card.name == "Test Agent"
        assert card.version == "1.0"

    @pytest.mark.asyncio
    async def test_send_task(self, handler):
        """测试发送任务"""
        req = SendMessageRequest(
            message=Message(
                message_id="msg-001",
                role=Role.USER,
                parts=[Part(text="Hello!")],
            )
        )

        task = await handler.on_send_task(req)
        assert task.id is not None
        assert task.context_id is not None

    @pytest.mark.asyncio
    async def test_get_task(self, handler):
        """测试获取任务"""
        # 先创建任务
        req = SendMessageRequest(
            message=Message(
                message_id="msg-001",
                role=Role.USER,
                parts=[Part(text="Hello!")],
            )
        )
        created_task = await handler.on_send_task(req)

        # 获取任务
        get_req = GetTaskRequest(task_id=created_task.id)
        task = await handler.on_get_task(get_req)

        assert task is not None
        assert task.id == created_task.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, handler):
        """测试获取不存在的任务"""
        get_req = GetTaskRequest(task_id="nonexistent")
        task = await handler.on_get_task(get_req)
        assert task is None

    @pytest.mark.asyncio
    async def test_cancel_task(self, handler):
        """测试取消任务"""
        # 创建长时间运行的任务
        async def slow_handler(msg):
            await asyncio.sleep(10)
            return "done"

        slow_executor = SimpleAgentExecutor(slow_handler, is_async=True)
        slow_handler_obj = GoogleA2AHandler(
            agent_card=handler.agent_card,
            agent_executor=slow_executor,
        )

        req = SendMessageRequest(
            message=Message(
                message_id="msg-001",
                role=Role.USER,
                parts=[Part(text="Hello!")],
            )
        )
        task = await slow_handler_obj.on_send_task(req)

        # 取消任务
        cancel_req = CancelTaskRequest(task_id=task.id)
        cancelled_task = await slow_handler_obj.on_cancel_task(cancel_req)

        assert cancelled_task is not None
        assert cancelled_task.status.state == TaskState.CANCELED

    @pytest.mark.asyncio
    async def test_task_execution(self, handler):
        """测试任务执行"""
        req = SendMessageRequest(
            message=Message(
                message_id="msg-001",
                role=Role.USER,
                parts=[Part(text="Hello!")],
            )
        )

        task = await handler.on_send_task(req)

        # 等待任务完成
        await asyncio.sleep(0.3)

        # 获取任务状态
        get_req = GetTaskRequest(task_id=task.id)
        final_task = await handler.on_get_task(get_req)

        assert final_task is not None
        assert final_task.status.state == TaskState.COMPLETED

    @pytest.mark.asyncio
    async def test_list_tasks(self, handler):
        """测试列出任务"""
        # 创建几个任务
        for i in range(3):
            req = SendMessageRequest(
                message=Message(
                    message_id=f"msg-{i}",
                    role=Role.USER,
                    parts=[Part(text=f"Hello {i}!")],
                )
            )
            await handler.on_send_task(req)

        # 等待任务完成
        await asyncio.sleep(0.5)

        # 列出任务
        from usmsb_sdk.protocol.types.google_a2a import ListTasksRequest

        list_req = ListTasksRequest()
        tasks, total = await handler.on_list_tasks(list_req)

        assert total >= 3
        assert len(tasks) >= 3
