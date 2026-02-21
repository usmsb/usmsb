"""
Utility functions for REST API services.
"""

import json
import logging
from typing import Any

from usmsb_sdk.core.elements import Agent, AgentType

logger = logging.getLogger(__name__)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    if default is None:
        default = {} if json_str and json_str.strip().startswith('{') else []

    if not json_str:
        return default

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON: {e}")
        return default


def safe_json_loads_deep(value: Any, default: Any = None) -> Any:
    """
    Safely parse JSON string, handling double-encoded JSON.

    Args:
        value: Value to parse (may be string, already parsed, or None)
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    if default is None:
        default = []

    if value is None:
        return default

    # Already a list or dict
    if isinstance(value, (list, dict)):
        return value

    # Try to parse string
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            # Handle double-encoded JSON
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    pass
            return parsed if isinstance(parsed, (list, dict)) else default
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {e}")
            return default

    return default


def create_agent_from_db_data(agent_data: dict) -> Agent:
    """
    Create an Agent object from database data.

    Args:
        agent_data: Dictionary containing agent data from database

    Returns:
        Agent object
    """
    try:
        agent_type = AgentType(agent_data.get('type', 'ai_agent'))
    except ValueError:
        agent_type = AgentType.AI_AGENT

    return Agent(
        id=agent_data['id'],
        name=agent_data['name'],
        type=agent_type,
        capabilities=safe_json_loads(agent_data.get('capabilities', '[]'), []),
        state=safe_json_loads(agent_data.get('state', '{}'), {}),
    )
