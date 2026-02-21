"""
Agent Discovery Module

Implements the discovery system for finding and recommending agents, including:
- Skill-based discovery
- Capability-based discovery
- Keyword and tag search
- Recommendation algorithm
- Agent ranking and scoring
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
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
