"""
USMSB SDK REST API Schemas

Pydantic models for request/response validation.
"""

from usmsb_sdk.api.rest.schemas.agent import (
    A2ARegistrationRequest,
    AgentCreate,
    AgentRegistrationRequest,
    AgentResponse,
    AgentTestRequest,
    AgentUpdate,
    MCPRegistrationRequest,
    SkillMDRegistrationRequest,
)
from usmsb_sdk.api.rest.schemas.collaboration import (
    CollaborationCreateRequest,
    CollaborationResponse,
    CollaborationRoleAssignRequest,
)
from usmsb_sdk.api.rest.schemas.demand import (
    DemandCreate,
    DemandResponse,
    SearchDemandsRequest,
    SearchSuppliersRequest,
)
from usmsb_sdk.api.rest.schemas.environment import (
    EnvironmentCreate,
    EnvironmentResponse,
    GoalCreate,
)
from usmsb_sdk.api.rest.schemas.matching import (
    MatchRequest,
    MatchResponse,
    NegotiationRequest,
    NetworkExploreRequest,
    ProposalRequest,
    RecommendationRequest,
)
from usmsb_sdk.api.rest.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
)
from usmsb_sdk.api.rest.schemas.system import (
    HealthResponse,
)
from usmsb_sdk.api.rest.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
)

__all__ = [
    # Agent schemas
    "AgentCreate",
    "AgentResponse",
    "AgentUpdate",
    "AgentRegistrationRequest",
    "MCPRegistrationRequest",
    "A2ARegistrationRequest",
    "SkillMDRegistrationRequest",
    "AgentTestRequest",
    # Demand schemas
    "DemandCreate",
    "DemandResponse",
    "SearchDemandsRequest",
    "SearchSuppliersRequest",
    # Environment schemas
    "EnvironmentCreate",
    "EnvironmentResponse",
    "GoalCreate",
    # Prediction schemas
    "PredictionRequest",
    "PredictionResponse",
    # Workflow schemas
    "WorkflowCreate",
    "WorkflowResponse",
    # Matching schemas
    "NegotiationRequest",
    "ProposalRequest",
    "NetworkExploreRequest",
    "RecommendationRequest",
    "MatchRequest",
    "MatchResponse",
    # Collaboration schemas
    "CollaborationCreateRequest",
    "CollaborationRoleAssignRequest",
    "CollaborationResponse",
    # System schemas
    "HealthResponse",
]
