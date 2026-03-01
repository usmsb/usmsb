"""
Platform Client Module

Unified client for all platform API interactions.
Provides a clean interface for agents to communicate with the platform.
"""

import asyncio
import aiohttp
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4


logger = logging.getLogger(__name__)


class RegistrationStatus(Enum):
    """Agent registration status"""
    NOT_REGISTERED = "not_registered"
    REGISTERING = "registering"
    REGISTERED = "registered"
    FAILED = "failed"
    EXPIRED = "expired"


class ProtocolType(Enum):
    """Supported registration protocols"""
    STANDARD = "standard"
    MCP = "mcp"
    A2A = "a2a"
    SKILL_MD = "skill_md"


@dataclass
class RegistrationResult:
    """Result of registration attempt"""
    success: bool
    agent_id: str
    message: str
    registered_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


@dataclass
class APIResponse:
    """Standard API response wrapper"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    status_code: int = 200


class PlatformClient:
    """
    Unified client for all platform API interactions.

    Features:
    - Agent registration and lifecycle management
    - Service and demand publishing
    - Matching and negotiation
    - Collaboration and workflow
    - Wallet and staking
    - Learning and optimization
    """

    def __init__(
        self,
        platform_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        agent_id: Optional[str] = None,
        timeout: float = 30.0,
        heartbeat_interval: float = 30.0,
        logger: Optional[logging.Logger] = None,
    ):
        self.platform_url = platform_url.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
        self.timeout = timeout
        self.heartbeat_interval = heartbeat_interval
        self.logger = logger or logging.getLogger(__name__)

        self._session: Optional[aiohttp.ClientSession] = None
        self._registration_status = RegistrationStatus.NOT_REGISTERED
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None

    # ==================== Session Management ====================

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            )
        return self._session

    async def close(self):
        """Close the client and cleanup resources"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> APIResponse:
        """Make an HTTP request to the platform"""
        session = await self._get_session()
        url = f"{self.platform_url}{endpoint}"

        try:
            async with session.request(
                method,
                url,
                json=data,
                params=params,
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()

                if response.status >= 400:
                    error_msg = response_data.get("detail", str(response_data)) if isinstance(response_data, dict) else str(response_data)
                    return APIResponse(
                        success=False,
                        error=error_msg,
                        status_code=response.status,
                    )

                return APIResponse(
                    success=True,
                    data=response_data,
                    status_code=response.status,
                )

        except asyncio.TimeoutError:
            return APIResponse(success=False, error="Request timeout", status_code=408)
        except aiohttp.ClientError as e:
            return APIResponse(success=False, error=str(e), status_code=0)
        except Exception as e:
            self.logger.error(f"Request error: {e}")
            return APIResponse(success=False, error=str(e), status_code=0)

    # ==================== Registration ====================

    @property
    def registration_status(self) -> RegistrationStatus:
        return self._registration_status

    @property
    def is_registered(self) -> bool:
        return self._registration_status == RegistrationStatus.REGISTERED

    async def register(
        self,
        name: str,
        agent_type: str = "ai_agent",
        capabilities: Optional[List[str]] = None,
        skills: Optional[List[Dict]] = None,
        endpoint: Optional[str] = None,
        protocol: str = "standard",
        stake: float = 0,
        balance: float = 0,
        description: str = "",
        metadata: Optional[Dict] = None,
        heartbeat_interval: Optional[int] = None,
        ttl: Optional[int] = None,
    ) -> RegistrationResult:
        """
        Register the agent with the platform.

        Args:
            name: Agent name
            agent_type: Type of agent
            capabilities: List of capability strings
            skills: List of skill definitions
            endpoint: Agent's HTTP endpoint
            protocol: Registration protocol (standard, mcp, a2a, skill_md)
            stake: Initial stake amount
            balance: Initial balance
            description: Agent description
            metadata: Additional metadata
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
            ttl: Time to live in seconds (default: 3x heartbeat_interval)

        Returns:
            RegistrationResult with registration status
        """
        self._registration_status = RegistrationStatus.REGISTERING

        agent_id = self.agent_id or f"agent-{uuid4().hex[:8]}"
        interval = heartbeat_interval or int(self.heartbeat_interval)
        time_to_live = ttl or (interval * 3)

        registration_data = {
            "agent_id": agent_id,
            "name": name,
            "agent_type": agent_type,
            "capabilities": capabilities or [],
            "skills": skills or [],
            "endpoint": endpoint or "",
            "protocol": protocol,
            "stake": stake,
            "balance": balance,
            "description": description,
            "metadata": metadata or {},
            "heartbeat_interval": interval,
            "ttl": time_to_live,
        }

        # Choose registration endpoint based on protocol
        if protocol == "mcp":
            endpoint_path = "/agents/register/mcp"
            registration_data = {
                "agent_id": agent_id,
                "name": name,
                "capabilities": capabilities or [],
                "description": description,
                "mcp_endpoint": endpoint,
                "stake": stake,
                "heartbeat_interval": interval,
            }
        elif protocol == "a2a":
            endpoint_path = "/agents/register/a2a"
            registration_data = {
                "agent_card": {
                    "agent_id": agent_id,
                    "name": name,
                    "capabilities": capabilities or [],
                    "skills": skills or [],
                    "description": description,
                    "metadata": metadata or {},
                },
                "endpoint": endpoint,
                "heartbeat_interval": interval,
            }
        else:
            endpoint_path = "/agents/register"

        response = await self._request("POST", endpoint_path, data=registration_data)

        if response.success:
            self.agent_id = agent_id
            self._registration_status = RegistrationStatus.REGISTERED
            self._last_heartbeat = datetime.now()

            # Start heartbeat if not running
            if not self._heartbeat_task:
                self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            return RegistrationResult(
                success=True,
                agent_id=agent_id,
                message="Agent registered successfully",
                registered_at=datetime.now(),
            )
        else:
            self._registration_status = RegistrationStatus.FAILED
            return RegistrationResult(
                success=False,
                agent_id=agent_id,
                message=response.error or "Registration failed",
            )

    async def unregister(self) -> bool:
        """Unregister the agent from the platform"""
        if not self.agent_id:
            return False

        response = await self._request("DELETE", f"/agents/{self.agent_id}/unregister")

        if response.success:
            self._registration_status = RegistrationStatus.NOT_REGISTERED
            if self._heartbeat_task:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            return True
        return False

    async def send_heartbeat(self, status: str = "online") -> bool:
        """Send a heartbeat to the platform"""
        if not self.agent_id:
            return False

        response = await self._request(
            "POST",
            f"/agents/{self.agent_id}/heartbeat",
            params={"status": status},
        )

        if response.success:
            self._last_heartbeat = datetime.now()
            return True
        return False

    async def _heartbeat_loop(self):
        """Background task for sending heartbeats"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                await self.send_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"Heartbeat failed: {e}")

    async def get_registration_status(self) -> Dict[str, Any]:
        """Get current registration status from platform"""
        if not self.agent_id:
            return {"status": "not_registered"}

        response = await self._request("GET", f"/agents/{self.agent_id}")
        if response.success:
            return response.data
        return {"status": "unknown"}

    # ==================== Service Management ====================

    async def publish_service(
        self,
        service_name: str,
        service_type: str,
        capabilities: List[str],
        price: float,
        description: str = "",
        price_type: str = "hourly",
        availability: str = "24/7",
    ) -> APIResponse:
        """Publish a service offered by this agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "service_name": service_name,
            "service_type": service_type,
            "capabilities": capabilities,
            "price": price,
            "description": description,
            "price_type": price_type,
            "availability": availability,
        }

        return await self._request(
            "POST",
            f"/agents/{self.agent_id}/services",
            data=data,
        )

    async def list_services(
        self,
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> APIResponse:
        """List services on the platform"""
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if category:
            params["category"] = category

        return await self._request("GET", "/services", params=params)

    # ==================== Demand Management ====================

    async def publish_demand(
        self,
        title: str,
        description: str,
        required_skills: List[str],
        budget_min: float,
        budget_max: float,
        category: str = "",
        deadline: Optional[str] = None,
        priority: str = "medium",
        quality_requirements: Optional[Dict] = None,
    ) -> APIResponse:
        """Publish a demand/requirement"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "title": title,
            "description": description,
            "category": category,
            "required_skills": required_skills,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "deadline": deadline,
            "priority": priority,
            "quality_requirements": quality_requirements or {},
        }

        return await self._request("POST", "/demands", data=data)

    async def list_demands(
        self,
        agent_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> APIResponse:
        """List demands on the platform"""
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        if category:
            params["category"] = category

        return await self._request("GET", "/demands", params=params)

    async def cancel_demand(self, demand_id: str) -> APIResponse:
        """Cancel a demand"""
        return await self._request("DELETE", f"/demands/{demand_id}")

    # ==================== Matching ====================

    async def search_demands(
        self,
        capabilities: Optional[List[str]] = None,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
    ) -> APIResponse:
        """Search for demands matching this agent's capabilities"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "capabilities": capabilities or [],
            "budget_min": budget_min,
            "budget_max": budget_max,
        }

        return await self._request("POST", "/matching/search-demands", data=data)

    async def search_suppliers(
        self,
        required_skills: List[str],
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
    ) -> APIResponse:
        """Search for suppliers matching requirements"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "required_skills": required_skills,
            "budget_min": budget_min,
            "budget_max": budget_max,
        }

        return await self._request("POST", "/matching/search-suppliers", data=data)

    async def get_opportunities(self) -> APIResponse:
        """Get all opportunities for this agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "GET",
            "/matching/opportunities",
            params={"agent_id": self.agent_id},
        )

    async def get_matching_stats(self) -> APIResponse:
        """Get matching statistics for this agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "GET",
            "/matching/stats",
            params={"agent_id": self.agent_id},
        )

    # ==================== Negotiation ====================

    async def initiate_negotiation(
        self,
        counterpart_id: str,
        context: Dict[str, Any],
    ) -> APIResponse:
        """Initiate a negotiation with another agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "initiator_id": self.agent_id,
            "counterpart_id": counterpart_id,
            "context": context,
        }

        return await self._request("POST", "/matching/negotiate", data=data)

    async def get_negotiations(self) -> APIResponse:
        """Get all negotiations for this agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "GET",
            "/matching/negotiations",
            params={"agent_id": self.agent_id},
        )

    async def submit_proposal(
        self,
        session_id: str,
        proposal: Dict[str, Any],
    ) -> APIResponse:
        """Submit a proposal in a negotiation"""
        data = {"proposal": proposal}
        return await self._request(
            "POST",
            f"/matching/negotiations/{session_id}/proposal",
            data=data,
        )

    # ==================== Collaboration ====================

    async def create_collaboration(
        self,
        goal_description: str,
        required_skills: List[str],
        collaboration_mode: str = "parallel",
        coordinator_agent_id: Optional[str] = None,
    ) -> APIResponse:
        """Create a new collaboration session"""
        data = {
            "goal_description": goal_description,
            "required_skills": required_skills,
            "collaboration_mode": collaboration_mode,
            "coordinator_agent_id": coordinator_agent_id or self.agent_id,
        }

        return await self._request("POST", "/collaborations", data=data)

    async def get_collaborations(self, status: Optional[str] = None) -> APIResponse:
        """Get collaboration sessions"""
        params = {}
        if status:
            params["status"] = status

        return await self._request("GET", "/collaborations", params=params)

    async def get_collaboration(self, session_id: str) -> APIResponse:
        """Get a specific collaboration session"""
        return await self._request("GET", f"/collaborations/{session_id}")

    async def execute_collaboration(self, session_id: str) -> APIResponse:
        """Execute a collaboration session"""
        return await self._request("POST", f"/collaborations/{session_id}/execute")

    async def get_collaboration_stats(self) -> APIResponse:
        """Get collaboration statistics"""
        return await self._request("GET", "/collaborations/stats")

    # ==================== Workflow ====================

    async def create_workflow(
        self,
        task_description: str,
        available_tools: Optional[List[str]] = None,
    ) -> APIResponse:
        """Create a new workflow"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "task_description": task_description,
            "available_tools": available_tools or [],
        }

        return await self._request("POST", "/workflows", data=data)

    async def execute_workflow(self, workflow_id: str) -> APIResponse:
        """Execute a workflow"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "POST",
            f"/workflows/{workflow_id}/execute",
            params={"agent_id": self.agent_id},
        )

    async def list_workflows(self) -> APIResponse:
        """List all workflows"""
        return await self._request("GET", "/workflows")

    # ==================== Learning ====================

    async def analyze_learning(self) -> APIResponse:
        """Analyze agent's learning data"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "POST",
            "/learning/analyze",
            params={"agent_id": self.agent_id},
        )

    async def get_learning_insights(self) -> APIResponse:
        """Get learning insights for this agent"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("GET", f"/learning/insights/{self.agent_id}")

    async def get_optimized_strategy(self) -> APIResponse:
        """Get optimized matching strategy"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("GET", f"/learning/strategy/{self.agent_id}")

    async def get_market_insights(self) -> APIResponse:
        """Get market insights"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("GET", f"/learning/market/{self.agent_id}")

    # ==================== Staking ====================

    async def stake(self, amount: float) -> APIResponse:
        """Stake tokens to increase reputation"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "POST",
            f"/agents/{self.agent_id}/stake",
            params={"amount": amount},
        )

    # ==================== Gene Capsule ====================

    async def get_gene_capsule(self) -> APIResponse:
        """
        Get agent's gene capsule containing experiences, skills, and patterns.

        Returns:
            APIResponse with gene capsule data
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("GET", f"/gene-capsule/{self.agent_id}")

    async def add_experience(
        self,
        experience_data: Dict[str, Any],
        auto_desensitize: bool = True,
    ) -> APIResponse:
        """
        Add a new experience gene to the capsule.

        Args:
            experience_data: Experience details including:
                - task_type: Type of task performed
                - techniques: List of techniques used
                - results: Outcome of the task
                - client_feedback: Optional client feedback
                - lessons_learned: What was learned
                - difficulty_level: Task difficulty (easy/medium/hard/expert)
                - time_spent: Time spent on task
                - share_level: Visibility (public/semi_public/private/hidden)
            auto_desensitize: Whether to auto-desensitize sensitive data

        Returns:
            APIResponse with added experience gene
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "experience": experience_data,
            "auto_desensitize": auto_desensitize,
        }

        return await self._request("POST", "/gene-capsule/experiences", data=data)

    async def update_experience_visibility(
        self,
        experience_id: str,
        share_level: str,
    ) -> APIResponse:
        """
        Update the visibility level of an experience gene.

        Args:
            experience_id: ID of the experience to update
            share_level: New visibility level (public/semi_public/private/hidden)

        Returns:
            APIResponse with update status
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "experience_id": experience_id,
            "share_level": share_level,
        }

        return await self._request(
            "PATCH",
            f"/gene-capsule/experiences/{experience_id}/visibility",
            data=data,
        )

    async def desensitize_text(
        self,
        text: str,
        context: Optional[str] = None,
        recursion_depth: int = 3,
    ) -> APIResponse:
        """
        Request LLM-based recursive desensitization for sensitive text.

        Args:
            text: Text to desensitize
            context: Optional context for better desensitization
            recursion_depth: Number of LLM verification rounds (default 3)

        Returns:
            APIResponse with desensitized text and detected entities
        """
        data = {
            "text": text,
            "context": context,
            "recursion_depth": recursion_depth,
        }

        return await self._request("POST", "/gene-capsule/desensitize", data=data)

    async def find_matching_experiences(
        self,
        task_description: str,
        required_skills: Optional[List[str]] = None,
        min_relevance: float = 0.5,
        limit: int = 10,
    ) -> APIResponse:
        """
        Find relevant experiences from gene capsule for a given task.

        Args:
            task_description: Description of the task to match
            required_skills: Optional list of required skills to filter by
            min_relevance: Minimum relevance score (0-1)
            limit: Maximum number of experiences to return

        Returns:
            APIResponse with matching experiences and relevance scores
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "task_description": task_description,
            "required_skills": required_skills or [],
            "min_relevance": min_relevance,
            "limit": limit,
        }

        return await self._request("POST", "/gene-capsule/match", data=data)

    async def get_skill_recommendations(
        self,
        task_description: str,
    ) -> APIResponse:
        """
        Get skill recommendations based on gene capsule analysis.

        Args:
            task_description: Description of the task

        Returns:
            APIResponse with recommended skills and confidence levels
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "POST",
            "/gene-capsule/skill-recommendations",
            data={
                "agent_id": self.agent_id,
                "task_description": task_description,
            },
        )

    async def export_showcase(
        self,
        experience_ids: Optional[List[str]] = None,
        for_negotiation: bool = True,
    ) -> APIResponse:
        """
        Export a showcase of experiences for negotiation or portfolio display.

        Args:
            experience_ids: Specific experiences to include (optional, uses best if not provided)
            for_negotiation: Whether this is for negotiation context

        Returns:
            APIResponse with showcase data suitable for sharing
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "agent_id": self.agent_id,
            "experience_ids": experience_ids,
            "for_negotiation": for_negotiation,
        }

        return await self._request("POST", "/gene-capsule/showcase", data=data)

    async def get_experience_value_scores(self) -> APIResponse:
        """
        Get experience value scores for all experiences in the capsule.

        Returns:
            APIResponse with value scores for each experience:
            - scarcity_score: Uniqueness of the experience
            - difficulty_score: Task difficulty level
            - impact_score: Business/user impact
            - recency_score: Time relevance
            - demonstration_score: Evidence quality
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "GET",
            f"/gene-capsule/{self.agent_id}/value-scores",
        )

    async def request_verification(
        self,
        experience_id: str,
    ) -> APIResponse:
        """
        Request platform verification for an experience.

        Args:
            experience_id: ID of the experience to verify

        Returns:
            APIResponse with verification request status
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "POST",
            f"/gene-capsule/experiences/{experience_id}/verify",
            data={"agent_id": self.agent_id},
        )

    async def get_verification_status(
        self,
        experience_id: str,
    ) -> APIResponse:
        """
        Get verification status for an experience.

        Args:
            experience_id: ID of the experience

        Returns:
            APIResponse with verification status and details
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request(
            "GET",
            f"/gene-capsule/experiences/{experience_id}/verification",
        )

    async def search_agents_by_experience(
        self,
        task_description: str,
        required_skills: Optional[List[str]] = None,
        min_experience_relevance: float = 0.6,
        limit: int = 20,
    ) -> APIResponse:
        """
        Search for agents with relevant experience genes.

        This is a powerful discovery method that finds agents based on
        their proven experience, not just claimed capabilities.

        Args:
            task_description: Description of the task
            required_skills: Optional required skills filter
            min_experience_relevance: Minimum relevance threshold
            limit: Maximum results

        Returns:
            APIResponse with matching agents and their relevant experiences
        """
        data = {
            "task_description": task_description,
            "required_skills": required_skills or [],
            "min_experience_relevance": min_experience_relevance,
            "limit": limit,
        }

        return await self._request("POST", "/gene-capsule/search-agents", data=data)

    async def get_pattern_library(self) -> APIResponse:
        """
        Get all extracted patterns from the gene capsule.

        Returns:
            APIResponse with pattern genes including:
            - problem_solving_patterns
            - collaboration_patterns
            - optimization_patterns
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("GET", f"/gene-capsule/{self.agent_id}/patterns")

    async def sync_capsule_version(self) -> APIResponse:
        """
        Sync local capsule with platform version.

        Returns:
            APIResponse with latest capsule data and version info
        """
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        return await self._request("POST", f"/gene-capsule/{self.agent_id}/sync")

    # ==================== Utility Methods ====================

    async def health_check(self) -> Dict[str, Any]:
        """Check platform health"""
        response = await self._request("GET", "/health")
        return {
            "platform_reachable": response.success,
            "agent_registered": self.is_registered,
            "last_heartbeat": self._last_heartbeat.isoformat() if self._last_heartbeat else None,
        }

    async def test_agent(self, test_input: str, context: Optional[Dict] = None) -> APIResponse:
        """Test agent connectivity"""
        if not self.agent_id:
            return APIResponse(success=False, error="Agent not registered")

        data = {
            "input": test_input,
            "context": context or {},
        }

        return await self._request("POST", f"/agents/{self.agent_id}/test", data=data)
