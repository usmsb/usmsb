"""
Agent Discovery Module

Implements the discovery system for finding and recommending agents, including:
- Skill-based discovery
- Capability-based discovery
- Keyword and tag search
- Recommendation algorithm
- Agent ranking and scoring
- Multi-dimensional search (capability/price/reputation/availability)
- Semantic matching (understanding task intent)
- Experience-based discovery via Gene Capsule
- Real-time monitoring (service status changes)
- Batch comparison analysis
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from uuid import uuid4
from urllib.parse import quote
import asyncio
import aiohttp
import json
import logging
import re
from collections import defaultdict

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    ProtocolType,
    SkillDefinition,
)
from usmsb_sdk.agent_sdk.communication import CommunicationManager, Message, MessageType


class DiscoveryScope(Enum):
    """Scope of discovery search"""
    LOCAL = "local"  # Only locally known agents
    PLATFORM = "platform"  # Platform registry
    NETWORK = "network"  # Full network including P2P
    ALL = "all"


class SortBy(Enum):
    """Sort options for discovery results"""
    RELEVANCE = "relevance"
    RATING = "rating"
    LATENCY = "latency"
    LAST_SEEN = "last_seen"
    NAME = "name"


@dataclass
class DiscoveryFilter:
    """Filter criteria for agent discovery"""
    skills: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    protocols: Optional[List[ProtocolType]] = None
    min_rating: Optional[float] = None
    max_latency: Optional[float] = None
    online_only: bool = True
    exclude_self: bool = True
    exclude_ids: Optional[Set[str]] = None
    include_only: Optional[Set[str]] = None
    categories: Optional[List[str]] = None
    capability_levels: Optional[Dict[str, str]] = None  # capability -> min level
    scope: DiscoveryScope = DiscoveryScope.PLATFORM
    sort_by: SortBy = SortBy.RELEVANCE
    limit: int = 100
    offset: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "skills": self.skills,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "keywords": self.keywords,
            "protocols": [p.value for p in self.protocols] if self.protocols else None,
            "min_rating": self.min_rating,
            "max_latency": self.max_latency,
            "online_only": self.online_only,
            "exclude_self": self.exclude_self,
            "exclude_ids": list(self.exclude_ids) if self.exclude_ids else None,
            "include_only": list(self.include_only) if self.include_only else None,
            "categories": self.categories,
            "capability_levels": self.capability_levels,
            "scope": self.scope.value,
            "sort_by": self.sort_by.value,
            "limit": self.limit,
            "offset": self.offset,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiscoveryFilter":
        """Create from dictionary"""
        return cls(
            skills=data.get("skills"),
            capabilities=data.get("capabilities"),
            tags=data.get("tags"),
            keywords=data.get("keywords"),
            protocols=[ProtocolType(p) for p in data["protocols"]] if data.get("protocols") else None,
            min_rating=data.get("min_rating"),
            max_latency=data.get("max_latency"),
            online_only=data.get("online_only", True),
            exclude_self=data.get("exclude_self", True),
            exclude_ids=set(data["exclude_ids"]) if data.get("exclude_ids") else None,
            include_only=set(data["include_only"]) if data.get("include_only") else None,
            categories=data.get("categories"),
            capability_levels=data.get("capability_levels"),
            scope=DiscoveryScope(data.get("scope", "platform")),
            sort_by=SortBy(data.get("sort_by", "relevance")),
            limit=data.get("limit", 100),
            offset=data.get("offset", 0),
        )


@dataclass
class AgentInfo:
    """Information about a discovered agent"""
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    skills: List[Dict[str, Any]] = field(default_factory=list)
    capabilities: List[Dict[str, Any]] = field(default_factory=list)
    protocols: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    rating: float = 0.0
    latency: float = 0.0
    last_seen: Optional[datetime] = None
    is_online: bool = False
    endpoint: Optional[str] = None
    p2p_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    score: float = 0.0  # Computed relevance score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "skills": self.skills,
            "capabilities": self.capabilities,
            "protocols": self.protocols,
            "tags": self.tags,
            "rating": self.rating,
            "latency": self.latency,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_online": self.is_online,
            "endpoint": self.endpoint,
            "p2p_endpoint": self.p2p_endpoint,
            "metadata": self.metadata,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInfo":
        """Create from dictionary"""
        return cls(
            agent_id=data["agent_id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            skills=data.get("skills", []),
            capabilities=data.get("capabilities", []),
            protocols=data.get("protocols", []),
            tags=data.get("tags", []),
            rating=data.get("rating", 0.0),
            latency=data.get("latency", 0.0),
            last_seen=datetime.fromisoformat(data["last_seen"]) if isinstance(data.get("last_seen"), str) else data.get("last_seen"),
            is_online=data.get("is_online", False),
            endpoint=data.get("endpoint"),
            p2p_endpoint=data.get("p2p_endpoint"),
            metadata=data.get("metadata", {}),
            score=data.get("score", 0.0),
        )

    def has_skill(self, skill_name: str) -> bool:
        """Check if agent has a specific skill"""
        return any(s.get("name") == skill_name for s in self.skills)

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability"""
        return any(c.get("name") == capability_name for c in self.capabilities)

    def get_skill(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Get skill by name"""
        for skill in self.skills:
            if skill.get("name") == skill_name:
                return skill
        return None

    def get_capability(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Get capability by name"""
        for cap in self.capabilities:
            if cap.get("name") == capability_name:
                return cap
        return None


@dataclass
class RecommendationResult:
    """Result of a recommendation query"""
    task_description: str
    recommended_agents: List[AgentInfo]
    total_candidates: int
    algorithm: str
    confidence: float
    explanations: Dict[str, str] = field(default_factory=dict)  # agent_id -> explanation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_description": self.task_description,
            "recommended_agents": [a.to_dict() for a in self.recommended_agents],
            "total_candidates": self.total_candidates,
            "algorithm": self.algorithm,
            "confidence": self.confidence,
            "explanations": self.explanations,
        }


