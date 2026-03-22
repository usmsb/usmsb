"""
Main AgentPlatform class for interacting with USMSB Platform.
"""

import asyncio
from typing import Callable

import aiohttp

from .intent_parser import IntentParser
from .registration import (
    BindingRequestResult,
    BindingStatus,
    RegistrationClient,
    RegistrationResult,
)
from .stake_checker import StakeChecker
from .types import (
    ErrorCode,
    Intent,
    PlatformResult,
    RetryConfig,
    StakeInfo,
    StakeRequirement,
)
from .order import Order, OrderTerms, OrderStatus, Deliverable
from .websocket_mixin import WebSocketMixin, WebSocketConnection


class PlatformClient:
    """HTTP client for platform API calls with retry support."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        agent_id: str,
        retry_config: RetryConfig | None = None
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.agent_id = agent_id
        self._session: aiohttp.ClientSession | None = None
        self.retry_config = retry_config or RetryConfig()

        # API handlers
        self.collaboration = CollaborationAPI(self)
        self.marketplace = MarketplaceAPI(self)
        self.discovery = DiscoveryAPI(self)
        self.negotiation = NegotiationAPI(self)
        self.workflow = WorkflowAPI(self)
        self.learning = LearningAPI(self)
        self.gene_capsule = GeneCapsuleAPI(self)
        self.prematch = PreMatchNegotiationAPI(self)
        self.meta_agent = MetaAgentAPI(self)
        self.staking = StakingAPI(self)
        self.reputation = ReputationAPI(self)
        self.wallet = WalletAPI(self)
        self.heartbeat = HeartbeatAPI(self)
        self.order = OrderAPI(self)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-API-Key": self.api_key,
                    "X-Agent-ID": self.agent_id,
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=30.0)
            )
        return self._session

    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        data: dict | None = None,
        params: dict | None = None
    ) -> dict:
        """Make request with automatic retry on transient errors."""
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(self.retry_config.max_retries):
            try:
                if method == "GET":
                    async with session.get(url, params=params) as resp:
                        return await self._handle_response(resp)
                elif method == "POST":
                    async with session.post(url, json=data) as resp:
                        return await self._handle_response(resp)
                elif method == "PATCH":
                    async with session.patch(url, json=data) as resp:
                        return await self._handle_response(resp)
                elif method == "DELETE":
                    async with session.delete(url) as resp:
                        return await self._handle_response(resp)
            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.retry_config.max_retries - 1:
                    delay = self.retry_config.retry_delay * (
                        self.retry_config.retry_multiplier ** attempt
                    )
                    await asyncio.sleep(delay)

        raise last_error or Exception("Request failed after retries")

    async def _handle_response(self, resp: aiohttp.ClientResponse) -> dict:
        """Handle HTTP response and extract data with enhanced error handling."""
        try:
            data = await resp.json()
        except:
            text = await resp.text()
            data = {"error": text, "success": False}

        # Extract request ID from headers
        request_id = resp.headers.get("X-Request-ID")
        if request_id:
            data["request_id"] = request_id

        # Extract rate limit info
        rate_limit = resp.headers.get("X-RateLimit-Remaining")
        if rate_limit:
            data["rate_limit_remaining"] = int(rate_limit)

        if resp.status >= 400:
            data["status_code"] = resp.status

            # Parse stake requirement if present
            if "stake_requirement" in data and isinstance(data["stake_requirement"], dict):
                sr = data["stake_requirement"]
                data["stake_requirement"] = StakeRequirement(
                    required=sr.get("required", 0),
                    current=sr.get("current", 0),
                    shortfall=sr.get("shortfall", 0),
                    action=sr.get("action", "")
                )

            # Add retry_after from header if present
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    data["retry_after"] = int(retry_after)
                except ValueError:
                    pass

        return data

    async def get(self, path: str, params: dict | None = None) -> dict:
        """Make GET request with retry."""
        return await self._request_with_retry("GET", path, params=params)

    async def post(self, path: str, data: dict | None = None) -> dict:
        """Make POST request with retry."""
        return await self._request_with_retry("POST", path, data=data)

    async def patch(self, path: str, data: dict | None = None) -> dict:
        """Make PATCH request with retry."""
        return await self._request_with_retry("PATCH", path, data=data)

    async def delete(self, path: str) -> dict:
        """Make DELETE request with retry."""
        return await self._request_with_retry("DELETE", path)

    async def get_staked_amount(self, agent_id: str) -> int:
        """Get staked amount for an agent from platform."""
        try:
            data = await self.get(f"/api/agents/v2/{agent_id}/binding-status")
            return data.get("staked_amount", 0)
        except Exception:
            return 0


class BaseAPI:
    """Base class for API handlers."""

    def __init__(self, client: PlatformClient):
        self.client = client


# ==================== Collaboration API ====================
class CollaborationAPI(BaseAPI):
    """Collaboration API handler."""

    async def create(self, goal: str = "", description: str = "", **kwargs) -> dict:
        return await self.client.post("/collaborations", {
            "goal_description": goal,
            "description": description,
            **kwargs
        })

    async def join(self, collab_id: str = "", **kwargs) -> dict:
        return await self.client.post(f"/collaborations/{collab_id}/join", kwargs)

    async def contribute(self, collab_id: str = "", content: str = "", **kwargs) -> dict:
        return await self.client.post(f"/collaborations/{collab_id}/contribute", {
            "contribution": {"content": content},
            **kwargs
        })

    async def list(self, **kwargs) -> dict:
        return await self.client.get("/collaborations", kwargs)

    async def get(self, session_id: str) -> dict:
        return await self.client.get(f"/collaborations/{session_id}")

    async def complete(self, session_id: str) -> dict:
        return await self.client.post(f"/collaborations/{session_id}/complete", {})


# ==================== Marketplace API ====================
class MarketplaceAPI(BaseAPI):
    """Marketplace API handler."""

    async def publish_service(
        self,
        name: str = "",
        price: int = 0,
        description: str = "",
        skills: list | None = None,
        **kwargs
    ) -> dict:
        return await self.client.post(f"/agents/{self.client.agent_id}/services", {
            "name": name,
            "price": price,
            "description": description,
            "skills": skills or [],
            **kwargs
        })

    async def find_work(self, skill_filter: str = "", **kwargs) -> dict:
        return await self.client.post("/matching/search-demands", {
            "agent_id": self.client.agent_id,
            "capabilities": [skill_filter] if skill_filter else [],
            **kwargs
        })

    async def find_workers(self, skills: list | None = None, **kwargs) -> dict:
        return await self.client.post("/matching/search-suppliers", {
            "agent_id": self.client.agent_id,
            "required_skills": skills or [],
            **kwargs
        })

    async def publish_demand(
        self,
        title: str = "",
        budget: int = 0,
        description: str = "",
        **kwargs
    ) -> dict:
        return await self.client.post("/demands", {
            "title": title,
            "budget_min": budget,
            "budget_max": budget,
            "description": description,
            **kwargs
        })

    async def list_services(self, **kwargs) -> dict:
        return await self.client.get("/services", kwargs)

    async def delete_service(self, service_id: str) -> dict:
        return await self.client.delete(f"/services/{service_id}")


# ==================== Discovery API ====================
class DiscoveryAPI(BaseAPI):
    """Discovery API handler."""

    async def by_capability(self, capability: str = "", **kwargs) -> dict:
        return await self.client.post("/network/explore", {
            "target_capabilities": [capability] if capability else [],
            **kwargs
        })

    async def by_skill(self, skills: list | None = None, **kwargs) -> dict:
        return await self.client.post("/network/explore", {
            "target_capabilities": skills or [],
            **kwargs
        })

    async def recommend(self, goal: str = "", **kwargs) -> dict:
        return await self.client.post("/network/recommendations", {
            "target_capability": goal,
            **kwargs
        })

    async def stats(self) -> dict:
        return await self.client.get("/network/stats")


# ==================== Negotiation API ====================
class NegotiationAPI(BaseAPI):
    """Negotiation API handler."""

    async def initiate(
        self,
        target_id: str = "",
        terms: dict | None = None,
        **kwargs
    ) -> dict:
        return await self.client.post("/matching/negotiate", {
            "counterpart_id": target_id,
            "context": terms or {},
            **kwargs
        })

    async def accept(self, negotiation_id: str = "", **kwargs) -> dict:
        return await self.client.post(f"/matching/negotiations/{negotiation_id}/accept", kwargs)

    async def reject(self, negotiation_id: str = "", **kwargs) -> dict:
        return await self.client.post(f"/matching/negotiations/{negotiation_id}/reject", kwargs)

    async def propose(
        self,
        negotiation_id: str = "",
        new_terms: dict | None = None,
        **kwargs
    ) -> dict:
        return await self.client.post(f"/matching/negotiations/{negotiation_id}/proposal", {
            "proposal": new_terms or {},
            **kwargs
        })

    async def list(self) -> dict:
        return await self.client.get("/matching/negotiations")


# ==================== Workflow API ====================
class WorkflowAPI(BaseAPI):
    """Workflow API handler."""

    async def create(
        self,
        name: str = "",
        steps: list | None = None,
        **kwargs
    ) -> dict:
        return await self.client.post("/workflows", {
            "task_description": name,
            "available_tools": steps or [],
            **kwargs
        })

    async def execute(
        self,
        workflow_id: str = "",
        inputs: dict | None = None,
        **kwargs
    ) -> dict:
        return await self.client.post(f"/workflows/{workflow_id}/execute", kwargs)

    async def list(self, **kwargs) -> dict:
        return await self.client.get("/workflows", kwargs)


# ==================== Learning API ====================
class LearningAPI(BaseAPI):
    """Learning API handler."""

    async def analyze(self, **kwargs) -> dict:
        return await self.client.post("/learning/analyze", kwargs)

    async def insights(self, **kwargs) -> dict:
        return await self.client.get("/learning/insights", kwargs)

    async def strategy(self, **kwargs) -> dict:
        return await self.client.get("/learning/strategy", kwargs)

    async def market(self, **kwargs) -> dict:
        return await self.client.get("/learning/market", kwargs)


# ==================== Gene Capsule API (NEW) ====================
class GeneCapsuleAPI(BaseAPI):
    """Gene Capsule API handler for experience management."""

    async def get_capsule(self, agent_id: str = "") -> dict:
        """Get agent's gene capsule."""
        target_id = agent_id or self.client.agent_id
        return await self.client.get(f"/gene-capsule/{target_id}")

    async def add_experience(
        self,
        title: str = "",
        description: str = "",
        skills: list[str] | None = None,
        auto_desensitize: bool = True,
        **kwargs
    ) -> dict:
        """Add a new experience gene."""
        return await self.client.post("/gene-capsule/experiences", {
            "agent_id": self.client.agent_id,
            "experience": {
                "title": title,
                "description": description,
                "skills": skills or [],
            },
            "auto_desensitize": auto_desensitize,
            **kwargs
        })

    async def update_visibility(
        self,
        experience_id: str = "",
        share_level: str = "semi_public",
        **kwargs
    ) -> dict:
        """Update experience visibility."""
        return await self.client.patch(f"/gene-capsule/experiences/{experience_id}/visibility", {
            "agent_id": self.client.agent_id,
            "share_level": share_level,
            **kwargs
        })

    async def match(
        self,
        task_description: str = "",
        required_skills: list[str] | None = None,
        min_relevance: float = 0.3,
        limit: int = 10,
        **kwargs
    ) -> dict:
        """Find matching experiences."""
        return await self.client.post("/gene-capsule/match", {
            "agent_id": self.client.agent_id,
            "task_description": task_description,
            "required_skills": required_skills or [],
            "min_relevance": min_relevance,
            "limit": limit,
            **kwargs
        })

    async def showcase(
        self,
        experience_ids: list[str] | None = None,
        for_negotiation: bool = True,
        **kwargs
    ) -> dict:
        """Export showcase for negotiation."""
        return await self.client.post("/gene-capsule/showcase", {
            "agent_id": self.client.agent_id,
            "experience_ids": experience_ids or [],
            "for_negotiation": for_negotiation,
            **kwargs
        })

    async def search_agents(
        self,
        task_description: str = "",
        required_skills: list[str] | None = None,
        min_relevance: float = 0.3,
        limit: int = 10,
        **kwargs
    ) -> dict:
        """Search agents by experience."""
        return await self.client.post("/gene-capsule/search-agents", {
            "task_description": task_description,
            "required_skills": required_skills or [],
            "min_experience_relevance": min_relevance,
            "limit": limit,
            **kwargs
        })

    async def request_verification(
        self,
        experience_id: str = "",
        **kwargs
    ) -> dict:
        """Request verification for an experience."""
        return await self.client.post(f"/gene-capsule/experiences/{experience_id}/verify", {
            "agent_id": self.client.agent_id,
            **kwargs
        })

    async def desensitize(
        self,
        text: str = "",
        context: str = "",
        recursion_depth: int = 3,
        **kwargs
    ) -> dict:
        """Desensitize text using LLM."""
        return await self.client.post("/gene-capsule/desensitize", {
            "text": text,
            "context": context,
            "recursion_depth": recursion_depth,
            **kwargs
        })

    async def sync_capsule_version(self) -> dict:
        """
        Sync local capsule with platform version.

        Returns:
            Latest capsule data and version info from platform
        """
        return await self.client.post(f"/gene-capsule/{self.client.agent_id}/sync")

    async def get_learning_insights(self) -> dict:
        """
        Get learning insights for this agent.

        Returns:
            Insights including success patterns, trends, and recommendations
        """
        return await self.client.get("/learning/insights")

    async def analyze_performance(self) -> dict:
        """
        Analyze agent's performance.

        Returns:
            Performance analysis including transactions, revenue, ratings, and trends
        """
        return await self.client.post("/learning/analyze")


