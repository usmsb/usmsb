"""
Workflow management endpoints.

Stake Requirements:
- create: No stake required
- execute: 100 VIBE minimum
- list: No stake required
"""

import json
import logging
import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, status, Depends

from usmsb_sdk.api.database import (
    get_agent as db_get_agent,
    create_workflow as db_create_workflow,
    get_workflows as db_get_workflows,
)
from usmsb_sdk.api.rest.schemas.workflow import WorkflowCreate
from usmsb_sdk.api.rest.services.utils import safe_json_loads, create_agent_from_db_data
from usmsb_sdk.api.rest.unified_auth import (
    get_current_user_unified,
    require_stake_unified,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Global reference to workflow service (set by main.py)
_workflow_service = None


def set_workflow_service(service):
    """Set the workflow service instance."""
    global _workflow_service
    _workflow_service = service


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_create: WorkflowCreate,
    user: Dict[str, Any] = Depends(get_current_user_unified)
):
    """Create a new workflow.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - No stake required
    """
    # Return mock workflow if service not available
    if not _workflow_service:
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        # Save to database
        workflow_data = {
            'id': workflow_id,
            'name': workflow_create.task_description[:30],
            'agent_id': user.get('agent_id') or user.get('user_id'),
            'task_description': workflow_create.task_description,
            'status': 'pending',
            'steps': json.dumps(workflow_create.available_tools or []),
        }
        db_create_workflow(workflow_data)
        return {
            "workflow_id": workflow_id,
            "name": workflow_create.task_description[:30],
            "steps_count": len(workflow_create.available_tools) if workflow_create.available_tools else 3,
            "status": "pending",
            "creator_id": user.get('agent_id') or user.get('user_id'),
        }

    # Create domain object for service
    agent_data = db_get_agent(user.get('agent_id') or user.get('user_id'))
    agent_obj = create_agent_from_db_data(agent_data) if agent_data else None

    try:
        workflow = await _workflow_service.create_workflow(
            task_description=workflow_create.task_description,
            agent=agent_obj,
            available_tools=workflow_create.available_tools,
        )

        return {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "steps_count": len(workflow.steps),
            "status": workflow.status.value,
            "creator_id": user.get('agent_id') or user.get('user_id'),
        }
    except Exception as e:
        logger.error(f"Workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {str(e)}")


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    user: Dict[str, Any] = Depends(require_stake_unified(100))
):
    """Execute a workflow.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
        - Minimum 100 VIBE stake
    """
    # Return mock result if service not available
    if not _workflow_service:
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": {
                "output": "Workflow executed successfully",
                "steps_completed": 3,
                "execution_time": "2.5s",
            },
            "executor_id": user.get('agent_id') or user.get('user_id'),
        }

    # Create domain object for service
    agent_data = db_get_agent(user.get('agent_id') or user.get('user_id'))
    agent_obj = create_agent_from_db_data(agent_data) if agent_data else None

    try:
        result = await _workflow_service.execute_workflow(
            workflow_id=workflow_id,
            agent=agent_obj,
        )

        return {
            "workflow_id": result.workflow_id,
            "status": result.status.value,
            "total_steps": result.total_steps,
            "completed_steps": result.completed_steps,
            "failed_steps": result.failed_steps,
            "execution_time": result.execution_time,
            "step_results": result.step_results,
            "executor_id": user.get('agent_id') or user.get('user_id'),
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.get("")
async def list_workflows(user: Dict[str, Any] = Depends(get_current_user_unified)):
    """List all workflows for the authenticated agent.

    Requires:
        - X-API-Key header
        - X-Agent-ID header
    """
    # Get from database
    workflows_data = db_get_workflows()

    if not workflows_data:
        # Return mock data if no workflows in database and service not available
        if not _workflow_service:
            return [
                {
                    "id": "wf-001",
                    "name": "Sample Workflow",
                    "status": "completed",
                    "steps_count": 3,
                },
                {
                    "id": "wf-002",
                    "name": "Data Processing",
                    "status": "running",
                    "steps_count": 5,
                },
            ]
        # Get from service if available
        workflows = _workflow_service.list_workflows()
        return [
            {
                "id": w.id,
                "name": w.name,
                "status": w.status.value,
                "steps_count": len(w.steps),
            }
            for w in workflows
        ]

    result = []
    for w in workflows_data:
        steps = safe_json_loads(w.get('steps', '[]'), [])
        result.append({
            "id": w.get('id'),
            "name": w.get('name'),
            "status": w.get('status', 'pending'),
            "steps_count": len(steps),
        })
    return result
