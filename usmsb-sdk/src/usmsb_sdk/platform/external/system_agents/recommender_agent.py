"""
Recommender Agent Module

Provides agent recommendation capabilities including:
    - Agent discovery and matching based on user requirements
    - Skill and capability-based recommendations
    - Performance and rating-based ranking
    - Personalized recommendation history

Skills:
    - recommend: Get agent recommendations for a task
    - search: Search for agents by criteria
    - rate: Rate an agent performance
    - get_history: Get recommendation history
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import logging
import math

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
)
from usmsb_sdk.agent_sdk.communication import Message, MessageType, Session
from usmsb_sdk.agent_sdk.discovery import AgentInfo
from usmsb_sdk.platform.external.system_agents.base_system_agent import (
    BaseSystemAgent,
    SystemAgentConfig,
    SystemAgentPermission,
)


class AgentRating:
    """Represents a rating for an agent"""

    def __init__(
        self,
        agent_id: str,
        rating: float,
        reviewer_id: str,
        task_type: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        self.agent_id = agent_id
        self.rating = min(5.0, max(0.0, rating))  # Clamp to 0-5 range
        self.reviewer_id = reviewer_id
        self.task_type = task_type
        self.comment = comment
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert rating to dictionary"""
        return {
            "agent_id": self.agent_id,
            "rating": self.rating,
            "reviewer_id": self.reviewer_id,
            "task_type": self.task_type,
            "comment": self.comment,
            "created_at": self.created_at.isoformat(),
        }


class AgentProfile:
    """Extended profile for an agent with recommendation metadata"""

    def __init__(self, agent_info: AgentInfo):
        self.agent_info = agent_info
        self.ratings: List[AgentRating] = []
        self.success_count = 0
        self.failure_count = 0
        self.recommendation_count = 0
        self.last_recommended: Optional[datetime] = None
        self.tags: List[str] = []
        self.performance_metrics: Dict[str, float] = {}

    @property
    def average_rating(self) -> float:
        """Calculate average rating"""
        if not self.ratings:
            return 0.0
        return sum(r.rating for r in self.ratings) / len(self.ratings)

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total

    @property
    def reliability_score(self) -> float:
        """Calculate overall reliability score (0-100)"""
        # Weight factors
        rating_weight = 0.4
        success_weight = 0.3
        experience_weight = 0.3

        # Rating score (0-100)
        rating_score = (self.average_rating / 5.0) * 100

        # Success rate score (0-100)
        success_score = self.success_rate * 100

        # Experience score based on total interactions
        total_interactions = self.success_count + self.failure_count
        if total_interactions >= 100:
            experience_score = 100
        elif total_interactions >= 50:
            experience_score = 80
        elif total_interactions >= 10:
            experience_score = 60
        elif total_interactions >= 5:
            experience_score = 40
        else:
            experience_score = 20

        return (
            rating_score * rating_weight +
            success_score * success_weight +
            experience_score * experience_weight
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            "agent_id": self.agent_info.agent_id,
            "name": self.agent_info.name,
            "description": self.agent_info.description,
            "skills": [s.to_dict() for s in self.agent_info.skills],
            "capabilities": [c.to_dict() for c in self.agent_info.capabilities],
            "average_rating": self.average_rating,
            "reliability_score": self.reliability_score,
            "success_rate": self.success_rate,
            "total_ratings": len(self.ratings),
            "tags": self.tags,
            "performance_metrics": self.performance_metrics,
        }