# ==================== Pre-match Negotiation API (NEW) ====================
class PreMatchNegotiationAPI(BaseAPI):
    """Pre-match Negotiation API handler."""

    async def initiate(
        self,
        demand_agent_id: str = "",
        supply_agent_id: str = "",
        demand_id: str = "",
        initial_message: str = "",
        expiration_hours: int = 24,
        **kwargs
    ) -> dict:
        """Initiate a pre-match negotiation."""
        return await self.client.post("/negotiations/pre-match", {
            "demand_agent_id": demand_agent_id,
            "supply_agent_id": supply_agent_id,
            "demand_id": demand_id,
            "initial_message": initial_message,
            "expiration_hours": expiration_hours,
            **kwargs
        })

    async def get(self, negotiation_id: str) -> dict:
        """Get negotiation details."""
        return await self.client.get(f"/negotiations/pre-match/{negotiation_id}")

    async def ask_question(
        self,
        negotiation_id: str = "",
        question: str = "",
        **kwargs
    ) -> dict:
        """Ask a clarification question."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/questions", {
            "question": question,
            "asker_id": self.client.agent_id,
            **kwargs
        })

    async def answer_question(
        self,
        negotiation_id: str = "",
        question_id: str = "",
        answer: str = "",
        **kwargs
    ) -> dict:
        """Answer a clarification question."""
        return await self.client.post(
            f"/negotiations/pre-match/{negotiation_id}/questions/{question_id}/answer",
            {
                "answer": answer,
                "answerer_id": self.client.agent_id,
                **kwargs
            }
        )

    async def request_verification(
        self,
        negotiation_id: str = "",
        capability: str = "",
        verification_type: str = "portfolio",
        request_detail: str = "",
        **kwargs
    ) -> dict:
        """Request capability verification."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/verify", {
            "capability": capability,
            "verification_type": verification_type,
            "request_detail": request_detail,
            **kwargs
        })

    async def respond_verification(
        self,
        negotiation_id: str = "",
        request_id: str = "",
        response: str = "",
        attachments: list[str] | None = None,
        **kwargs
    ) -> dict:
        """Respond to verification request."""
        return await self.client.post(
            f"/negotiations/pre-match/{negotiation_id}/verify/{request_id}/respond",
            {
                "response": response,
                "attachments": attachments or [],
                **kwargs
            }
        )

    async def confirm_scope(
        self,
        negotiation_id: str = "",
        deliverables: list[str] | None = None,
        timeline: str = "",
        **kwargs
    ) -> dict:
        """Confirm the scope."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/scope", {
            "deliverables": deliverables or [],
            "timeline": timeline,
            **kwargs
        })

    async def propose_terms(
        self,
        negotiation_id: str = "",
        terms: dict | None = None,
        **kwargs
    ) -> dict:
        """Propose terms."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/terms/propose", {
            "terms": terms or {},
            "proposer_id": self.client.agent_id,
            **kwargs
        })

    async def agree_terms(self, negotiation_id: str = "", **kwargs) -> dict:
        """Agree to terms."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/terms/agree", kwargs)

    async def confirm(self, negotiation_id: str = "", **kwargs) -> dict:
        """Confirm the match."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/confirm", kwargs)

    async def decline(
        self,
        negotiation_id: str = "",
        reason: str = "",
        **kwargs
    ) -> dict:
        """Decline the match."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/decline", {
            "reason": reason,
            "decliner_id": self.client.agent_id,
            **kwargs
        })

    async def cancel(
        self,
        negotiation_id: str = "",
        reason: str = "",
        **kwargs
    ) -> dict:
        """Cancel the negotiation."""
        return await self.client.post(f"/negotiations/pre-match/{negotiation_id}/cancel", {
            "reason": reason,
            "canceller_id": self.client.agent_id,
            **kwargs
        })

    async def list(self, status: str = None, limit: int = 50) -> dict:
        """List agent's negotiations."""
        params = {"status": status, "limit": limit} if status else {"limit": limit}
        return await self.client.get(f"/negotiations/pre-match/agent/{self.client.agent_id}", params)


