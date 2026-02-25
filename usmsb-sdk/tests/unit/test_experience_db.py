"""
Unit tests for experience_db.py - ExperienceDB class

Tests the experience database for storing error solutions and successful experiences.
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sqlite3
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usmsb_sdk.platform.external.meta_agent.memory.experience_db import ExperienceDB


@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture providing temporary database path"""
    db_path = tmp_path / "test_experience.db"
    yield str(db_path)
    # Cleanup
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except:
            pass


@pytest.fixture
def experience_db(temp_db_path):
    """Fixture providing ExperienceDB instance"""
    return ExperienceDB(db_path=temp_db_path)


# ============================================================================
# Tests for ExperienceDB initialization
# ============================================================================

class TestExperienceDBInit:
    """Tests for ExperienceDB initialization"""

    def test_init_with_path(self, temp_db_path):
        """Test initialization with path"""
        db = ExperienceDB(db_path=temp_db_path)

        assert db.db_path == temp_db_path
        assert db._initialized is False

    def test_init_default_path(self):
        """Test initialization with default path"""
        db = ExperienceDB()

        assert db.db_path == "experience.db"


# ============================================================================
# Tests for init and _init_db
# ============================================================================

class TestInitDB:
    """Tests for database initialization"""

    @pytest.mark.asyncio
    async def test_init(self, experience_db):
        """Test initialization"""
        await experience_db.init()

        assert experience_db._initialized is True

    @pytest.mark.asyncio
    async def test_init_twice(self, experience_db):
        """Test initialization twice (idempotent)"""
        await experience_db.init()
        await experience_db.init()

        assert experience_db._initialized is True

    def test_init_db_creates_tables(self, temp_db_path):
        """Test that _init_db creates tables"""
        db = ExperienceDB(db_path=temp_db_path)
        db._init_db()

        # Verify tables exist
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "error_solutions" in tables
        assert "success_experiences" in tables
        assert "failure_lessons" in tables

        conn.close()

    def test_init_db_creates_indexes(self, temp_db_path):
        """Test that _init_db creates indexes"""
        db = ExperienceDB(db_path=temp_db_path)
        db._init_db()

        # Verify indexes exist
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        assert any("error_solutions" in idx for idx in indexes)

        conn.close()


# ============================================================================
# Tests for add method
# ============================================================================

class TestAdd:
    """Tests for add method"""

    @pytest.mark.asyncio
    async def test_add_error_solution(self, experience_db):
        """Test adding error solution"""
        experience = {
            "type": "error_solution",
            "error_type": "json_format",
            "error_message": "Invalid JSON",
            "solution_type": "retry",
            "solution_data": {"wait_seconds": 1},
            "reasoning": "Test reasoning",
            "prevent_future": "Prevention",
            "tool_name": "parser"
        }

        await experience_db.add(experience)

    @pytest.mark.asyncio
    async def test_add_success_experience(self, experience_db):
        """Test adding success experience"""
        experience = {
            "type": "success_experience",
            "experience_type": "pattern",
            "content": "Use retry for transient errors",
            "context": {"tool": "test"}
        }

        await experience_db.add(experience)

    @pytest.mark.asyncio
    async def test_add_failure_lesson(self, experience_db):
        """Test adding failure lesson"""
        experience = {
            "type": "failure_lesson",
            "lesson_type": "timeout",
            "content": "Don't use long timeouts",
            "context": {"timeout": 300}
        }

        await experience_db.add(experience)

    @pytest.mark.asyncio
    async def test_add_default_type(self, experience_db):
        """Test adding with default type"""
        experience = {
            "error_type": "json_format",
            "solution_type": "retry"
        }

        await experience_db.add(experience)


# ============================================================================
# Tests for search_solutions
# ============================================================================

class TestSearchSolutions:
    """Tests for search_solutions method"""

    @pytest.mark.asyncio
    async def test_search_solutions_empty(self, experience_db):
        """Test searching with no results"""
        await experience_db.init()

        results = await experience_db.search_solutions(error_type="json_format")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_solutions_with_results(self, experience_db):
        """Test searching with results"""
        # Add an experience first
        experience = {
            "type": "error_solution",
            "error_type": "json_format",
            "error_message": "Invalid JSON",
            "solution_type": "retry",
            "tool_name": "parser"
        }
        await experience_db.add(experience)

        # Search
        results = await experience_db.search_solutions(error_type="json_format")

        assert len(results) > 0
        assert results[0]["error_type"] == "json_format"

    @pytest.mark.asyncio
    async def test_search_solutions_by_tool(self, experience_db):
        """Test searching by tool name"""
        # Add experiences
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "solution_type": "retry",
            "tool_name": "parser"
        })

        results = await experience_db.search_solutions(tool_name="parser")

        assert len(results) > 0
        assert results[0]["tool_name"] == "parser"

    @pytest.mark.asyncio
    async def test_search_solutions_by_both(self, experience_db):
        """Test searching by both error_type and tool_name"""
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "solution_type": "retry",
            "tool_name": "parser"
        })

        results = await experience_db.search_solutions(
            error_type="json_format",
            tool_name="parser"
        )

        assert len(results) > 0


