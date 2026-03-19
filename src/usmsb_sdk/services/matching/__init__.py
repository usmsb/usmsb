"""
USMSB Matching Module.

Phase 3 of USMSB Agent Platform implementation.

Exports:
- USMSBMatchingEngine: Three-dimensional matching (Goal + Capability + Value)
- EmergenceDiscovery: Hybrid emergence mechanism
- CollaborationOpportunity: Match result data model
- EmergenceStats: Platform emergence statistics
"""

from usmsb_sdk.services.matching.emergence_discovery import (
    EmergenceDiscovery,
    EmergenceStats,
    OpportunityDiscoveryResult,
)
from usmsb_sdk.services.matching.usmsb_matching_engine import (
    CollaborationOpportunity,
    USMSBMatchingEngine,
)

__all__ = [
    "USMSBMatchingEngine",
    "EmergenceDiscovery",
    "CollaborationOpportunity",
    "EmergenceStats",
    "OpportunityDiscoveryResult",
]
