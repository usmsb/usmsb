"""
Unit Tests for Pre-Match Negotiation Service

Tests for:
- Negotiation session management
- Clarification Q&A
- Capability verification
- Scope confirmation
- Terms proposal and agreement
- Match confirmation/decline
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

from usmsb_sdk.services.pre_match_negotiation import (
    PreMatchNegotiationService,
    NegotiationStatus,
    VerificationType,
    ClarificationQA,
    VerificationRequest,
    ScopeConfirmation,
    GeneCapsuleMatch,
)


# ==================== Fixtures ====================

@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.query = MagicMock()
    return session


@pytest.fixture
def mock_gene_capsule_service():
    """Mock gene capsule service"""
    return AsyncMock()


@pytest.fixture
def negotiation_service(mock_db_session, mock_gene_capsule_service):
    """Negotiation service instance"""
    return PreMatchNegotiationService(
        db_session=mock_db_session,
        gene_capsule_service=mock_gene_capsule_service,
    )


@pytest.fixture
def sample_negotiation_data():
    """Sample negotiation data"""
    return {
        "demand_agent_id": "demand-001",
        "supply_agent_id": "supply-001",
        "demand_id": "demand-123",
    }


# ==================== Test ClarificationQA ====================

class TestClarificationQA:
    """Tests for ClarificationQA"""

    def test_creation(self):
        """Test QA creation"""
        qa = ClarificationQA(
            question_id="qa-001",
            question="What is your experience with ML?",
            asker_id="demand-001",
        )

        assert qa.question_id == "qa-001"
        assert qa.question == "What is your experience with ML?"
        assert qa.answer is None
        assert qa.asker_id == "demand-001"

    def test_answer(self):
        """Test answering a question"""
        qa = ClarificationQA(
            question_id="qa-001",
            question="What is your experience?",
            asker_id="demand-001",
        )

        qa.answer = "I have 5 years of experience"
        qa.answerer_id = "supply-001"
        qa.answered_at = datetime.now()

        assert qa.answer == "I have 5 years of experience"
        assert qa.answerer_id == "supply-001"

    def test_to_dict(self):
        """Test serialization"""
        qa = ClarificationQA(
            question_id="qa-001",
            question="Test question?",
            asker_id="demand-001",
        )

        data = qa.to_dict()

        assert data["question_id"] == "qa-001"
        assert data["question"] == "Test question?"
        assert data["asker_id"] == "demand-001"


# ==================== Test VerificationRequest ====================

class TestVerificationRequest:
    """Tests for VerificationRequest"""

    def test_creation(self):
        """Test verification request creation"""
        request = VerificationRequest(
            request_id="vr-001",
            capability="machine_learning",
            verification_type=VerificationType.PORTFOLIO,
            request_detail="Please share your ML project portfolio",
        )

        assert request.request_id == "vr-001"
        assert request.capability == "machine_learning"
        assert request.verification_type == VerificationType.PORTFOLIO
        assert request.status == "pending"

    def test_respond(self):
        """Test responding to verification"""
        request = VerificationRequest(
            request_id="vr-001",
            capability="ml",
            verification_type=VerificationType.GENE_CAPSULE,
            request_detail="Show relevant experiences",
        )

        request.response = "Here are my verified experiences..."
        request.response_attachments = ["link1", "link2"]
        request.status = "submitted"

        assert request.status == "submitted"
        assert len(request.response_attachments) == 2

    def test_to_dict(self):
        """Test serialization"""
        request = VerificationRequest(
            request_id="vr-001",
            capability="test",
            verification_type=VerificationType.TEST_TASK,
            request_detail="Complete test task",
        )

        data = request.to_dict()

        assert data["request_id"] == "vr-001"
        assert data["verification_type"] == "test_task"
        assert data["status"] == "pending"


# ==================== Test ScopeConfirmation ====================

class TestScopeConfirmation:
    """Tests for ScopeConfirmation"""

    def test_creation(self):
        """Test scope confirmation creation"""
        scope = ScopeConfirmation(
            deliverables=["Analysis report", "Visualization dashboard"],
            timeline="2 weeks",
            milestones=[
                {"name": "Data collection", "deadline": "Week 1"},
                {"name": "Analysis", "deadline": "Week 2"},
            ],
            exclusions=["Raw data export"],
            assumptions=["Data will be provided by client"],
        )

        assert len(scope.deliverables) == 2
        assert scope.timeline == "2 weeks"
        assert len(scope.milestones) == 2
        assert len(scope.exclusions) == 1
        assert len(scope.assumptions) == 1

    def test_to_dict(self):
        """Test serialization"""
        scope = ScopeConfirmation(
            deliverables=["Report"],
            timeline="1 week",
        )

        data = scope.to_dict()

        assert data["deliverables"] == ["Report"]
        assert data["timeline"] == "1 week"


# ==================== Test GeneCapsuleMatch ====================

class TestGeneCapsuleMatch:
    """Tests for GeneCapsuleMatch"""

    def test_creation(self):
        """Test gene capsule match creation"""
        match = GeneCapsuleMatch(
            matched_experiences=[
                {"task_type": "data_analysis", "relevance": 0.95},
            ],
            relevance_score=0.85,
            verified_count=3,
            total_experience_value=4.5,
        )

        assert len(match.matched_experiences) == 1
        assert match.relevance_score == 0.85
        assert match.verified_count == 3

    def test_to_dict(self):
        """Test serialization"""
        match = GeneCapsuleMatch(
            relevance_score=0.9,
            verified_count=5,
        )

        data = match.to_dict()

        assert data["relevance_score"] == 0.9
        assert data["verified_count"] == 5


# ==================== Test PreMatchNegotiationService ====================

class TestPreMatchNegotiationService:
    """Tests for PreMatchNegotiationService"""

    def test_initialization(self, negotiation_service):
        """Test service initialization"""
        assert negotiation_service.db is not None
        assert negotiation_service._active_negotiations == {}

    @pytest.mark.asyncio
    async def test_initiate_negotiation(self, negotiation_service, sample_negotiation_data, mock_db_session):
        """Test initiating a negotiation"""
        # Mock database query to return None (no existing negotiation)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db_session.query.return_value = mock_query

        result = await negotiation_service.initiate(
            demand_agent_id=sample_negotiation_data["demand_agent_id"],
            supply_agent_id=sample_negotiation_data["supply_agent_id"],
            demand_id=sample_negotiation_data["demand_id"],
        )

        assert "negotiation_id" in result
        assert result["demand_agent_id"] == sample_negotiation_data["demand_agent_id"]
        assert result["supply_agent_id"] == sample_negotiation_data["supply_agent_id"]
        assert result["status"] == NegotiationStatus.INITIATED.value

        # Verify database commit was called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_question(self, negotiation_service):
        """Test asking a clarification question"""
        # Mock negotiation
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.INITIATED.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.clarification_qa = json.dumps([])

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        qa = await negotiation_service.ask_question(
            negotiation_id="neg-001",
            question="What is your availability?",
            asker_id="demand-001",
        )

        assert qa.question == "What is your availability?"
        assert qa.asker_id == "demand-001"
        assert qa.answer is None

    @pytest.mark.asyncio
    async def test_answer_question(self, negotiation_service):
        """Test answering a clarification question"""
        # Create existing Q&A
        existing_qa = ClarificationQA(
            question_id="qa-001",
            question="What is your availability?",
            asker_id="demand-001",
        )

        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.clarification_qa = json.dumps([existing_qa.to_dict()])

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        qa = await negotiation_service.answer_question(
            negotiation_id="neg-001",
            question_id="qa-001",
            answer="I'm available 9am-5pm EST",
            answerer_id="supply-001",
        )

        assert qa.answer == "I'm available 9am-5pm EST"
        assert qa.answerer_id == "supply-001"
        assert qa.answered_at is not None

    @pytest.mark.asyncio
    async def test_request_capability_verification(self, negotiation_service):
        """Test requesting capability verification"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.capability_verification = json.dumps({"requests": []})

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        request = await negotiation_service.request_capability_verification(
            negotiation_id="neg-001",
            capability="machine_learning",
            verification_type=VerificationType.GENE_CAPSULE,
            request_detail="Please share relevant experiences",
        )

        assert request.capability == "machine_learning"
        assert request.verification_type == VerificationType.GENE_CAPSULE
        assert request.status == "pending"

    @pytest.mark.asyncio
    async def test_respond_to_verification(self, negotiation_service):
        """Test responding to verification request"""
        existing_request = VerificationRequest(
            request_id="vr-001",
            capability="ml",
            verification_type=VerificationType.GENE_CAPSULE,
            request_detail="Show experiences",
        )

        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.capability_verification = json.dumps({
            "requests": [existing_request.to_dict()]
        })

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        request = await negotiation_service.respond_to_verification(
            negotiation_id="neg-001",
            request_id="vr-001",
            response="Here are my verified ML experiences...",
            attachments=["https://example.com/portfolio"],
        )

        assert request.response == "Here are my verified ML experiences..."
        assert request.status == "submitted"
        assert "https://example.com/portfolio" in request.response_attachments

    @pytest.mark.asyncio
    async def test_confirm_scope(self, negotiation_service):
        """Test scope confirmation"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.scope_confirmation = json.dumps({})

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        scope = ScopeConfirmation(
            deliverables=["Report", "Dashboard"],
            timeline="2 weeks",
        )

        result = await negotiation_service.confirm_scope(
            negotiation_id="neg-001",
            scope=scope,
        )

        assert result["deliverables"] == ["Report", "Dashboard"]
        assert result["timeline"] == "2 weeks"

    @pytest.mark.asyncio
    async def test_propose_terms(self, negotiation_service):
        """Test proposing terms"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.proposed_terms = None

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        terms = {
            "price": 100,
            "price_type": "hourly",
            "delivery_date": "2024-03-01",
        }

        result = await negotiation_service.propose_terms(
            negotiation_id="neg-001",
            terms=terms,
            proposer_id="supply-001",
        )

        assert result["proposed"] is True

    @pytest.mark.asyncio
    async def test_agree_to_terms(self, negotiation_service):
        """Test agreeing to terms"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.proposed_terms = json.dumps({
            "terms": {"price": 100},
            "proposer_id": "supply-001",
        })

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        result = await negotiation_service.agree_to_terms(negotiation_id="neg-001")

        assert result["agreed"] is True

    @pytest.mark.asyncio
    async def test_confirm_match_first_confirmation(self, negotiation_service):
        """Test first confirmation of match"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.mutual_interest = None

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        result = await negotiation_service.confirm_match(
            negotiation_id="neg-001",
            confirmer_id="demand-001",
        )

        assert result["status"] == "pending_counterpart"
        assert "Waiting for counterpart" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_match_second_confirmation(self, negotiation_service):
        """Test second confirmation of match"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.mutual_interest = True
        mock_negotiation.negotiation_id = "neg-001"
        mock_negotiation.demand_agent_id = "demand-001"
        mock_negotiation.supply_agent_id = "supply-001"

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)
        negotiation_service._negotiation_to_dict = MagicMock(return_value={"negotiation_id": "neg-001"})

        result = await negotiation_service.confirm_match(
            negotiation_id="neg-001",
            confirmer_id="supply-001",
        )

        assert result["status"] == "confirmed"
        assert "confirmed by both parties" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_decline_match(self, negotiation_service):
        """Test declining a match"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        result = await negotiation_service.decline_match(
            negotiation_id="neg-001",
            reason="Budget constraints",
            decliner_id="demand-001",
        )

        assert result["status"] == "declined"
        assert result["reason"] == "Budget constraints"

    @pytest.mark.asyncio
    async def test_cancel_negotiation(self, negotiation_service):
        """Test cancelling a negotiation"""
        mock_negotiation = MagicMock()
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)

        negotiation_service._get_and_validate_negotiation = MagicMock(return_value=mock_negotiation)

        result = await negotiation_service.cancel_negotiation(
            negotiation_id="neg-001",
            reason="Project cancelled",
            canceller_id="demand-001",
        )

        assert result["status"] == "cancelled"
        assert result["reason"] == "Project cancelled"

    @pytest.mark.asyncio
    async def test_check_expired_negotiations(self, negotiation_service, mock_db_session):
        """Test checking for expired negotiations"""
        # Mock query for expired negotiations
        mock_negotiation = MagicMock()
        mock_negotiation.negotiation_id = "neg-expired"

        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = [mock_negotiation]
        mock_db_session.query.return_value = mock_query

        count = await negotiation_service.check_expired_negotiations()

        assert count == 1
        mock_db_session.commit.assert_called()

    def test_negotiation_to_dict(self, negotiation_service):
        """Test negotiation serialization"""
        mock_negotiation = MagicMock()
        mock_negotiation.negotiation_id = "neg-001"
        mock_negotiation.demand_agent_id = "demand-001"
        mock_negotiation.supply_agent_id = "supply-001"
        mock_negotiation.demand_id = "demand-123"
        mock_negotiation.status = NegotiationStatus.IN_PROGRESS.value
        mock_negotiation.clarification_qa = json.dumps([])
        mock_negotiation.scope_confirmation = json.dumps({})
        mock_negotiation.capability_verification = json.dumps({"requests": []})
        mock_negotiation.gene_capsule_match = json.dumps({})
        mock_negotiation.mutual_interest = None
        mock_negotiation.proposed_terms = None
        mock_negotiation.agreed_terms = None
        mock_negotiation.initiated_at = datetime.utcnow()
        mock_negotiation.last_updated = datetime.utcnow()
        mock_negotiation.expires_at = datetime.utcnow() + timedelta(hours=24)
        mock_negotiation.outcome_reason = None

        result = negotiation_service._negotiation_to_dict(mock_negotiation)

        assert result["negotiation_id"] == "neg-001"
        assert result["demand_agent_id"] == "demand-001"
        assert result["supply_agent_id"] == "supply-001"
        assert result["status"] == NegotiationStatus.IN_PROGRESS.value


# ==================== Test Enums ====================

class TestEnums:
    """Tests for enum types"""

    def test_negotiation_status_values(self):
        """Test negotiation status enum values"""
        assert NegotiationStatus.INITIATED.value == "initiated"
        assert NegotiationStatus.IN_PROGRESS.value == "in_progress"
        assert NegotiationStatus.CONFIRMED.value == "confirmed"
        assert NegotiationStatus.DECLINED.value == "declined"
        assert NegotiationStatus.EXPIRED.value == "expired"
        assert NegotiationStatus.CANCELLED.value == "cancelled"

    def test_verification_type_values(self):
        """Test verification type enum values"""
        assert VerificationType.PORTFOLIO.value == "portfolio"
        assert VerificationType.TEST_TASK.value == "test_task"
        assert VerificationType.REFERENCE.value == "reference"
        assert VerificationType.GENE_CAPSULE.value == "gene_capsule"
        assert VerificationType.CERTIFICATE.value == "certificate"


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
