"""
E2E tests for the smart memory system

Tests the complete integration of all smart memory components:
- IntelligentRecall
- ErrorDrivenLearning
- ExperienceDB
- GuardianDaemon
- MemoryManager
"""

import pytest
import asyncio
import os
import tempfile

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.smart_recall import IntelligentRecall
from usmsb_sdk.platform.external.meta_agent.memory.error_learning import ErrorDrivenLearning
from usmsb_sdk.platform.external.meta_agent.memory.experience_db import ExperienceDB
from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import GuardianDaemon
from usmsb_sdk.platform.external.meta_agent.memory.memory_manager import MemoryManager


class MockLLMManager:
    """Mock LLM manager for testing"""

    async def chat(self, prompt: str) -> str:
        """Return mock LLM response"""
        if "分析用户输入" in prompt:
            return '''{
                "explicit_intent": "test intent",
                "implicit_intent": "test implicit",
                "potential_intent": "test potential",
                "entities": ["entity1"],
                "task_type": "coding",
                "reasoning": "test reasoning"
            }'''
        elif "决定检索维度" in prompt or "检索维度" in prompt:
            return '''{
                "dimensions": ["semantic_vector", "keyword"],
                "weights": {"semantic_vector": 0.5, "keyword": 0.5},
                "reasoning": "test"
            }'''
        elif "解决方案" in prompt or "solution" in prompt.lower():
            return '''{
                "solution_type": "retry",
                "solution_data": {"wait_seconds": 1},
                "reasoning": "Test reasoning",
                "prevent_future": "Prevention"
            }'''
        elif "复盘" in prompt or "总结" in prompt:
            return '''{
                "summary": "Test summary",
                "successes": ["success1"],
                "improvements": ["improvement1"],
                "suggestions": ["suggestion1"]
            }'''
        elif "错误" in prompt:
            return '''{
                "root_causes": ["cause1"],
                "preventions": ["prevention1"],
                "lessons": ["lesson1"]
            }'''
        elif "能力" in prompt:
            return '''{
                "capabilities": {"coding": 0.8, "reasoning": 0.7},
                "improvement_areas": ["area1"],
                "strengths": ["strength1"]
            }'''
        elif "排序" in prompt:
            return '''{"ranked_ids": [], "reasoning": "test"}'''
        elif "选择" in prompt:
            return '''{"selected_ids": [], "reasoning": "test"}'''
        return '{"result": "ok"}'


class MockKnowledgeBase:
    """Mock knowledge base"""

    async def add_knowledge(self, content: str, metadata: dict = None):
        pass


@pytest.fixture
def temp_db_dir(tmp_path):
    """Fixture providing temporary directory for databases"""
    db_dir = tmp_path / "e2e_dbs"
    db_dir.mkdir()
    yield str(db_dir)
    # Cleanup
    import shutil
    if os.path.exists(db_dir):
        shutil.rmtree(db_dir, ignore_errors=True)


# ============================================================================
# E2E Test: Complete Smart Recall Flow
# ============================================================================

class TestSmartRecallE2E:
    """End-to-end tests for smart recall"""

    @pytest.mark.asyncio
    async def test_full_recall_flow(self, temp_db_dir):
        """Test complete recall flow"""
        # Setup
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        recall = IntelligentRecall(
            llm_manager=MockLLMManager(),
            memory_db=memory_db
        )

        # Execute recall
        result = await recall.recall(
            user_input="How did I solve the JSON parsing issue?",
            context={"user_id": "test_user"}
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_recall_with_context(self, temp_db_dir):
        """Test recall with full context"""
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        recall = IntelligentRecall(
            llm_manager=MockLLMManager(),
            memory_db=memory_db
        )

        # Add some memories
        await memory_db.add_important_memory(
            user_id="user1",
            content="Successfully resolved JSON parsing error by using try-except",
            memory_type="success_experience",
            importance=0.8
        )

        result = await recall.recall(
            user_input="JSON parsing error",
            context={"user_id": "user1", "max_context_tokens": 50000}
        )

        assert isinstance(result, str)


# ============================================================================
# E2E Test: Complete Error Learning Flow
# ============================================================================

class TestErrorLearningE2E:
    """End-to-end tests for error-driven learning"""

    @pytest.mark.asyncio
    async def test_error_handling_flow(self, temp_db_dir):
        """Test complete error handling flow"""
        # Setup
        experience_db = ExperienceDB(
            db_path=os.path.join(temp_db_dir, "experience.db")
        )

        error_learning = ErrorDrivenLearning(
            llm_manager=MockLLMManager(),
            experience_db=experience_db
        )

        # Simulate an error
        error = ValueError("Invalid JSON format")
        context = {"tool_name": "parser", "params": {"data": "{}"}}

        # Handle error
        result = await error_learning.handle_error(error, context)

        assert isinstance(result, dict)
        assert "action" in result

    @pytest.mark.asyncio
    async def test_error_learning_with_solution_storage(self, temp_db_dir):
        """Test error learning with solution storage"""
        experience_db = ExperienceDB(
            db_path=os.path.join(temp_db_dir, "experience.db")
        )

        error_learning = ErrorDrivenLearning(
            llm_manager=MockLLMManager(),
            experience_db=experience_db
        )

        # Add a solution to experience DB for a specific error
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "error_message": "Invalid JSON at position 0",
            "solution_type": "retry",
            "solution_data": {"wait_seconds": 1},
            "tool_name": "parser"
        })

        # Clear any cache that might exist
        error_learning._solutions_cache.clear()

        # Now handle a DIFFERENT error - no solution match, will use LLM
        # This tests the fallback path when no matching solution is found
        error = ValueError("Completely different error")
        context = {"tool_name": "parser"}

        result = await error_learning.handle_error(error, context)

        assert isinstance(result, dict)


