"""
USMSB SDK Core Module.

Stable API exports for USMSB Core Framework:
- 9 Elements
- 9 Universal Actions
- 6 Logic Engines
"""

from usmsb_sdk.core.config import (
    AgentConfig as CoreAgentConfig,
    AuthConfig,
    DatabaseConfig,
    LoggingConfig,
    NetworkConfig,
    PlatformConfig,
    load_config,
    load_config_from_env,
)

# Elements
from usmsb_sdk.core.elements import (
    Agent,
    AgentType,
    Environment,
    EnvironmentType,
    Goal,
    GoalStatus,
    Information,
    InformationType,
    Object,
    Resource,
    ResourceType,
    Risk,
    RiskType,
    Rule,
    RuleType,
    Value,
    ValueType,
)

# Interfaces
from usmsb_sdk.core.interfaces import (
    IDecisionService,
    IEvaluationService,
    IExecutionService,
    IFeedbackService,
    IInteractionService,
    ILearningService,
    IPerceptionService,
    IRiskManagementService,
    ITransformationService,
)

# Universal Actions (Interface + LLM Implementations)
from usmsb_sdk.core.universal_actions import (
    IPerceptionService,
    IDecisionService,
    IExecutionService,
    IInteractionService,
    ITransformationService,
    IEvaluationService,
    IFeedbackService,
    ILearningService,
    IRiskManagementService,
    LLMPerceptionService,
    LLMDecisionService,
    LLMExecutionService,
    LLMInteractionService,
    LLMTransformationService,
    LLMEvaluationService,
    LLMFeedbackService,
    LLMLearningService,
    LLMRiskManagementService,
    UniversalActionServiceFactory,
    ActionResult,
    ActionResultStatus,
)

# Logic - Goal Action Outcome
from usmsb_sdk.core.logic.goal_action_outcome import (
    ActionResult,
    GoalActionOutcomeLoop,
    GoalManager,
    LoopIteration,
    LoopStatus,
)

# Logic - Core Engines
from usmsb_sdk.core.logic.core_engines import (
    LogicEngineRegistry,
    ResourceTransformationValueEngine,
    InformationDecisionControlEngine,
    SystemEnvironmentEngine,
    EmergenceSelfOrganizationEngine,
    AdaptationEvolutionEngine,
    AdaptationRecord,
    EvolutionMetric,
)

__all__ = [
    # Configuration
    "CoreAgentConfig",
    "AuthConfig",
    "DatabaseConfig",
    "LoggingConfig",
    "NetworkConfig",
    "PlatformConfig",
    "load_config",
    "load_config_from_env",
    # Elements
    "Agent",
    "AgentType",
    "Environment",
    "EnvironmentType",
    "Goal",
    "GoalStatus",
    "Information",
    "InformationType",
    "Object",
    "Resource",
    "ResourceType",
    "Risk",
    "RiskType",
    "Rule",
    "RuleType",
    "Value",
    "ValueType",
    # Interfaces
    "IDecisionService",
    "IEvaluationService",
    "IExecutionService",
    "IFeedbackService",
    "IInteractionService",
    "ILearningService",
    "IPerceptionService",
    "IRiskManagementService",
    "ITransformationService",
    # Universal Actions
    "LLMPerceptionService",
    "LLMDecisionService",
    "LLMExecutionService",
    "LLMInteractionService",
    "LLMTransformationService",
    "LLMEvaluationService",
    "LLMFeedbackService",
    "LLMLearningService",
    "LLMRiskManagementService",
    "UniversalActionServiceFactory",
    "ActionResult",
    "ActionResultStatus",
    # Goal Action Outcome
    "GoalActionOutcomeLoop",
    "GoalManager",
    "LoopStatus",
    "LoopIteration",
    # Core Engines
    "LogicEngineRegistry",
    "ResourceTransformationValueEngine",
    "InformationDecisionControlEngine",
    "SystemEnvironmentEngine",
    "EmergenceSelfOrganizationEngine",
    "AdaptationEvolutionEngine",
    "AdaptationRecord",
    "EvolutionMetric",
]
