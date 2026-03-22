"""
Agent Skill (TypeScript) Test Client - Provides a configured PlatformClient for E2E tests.
"""
import pytest
import uuid
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from usmsb_agent_platform import AgentPlatform


@pytest.fixture(scope="module")
def skill_base_url(backend_server):
    """Get the backend URL for Agent Skill clients."""
    return backend_server


@pytest.fixture(scope="function")
def skill_agent_demand(skill_base_url):
    """Create a demand skill agent."""
    agent_id = f"skill_demand_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_skill_demand_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def skill_agent_supply(skill_base_url):
    """Create a supply skill agent."""
    agent_id = f"skill_supply_{uuid.uuid4().hex[:8]}"
    api_key = f"usmsb_skill_supply_{uuid.uuid4().hex[:12]}"
    return agent_id, api_key


@pytest.fixture(scope="function")
def skill_client(skill_base_url, skill_agent_demand):
    """Create a configured AgentPlatform client for the demand skill agent."""
    agent_id, api_key = skill_agent_demand
    return AgentPlatform(
        base_url=skill_base_url,
        api_key=api_key,
        agent_id=agent_id,
    )


@pytest.fixture(scope="function")
def skill_supply_client(skill_base_url, skill_agent_supply):
    """Create a configured AgentPlatform client for the supply skill agent."""
    agent_id, api_key = skill_agent_supply
    return AgentPlatform(
        base_url=skill_base_url,
        api_key=api_key,
        agent_id=agent_id,
    )