class RecommendationResult:
    """Result of a recommendation request"""

    def __init__(
        self,
        request_id: str,
        query: str,
        results: List[Tuple[AgentProfile, float]],  # (profile, score)
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.request_id = request_id
        self.query = query
        self.results = results
        self.metadata = metadata or {}
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "request_id": self.request_id,
            "query": self.query,
            "results": [
                {
                    "agent": profile.to_dict(),
                    "score": score,
                    "rank": idx + 1,
                }
                for idx, (profile, score) in enumerate(self.results)
            ],
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class RecommenderAgent(BaseSystemAgent):
    """
    Agent recommendation service for matching user needs with suitable agents.

    This agent provides intelligent agent recommendations based on:
    - Skill and capability matching
    - Performance history and ratings
    - Task type preferences
    - User personalization

    Skills:
        - recommend: Get agent recommendations for a task
        - search: Search for agents by various criteria
        - rate: Submit a rating for an agent
        - get_history: Get recommendation history

    Example:
        config = AgentConfig(
            agent_id="recommender-001",
            name="AgentRecommender",
            # ... other config
        )
        recommender = RecommenderAgent(config)
        await recommender.start()

        # Get recommendations
        results = await recommender.call_skill("recommend", {
            "task_description": "Process PDF documents",
            "limit": 5
        })
    """

    SYSTEM_AGENT_TYPE = "recommender"

    def __init__(
        self,
        config: AgentConfig,
        system_config: Optional[SystemAgentConfig] = None,
    ):
        """Initialize the recommender agent"""
        super().__init__(config, system_config)

        # Agent profiles database
        self._agent_profiles: Dict[str, AgentProfile] = {}

        # Recommendation history
        self._recommendation_history: List[RecommendationResult] = []

        # User preferences (user_id -> preferences)
        self._user_preferences: Dict[str, Dict[str, Any]] = {}

        # Request counter for unique IDs
        self._request_counter = 0

        # Skill keyword mappings for matching
        self._skill_keywords: Dict[str, List[str]] = {
            "pdf_processing": ["pdf", "document", "extract", "parse"],
            "image_analysis": ["image", "picture", "photo", "analyze", "vision"],
            "text_generation": ["text", "generate", "write", "content"],
            "data_analysis": ["data", "analyze", "statistics", "report"],
            "web_scraping": ["web", "scrape", "crawl", "fetch"],
            "code_generation": ["code", "generate", "programming", "develop"],
            "translation": ["translate", "language", "multilingual"],
            "summarization": ["summarize", "summary", "condense", "brief"],
        }

        # Register recommender skills
        self._register_recommender_skills()

    def _register_recommender_skills(self) -> None:
        """Register recommender skills"""
        skills = [
            SkillDefinition(
                name="recommend",
                description="Get agent recommendations based on task requirements",
                parameters=[
                    SkillParameter(
                        name="task_description",
                        type="string",
                        description="Description of the task to accomplish",
                        required=True,
                    ),
                    SkillParameter(
                        name="required_skills",
                        type="array",
                        description="List of required skill names",
                        required=False,
                    ),
                    SkillParameter(
                        name="required_capabilities",
                        type="array",
                        description="List of required capability names",
                        required=False,
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Maximum number of recommendations",
                        required=False,
                        default=5,
                        min_value=1,
                        max_value=20,
                    ),
                    SkillParameter(
                        name="min_rating",
                        type="float",
                        description="Minimum agent rating (0-5)",
                        required=False,
                        default=0.0,
                        min_value=0.0,
                        max_value=5.0,
                    ),
                    SkillParameter(
                        name="user_id",
                        type="string",
                        description="User ID for personalization",
                        required=False,
                    ),
                ],
                returns="dict",
                tags=["recommendation", "discovery"],
            ),
            SkillDefinition(
                name="search",
                description="Search for agents by various criteria",
                parameters=[
                    SkillParameter(
                        name="query",
                        type="string",
                        description="Search query string",
                        required=False,
                    ),
                    SkillParameter(
                        name="skill",
                        type="string",
                        description="Filter by skill name",
                        required=False,
                    ),
                    SkillParameter(
                        name="capability",
                        type="string",
                        description="Filter by capability name",
                        required=False,
                    ),
                    SkillParameter(
                        name="min_rating",
                        type="float",
                        description="Minimum rating filter",
                        required=False,
                    ),
                    SkillParameter(
                        name="tags",
                        type="array",
                        description="Filter by tags",
                        required=False,
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Maximum results",
                        required=False,
                        default=20,
                    ),
                ],
                returns="list",
                tags=["search", "discovery"],
            ),
            SkillDefinition(
                name="rate",
                description="Rate an agent's performance",
                parameters=[
                    SkillParameter(
                        name="agent_id",
                        type="string",
                        description="ID of the agent to rate",
                        required=True,
                    ),
                    SkillParameter(
                        name="rating",
                        type="float",
                        description="Rating value (0-5)",
                        required=True,
                        min_value=0.0,
                        max_value=5.0,
                    ),
                    SkillParameter(
                        name="reviewer_id",
                        type="string",
                        description="ID of the reviewer",
                        required=True,
                    ),
                    SkillParameter(
                        name="task_type",
                        type="string",
                        description="Type of task being rated",
                        required=False,
                    ),
                    SkillParameter(
                        name="comment",
                        type="string",
                        description="Optional comment",
                        required=False,
                    ),
                    SkillParameter(
                        name="success",
                        type="boolean",
                        description="Whether the task succeeded",
                        required=False,
                        default=True,
                    ),
                ],
                returns="dict",
                tags=["rating", "feedback"],
            ),
            SkillDefinition(
                name="get_history",
                description="Get recommendation history",
                parameters=[
                    SkillParameter(
                        name="user_id",
                        type="string",
                        description="Filter by user ID",
                        required=False,
                    ),
                    SkillParameter(
                        name="agent_id",
                        type="string",
                        description="Filter by agent ID",
                        required=False,
                    ),
                    SkillParameter(
                        name="time_range",
                        type="integer",
                        description="Time range in hours",
                        required=False,
                        default=24,
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Maximum results",
                        required=False,
                        default=50,
                    ),
                ],
                returns="list",
                tags=["history", "analytics"],
            ),
        ]

        for skill in skills:
            self.register_skill(skill)

    # ==================== Lifecycle Methods ====================

    async def initialize(self) -> None:
        """Initialize the recommender agent"""
        self.logger.info("Initializing Recommender Agent")

        # Register capabilities
        capabilities = [
            CapabilityDefinition(
                name="agent_recommendation",
                description="Provide intelligent agent recommendations",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="agent_search",
                description="Search and discover agents",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="rating_management",
                description="Manage agent ratings and reviews",
                version="1.0.0",
            ),
        ]

        for cap in capabilities:
            self.add_capability(cap)

        # Load existing agent profiles from discovery
        await self._refresh_agent_profiles()

    async def handle_message(
        self,
        message: Message,
        session: Optional[Session] = None
    ) -> Optional[Message]:
        """Handle incoming messages"""
        await self.audit_operation("message_received", {
            "message_type": message.type.value if hasattr(message.type, 'value') else str(message.type),
            "sender": message.sender_id,
        })

        content = message.content if isinstance(message.content, dict) else {"data": message.content}

        # Handle agent registration updates
        if content.get("type") == "agent_registered":
            await self._register_agent_profile(content.get("agent_info"))
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "acknowledged"},
            )

        # Handle agent unregistration
        if content.get("type") == "agent_unregistered":
            agent_id = content.get("agent_id")
            if agent_id and agent_id in self._agent_profiles:
                del self._agent_profiles[agent_id]
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "acknowledged"},
            )

        return None

    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
        """Execute recommender skills"""
        await self.audit_operation("skill_execution", {
            "skill": skill_name,
            "params": {k: v for k, v in params.items() if k not in ["comment"]},
        })

        if skill_name == "recommend":
            return await self._skill_recommend(params)
        elif skill_name == "search":
            return await self._skill_search(params)
        elif skill_name == "rate":
            return await self._skill_rate(params)
        elif skill_name == "get_history":
            return await self._skill_get_history(params)
        else:
            raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self) -> None:
        """Shutdown the recommender agent"""
        self.logger.info("Shutting down Recommender Agent")

    # ==================== Skill Implementations ====================

    async def _skill_recommend(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute recommend skill"""
        task_description = params.get("task_description", "")
        required_skills = params.get("required_skills", [])
        required_capabilities = params.get("required_capabilities", [])
        limit = params.get("limit", 5)
        min_rating = params.get("min_rating", 0.0)
        user_id = params.get("user_id")

        # Generate unique request ID
        self._request_counter += 1
        request_id = f"rec-{self._request_counter:06d}"

        # Score and rank agents
        scored_agents: List[Tuple[AgentProfile, float]] = []

        for agent_id, profile in self._agent_profiles.items():
            # Skip if rating is below minimum
            if profile.average_rating < min_rating:
                continue

            # Calculate match score
            score = await self._calculate_match_score(
                profile,
                task_description,
                required_skills,
                required_capabilities,
                user_id,
            )

            if score > 0:
                scored_agents.append((profile, score))

        # Sort by score (descending)
        scored_agents.sort(key=lambda x: x[1], reverse=True)

        # Limit results
        scored_agents = scored_agents[:limit]

        # Create result
        result = RecommendationResult(
            request_id=request_id,
            query=task_description,
            results=scored_agents,
            metadata={
                "required_skills": required_skills,
                "required_capabilities": required_capabilities,
                "min_rating": min_rating,
                "user_id": user_id,
            },
        )

        # Store in history
        self._recommendation_history.append(result)

        # Update recommendation counts
        for profile, _ in scored_agents:
            profile.recommendation_count += 1
            profile.last_recommended = datetime.now()

        return result.to_dict()

    async def _skill_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute search skill"""
        query = params.get("query", "").lower()
        skill_filter = params.get("skill")
        capability_filter = params.get("capability")
        min_rating = params.get("min_rating", 0.0)
        tags = params.get("tags", [])
        limit = params.get("limit", 20)

        results = []

        for profile in self._agent_profiles.values():
            # Apply filters
            if min_rating > 0 and profile.average_rating < min_rating:
                continue

            if skill_filter:
                skill_names = [s.name for s in profile.agent_info.skills]
                if skill_filter not in skill_names:
                    continue

            if capability_filter:
                cap_names = [c.name for c in profile.agent_info.capabilities]
                if capability_filter not in cap_names:
                    continue

            if tags:
                if not any(tag in profile.tags for tag in tags):
                    continue

            # Text search
            if query:
                searchable = " ".join([
                    profile.agent_info.name.lower(),
                    profile.agent_info.description.lower(),
                    " ".join(s.name.lower() for s in profile.agent_info.skills),
                    " ".join(c.name.lower() for c in profile.agent_info.capabilities),
                    " ".join(profile.tags),
                ])
                if query not in searchable:
                    continue

            results.append(profile.to_dict())

        # Sort by reliability score
        results.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)

        return results[:limit]

    async def _skill_rate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rate skill"""
        agent_id = params.get("agent_id")
        rating = params.get("rating")
        reviewer_id = params.get("reviewer_id")
        task_type = params.get("task_type")
        comment = params.get("comment")
        success = params.get("success", True)

        if not agent_id or rating is None or not reviewer_id:
            raise ValueError("agent_id, rating, and reviewer_id are required")

        if agent_id not in self._agent_profiles:
            raise ValueError(f"Unknown agent: {agent_id}")

        profile = self._agent_profiles[agent_id]

        # Create rating
        agent_rating = AgentRating(
            agent_id=agent_id,
            rating=rating,
            reviewer_id=reviewer_id,
            task_type=task_type,
            comment=comment,
        )

        profile.ratings.append(agent_rating)

        # Update success/failure counts
        if success:
            profile.success_count += 1
        else:
            profile.failure_count += 1

        await self.audit_operation("agent_rated", {
            "agent_id": agent_id,
            "rating": rating,
            "reviewer_id": reviewer_id,
            "success": success,
        })

        return {
            "status": "success",
            "agent_id": agent_id,
            "new_average_rating": profile.average_rating,
            "total_ratings": len(profile.ratings),
        }

    async def _skill_get_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute get_history skill"""
        user_id = params.get("user_id")
        agent_id = params.get("agent_id")
        time_range = params.get("time_range", 24)
        limit = params.get("limit", 50)

        cutoff_time = datetime.now() - timedelta(hours=time_range)

        results = []
        for result in self._recommendation_history:
            if result.created_at < cutoff_time:
                continue

            if user_id and result.metadata.get("user_id") != user_id:
                continue

            if agent_id:
                # Check if agent_id is in results
                agent_ids = [p.agent_info.agent_id for p, _ in result.results]
                if agent_id not in agent_ids:
                    continue

            results.append(result.to_dict())

        return results[:limit]

    # ==================== Internal Methods ====================

    async def _refresh_agent_profiles(self) -> None:
        """Refresh agent profiles from discovery manager"""
        if self._discovery_manager:
            agents = await self._discovery_manager.get_all_agents()
            for agent_info in agents:
                await self._register_agent_profile(agent_info)

    async def _register_agent_profile(self, agent_info: Optional[AgentInfo]) -> None:
        """Register or update an agent profile"""
        if not agent_info:
            return

        agent_id = agent_info.agent_id

        if agent_id in self._agent_profiles:
            # Update existing profile
            profile = self._agent_profiles[agent_id]
            profile.agent_info = agent_info
        else:
            # Create new profile
            profile = AgentProfile(agent_info)
            self._agent_profiles[agent_id] = profile

        # Extract tags from skills
        profile.tags = []
        for skill in agent_info.skills:
            skill_tags = self._skill_keywords.get(skill.name, [])
            profile.tags.extend(skill_tags)

        profile.tags = list(set(profile.tags))  # Remove duplicates

    async def _calculate_match_score(
        self,
        profile: AgentProfile,
        task_description: str,
        required_skills: List[str],
        required_capabilities: List[str],
        user_id: Optional[str],
    ) -> float:
        """
        Calculate match score between profile and requirements.

        Returns a score from 0 to 100.
        """
        score = 0.0

        # Text matching score (0-40)
        text_score = self._calculate_text_match(profile, task_description)
        score += text_score * 0.4

        # Skill matching score (0-30)
        if required_skills:
            skill_score = self._calculate_skill_match(profile, required_skills)
            score += skill_score * 0.3
        else:
            score += 15  # Neutral score if no skills required

        # Capability matching score (0-20)
        if required_capabilities:
            cap_score = self._calculate_capability_match(profile, required_capabilities)
            score += cap_score * 0.2
        else:
            score += 10  # Neutral score

        # Reliability bonus (0-10)
        reliability_bonus = profile.reliability_score * 0.1
        score += reliability_bonus

        # Personalization bonus
        if user_id:
            personalization_bonus = self._calculate_personalization_bonus(profile, user_id)
            score += personalization_bonus

        return min(100.0, score)

    def _calculate_text_match(self, profile: AgentProfile, task_description: str) -> float:
        """Calculate text matching score"""
        if not task_description:
            return 50.0

        task_words = set(task_description.lower().split())

        # Check agent name and description
        agent_words = set(
            (profile.agent_info.name + " " + profile.agent_info.description).lower().split()
        )

        # Check skill names and descriptions
        for skill in profile.agent_info.skills:
            agent_words.add(skill.name.lower())
            if skill.description:
                agent_words.update(skill.description.lower().split())

        # Calculate overlap
        overlap = len(task_words & agent_words)
        if not task_words:
            return 0.0

        return min(100.0, (overlap / len(task_words)) * 100)

    def _calculate_skill_match(
        self,
        profile: AgentProfile,
        required_skills: List[str]
    ) -> float:
        """Calculate skill matching score"""
        if not required_skills:
            return 100.0

        agent_skills = {s.name.lower() for s in profile.agent_info.skills}
        required = {s.lower() for s in required_skills}

        matched = len(agent_skills & required)
        return (matched / len(required)) * 100

    def _calculate_capability_match(
        self,
        profile: AgentProfile,
        required_capabilities: List[str]
    ) -> float:
        """Calculate capability matching score"""
        if not required_capabilities:
            return 100.0

        agent_caps = {c.name.lower() for c in profile.agent_info.capabilities}
        required = {c.lower() for c in required_capabilities}

        matched = len(agent_caps & required)
        return (matched / len(required)) * 100

    def _calculate_personalization_bonus(
        self,
        profile: AgentProfile,
        user_id: str
    ) -> float:
        """Calculate personalization bonus based on user history"""
        prefs = self._user_preferences.get(user_id, {})

        # Bonus for previously used agents
        used_agents = prefs.get("used_agents", {})
        if profile.agent_info.agent_id in used_agents:
            return 5.0

        # Bonus for preferred tags
        preferred_tags = prefs.get("preferred_tags", [])
        matching_tags = len(set(profile.tags) & set(preferred_tags))
        return min(5.0, matching_tags * 1.0)

    # ==================== Public Helper Methods ====================

    def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> None:
        """Update user preferences for personalization"""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {
                "used_agents": {},
                "preferred_tags": [],
                "preferred_skills": [],
            }

        self._user_preferences[user_id].update(preferences)

    def record_agent_usage(self, user_id: str, agent_id: str) -> None:
        """Record that a user used an agent"""
        if user_id not in self._user_preferences:
            self._user_preferences[user_id] = {}

        if "used_agents" not in self._user_preferences[user_id]:
            self._user_preferences[user_id]["used_agents"] = {}

        self._user_preferences[user_id]["used_agents"][agent_id] = datetime.now().isoformat()

    def get_agent_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get profile for a specific agent"""
        if agent_id in self._agent_profiles:
            return self._agent_profiles[agent_id].to_dict()
        return None

    def get_all_profiles(self) -> List[Dict[str, Any]]:
        """Get all agent profiles"""
        return [p.to_dict() for p in self._agent_profiles.values()]
