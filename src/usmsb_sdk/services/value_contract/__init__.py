"""
Value Contract Module.

Phase 2 of USMSB Agent Platform implementation.

Exports:
- TaskValueContract, ProjectValueContract, ValueFlow, ContractRisk, ContractMilestone
- ValueContractService for lifecycle management
- ValueNegotiationService for negotiation
- ContractTemplate and TEMPLATES registry
"""

from usmsb_sdk.services.value_contract.models import (
    BaseValueContract,
    ContractMilestone,
    ContractRisk,
    ProjectValueContract,
    TaskValueContract,
    ValueFlow,
)
from usmsb_sdk.services.value_contract.negotiation import (
    NegotiationRound,
    ValueNegotiationSession,
    ValueNegotiationService,
)
from usmsb_sdk.services.value_contract.service import ValueContractService
from usmsb_sdk.services.value_contract.templates import (
    TEMPLATES,
    ContractTemplate,
    SIMPLE_TASK_TEMPLATE,
    COMPLEX_TASK_TEMPLATE,
    PROJECT_TEMPLATE,
    get_template,
    list_templates,
)

__all__ = [
    # Models
    "BaseValueContract",
    "TaskValueContract",
    "ProjectValueContract",
    "ValueFlow",
    "ContractRisk",
    "ContractMilestone",
    # Negotiation
    "ValueNegotiationSession",
    "ValueNegotiationService",
    "NegotiationRound",
    # Service
    "ValueContractService",
    # Templates
    "ContractTemplate",
    "TEMPLATES",
    "SIMPLE_TASK_TEMPLATE",
    "COMPLEX_TASK_TEMPLATE",
    "PROJECT_TEMPLATE",
    "get_template",
    "list_templates",
]
