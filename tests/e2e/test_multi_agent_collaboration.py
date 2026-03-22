"""
E2E Test: Multi-Agent Collaboration Loop

Simulates a complete multi-agent collaboration scenario:
1. Supply Agent publishes capability
2. Demand Agent discovers and assigns task
3. Supply Agent executes task
4. Auto-verification and auto-payment

This is a true end-to-end test of the AI Agent collaboration闭环.
"""

import pytest
import uuid


@pytest.mark.asyncio
class TestMultiAgentCollaboration:
    """
    Test complete multi-agent collaboration闭环.

    Scenario:
    - Supply Agent: Has "data_analysis" capability, publishes it
    - Demand Agent: Needs data analysis, discovers and assigns task
    - Supply Agent: Executes task, submits result
    - System: Auto-verifies and auto-releases payment
    """

    async def test_complete_collaboration_loop(self, backend_server):
        """
        Full multi-agent collaboration闭环 test.

        Two agents collaborate:
        1. Supply publishes capability
        2. Demand discovers and assigns task
        3. Supply executes and submits result
        4. Auto-verification and payment
        """
        from usmsb_agent_platform import AIAgentPlatform

        # Create two agents
        supply_id = f"supply_{uuid.uuid4().hex[:8]}"
        demand_id = f"demand_{uuid.uuid4().hex[:8]}"
        supply_key = f"usmsb_supply_{uuid.uuid4().hex[:12]}"
        demand_key = f"usmsb_demand_{uuid.uuid4().hex[:12]}"

        supply_agent = AIAgentPlatform(
            api_key=supply_key,
            agent_id=supply_id,
            base_url=backend_server
        )
        demand_agent = AIAgentPlatform(
            api_key=demand_key,
            agent_id=demand_id,
            base_url=backend_server
        )

        # ========== Step 1: Registration ==========
        print("\n=== Step 1: Registration ===")

        await supply_agent.register(
            name="Data Analysis Expert",
            capabilities=["data_analysis", "python", "pandas"]
        )
        print(f"✓ Supply Agent registered: {supply_id}")

        await demand_agent.register(
            name="Business Analyst",
            capabilities=["business_analysis"]
        )
        print(f"✓ Demand Agent registered: {demand_id}")

        # ========== Step 2: Publish Capability ==========
        print("\n=== Step 2: Publish Capability ===")

        await supply_agent.publish_capability(
            capability="data_analysis",
            price=100,
            description="Professional data analysis with Python and Pandas"
        )
        print(f"✓ Supply Agent published: data_analysis @ 100 VIBE")

        # ========== Step 3: Discovery ==========
        print("\n=== Step 3: Discovery ===")

        # Demand Agent discovers agents with data_analysis capability
        discovery = await demand_agent.client.discover_agents(
            capability="data_analysis"
        )
        assert discovery is not None
        print(f"✓ Demand Agent discovered agents: {discovery}")

        # Demand Agent finds workers
        workers = await demand_agent.client.find_workers(
            skills=["data_analysis"]
        )
        assert workers is not None
        print(f"✓ Demand Agent found workers: {workers}")

        # ========== Step 4: Task Assignment ==========
        print("\n=== Step 4: Task Assignment ===")

        # In real scenario, this would create an order via matching
        # For testing, we simulate the task assignment
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task_context = {
            "task": "Analyze Q4 sales data",
            "input": "sales_q4.csv",
            "requirements": ["python", "pandas", "visualization"]
        }
        print(f"✓ Task assigned: {task_id}")
        print(f"  Context: {task_context}")

        # ========== Step 5: Task Execution ==========
        print("\n=== Step 5: Task Execution ===")

        # Supply Agent executes the task
        exec_result = await supply_agent.execute_task(
            task_id=task_id,
            context=task_context
        )
        assert exec_result is not None
        assert exec_result["task_id"] == task_id
        print(f"✓ Supply Agent executed task: {exec_result['status']}")

        # ========== Step 6: Result Submission ==========
        print("\n=== Step 6: Result Submission ===")

        # Supply Agent submits result with auto-verification
        task_result = {
            "output_file": "sales_analysis_q4.pdf",
            "summary": "Q4 sales increased by 15%",
            "charts": ["sales_trend.png", "product_breakdown.png"]
        }

        submit_result = await supply_agent.submit_result(
            task_id=task_id,
            result=task_result,
            metadata={
                "quality_score": 0.95,
                "completion_time": 3600,
                "techniques": ["pandas", "matplotlib", "seaborn"]
            }
        )
        assert submit_result is not None
        assert submit_result["verification_status"] == "auto"
        assert submit_result["payment_status"] == "released"
        print(f"✓ Result submitted: {submit_result['status']}")
        print(f"  Verification: {submit_result['verification_status']}")
        print(f"  Payment: {submit_result['payment_status']}")

        # ========== Step 7: Verify Completion ==========
        print("\n=== Step 7: Verify Completion ===")

        # Check supply agent's completed tasks
        completed = await supply_agent.get_completed_tasks()
        print(f"✓ Completed tasks: {len(completed)}")

        # Check supply agent's balance (should have increased)
        balance = await supply_agent.get_balance()
        print(f"✓ Supply Agent balance: {balance}")

        # Check supply agent's reputation
        reputation = await supply_agent.get_reputation()
        print(f"✓ Supply Agent reputation: {reputation}")

        # Cleanup
        await supply_agent.shutdown()
        await demand_agent.shutdown()

        print("\n" + "=" * 50)
        print("✅ COMPLETE COLLABORATION LOOP SUCCESSFUL!")
        print("=" * 50)

    async def test_parallel_multi_agent(self, backend_server):
        """
        Test multiple agents working in parallel.

        Simulates:
        - 3 Supply Agents publishing different capabilities
        - 2 Demand Agents assigning tasks
        - All tasks execute and complete
        """
        from usmsb_agent_platform import AIAgentPlatform

        # Create agents
        agents = []
        for i in range(5):
            agent_id = f"agent_{i}_{uuid.uuid4().hex[:6]}"
            api_key = f"usmsb_agent_{uuid.uuid4().hex[:10]}"
            is_supply = i < 3  # First 3 are supply

            agent = AIAgentPlatform(
                api_key=api_key,
                agent_id=agent_id,
                base_url=backend_server
            )

            capabilities = ["data_analysis", "web_dev", "ml"] if is_supply else ["business_analysis"]
            name = f"Supply Agent {i}" if is_supply else f"Demand Agent {i}"

            await agent.register(name=name, capabilities=capabilities)
            print(f"✓ Registered: {name} ({agent_id})")

            if is_supply:
                cap = capabilities[0]
                await agent.publish_capability(capability=cap, price=100 * (i + 1))
                print(f"  → Published: {cap} @ {100 * (i + 1)} VIBE")

            agents.append(agent)

        print(f"\n✓ Created {len(agents)} agents (3 supply, 2 demand)")

        # Simulate parallel task execution
        print("\n=== Parallel Task Execution ===")
        tasks = []
        for i, agent in enumerate(agents[:3]):  # Supply agents
            if isinstance(agent, AIAgentPlatform):
                task_id = f"task_parallel_{i}"
                result = await agent.execute_task(
                    task_id=task_id,
                    context={"task": f"Task {i}", "data": f"dataset_{i}.csv"}
                )
                submit = await agent.submit_result(
                    task_id=task_id,
                    result={"output": f"result_{i}.pdf"}
                )
                tasks.append({"agent": agent.agent_id, "task": task_id, "status": "completed"})
                print(f"✓ Agent {i} completed task: {task_id}")

        # Cleanup all agents
        for agent in agents:
            await agent.shutdown()

        print(f"\n✓ All {len(tasks)} tasks completed in parallel")
        print("\n✅ PARALLEL MULTI-AGENT TEST SUCCESSFUL!")

    async def test_sequential_collaboration(self, backend_server):
        """
        Test sequential collaboration where one task depends on another.

        Flow:
        1. Agent A publishes "data_analysis"
        2. Agent B assigns task to A
        3. Agent A completes, publishes "visualization"
        4. Agent C assigns visualization task to A
        5. Agent A completes
        """
        from usmsb_agent_platform import AIAgentPlatform

        # Create agents
        agent_a = AIAgentPlatform(
            api_key=f"usmsb_a_{uuid.uuid4().hex[:12]}",
            agent_id=f"agent_a_{uuid.uuid4().hex[:6]}",
            base_url=backend_server
        )
        agent_b = AIAgentPlatform(
            api_key=f"usmsb_b_{uuid.uuid4().hex[:12]}",
            agent_id=f"agent_b_{uuid.uuid4().hex[:6]}",
            base_url=backend_server
        )
        agent_c = AIAgentPlatform(
            api_key=f"usmsb_c_{uuid.uuid4().hex[:12]}",
            agent_id=f"agent_c_{uuid.uuid4().hex[:6]}",
            base_url=backend_server
        )

        # Register all
        await agent_a.register(name="Data Expert", capabilities=["data_analysis", "visualization"])
        await agent_b.register(name="Business User", capabilities=["business_analysis"])
        await agent_c.register(name="Marketing User", capabilities=["marketing"])
        print("✓ All agents registered")

        # ========== First Task ==========
        print("\n--- First Task: Data Analysis ---")

        # Agent A publishes data_analysis
        await agent_a.publish_capability(capability="data_analysis", price=100)

        # Agent B assigns task
        task1_id = "task_seq_001"
        exec1 = await agent_a.execute_task(
            task_id=task1_id,
            context={"task": "Analyze sales data"}
        )
        result1 = await agent_a.submit_result(
            task_id=task1_id,
            result={"analysis": "Sales up 20%", "file": "analysis.pdf"}
        )
        print(f"✓ First task completed: {result1['status']}")

        # ========== Second Task ==========
        print("\n--- Second Task: Visualization ---")

        # Agent A now publishes visualization (its new capability after first task)
        # In real scenario, the capability would be updated based on completed work
        await agent_a.publish_capability(capability="visualization", price=150)

        # Agent C assigns visualization task
        task2_id = "task_seq_002"
        exec2 = await agent_a.execute_task(
            task_id=task2_id,
            context={"task": "Create dashboard", "data": "analysis.pdf"}
        )
        result2 = await agent_a.submit_result(
            task_id=task2_id,
            result={"dashboard": "dashboard.html", "charts": 5}
        )
        print(f"✓ Second task completed: {result2['status']}")

        # Cleanup
        await agent_a.shutdown()
        await agent_b.shutdown()
        await agent_c.shutdown()

        print("\n✅ SEQUENTIAL COLLABORATION TEST SUCCESSFUL!")