class DiscoveryManager:
    """
    Manages agent discovery and recommendation.

    Features:
    - Skill-based agent discovery
    - Capability-based agent discovery
    - Keyword and tag search
    - Recommendation algorithm
    - Local caching of discovered agents
    - P2P discovery support
    """

    # Capability level hierarchy
    CAPABILITY_LEVELS = {
        "basic": 1,
        "intermediate": 2,
        "advanced": 3,
        "expert": 4,
    }

    def __init__(
        self,
        agent_id: str,
        agent_config: AgentConfig,
        communication_manager: CommunicationManager,
        logger: Optional[logging.Logger] = None,
    ):
        self.agent_id = agent_id
        self.config = agent_config
        self.comm_manager = communication_manager
        self.logger = logger or logging.getLogger(__name__)

        # Cache
        self._agent_cache: Dict[str, AgentInfo] = {}
        self._cache_expiry: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=5)

        # HTTP session
        self._http_session: Optional[aiohttp.ClientSession] = None

        # State
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize discovery manager"""
        if self._initialized:
            return

        self._http_session = aiohttp.ClientSession()
        self._initialized = True
        self.logger.info(f"Discovery manager initialized for agent {self.agent_id}")

    async def close(self) -> None:
        """Close discovery manager"""
        if self._http_session:
            await self._http_session.close()
        self._initialized = False

    # ==================== Discovery Methods ====================

    async def discover(self, filter_criteria: Optional[DiscoveryFilter] = None) -> List[AgentInfo]:
        """
        Discover agents matching the given criteria.

        Args:
            filter_criteria: Filter for discovery

        Returns:
            List of matching agents
        """
        if not self._initialized:
            raise RuntimeError("Discovery manager not initialized")

        filter_criteria = filter_criteria or DiscoveryFilter()

        # Exclude self if requested
        if filter_criteria.exclude_self:
            if filter_criteria.exclude_ids:
                filter_criteria.exclude_ids.add(self.agent_id)
            else:
                filter_criteria.exclude_ids = {self.agent_id}

        # Get agents based on scope
        if filter_criteria.scope == DiscoveryScope.LOCAL:
            agents = await self._discover_local(filter_criteria)
        elif filter_criteria.scope == DiscoveryScope.PLATFORM:
            agents = await self._discover_platform(filter_criteria)
        elif filter_criteria.scope == DiscoveryScope.NETWORK:
            agents = await self._discover_network(filter_criteria)
        else:
            # ALL scope - combine all sources
            local_agents = await self._discover_local(filter_criteria)
            platform_agents = await self._discover_platform(filter_criteria)
            network_agents = await self._discover_network(filter_criteria)

            # Merge results
            agents = self._merge_discoveries([local_agents, platform_agents, network_agents])

        # Apply filters
        agents = self._apply_filters(agents, filter_criteria)

        # Score and sort
        agents = self._score_agents(agents, filter_criteria)
        agents = self._sort_agents(agents, filter_criteria.sort_by)

        # Apply pagination
        start = filter_criteria.offset
        end = start + filter_criteria.limit

        return agents[start:end]

    async def _discover_local(self, filter_criteria: DiscoveryFilter) -> List[AgentInfo]:
        """Discover from local cache"""
        agents = []
        now = datetime.now()

        for agent_id, agent_info in self._agent_cache.items():
            # Check cache expiry
            if agent_id in self._cache_expiry:
                if now > self._cache_expiry[agent_id]:
                    continue

            agents.append(agent_info)

        return agents

    async def _discover_platform(self, filter_criteria: DiscoveryFilter) -> List[AgentInfo]:
        """Discover from platform registry"""
        if not self._http_session:
            return []

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        try:
            # Build query parameters
            params = {}
            if filter_criteria.skills:
                params["skills"] = ",".join(filter_criteria.skills)
            if filter_criteria.capabilities:
                params["capabilities"] = ",".join(filter_criteria.capabilities)
            if filter_criteria.tags:
                params["tags"] = ",".join(filter_criteria.tags)
            if filter_criteria.keywords:
                params["q"] = " ".join(filter_criteria.keywords)
            if filter_criteria.online_only:
                params["online"] = "true"
            params["limit"] = str(filter_criteria.limit)

            headers = {}
            if self.config.security.api_key:
                headers["Authorization"] = f"Bearer {self.config.security.api_key}"

            async with self._http_session.get(
                f"{platform_url}/api/v1/agents/discover",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    agents = [AgentInfo.from_dict(a) for a in data.get("agents", [])]

                    # Update cache
                    await self._update_cache(agents)

                    return agents
                else:
                    self.logger.warning(f"Platform discovery failed: {response.status}")
                    return []
        except Exception as e:
            self.logger.error(f"Platform discovery error: {e}")
            return []

    async def _discover_network(self, filter_criteria: DiscoveryFilter) -> List[AgentInfo]:
        """Discover from P2P network"""
        agents = []

        # Query P2P connected agents
        p2p_connections = self.comm_manager.p2p_connections
        if not p2p_connections:
            return agents

        # Create discovery message
        discovery_msg = Message(
            type=MessageType.DISCOVERY,
            sender_id=self.agent_id,
            content={
                "action": "query",
                "filter": filter_criteria.to_dict(),
            },
        )

        # Broadcast to P2P connections
        tasks = []
        for target_id in p2p_connections.keys():
            try:
                task = asyncio.create_task(
                    self.comm_manager.send_p2p(discovery_msg, target_id)
                )
                tasks.append(task)
            except Exception:
                pass

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Message):
                    try:
                        response_agents = result.content.get("agents", [])
                        for agent_data in response_agents:
                            agents.append(AgentInfo.from_dict(agent_data))
                    except Exception as e:
                        self.logger.warning(f"Error parsing P2P discovery response: {e}")

        return agents

    def _merge_discoveries(self, agent_lists: List[List[AgentInfo]]) -> List[AgentInfo]:
        """Merge multiple discovery results, deduplicating by agent_id"""
        merged = {}

        for agents in agent_lists:
            for agent in agents:
                if agent.agent_id in merged:
                    # Merge, keeping more complete info
                    existing = merged[agent.agent_id]
                    if not existing.is_online and agent.is_online:
                        merged[agent.agent_id] = agent
                    elif len(agent.skills) > len(existing.skills):
                        merged[agent.agent_id] = agent
                else:
                    merged[agent.agent_id] = agent

        return list(merged.values())

    # ==================== Convenience Methods ====================

    async def discover_by_skill(self, skill_name: str, limit: int = 10) -> List[AgentInfo]:
        """Discover agents with a specific skill"""
        filter_criteria = DiscoveryFilter(
            skills=[skill_name],
            limit=limit,
        )
        return await self.discover(filter_criteria)

    async def discover_by_capability(
        self,
        capability_name: str,
        min_level: Optional[str] = None,
        limit: int = 10,
    ) -> List[AgentInfo]:
        """Discover agents with a specific capability"""
        capability_levels = {capability_name: min_level} if min_level else None

        filter_criteria = DiscoveryFilter(
            capabilities=[capability_name],
            capability_levels=capability_levels,
            limit=limit,
        )
        return await self.discover(filter_criteria)

    async def discover_by_keywords(
        self,
        keywords: List[str],
        limit: int = 10,
    ) -> List[AgentInfo]:
        """Discover agents by keywords"""
        filter_criteria = DiscoveryFilter(
            keywords=keywords,
            limit=limit,
        )
        return await self.discover(filter_criteria)

    async def discover_by_tags(
        self,
        tags: List[str],
        limit: int = 10,
    ) -> List[AgentInfo]:
        """Discover agents by tags"""
        filter_criteria = DiscoveryFilter(
            tags=tags,
            limit=limit,
        )
        return await self.discover(filter_criteria)

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent"""
        # Check cache first
        if agent_id in self._agent_cache:
            if agent_id in self._cache_expiry:
                if datetime.now() <= self._cache_expiry[agent_id]:
                    return self._agent_cache[agent_id]

        # Query platform
        if not self._http_session:
            return None

        platform_url = self.config.network.platform_endpoints[0] if self.config.network.platform_endpoints else "http://localhost:8000"

        try:
            headers = {}
            if self.config.security.api_key:
                headers["Authorization"] = f"Bearer {self.config.security.api_key}"

            async with self._http_session.get(
                f"{platform_url}/api/v1/agents/{agent_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    agent = AgentInfo.from_dict(data)

                    # Update cache
                    await self._update_cache([agent])

                    return agent
        except Exception as e:
            self.logger.error(f"Error getting agent {agent_id}: {e}")

        return None

    async def get_all_agent_ids(self) -> List[str]:
        """Get all known agent IDs"""
        # Combine cached and platform agents
        ids = set(self._agent_cache.keys())

        # Query platform for all agents
        filter_criteria = DiscoveryFilter(limit=1000, online_only=False)
        agents = await self._discover_platform(filter_criteria)
        ids.update(a.agent_id for a in agents)

        return list(ids)

    # ==================== Recommendation ====================

    async def get_recommendations(
        self,
        task_description: str,
        limit: int = 5,
    ) -> List[AgentInfo]:
        """
        Get recommended agents for a task.

        Uses a basic recommendation algorithm that:
        1. Extracts keywords from task description
        2. Matches against agent skills, capabilities, and descriptions
        3. Ranks by relevance score

        Args:
            task_description: Description of the task
            limit: Maximum number of recommendations

        Returns:
            List of recommended agents
        """
        if not self._initialized:
            raise RuntimeError("Discovery manager not initialized")

        # Extract keywords from task description
        keywords = self._extract_keywords(task_description)

        # Discover agents matching keywords
        filter_criteria = DiscoveryFilter(
            keywords=keywords,
            limit=100,  # Get more candidates for ranking
            sort_by=SortBy.RELEVANCE,
        )

        candidates = await self.discover(filter_criteria)

        if not candidates:
            # Try broader search
            filter_criteria.keywords = None
            filter_criteria.tags = keywords
            candidates = await self.discover(filter_criteria)

        # Score candidates
        scored_candidates = []
        for agent in candidates:
            score, explanation = self._calculate_recommendation_score(
                agent, task_description, keywords
            )
            agent.score = score
            scored_candidates.append((score, explanation, agent))

        # Sort by score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Build result
        recommended = [c[2] for c in scored_candidates[:limit]]
        explanations = {c[2].agent_id: c[1] for c in scored_candidates[:limit]}

        result = RecommendationResult(
            task_description=task_description,
            recommended_agents=recommended,
            total_candidates=len(candidates),
            algorithm="keyword_matching",
            confidence=min(1.0, len(recommended) / limit) if recommended else 0.0,
            explanations=explanations,
        )

        self.logger.info(f"Recommended {len(recommended)} agents for task")

        return recommended

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Basic keyword extraction
        # Remove common words
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "need", "dare",
            "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
            "and", "or", "but", "if", "then", "else", "when", "where", "why",
            "how", "all", "each", "every", "both", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "just", "also", "now", "here", "there",
            "i", "you", "he", "she", "it", "we", "they", "this", "that",
            "these", "those", "what", "which", "who", "whom", "whose",
        }

        # Tokenize and clean
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]

        # Return unique keywords
        return list(set(keywords))

    def _calculate_recommendation_score(
        self,
        agent: AgentInfo,
        task_description: str,
        keywords: List[str],
    ) -> Tuple[float, str]:
        """Calculate recommendation score for an agent"""
        score = 0.0
        explanations = []

        task_lower = task_description.lower()

        # Score based on skill matches
        for skill in agent.skills:
            skill_name = skill.get("name", "").lower()
            skill_desc = skill.get("description", "").lower()
            skill_tags = [t.lower() for t in skill.get("tags", [])]

            for keyword in keywords:
                if keyword in skill_name:
                    score += 10
                    explanations.append(f"Has skill '{skill_name}' matching '{keyword}'")
                elif keyword in skill_desc:
                    score += 5
                elif any(keyword in tag for tag in skill_tags):
                    score += 3

        # Score based on capability matches
        for cap in agent.capabilities:
            cap_name = cap.get("name", "").lower()
            cap_desc = cap.get("description", "").lower()
            cap_category = cap.get("category", "").lower()
            cap_level = cap.get("level", "basic")

            for keyword in keywords:
                if keyword in cap_name:
                    score += 8
                    level_bonus = self.CAPABILITY_LEVELS.get(cap_level, 1)
                    score += level_bonus
                    explanations.append(f"Has capability '{cap_name}' (level: {cap_level})")
                elif keyword in cap_category:
                    score += 4
                elif keyword in cap_desc:
                    score += 2

        # Score based on description match
        agent_desc = agent.description.lower()
        for keyword in keywords:
            if keyword in agent_desc:
                score += 2

        # Score based on tags
        for tag in agent.tags:
            tag_lower = tag.lower()
            for keyword in keywords:
                if keyword in tag_lower or tag_lower in keyword:
                    score += 3

        # Bonus for online agents
        if agent.is_online:
            score += 5

        # Bonus for high rating
        score += agent.rating * 2

        # Penalty for high latency
        if agent.latency > 0:
            score -= agent.latency / 100

        # Normalize score
        max_possible = len(keywords) * 25  # Rough estimate
        normalized_score = min(1.0, score / max_possible) if max_possible > 0 else 0.0

        explanation = "; ".join(explanations[:3]) if explanations else "General match"
        if not explanations:
            explanation = f"Matched {len(keywords)} keywords in agent info"

        return (normalized_score, explanation)

    # ==================== Filtering and Sorting ====================

    def _apply_filters(self, agents: List[AgentInfo], filter_criteria: DiscoveryFilter) -> List[AgentInfo]:
        """Apply filter criteria to agents"""
        filtered = []

        for agent in agents:
            # Exclude specific IDs
            if filter_criteria.exclude_ids and agent.agent_id in filter_criteria.exclude_ids:
                continue

            # Include only specific IDs
            if filter_criteria.include_only and agent.agent_id not in filter_criteria.include_only:
                continue

            # Online filter
            if filter_criteria.online_only and not agent.is_online:
                continue

            # Skills filter
            if filter_criteria.skills:
                if not all(agent.has_skill(s) for s in filter_criteria.skills):
                    continue

            # Capabilities filter
            if filter_criteria.capabilities:
                if not all(agent.has_capability(c) for c in filter_criteria.capabilities):
                    continue

            # Capability levels filter
            if filter_criteria.capability_levels:
                meets_levels = True
                for cap_name, min_level in filter_criteria.capability_levels.items():
                    cap = agent.get_capability(cap_name)
                    if not cap:
                        meets_levels = False
                        break
                    agent_level = self.CAPABILITY_LEVELS.get(cap.get("level", "basic"), 1)
                    required_level = self.CAPABILITY_LEVELS.get(min_level, 1)
                    if agent_level < required_level:
                        meets_levels = False
                        break
                if not meets_levels:
                    continue

            # Protocols filter
            if filter_criteria.protocols:
                agent_protocols = set(agent.protocols)
                required_protocols = {p.value for p in filter_criteria.protocols}
                if not required_protocols.intersection(agent_protocols):
                    continue

            # Tags filter
            if filter_criteria.tags:
                agent_tags = set(t.lower() for t in agent.tags)
                required_tags = set(t.lower() for t in filter_criteria.tags)
                if not required_tags.intersection(agent_tags):
                    continue

            # Keywords filter
            if filter_criteria.keywords:
                keyword_match = False
                search_text = f"{agent.name} {agent.description} {' '.join(agent.tags)}".lower()
                for keyword in filter_criteria.keywords:
                    if keyword.lower() in search_text:
                        keyword_match = True
                        break

                if not keyword_match:
                    # Also check skills and capabilities
                    for skill in agent.skills:
                        if any(kw.lower() in skill.get("name", "").lower() for kw in filter_criteria.keywords):
                            keyword_match = True
                            break

                    if not keyword_match:
                        for cap in agent.capabilities:
                            if any(kw.lower() in cap.get("name", "").lower() for kw in filter_criteria.keywords):
                                keyword_match = True
                                break

                    if not keyword_match:
                        continue

            # Min rating filter
            if filter_criteria.min_rating is not None:
                if agent.rating < filter_criteria.min_rating:
                    continue

            # Max latency filter
            if filter_criteria.max_latency is not None:
                if agent.latency > filter_criteria.max_latency:
                    continue

            # Categories filter
            if filter_criteria.categories:
                agent_categories = set(c.get("category", "").lower() for c in agent.capabilities)
                required_categories = set(c.lower() for c in filter_criteria.categories)
                if not required_categories.intersection(agent_categories):
                    continue

            filtered.append(agent)

        return filtered

    def _score_agents(self, agents: List[AgentInfo], filter_criteria: DiscoveryFilter) -> List[AgentInfo]:
        """Calculate relevance scores for agents"""
        keywords = filter_criteria.keywords or []

        for agent in agents:
            score = 0.0

            # Base score from rating
            score += agent.rating * 0.2

            # Keyword relevance
            for keyword in keywords:
                keyword_lower = keyword.lower()

                # Check name
                if keyword_lower in agent.name.lower():
                    score += 0.3

                # Check description
                if keyword_lower in agent.description.lower():
                    score += 0.2

                # Check skills
                for skill in agent.skills:
                    if keyword_lower in skill.get("name", "").lower():
                        score += 0.25

                # Check capabilities
                for cap in agent.capabilities:
                    if keyword_lower in cap.get("name", "").lower():
                        score += 0.25

            # Online bonus
            if agent.is_online:
                score += 0.1

            # Latency penalty
            if agent.latency > 100:
                score -= 0.05 * (agent.latency / 100)

            agent.score = max(0, min(1, score))

        return agents

    def _sort_agents(self, agents: List[AgentInfo], sort_by: SortBy) -> List[AgentInfo]:
        """Sort agents by specified criteria"""
        if sort_by == SortBy.RELEVANCE:
            return sorted(agents, key=lambda a: a.score, reverse=True)
        elif sort_by == SortBy.RATING:
            return sorted(agents, key=lambda a: a.rating, reverse=True)
        elif sort_by == SortBy.LATENCY:
            return sorted(agents, key=lambda a: a.latency)
        elif sort_by == SortBy.LAST_SEEN:
            return sorted(agents, key=lambda a: a.last_seen or datetime.min, reverse=True)
        elif sort_by == SortBy.NAME:
            return sorted(agents, key=lambda a: a.name.lower())
        else:
            return agents

    # ==================== Cache Management ====================

    async def _update_cache(self, agents: List[AgentInfo]) -> None:
        """Update local cache with discovered agents"""
        now = datetime.now()

        async with self._lock:
            for agent in agents:
                self._agent_cache[agent.agent_id] = agent
                self._cache_expiry[agent.agent_id] = now + self._cache_ttl

    async def refresh_discoveries(self) -> None:
        """Refresh all cached discoveries"""
        # Clear expired cache entries
        now = datetime.now()
        expired_ids = [
            agent_id for agent_id, expiry in self._cache_expiry.items()
            if now > expiry
        ]

        async with self._lock:
            for agent_id in expired_ids:
                self._agent_cache.pop(agent_id, None)
                self._cache_expiry.pop(agent_id, None)

        # Refresh with platform query
        filter_criteria = DiscoveryFilter(limit=100)
        await self._discover_platform(filter_criteria)

    def clear_cache(self) -> None:
        """Clear all cached data"""
        self._agent_cache.clear()
        self._cache_expiry.clear()


