"""
Unit tests for error_learning.py - ErrorDrivenLearning class

Tests the error-driven learning system that learns from errors.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.error_learning import (
    ErrorDrivenLearning,
    ErrorType,
    SolutionType,
    ErrorRecord,
    Solution,
    AgentWithSelfHealing,
)


class MockLLMManager:
    """Mock LLM manager for testing"""

    async def chat(self, prompt: str) -> str:
        """Return mock LLM response"""
        if "解决方案" in prompt or "solution" in prompt.lower():
            return '''{
                "solution_type": "retry",
                "solution_data": {"wait_seconds": 1},
                "reasoning": "Test reasoning",
                "prevent_future": "Prevention"
            }'''
        return '{"summary": "test"}'


class MockExperienceDB:
    """Mock experience database"""

    def __init__(self):
        self.experiences = []

    async def search_solutions(self, error_type: str = None, tool_name: str = None):
        return []

    async def add(self, experience: dict):
        self.experiences.append(experience)


@pytest.fixture
def mock_llm():
    """Fixture providing mock LLM manager"""
    return MockLLMManager()


@pytest.fixture
def mock_experience_db():
    """Fixture providing mock experience database"""
    return MockExperienceDB()


@pytest.fixture
def error_driven_learning(mock_llm, mock_experience_db):
    """Fixture providing ErrorDrivenLearning instance"""
    return ErrorDrivenLearning(
        llm_manager=mock_llm,
        experience_db=mock_experience_db
    )


# ============================================================================
# Tests for ErrorType enum
# ============================================================================

class TestErrorType:
    """Tests for ErrorType enum"""

    def test_all_error_types_defined(self):
        """Test all error types are defined"""
        expected_types = [
            "json_format",
            "parameter_error",
            "context_overflow",
            "permission_error",
            "network_error",
            "timeout_error",
            "tool_not_found",
            "execution_error",
            "unknown_error"
        ]

        for error_type in expected_types:
            assert ErrorType(error_type) is not None

    def test_error_type_values(self):
        """Test error type values"""
        assert ErrorType.JSON_FORMAT.value == "json_format"
        assert ErrorType.PARAMETER_ERROR.value == "parameter_error"
        assert ErrorType.CONTEXT_OVERFLOW.value == "context_overflow"


# ============================================================================
# Tests for SolutionType enum
# ============================================================================

class TestSolutionType:
    """Tests for SolutionType enum"""

    def test_all_solution_types_defined(self):
        """Test all solution types are defined"""
        expected_types = ["retry", "fix_params", "use_alternative", "skip", "escalate"]

        for sol_type in expected_types:
            assert SolutionType(sol_type) is not None

    def test_solution_type_values(self):
        """Test solution type values"""
        assert SolutionType.RETRY.value == "retry"
        assert SolutionType.FIX_PARAMS.value == "fix_params"
        assert SolutionType.USE_ALTERNATIVE.value == "use_alternative"


# ============================================================================
# Tests for ErrorRecord dataclass
# ============================================================================

class TestErrorRecord:
    """Tests for ErrorRecord dataclass"""

    def test_error_record_creation(self):
        """Test creating ErrorRecord"""
        record = ErrorRecord(
            error_type=ErrorType.JSON_FORMAT,
            error_message="Test error",
            context={"test": True}
        )

        assert record.error_type == ErrorType.JSON_FORMAT
        assert record.error_message == "Test error"
        assert record.occurrence_count == 1
        assert record.context == {"test": True}

    def test_error_record_defaults(self):
        """Test ErrorRecord default values"""
        record = ErrorRecord()

        assert record.id is not None
        assert record.error_type == ErrorType.UNKNOWN_ERROR
        assert record.error_message == ""
        assert record.occurrence_count == 1


# ============================================================================
# Tests for Solution dataclass
# ============================================================================

class TestSolution:
    """Tests for Solution dataclass"""

    def test_solution_creation(self):
        """Test creating Solution"""
        solution = Solution(
            solution_type=SolutionType.RETRY,
            solution_data={"wait_seconds": 1},
            reasoning="Test reasoning"
        )

        assert solution.solution_type == SolutionType.RETRY
        assert solution.solution_data == {"wait_seconds": 1}
        assert solution.success_rate == 0.0
        assert solution.times_used == 0

    def test_solution_defaults(self):
        """Test Solution default values"""
        solution = Solution()

        assert solution.id is not None
        assert solution.solution_type == SolutionType.RETRY
        assert solution.success_rate == 0.0


# ============================================================================
# Tests for ErrorDrivenLearning initialization
# ============================================================================

class TestErrorDrivenLearningInit:
    """Tests for ErrorDrivenLearning initialization"""

    def test_init_with_llm_only(self, mock_llm):
        """Test initialization with LLM only"""
        learning = ErrorDrivenLearning(llm_manager=mock_llm)

        assert learning.llm == mock_llm
        assert learning.experience_db is None

    def test_init_with_experience_db(self, mock_llm, mock_experience_db):
        """Test initialization with experience DB"""
        learning = ErrorDrivenLearning(
            llm_manager=mock_llm,
            experience_db=mock_experience_db
        )

        assert learning.llm == mock_llm
        assert learning.experience_db == mock_experience_db

    def test_default_config(self, mock_llm):
        """Test default configuration"""
        learning = ErrorDrivenLearning(llm_manager=mock_llm)

        assert learning.max_retries == 5
        assert learning.solution_confidence_threshold == 0.5

    def test_error_classifiers_count(self, mock_llm):
        """Test error classifiers are set up"""
        learning = ErrorDrivenLearning(llm_manager=mock_llm)

        assert len(learning.error_classifiers) == 8


# ============================================================================
# Tests for error classification
# ============================================================================

class TestErrorClassification:
    """Tests for error classification"""

    def test_classify_json_error(self, error_driven_learning):
        """Test JSON error classification"""
        error = ValueError("Invalid JSON format")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.JSON_FORMAT

    def test_classify_parameter_error(self, error_driven_learning):
        """Test parameter error classification"""
        error = TypeError("Missing required parameter")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.PARAMETER_ERROR

    def test_classify_context_overflow(self, error_driven_learning):
        """Test context overflow classification"""
        error = ValueError("Context length exceeded maximum tokens")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.CONTEXT_OVERFLOW

    def test_classify_permission_error(self, error_driven_learning):
        """Test permission error classification"""
        error = PermissionError("Access denied")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.PERMISSION_ERROR

    def test_classify_network_error(self, error_driven_learning):
        """Test network error classification"""
        error = ConnectionError("Connection refused")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.NETWORK_ERROR

    def test_classify_timeout_error(self, error_driven_learning):
        """Test timeout error classification"""
        error = TimeoutError("Request timeout")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.TIMEOUT_ERROR

    def test_classify_tool_not_found(self, error_driven_learning):
        """Test tool not found classification"""
        error = ValueError("Tool not found")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        assert result == ErrorType.TOOL_NOT_FOUND

    def test_classify_unknown_error(self, error_driven_learning):
        """Test unknown error classification"""
        # Use an error message that doesn't match any classifier
        error = RuntimeError("Completely unexpected situation occurred")
        context = {}

        result = error_driven_learning._classify_error(error, context)

        # Should match EXECUTION_ERROR since it contains "error"
        # or UNKNOWN_ERROR if none match
        assert result in [ErrorType.UNKNOWN_ERROR, ErrorType.EXECUTION_ERROR]


# ============================================================================
# Tests for error classifiers
# ============================================================================

class TestErrorClassifiers:
    """Tests for individual error classifiers"""

    def test_is_json_error(self, error_driven_learning):
        """Test JSON error detection"""
        assert error_driven_learning._is_json_error("Invalid JSON", {})
        assert error_driven_learning._is_json_error("JSONDecodeError", {})
        assert error_driven_learning._is_json_error("expecting value", {})

    def test_is_parameter_error(self, error_driven_learning):
        """Test parameter error detection"""
        assert error_driven_learning._is_parameter_error("Missing parameter", {})
        assert error_driven_learning._is_parameter_error("TypeError: argument", {})

    def test_is_context_overflow(self, error_driven_learning):
        """Test context overflow detection"""
        assert error_driven_learning._is_context_overflow("context too long", {})
        assert error_driven_learning._is_context_overflow("maximum tokens exceeded", {})

    def test_is_permission_error(self, error_driven_learning):
        """Test permission error detection"""
        assert error_driven_learning._is_permission_error("Permission denied", {})
        assert error_driven_learning._is_permission_error("access denied", {})

    def test_is_network_error(self, error_driven_learning):
        """Test network error detection"""
        assert error_driven_learning._is_network_error("Connection refused", {})
        assert error_driven_learning._is_network_error("DNS failure", {})

    def test_is_timeout_error(self, error_driven_learning):
        """Test timeout error detection"""
        assert error_driven_learning._is_timeout_error("timeout", {})

    def test_is_tool_not_found(self, error_driven_learning):
        """Test tool not found detection"""
        assert error_driven_learning._is_tool_not_found("Tool not found", {})
        assert error_driven_learning._is_tool_not_found("does not exist", {})


# ============================================================================
# Tests for _get_error_key
# ============================================================================

class TestGetErrorKey:
    """Tests for _get_error_key method"""

    def test_error_key_generation(self, error_driven_learning):
        """Test error key generation"""
        key = error_driven_learning._get_error_key(
            "This is a test error message",
            {"tool_name": "test_tool"}
        )

        assert "test_tool" in key

    def test_error_key_truncation(self, error_driven_learning):
        """Test error key truncation"""
        long_message = "a" * 100
        key = error_driven_learning._get_error_key(
            long_message,
            {"tool_name": "test_tool"}
        )

        # Key should be truncated
        assert len(key) < 150


# ============================================================================
# Tests for _update_error_record
# ============================================================================

class TestUpdateErrorRecord:
    """Tests for _update_error_record method"""

    @pytest.mark.asyncio
    async def test_create_new_error_record(self, error_driven_learning):
        """Test creating new error record"""
        record = await error_driven_learning._update_error_record(
            "test_key",
            ErrorType.JSON_FORMAT,
            "Test error",
            {"tool_name": "test"}
        )

        assert record.error_type == ErrorType.JSON_FORMAT
        assert record.occurrence_count == 1

    @pytest.mark.asyncio
    async def test_update_existing_error_record(self, error_driven_learning):
        """Test updating existing error record"""
        # Create initial record
        await error_driven_learning._update_error_record(
            "test_key",
            ErrorType.JSON_FORMAT,
            "Test error",
            {"tool_name": "test"}
        )

        # Update same key
        record = await error_driven_learning._update_error_record(
            "test_key",
            ErrorType.JSON_FORMAT,
            "Updated error",
            {"tool_name": "test"}
        )

        assert record.occurrence_count == 2


# ============================================================================
# Tests for _check_known_solution
# ============================================================================

class TestCheckKnownSolution:
    """Tests for _check_known_solution method"""

    @pytest.mark.asyncio
    async def test_check_known_solution_from_cache(self, error_driven_learning):
        """Test checking known solution from cache"""
        # Add solution to cache with the correct key format
        error_key = error_driven_learning._get_error_key("test error", {"tool_name": "test"})
        solution = Solution(solution_type=SolutionType.RETRY)
        error_driven_learning._solutions_cache[error_key] = solution

        result = await error_driven_learning._check_known_solution(
            ErrorType.JSON_FORMAT,
            "test error",
            {"tool_name": "test"}
        )

        assert result == solution

    @pytest.mark.asyncio
    async def test_check_known_solution_empty_cache(self, error_driven_learning):
        """Test checking when cache is empty"""
        result = await error_driven_learning._check_known_solution(
            ErrorType.JSON_FORMAT,
            "test error",
            {"tool_name": "test"}
        )

        assert result is None


# ============================================================================
# Tests for _apply_solution
# ============================================================================

class TestApplySolution:
    """Tests for _apply_solution method"""

    @pytest.mark.asyncio
    async def test_apply_retry_solution(self, error_driven_learning):
        """Test applying retry solution"""
        solution = Solution(
            solution_type=SolutionType.RETRY,
            solution_data={"wait_seconds": 0}
        )

        result = await error_driven_learning._apply_solution(solution, {})

        assert result["action"] == "retry"
        assert solution.times_used == 1

    @pytest.mark.asyncio
    async def test_apply_fix_params_solution(self, error_driven_learning):
        """Test applying fix params solution"""
        solution = Solution(
            solution_type=SolutionType.FIX_PARAMS,
            solution_data={"fixed_params": {"param1": "value1"}}
        )

        context = {"params": {"original": "value"}}
        result = await error_driven_learning._apply_solution(solution, context)

        assert result["action"] == "retry_with_fixed_params"
        assert "param1" in result["context"]["params"]

    @pytest.mark.asyncio
    async def test_apply_use_alternative_solution(self, error_driven_learning):
        """Test applying use alternative solution"""
        solution = Solution(
            solution_type=SolutionType.USE_ALTERNATIVE,
            solution_data={"alternative_tool": "alt_tool", "params": {"key": "value"}}
        )

        result = await error_driven_learning._apply_solution(solution, {})

        assert result["action"] == "use_alternative"
        assert result["tool"] == "alt_tool"

    @pytest.mark.asyncio
    async def test_apply_skip_solution(self, error_driven_learning):
        """Test applying skip solution"""
        solution = Solution(
            solution_type=SolutionType.SKIP,
            solution_data={"reason": "Skipped"}
        )

        result = await error_driven_learning._apply_solution(solution, {})

        assert result["action"] == "skip"
        assert result["reason"] == "Skipped"


# ============================================================================
# Tests for _record_solution_result
# ============================================================================

class TestRecordSolutionResult:
    """Tests for _record_solution_result method"""

    @pytest.mark.asyncio
    async def test_record_success(self, error_driven_learning):
        """Test recording successful solution"""
        solution = Solution()
        solution.times_used = 1  # Must be set for success_rate calculation

        await error_driven_learning._record_solution_result(solution, True)

        assert solution.times_succeeded == 1
        assert solution.success_rate == 1.0

    @pytest.mark.asyncio
    async def test_record_failure(self, error_driven_learning):
        """Test recording failed solution"""
        solution = Solution()
        solution.times_used = 1

        await error_driven_learning._record_solution_result(solution, False)

        assert solution.times_succeeded == 0
        assert solution.success_rate == 0.0


# ============================================================================
# Tests for _record_experience
# ============================================================================

class TestRecordExperience:
    """Tests for _record_experience method"""

    @pytest.mark.asyncio
    async def test_record_experience_no_db(self, error_driven_learning):
        """Test recording without experience DB"""
        # Create instance without experience DB
        learning = ErrorDrivenLearning(llm_manager=error_driven_learning.llm)

        solution = Solution(solution_type=SolutionType.RETRY)

        # Should not raise
        await learning._record_experience(
            ErrorType.JSON_FORMAT,
            "test error",
            solution,
            {}
        )

    @pytest.mark.asyncio
    async def test_record_experience_with_db(self, error_driven_learning, mock_experience_db):
        """Test recording with experience DB"""
        solution = Solution(
            solution_type=SolutionType.RETRY,
            reasoning="Test reasoning",
            prevent_future="Prevention"
        )

        await error_driven_learning._record_experience(
            ErrorType.JSON_FORMAT,
            "test error",
            solution,
            {"tool_name": "test_tool"}
        )

        # Check experience was added
        assert len(mock_experience_db.experiences) == 1
        exp = mock_experience_db.experiences[0]
        assert exp["type"] == "error_solution"
        assert exp["error_type"] == "json_format"


# ============================================================================
# Tests for handle_error
# ============================================================================

class TestHandleError:
    """Tests for handle_error method"""

    @pytest.mark.asyncio
    async def test_handle_error_with_known_solution(self, error_driven_learning):
        """Test handling error with known solution"""
        # Pre-populate cache
        solution = Solution(solution_type=SolutionType.RETRY)
        error_driven_learning._solutions_cache["test_tool_test"] = solution

        error = ValueError("Test error")
        context = {"tool_name": "test_tool"}

        result = await error_driven_learning.handle_error(error, context)

        assert result is not None
        assert "action" in result

    @pytest.mark.asyncio
    async def test_handle_error_without_solution(self, error_driven_learning):
        """Test handling error without solution"""
        error = ValueError("Test error")
        context = {"tool_name": "test_tool"}

        result = await error_driven_learning.handle_error(error, context)

        assert result is not None


# ============================================================================
# Tests for AgentWithSelfHealing
# ============================================================================

class TestAgentWithSelfHealing:
    """Tests for AgentWithSelfHealing class"""

    def test_init(self, mock_llm):
        """Test initialization"""
        agent = AgentWithSelfHealing(llm_manager=mock_llm)

        assert agent.llm == mock_llm
        assert agent.error_learning is not None

    @pytest.mark.asyncio
    async def test_execute_with_self_healing_success(self, mock_llm):
        """Test successful execution with self-healing"""
        agent = AgentWithSelfHealing(llm_manager=mock_llm)

        async def executor(tool_name, params):
            return "success"

        result = await agent.execute_with_self_healing(
            executor,
            "test_tool",
            {}
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_self_healing_retry(self, mock_llm):
        """Test execution with retry on failure"""
        agent = AgentWithSelfHealing(llm_manager=mock_llm)

        attempt_count = 0

        async def executor(tool_name, params):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Test error")
            return "success"

        result = await agent.execute_with_self_healing(
            executor,
            "test_tool",
            {}
        )

        assert result == "success"
        assert attempt_count == 2


# ============================================================================
# Integration tests for the full flow
# ============================================================================

class TestErrorLearningIntegration:
    """Integration tests for error learning"""

    @pytest.mark.asyncio
    async def test_full_error_handling_flow(self, error_driven_learning, mock_experience_db):
        """Test complete error handling flow"""
        # Create a new error
        error = ValueError("JSON decode error")
        context = {"tool_name": "parser", "params": {"data": "{}"}}

        # Handle the error
        result = await error_driven_learning.handle_error(error, context)

        # Verify result structure
        assert isinstance(result, dict)
        assert "action" in result

    @pytest.mark.asyncio
    async def test_error_tracking(self, error_driven_learning):
        """Test error is tracked correctly"""
        error = ValueError("Test error")
        context = {"tool_name": "test_tool"}

        await error_driven_learning.handle_error(error, context)

        # Check error was recorded
        assert len(error_driven_learning._error_cache) > 0