# ============================================================================
# Tests for get_all_experiences
# ============================================================================

class TestGetAllExperiences:
    """Tests for get_all_experiences method"""

    @pytest.mark.asyncio
    async def test_get_all_experiences_empty(self, experience_db):
        """Test getting all experiences when empty"""
        await experience_db.init()

        result = await experience_db.get_all_experiences()

        assert "error_solutions" in result
        assert "success_experiences" in result
        assert "failure_lessons" in result

    @pytest.mark.asyncio
    async def test_get_all_experiences_with_data(self, experience_db):
        """Test getting all experiences with data"""
        # Add experiences
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "solution_type": "retry"
        })

        await experience_db.add({
            "type": "success_experience",
            "experience_type": "pattern",
            "content": "Test pattern"
        })

        await experience_db.add({
            "type": "failure_lesson",
            "lesson_type": "timeout",
            "content": "Test lesson"
        })

        result = await experience_db.get_all_experiences()

        assert len(result["error_solutions"]) > 0
        assert len(result["success_experiences"]) > 0
        assert len(result["failure_lessons"]) > 0


# ============================================================================
# Tests for data integrity
# ============================================================================

class TestDataIntegrity:
    """Tests for data integrity"""

    @pytest.mark.asyncio
    async def test_solution_data_persisted(self, experience_db):
        """Test that solution data is properly stored and retrieved"""
        solution_data = {"wait_seconds": 5, "max_retries": 3}

        await experience_db.add({
            "type": "error_solution",
            "error_type": "network_error",
            "solution_type": "retry",
            "solution_data": solution_data
        })

        results = await experience_db.search_solutions(error_type="network_error")

        assert len(results) > 0
        # solution_data is stored as JSON string
        assert results[0]["solution_data"] == solution_data

    @pytest.mark.asyncio
    async def test_context_persisted(self, experience_db):
        """Test that context is properly stored and retrieved"""
        context = {"param1": "value1", "param2": 123}

        await experience_db.add({
            "type": "success_experience",
            "experience_type": "test",
            "content": "Test content",
            "context": context
        })

        result = await experience_db.get_all_experiences()

        assert len(result["success_experiences"]) > 0


# ============================================================================
# Tests for error handling
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""

    def test_init_db_creates_directory(self, tmp_path):
        """Test that init creates directory if needed"""
        subdir = tmp_path / "subdir"
        db_path = subdir / "test.db"

        db = ExperienceDB(db_path=str(db_path))
        db._init_db()

        assert os.path.exists(db_path)


# ============================================================================
# Tests for async behavior
# ============================================================================

class TestAsyncBehavior:
    """Tests for async behavior"""

    @pytest.mark.asyncio
    async def test_concurrent_add(self, experience_db):
        """Test concurrent add operations"""
        experiences = [
            {"type": "error_solution", "error_type": f"type_{i}", "solution_type": "retry"}
            for i in range(10)
        ]

        await asyncio.gather(*[experience_db.add(exp) for exp in experiences])

        results = await experience_db.get_all_experiences()
        assert len(results["error_solutions"]) == 10


# ============================================================================
# Integration tests
# ============================================================================

class TestExperienceDBIntegration:
    """Integration tests for ExperienceDB"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, experience_db):
        """Test complete workflow"""
        # Add error solution
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "error_message": "Invalid JSON",
            "solution_type": "retry",
            "solution_data": {"wait_seconds": 1},
            "reasoning": "Simple retry works",
            "prevent_future": "Validate JSON before sending",
            "tool_name": "parser"
        })

        # Search for solution
        solutions = await experience_db.search_solutions(error_type="json_format")
        assert len(solutions) > 0

        # Add success experience
        await experience_db.add({
            "type": "success_experience",
            "experience_type": "best_practice",
            "content": "Always validate input before processing"
        })

        # Get all experiences
        all_exp = await experience_db.get_all_experiences()
        assert len(all_exp["error_solutions"]) == 1
        assert len(all_exp["success_experiences"]) == 1

    @pytest.mark.asyncio
    async def test_multiple_searches(self, experience_db):
        """Test multiple searches return correct results"""
        # Add different types
        await experience_db.add({
            "type": "error_solution",
            "error_type": "json_format",
            "solution_type": "retry",
            "tool_name": "parser"
        })

        await experience_db.add({
            "type": "error_solution",
            "error_type": "network_error",
            "solution_type": "retry",
            "tool_name": "http_client"
        })

        # Search by type
        json_sols = await experience_db.search_solutions(error_type="json_format")
        assert len(json_sols) == 1

        network_sols = await experience_db.search_solutions(error_type="network_error")
        assert len(network_sols) == 1
