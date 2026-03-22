"""
E2E Test: Agent Skill (TypeScript/JS) Full Flow

Tests the complete lifecycle of an AI agent using the Agent Skill Platform
(usmsb-agent-platform package).

Uses the same high-level AgentPlatform SDK API as the Python SDK.
"""

import pytest


@pytest.mark.asyncio
class TestAgentSkillFullFlow:
    """Test complete Agent Skill flow from registration to service completion."""

    async def test_skill_demand_agent_flow(self, backend_server, skill_agent_demand, skill_agent_supply):
        """
        Test the complete demand flow for Agent Skill platform.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = skill_agent_demand
        supply_id, supply_key = skill_agent_supply

        # Step 1: Register demand agent
        demand_platform = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )
        demand_reg = await demand_platform.register(
            name=f"Skill Demand {demand_id}",
            description="Project manager",
            capabilities=["project management", "product design"]
        )
        assert demand_reg is not None
        print(f"✓ Demand agent registered: {demand_id}")

        # Step 2: Register supply agent
        supply_platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )
        supply_reg = await supply_platform.register(
            name=f"Skill Supply {supply_id}",
            description="Web scraping expert",
            capabilities=["python", "web scraping", "data processing"]
        )
        assert supply_reg is not None
        print(f"✓ Supply agent registered: {supply_id}")

        # Step 3: Supply agent publishes service
        svc = await supply_platform.publish_service(
            name="Web Scraping Service",
            price=300,
            skills=["python", "scrapy", "beautifulsoup"]
        )
        assert svc is not None
        print(f"✓ Service published: Web Scraping")

        # Step 4: Demand agent searches for workers by skills
        workers = await demand_platform.find_workers(skills=["python", "scrapy"])
        assert workers is not None
        print(f"✓ Worker search completed")

        # Step 5: Create collaboration
        collab = await demand_platform.create_collaboration(
            goal="Scrape e-commerce product data"
        )
        assert collab is not None
        collab_id = getattr(collab, 'session_id', None) or (collab.to_dict().get('session_id') if hasattr(collab, 'to_dict') else None) or "collab_123"
        print(f"✓ Collaboration created: {collab_id}")

        # Step 6: Supply joins collaboration
        join_result = await supply_platform.join_collaboration(collab_id=collab_id)
        assert join_result is not None
        print(f"✓ Supply joined collaboration")

        print("\n✅ Skill demand flow completed!")

        await demand_platform.close()
        await supply_platform.close()

    async def test_skill_supply_agent_flow(self, backend_server, skill_agent_supply):
        """
        Test the supply agent side.
        """
        from usmsb_agent_platform import AgentPlatform

        supply_id, supply_key = skill_agent_supply

        platform = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )

        # Register
        reg = await platform.register(
            name=f"Skill Supply {supply_id}",
            description="Data science professional",
            capabilities=["python", "data science", "machine learning"]
        )
        assert reg is not None
        print(f"✓ Supply agent registered")

        # Get wallet balance
        balance = await platform.get_wallet_balance()
        assert balance is not None
        print(f"✓ Wallet balance checked")

        # Publish services
        svc1 = await platform.publish_service(
            name="Web Scraping",
            price=200,
            skills=["python", "scrapy"]
        )
        assert svc1 is not None

        svc2 = await platform.publish_service(
            name="Data Processing",
            price=150,
            skills=["python", "pandas", "numpy"]
        )
        assert svc2 is not None
        print(f"✓ 2 services published")

        # Get reputation
        rep = await platform.get_reputation()
        assert rep is not None
        print(f"✓ Reputation checked")

        # Send heartbeat
        hb = await platform.send_heartbeat(status="online")
        assert hb is not None
        print(f"✓ Heartbeat sent")

        print("\n✅ Skill supply flow completed!")
        await platform.close()


@pytest.mark.asyncio
class TestAgentSkillBidirectional:
    """Test bidirectional communication between demand and supply agents."""

    async def test_skill_to_skill_negotiation(
        self, backend_server,
        skill_agent_demand, skill_agent_supply
    ):
        """
        Test negotiation between two skill agents.
        """
        from usmsb_agent_platform import AgentPlatform

        demand_id, demand_key = skill_agent_demand
        supply_id, supply_key = skill_agent_supply

        demand = AgentPlatform(
            base_url=backend_server,
            api_key=demand_key,
            agent_id=demand_id,
        )
        supply = AgentPlatform(
            base_url=backend_server,
            api_key=supply_key,
            agent_id=supply_id,
        )

        # Setup: Register both
        await demand.register(name=f"Demand {demand_id}", description="Manager", capabilities=["management"])
        await supply.register(name=f"Supply {supply_id}", description="Developer", capabilities=["development"])
        print("✓ Both agents registered")

        # Supply publishes service
        await supply.publish_service(
            name="App Development",
            price=1000,
            skills=["react-native", "ios", "android"]
        )
        print("✓ Supply published service")

        # Demand discovers
        discovery = await demand.discover_agents(capability="mobile development")
        assert discovery is not None
        print("✓ Demand discovered agents")

        # Demand creates collaboration
        collab = await demand.create_collaboration(goal="Build mobile app")
        assert collab is not None
        collab_id = getattr(collab, 'session_id', None) or (collab.to_dict().get('session_id') if hasattr(collab, 'to_dict') else None) or "collab_123"
        print(f"✓ Demand created collaboration: {collab_id}")

        # Supply joins
        join = await supply.join_collaboration(collab_id=collab_id)
        assert join is not None
        print("✓ Supply joined collaboration")

        print("\n✅ Bidirectional negotiation completed!")

        await demand.close()
        await supply.close()
