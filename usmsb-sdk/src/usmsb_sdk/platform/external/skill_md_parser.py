"""
External Agent Protocol Support

Implements support for external agent protocols:
- skill.md: Skill definition format
- A2A: Agent-to-Agent communication
- MCP: Model Context Protocol
- P2P: Peer-to-peer networking
"""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


# ==================== Skill.md Parser ====================

@dataclass
class SkillDefinition:
    """A parsed skill definition from skill.md."""
    name: str
    description: str
    inputs: List[Dict[str, Any]]
    outputs: List[Dict[str, Any]]
    endpoint: Optional[str] = None
    authentication: Optional[str] = None
    rate_limit: Optional[int] = None
    pricing: Optional[Dict[str, float]] = None
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "endpoint": self.endpoint,
            "authentication": self.authentication,
            "rateLimit": self.rate_limit,
            "pricing": self.pricing,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
        }


class SkillMdParser:
    """
    Parser for skill.md format.

    Skill.md is a markdown-based format for defining agent skills.
    Example:
    ```markdown
    # Skill: Text Summarization

    ## Description
    Summarizes long text into concise summaries.

    ## Inputs
    - text (string, required): The text to summarize
    - max_length (integer, optional): Maximum summary length

    ## Outputs
    - summary (string): The generated summary
    - confidence (float): Confidence score

    ## Endpoint
    POST /api/skills/summarize

    ## Pricing
    - per_request: 0.01 VIBE
    ```
    """

    @staticmethod
    def parse(content: str) -> List[SkillDefinition]:
        """
        Parse skill.md content into skill definitions.

        Args:
            content: Markdown content

        Returns:
            List of parsed skill definitions
        """
        skills = []

        # Split by skill headers
        skill_sections = re.split(r'^# Skill:\s*(.+)$', content, flags=re.MULTILINE)

        # Process each skill
        for i in range(1, len(skill_sections), 2):
            if i + 1 < len(skill_sections):
                name = skill_sections[i].strip()
                body = skill_sections[i + 1]
                skill = SkillMdParser._parse_skill(name, body)
                if skill:
                    skills.append(skill)

        # Handle single skill files (no explicit Skill header)
        if not skills and content.strip():
            skill = SkillMdParser._parse_skill_from_sections(content)
            if skill:
                skills.append(skill)

        return skills

    @staticmethod
    def _parse_skill(name: str, body: str) -> Optional[SkillDefinition]:
        """Parse a single skill definition."""
        try:
            sections = SkillMdParser._extract_sections(body)

            return SkillDefinition(
                name=name,
                description=sections.get("description", ""),
                inputs=SkillMdParser._parse_inputs(sections.get("inputs", "")),
                outputs=SkillMdParser._parse_outputs(sections.get("outputs", "")),
                endpoint=sections.get("endpoint"),
                authentication=sections.get("authentication"),
                rate_limit=SkillMdParser._parse_rate_limit(sections.get("rate_limit", "")),
                pricing=SkillMdParser._parse_pricing(sections.get("pricing", "")),
                tags=SkillMdParser._parse_tags(sections.get("tags", "")),
                version=sections.get("version", "1.0.0"),
                author=sections.get("author"),
            )
        except Exception as e:
            logger.error(f"Failed to parse skill '{name}': {e}")
            return None

    @staticmethod
    def _parse_skill_from_sections(content: str) -> Optional[SkillDefinition]:
        """Parse a skill from sections without explicit name."""
        sections = SkillMdParser._extract_sections(content)

        name = sections.get("name", sections.get("skill", "Unnamed Skill"))

        return SkillDefinition(
            name=name,
            description=sections.get("description", ""),
            inputs=SkillMdParser._parse_inputs(sections.get("inputs", "")),
            outputs=SkillMdParser._parse_outputs(sections.get("outputs", "")),
            endpoint=sections.get("endpoint"),
            authentication=sections.get("authentication"),
            rate_limit=SkillMdParser._parse_rate_limit(sections.get("rate_limit", "")),
            pricing=SkillMdParser._parse_pricing(sections.get("pricing", "")),
            tags=SkillMdParser._parse_tags(sections.get("tags", "")),
            version=sections.get("version", "1.0.0"),
            author=sections.get("author"),
        )

    @staticmethod
    def _extract_sections(content: str) -> Dict[str, str]:
        """Extract markdown sections into a dictionary."""
        sections = {}
        current_section = None
        current_content = []

        for line in content.split('\n'):
            # Check for section header
            match = re.match(r'^##\s*(.+)$', line)
            if match:
                # Save previous section
                if current_section:
                    sections[current_section.lower().replace(' ', '_')] = '\n'.join(current_content).strip()

                current_section = match.group(1)
                current_content = []
            elif current_section:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section.lower().replace(' ', '_')] = '\n'.join(current_content).strip()

        return sections

    @staticmethod
    def _parse_inputs(content: str) -> List[Dict[str, Any]]:
        """Parse inputs section."""
        inputs = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                # Parse: - name (type, required): description
                match = re.match(r'-\s*(\w+)\s*\(([^)]+)\)(?:\s*:\s*(.+))?', line)
                if match:
                    name = match.group(1)
                    type_info = match.group(2)
                    description = match.group(3) or ""

                    # Parse type info
                    parts = [p.strip() for p in type_info.split(',')]
                    input_type = parts[0] if parts else "string"
                    required = "required" in type_info.lower()

                    inputs.append({
                        "name": name,
                        "type": input_type,
                        "required": required,
                        "description": description.strip(),
                    })

        return inputs

    @staticmethod
    def _parse_outputs(content: str) -> List[Dict[str, Any]]:
        """Parse outputs section."""
        outputs = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                match = re.match(r'-\s*(\w+)\s*\(([^)]+)\)(?:\s*:\s*(.+))?', line)
                if match:
                    outputs.append({
                        "name": match.group(1),
                        "type": match.group(2).strip(),
                        "description": (match.group(3) or "").strip(),
                    })
        return outputs

    @staticmethod
    def _parse_rate_limit(content: str) -> Optional[int]:
        """Parse rate limit."""
        match = re.search(r'(\d+)\s*requests?\s*(?:per|/)\s*(\w+)', content)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _parse_pricing(content: str) -> Optional[Dict[str, float]]:
        """Parse pricing information."""
        pricing = {}
        for line in content.split('\n'):
            match = re.match(r'-\s*(\w+):\s*([\d.]+)\s*(\w+)?', line.strip())
            if match:
                key = match.group(1)
                value = float(match.group(2))
                unit = match.group(3) or "VIBE"
                pricing[key] = {"amount": value, "unit": unit}
        return pricing if pricing else None

    @staticmethod
    def _parse_tags(content: str) -> List[str]:
        """Parse tags."""
        tags = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('-'):
                tag = line[1:].strip()
                if tag:
                    tags.append(tag)
            elif line.startswith('#'):
                tag = line.strip()
                if tag not in ['##']:
                    tags.append(tag)
        return tags


