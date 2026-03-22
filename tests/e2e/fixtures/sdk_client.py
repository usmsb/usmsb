"""
SDK Test Client - Provides a configured Agent SDK instance for E2E tests.
"""
import pytest
import uuid


@pytest.fixture(scope="module")
def sdk_base_url(backend_server):
    """Get the backend URL for SDK clients."""
    return backend_server


@pytest.fixture(scope="function")
def sdk_agent_demand(sdk_base_url):
    """
    Create a demand agent (the one who initiates work).
    Returns (agent_id, api_key).
    """
    import asyncio
    from usmsb_agent_platform import AgentPlatform, PlatformClient

    agent_id = f"demand_agent_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_sdk_demand_{uuid.uuid4().hex[:12]}"

    return agent_id, api_key


@pytest.fixture(scope="function")
def sdk_agent_supply(sdk_base_url):
    """
    Create a supply agent (the one who provides services).
    Returns (agent_id, api_key).
    """
    agent_id = f"supply_agent_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_sdk_supply_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def sdk_client(sdk_base_url, sdk_agent_demand):
    """
    Create a configured AgentPlatform client for the demand agent.
    """
    agent_id, api_key = sdk_agent_demand
    return AgentPlatform(
        base_url=sdk_base_url,
        api_key=api_key,
        agent_id=agent_id,
    )


@pytest.fixture(scope="function")
def sdk_supply_client(sdk_base_url, sdk_agent_supply):
    """
    Create a configured AgentPlatform client for the supply agent.
    """
    agent_id, api_key = sdk_agent_supply
    return AgentPlatform(
        base_url=sdk_base_url,
        api_key=api_key,
        agent_id=agent_id,
    )
