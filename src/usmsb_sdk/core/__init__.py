"""
USMSB SDK Core Module.

Stable API exports for USMSB Core Framework:
- 9 Elements
- 9 Universal Actions
- 6 Logic Engines
"""

from importlib import import_module as _import_module

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

_EXPORTS = {}
for _module, _names in (
    (
        "config",
        (
            "AuthConfig",
            "DatabaseConfig",
            "LoggingConfig",
            "NetworkConfig",
            "PlatformConfig",
            "load_config",
            "load_config_from_env",
        ),
    ),
    (
        "elements",
        (
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
        ),
    ),
    # Historically these interfaces shadowed core.interfaces' names. Preserve
    # the final public objects, including the distinct ActionResult below.
    (
        "universal_actions",
        (
            "IDecisionService",
            "IEvaluationService",
            "IExecutionService",
            "IFeedbackService",
            "IInteractionService",
            "ILearningService",
            "IPerceptionService",
            "IRiskManagementService",
            "ITransformationService",
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
            "ActionResultStatus",
        ),
    ),
    (
        "logic.goal_action_outcome",
        (
            "ActionResult",
            "GoalActionOutcomeLoop",
            "GoalManager",
            "LoopStatus",
            "LoopIteration",
        ),
    ),
    (
        "logic.core_engines",
        (
            "LogicEngineRegistry",
            "ResourceTransformationValueEngine",
            "InformationDecisionControlEngine",
            "SystemEnvironmentEngine",
            "EmergenceSelfOrganizationEngine",
            "AdaptationEvolutionEngine",
            "AdaptationRecord",
            "EvolutionMetric",
        ),
    ),
):
    _EXPORTS.update({name: (f"usmsb_sdk.core.{_module}", name) for name in _names})
_EXPORTS["CoreAgentConfig"] = ("usmsb_sdk.core.config", "AgentConfig")
del _module, _names


def __getattr__(name: str):
    """Resolve the same public object as the full SDK's former eager exports."""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module, attribute = _EXPORTS[name]
    value = getattr(_import_module(module), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