# ==================== A2A Protocol ====================

class A2AMessageType(str, Enum):
    """A2A message types."""
    HELLO = "hello"
    BYE = "bye"
    REQUEST = "request"
    RESPONSE = "response"
    ERROR = "error"
    PING = "ping"
    PONG = "pong"


@dataclass
class A2AMessage:
    """An A2A protocol message."""
    message_type: A2AMessageType
    sender_id: str
    receiver_id: str
    payload: Dict[str, Any]
    message_id: str = ""
    timestamp: float = field(default_factory=time.time)
    ttl: int = 10  # Time to live for routing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.message_type.value,
            "senderId": self.sender_id,
            "receiverId": self.receiver_id,
            "payload": self.payload,
            "messageId": self.message_id,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        return cls(
            message_type=A2AMessageType(data.get("type", "request")),
            sender_id=data.get("senderId", ""),
            receiver_id=data.get("receiverId", ""),
            payload=data.get("payload", {}),
            message_id=data.get("messageId", ""),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl", 10),
        )


class A2AProtocol:
    """
    Agent-to-Agent communication protocol handler.

    Implements the A2A protocol for inter-agent messaging.
    """

    def __init__(self, agent_id: str, endpoint: str):
        """
        Initialize A2A protocol handler.

        Args:
            agent_id: This agent's ID
            endpoint: HTTP endpoint for receiving messages
        """
        self.agent_id = agent_id
        self.endpoint = endpoint
        self._handlers: Dict[str, Callable] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}

    def register_handler(
        self,
        message_type: A2AMessageType,
        handler: Callable[[A2AMessage], Any],
    ) -> None:
        """Register a handler for a message type."""
        self._handlers[message_type.value] = handler

    async def send_message(
        self,
        receiver_endpoint: str,
        message: A2AMessage,
        timeout: float = 30.0,
    ) -> Optional[A2AMessage]:
        """
        Send a message to another agent.

        Args:
            receiver_endpoint: HTTP endpoint of the receiver
            message: The message to send
            timeout: Response timeout

        Returns:
            Response message if any
        """
        import uuid
        message.message_id = str(uuid.uuid4())

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{receiver_endpoint}/a2a",
                    json=message.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return A2AMessage.from_dict(data)
                    else:
                        logger.error(f"A2A send failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"A2A send error: {e}")
            return None

    async def handle_message(self, message: A2AMessage) -> Optional[A2AMessage]:
        """Handle an incoming message."""
        handler = self._handlers.get(message.message_type.value)
        if handler:
            try:
                result = await handler(message)
                if result:
                    if isinstance(result, A2AMessage):
                        return result
                    else:
                        return A2AMessage(
                            message_type=A2AMessageType.RESPONSE,
                            sender_id=self.agent_id,
                            receiver_id=message.sender_id,
                            payload={"result": result},
                            message_id=message.message_id,
                        )
            except Exception as e:
                logger.error(f"A2A handler error: {e}")
                return A2AMessage(
                    message_type=A2AMessageType.ERROR,
                    sender_id=self.agent_id,
                    receiver_id=message.sender_id,
                    payload={"error": str(e)},
                    message_id=message.message_id,
                )

        return None


# ==================== MCP Protocol ====================

@dataclass
class MCPTool:
    """An MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
        }


@dataclass
class MCPToolCall:
    """An MCP tool call request."""
    tool_name: str
    arguments: Dict[str, Any]
    call_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "toolName": self.tool_name,
            "arguments": self.arguments,
            "callId": self.call_id,
        }


@dataclass
class MCPToolResult:
    """An MCP tool call result."""
    call_id: str
    success: bool
    result: Any
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "callId": self.call_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
        }


class MCPAdapter:
    """
    Model Context Protocol adapter.

    Implements MCP for tool discovery and execution.
    """

    def __init__(self, agent_id: str, tools: List[MCPTool] = None):
        """
        Initialize MCP adapter.

        Args:
            agent_id: This agent's ID
            tools: Available tools
        """
        self.agent_id = agent_id
        self._tools: Dict[str, MCPTool] = {}
        self._tool_handlers: Dict[str, Callable] = {}

        if tools:
            for tool in tools:
                self._tools[tool.name] = tool

    def register_tool(
        self,
        tool: MCPTool,
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Register a tool with its handler."""
        self._tools[tool.name] = tool
        self._tool_handlers[tool.name] = handler

    def list_tools(self) -> List[MCPTool]:
        """List available tools."""
        return list(self._tools.values())

    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call."""
        import uuid
        call.call_id = call.call_id or str(uuid.uuid4())

        tool = self._tools.get(call.tool_name)
        if not tool:
            return MCPToolResult(
                call_id=call.call_id,
                success=False,
                result=None,
                error=f"Tool not found: {call.tool_name}",
            )

        handler = self._tool_handlers.get(call.tool_name)
        if not handler:
            return MCPToolResult(
                call_id=call.call_id,
                success=False,
                result=None,
                error=f"No handler for tool: {call.tool_name}",
            )

        try:
            result = await handler(call.arguments)
            return MCPToolResult(
                call_id=call.call_id,
                success=True,
                result=result,
            )
        except Exception as e:
            return MCPToolResult(
                call_id=call.call_id,
                success=False,
                result=None,
                error=str(e),
            )

    async def call_remote_tool(
        self,
        endpoint: str,
        call: MCPToolCall,
        timeout: float = 30.0,
    ) -> MCPToolResult:
        """Call a tool on a remote agent."""
        import uuid
        call.call_id = call.call_id or str(uuid.uuid4())

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/mcp/call",
                    json=call.to_dict(),
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return MCPToolResult(
                            call_id=data.get("callId", call.call_id),
                            success=data.get("success", False),
                            result=data.get("result"),
                            error=data.get("error"),
                        )
                    else:
                        return MCPToolResult(
                            call_id=call.call_id,
                            success=False,
                            result=None,
                            error=f"HTTP error: {response.status}",
                        )
        except Exception as e:
            return MCPToolResult(
                call_id=call.call_id,
                success=False,
                result=None,
                error=str(e),
            )


# ==================== External Agent Registry ====================

@dataclass
class ExternalAgentProfile:
    """Profile of an external agent."""
    agent_id: str
    name: str
    endpoint: str
    protocol: str  # "skill.md", "a2a", "mcp"
    skills: List[SkillDefinition]
    capabilities: List[str]
    status: str = "offline"
    last_seen: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "protocol": self.protocol,
            "skills": [s.to_dict() for s in self.skills],
            "capabilities": self.capabilities,
            "status": self.status,
            "lastSeen": self.last_seen,
            "metadata": self.metadata,
        }


class ExternalAgentRegistry:
    """
    Registry for external agents.

    Manages discovery, registration, and communication with external agents.
    """

    def __init__(self):
        """Initialize the registry."""
        self._agents: Dict[str, ExternalAgentProfile] = {}
        self._skill_index: Dict[str, List[str]] = {}  # skill -> agent_ids

    async def register_from_skill_md(
        self,
        skill_md_url: str,
        agent_name: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[ExternalAgentProfile]:
        """
        Register an agent from its skill.md URL.

        Args:
            skill_md_url: URL to skill.md file
            agent_name: Optional name override
            metadata: Additional metadata

        Returns:
            Registered agent profile
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(skill_md_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch skill.md: {response.status}")
                        return None

                    content = await response.text()

            # Parse skills
            skills = SkillMdParser.parse(content)
            if not skills:
                logger.error("No skills found in skill.md")
                return None

            # Extract capabilities
            capabilities = list(set(
                skill.name.lower().replace(' ', '_')
                for skill in skills
            ))

            # Create profile
            import hashlib
            agent_id = hashlib.md5(skill_md_url.encode()).hexdigest()[:16]

            profile = ExternalAgentProfile(
                agent_id=agent_id,
                name=agent_name or skills[0].name,
                endpoint=skill_md_url.rsplit('/', 1)[0] if '/' in skill_md_url else "",
                protocol="skill.md",
                skills=skills,
                capabilities=capabilities,
                status="online",
                last_seen=time.time(),
                metadata=metadata or {},
            )

            # Register
            self._agents[agent_id] = profile

            # Index skills
            for skill in skills:
                skill_key = skill.name.lower()
                if skill_key not in self._skill_index:
                    self._skill_index[skill_key] = []
                self._skill_index[skill_key].append(agent_id)

            logger.info(f"Registered external agent: {profile.name}")
            return profile

        except Exception as e:
            logger.error(f"Failed to register agent from skill.md: {e}")
            return None

    def register_agent(self, profile: ExternalAgentProfile) -> None:
        """Register an external agent profile."""
        self._agents[profile.agent_id] = profile

        # Index skills
        for skill in profile.skills:
            skill_key = skill.name.lower()
            if skill_key not in self._skill_index:
                self._skill_index[skill_key] = []
            if profile.agent_id not in self._skill_index[skill_key]:
                self._skill_index[skill_key].append(profile.agent_id)

        logger.info(f"Registered external agent: {profile.name}")

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            profile = self._agents[agent_id]

            # Remove from skill index
            for skill in profile.skills:
                skill_key = skill.name.lower()
                if skill_key in self._skill_index:
                    self._skill_index[skill_key] = [
                        aid for aid in self._skill_index[skill_key]
                        if aid != agent_id
                    ]

            del self._agents[agent_id]
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[ExternalAgentProfile]:
        """Get an agent by ID."""
        return self._agents.get(agent_id)

    def find_by_skill(self, skill_name: str) -> List[ExternalAgentProfile]:
        """Find agents with a specific skill."""
        skill_key = skill_name.lower()
        agent_ids = self._skill_index.get(skill_key, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def find_by_capability(self, capability: str) -> List[ExternalAgentProfile]:
        """Find agents with a specific capability."""
        cap_lower = capability.lower()
        return [
            agent for agent in self._agents.values()
            if cap_lower in [c.lower() for c in agent.capabilities]
        ]

    def list_agents(self, status: str = None) -> List[ExternalAgentProfile]:
        """List all registered agents."""
        agents = list(self._agents.values())
        if status:
            agents = [a for a in agents if a.status == status]
        return agents

    def update_status(self, agent_id: str, status: str) -> bool:
        """Update an agent's status."""
        if agent_id in self._agents:
            self._agents[agent_id].status = status
            self._agents[agent_id].last_seen = time.time()
            return True
        return False
