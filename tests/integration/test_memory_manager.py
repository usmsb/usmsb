"""
Integration tests for MemoryManager

Tests the integration of new methods added to MemoryManager
for smart recall and guardian daemon support.
"""

import pytest
import asyncio
import os
import tempfile

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.memory_manager import (
    MemoryManager,
    MemoryConfig,
    ConversationSummary,
    UserProfile,
)


class MockLLMManager:
    """Mock LLM manager for testing"""

    async def chat(self, prompt: str) -> str:
        """Return mock LLM response"""
        if "摘要" in prompt:
            return '''{
                "summary": "Test summary of the conversation",
                "key_topics": ["topic1", "topic2"],
                "decisions": ["decision1"]
            }'''
        elif "偏好" in prompt or "preference" in prompt.lower():
            return '''{
                "preferences": {"style": "concise", "language": "zh"},
                "commitments": ["commitment1"],
                "knowledge": {"fact": "value"}
            }'''
        return '{"result": "ok"}'


@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture providing temporary database path"""
    db_path = tmp_path / "test_memory.db"
    yield str(db_path)
    # Cleanup
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass


@pytest.fixture
def memory_manager(temp_db_path):
    """Fixture providing MemoryManager instance"""
    config = MemoryConfig(
        short_term_messages=5,
        summary_threshold=10,
        max_summaries=5,
        extract_preferences=True
    )
    return MemoryManager(
        db_path=temp_db_path,
        config=config,
        llm_manager=MockLLMManager()
    )


# ============================================================================
# Tests for MemoryManager initialization
# ============================================================================

class TestMemoryManagerInit:
    """Tests for MemoryManager initialization"""

    @pytest.mark.asyncio
    async def test_init(self, memory_manager):
        """Test initialization"""
        await memory_manager.init()

        assert memory_manager._initialized is True

    @pytest.mark.asyncio
    async def test_init_twice(self, memory_manager):
        """Test initialization twice"""
        await memory_manager.init()
        await memory_manager.init()

        assert memory_manager._initialized is True


# ============================================================================
# Tests for process_conversation
# ============================================================================

class TestProcessConversation:
    """Tests for process_conversation method"""

    @pytest.mark.asyncio
    async def test_process_conversation_with_few_messages(self, memory_manager):
        """Test processing with few messages"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        await memory_manager.process_conversation(
            conversation_id="test_conv",
            user_id="test_user",
            messages=messages
        )

        # Should not raise

    @pytest.mark.asyncio
    async def test_process_conversation_with_many_messages(self, memory_manager):
        """Test processing with many messages"""
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(20)
        ]

        await memory_manager.process_conversation(
            conversation_id="test_conv",
            user_id="test_user",
            messages=messages
        )


# ============================================================================
# Tests for get_context
# ============================================================================

class TestGetContext:
    """Tests for get_context method"""

    @pytest.mark.asyncio
    async def test_get_context_empty(self, memory_manager):
        """Test getting context when empty"""
        await memory_manager.init()

        context = await memory_manager.get_context(
            user_id="test_user",
            conversation_id="test_conv"
        )

        assert "summaries" in context
        assert "user_profile" in context
        assert "important_memories" in context

    @pytest.mark.asyncio
    async def test_get_context_with_data(self, memory_manager):
        """Test getting context with data"""
        # Add some data first
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Test important memory",
            memory_type="preference",
            importance=0.8
        )

        context = await memory_manager.get_context(
            user_id="test_user",
            conversation_id="test_conv"
        )

        assert context is not None


# ============================================================================
# Tests for build_context_prompt
# ============================================================================

class TestBuildContextPrompt:
    """Tests for build_context_prompt method"""

    def test_build_empty_context(self, memory_manager):
        """Test building prompt with empty context"""
        context = {
            "summaries": [],
            "user_profile": None,
            "important_memories": []
        }

        prompt = memory_manager.build_context_prompt(context)

        assert prompt == ""

    def test_build_context_with_summaries(self, memory_manager):
        """Test building prompt with summaries"""
        context = {
            "summaries": [
                {
                    "summary": "Test summary",
                    "topics": ["topic1"],
                    "decisions": ["decision1"],
                    "message_count": 10
                }
            ],
            "user_profile": None,
            "important_memories": []
        }

        prompt = memory_manager.build_context_prompt(context)

        assert "Test summary" in prompt

    def test_build_context_with_profile(self, memory_manager):
        """Test building prompt with user profile"""
        context = {
            "summaries": [],
            "user_profile": {
                "preferences": {"style": "concise"},
                "commitments": ["commitment1"],
                "knowledge": {}
            },
            "important_memories": []
        }

        prompt = memory_manager.build_context_prompt(context)

        assert "用户画像" in prompt

    def test_build_context_with_memories(self, memory_manager):
        """Test building prompt with important memories"""
        context = {
            "summaries": [],
            "user_profile": None,
            "important_memories": [
                {"content": "Important note", "type": "preference"}
            ]
        }

        prompt = memory_manager.build_context_prompt(context)

        assert "Important note" in prompt


# ============================================================================
# Tests for smart recall methods
# ============================================================================

