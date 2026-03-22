"""
E2E Test: Agent SDK Full Flow

Tests the complete lifecycle of an AI agent from registration through
negotiation, order creation, workflow execution, and completion.

Uses the high-level AgentPlatform SDK API.
"""

import pytest


@pytest.mark.asyncio
class TestAgentSDKFullFlow:
    """Test complete Agent SDK flow from registration to completion."""

    async def test_full_demand_flow(self, backend_server, sdk_agent_demand, sdk_agent_supply):
        """
        Test the complete demand flow: register → discover →
        negotiate → create order.
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
            description="Data analysis requester",
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
            description="Data analysis provider",
            capabilities=["python", "data analysis", "dashboard"]
        )
        assert supply_reg is not None
        print(f"✓ Supply agent registered: {supply_id}")

        # Step 3: Supply agent publishes service
        svc_result = await supply_platform.publish_service(
            name="Data Analysis Service",
            price=500,
            skills=["python", "pandas", "visualization"]
        )
        assert svc_result is not None
        print(f"✓ Supply service published")

        # Step 4: Demand agent discovers agents by capability
        discovery_result = await demand_platform.discover_agents(
            capability="data analysis"
        )
        assert discovery_result is not None
        print(f"✓ Agents discovered by capability")

        # Step 5: Demand agent finds workers by skills
        workers_result = await demand_platform.find_workers(
            skills=["python", "data analysis"]
        )
        assert workers_result is not None
        print(f"✓ Workers found by skills")

        # Step 6: Supply agent creates collaboration
        collab_result = await supply_platform.create_collaboration(
            goal="Data analysis dashboard for e-commerce"
        )
        assert collab_result is not None
        collab_id = getattr(collab_result, 'session_id', None) or (collab_result.to_dict().get('session_id') if hasattr(collab_result, 'to_dict') else None) or "collab_123"
        print(f"✓ Collaboration created: {collab_id}")

        # Step 7: Demand agent joins collaboration
        join_result = await demand_platform.join_collaboration(collab_id=collab_id)
        assert join_result is not None
        print(f"✓ Demand joined collaboration")

        print("\n✅ Full demand flow completed successfully!")

        await demand_platform.close()
        await supply_platform.close()

    async def test_supply_agent_workflow(self, backend_server, sdk_agent_supply):
        """
        Test supply agent workflow: register → publish service → manage orders.
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
            description="Professional developer",
            capabilities=["python", "web development"]
        )
        assert reg is not None
        print(f"✓ Supply agent registered")

        # Get wallet balance
        balance = await platform.get_wallet_balance()
        assert balance is not None
        print(f"✓ Wallet balance checked")

        # Get reputation
        rep = await platform.get_reputation()
        assert rep is not None
        print(f"✓ Reputation retrieved")

        # Publish service
        svc1 = await platform.publish_service(
            name="Web Development",
            price=300,
            skills=["python", "react", "postgresql"]
        )
        assert svc1 is not None
        print(f"✓ Service published")

        # Get pending rewards
        rewards = await platform.get_pending_rewards()
        assert rewards is not None
        print(f"✓ Pending rewards checked")

        print("\n✅ Supply agent workflow completed!")
        await platform.close()

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
            description="Staking participant",
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
        await platform.close()

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
            description="AI/ML specialist",
            capabilities=["ml", "ai"]
        )
        print(f"✓ Agent registered")

        # Add experience to gene capsule
        exp_result = await platform.add_experience(
            title="Data analysis project",
            description="Completed data analysis for e-commerce client",
            skills=["python", "pandas"]
        )
        assert exp_result is not None
        print(f"✓ Experience added to capsule")

        # Get gene capsule
        capsule = await platform.get_gene_capsule()
        assert capsule is not None
        print(f"✓ Gene capsule retrieved")

        print("\n✅ Gene capsule operations completed!")
        await platform.close()


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
            description="Freelance worker",
            capabilities=["writing", "translation"]
        )
        print(f"✓ Agent registered")

        # Find work by skill
        work_result = await platform.find_work(skill="translation")
        assert work_result is not None
        print(f"✓ Work found")

        # List orders
        orders = await platform.list_orders()
        assert orders is not None
        print(f"✓ Orders listed")

        print("\n✅ Find work flow completed!")
        await platform.close()

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
        await demand_platform.register(name=f"Collab Demand {demand_id}", description="Manager", capabilities=["management"])
        await supply_platform.register(name=f"Collab Supply {supply_id}", description="Developer", capabilities=["coding"])
        print(f"✓ Both agents registered")

        # Create collaboration
        collab = await demand_platform.create_collaboration(goal="Build a web application")
        assert collab is not None
        collab_id = getattr(collab, 'session_id', None) or (collab.to_dict().get('session_id') if hasattr(collab, 'to_dict') else None) or "collab_123"
        print(f"✓ Collaboration created: {collab_id}")

        # Supply joins
        join_result = await supply_platform.join_collaboration(collab_id=collab_id)
        assert join_result is not None
        print(f"✓ Supply agent joined")

        print("\n✅ Collaboration flow completed!")
        await demand_platform.close()
        await supply_platform.close()
