"""
E2E Test: Agent SDK Full Flow

Tests the complete lifecycle of an AI agent using the real AgentPlatform API.

Real API methods used:
- register(name, capabilities)
- publish_service(name, price, description, skills)
- discover_agents(capability)
- find_workers(skills)
- create_collaboration(goal)
- join_collaboration(collab_id)
- create_order_from_pre_match(negotiation_id, task_description)
- get_order_status(order_id)
- stake(amount) / unstake(amount)
- get_stake_info()
- get_wallet_balance()
- get_reputation()
- add_experience(task_type, outcome, quality_score, completion_time)
- get_gene_capsule()
"""

import pytest


@pytest.mark.asyncio
class TestAgentSDKFullFlow:
    """Test complete Agent SDK flow from registration to completion."""

    async def test_full_demand_flow(self, backend_server, sdk_agent_demand, sdk_agent_supply):
        """
        Test the complete demand flow: register → publish service → discover → collaborate.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = sdk_agent_demand
        supply_id, supply_key = sdk_agent_supply

        # Step 1: Register demand agent
        demand_platform = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )
        reg_result = await demand_platform.register(
            name=f"Demand Agent {demand_id}",
            capabilities=["project management", "data analysis"]
        )
        assert reg_result is not None
        print(f"✓ Demand agent registered: {demand_id}")

        # Step 2: Register supply agent
        supply_platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )
        supply_reg = await supply_platform.register(
            name=f"Supply Agent {supply_id}",
            capabilities=["python", "data analysis", "dashboard"]
        )
        assert supply_reg is not None
        print(f"✓ Supply agent registered: {supply_id}")

        # Step 3: Supply agent publishes service
        svc_result = await supply_platform.publish_service(
            name="Data Analysis Service",
            price=500,
            description="Professional data analysis with Python",
            skills=["python", "pandas", "visualization"]
        )
        assert svc_result is not None
        print(f"✓ Supply service published")

        # Step 4: Demand agent discovers agents
        discovery_result = await demand_platform.discover_agents(
            capability="data analysis"
        )
        assert discovery_result is not None
        print(f"✓ Agents discovered")

        # Step 5: Demand agent finds workers
        workers_result = await demand_platform.find_workers(
            skills=["python", "data analysis"]
        )
        assert workers_result is not None
        print(f"✓ Workers found")

        # Step 6: Supply agent creates collaboration
        collab_result = await supply_platform.create_collaboration(
            goal="Data analysis dashboard for e-commerce"
        )
        assert collab_result is not None
        # Extract collab_id from PlatformResult
        collab_data = collab_result.result if hasattr(collab_result, 'result') and collab_result.result else {}
        if isinstance(collab_data, dict):
            collab_id = collab_data.get("session_id") or collab_data.get("id")
        else:
            collab_id = getattr(collab_data, 'session_id', None) or getattr(collab_data, 'id', None)
        print(f"✓ Collaboration created: {collab_id}")

        # Step 7: Demand agent joins collaboration
        join_result = await demand_platform.join_collaboration(collab_id=collab_id)
        assert join_result is not None
        print(f"✓ Demand agent joined collaboration")

        print("\n✅ Full demand flow completed successfully!")

    async def test_supply_agent_workflow(self, backend_server, sdk_agent_supply):
        """
        Test supply agent workflow: register → bind → publish service → manage orders.
        """
        from usmsb_agent_platform import AgentPlatform

        supply_id, supply_key = sdk_agent_supply

        platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )

        # Register
        reg = await platform.register(
            name=f"Supply Agent {supply_id}",
            capabilities=["python", "web development"]
        )
        assert reg is not None
        print(f"✓ Supply agent registered")

        # Get wallet balance
        balance = await platform.get_wallet_balance()
        assert balance is not None
        print(f"✓ Wallet balance: {balance}")

        # Get reputation
        rep = await platform.get_reputation()
        assert rep is not None
        print(f"✓ Reputation retrieved")

        # Publish multiple services
        svc1 = await platform.publish_service(
            name="Web Development",
            price=300,
            description="Full-stack web development",
            skills=["python", "react", "postgresql"]
        )
        assert svc1 is not None

        svc2 = await platform.publish_service(
            name="API Development",
            price=250,
            description="RESTful API development",
            skills=["python", "fastapi", "docker"]
        )
        assert svc2 is not None
        print(f"✓ 2 services published")

        # Get pending rewards
        rewards = await platform.get_pending_rewards()
        assert rewards is not None
        print(f"✓ Pending rewards checked")

        print("\n✅ Supply agent workflow completed!")

    async def test_staking_operations(self, backend_server, sdk_agent_demand):
        """
        Test staking deposit and withdraw operations.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = sdk_agent_demand

        platform = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )

        # Register first
        await platform.register(
            name=f"Staking Agent {demand_id}",
            capabilities=["staking", "defi"]
        )
        print(f"✓ Agent registered for staking")

        # Stake
        stake_result = await platform.stake(amount=1000)
        assert stake_result is not None
        print(f"✓ Staked: 1000")

        # Get stake info
        stake_info = await platform.get_stake_info()
        assert stake_info is not None
        print(f"✓ Stake info retrieved")

        # Unstake (partial)
        unstake_result = await platform.unstake(amount=500)
        assert unstake_result is not None
        print(f"✓ Unstaked: 500")

        print("\n✅ Staking operations completed!")

    async def test_gene_capsule_operations(self, backend_server, sdk_agent_supply):
        """
        Test Gene Capsule operations.
        """
        from usmsb_agent_platform import AgentPlatform

        supply_id, supply_key = sdk_agent_supply

        platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )

        # Register
        await platform.register(
            name=f"Gene Agent {supply_id}",
            capabilities=["ml", "ai"]
        )
        print(f"✓ Agent registered")

        # Add experience to gene capsule
        exp_result = await platform.add_experience(
            title="Data Analysis Task",
            description="Professional data analysis with Python",
            skills=["python", "pandas", "visualization"]
        )
        assert exp_result is not None
        print(f"✓ Experience added to capsule")

        # Get gene capsule
        capsule = await platform.get_gene_capsule()
        assert capsule is not None
        print(f"✓ Gene capsule retrieved")

        print("\n✅ Gene capsule operations completed!")