# ==================== Enhanced Discovery Classes ====================

class MatchDimension(Enum):
    """Dimensions for multi-dimensional matching"""
    CAPABILITY = "capability"
    PRICE = "price"
    REPUTATION = "reputation"
    AVAILABILITY = "availability"
    EXPERIENCE = "experience"
    SEMANTIC = "semantic"


@dataclass
class DimensionScore:
    """Score for a single dimension"""
    dimension: MatchDimension
    score: float  # 0.0 - 1.0
    weight: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultiDimensionalMatchResult:
    """Result of multi-dimensional matching"""
    agent: AgentInfo
    overall_score: float
    dimension_scores: List[DimensionScore]
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    gene_capsule_match: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent.agent_id,
            "agent_name": self.agent.name,
            "overall_score": self.overall_score,
            "dimension_scores": [
                {
                    "dimension": ds.dimension.value,
                    "score": ds.score,
                    "weight": ds.weight,
                    "details": ds.details,
                }
                for ds in self.dimension_scores
            ],
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendation": self.recommendation,
            "gene_capsule_match": self.gene_capsule_match,
        }


@dataclass
class SearchCriteria:
    """Multi-dimensional search criteria"""
    task_description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    required_capabilities: Optional[List[str]] = None

    # Price constraints
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    price_type: Optional[str] = None  # hourly, fixed, per_request

    # Reputation constraints
    min_rating: Optional[float] = None
    min_successful_tasks: Optional[int] = None
    require_verified: bool = False

    # Availability constraints
    availability_window: Optional[Tuple[datetime, datetime]] = None
    max_response_time: Optional[float] = None  # seconds
    require_online: bool = False

    # Experience requirements (Gene Capsule)
    require_experience_in: Optional[List[str]] = None  # Task types
    min_experience_count: Optional[int] = None
    require_verified_experience: bool = False

    # Weights for each dimension (should sum to 1.0)
    dimension_weights: Dict[MatchDimension, float] = field(default_factory=lambda: {
        MatchDimension.CAPABILITY: 0.30,
        MatchDimension.PRICE: 0.15,
        MatchDimension.REPUTATION: 0.20,
        MatchDimension.AVAILABILITY: 0.10,
        MatchDimension.EXPERIENCE: 0.25,
    })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_description": self.task_description,
            "required_skills": self.required_skills,
            "required_capabilities": self.required_capabilities,
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "price_type": self.price_type,
            "min_rating": self.min_rating,
            "min_successful_tasks": self.min_successful_tasks,
            "require_verified": self.require_verified,
            "availability_window": [
                self.availability_window[0].isoformat(),
                self.availability_window[1].isoformat()
            ] if self.availability_window else None,
            "max_response_time": self.max_response_time,
            "require_online": self.require_online,
            "require_experience_in": self.require_experience_in,
            "min_experience_count": self.min_experience_count,
            "require_verified_experience": self.require_verified_experience,
            "dimension_weights": {k.value: v for k, v in self.dimension_weights.items()},
        }


