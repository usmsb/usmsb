"""
E2E Test: AI Agent Platform (Simplified Workflow)

Tests the simplified AIAgentPlatform for fully autonomous agents.
"""

import pytest


@pytest.mark.asyncio
class TestAIAgentPlatform:
    """Test AIAgentPlatform simplified workflow."""

    async def test_agent_lifecycle(self, backend_server):
        """
        Test the complete AI agent lifecycle:
        register → publish_capability → poll_for_task → execute → submit_result
        """
        import uuid
        from usmsb_agent_platform import AIAgentPlatform

        agent_id = f"ai_agent_{uuid.uuid4().hex[:8]}"
        api_key = f"usmsb_ai_{uuid.uuid4().hex[:12]}"

        # Create AI agent
        agent = AIAgentPlatform(
            api_key=api_key,
            agent_id=agent_id,
            base_url=backend_server
        )

        # 1. Register
        reg_result = await agent.register(
            name=f"AI Agent {agent_id}",
            capabilities=["data_analysis", "python"]
        )
        assert reg_result is not None
        assert agent.is_registered
        print(f"✓ AI Agent registered: {agent_id}")

        # 2. Publish capability
        cap_result = await agent.publish_capability(
            capability="data_analysis",
            price=100,
            description="Professional data analysis"
        )
        assert cap_result is not None
        print(f"✓ Capability published: data_analysis")

        # 3. Get capabilities
        caps = await agent.get_capabilities()
        assert "data_analysis" in caps
        print(f"✓ Capabilities confirmed: {caps}")

        # 4. Check balance
        balance = await agent.get_balance()
        assert balance is not None
        print(f"✓ Balance checked")

        # 5. Check reputation
        rep = await agent.get_reputation()
        assert rep is not None
        print(f"✓ Reputation checked")

        # 6. Poll for tasks (should be empty)
        task = await agent.poll_for_task(timeout=0)
        # task may be None if no tasks available
        print(f"✓ Polled for task: {task}")

        # Cleanup
        await agent.shutdown()
        print("\n✅ AI Agent lifecycle completed!")

    async def test_task_execution_simplified(self, backend_server):
        """
        Test simplified task execution flow.
        """
        import uuid
        from usmsb_agent_platform import AIAgentPlatform, Task

        agent_id = f"ai_exec_{uuid.uuid4().hex[:8]}"
        api_key = f"usmsb_exec_{uuid.uuid4().hex[:12]}"

        agent = AIAgentPlatform(
            api_key=api_key,
            agent_id=agent_id,
            base_url=backend_server
        )

        # Register
        await agent.register(
            name=f"AI Exec {agent_id}",
            capabilities=["python", "fastapi"]
        )
        print(f"✓ Agent registered for execution")

        # Publish capability
        await agent.publish_capability(
            capability="api_development",
            price=200
        )
        print(f"✓ Capability published")

        # Simulate task execution (without actual backend task)
        # In real usage, this would come from poll_for_task() or WebSocket
        mock_task = Task(
            task_id="task_mock_001",
            requester_id="requester_001",
            capability="api_development",
            context={"endpoint": "/api/users", "method": "GET"},
            price=200
        )

        # Execute task
        exec_result = await agent.execute_task(
            task_id=mock_task.task_id,
            context=mock_task.context
        )
        assert exec_result is not None
        assert exec_result["task_id"] == mock_task.task_id
        assert exec_result["status"] == "executed"
        print(f"✓ Task executed: {exec_result['status']}")

        # Submit result
        submit_result = await agent.submit_result(
            task_id=mock_task.task_id,
            result={"output": "api_response.json", "status_code": 200}
        )
        assert submit_result is not None
        assert submit_result["verification_status"] == "auto"
        assert submit_result["payment_status"] == "released"
        print(f"✓ Result submitted with auto-verification")

        await agent.shutdown()
        print("\n✅ Task execution flow completed!")

    async def test_task_callback(self, backend_server):
        """
        Test WebSocket callback registration for tasks.
        """
        import uuid
        from usmsb_agent_platform import AIAgentPlatform, Task

        agent_id = f"ai_cb_{uuid.uuid4().hex[:8]}"
        api_key = f"usmsb_cb_{uuid.uuid4().hex[:12]}"

        agent = AIAgentPlatform(
            api_key=api_key,
            agent_id=agent_id,
            base_url=backend_server
        )

        # Register callback
        received_tasks = []

        async def on_task(task: Task):
            received_tasks.append(task)
            print(f"✓ Received task via callback: {task.task_id}")

        await agent.on_task_received(on_task)
        print("✓ Task callback registered")

        # Register agent
        await agent.register(
            name=f"AI Callback {agent_id}",
            capabilities=["ml"]
        )

        # Publish
        await agent.publish_capability(
            capability="machine_learning",
            price=500
        )

        # Note: In this test environment, we can't actually receive WebSocket
        # messages, but the callback is properly registered
        print(f"✓ Agent ready with {len(agent._task_callbacks)} callback(s)")

        await agent.shutdown()
        print("\n✅ Callback registration completed!")

    async def test_pending_and_completed_tasks(self, backend_server):
        """
        Test querying pending and completed tasks.
        """
        import uuid
        from usmsb_agent_platform import AIAgentPlatform

        agent_id = f"ai_qry_{uuid.uuid4().hex[:8]}"
        api_key = f"usmsb_qry_{uuid.uuid4().hex[:12]}"

        agent = AIAgentPlatform(
            api_key=api_key,
            agent_id=agent_id,
            base_url=backend_server
        )

        await agent.register(
            name=f"AI Query {agent_id}",
            capabilities=["testing"]
        )

        # Get pending tasks
        pending = await agent.get_pending_tasks()
        assert isinstance(pending, list)
        print(f"✓ Pending tasks: {len(pending)}")

        # Get completed tasks
        completed = await agent.get_completed_tasks()
        assert isinstance(completed, list)
        print(f"✓ Completed tasks: {len(completed)}")

        await agent.shutdown()
        print("\n✅ Query methods completed!")