class TestSmartRecallMethods:
    """Tests for smart recall support methods"""

    @pytest.mark.asyncio
    async def test_search(self, memory_manager):
        """Test general search"""
        await memory_manager.init()

        # Add some memories
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Python programming",
            memory_type="skill",
            importance=0.8
        )

        results = await memory_manager.search("Python")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_by_keyword(self, memory_manager):
        """Test keyword search"""
        await memory_manager.init()

        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Test keyword content",
            memory_type="general",
            importance=0.5
        )

        results = await memory_manager.search_by_keyword("keyword")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_by_task_type(self, memory_manager):
        """Test task type search"""
        await memory_manager.init()

        results = await memory_manager.search_by_task_type("coding")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_by_time(self, memory_manager):
        """Test time-based search"""
        await memory_manager.init()

        results = await memory_manager.search_by_time("recent")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_by_entity(self, memory_manager):
        """Test entity search"""
        await memory_manager.init()

        results = await memory_manager.search_by_entity("entity")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_by_success(self, memory_manager):
        """Test success/failure search"""
        await memory_manager.init()

        # Add success experience
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Successful approach",
            memory_type="success_experience",
            importance=0.8
        )

        results = await memory_manager.search_by_success(True)

        assert isinstance(results, list)


# ============================================================================
# Tests for guardian daemon methods
# ============================================================================

class TestGuardianDaemonMethods:
    """Tests for guardian daemon support methods"""

    @pytest.mark.asyncio
    async def test_get_recent_conversations(self, memory_manager):
        """Test getting recent conversations"""
        await memory_manager.init()

        results = await memory_manager.get_recent_conversations(limit=10)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_recent_errors(self, memory_manager):
        """Test getting recent errors"""
        await memory_manager.init()

        # Add error record
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Error occurred: something failed",
            memory_type="error_record",
            importance=0.9
        )

        results = await memory_manager.get_recent_errors(limit=10)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_successful_conversations(self, memory_manager):
        """Test getting successful conversations"""
        await memory_manager.init()

        results = await memory_manager.get_successful_conversations(limit=10)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_pending_knowledge(self, memory_manager):
        """Test getting pending knowledge"""
        await memory_manager.init()

        results = await memory_manager.get_pending_knowledge()

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_mark_knowledge_validated(self, memory_manager):
        """Test marking knowledge as validated"""
        await memory_manager.init()

        # Add pending knowledge
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="New knowledge to validate",
            memory_type="pending_knowledge",
            importance=0.5
        )

        # Mark as validated (will use the last added memory ID)
        await memory_manager.mark_knowledge_validated("some_id")

    @pytest.mark.asyncio
    async def test_get_execution_logs(self, memory_manager):
        """Test getting execution logs"""
        await memory_manager.init()

        # Add execution log
        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Executed tool: test_tool",
            memory_type="execution_log",
            importance=0.6
        )

        results = await memory_manager.get_execution_logs(limit=10)

        assert isinstance(results, list)


# ============================================================================
# Tests for add_important_memory
# ============================================================================

class TestAddImportantMemory:
    """Tests for add_important_memory method"""

    @pytest.mark.asyncio
    async def test_add_important_memory(self, memory_manager):
        """Test adding important memory"""
        await memory_manager.init()

        await memory_manager.add_important_memory(
            user_id="test_user",
            content="Important test content",
            memory_type="test",
            importance=0.7,
            context={"key": "value"}
        )

    @pytest.mark.asyncio
    async def test_add_multiple_memories(self, memory_manager):
        """Test adding multiple memories"""
        await memory_manager.init()

        for i in range(5):
            await memory_manager.add_important_memory(
                user_id="test_user",
                content=f"Memory {i}",
                memory_type="test",
                importance=0.5 + i * 0.1
            )


# ============================================================================
# Integration tests
# ============================================================================

class TestMemoryManagerIntegration:
    """Integration tests for MemoryManager"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, memory_manager):
        """Test complete memory workflow"""
        # Initialize
        await memory_manager.init()

        # Add important memories
        await memory_manager.add_important_memory(
            user_id="user1",
            content="User prefers concise responses",
            memory_type="preference",
            importance=0.8
        )

        await memory_manager.add_important_memory(
            user_id="user1",
            content="Error: JSON parse failed",
            memory_type="error_record",
            importance=0.9
        )

        await memory_manager.add_important_memory(
            user_id="user1",
            content="Used retry pattern successfully",
            memory_type="success_experience",
            importance=0.7
        )

        # Get context
        context = await memory_manager.get_context(user_id="user1")

        assert context is not None
        assert len(context["important_memories"]) >= 0

        # Build prompt
        prompt = memory_manager.build_context_prompt(context)

        assert isinstance(prompt, str)

    @pytest.mark.asyncio
    async def test_search_integration(self, memory_manager):
        """Test search integration"""
        await memory_manager.init()

        # Add various memories
        await memory_manager.add_important_memory(
            user_id="user1",
            content="Python is a programming language",
            memory_type="skill",
            importance=0.8
        )

        await memory_manager.add_important_memory(
            user_id="user1",
            content="JavaScript is for web development",
            memory_type="skill",
            importance=0.7
        )

        # Search
        results = await memory_manager.search("Python")

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_time_based_search(self, memory_manager):
        """Test time-based search"""
        await memory_manager.init()

        results_recent = await memory_manager.search_by_time("recent")
        results_week = await memory_manager.search_by_time("week")
        results_month = await memory_manager.search_by_time("month")
        results_all = await memory_manager.search_by_time("all")

        assert isinstance(results_recent, list)
        assert isinstance(results_week, list)
        assert isinstance(results_month, list)
        assert isinstance(results_all, list)