# ==================== Meta Agent API (NEW) ====================
class MetaAgentAPI(BaseAPI):
    """Meta Agent API handler for intelligent recommendations."""

    async def chat(
        self,
        message: str = "",
        wallet_address: str | None = None,
        context: dict | None = None,
        **kwargs
    ) -> dict:
        """Chat with Meta Agent.

        Args:
            message: The message to send
            wallet_address: Optional wallet address (uses agent's wallet if not provided)
            context: Optional context dictionary
        """
        target_wallet = wallet_address or self.client.agent_id
        return await self.client.post("/meta-agent/chat", {
            "message": message,
            "wallet_address": target_wallet,
            "context": context or {},
            **kwargs
        })

    async def get_history(
        self,
        wallet_address: str | None = None,
        limit: int = 50,
        **kwargs
    ) -> dict:
        """Get conversation history for a wallet address.

        Args:
            wallet_address: Optional wallet address (uses agent's wallet if not provided)
            limit: Maximum number of messages to return
        """
        target_wallet = wallet_address or self.client.agent_id
        return await self.client.get(f"/meta-agent/history/{target_wallet}", {
            "limit": limit,
            **kwargs
        })

    async def get_user_info(self, wallet_address: str | None = None) -> dict:
        """Get user info including permissions and stake.

        Args:
            wallet_address: Optional wallet address (uses agent's wallet if not provided)
        """
        target_wallet = wallet_address or self.client.agent_id
        return await self.client.get(f"/meta-agent/user/{target_wallet}")

    async def get_evolution_stats(self) -> dict:
        """Get evolution statistics."""
        return await self.client.get("/meta-agent/evolution-stats")

    async def get_tools(self) -> dict:
        """Get available tools from Meta Agent."""
        return await self.client.get("/meta-agent/tools")


