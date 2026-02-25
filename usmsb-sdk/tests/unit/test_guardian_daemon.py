"""
Unit tests for guardian_daemon.py - GuardianDaemon class

Tests the guardian daemon for self-evolution and learning.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.guardian_daemon import (
    GuardianDaemon,
    GuardianConfig,
    GuardianStats,
    TriggerType,
    GuardianTask,
)


class MockLLMManager:
    """Mock LLM manager for testing"""

    async def chat(self, prompt: str) -> str:
        """Return mock LLM response"""
        if "复盘" in prompt or "总结" in prompt:
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
        return '{"result": "ok"}'


class MockKnowledgeBase:
    """Mock knowledge base"""

    async def add_knowledge(self, content: str, metadata: dict = None):
        pass


class MockMemoryManager:
    """Mock memory manager"""

    def __init__(self):
        self.conversations = []
        self.errors = []

    async def get_recent_conversations(self, limit: int = 10):
        return self.conversations[:limit]

    async def get_recent_errors(self, limit: int = 10):
        return self.errors[:limit]

    async def get_successful_conversations(self, limit: int = 10):
        return []

    async def get_pending_knowledge(self):
        return []

    async def get_execution_logs(self, limit: int = 50):
        return []

    async def mark_knowledge_validated(self, knowledge_id: str):
        pass


class MockEvolutionEngine:
    """Mock evolution engine"""
    pass


@pytest.fixture
def mock_llm():
    """Fixture providing mock LLM manager"""
    return MockLLMManager()


@pytest.fixture
def mock_knowledge_base():
    """Fixture providing mock knowledge base"""
    return MockKnowledgeBase()


@pytest.fixture
def mock_memory_manager():
    """Fixture providing mock memory manager"""
    return MockMemoryManager()


@pytest.fixture
def mock_evolution_engine():
    """Fixture providing mock evolution engine"""
    return MockEvolutionEngine()


@pytest.fixture
def guardian_config():
    """Fixture providing guardian config"""
    config = GuardianConfig()
    config.idle_timeout_minutes = 1
    config.tasks_before_trigger = 2
    config.errors_before_trigger = 1
    config.hourly_enabled = False
    config.daily_enabled = False
    return config


@pytest.fixture
def guardian_daemon(mock_llm, mock_knowledge_base, mock_memory_manager, mock_evolution_engine, guardian_config):
    """Fixture providing GuardianDaemon instance"""
    return GuardianDaemon(
        llm_manager=mock_llm,
        knowledge_base=mock_knowledge_base,
        memory_manager=mock_memory_manager,
        evolution_engine=mock_evolution_engine,
        config=guardian_config
    )


# ============================================================================
# Tests for GuardianConfig
# ============================================================================

class TestGuardianConfig:
    """Tests for GuardianConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = GuardianConfig()

        assert config.idle_timeout_minutes == 5
        assert config.tasks_before_trigger == 10
        assert config.errors_before_trigger == 3
        assert config.hourly_enabled is True
        assert config.daily_enabled is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = GuardianConfig(
            idle_timeout_minutes=10,
            tasks_before_trigger=5,
            errors_before_trigger=2
        )

        assert config.idle_timeout_minutes == 10
        assert config.tasks_before_trigger == 5
        assert config.errors_before_trigger == 2


# ============================================================================
# Tests for GuardianStats
# ============================================================================

class TestGuardianStats:
    """Tests for GuardianStats"""

    def test_default_stats(self):
        """Test default statistics"""
        stats = GuardianStats()

        assert stats.tasks_completed == 0
        assert stats.last_task_time == 0
        assert stats.total_evolutions == 0
        assert stats.errors_learned_from == 0
        assert stats.experiences_extracted == 0


# ============================================================================
# Tests for TriggerType enum
# ============================================================================

class TestTriggerType:
    """Tests for TriggerType enum"""

    def test_all_trigger_types_defined(self):
        """Test all trigger types are defined"""
        expected = ["idle", "task_complete", "error_accumulated", "scheduled", "capability_gap", "new_knowledge"]
        for trigger in expected:
            assert TriggerType(trigger) is not None


