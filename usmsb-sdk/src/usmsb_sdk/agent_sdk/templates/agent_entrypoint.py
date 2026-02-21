#!/usr/bin/env python3
"""
Auto-Registration Script for Docker Agents

This script is the entrypoint for Docker-based agents.
It handles:
- Loading configuration from environment/files
- Auto-registration with the platform
- Starting the agent
- Graceful shutdown
"""

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Optional

import yaml

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from usmsb_sdk.agent_sdk import (
    BaseAgent,
    AgentConfig,
    SkillDefinition,
    SkillParameter,
    CapabilityDefinition,
    Message,
    MessageType,
    Session,
)


# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent-entrypoint")


class DockerAgent(BaseAgent):
    """
    A configurable agent that loads skills and capabilities from config.
    """

    async def initialize(self) -> None:
        """Initialize the agent."""
        logger.info(f"Initializing agent: {self.name}")
        logger.info(f"Agent ID: {self.agent_id}")
        logger.info(f"Version: {self.version}")

        # Log capabilities
        if self.capabilities:
            logger.info(f"Capabilities: {[c.name for c in self.capabilities]}")

        # Log skills
        if self.skills:
            logger.info(f"Skills: {[s.name for s in self.skills]}")

        # Perform any custom initialization here
        # e.g., load ML models, connect to databases, etc.

    async def handle_message(self, message: Message, session: Optional[Session] = None) -> Optional[Message]:
        """Handle incoming messages."""
        logger.info(f"Received message from {message.sender_id}: {message.type.value}")

        # Handle different message types
        if message.type == MessageType.SKILL_CALL:
            return await self._handle_skill_call(message)
        elif message.type == MessageType.REQUEST:
            return await self._handle_request(message)
        elif message.type == MessageType.BROADCAST:
            await self._handle_broadcast(message)
            return None
        else:
            logger.debug(f"Unhandled message type: {message.type}")
            return None

    async def execute_skill(self, skill_name: str, params: dict) -> any:
        """Execute a skill."""
        logger.info(f"Executing skill: {skill_name} with params: {params}")

        # Check if skill exists
        if skill_name not in self._skills:
            raise ValueError(f"Unknown skill: {skill_name}")

        # Execute the skill based on its name
        # Override this method or register skill handlers for custom behavior
        skill = self._skills[skill_name]

        # Default skill implementations (override in subclass)
        if skill_name == "ping":
            return {"status": "pong", "agent_id": self.agent_id}
        elif skill_name == "info":
            return self.to_dict()
        elif skill_name == "health":
            return await self._perform_health_check()
        else:
            # Generic skill execution - override this in your agent
            logger.warning(f"No implementation for skill: {skill_name}")
            return {"status": "not_implemented", "skill": skill_name}

    async def shutdown(self) -> None:
        """Cleanup resources."""
        logger.info(f"Shutting down agent: {self.name}")

        # Perform cleanup here
        # e.g., save state, close connections, etc.

    async def _handle_skill_call(self, message: Message) -> Message:
        """Handle a skill call message."""
        try:
            content = message.content
            skill_name = content.get("skill")
            params = content.get("params", {})

            result = await self.call_skill(skill_name, params)

            return message.create_response({
                "status": "success",
                "result": result,
            })
        except Exception as e:
            logger.error(f"Skill call error: {e}")
            return message.create_error(str(e))

    async def _handle_request(self, message: Message) -> Message:
        """Handle a request message."""
        # Default request handling
        content = message.content
        action = content.get("action", "unknown")

        if action == "ping":
            return message.create_response({"status": "pong"})
        elif action == "info":
            return message.create_response(self.to_dict())
        elif action == "health":
            health = await self._perform_health_check()
            return message.create_response(health)
        else:
            return message.create_error(f"Unknown action: {action}")

    async def _handle_broadcast(self, message: Message) -> None:
        """Handle a broadcast message."""
        logger.info(f"Received broadcast: {message.content}")
        # Handle broadcast messages as needed


