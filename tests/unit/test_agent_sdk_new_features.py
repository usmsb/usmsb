"""
Agent SDK 新增功能 - 单元测试

专注于可测试的核心功能 - 数据类和基础模块
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== Gene Capsule Tests ====================

class TestGeneCapsuleImports:
    """Tests for Gene Capsule imports"""

    def test_gene_capsule_module_import(self):
        """Test that gene capsule module can be imported"""
        try:
            from usmsb_sdk.agent_sdk import gene_capsule
            assert gene_capsule is not None
        except ImportError as e:
            pytest.skip(f"Gene capsule module not available: {e}")

    def test_gene_capsule_manager_import(self):
        """Test that GeneCapsuleManager can be imported"""
        try:
            from usmsb_sdk.agent_sdk.gene_capsule import GeneCapsuleManager
            assert GeneCapsuleManager is not None
        except ImportError as e:
            pytest.skip(f"GeneCapsuleManager not available: {e}")


# ==================== Enhanced Discovery Tests ====================

class TestDiscoveryImports:
    """Tests for Discovery module imports"""

    def test_discovery_module_import(self):
        """Test that discovery module can be imported"""
        try:
            from usmsb_sdk.agent_sdk import discovery
            assert discovery is not None
        except ImportError as e:
            pytest.skip(f"Discovery module not available: {e}")

    def test_enhanced_discovery_manager_import(self):
        """Test that EnhancedDiscoveryManager can be imported"""
        try:
            from usmsb_sdk.agent_sdk.discovery import EnhancedDiscoveryManager
            assert EnhancedDiscoveryManager is not None
        except ImportError as e:
            pytest.skip(f"EnhancedDiscoveryManager not available: {e}")


# ==================== Platform Client Tests ====================

class TestPlatformClientImports:
    """Tests for PlatformClient imports"""

    def test_platform_client_import(self):
        """Test that PlatformClient can be imported"""
        try:
            from usmsb_sdk.agent_sdk.platform_client import PlatformClient
            assert PlatformClient is not None
        except ImportError as e:
            pytest.skip(f"PlatformClient not available: {e}")


# ==================== Pre-Match Negotiation Data Classes Tests ====================

class TestPreMatchNegotiationDataClasses:
    """Tests for Pre-Match Negotiation data classes"""

    def test_clarification_qa_creation(self):
        """Test creating ClarificationQA"""
        from usmsb_sdk.services.pre_match_negotiation import ClarificationQA

        qa = ClarificationQA(
            question_id="qa_001",
            question="你的数据处理能力如何？",
            asker_id="demand_agent",
        )

        assert qa.question_id == "qa_001"
        assert qa.question == "你的数据处理能力如何？"
        assert qa.answer is None

    def test_verification_request_creation(self):
        """Test creating VerificationRequest"""
        from usmsb_sdk.services.pre_match_negotiation import (
            VerificationRequest,
            VerificationType,
        )

        request = VerificationRequest(
            request_id="ver_001",
            capability="数据分析",
            verification_type=VerificationType.PORTFOLIO,
            request_detail="请展示之前的数据分析项目",
        )

        assert request.request_id == "ver_001"
        assert request.capability == "数据分析"
        assert request.verification_type == VerificationType.PORTFOLIO

    def test_verification_type_enum(self):
        """Test VerificationType enum"""
        from usmsb_sdk.services.pre_match_negotiation import VerificationType

        assert VerificationType.PORTFOLIO.value == "portfolio"
        assert VerificationType.TEST_TASK.value == "test_task"
        assert VerificationType.REFERENCE.value == "reference"
        assert VerificationType.GENE_CAPSULE.value == "gene_capsule"

    def test_negotiation_status_enum(self):
        """Test NegotiationStatus enum"""
        from usmsb_sdk.services.pre_match_negotiation import NegotiationStatus

        assert NegotiationStatus.INITIATED.value == "initiated"
        assert NegotiationStatus.IN_PROGRESS.value == "in_progress"
        assert NegotiationStatus.CONFIRMED.value == "confirmed"
        assert NegotiationStatus.DECLINED.value == "declined"


# ==================== Negotiation Notifications Tests ====================

class TestNegotiationNotifications:
    """Tests for Negotiation Notifications"""

    def test_notification_types(self):
        """Test NotificationType enum values"""
        from usmsb_sdk.services.negotiation_notifications import NotificationType

        assert NotificationType.QUESTION_ASKED.value == "question_asked"
        assert NotificationType.VERIFICATION_REQUESTED.value == "verification_requested"
        assert NotificationType.TERMS_PROPOSED.value == "terms_proposed"
        assert NotificationType.MATCH_CONFIRMED.value == "match_confirmed"

    def test_notification_manager_creation(self):
        """Test creating NegotiationNotificationManager"""
        from usmsb_sdk.services.negotiation_notifications import (
            NegotiationNotificationManager,
        )

        manager = NegotiationNotificationManager()
        assert manager is not None

    def test_notification_data_class(self):
        """Test Notification data class"""
        from usmsb_sdk.services.negotiation_notifications import (
            NegotiationNotification,
            NotificationType,
        )
        from datetime import datetime

        notification = NegotiationNotification(
            notification_id="notif_001",
            notification_type=NotificationType.QUESTION_ASKED,
            negotiation_id="neg_001",
            recipient_id="user_001",
            data={"question": "test"},
            created_at=datetime.now(),
        )

        assert notification.notification_id == "notif_001"
        assert notification.notification_type == NotificationType.QUESTION_ASKED


# ==================== Gene Capsule Service Data Classes Tests ====================

class TestGeneCapsuleServiceDataClasses:
    """Tests for Gene Capsule Service data classes"""

    def test_experience_create_schema(self):
        """Test ExperienceCreate schema"""
        try:
            from usmsb_sdk.api.rest.schemas.gene_capsule import ExperienceCreate

            exp = ExperienceCreate(
                task_type="数据分析",
                task_description="测试任务",
                outcome="success",
                quality_score=0.9,
            )

            assert exp.task_type == "数据分析"
            assert exp.outcome == "success"
        except ImportError:
            pytest.skip("Gene capsule schema not available")

    def test_capsule_response_schema(self):
        """Test CapsuleResponse schema"""
        try:
            from usmsb_sdk.api.rest.schemas.gene_capsule import CapsuleResponse

            capsule = CapsuleResponse(
                capsule_id="cap_001",
                agent_id="agent_001",
                total_experiences=5,
                success_rate=0.85,
            )

            assert capsule.capsule_id == "cap_001"
            assert capsule.total_experiences == 5
        except ImportError:
            pytest.skip("Gene capsule schema not available")


# ==================== Enhanced Discovery Data Classes Tests ====================

class TestEnhancedDiscoveryDataClasses:
    """Tests for Enhanced Discovery data classes"""

    def test_discovery_filter_creation(self):
        """Test creating DiscoveryFilter"""
        from usmsb_sdk.agent_sdk.discovery import DiscoveryFilter

        filter = DiscoveryFilter(
            capabilities=["数据分析"],
            min_rating=4.0,
        )

        assert "数据分析" in filter.capabilities
        assert filter.min_rating == 4.0

    def test_agent_info_creation(self):
        """Test creating AgentInfo"""
        from usmsb_sdk.agent_sdk.discovery import AgentInfo

        agent = AgentInfo(
            agent_id="agent_001",
            name="Test Agent",
            description="Test description",
            capabilities=["数据分析"],
        )

        assert agent.agent_id == "agent_001"
        assert "数据分析" in agent.capabilities

    def test_search_criteria_creation(self):
        """Test creating SearchCriteria"""
        from usmsb_sdk.agent_sdk.discovery import SearchCriteria

        criteria = SearchCriteria(
            task_description="数据分析",
        )

        assert criteria.task_description == "数据分析"

    def test_match_dimension_enum(self):
        """Test MatchDimension enum"""
        from usmsb_sdk.agent_sdk.discovery import MatchDimension

        assert MatchDimension.CAPABILITY.value == "capability"
        assert MatchDimension.PRICE.value == "price"
        assert MatchDimension.REPUTATION.value == "reputation"
        assert MatchDimension.AVAILABILITY.value == "availability"
        assert MatchDimension.EXPERIENCE.value == "experience"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