@dataclass
class WatchCondition:
    """Condition for watching agent changes"""
    condition_type: str  # "status_change", "new_capability", "price_change", "rating_change"
    agent_ids: Optional[Set[str]] = None
    filter_criteria: Optional[DiscoveryFilter] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class WatchEvent:
    """Event triggered by watch condition"""
    event_id: str
    watch_id: str
    agent_id: str
    event_type: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentComparison:
    """Comparison between multiple agents"""
    agents: List[AgentInfo]
    comparison_dimensions: List[MatchDimension]
    rankings: Dict[str, int]  # agent_id -> rank
    scores: Dict[str, Dict[MatchDimension, float]]  # agent_id -> dimension -> score
    summary: str
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": [a.to_dict() for a in self.agents],
            "comparison_dimensions": [d.value for d in self.comparison_dimensions],
            "rankings": self.rankings,
            "scores": {
                agent_id: {dim.value: score for dim, score in scores.items()}
                for agent_id, scores in self.scores.items()
            },
            "summary": self.summary,
            "recommendation": self.recommendation,
        }


class EnhancedDiscoveryManager(DiscoveryManager):
    """
    Enhanced Discovery Manager with multi-dimensional search,
    semantic matching, and gene capsule integration.
    """

    def __init__(
        self,
        agent_id: str,
        agent_config: AgentConfig,
        communication_manager: CommunicationManager,
        platform_client: Optional[Any] = None,  # PlatformClient
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__(agent_id, agent_config, communication_manager, logger)
        self.platform_client = platform_client

        # Enhanced features
        self._watchers: Dict[str, WatchCondition] = {}
        self._watch_callbacks: Dict[str, Callable] = {}
        self._watch_task: Optional[asyncio.Task] = None

        # Experience cache from gene capsule searches
        self._experience_cache: Dict[str, List[Dict]] = {}

        # Semantic matching LLM client (optional)
        self._llm_adapter = None

    async def initialize(self) -> None:
        """Initialize enhanced discovery manager"""
        await super().initialize()

        # Start watch task
        self._watch_task = asyncio.create_task(self._watch_loop())

        self.logger.info(f"Enhanced discovery manager initialized for agent {self.agent_id}")

    async def close(self) -> None:
        """Close enhanced discovery manager"""
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

        await super().close()

    # ==================== Multi-Dimensional Search ====================

    async def multi_dimensional_search(
        self,
        criteria: SearchCriteria,
        limit: int = 20,
    ) -> List[MultiDimensionalMatchResult]:
        """
        Perform multi-dimensional search with comprehensive scoring.

        Scoring dimensions:
        - Capability match (30%)
        - Experience match via Gene Capsule (25%)
        - Reputation (20%)
        - Price alignment (15%)
        - Availability (10%)
        """
        # Step 1: Get base candidates
        base_filter = DiscoveryFilter(
            skills=criteria.required_skills,
            capabilities=criteria.required_capabilities,
            min_rating=criteria.min_rating,
            online_only=criteria.require_online,
            limit=100,
        )
        candidates = await self.discover(base_filter)

        if not candidates:
            return []

        # Step 2: Score each candidate on all dimensions
        results = []
        for agent in candidates:
            match_result = await self._score_multi_dimensional(agent, criteria)
            results.append(match_result)

        # Step 3: Sort by overall score
        results.sort(key=lambda x: x.overall_score, reverse=True)

        return results[:limit]

    async def _score_multi_dimensional(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> MultiDimensionalMatchResult:
        """Score an agent across all dimensions"""
        dimension_scores = []
        strengths = []
        weaknesses = []

        weights = criteria.dimension_weights

        # 1. Capability Match
        cap_score, cap_details = self._score_capability_match(agent, criteria)
        dimension_scores.append(DimensionScore(
            dimension=MatchDimension.CAPABILITY,
            score=cap_score,
            weight=weights.get(MatchDimension.CAPABILITY, 0.30),
            details=cap_details,
        ))
        if cap_score > 0.8:
            strengths.append(f"Strong capability match ({cap_score:.0%})")
        elif cap_score < 0.5:
            weaknesses.append(f"Limited capability match ({cap_score:.0%})")

        # 2. Experience Match (via Gene Capsule)
        exp_score, exp_details = await self._score_experience_match(agent, criteria)
        dimension_scores.append(DimensionScore(
            dimension=MatchDimension.EXPERIENCE,
            score=exp_score,
            weight=weights.get(MatchDimension.EXPERIENCE, 0.25),
            details=exp_details,
        ))
        if exp_score > 0.7:
            strengths.append(f"Proven experience in relevant tasks")
        elif exp_score < 0.3 and criteria.require_experience_in:
            weaknesses.append(f"Limited relevant experience")

        # 3. Reputation Score
        rep_score, rep_details = self._score_reputation(agent, criteria)
        dimension_scores.append(DimensionScore(
            dimension=MatchDimension.REPUTATION,
            score=rep_score,
            weight=weights.get(MatchDimension.REPUTATION, 0.20),
            details=rep_details,
        ))
        if rep_score > 0.8:
            strengths.append(f"High reputation ({agent.rating:.1f} rating)")
        elif rep_score < 0.5:
            weaknesses.append(f"Lower reputation score")

        # 4. Price Match
        price_score, price_details = self._score_price_match(agent, criteria)
        dimension_scores.append(DimensionScore(
            dimension=MatchDimension.PRICE,
            score=price_score,
            weight=weights.get(MatchDimension.PRICE, 0.15),
            details=price_details,
        ))
        if price_score > 0.8:
            strengths.append(f"Price within budget")
        elif price_score < 0.5:
            weaknesses.append(f"Price may exceed budget")

        # 5. Availability Score
        avail_score, avail_details = self._score_availability(agent, criteria)
        dimension_scores.append(DimensionScore(
            dimension=MatchDimension.AVAILABILITY,
            score=avail_score,
            weight=weights.get(MatchDimension.AVAILABILITY, 0.10),
            details=avail_details,
        ))
        if avail_score > 0.8:
            strengths.append(f"Currently available")
        elif avail_score < 0.5:
            weaknesses.append(f"Limited availability")

        # Calculate overall score
        overall_score = sum(ds.score * ds.weight for ds in dimension_scores)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            overall_score, strengths, weaknesses
        )

        return MultiDimensionalMatchResult(
            agent=agent,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
            gene_capsule_match=exp_details.get("gene_capsule_data"),
        )

    def _score_capability_match(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> Tuple[float, Dict[str, Any]]:
        """Score capability match"""
        if not criteria.required_capabilities and not criteria.required_skills:
            return (0.7, {"reason": "No specific capabilities required"})

        matched_caps = []
        matched_skills = []
        total_required = len(criteria.required_capabilities or []) + len(criteria.required_skills or [])

        # Check capabilities
        if criteria.required_capabilities:
            for req_cap in criteria.required_capabilities:
                if agent.has_capability(req_cap):
                    matched_caps.append(req_cap)

        # Check skills
        if criteria.required_skills:
            for req_skill in criteria.required_skills:
                if agent.has_skill(req_skill):
                    matched_skills.append(req_skill)

        matched_count = len(matched_caps) + len(matched_skills)
        score = matched_count / total_required if total_required > 0 else 0.7

        return (score, {
            "matched_capabilities": matched_caps,
            "matched_skills": matched_skills,
            "total_required": total_required,
            "match_count": matched_count,
        })

    async def _score_experience_match(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> Tuple[float, Dict[str, Any]]:
        """Score experience match using Gene Capsule"""
        if not criteria.require_experience_in:
            return (0.5, {"reason": "No experience requirements specified"})

        # Try to get gene capsule data
        gene_capsule_data = None
        if self.platform_client:
            try:
                response = await self.platform_client.find_matching_experiences(
                    task_description=criteria.task_description or "",
                    required_skills=criteria.required_skills,
                    min_relevance=0.3,
                    limit=5,
                )
                if response.success:
                    gene_capsule_data = response.data
            except Exception as e:
                self.logger.warning(f"Failed to get gene capsule data: {e}")

        if not gene_capsule_data:
            # Fallback to simple heuristic
            return (0.5, {
                "reason": "Gene capsule data not available",
                "heuristic": True,
            })

        # Calculate experience score based on matched experiences
        matched_experiences = gene_capsule_data.get("matches", [])
        if not matched_experiences:
            return (0.3, {
                "reason": "No matching experiences found",
                "gene_capsule_data": gene_capsule_data,
            })

        # Score based on relevance and count
        total_relevance = sum(m.get("relevance_score", 0) for m in matched_experiences)
        avg_relevance = total_relevance / len(matched_experiences) if matched_experiences else 0

        # Bonus for verified experiences
        verified_count = sum(
            1 for m in matched_experiences
            if m.get("experience", {}).get("verified", False)
        )
        verification_bonus = min(0.2, verified_count * 0.05)

        # Count bonus
        count_bonus = min(0.2, len(matched_experiences) * 0.04)

        score = min(1.0, avg_relevance + verification_bonus + count_bonus)

        return (score, {
            "matched_count": len(matched_experiences),
            "avg_relevance": avg_relevance,
            "verified_count": verified_count,
            "gene_capsule_data": gene_capsule_data,
        })

    def _score_reputation(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> Tuple[float, Dict[str, Any]]:
        """Score reputation"""
        # Base score from rating
        rating_score = agent.rating / 5.0 if agent.rating else 0.5

        # Adjust based on requirements
        if criteria.min_rating and agent.rating < criteria.min_rating:
            rating_score *= 0.5

        # Verified bonus
        is_verified = agent.metadata.get("verified", False)
        verification_bonus = 0.2 if is_verified else 0

        score = min(1.0, rating_score + verification_bonus)

        return (score, {
            "rating": agent.rating,
            "verified": is_verified,
            "rating_score": rating_score,
            "verification_bonus": verification_bonus,
        })

    def _score_price_match(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> Tuple[float, Dict[str, Any]]:
        """Score price alignment"""
        if not criteria.budget_min and not criteria.budget_max:
            return (0.7, {"reason": "No budget specified"})

        agent_price = agent.metadata.get("hourly_rate") or agent.metadata.get("price")

        if not agent_price:
            return (0.5, {"reason": "Agent price not available"})

        budget_min = criteria.budget_min or 0
        budget_max = criteria.budget_max or float("inf")

        if budget_min <= agent_price <= budget_max:
            # Perfect match
            budget_mid = (budget_min + budget_max) / 2 if budget_max != float("inf") else budget_min * 1.5
            # Higher score if price is closer to budget mid
            score = 0.7 + 0.3 * (1 - abs(agent_price - budget_mid) / max(budget_mid, 1))
            return (min(1.0, score), {
                "agent_price": agent_price,
                "within_budget": True,
            })
        elif agent_price < budget_min:
            # Below budget - still acceptable
            score = 0.6
            return (score, {
                "agent_price": agent_price,
                "within_budget": False,
                "below_budget": True,
            })
        else:
            # Above budget
            overage_ratio = (agent_price - budget_max) / budget_max
            score = max(0.1, 0.5 - overage_ratio)
            return (score, {
                "agent_price": agent_price,
                "within_budget": False,
                "overage_percent": overage_ratio * 100,
            })

    def _score_availability(
        self,
        agent: AgentInfo,
        criteria: SearchCriteria,
    ) -> Tuple[float, Dict[str, Any]]:
        """Score availability"""
        details = {}

        # Online status
        if criteria.require_online and not agent.is_online:
            return (0.0, {"reason": "Agent not online but required"})

        online_score = 0.3 if agent.is_online else 0.1

        # Response time
        response_score = 0.3
        if criteria.max_response_time and agent.latency > criteria.max_response_time:
            response_score = 0.1
            details["latency_issue"] = True
        elif agent.latency > 0:
            response_score = max(0.1, 0.3 - (agent.latency / 1000))

        # Availability window
        window_score = 0.4
        if criteria.availability_window:
            # Check if agent has availability info
            agent_availability = agent.metadata.get("availability")
            if agent_availability:
                # Simplified check - real implementation would parse schedule
                window_score = 0.4
            else:
                window_score = 0.3
                details["availability_unknown"] = True

        score = online_score + response_score + window_score

        return (score, details)

    def _generate_recommendation(
        self,
        overall_score: float,
        strengths: List[str],
        weaknesses: List[str],
    ) -> str:
        """Generate a recommendation message"""
        if overall_score >= 0.8:
            return "Highly recommended - strong match across all dimensions"
        elif overall_score >= 0.6:
            return "Recommended - good overall match with some considerations"
        elif overall_score >= 0.4:
            return "Conditional - may be suitable depending on priorities"
        else:
            return "Not recommended - significant gaps in requirements"

    # ==================== Semantic Search ====================

    async def semantic_search(
        self,
        task_description: str,
        limit: int = 10,
    ) -> List[MultiDimensionalMatchResult]:
        """
        Perform semantic search using task description.

        Uses LLM to understand task intent and find matching agents.
        Falls back to keyword search if LLM is not available.
        """
        # Extract intent and requirements from task description
        intent = await self._extract_task_intent(task_description)

        # Build search criteria from extracted intent
        criteria = SearchCriteria(
            task_description=task_description,
            required_skills=intent.get("skills", []),
            required_capabilities=intent.get("capabilities", []),
            budget_min=intent.get("budget_min"),
            budget_max=intent.get("budget_max"),
            require_experience_in=intent.get("experience_types", []),
            dimension_weights={
                MatchDimension.CAPABILITY: 0.25,
                MatchDimension.EXPERIENCE: 0.35,
                MatchDimension.REPUTATION: 0.20,
                MatchDimension.PRICE: 0.10,
                MatchDimension.AVAILABILITY: 0.10,
            },
        )

        return await self.multi_dimensional_search(criteria, limit)

    async def _extract_task_intent(self, task_description: str) -> Dict[str, Any]:
        """Extract task intent using LLM or heuristics"""
        # If LLM adapter is available, use it
        if self._llm_adapter:
            try:
                prompt = f"""
Analyze this task description and extract the following:
1. Required skills (technical abilities)
2. Required capabilities (functional abilities)
3. Budget range (if mentioned)
4. Task types that would be relevant experience

Task: {task_description}

Return as JSON with keys: skills, capabilities, budget_min, budget_max, experience_types
"""
                response = await self._llm_adapter.generate(prompt)
                return json.loads(response)
            except Exception as e:
                self.logger.warning(f"LLM intent extraction failed: {e}")

        # Fallback to keyword extraction
        keywords = self._extract_keywords(task_description)

        # Map keywords to potential skills/capabilities
        skill_keywords = {
            "python", "javascript", "typescript", "java", "rust", "go",
            "machine learning", "ml", "ai", "nlp", "data analysis",
            "web development", "api", "database", "sql", "nosql",
            "cloud", "aws", "azure", "docker", "kubernetes",
        }

        capability_keywords = {
            "analysis", "development", "design", "testing", "deployment",
            "optimization", "integration", "migration", "automation",
            "monitoring", "security", "documentation", "training",
        }

        skills = [kw for kw in keywords if kw in skill_keywords]
        capabilities = [kw for kw in keywords if kw in capability_keywords]

        # Extract budget if mentioned
        budget_min, budget_max = None, None
        budget_pattern = r'\$?(\d+(?:,\d+)*(?:\.\d+)?)\s*[-–to]\s*\$?(\d+(?:,\d+)*(?:\.\d+)?)'
        match = re.search(budget_pattern, task_description, re.IGNORECASE)
        if match:
            budget_min = float(match.group(1).replace(',', ''))
            budget_max = float(match.group(2).replace(',', ''))

        return {
            "skills": skills,
            "capabilities": capabilities,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "experience_types": keywords[:5],  # Top 5 keywords as experience types
        }

    # ==================== Real-time Monitoring ====================

    async def watch_agents(
        self,
        watch_id: str,
        condition: WatchCondition,
        callback: Callable[[WatchEvent], None],
    ) -> str:
        """
        Watch agents for changes and trigger callbacks.

        Watch types:
        - status_change: Agent goes online/offline
        - new_capability: Agent adds new capability
        - price_change: Agent price changes
        - rating_change: Agent rating changes
        """
        self._watchers[watch_id] = condition
        self._watch_callbacks[watch_id] = callback

        self.logger.info(f"Started watching agents with condition: {condition.condition_type}")
        return watch_id

    async def stop_watch(self, watch_id: str) -> bool:
        """Stop watching for changes"""
        if watch_id in self._watchers:
            del self._watchers[watch_id]
            del self._watch_callbacks[watch_id]
            return True
        return False

    async def _watch_loop(self):
        """Background loop for checking watch conditions"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                for watch_id, condition in list(self._watchers.items()):
                    try:
                        events = await self._check_watch_condition(condition)
                        for event in events:
                            callback = self._watch_callbacks.get(watch_id)
                            if callback:
                                try:
                                    if asyncio.iscoroutinefunction(callback):
                                        await callback(event)
                                    else:
                                        callback(event)
                                except Exception as e:
                                    self.logger.error(f"Watch callback error: {e}")
                    except Exception as e:
                        self.logger.error(f"Watch check error for {watch_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Watch loop error: {e}")
                await asyncio.sleep(5)

    async def _check_watch_condition(self, condition: WatchCondition) -> List[WatchEvent]:
        """Check if watch condition is triggered"""
        events = []

        # Get current state of watched agents
        if condition.agent_ids:
            agents = []
            for agent_id in condition.agent_ids:
                agent = await self.get_agent(agent_id)
                if agent:
                    agents.append(agent)
        elif condition.filter_criteria:
            agents = await self.discover(condition.filter_criteria)
        else:
            return events

        for agent in agents:
            cached_agent = self._agent_cache.get(agent.agent_id)

            if not cached_agent:
                continue

            if condition.condition_type == "status_change":
                if agent.is_online != cached_agent.is_online:
                    events.append(WatchEvent(
                        event_id=f"evt-{uuid4().hex[:8]}",
                        watch_id=str(condition.created_at.timestamp()),
                        agent_id=agent.agent_id,
                        event_type="status_change",
                        old_value=cached_agent.is_online,
                        new_value=agent.is_online,
                    ))

            elif condition.condition_type == "rating_change":
                if abs(agent.rating - cached_agent.rating) >= (condition.threshold or 0.5):
                    events.append(WatchEvent(
                        event_id=f"evt-{uuid4().hex[:8]}",
                        watch_id=str(condition.created_at.timestamp()),
                        agent_id=agent.agent_id,
                        event_type="rating_change",
                        old_value=cached_agent.rating,
                        new_value=agent.rating,
                    ))

        return events

    # ==================== Batch Comparison ====================

    async def compare_agents(
        self,
        agent_ids: List[str],
        criteria: Optional[SearchCriteria] = None,
    ) -> AgentComparison:
        """
        Compare multiple agents across dimensions.

        Returns ranking, scores, and recommendation.
        """
        # Get all agents
        agents = []
        for agent_id in agent_ids:
            agent = await self.get_agent(agent_id)
            if agent:
                agents.append(agent)

        if len(agents) < 2:
            raise ValueError("Need at least 2 agents to compare")

        # Default criteria if not provided
        if not criteria:
            criteria = SearchCriteria()

        # Score each agent
        comparison_dimensions = [
            MatchDimension.CAPABILITY,
            MatchDimension.EXPERIENCE,
            MatchDimension.REPUTATION,
            MatchDimension.PRICE,
            MatchDimension.AVAILABILITY,
        ]

        scores: Dict[str, Dict[MatchDimension, float]] = {}

        for agent in agents:
            result = await self._score_multi_dimensional(agent, criteria)
            scores[agent.agent_id] = {
                ds.dimension: ds.score
                for ds in result.dimension_scores
            }

        # Calculate rankings
        overall_scores = {
            agent_id: sum(
                score * criteria.dimension_weights.get(dim, 0.2)
                for dim, score in dim_scores.items()
            )
            for agent_id, dim_scores in scores.items()
        }

        sorted_agents = sorted(overall_scores.items(), key=lambda x: x[1], reverse=True)
        rankings = {agent_id: rank + 1 for rank, (agent_id, _) in enumerate(sorted_agents)}

        # Generate summary
        top_agent_id = sorted_agents[0][0]
        top_agent = next(a for a in agents if a.agent_id == top_agent_id)

        summary = f"Compared {len(agents)} agents. "
        summary += f"Top ranked: {top_agent.name} (score: {sorted_agents[0][1]:.2f})"

        # Generate recommendation
        score_diff = sorted_agents[0][1] - sorted_agents[1][1] if len(sorted_agents) > 1 else 1.0

        if score_diff > 0.3:
            recommendation = f"Clear winner: {top_agent.name} is significantly better matched"
        elif score_diff > 0.1:
            recommendation = f"Recommended: {top_agent.name} has a moderate advantage"
        else:
            recommendation = "Close match - consider specific priorities"

        return AgentComparison(
            agents=agents,
            comparison_dimensions=comparison_dimensions,
            rankings=rankings,
            scores=scores,
            summary=summary,
            recommendation=recommendation,
        )

    # ==================== Experience-based Discovery ====================

    async def discover_by_experience(
        self,
        task_description: str,
        min_relevance: float = 0.6,
        limit: int = 10,
    ) -> List[MultiDimensionalMatchResult]:
        """
        Discover agents based on their proven experience (Gene Capsule).

        This prioritizes agents with demonstrated experience over
        just claimed capabilities.
        """
        if not self.platform_client:
            self.logger.warning("Platform client not available for experience discovery")
            return []

        # Search agents by experience via platform
        response = await self.platform_client.search_agents_by_experience(
            task_description=task_description,
            min_experience_relevance=min_relevance,
            limit=limit * 2,  # Get more candidates for filtering
        )

        if not response.success:
            self.logger.error(f"Experience search failed: {response.error}")
            return []

        results = []
        for agent_match in response.data:
            agent_id = agent_match.get("agent_id")

            # Get full agent info
            agent_info = await self.get_agent(agent_id)
            if not agent_info:
                continue

            # Build match result from experience data
            overall_relevance = agent_match.get("overall_relevance", 0)

            dimension_scores = [
                DimensionScore(
                    dimension=MatchDimension.EXPERIENCE,
                    score=overall_relevance,
                    weight=0.40,
                    details={
                        "matched_experiences": len(agent_match.get("matched_experiences", [])),
                        "verified_count": agent_match.get("verified_experiences_count", 0),
                    },
                ),
            ]

            # Add other dimension scores
            rep_score = agent_info.rating / 5.0 if agent_info.rating else 0.5
            dimension_scores.append(DimensionScore(
                dimension=MatchDimension.REPUTATION,
                score=rep_score,
                weight=0.30,
                details={"rating": agent_info.rating},
            ))

            avail_score = 0.7 if agent_info.is_online else 0.3
            dimension_scores.append(DimensionScore(
                dimension=MatchDimension.AVAILABILITY,
                score=avail_score,
                weight=0.30,
                details={"online": agent_info.is_online},
            ))

            # Calculate overall
            overall = sum(ds.score * ds.weight for ds in dimension_scores)

            results.append(MultiDimensionalMatchResult(
                agent=agent_info,
                overall_score=overall,
                dimension_scores=dimension_scores,
                strengths=[f"Proven experience (relevance: {overall_relevance:.0%})"],
                weaknesses=[],
                recommendation="Based on demonstrated experience",
                gene_capsule_match=agent_match,
            ))

        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:limit]

    # ==================== Historical Success Recommendations ====================

    async def get_recommendations_from_history(
        self,
        task_type: str,
        limit: int = 5,
    ) -> List[MultiDimensionalMatchResult]:
        """
        Get recommendations based on historical success patterns.

        Looks at agents who have successfully completed similar tasks.
        """
        if not self.platform_client:
            return []

        # Get agents with successful experiences in this task type
        response = await self.platform_client.search_agents_by_experience(
            task_description=task_type,
            min_experience_relevance=0.5,
            limit=limit * 3,
        )

        if not response.success:
            return []

        results = []
        for match in response.data:
            agent_id = match.get("agent_id")

            # Filter for successful outcomes
            matched_exp = match.get("matched_experiences", [])
            successful = [
                e for e in matched_exp
                if e.get("experience", {}).get("outcome") == "success"
            ]

            if not successful:
                continue

            agent_info = await self.get_agent(agent_id)
            if not agent_info:
                continue

            # Calculate success-based score
            success_rate = len(successful) / len(matched_exp) if matched_exp else 0
            avg_rating = sum(
                e.get("experience", {}).get("client_rating", 0)
                for e in successful
            ) / len(successful) if successful else 0

            score = (success_rate * 0.6) + (avg_rating / 5.0 * 0.4)

            results.append(MultiDimensionalMatchResult(
                agent=agent_info,
                overall_score=score,
                dimension_scores=[
                    DimensionScore(
                        dimension=MatchDimension.EXPERIENCE,
                        score=success_rate,
                        weight=0.6,
                        details={
                            "successful_count": len(successful),
                            "total_matched": len(matched_exp),
                        },
                    ),
                    DimensionScore(
                        dimension=MatchDimension.REPUTATION,
                        score=avg_rating / 5.0,
                        weight=0.4,
                        details={"avg_rating": avg_rating},
                    ),
                ],
                strengths=[f"{len(successful)} successful similar tasks"],
                weaknesses=[],
                recommendation="Based on historical success",
            ))

        results.sort(key=lambda x: x.overall_score, reverse=True)
        return results[:limit]
