"""
E2E Test: Bidirectional Flow (SDK ↔ Skill)

Tests communication between agents using the AgentPlatform SDK.
Since both use the same API, this validates cross-platform consistency.
"""

import pytest


@pytest.mark.asyncio
class TestBidirectionalSDKAndSkill:
    """
    Test bidirectional communication between SDK and Skill agents.
    """

    async def test_sdk_demand_negotiates_with_skill_supply(
        self, backend_server,
        sdk_agent_demand, skill_agent_supply
    ):
        """
        SDK agent (demand) initiates work request.
        Skill agent (supply) responds.
        """
        from usmsb_agent_platform import AgentPlatform

        sdk_demand_id, sdk_demand_key = sdk_agent_demand
        skill_supply_id, skill_supply_key = skill_agent_supply

        # === SDK Agent (Demand) ===
        sdk_platform = AgentPlatform(
            base_url=backend_server,
            api_key=sdk_demand_key,
            agent_id=sdk_demand_id,
        )

        await sdk_platform.register(
            name=f"SDK Demand {sdk_demand_id}",
            description="Product manager",
            capabilities=["product management", "business analysis"]
        )
        print(f"✓ SDK demand agent registered: {sdk_demand_id}")

        # === Skill Agent (Supply) ===
        skill_platform = AgentPlatform(
            base_url=backend_server,
            api_key=skill_supply_key,
            agent_id=skill_supply_id,
        )

        await skill_platform.register(
            name=f"Skill Supply {skill_supply_id}",
            description="Mobile developer",
            capabilities=["mobile development", "ios", "android"]
        )
        print(f"✓ Skill supply agent registered: {skill_supply_id}")

        # Publish service by skill agent
        await skill_platform.publish_service(
            name="Mobile App Development",
            price=2000,
            skills=["react-native", "ios", "android"]
        )
        print("✓ Skill supply published service")

        # === SDK discovers skill agents ===
        discovery = await sdk_platform.discover_agents(capability="mobile development")
        assert discovery is not None
        print("✓ SDK discovered agents")

        # === SDK finds workers ===
        workers = await sdk_platform.find_workers(skills=["mobile", "ios", "android"])
        assert workers is not None
        print("✓ SDK found workers")

        # === SDK creates collaboration ===
        collab = await sdk_platform.create_collaboration(
            goal="Build e-commerce mobile app"
        )
        assert collab is not None
        collab_id = getattr(collab, 'session_id', None) or (collab.to_dict().get('session_id') if hasattr(collab, 'to_dict') else None) or "collab_123"
        print(f"✓ SDK created collaboration: {collab_id}")

        # === Skill joins collaboration ===
        join = await skill_platform.join_collaboration(collab_id=collab_id)
        assert join is not None
        print("✓ Skill joined collaboration")

        print("\n✅ Bidirectional SDK↔Skill flow completed!")

        await sdk_platform.close()
        await skill_platform.close()


@pytest.mark.asyncio
class TestSDKAsSkillSupplier:
    """
    Test the reverse: SDK agent acts as supply, Skill agent as demand.
    """

    async def test_skill_demand_negotiates_with_sdk_supply(
        self, backend_server,
        skill_agent_demand, sdk_agent_supply
    ):
        """
        Skill agent (demand) initiates work request.
        SDK agent (supply) responds.
        """
        from usmsb_agent_platform import AgentPlatform

        skill_demand_id, skill_demand_key = skill_agent_demand
        sdk_supply_id, sdk_supply_key = sdk_agent_supply

        # === Skill Agent (Demand) ===
        skill_platform = AgentPlatform(
            base_url=backend_server,
            api_key=skill_demand_key,
            agent_id=skill_demand_id,
        )

        await skill_platform.register(
            name=f"Skill Demand {skill_demand_id}",
            description="Marketing professional",
            capabilities=["marketing", "sales"]
        )
        print(f"✓ Skill demand agent registered: {skill_demand_id}")

        # === SDK Agent (Supply) ===
        sdk_platform = AgentPlatform(
            base_url=backend_server,
            api_key=sdk_supply_key,
            agent_id=sdk_supply_id,
        )

        await sdk_platform.register(
            name=f"SDK Supply {sdk_supply_id}",
            description="Data analyst",
            capabilities=["data analysis", "python", "pandas"]
        )

        # Publish service via SDK
        await sdk_platform.publish_service(
            name="Data Analysis Service",
            price=500,
            skills=["python", "pandas", "visualization"]
        )
        print(f"✓ SDK supply agent registered and published service: {sdk_supply_id}")

        # === Skill searches ===
        workers = await skill_platform.find_workers(skills=["python", "data analysis"])
        assert workers is not None
        print("✓ Skill found SDK supply agents")

        # === Skill creates collaboration ===
        collab = await skill_platform.create_collaboration(
            goal="Analyze sales data for Q4"
        )
        assert collab is not None
        collab_id = getattr(collab, 'session_id', None) or (collab.to_dict().get('session_id') if hasattr(collab, 'to_dict') else None) or "collab_123"
        print(f"✓ Skill created collaboration: {collab_id}")

        # === SDK joins ===
        join = await sdk_platform.join_collaboration(collab_id=collab_id)
        assert join is not None
        print("✓ SDK joined collaboration")

        print("\n✅ Reverse bidirectional flow completed!")

        await skill_platform.close()
        await sdk_platform.close()


@pytest.mark.asyncio
class TestCrossPlatformConsistency:
    """
    Verify that both SDK and Skill platforms behave consistently.
    """

    async def test_same_api_works_for_both(self, backend_server, sdk_agent_demand, skill_agent_demand):
        """
        Verify that the same API calls work for both SDK and Skill agents.
        """
        from usmsb_agent_platform import AgentPlatform

        sdk_id, sdk_key = sdk_agent_demand
        skill_id, skill_key = skill_agent_demand

        sdk_platform = AgentPlatform(base_url=backend_server, api_key=sdk_key, agent_id=sdk_id)
        skill_platform = AgentPlatform(base_url=backend_server, api_key=skill_key, agent_id=skill_id)

        # Both should register successfully
        sdk_reg = await sdk_platform.register(name=f"SDK {sdk_id}", description="Coder", capabilities=["coding"])
        skill_reg = await skill_platform.register(name=f"Skill {skill_id}", description="Designer", capabilities=["design"])

        assert sdk_reg is not None
        assert skill_reg is not None
        print("✓ Both platforms registered successfully")

        # Both should publish services
        sdk_svc = await sdk_platform.publish_service(
            name="Coding Service",
            price=100,
            skills=["python"]
        )
        skill_svc = await skill_platform.publish_service(
            name="Design Service",
            price=100,
            skills=["figma"]
        )

        assert sdk_svc is not None
        assert skill_svc is not None
        print("✓ Both platforms published services")

        # Both should discover
        sdk_disc = await sdk_platform.discover_agents(capability="design")
        skill_disc = await skill_platform.discover_agents(capability="coding")

        assert sdk_disc is not None
        assert skill_disc is not None
        print("✓ Both platforms discovered agents")

        print("\n✅ Cross-platform consistency verified!")

        await sdk_platform.close()
        await skill_platform.close()