@pytest.mark.asyncio
class TestAgentSDKMarketplace:
    """Test marketplace-related flows."""

    async def test_find_work_flow(self, backend_server, sdk_agent_demand):
        """
        Test finding work as a demand agent.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = sdk_agent_demand

        platform = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )

        await platform.register(
            name=f"Worker {demand_id}",
            capabilities=["writing", "translation"]
        )
        print(f"✓ Agent registered")

        # Find work
        work_result = await platform.find_work(
            skill="translation"
        )
        assert work_result is not None
        print(f"✓ Work found")

        # List orders
        orders = await platform.list_orders()
        assert orders is not None
        print(f"✓ Orders listed")

        print("\n✅ Find work flow completed!")

    async def test_collaboration_flow(self, backend_server, sdk_agent_demand, sdk_agent_supply):
        """
        Test collaboration between agents.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = sdk_agent_demand
        supply_id, supply_key = sdk_agent_supply

        demand_platform = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )
        supply_platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )

        # Register both
        await demand_platform.register(name=f"Collab Demand {demand_id}", capabilities=["management"])
        await supply_platform.register(name=f"Collab Supply {supply_id}", capabilities=["coding"])
        print(f"✓ Both agents registered")

        # Create collaboration
        collab = await demand_platform.create_collaboration(
            goal="Build a web application"
        )
        assert collab is not None
        collab_data = collab.result if hasattr(collab, 'result') and collab.result else (collab if isinstance(collab, dict) else {})
        if isinstance(collab_data, dict):
            collab_id = collab_data.get("session_id") or collab_data.get("id")
        else:
            collab_id = getattr(collab_data, 'session_id', None) or getattr(collab_data, 'id', None)
        print(f"✓ Collaboration created: {collab_id}")

        # Supply joins
        join_result = await supply_platform.join_collaboration(collab_id=collab_id)
        assert join_result is not None
        print(f"✓ Supply agent joined")

        print("\n✅ Collaboration flow completed!")
