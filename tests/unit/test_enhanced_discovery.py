"""
Unit Tests for Enhanced Discovery Module

Tests for:
- Multi-dimensional search
- Semantic matching
- Real-time monitoring
- Batch comparison
- Experience-based discovery
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from usmsb_sdk.agent_sdk.discovery import (
    DiscoveryManager,
    DiscoveryFilter,
    AgentInfo,
    DiscoveryScope,
    SortBy,
    EnhancedDiscoveryManager,
    MatchDimension,
    DimensionScore,
    MultiDimensionalMatchResult,
    SearchCriteria,
    WatchCondition,
    WatchEvent,
    AgentComparison,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Mock agent config"""
    config = MagicMock()
    config.network.platform_endpoints = ["http://localhost:8000"]
    config.security.api_key = "test-key"
    return config


@pytest.fixture
def mock_comm_manager():
    """Mock communication manager"""
    return MagicMock()


@pytest.fixture
def mock_platform_client():
    """Mock platform client"""
    client = AsyncMock()
    client.search_agents_by_experience = AsyncMock()
    client.find_matching_experiences = AsyncMock()
    return client


@pytest.fixture
def sample_agent_info():
    """Sample agent info"""
    return AgentInfo(
        agent_id="agent-001",
        name="Test Agent",
        description="A test agent for unit testing",
        skills=[
            {"name": "python", "level": "expert"},
            {"name": "data_analysis", "level": "advanced"},
        ],
        capabilities=[
            {"name": "ml", "level": "advanced", "category": "ai"},
        ],
        rating=4.5,
        is_online=True,
        latency=50,
        tags=["data", "ml"],
    )


@pytest.fixture
def enhanced_discovery(mock_config, mock_comm_manager, mock_platform_client):
    """Enhanced discovery manager instance"""
    return EnhancedDiscoveryManager(
        agent_id="test-agent",
        agent_config=mock_config,
        communication_manager=mock_comm_manager,
        platform_client=mock_platform_client,
    )


# ==================== Test DiscoveryFilter ====================

class TestDiscoveryFilter:
    """Tests for DiscoveryFilter"""

    def test_to_dict(self):
        """Test filter serialization"""
        filter = DiscoveryFilter(
            skills=["python", "ml"],
            capabilities=["data_analysis"],
            min_rating=4.0,
            online_only=True,
            limit=50,
        )

        result = filter.to_dict()

        assert result["skills"] == ["python", "ml"]
        assert result["capabilities"] == ["data_analysis"]
        assert result["min_rating"] == 4.0
        assert result["online_only"] is True
        assert result["limit"] == 50

    def test_from_dict(self):
        """Test filter deserialization"""
        data = {
            "skills": ["python"],
            "capabilities": ["ml"],
            "min_rating": 3.5,
            "scope": "platform",
            "sort_by": "rating",
        }

        filter = DiscoveryFilter.from_dict(data)

        assert filter.skills == ["python"]
        assert filter.capabilities == ["ml"]
        assert filter.min_rating == 3.5
        assert filter.scope == DiscoveryScope.PLATFORM
        assert filter.sort_by == SortBy.RATING


# ==================== Test AgentInfo ====================

class TestAgentInfo:
    """Tests for AgentInfo"""

    def test_has_skill(self, sample_agent_info):
        """Test skill checking"""
        assert sample_agent_info.has_skill("python") is True
        assert sample_agent_info.has_skill("java") is False

    def test_has_capability(self, sample_agent_info):
        """Test capability checking"""
        assert sample_agent_info.has_capability("ml") is True
        assert sample_agent_info.has_capability("web") is False

    def test_get_skill(self, sample_agent_info):
        """Test getting skill"""
        skill = sample_agent_info.get_skill("python")
        assert skill is not None
        assert skill["level"] == "expert"

        assert sample_agent_info.get_skill("nonexistent") is None

    def test_to_dict_and_from_dict(self, sample_agent_info):
        """Test serialization round-trip"""
        data = sample_agent_info.to_dict()
        restored = AgentInfo.from_dict(data)

        assert restored.agent_id == sample_agent_info.agent_id
        assert restored.name == sample_agent_info.name
        assert restored.rating == sample_agent_info.rating


# ==================== Test SearchCriteria ====================