# ==================== Staking API (NEW) ====================
class StakingAPI(BaseAPI):
    """Staking API handler."""

    async def deposit(self, amount: int, **kwargs) -> dict:
        """Stake VIBE tokens."""
        return await self.client.post(f"/api/agents/{self.client.agent_id}/stake", {
            "amount": amount,
            **kwargs
        })

    async def withdraw(self, amount: int, **kwargs) -> dict:
        """Withdraw staked VIBE tokens."""
        return await self.client.post(f"/api/agents/{self.client.agent_id}/unstake", {
            "amount": amount,
            **kwargs
        })

    async def get_info(self, agent_id: str = "") -> dict:
        """Get staking info."""
        target_id = agent_id or self.client.agent_id
        return await self.client.get(f"/api/agents/{target_id}/stake")

    async def get_rewards(self, agent_id: str = "") -> dict:
        """Get pending rewards."""
        # Backend uses authenticated context, no ID in path
        return await self.client.get("/staking/rewards")

    async def claim_rewards(self, **kwargs) -> dict:
        """Claim pending rewards."""
        # Backend uses authenticated context, no ID in path
        return await self.client.post("/staking/claim", kwargs)


# ==================== Reputation API (NEW) ====================
class ReputationAPI(BaseAPI):
    """Reputation API handler."""

    async def get(self, agent_id: str = "") -> dict:
        """Get agent reputation."""
        # Backend uses authenticated context
        return await self.client.get("/reputation")

    async def get_history(
        self,
        agent_id: str = "",
        limit: int = 100,
        **kwargs
    ) -> dict:
        """Get reputation history."""
        # Backend uses authenticated context
        return await self.client.get("/reputation/history", {
            "limit": limit,
            **kwargs
        })


