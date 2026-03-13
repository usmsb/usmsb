"""
Agent SDK Templates

This module provides Docker templates and configuration examples
for deploying agents in containerized environments.

Available Templates:
- Dockerfile.agent: Multi-stage Dockerfile for agent deployment
- docker-compose.yml: Complete orchestration with platform and multiple agents
- config.yaml.example: Comprehensive configuration example
- requirements-agent.txt: Python dependencies for agents
- agent_entrypoint.py: Auto-registration script for Docker agents

Usage:
    # Build an agent image
    docker build -f src/usmsb_sdk/agent_sdk/templates/Dockerfile.agent -t my-agent .

    # Run with docker-compose
    docker-compose -f src/usmsb_sdk/agent_sdk/templates/docker-compose.yml up -d

    # Create config from example
    cp src/usmsb_sdk/agent_sdk/templates/config.yaml.example config/my-agent.yaml
"""

import os
from pathlib import Path

# Template directory path
TEMPLATES_DIR = Path(__file__).parent

# Available template files
TEMPLATE_FILES = {
    "dockerfile": "Dockerfile.agent",
    "docker_compose": "docker-compose.yml",
    "config_example": "config.yaml.example",
    "requirements": "requirements-agent.txt",
    "entrypoint": "agent_entrypoint.py",
}


def get_template_path(template_name: str) -> Path:
    """
    Get the full path to a template file.

    Args:
        template_name: Name of the template (e.g., 'dockerfile', 'config_example')

    Returns:
        Path to the template file

    Raises:
        ValueError: If template name is not found
    """
    if template_name not in TEMPLATE_FILES:
        raise ValueError(
            f"Unknown template: {template_name}. "
            f"Available: {list(TEMPLATE_FILES.keys())}"
        )

    return TEMPLATES_DIR / TEMPLATE_FILES[template_name]


def get_template_content(template_name: str) -> str:
    """
    Get the content of a template file.

    Args:
        template_name: Name of the template

    Returns:
        Template file content as string
    """
    path = get_template_path(template_name)
    return path.read_text(encoding="utf-8")


def copy_template(template_name: str, destination: Path) -> Path:
    """
    Copy a template file to a destination.

    Args:
        template_name: Name of the template
        destination: Destination path (file or directory)

    Returns:
        Path to the copied file
    """
    source = get_template_path(template_name)

    if destination.is_dir():
        destination = destination / TEMPLATE_FILES[template_name]

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    return destination


__all__ = [
    "TEMPLATES_DIR",
    "TEMPLATE_FILES",
    "get_template_path",
    "get_template_content",
    "copy_template",
]