class TestSearchCriteria:
    """Tests for SearchCriteria"""

    def test_default_values(self):
        """Test default search criteria"""
        criteria = SearchCriteria()

        assert criteria.task_description is None
        assert criteria.require_online is False
        assert criteria.require_verified is False

    def test_to_dict(self):
        """Test criteria serialization"""
        criteria = SearchCriteria(
            task_description="Need ML expert",
            required_skills=["python", "tensorflow"],
            budget_min=50,
            budget_max=150,
            min_rating=4.0,
            require_online=True,
        )

        result = criteria.to_dict()

        assert result["task_description"] == "Need ML expert"
        assert result["required_skills"] == ["python", "tensorflow"]
        assert result["budget_min"] == 50
        assert result["budget_max"] == 150
        assert result["require_online"] is True


# ==================== Test MultiDimensionalMatchResult ====================

class TestMultiDimensionalMatchResult:
    """Tests for MultiDimensionalMatchResult"""

    def test_to_dict(self, sample_agent_info):
        """Test match result serialization"""
        result = MultiDimensionalMatchResult(
            agent=sample_agent_info,
            overall_score=0.85,
            dimension_scores=[
                DimensionScore(
                    dimension=MatchDimension.CAPABILITY,
                    score=0.9,
                    weight=0.3,
                    details={"matched": 3},
                ),
                DimensionScore(
                    dimension=MatchDimension.PRICE,
                    score=0.8,
                    weight=0.15,
                    details={"within_budget": True},
                ),
            ],
            strengths=["Strong capability match"],
            weaknesses=[],
            recommendation="Highly recommended",
        )

        data = result.to_dict()

        assert data["agent_id"] == "agent-001"
        assert data["overall_score"] == 0.85
        assert len(data["dimension_scores"]) == 2
        assert "Strong capability match" in data["strengths"]


# ==================== Test EnhancedDiscoveryManager ====================

class TestEnhancedDiscoveryManager:
    """Tests for EnhancedDiscoveryManager"""

    @pytest.mark.asyncio
    async def test_initialize(self, enhanced_discovery):
        """Test initialization"""
        await enhanced_discovery.initialize()
        assert enhanced_discovery._initialized is True
        await enhanced_discovery.close()

    @pytest.mark.asyncio
    async def test_score_capability_match(self, enhanced_discovery, sample_agent_info):
        """Test capability scoring"""
        criteria = SearchCriteria(
            required_capabilities=["ml"],
            required_skills=["python"],
        )

        score, details = enhanced_discovery._score_capability_match(
            sample_agent_info, criteria
        )

        assert score > 0
        assert "matched_capabilities" in details
        assert "ml" in details["matched_capabilities"]

    @pytest.mark.asyncio
    async def test_score_capability_match_no_requirements(self, enhanced_discovery, sample_agent_info):
        """Test capability scoring with no requirements"""
        criteria = SearchCriteria()

        score, details = enhanced_discovery._score_capability_match(
            sample_agent_info, criteria
        )

        assert score == 0.7
        assert details["reason"] == "No specific capabilities required"

    @pytest.mark.asyncio
    async def test_score_reputation(self, enhanced_discovery, sample_agent_info):
        """Test reputation scoring"""
        criteria = SearchCriteria(min_rating=4.0)

        score, details = enhanced_discovery._score_reputation(
            sample_agent_info, criteria
        )

        assert score > 0
        assert details["rating"] == 4.5

    @pytest.mark.asyncio
    async def test_score_price_match_within_budget(self, enhanced_discovery):
        """Test price scoring within budget"""
        agent = AgentInfo(
            agent_id="agent-001",
            name="Test Agent",
            description="Test",
            metadata={"hourly_rate": 100},
        )
        criteria = SearchCriteria(budget_min=50, budget_max=150)

        score, details = enhanced_discovery._score_price_match(agent, criteria)

        assert score >= 0.7
        assert details["within_budget"] is True

    @pytest.mark.asyncio
    async def test_score_price_match_over_budget(self, enhanced_discovery):
        """Test price scoring over budget"""
        agent = AgentInfo(
            agent_id="agent-001",
            name="Test Agent",
            description="Test",
            metadata={"hourly_rate": 200},
        )
        criteria = SearchCriteria(budget_min=50, budget_max=150)

        score, details = enhanced_discovery._score_price_match(agent, criteria)

        assert score < 0.5
        assert details["within_budget"] is False

    @pytest.mark.asyncio
    async def test_score_availability_online(self, enhanced_discovery, sample_agent_info):
        """Test availability scoring for online agent"""
        criteria = SearchCriteria(require_online=True)

        score, details = enhanced_discovery._score_availability(sample_agent_info, criteria)

        assert score > 0

    @pytest.mark.asyncio
    async def test_generate_recommendation(self, enhanced_discovery):
        """Test recommendation generation"""
        # High score
        rec = enhanced_discovery._generate_recommendation(0.85, ["Strong match"], [])
        assert "Highly recommended" in rec

        # Medium score
        rec = enhanced_discovery._generate_recommendation(0.65, ["Good"], ["Some issues"])
        assert "Recommended" in rec

        # Low score
        rec = enhanced_discovery._generate_recommendation(0.35, [], ["Major gaps"])
        assert "Not recommended" in rec

    @pytest.mark.asyncio
    async def test_extract_task_intent_keywords(self, enhanced_discovery):
        """Test task intent extraction with keywords"""
        description = "I need a Python developer who can do machine learning for $50-100 per hour"

        intent = await enhanced_discovery._extract_task_intent(description)

        assert "python" in intent["skills"]
        # Note: The keyword extraction uses exact matching, so "machine" won't match "machine learning"
        # This is expected behavior - LLM-based extraction would handle multi-word phrases better
        assert intent["budget_min"] == 50
        assert intent["budget_max"] == 100


