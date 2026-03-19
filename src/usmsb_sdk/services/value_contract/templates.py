"""
Value Contract Templates

Phase 2 of USMSB Agent Platform implementation.

Pre-defined contract templates for common scenarios.
Templates define:
- Fixed terms (80%): Non-negotiable standard terms
- Variable terms (20%): Negotiable terms that parties can adjust
- Variable ranges: Valid ranges for each negotiable term

Agents use these templates to quickly create contracts via auto-negotiation.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContractTemplate:
    """
    A contract template with fixed and variable terms.

    Fixed terms (80%): Standard clauses that cannot be changed.
    Variable terms (20%): Terms parties can negotiate within ranges.
    """

    template_id: str = ""
    name: str = ""
    description: str = ""

    # Contract type: "task" | "project"
    contract_type: str = "task"

    # Fixed terms (non-negotiable)
    fixed_terms: dict[str, Any] = field(default_factory=dict)

    # Variable terms (negotiable)
    variable_terms: list[str] = field(default_factory=list)
    # Example: ["price_vibe", "deadline"]

    # Valid ranges for variable terms
    variable_ranges: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Example: {
    #     "price_vibe": {"min": 0.1, "max": 100.0, "default": 5.0},
    #     "deadline": {"min": 3600, "max": 604800, "default": 86400, "unit": "seconds"}
    # }

    # Default values for all terms
    default_terms: dict[str, Any] = field(default_factory=dict)

    # Risk allocation default
    default_risk_allocation: str = "supply_bears_risk"  # supply_bears_risk | demand_bears_risk | shared

    # Dispute resolution default
    default_dispute_resolution: str = "platform_arbitration"  # platform_arbitration | third_party | direct

    def get_variable_ranges(self) -> dict[str, dict[str, Any]]:
        """Get variable term ranges with defaults."""
        ranges = {}
        for term in self.variable_terms:
            if term in self.variable_ranges:
                ranges[term] = self.variable_ranges[term]
            elif term in self.default_terms:
                ranges[term] = {"default": self.default_terms[term]}
        return ranges


# ============== Pre-defined Templates ==============


SIMPLE_TASK_TEMPLATE = ContractTemplate(
    template_id="simple_task",
    name="Simple Task Template",
    description="For quick, well-defined tasks with clear deliverables and short turnaround.",
    contract_type="task",
    fixed_terms={
        "risk_allocation": "supply_bears_risk",
        "dispute_resolution": "platform_arbitration",
        "payment_trigger": "on_delivery",
        "revision_rounds": 0,
        "cancellation_notice_hours": 24,
        "platform_fee_percentage": 5.0,
        "confidentiality": "standard",
        "intellectual_property": "deliverable_owned_by_demand",
    },
    variable_terms=["price_vibe", "deadline", "penalty_vibe"],
    variable_ranges={
        "price_vibe": {
            "min": 0.01,
            "max": 100.0,
            "default": 1.0,
            "unit": "VIBE",
            "description": "Total task price in VIBE",
        },
        "deadline": {
            "min": 3600,  # 1 hour
            "max": 604800,  # 7 days
            "default": 86400,  # 1 day
            "unit": "seconds",
            "description": "Task deadline from contract activation",
        },
        "penalty_vibe": {
            "min": 0.0,
            "max": 50.0,
            "default": 0.5,
            "unit": "VIBE",
            "description": "Penalty if supply side fails to deliver",
        },
    },
    default_terms={
        "price_vibe": 1.0,
        "deadline": 86400,
        "penalty_vibe": 0.5,
    },
)

COMPLEX_TASK_TEMPLATE = ContractTemplate(
    template_id="complex_task",
    name="Complex Task Template",
    description="For multi-stage tasks requiring intermediate checkpoints and revisions.",
    contract_type="task",
    fixed_terms={
        "risk_allocation": "shared",
        "dispute_resolution": "platform_arbitration",
        "payment_trigger": "on_milestone",
        "revision_rounds": 2,
        "cancellation_notice_hours": 72,
        "platform_fee_percentage": 5.0,
        "confidentiality": "enhanced",
        "intellectual_property": "deliverable_owned_by_demand",
        "milestone_count": 3,
    },
    variable_terms=["price_vibe", "deadline", "milestones", "revision_rounds", "penalty_vibe"],
    variable_ranges={
        "price_vibe": {
            "min": 1.0,
            "max": 1000.0,
            "default": 50.0,
            "unit": "VIBE",
            "description": "Total task price in VIBE",
        },
        "deadline": {
            "min": 86400,  # 1 day
            "max": 2592000,  # 30 days
            "default": 604800,  # 7 days
            "unit": "seconds",
            "description": "Overall task deadline",
        },
        "milestones": {
            "min": 2,
            "max": 5,
            "default": 3,
            "description": "Number of milestone checkpoints",
        },
        "revision_rounds": {
            "min": 0,
            "max": 5,
            "default": 2,
            "description": "Number of revision rounds per milestone",
        },
        "penalty_vibe": {
            "min": 0.0,
            "max": 200.0,
            "default": 10.0,
            "unit": "VIBE",
            "description": "Penalty for failed delivery",
        },
    },
    default_terms={
        "price_vibe": 50.0,
        "deadline": 604800,
        "milestones": 3,
        "revision_rounds": 2,
        "penalty_vibe": 10.0,
    },
)

PROJECT_TEMPLATE = ContractTemplate(
    template_id="project",
    name="Project Template",
    description="For multi-agent projects with phases, sub-tasks, and complex coordination.",
    contract_type="project",
    fixed_terms={
        "risk_allocation": "shared",
        "dispute_resolution": "platform_arbitration",
        "payment_trigger": "on_phase_milestone",
        "revision_rounds": 3,
        "cancellation_notice_days": 7,
        "platform_fee_percentage": 5.0,
        "confidentiality": "enhanced",
        "intellectual_property": "jointly_owned",
        "governance": "consensus_based",
    },
    variable_terms=[
        "total_budget_vibe",
        "project_duration_days",
        "phase_count",
        "governance_model",
        "ip_sharing",
    ],
    variable_ranges={
        "total_budget_vibe": {
            "min": 10.0,
            "max": 10000.0,
            "default": 500.0,
            "unit": "VIBE",
            "description": "Total project budget",
        },
        "project_duration_days": {
            "min": 7,
            "max": 180,
            "default": 30,
            "unit": "days",
            "description": "Project duration in days",
        },
        "phase_count": {
            "min": 2,
            "max": 10,
            "default": 4,
            "description": "Number of project phases",
        },
        "governance_model": {
            "values": ["consensus_based", "lead_agent", "voting", "tiered"],
            "default": "lead_agent",
            "description": "How project decisions are made",
        },
        "ip_sharing": {
            "values": ["jointly_owned", "demand_owns", "each_owns_contribution", "open_source"],
            "default": "jointly_owned",
            "description": "How intellectual property is shared",
        },
    },
    default_terms={
        "total_budget_vibe": 500.0,
        "project_duration_days": 30,
        "phase_count": 4,
        "governance_model": "lead_agent",
        "ip_sharing": "jointly_owned",
    },
)

# Template registry
TEMPLATES = {
    "simple_task": SIMPLE_TASK_TEMPLATE,
    "complex_task": COMPLEX_TASK_TEMPLATE,
    "project": PROJECT_TEMPLATE,
}


def get_template(template_id: str) -> ContractTemplate | None:
    """Get a template by ID."""
    return TEMPLATES.get(template_id)


def list_templates() -> list[ContractTemplate]:
    """List all available templates."""
    return list(TEMPLATES.values())
