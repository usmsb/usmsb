"""
USMSB SDK REST API Schemas

Pydantic models for request/response validation.
"""

from usmsb_sdk.api.rest.schemas.agent import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    AgentRegistrationRequest,
    MCPRegistrationRequest,
    A2ARegistrationRequest,
    SkillMDRegistrationRequest,
    AgentTestRequest,
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
from usmsb_sdk.api.rest.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
)
from usmsb_sdk.api.rest.schemas.workflow import (
    WorkflowCreate,
    WorkflowResponse,
)
from usmsb_sdk.api.rest.schemas.matching import (
    NegotiationRequest,
    ProposalRequest,
    NetworkExploreRequest,
    RecommendationRequest,
    MatchRequest,
    MatchResponse,
)
from usmsb_sdk.api.rest.schemas.collaboration import (
    CollaborationCreateRequest,
    CollaborationRoleAssignRequest,
    CollaborationResponse,
)
from usmsb_sdk.api.rest.schemas.system import (
    HealthResponse,
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