# ============================================================================
# Tests for GuardianTask enum
# ============================================================================

class TestGuardianTask:
    """Tests for GuardianTask enum"""

    def test_all_tasks_defined(self):
        """Test all guardian tasks are defined"""
        expected = [
            "review_summary", "error_review", "experience_extraction",
            "active_learning", "capability_assessment", "goal_adjustment",
            "exploration", "knowledge_update", "self_optimization"
        ]
        for task in expected:
            assert GuardianTask(task) is not None


# ============================================================================
# Tests for GuardianDaemon initialization
# ============================================================================

class TestGuardianDaemonInit:
    """Tests for GuardianDaemon initialization"""

    def test_init_with_all_params(self, mock_llm, mock_knowledge_base, mock_memory_manager, mock_evolution_engine, guardian_config):
        """Test initialization with all parameters"""
        daemon = GuardianDaemon(
            llm_manager=mock_llm,
            knowledge_base=mock_knowledge_base,
            memory_manager=mock_memory_manager,
            evolution_engine=mock_evolution_engine,
            config=guardian_config
        )

        assert daemon.llm == mock_llm
        assert daemon.knowledge == mock_knowledge_base
        assert daemon.memory == mock_memory_manager
        assert daemon.evolution == mock_evolution_engine

    def test_init_default_config(self, mock_llm, mock_knowledge_base, mock_memory_manager, mock_evolution_engine):
        """Test initialization with default config"""
        daemon = GuardianDaemon(
            llm_manager=mock_llm,
            knowledge_base=mock_knowledge_base,
            memory_manager=mock_memory_manager,
            evolution_engine=mock_evolution_engine
        )

        assert daemon.config is not None
        assert isinstance(daemon.config, GuardianConfig)

    def test_initial_state(self, guardian_daemon):
        """Test initial state"""
        assert guardian_daemon._running is False
        assert guardian_daemon._guardian_task is None
        assert guardian_daemon._task_count == 0
        assert guardian_daemon._error_count == 0


# ============================================================================
# Tests for start/stop
# ============================================================================

class TestStartStop:
    """Tests for start and stop methods"""

    @pytest.mark.asyncio
    async def test_start(self, guardian_daemon):
        """Test starting the daemon"""
        await guardian_daemon.start()

        assert guardian_daemon._running is True
        assert guardian_daemon._guardian_task is not None

    @pytest.mark.asyncio
    async def test_start_already_running(self, guardian_daemon):
        """Test starting when already running"""
        guardian_daemon._running = True

        await guardian_daemon.start()

        # Should not create another task
        assert guardian_daemon._guardian_task is None

    @pytest.mark.asyncio
    async def test_stop(self, guardian_daemon):
        """Test stopping the daemon"""
        guardian_daemon._running = True
        guardian_daemon._guardian_task = asyncio.create_task(asyncio.sleep(100))

        await guardian_daemon.stop()

        assert guardian_daemon._running is False


# ============================================================================
# Tests for notify methods
# ============================================================================

class TestNotifyMethods:
    """Tests for notification methods"""

    def test_notify_task_complete(self, guardian_daemon):
        """Test task complete notification"""
        # Set task count to one less than threshold (threshold is 2)
        guardian_daemon._task_count = 1

        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            guardian_daemon.notify_task_complete()

            # Task count should reset after trigger
            # (It's reset in _execute_guardian_tasks)
            # Should trigger guardian
            mock_trigger.assert_called_once()

    def test_notify_task_complete_no_trigger(self, guardian_daemon):
        """Test task complete without triggering"""
        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            guardian_daemon.notify_task_complete()

            mock_trigger.assert_not_called()

    def test_notify_error(self, guardian_daemon):
        """Test error notification"""
        guardian_daemon._error_count = 0

        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            guardian_daemon.notify_error()

            assert guardian_daemon._error_count == 1

    def test_notify_error_trigger(self, guardian_daemon):
        """Test error notification triggering"""
        guardian_daemon._error_count = 0

        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            # Set to one less than threshold (threshold is 1)
            guardian_daemon._error_count = 0
            guardian_daemon.notify_error()

            # Threshold is 1, so should trigger
            mock_trigger.assert_called_once_with(TriggerType.ERROR_ACCUMULATED)

    def test_notify_idle(self, guardian_daemon):
        """Test idle notification"""
        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            guardian_daemon.notify_idle()

            # Should not trigger immediately (needs timeout)

    def test_notify_new_knowledge(self, guardian_daemon):
        """Test new knowledge notification"""
        with patch.object(guardian_daemon, '_trigger_guardian') as mock_trigger:
            guardian_daemon.notify_new_knowledge()

            mock_trigger.assert_called_once_with(TriggerType.NEW_KNOWLEDGE)


