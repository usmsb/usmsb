"""
Unit tests for smart_recall.py - IntelligentRecall class

Tests the intelligent memory recall system that uses LLM for decision making.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.smart_recall import (
    IntelligentRecall,
    RetrievalDimension,
    MemoryItem,
    RetrievalResult,
    IntentUnderstanding,
)


class MockLLMManager:
    """Mock LLM manager for testing"""

    async def chat(self, prompt: str) -> str:
        """Return mock LLM response"""
        # Return JSON based on prompt content
        if "分析用户输入" in prompt or "分析用户" in prompt:
            return '''{
                "explicit_intent": "test intent",
                "implicit_intent": "test implicit",
                "potential_intent": "test potential",
                "entities": ["entity1", "entity2"],
                "task_type": "coding",
                "reasoning": "test reasoning"
            }'''
        elif "决定检索维度" in prompt or "检索维度" in prompt:
            return '''{
                "dimensions": ["semantic_vector", "keyword"],
                "weights": {"semantic_vector": 0.5, "keyword": 0.5},
                "reasoning": "test"
            }'''
        elif "排序" in prompt:
            return '''{"ranked_ids": [], "reasoning": "test"}'''
        elif "选择最重要" in prompt:
            return '''{"selected_ids": [], "reasoning": "test"}'''
        else:
            return '{"summary": "test summary"}'


class MockMemoryDB:
    """Mock memory database"""

    def __init__(self):
        self.memories = []

    async def search(self, query: str, limit: int = 20):
        return self.memories[:limit]

    async def search_by_keyword(self, keyword: str):
        results = []
        for m in self.memories:
            if isinstance(m, dict):
                content = m.get("content", "")
            else:
                content = m.content
            if keyword in content:
                results.append(m)
        return results

    async def search_by_task_type(self, task_type: str):
        results = []
        for m in self.memories:
            if isinstance(m, dict):
                task = m.get("task_type")
            else:
                task = m.task_type
            if task == task_type:
                results.append(m)
        return results

    async def search_by_time(self, time_range: str):
        return self.memories

    async def search_by_entity(self, entity: str):
        return self.memories

    async def search_by_success(self, success: bool):
        results = []
        for m in self.memories:
            if isinstance(m, dict):
                s = m.get("success")
            else:
                s = m.success
            if s == success:
                results.append(m)
        return results


@pytest.fixture
def mock_llm():
    """Fixture providing mock LLM manager"""
    return MockLLMManager()


@pytest.fixture
def mock_memory_db():
    """Fixture providing mock memory database"""
    return MockMemoryDB()


@pytest.fixture
def mock_vector_store():
    """Fixture providing mock vector store"""
    store = Mock()
    store.search = AsyncMock(return_value=[])
    store.search_knowledge_base = AsyncMock(return_value=[])
    store.search_in_document = AsyncMock(return_value=[])
    return store


@pytest.fixture
def mock_knowledge_graph():
    """Fixture providing mock knowledge graph"""
    kg = Mock()
    kg.get_related_entities = AsyncMock(return_value=[])
    kg.query_paths = AsyncMock(return_value=[])
    return kg


@pytest.fixture
def intelligent_recall(mock_llm, mock_memory_db, mock_vector_store, mock_knowledge_graph):
    """Fixture providing IntelligentRecall instance"""
    return IntelligentRecall(
        llm_manager=mock_llm,
        memory_db=mock_memory_db,
        vector_store=mock_vector_store,
        knowledge_graph=mock_knowledge_graph
    )


# ============================================================================
# Tests for IntelligentRecall initialization
# ============================================================================

class TestIntelligentRecallInit:
    """Tests for IntelligentRecall initialization"""

    def test_init_with_all_params(self, mock_llm, mock_memory_db, mock_vector_store, mock_knowledge_graph):
        """Test initialization with all parameters"""
        recall = IntelligentRecall(
            llm_manager=mock_llm,
            memory_db=mock_memory_db,
            vector_store=mock_vector_store,
            knowledge_graph=mock_knowledge_graph
        )

        assert recall.llm == mock_llm
        assert recall.memory_db == mock_memory_db
        assert recall.vector_store == mock_vector_store
        assert recall.kg == mock_knowledge_graph

    def test_init_without_optional_params(self, mock_llm, mock_memory_db):
        """Test initialization without optional parameters"""
        recall = IntelligentRecall(
            llm_manager=mock_llm,
            memory_db=mock_memory_db
        )

        assert recall.llm == mock_llm
        assert recall.memory_db == mock_memory_db
        assert recall.vector_store is None
        assert recall.kg is None

    def test_default_dimension_weights(self, mock_llm, mock_memory_db):
        """Test default dimension weights are set correctly"""
        recall = IntelligentRecall(
            llm_manager=mock_llm,
            memory_db=mock_memory_db
        )

        # Check all dimensions have weights
        assert len(recall.dimension_weights) == 9
        assert recall.dimension_weights[RetrievalDimension.SEMANTIC_VECTOR] == 0.20
        assert recall.dimension_weights[RetrievalDimension.KEYWORD] == 0.15
        assert recall.dimension_weights[RetrievalDimension.TASK_TYPE] == 0.15

    def test_default_config_values(self, mock_llm, mock_memory_db):
        """Test default configuration values"""
        recall = IntelligentRecall(
            llm_manager=mock_llm,
            memory_db=mock_memory_db
        )

        assert recall.default_top_k == 20
        assert recall.max_items_for_llm_ranking == 30
        assert recall.compression_ratio == 0.7


# ============================================================================
# Tests for IntentUnderstanding dataclass
# ============================================================================

class TestIntentUnderstanding:
    """Tests for IntentUnderstanding dataclass"""

    def test_intent_understanding_creation(self):
        """Test creating IntentUnderstanding"""
        understanding = IntentUnderstanding(
            explicit_intent="test intent",
            implicit_intent="test implicit",
            potential_intent="test potential",
            entities=["entity1", "entity2"],
            task_type="coding",
            reasoning="test reasoning"
        )

        assert understanding.explicit_intent == "test intent"
        assert understanding.implicit_intent == "test implicit"
        assert understanding.entities == ["entity1", "entity2"]
        assert understanding.task_type == "coding"

    def test_intent_understanding_defaults(self):
        """Test IntentUnderstanding default values"""
        understanding = IntentUnderstanding()

        assert understanding.explicit_intent == ""
        assert understanding.implicit_intent == ""
        assert understanding.potential_intent == ""
        assert understanding.entities == []
        assert understanding.task_type == "general"
        assert understanding.reasoning == ""


# ============================================================================
# Tests for MemoryItem dataclass
# ============================================================================

class TestMemoryItem:
    """Tests for MemoryItem dataclass"""

    def test_memory_item_creation(self):
        """Test creating MemoryItem"""
        item = MemoryItem(
            id="test-id",
            content="test content",
            timestamp=1234567890.0,
            importance=0.8,
            task_type="coding"
        )

        assert item.id == "test-id"
        assert item.content == "test content"
        assert item.importance == 0.8
        assert item.task_type == "coding"

    def test_memory_item_defaults(self):
        """Test MemoryItem default values"""
        item = MemoryItem(
            id="test-id",
            content="test content",
            timestamp=1234567890.0
        )

        assert item.id == "test-id"
        assert item.importance == 0.5
        assert item.dimensions == {}
        assert item.entities == []
        assert item.task_type is None
        assert item.success is None
        assert item.user_emphasized is False
        assert item.embedding is None


# ============================================================================
# Tests for RetrievalDimension enum
# ============================================================================

class TestRetrievalDimension:
    """Tests for RetrievalDimension enum"""

    def test_all_dimensions_defined(self):
        """Test all retrieval dimensions are defined"""
        expected_dimensions = [
            "semantic_vector",
            "keyword",
            "task_type",
            "time_context",
            "entity_relation",
            "experience_lesson",
            "user_document",
            "knowledge_base",
            "knowledge_graph"
        ]

        for dim in expected_dimensions:
            assert RetrievalDimension(dim) is not None

    def test_dimension_values(self):
        """Test dimension string values"""
        assert RetrievalDimension.SEMANTIC_VECTOR.value == "semantic_vector"
        assert RetrievalDimension.KEYWORD.value == "keyword"
        assert RetrievalDimension.TASK_TYPE.value == "task_type"


# ============================================================================
# Tests for IntelligentRecall.recall() method
# ============================================================================

class TestIntelligentRecallRecall:
    """Tests for IntelligentRecall.recall() main method"""

    @pytest.mark.asyncio
    async def test_recall_basic_flow(self, intelligent_recall):
        """Test basic recall flow"""
        user_input = "test user input"
        context = {}

        result = await intelligent_recall.recall(user_input, context)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_recall_with_empty_input(self, intelligent_recall):
        """Test recall with empty input"""
        context = {}

        result = await intelligent_recall.recall("", context)

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_recall_with_context(self, intelligent_recall, mock_memory_db):
        """Test recall with context"""
        user_input = "test input"
        context = {"max_context_tokens": 50000}

        result = await intelligent_recall.recall(user_input, context)

        assert isinstance(result, str)


# ============================================================================
# Tests for _smart_understand method
# ============================================================================

class TestSmartUnderstand:
    """Tests for _smart_understand method"""

    @pytest.mark.asyncio
    async def test_smart_understand_basic(self, intelligent_recall):
        """Test basic understanding"""
        result = await intelligent_recall._smart_understand(
            "test input",
            {}
        )

        assert isinstance(result, IntentUnderstanding)
        assert result.task_type is not None

    @pytest.mark.asyncio
    async def test_smart_understand_with_context(self, intelligent_recall):
        """Test understanding with context"""
        context = {"previous_intent": "test"}
        result = await intelligent_recall._smart_understand(
            "test input",
            context
        )

        assert isinstance(result, IntentUnderstanding)

    @pytest.mark.asyncio
    async def test_smart_understand_fallback_on_error(self, mock_llm, mock_memory_db):
        """Test fallback when LLM fails"""
        # Create a recall with failing LLM
        failing_llm = Mock()
        failing_llm.chat = AsyncMock(side_effect=Exception("LLM error"))

        recall = IntelligentRecall(
            llm_manager=failing_llm,
            memory_db=mock_memory_db
        )

        result = await recall._smart_understand("test input", {})

        # Should return fallback understanding
        assert isinstance(result, IntentUnderstanding)
        assert result.explicit_intent == "test input"


# ============================================================================
# Tests for _smart_decide_dimensions method
# ============================================================================

class TestSmartDecideDimensions:
    """Tests for _smart_decide_dimensions method"""

    @pytest.mark.asyncio
    async def test_decide_dimensions_returns_list(self, intelligent_recall):
        """Test that decide dimensions returns a list"""
        understanding = IntentUnderstanding(
            explicit_intent="test",
            task_type="coding"
        )

        result = await intelligent_recall._smart_decide_dimensions(
            understanding,
            {}
        )

        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_decide_dimensions_contains_valid_dimensions(self, intelligent_recall):
        """Test that returned dimensions are valid"""
        understanding = IntentUnderstanding(
            explicit_intent="test",
            task_type="coding"
        )

        result = await intelligent_recall._smart_decide_dimensions(
            understanding,
            {}
        )

        for dim in result:
            assert isinstance(dim, RetrievalDimension)


# ============================================================================
# Tests for retrieval methods
# ============================================================================

class TestRetrievalMethods:
    """Tests for various retrieval methods"""

    @pytest.mark.asyncio
    async def test_search_semantic_no_vector_store(self, intelligent_recall):
        """Test semantic search without vector store"""
        # Create recall without vector store
        recall = IntelligentRecall(
            llm_manager=intelligent_recall.llm,
            memory_db=None,
            vector_store=None
        )

        understanding = IntentUnderstanding(explicit_intent="test")
        result = await recall._search_semantic(understanding, {})

        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_search_semantic_with_vector_store(self, intelligent_recall, mock_vector_store):
        """Test semantic search with vector store"""
        mock_vector_store.search = AsyncMock(return_value=[
            MemoryItem(id="1", content="test", timestamp=123.0, importance=0.5)
        ])

        understanding = IntentUnderstanding(explicit_intent="test")
        result = await intelligent_recall._search_semantic(understanding, {})

        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_search_keyword(self, intelligent_recall, mock_memory_db):
        """Test keyword search"""
        mock_memory_db.memories = [
            MemoryItem(id="1", content="test keyword content", timestamp=123.0, importance=0.5)
        ]

        understanding = IntentUnderstanding(entities=["keyword"])
        result = await intelligent_recall._search_keyword(understanding, {})

        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_search_task_type(self, intelligent_recall, mock_memory_db):
        """Test task type search"""
        mock_memory_db.memories = [
            {"id": "1", "task_type": "coding"}
        ]

        understanding = IntentUnderstanding(task_type="coding")
        result = await intelligent_recall._search_task_type(understanding, {})

        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_search_time_context(self, intelligent_recall):
        """Test time context search"""
        understanding = IntentUnderstanding(explicit_intent="test")
        result = await intelligent_recall._search_time_context(understanding, {})

        assert isinstance(result, RetrievalResult)

    @pytest.mark.asyncio
    async def test_search_entity_relation_no_entities(self, intelligent_recall):
        """Test entity relation search with no entities"""
        understanding = IntentUnderstanding(entities=[])
        result = await intelligent_recall._search_entity_relation(understanding, {})

        assert isinstance(result, RetrievalResult)
        assert result.reasoning == "No entities"

    @pytest.mark.asyncio
    async def test_search_experience_lesson(self, intelligent_recall, mock_memory_db):
        """Test experience lesson search"""
        mock_memory_db.memories = [
            {"id": "1", "content": "success", "success": True, "importance": 0.8}
        ]

        understanding = IntentUnderstanding(explicit_intent="test")
        result = await intelligent_recall._search_experience_lesson(understanding, {})

        assert isinstance(result, RetrievalResult)


# ============================================================================
# Tests for ranking and assembly methods
# ============================================================================

class TestRankingAndAssembly:
    """Tests for ranking and assembly methods"""

    @pytest.mark.asyncio
    async def test_smart_rank_with_empty_results(self, intelligent_recall):
        """Test ranking with empty results"""
        understanding = IntentUnderstanding(explicit_intent="test")
        result = await intelligent_recall._smart_rank(understanding, [], {})

        assert result == []

    @pytest.mark.asyncio
    async def test_smart_rank_with_results(self, intelligent_recall):
        """Test ranking with results"""
        understanding = IntentUnderstanding(explicit_intent="test")
        results = [
            RetrievalResult(
                items=[
                    MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.8),
                    MemoryItem(id="2", content="test2", timestamp=124.0, importance=0.5),
                ],
                scores={"test": 1.0},
                reasoning="test"
            )
        ]

        result = await intelligent_recall._smart_rank(understanding, results, {})

        assert len(result) == 2

    def test_weighted_rank(self, intelligent_recall):
        """Test weighted ranking"""
        items = [
            MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.8),
            MemoryItem(id="2", content="test2", timestamp=124.0, importance=0.5),
        ]

        result = intelligent_recall._weighted_rank(items)

        assert len(result) == 2
        # Higher importance should come first
        assert result[0].importance >= result[1].importance


# ============================================================================
# Tests for smart assemble
# ============================================================================

class TestSmartAssemble:
    """Tests for smart assemble method"""

    @pytest.mark.asyncio
    async def test_smart_assemble_within_limit(self, intelligent_recall):
        """Test assembly within token limit"""
        items = [
            MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.5),
            MemoryItem(id="2", content="test2", timestamp=124.0, importance=0.5),
        ]

        context = {"max_context_tokens": 100000}
        result = await intelligent_recall._smart_assemble(items, context)

        assert result == items


# ============================================================================
# Tests for smart compress
# ============================================================================

class TestSmartCompress:
    """Tests for smart compress method"""

    @pytest.mark.asyncio
    async def test_smart_compress_within_limit(self, intelligent_recall):
        """Test compression within token limit"""
        items = [
            MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.5),
        ]

        context = {"max_context_tokens": 100000}
        result = await intelligent_recall._smart_compress(items, context)

        assert isinstance(result, str)


# ============================================================================
# Tests for helper methods
# ============================================================================

class TestHelperMethods:
    """Tests for helper methods"""

    def test_estimate_length(self, intelligent_recall):
        """Test length estimation"""
        items = [
            MemoryItem(id="1", content="a" * 100, timestamp=123.0, importance=0.5),
            MemoryItem(id="2", content="b" * 100, timestamp=124.0, importance=0.5),
        ]

        length = intelligent_recall._estimate_length(items)

        assert length > 0

    def test_format_context(self, intelligent_recall):
        """Test context formatting"""
        items = [
            MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.5),
            MemoryItem(id="2", content="test2", timestamp=124.0, importance=0.5),
        ]

        result = intelligent_recall._format_context(items)

        assert isinstance(result, str)
        assert "test1" in result
        assert "test2" in result

    def test_deduplicate(self, intelligent_recall):
        """Test deduplication"""
        items = [
            MemoryItem(id="1", content="test1", timestamp=123.0, importance=0.5),
            MemoryItem(id="1", content="test1 duplicate", timestamp=124.0, importance=0.5),
            MemoryItem(id="2", content="test2", timestamp=125.0, importance=0.5),
        ]

        result = intelligent_recall._deduplicate(items)

        assert len(result) == 2
        ids = [item.id for item in result]
        assert "1" in ids
        assert "2" in ids


# ============================================================================
# Tests for RetrievalResult
# ============================================================================

class TestRetrievalResult:
    """Tests for RetrievalResult dataclass"""

    def test_retrieval_result_creation(self):
        """Test creating RetrievalResult"""
        items = [
            MemoryItem(id="1", content="test", timestamp=123.0)
        ]
        result = RetrievalResult(
            items=items,
            scores={"test": 1.0},
            reasoning="test reason"
        )

        assert result.items == items
        assert result.scores == {"test": 1.0}
        assert result.reasoning == "test reason"