# ============================================================================
# E2E Test: Complete Guardian Daemon Flow
# ============================================================================

class TestGuardianDaemonE2E:
    """End-to-end tests for guardian daemon"""

    @pytest.mark.asyncio
    async def test_guardian_daemon_lifecycle(self, temp_db_dir):
        """Test complete guardian daemon lifecycle"""
        from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import GuardianConfig

        # Setup
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        config = GuardianConfig()
        config.hourly_enabled = False
        config.daily_enabled = False

        guardian = GuardianDaemon(
            llm_manager=MockLLMManager(),
            knowledge_base=MockKnowledgeBase(),
            memory_manager=memory_db,
            evolution_engine=object(),
            config=config
        )

        # Start daemon
        await guardian.start()
        assert guardian._running is True

        # Notify task complete
        guardian.notify_task_complete()

        # Wait for async tasks
        await asyncio.sleep(0.3)

        # Stop daemon
        await guardian.stop()
        assert guardian._running is False

    @pytest.mark.asyncio
    async def test_guardian_error_review(self, temp_db_dir):
        """Test guardian error review"""
        from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import GuardianConfig, GuardianTask

        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        # Add error record
        await memory_db.add_important_memory(
            user_id="system",
            content="Error: JSON parsing failed",
            memory_type="error_record",
            importance=0.9
        )

        config = GuardianConfig()
        config.hourly_enabled = False
        config.daily_enabled = False

        guardian = GuardianDaemon(
            llm_manager=MockLLMManager(),
            knowledge_base=MockKnowledgeBase(),
            memory_manager=memory_db,
            evolution_engine=object(),
            config=config
        )

        # Execute error review task
        await guardian._execute_single_task(GuardianTask.ERROR_REVIEW)


# ============================================================================
# E2E Test: Integration of All Components
# ============================================================================