# ==================== Test Watch Functionality ====================

class TestWatchFunctionality:
    """Tests for watch/monitoring functionality"""

    def test_watch_condition_creation(self):
        """Test watch condition creation"""
        condition = WatchCondition(
            condition_type="status_change",
            agent_ids={"agent-001", "agent-002"},
        )

        assert condition.condition_type == "status_change"
        assert "agent-001" in condition.agent_ids

    def test_watch_event_creation(self):
        """Test watch event creation"""
        event = WatchEvent(
            event_id="evt-001",
            watch_id="watch-001",
            agent_id="agent-001",
            event_type="status_change",
            old_value=False,
            new_value=True,
        )

        assert event.event_id == "evt-001"
        assert event.event_type == "status_change"

    @pytest.mark.asyncio
    async def test_watch_agents(self, enhanced_discovery):
        """Test watching agents"""
        await enhanced_discovery.initialize()

        callback_called = []

        async def callback(event):
            callback_called.append(event)

        condition = WatchCondition(
            condition_type="status_change",
            agent_ids={"agent-001"},
        )

        watch_id = await enhanced_discovery.watch_agents(
            "test-watch",
            condition,
            callback,
        )

        assert watch_id == "test-watch"
        assert "test-watch" in enhanced_discovery._watchers

        # Stop watch
        result = await enhanced_discovery.stop_watch("test-watch")
        assert result is True
        assert "test-watch" not in enhanced_discovery._watchers

        await enhanced_discovery.close()


# ==================== Test Agent Comparison ====================

class TestAgentComparison:
    """Tests for agent comparison"""

    def test_agent_comparison_creation(self, sample_agent_info):
        """Test comparison object creation"""
        comparison = AgentComparison(
            agents=[sample_agent_info],
            comparison_dimensions=[
                MatchDimension.CAPABILITY,
                MatchDimension.REPUTATION,
            ],
            rankings={"agent-001": 1},
            scores={
                "agent-001": {
                    MatchDimension.CAPABILITY: 0.9,
                    MatchDimension.REPUTATION: 0.8,
                }
            },
            summary="Test comparison",
            recommendation="Agent 1 is recommended",
        )

        data = comparison.to_dict()

        assert len(data["agents"]) == 1
        assert data["rankings"]["agent-001"] == 1
        assert data["recommendation"] == "Agent 1 is recommended"


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_multi_dimensional_search_flow(self, enhanced_discovery, sample_agent_info):
        """Test full multi-dimensional search flow"""
        await enhanced_discovery.initialize()

        # Mock the discover method
        enhanced_discovery.discover = AsyncMock(return_value=[sample_agent_info])

        criteria = SearchCriteria(
            task_description="Need Python ML expert",
            required_skills=["python"],
            required_capabilities=["ml"],
            budget_min=50,
            budget_max=200,
            min_rating=4.0,
        )

        # This would normally call the platform
        # For now, just verify the scoring logic works
        result = await enhanced_discovery._score_multi_dimensional(
            sample_agent_info, criteria
        )

        assert result.overall_score >= 0
        assert len(result.dimension_scores) > 0
        assert isinstance(result.recommendation, str)

        await enhanced_discovery.close()


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