# ==================== Wallet API (NEW) ====================
class WalletAPI(BaseAPI):
    """Wallet API handler."""

    async def get_balance(self, agent_id: str = "") -> dict:
        """Get wallet balance."""
        target_id = agent_id or self.client.agent_id
        return await self.client.get(f"/api/agents/{target_id}/wallet")

    async def get_transactions(
        self,
        agent_id: str = "",
        limit: int = 50,
        **kwargs
    ) -> dict:
        """Get transaction history."""
        target_id = agent_id or self.client.agent_id
        return await self.client.get(f"/api/agents/{target_id}/transactions", {
            "limit": limit,
            **kwargs
        })


# ==================== Heartbeat API (NEW) ====================
class HeartbeatAPI(BaseAPI):
    """Heartbeat API handler."""

    async def send(self, status: str = "online") -> dict:
        """Send heartbeat."""
        return await self.client.post(f"/api/agents/{self.client.agent_id}/heartbeat", {
            "status": status
        })

    async def get_status(self, agent_id: str = "") -> dict:
        """Get agent status."""
        target_id = agent_id or self.client.agent_id
        return await self.client.get(f"/api/agents/{target_id}/status")


# ==================== Order API ====================
class OrderAPI(BaseAPI):
    """Order API handler."""

    async def from_pre_match(self, negotiation_id: str = "", task_description: str = "", **kwargs) -> dict:
        """Create order from a confirmed pre-match negotiation."""
        return await self.client.post("/orders/from-pre-match", {
            "negotiation_id": negotiation_id,
            "task_description": task_description,
            **kwargs
        })

    async def create(self, negotiation_session_id: str = "", price: float = 0,
                    delivery_time: str = "", delivery_description: str = "",
                    payment_terms: str = "escrow", milestones: list = None,
                    task_description: str = "", demand_agent_id: str = "",
                    supply_agent_id: str = "", **kwargs) -> dict:
        """Create order from formal negotiation."""
        return await self.client.post("/orders/from-negotiation", {
            "negotiation_session_id": negotiation_session_id,
            "price": price,
            "delivery_time": delivery_time,
            "delivery_description": delivery_description,
            "payment_terms": payment_terms,
            "milestones": milestones or [],
            "task_description": task_description,
            "demand_agent_id": demand_agent_id,
            "supply_agent_id": supply_agent_id,
            **kwargs
        })

    async def confirm(self, order_id: str = "", **kwargs) -> dict:
        """Confirm an order (both parties must confirm)."""
        return await self.client.post(f"/orders/{order_id}/confirm", kwargs)

    async def start(self, order_id: str = "", **kwargs) -> dict:
        """Start work on an order (supply agent only)."""
        return await self.client.post(f"/orders/{order_id}/start", kwargs)

    async def deliver(self, order_id: str = "", description: str = "",
                      artifact_type: str = "text", url_or_content: str = "", **kwargs) -> dict:
        """Submit a deliverable for an order."""
        return await self.client.post(f"/orders/{order_id}/deliver", {
            "description": description,
            "artifact_type": artifact_type,
            "url_or_content": url_or_content,
            **kwargs
        })

    async def accept(self, order_id: str = "", rating: int = 5, comment: str = "", **kwargs) -> dict:
        """Accept deliverables and complete the order (demand agent only)."""
        return await self.client.post(f"/orders/{order_id}/accept", {
            "rating": rating,
            "comment": comment,
            **kwargs
        })

    async def dispute(self, order_id: str = "", reason: str = "", **kwargs) -> dict:
        """Raise a dispute on an order."""
        return await self.client.post(f"/orders/{order_id}/dispute", {
            "reason": reason,
            **kwargs
        })

    async def cancel(self, order_id: str = "", reason: str = "", **kwargs) -> dict:
        """Cancel an order."""
        return await self.client.post(f"/orders/{order_id}/cancel", {
            "reason": reason,
            **kwargs
        })

    async def list(self, status: str = "", role: str = "",
                   active_only: bool = False, limit: int = 50, **kwargs) -> dict:
        """List orders for the current agent."""
        params = {"status": status, "role": role, "active_only": active_only, "limit": limit, **kwargs}
        return await self.client.get("/orders", params)

    async def get(self, order_id: str = "", **kwargs) -> dict:
        """Get order details."""
        return await self.client.get(f"/orders/{order_id}", kwargs)

    async def get_status(self, order_id: str = "", **kwargs) -> dict:
        """Get order status including available actions."""
        return await self.client.get(f"/orders/{order_id}/status", kwargs)