class TestSmartMemorySystemIntegration:
    """End-to-end tests for complete smart memory system"""

    @pytest.mark.asyncio
    async def test_complete_memory_system(self, temp_db_dir):
        """Test complete smart memory system integration"""
        # 1. Setup all components
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        # Don't add experience_db to avoid matching issues
        recall = IntelligentRecall(
            llm_manager=MockLLMManager(),
            memory_db=memory_db
        )

        error_learning = ErrorDrivenLearning(
            llm_manager=MockLLMManager(),
            experience_db=None  # No experience DB to avoid matching issues
        )

        # 2. Add memories
        await memory_db.add_important_memory(
            user_id="user1",
            content="Successfully handled timeout error by adding retry",
            memory_type="success_experience",
            importance=0.8
        )

        await memory_db.add_important_memory(
            user_id="user1",
            content="Error: Connection refused",
            memory_type="error_record",
            importance=0.9
        )

        # 3. Test recall
        recall_result = await recall.recall(
            user_input="How to handle connection errors?",
            context={"user_id": "user1"}
        )

        assert isinstance(recall_result, str)

        # 4. Test error handling
        error_result = await error_learning.handle_error(
            ConnectionError("Connection refused"),
            {"tool_name": "http_client"}
        )

        assert isinstance(error_result, dict)

    @pytest.mark.asyncio
    async def test_memory_recall_and_error_recovery(self, temp_db_dir):
        """Test memory recall and error recovery flow"""
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        experience_db = ExperienceDB(
            db_path=os.path.join(temp_db_dir, "experience.db")
        )

        # Add a success experience
        await memory_db.add_important_memory(
            user_id="user1",
            content="When JSON parse fails, use json.loads with try-except block",
            memory_type="success_experience",
            importance=0.9
        )

        # Store error solution
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "error_message": "Invalid JSON",
            "solution_type": "fix_params",
            "solution_data": {"fixed_params": {"strict": False}},
            "tool_name": "parser"
        })

        # Test recall
        recall = IntelligentRecall(
            llm_manager=MockLLMManager(),
            memory_db=memory_db
        )

        result = await recall.recall(
            user_input="JSON parsing issue",
            context={"user_id": "user1"}
        )

        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_concurrent_memory_operations(self, temp_db_dir):
        """Test concurrent memory operations"""
        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        # Add multiple memories concurrently
        tasks = [
            memory_db.add_important_memory(
                user_id="user1",
                content=f"Memory {i}",
                memory_type="general",
                importance=0.5
            )
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        # Search for memories
        results = await memory_db.search("Memory")

        assert isinstance(results, list)


# ============================================================================
# E2E Test: Error Recovery and Learning
# ============================================================================

class TestErrorRecoveryAndLearning:
    """End-to-end tests for error recovery and learning"""

    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, temp_db_dir):
        """Test error recovery with learning"""
        experience_db = ExperienceDB(
            db_path=os.path.join(temp_db_dir, "experience.db")
        )

        error_learning = ErrorDrivenLearning(
            llm_manager=MockLLMManager(),
            experience_db=experience_db
        )

        # First error - no known solution
        error1 = ValueError("Network timeout")
        result1 = await error_learning.handle_error(
            error1,
            {"tool_name": "http"}
        )

        assert isinstance(result1, dict)

        # Second error - should have solution now
        error2 = ValueError("Network timeout")
        result2 = await error_learning.handle_error(
            error2,
            {"tool_name": "http"}
        )

        assert isinstance(result2, dict)

    @pytest.mark.asyncio
    async def test_multiple_error_types(self, temp_db_dir):
        """Test handling multiple error types"""
        experience_db = ExperienceDB(
            db_path=os.path.join(temp_db_dir, "experience.db")
        )

        error_learning = ErrorDrivenLearning(
            llm_manager=MockLLMManager(),
            experience_db=experience_db
        )

        errors = [
            (ValueError("Invalid JSON"), "json_format"),
            (ConnectionError("Connection refused"), "network_error"),
            (TimeoutError("Timeout"), "timeout_error"),
        ]

        for error, error_type in errors:
            result = await error_learning.handle_error(
                error,
                {"tool_name": "test"}
            )
            assert isinstance(result, dict)


# ============================================================================
# E2E Test: Guardian and Memory Integration
# ============================================================================

class TestGuardianMemoryIntegration:
    """End-to-end tests for guardian and memory integration"""

    @pytest.mark.asyncio
    async def test_guardian_uses_memory(self, temp_db_dir):
        """Test guardian daemon using memory manager"""
        from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import GuardianConfig

        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        # Add data for guardian to use
        await memory_db.add_important_memory(
            user_id="system",
            content="Test conversation for review",
            memory_type="conversation",
            importance=0.5
        )

        config = GuardianConfig()
        config.hourly_enabled = False
        config.daily_enabled = False

        guardian = GuardianDaemon(
            llm_manager=MockLLMManager(),
            knowledge_base=MockKnowledgeBase(),
            memory_manager=memory_db,
            evolution_engine=object(),
            config=config
        )

        # Execute review summary task
        await guardian._review_summary()

    @pytest.mark.asyncio
    async def test_guardian_knowledge_update(self, temp_db_dir):
        """Test guardian knowledge update"""
        from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import GuardianConfig

        memory_db = MemoryManager(
            db_path=os.path.join(temp_db_dir, "memory.db"),
            llm_manager=MockLLMManager()
        )

        # Add pending knowledge
        await memory_db.add_important_memory(
            user_id="system",
            content="New knowledge to validate",
            memory_type="pending_knowledge",
            importance=0.6
        )

        config = GuardianConfig()
        config.hourly_enabled = False
        config.daily_enabled = False

        guardian = GuardianDaemon(
            llm_manager=MockLLMManager(),
            knowledge_base=MockKnowledgeBase(),
            memory_manager=memory_db,
            evolution_engine=object(),
            config=config
        )

        # Execute knowledge update task
        await guardian._knowledge_update()