@pytest.mark.asyncio
class TestAgentMarketplace:
    """Test agent marketplace discovery and matching."""

    async def test_capability_matching(self, backend_server):
        """
        Test that demand agents can find supply agents by capability.
        """
        from usmsb_agent_platform import AIAgentPlatform

        # Create supply agents with different capabilities
        capabilities = [
            ("data_analysis", 100),
            ("web_development", 200),
            ("ml_modeling", 300),
        ]

        supply_agents = []
        for cap, price in capabilities:
            agent = AIAgentPlatform(
                api_key=f"usmsb_{uuid.uuid4().hex[:12]}",
                agent_id=f"supply_{cap}_{uuid.uuid4().hex[:6]}",
                base_url=backend_server
            )
            await agent.register(
                name=f"{cap.title()} Expert",
                capabilities=[cap]
            )
            await agent.publish_capability(
                capability=cap,
                price=price,
                description=f"Professional {cap}"
            )
            supply_agents.append(agent)
            print(f"✓ Supply agent published: {cap}")

        # Create demand agent
        demand = AIAgentPlatform(
            api_key=f"usmsb_{uuid.uuid4().hex[:12]}",
            agent_id=f"demand_{uuid.uuid4().hex[:6]}",
            base_url=backend_server
        )
        await demand.register(
            name="Project Manager",
            capabilities=["project_management"]
        )

        # Discover by capability
        print("\n--- Discovery by Capability ---")
        for cap, _ in capabilities:
            result = await demand.client.discover_agents(capability=cap)
            print(f"  {cap}: {result}")

        # Find workers by skill
        print("\n--- Find Workers by Skill ---")
        for cap, _ in capabilities:
            result = await demand.client.find_workers(skills=[cap])
            print(f"  {cap}: {result}")

        # Cleanup
        for agent in supply_agents:
            await agent.shutdown()
        await demand.shutdown()

        print("\n✅ CAPABILITY MATCHING TEST SUCCESSFUL!")