def load_config_from_env() -> AgentConfig:
    """Load agent configuration from environment variables."""
    name = os.getenv("AGENT_NAME", "docker-agent")
    description = os.getenv("AGENT_DESCRIPTION", "A Docker-based agent")
    version = os.getenv("AGENT_VERSION", "1.0.0")
    platform_endpoint = os.getenv("PLATFORM_ENDPOINT", "http://localhost:8000")

    # Load config file if specified
    config_path = os.getenv("AGENT_CONFIG")
    if config_path and Path(config_path).exists():
        return load_config_from_file(config_path)

    # Create basic config from environment
    from usmsb_sdk.agent_sdk.agent_config import (
        NetworkConfig,
        SecurityConfig,
        ProtocolConfig,
        ProtocolType,
    )

    config = AgentConfig(
        name=name,
        description=description,
        version=version,
        network=NetworkConfig(
            platform_endpoints=[platform_endpoint],
        ),
        security=SecurityConfig(
            api_key=os.getenv("API_KEY"),
            jwt_secret=os.getenv("JWT_SECRET"),
        ),
    )

    # Add basic skills
    config.add_skill(SkillDefinition(
        name="ping",
        description="Ping the agent to check availability",
        parameters=[],
        returns="object",
        tags=["system"],
    ))

    config.add_skill(SkillDefinition(
        name="info",
        description="Get agent information",
        parameters=[],
        returns="object",
        tags=["system"],
    ))

    config.add_skill(SkillDefinition(
        name="health",
        description="Get agent health status",
        parameters=[],
        returns="object",
        tags=["system"],
    ))

    return config


def load_config_from_file(config_path: str) -> AgentConfig:
    """Load agent configuration from a YAML file."""
    logger.info(f"Loading configuration from: {config_path}")

    with open(config_path, "r") as f:
        data = yaml.safe_load(f)

    # Parse agent section
    agent_data = data.get("agent", {})

    # Parse capabilities
    capabilities = []
    for cap_data in data.get("capabilities", []):
        capabilities.append(CapabilityDefinition(
            name=cap_data["name"],
            description=cap_data.get("description", ""),
            category=cap_data.get("category", "general"),
            level=cap_data.get("level", "basic"),
            dependencies=cap_data.get("dependencies", []),
            metrics=cap_data.get("metrics", {}),
        ))

    # Parse skills
    skills = []
    for skill_data in data.get("skills", []):
        parameters = []
        for param_data in skill_data.get("parameters", []):
            parameters.append(SkillParameter(
                name=param_data["name"],
                type=param_data.get("type", "string"),
                description=param_data.get("description", ""),
                required=param_data.get("required", True),
                default=param_data.get("default"),
                enum=param_data.get("enum"),
                min_value=param_data.get("min_value"),
                max_value=param_data.get("max_value"),
            ))

        skills.append(SkillDefinition(
            name=skill_data["name"],
            description=skill_data.get("description", ""),
            parameters=parameters,
            returns=skill_data.get("returns", "object"),
            timeout=skill_data.get("timeout", 30),
            rate_limit=skill_data.get("rate_limit", 100),
            tags=skill_data.get("tags", []),
        ))

    # Parse network config
    network_data = data.get("network", {})
    from usmsb_sdk.agent_sdk.agent_config import NetworkConfig, SecurityConfig

    network = NetworkConfig(
        platform_endpoints=network_data.get("platform_endpoints", ["http://localhost:8000"]),
        p2p_bootstrap_nodes=network_data.get("p2p_bootstrap_nodes", []),
        p2p_listen_port=network_data.get("p2p_listen_port", 9000),
    )

    # Parse security config
    security_data = data.get("security", {})
    security = SecurityConfig(
        auth_enabled=security_data.get("auth_enabled", True),
        api_key=os.getenv("API_KEY") or security_data.get("api_key"),
        jwt_secret=os.getenv("JWT_SECRET") or security_data.get("jwt_secret"),
        allowed_origins=security_data.get("allowed_origins", ["*"]),
    )

    # Parse runtime settings
    runtime_data = data.get("runtime", {})

    # Create config
    config = AgentConfig(
        agent_id=agent_data.get("agent_id"),
        name=agent_data.get("name", "docker-agent"),
        description=agent_data.get("description", ""),
        version=agent_data.get("version", "1.0.0"),
        owner=agent_data.get("owner"),
        tags=agent_data.get("tags", []),
        capabilities=capabilities,
        skills=skills,
        network=network,
        security=security,
        auto_register=runtime_data.get("auto_register", True),
        auto_discover=runtime_data.get("auto_discover", True),
        log_level=runtime_data.get("log_level", "INFO"),
        health_check_interval=runtime_data.get("health_check_interval", 30),
        heartbeat_interval=runtime_data.get("heartbeat_interval", 10),
        metadata=data.get("metadata", {}),
    )

    return config


async def main():
    """Main entrypoint for the agent."""
    logger.info("Starting Docker Agent...")

    # Load configuration
    config = load_config_from_env()

    # Create agent instance
    agent = DockerAgent(config)

    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            signal.signal(sig, lambda s, f: signal_handler())

    try:
        # Start the agent
        await agent.start()

        # Wait for shutdown signal
        await shutdown_event.wait()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise
    finally:
        # Graceful shutdown
        await agent.stop()
        logger.info("Agent stopped")


if __name__ == "__main__":
    asyncio.run(main())