# ============================================================================
# Tests for _trigger_guardian
# ============================================================================

class TestTriggerGuardian:
    """Tests for _trigger_guardian method"""

    def test_trigger_guardian_not_running(self, guardian_daemon):
        """Test triggering when not running"""
        guardian_daemon._running = False

        with patch.object(guardian_daemon, '_execute_guardian_tasks') as mock_exec:
            guardian_daemon._trigger_guardian(TriggerType.IDLE)

            mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_trigger_guardian_running(self, guardian_daemon):
        """Test triggering when running"""
        guardian_daemon._running = True

        # Should not raise
        guardian_daemon._trigger_guardian(TriggerType.IDLE)

        # Let the async task run
        await asyncio.sleep(0.1)


# ============================================================================
# Tests for _select_tasks
# ============================================================================

class TestSelectTasks:
    """Tests for _select_tasks method"""

    def test_select_tasks_idle(self, guardian_daemon):
        """Test task selection for idle trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.IDLE)

        assert GuardianTask.REVIEW_SUMMARY in tasks
        assert GuardianTask.ERROR_REVIEW in tasks
        assert GuardianTask.CAPABILITY_ASSESSMENT in tasks

    def test_select_tasks_task_complete(self, guardian_daemon):
        """Test task selection for task complete trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.TASK_COMPLETE)

        assert GuardianTask.EXPERIENCE_EXTRACTION in tasks
        assert GuardianTask.KNOWLEDGE_UPDATE in tasks

    def test_select_tasks_error_accumulated(self, guardian_daemon):
        """Test task selection for error accumulated trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.ERROR_ACCUMULATED)

        assert GuardianTask.ERROR_REVIEW in tasks
        assert GuardianTask.SELF_OPTIMIZATION in tasks

    def test_select_tasks_capability_gap(self, guardian_daemon):
        """Test task selection for capability gap trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.CAPABILITY_GAP)

        assert GuardianTask.CAPABILITY_ASSESSMENT in tasks
        assert GuardianTask.GOAL_ADJUSTMENT in tasks
        assert GuardianTask.EXPLORATION in tasks

    def test_select_tasks_new_knowledge(self, guardian_daemon):
        """Test task selection for new knowledge trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.NEW_KNOWLEDGE)

        assert GuardianTask.KNOWLEDGE_UPDATE in tasks
        assert GuardianTask.EXPERIENCE_EXTRACTION in tasks

    def test_select_tasks_scheduled(self, guardian_daemon):
        """Test task selection for scheduled trigger"""
        tasks = guardian_daemon._select_tasks(TriggerType.SCHEDULED)

        assert GuardianTask.REVIEW_SUMMARY in tasks
        assert GuardianTask.ACTIVE_LEARNING in tasks


# ============================================================================
# Tests for get_stats
# ============================================================================

class TestGetStats:
    """Tests for get_stats method"""

    def test_get_stats(self, guardian_daemon):
        """Test getting statistics"""
        stats = guardian_daemon.get_stats()

        assert "running" in stats
        assert "tasks_completed" in stats
        assert "total_evolutions" in stats
        assert "errors_learned_from" in stats
        assert "experiences_extracted" in stats

    def test_get_stats_values(self, guardian_daemon):
        """Test statistics values"""
        guardian_daemon.stats.tasks_completed = 5

        stats = guardian_daemon.get_stats()

        assert stats["running"] is False
        assert stats["tasks_completed"] == 5


# ============================================================================
# Tests for task execution methods
# ============================================================================

class TestTaskExecution:
    """Tests for individual task execution methods"""

    @pytest.mark.asyncio
    async def test_execute_single_task_review_summary(self, guardian_daemon):
        """Test executing review summary task"""
        await guardian_daemon._execute_single_task(GuardianTask.REVIEW_SUMMARY)

    @pytest.mark.asyncio
    async def test_execute_single_task_error_review(self, guardian_daemon):
        """Test executing error review task"""
        await guardian_daemon._execute_single_task(GuardianTask.ERROR_REVIEW)

    @pytest.mark.asyncio
    async def test_execute_single_task_experience_extraction(self, guardian_daemon):
        """Test executing experience extraction task"""
        await guardian_daemon._execute_single_task(GuardianTask.EXPERIENCE_EXTRACTION)

    @pytest.mark.asyncio
    async def test_execute_single_task_active_learning(self, guardian_daemon):
        """Test executing active learning task"""
        await guardian_daemon._execute_single_task(GuardianTask.ACTIVE_LEARNING)

    @pytest.mark.asyncio
    async def test_execute_single_task_capability_assessment(self, guardian_daemon):
        """Test executing capability assessment task"""
        await guardian_daemon._execute_single_task(GuardianTask.CAPABILITY_ASSESSMENT)

    @pytest.mark.asyncio
    async def test_execute_single_task_goal_adjustment(self, guardian_daemon):
        """Test executing goal adjustment task"""
        # Need some capabilities set
        guardian_daemon._capabilities = {"test": 0.5}

        await guardian_daemon._execute_single_task(GuardianTask.GOAL_ADJUSTMENT)

    @pytest.mark.asyncio
    async def test_execute_single_task_exploration(self, guardian_daemon):
        """Test executing exploration task"""
        await guardian_daemon._execute_single_task(GuardianTask.EXPLORATION)

    @pytest.mark.asyncio
    async def test_execute_single_task_knowledge_update(self, guardian_daemon):
        """Test executing knowledge update task"""
        await guardian_daemon._execute_single_task(GuardianTask.KNOWLEDGE_UPDATE)

    @pytest.mark.asyncio
    async def test_execute_single_task_self_optimization(self, guardian_daemon):
        """Test executing self optimization task"""
        await guardian_daemon._execute_single_task(GuardianTask.SELF_OPTIMIZATION)


# ============================================================================
# Tests for _validate_knowledge
# ============================================================================

class TestValidateKnowledge:
    """Tests for _validate_knowledge method"""

    @pytest.mark.asyncio
    async def test_validate_knowledge(self, guardian_daemon):
        """Test knowledge validation"""
        knowledge = {"content": "Test knowledge"}

        result = await guardian_daemon._validate_knowledge(knowledge)

        assert isinstance(result, bool)


# ============================================================================
# Integration tests
# ============================================================================

class TestGuardianDaemonIntegration:
    """Integration tests for GuardianDaemon"""

    @pytest.mark.asyncio
    async def test_full_task_cycle(self, guardian_daemon):
        """Test complete task cycle"""
        # Start daemon
        await guardian_daemon.start()
        assert guardian_daemon._running is True

        # Notify task complete
        guardian_daemon.notify_task_complete()

        # Let async tasks complete
        await asyncio.sleep(0.2)

        # Stop daemon
        await guardian_daemon.stop()
        assert guardian_daemon._running is False

    @pytest.mark.asyncio
    async def test_error_accumulation_triggers_review(self, guardian_daemon):
        """Test error accumulation triggers error review"""
        await guardian_daemon.start()

        # Simulate multiple errors
        guardian_daemon.notify_error()

        # Let async tasks complete
        await asyncio.sleep(0.2)

        await guardian_daemon.stop()