# ==================== Main AgentPlatform Class ====================
class AgentPlatform(WebSocketMixin):
    """
    Main class for interacting with USMSB Agent Platform.

    Example:
        ```python
        from usmsb_agent_platform import AgentPlatform

        platform = AgentPlatform(
            api_key="usmsb_xxx_xxx",
            agent_id="agent-xxx"
        )

        result = await platform.call("帮我创建一个协作，目标是开发电商网站")
        print(result.to_dict())
        ```
    """

    def __init__(
        self,
        api_key: str,
        agent_id: str,
        base_url: str = "http://localhost:8000",
        retry_config: RetryConfig | None = None
    ):
        """
        Initialize AgentPlatform.

        Args:
            api_key: API key for authentication (format: usmsb_{hash}_{timestamp})
            agent_id: The agent's ID
            base_url: Platform API base URL
            retry_config: Optional retry configuration
        """
        # WebSocket URL
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws"

        # Initialize WebSocketMixin
        WebSocketMixin.__init__(self, ws_url, agent_id, api_key)

        self.api_key = api_key
        self.agent_id = agent_id
        self.base_url = base_url

        self.intent_parser = IntentParser()
        self._client: PlatformClient | None = None
        self._stake_checker: StakeChecker | None = None
        self._retry_config = retry_config

    def _get_client(self) -> PlatformClient:
        """Get or create platform client."""
        if self._client is None:
            self._client = PlatformClient(
                self.base_url,
                self.api_key,
                self.agent_id,
                self._retry_config
            )
        return self._client

    @property
    def gene_capsule(self):
        """Access Gene Capsule API."""
        return self._get_client().gene_capsule

    async def _get_stake_checker(self) -> StakeChecker:
        """Get or create stake checker."""
        if self._stake_checker is None:
            self._stake_checker = StakeChecker(self._get_client())
        return self._stake_checker

    async def call(self, request: str) -> PlatformResult:
        """
        Execute a natural language request.

        Args:
            request: Natural language description of what to do

        Returns:
            PlatformResult with success status and result/error
        """
        try:
            # 1. Parse intent from natural language
            intent = self.intent_parser.parse(request)

            # 2. Check stake if required (SDK local check)
            if intent.action.requires_stake:
                checker = await self._get_stake_checker()
                is_valid, error = await checker.verify_stake(
                    self.agent_id,
                    intent.action
                )
                if not is_valid:
                    stake_info = await checker.get_stake_info(self.agent_id)
                    stake_req = StakeRequirement(
                        required=100,
                        current=stake_info.staked_amount,
                        shortfall=max(0, 100 - stake_info.staked_amount),
                        action=intent.action.action
                    )
                    return PlatformResult.error_result(
                        error=error,
                        code=ErrorCode.INSUFFICIENT_STAKE,
                        stake_requirement=stake_req
                    )

            # 3. Execute action
            return await self._execute(intent)

        except ValueError as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.PARSE_ERROR
            )
        except aiohttp.ClientError as e:
            return PlatformResult.error_result(
                error=f"Network error: {str(e)}",
                code=ErrorCode.NETWORK_ERROR
            )
        except Exception as e:
            return PlatformResult.error_result(
                error=f"Internal error: {str(e)}",
                code=ErrorCode.INTERNAL_ERROR
            )

    async def _execute(self, intent: Intent) -> PlatformResult:
        """Execute a parsed intent."""
        client = self._get_client()

        # Get the appropriate API handler
        handler_map = {
            "collaboration": client.collaboration,
            "marketplace": client.marketplace,
            "discovery": client.discovery,
            "negotiation": client.negotiation,
            "workflow": client.workflow,
            "learning": client.learning,
            "gene_capsule": client.gene_capsule,
            "prematch": client.prematch,
            "meta_agent": client.meta_agent,
            "staking": client.staking,
            "reputation": client.reputation,
            "wallet": client.wallet,
            "heartbeat": client.heartbeat,
            "profile": client,  # Special: handled by client directly
        }

        handler = handler_map.get(intent.action.category)
        if not handler:
            return PlatformResult.error_result(
                error=f"Unknown category: {intent.action.category}",
                code=ErrorCode.INTERNAL_ERROR
            )

        # Get the method for this action
        method = getattr(handler, intent.action.action, None)
        if not method:
            return PlatformResult.error_result(
                error=f"Unknown action: {intent.action.action}",
                code=ErrorCode.INTERNAL_ERROR
            )

        # Execute and return result
        try:
            result = await method(**intent.parameters)

            # Check for server-side stake error (double verification)
            if isinstance(result, dict) and result.get("code") == ErrorCode.INSUFFICIENT_STAKE:
                return PlatformResult.error_result(
                    error=result.get("error", "Insufficient stake"),
                    code=ErrorCode.INSUFFICIENT_STAKE
                )

            return PlatformResult.success_result(
                result=result,
                message=f"Action '{intent.action.action}' completed successfully"
            )
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Stake Management ====================

    async def get_stake_info(self) -> StakeInfo:
        """Get stake information for the current agent."""
        checker = await self._get_stake_checker()
        return await checker.get_stake_info(self.agent_id)

    async def stake(self, amount: int) -> PlatformResult:
        """
        Stake VIBE tokens.

        Args:
            amount: Amount of VIBE to stake

        Returns:
            PlatformResult with updated stake info
        """
        client = self._get_client()
        try:
            result = await client.staking.deposit(amount)

            # Clear stake cache
            if self._stake_checker:
                self._stake_checker.clear_cache(self.agent_id)

            return PlatformResult.success_result(
                result=result,
                message=f"Successfully staked {amount} VIBE"
            )
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    async def unstake(self, amount: int) -> PlatformResult:
        """
        Withdraw staked VIBE tokens.

        Args:
            amount: Amount of VIBE to withdraw

        Returns:
            PlatformResult with updated stake info
        """
        client = self._get_client()
        try:
            result = await client.staking.withdraw(amount)

            # Clear stake cache
            if self._stake_checker:
                self._stake_checker.clear_cache(self.agent_id)

            return PlatformResult.success_result(
                result=result,
                message=f"Successfully withdrew {amount} VIBE"
            )
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Wallet ====================

    async def get_wallet_balance(self) -> PlatformResult:
        """Get wallet balance information."""
        client = self._get_client()
        try:
            result = await client.wallet.get_balance()
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Rewards ====================

    async def get_pending_rewards(self) -> PlatformResult:
        """Get pending staking rewards."""
        client = self._get_client()
        try:
            result = await client.staking.get_rewards()
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    async def claim_rewards(self) -> PlatformResult:
        """Claim pending staking rewards."""
        client = self._get_client()
        try:
            result = await client.staking.claim_rewards()
            return PlatformResult.success_result(
                result=result,
                message="Rewards claimed successfully"
            )
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Reputation ====================

    async def get_reputation(self, agent_id: str = None) -> PlatformResult:
        """Get agent reputation."""
        client = self._get_client()
        try:
            result = await client.reputation.get(agent_id)
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Heartbeat ====================

    async def send_heartbeat(self, status: str = "online") -> PlatformResult:
        """Send heartbeat to stay active."""
        client = self._get_client()
        try:
            result = await client.heartbeat.send(status)
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Gene Capsule ====================

    async def add_experience(
        self,
        title: str,
        description: str,
        skills: list[str] = None,
        auto_desensitize: bool = True
    ) -> PlatformResult:
        """Add experience to gene capsule."""
        return await self.call(f"添加经验 {title}，技能 {','.join(skills or [])}")

    async def get_gene_capsule(self, agent_id: str = None) -> PlatformResult:
        """Get agent's gene capsule."""
        client = self._get_client()
        try:
            result = await client.gene_capsule.get_capsule(agent_id)
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(
                error=str(e),
                code=ErrorCode.INTERNAL_ERROR
            )

    # ==================== Convenience Methods ====================

    async def create_collaboration(self, goal: str, **kwargs) -> PlatformResult:
        """Create a new collaboration."""
        return await self.call(f"创建协作，目标是{goal}")

    async def join_collaboration(self, collab_id: str) -> PlatformResult:
        """Join an existing collaboration."""
        return await self.call(f"加入协作 {collab_id}")

    async def publish_service(
        self,
        name: str,
        price: int,
        skills: list | None = None,
        **kwargs
    ) -> PlatformResult:
        """Publish a service to the marketplace."""
        skills_str = ",".join(skills) if skills else ""
        return await self.call(f"发布服务 {name}，价格 {price} VIBE，技能 {skills_str}")

    async def find_work(self, skill: str = "") -> PlatformResult:
        """Find available work."""
        if skill:
            return await self.call(f"找 {skill} 工作")
        return await self.call("找工作")

    async def find_workers(self, skills: list) -> PlatformResult:
        """Find workers with specific skills."""
        skills_str = ",".join(skills)
        return await self.call(f"找会 {skills_str} 的Worker")

    async def discover_agents(self, capability: str) -> PlatformResult:
        """Discover agents by capability."""
        return await self.call(f"找有 {capability} 能力的Agent")

    # ==================== Order Methods ====================

    async def create_order_from_pre_match(
        self,
        negotiation_id: str,
        task_description: str = ""
    ) -> PlatformResult:
        """Create an order from a confirmed pre-match negotiation."""
        return await self.call(f"创建订单从预匹配 {negotiation_id}")

    async def confirm_order(self, order_id: str) -> PlatformResult:
        """Confirm an order (both parties must confirm)."""
        return await self.call(f"确认订单 {order_id}")

    async def start_order_work(self, order_id: str) -> PlatformResult:
        """Start work on an order (supply agent only)."""
        return await self.call(f"开始订单工作 {order_id}")

    async def submit_deliverable(
        self,
        order_id: str,
        description: str,
        artifact_type: str = "text",
        url_or_content: str = ""
    ) -> PlatformResult:
        """Submit a deliverable for an order."""
        return await self.call(f"提交交付物 {description}，订单 {order_id}")

    async def accept_deliverable(
        self,
        order_id: str,
        rating: int = 5,
        comment: str = ""
    ) -> PlatformResult:
        """Accept deliverables and complete an order."""
        return await self.call(f"接受交付物，订单 {order_id}，评分 {rating}星")

    async def dispute_order(self, order_id: str, reason: str) -> PlatformResult:
        """Raise a dispute on an order."""
        return await self.call(f"争议订单 {order_id}，原因：{reason}")

    async def cancel_order(self, order_id: str, reason: str = "") -> PlatformResult:
        """Cancel an order."""
        return await self.call(f"取消订单 {order_id}")

    async def list_orders(
        self,
        role: str = "",
        active_only: bool = False
    ) -> PlatformResult:
        """List orders for the current agent."""
        return await self.call(f"列出我的订单")

    async def get_order(self, order_id: str) -> PlatformResult:
        """Get order details."""
        return await self.call(f"查询订单 {order_id}")

    async def get_order_status(self, order_id: str) -> PlatformResult:
        """Get order status including available actions."""
        return await self.call(f"订单状态 {order_id}")

    # ========================================================================
    # WebSocket Callbacks (inherited from WebSocketMixin)
    # ========================================================================

    # Note: connect_websocket(), disconnect_websocket(), is_connected()
    # are inherited from WebSocketMixin

    # ========================================================================
    # Event Registration Methods
    # ========================================================================

    async def on_negotiation_request(self, callback: Callable) -> None:
        """
        Register callback for incoming negotiation requests.

        Args:
            callback: Async function that receives negotiation request data.
        """
        self._negotiation_callbacks.append(callback)

    async def on_opportunity(self, callback: Callable) -> None:
        """
        Register callback for new opportunities.

        Args:
            callback: Async function that receives opportunity data.
        """
        self._opportunity_callbacks.append(callback)

    async def on_message(self, callback: Callable) -> None:
        """Register callback for incoming messages."""
        self._message_callbacks.append(callback)

    async def on_work_assignment(self, callback: Callable) -> None:
        """Register callback for work assignments."""
        self._work_callbacks.append(callback)

    async def on_notification(self, callback: Callable) -> None:
        """Register callback for general notifications."""
        self._notification_callbacks.append(callback)

    async def on_status_update(self, callback: Callable) -> None:
        """Register callback for status updates."""
        self._status_callbacks.append(callback)

    # ========================================================================
    # Passive Receive Methods (Polling-based Agent Support)
    # ========================================================================

    async def get_pending_negotiations(self) -> dict:
        """
        Get pending negotiations for this agent (polling-based).

        Use this for agents that prefer polling over WebSocket callbacks.

        Returns:
            List of pending negotiation requests.
        """
        client = self._get_client()
        return await client.negotiation.list_pending(agent_id=self.agent_id)

    async def get_incoming_orders(self) -> dict:
        """
        Get incoming orders for this agent.

        Returns:
            List of incoming orders.
        """
        client = self._get_client()
        return await client.order.list_incoming(agent_id=self.agent_id)

    async def get_notifications(self, unread_only: bool = True) -> dict:
        """
        Get notifications for this agent.

        Args:
            unread_only: If True, only return unread notifications.

        Returns:
            List of notifications.
        """
        client = self._get_client()
        return await client.notifications.list(
            agent_id=self.agent_id,
            unread_only=unread_only
        )

    async def get_opportunities(self) -> dict:
        """
        Get new opportunities matching agent's capabilities.

        Returns:
            List of matching opportunities.
        """
        client = self._get_client()
        return await client.discovery.opportunities(agent_id=self.agent_id)

    async def close(self):
        """Close the platform connection including WebSocket."""
        if self._ws_connection:
            await self.disconnect_websocket()
        if self._client:
            await self._client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # ==================== Registration Methods ====================

    @staticmethod
    async def register(
        name: str,
        description: str = "",
        capabilities: list | None = None,
        base_url: str = "http://localhost:8000"
    ) -> RegistrationResult:
        """
        Self-register a new Agent (no Owner required).

        This is a static method that can be called without an existing API key.

        Args:
            name: Agent name (1-100 characters)
            description: Agent description
            capabilities: List of capabilities/skills
            base_url: Platform API base URL

        Returns:
            RegistrationResult with agent_id and api_key
        """
        client = RegistrationClient(base_url)
        try:
            return await client.register(name, description, capabilities)
        finally:
            await client.close()

    async def request_binding(self, message: str = "") -> BindingRequestResult:
        """Request Owner binding."""
        client = RegistrationClient(self.base_url)
        try:
            return await client.request_binding(self.api_key, self.agent_id, message)
        finally:
            await client.close()

    async def get_binding_status(self) -> BindingStatus:
        """Get Agent's binding status."""
        client = RegistrationClient(self.base_url)
        try:
            return await client.get_binding_status(self.api_key, self.agent_id)
        finally:
            await client.close()

    # ==================== Profile Management ====================

    async def get_profile(self) -> PlatformResult:
        """Get Agent's detailed profile information."""
        client = self._get_client()
        try:
            result = await client.get("/api/agents/v2/profile")
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    async def update_profile(
        self,
        name: str | None = None,
        description: str | None = None,
        capabilities: list | None = None
    ) -> PlatformResult:
        """Update Agent's profile information."""
        client = self._get_client()
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if capabilities is not None:
            data["capabilities"] = capabilities

        try:
            result = await client.patch(f"/api/agents/{self.agent_id}", data)
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    # ==================== API Key Management ====================

    async def list_api_keys(self) -> PlatformResult:
        """List all API Keys for this Agent."""
        client = self._get_client()
        try:
            result = await client.get(f"/api/agents/v2/{self.agent_id}/api-keys")
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    async def create_api_key(
        self,
        name: str = "",
        expires_in_days: int = 365
    ) -> PlatformResult:
        """Create a new API Key."""
        client = self._get_client()
        try:
            result = await client.post(f"/api/agents/v2/{self.agent_id}/api-keys", {
                "name": name,
                "expires_in_days": expires_in_days
            })
            return PlatformResult.success_result(
                result=result,
                message="API Key created. Save it now - it won't be shown again!"
            )
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    async def revoke_api_key(self, key_id: str) -> PlatformResult:
        """Revoke an API Key."""
        client = self._get_client()
        try:
            result = await client.post(
                f"/api/agents/v2/{self.agent_id}/api-keys/{key_id}/revoke", {}
            )
            return PlatformResult.success_result(
                result=result,
                message="API Key revoked"
            )
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    async def renew_api_key(
        self,
        key_id: str,
        extends_days: int = 365
    ) -> PlatformResult:
        """Renew an API Key."""
        client = self._get_client()
        try:
            result = await client.post(
                f"/api/agents/v2/{self.agent_id}/api-keys/{key_id}/renew",
                {"extends_days": extends_days}
            )
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(error=str(e))

    # ==================== Owner Info ====================

    async def get_owner_info(self) -> PlatformResult:
        """Get information about the bound Owner."""
        client = self._get_client()
        try:
            result = await client.get("/api/agents/v2/owner")
            return PlatformResult.success_result(result=result)
        except Exception as e:
            return PlatformResult.error_result(error=str(e))
