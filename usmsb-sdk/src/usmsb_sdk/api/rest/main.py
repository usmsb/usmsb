"""
USMSB SDK REST API

FastAPI-based REST API for the USMSB SDK.
Provides endpoints for agent management, predictions, simulations, and workflows.
"""

import logging
import os
import uuid
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from usmsb_sdk.config.settings import get_settings, Settings
from usmsb_sdk.core.elements import (
    Agent,
    AgentType,
    Environment,
    EnvironmentType,
    Goal,
    GoalStatus,
    Information,
    Resource,
    Risk,
    Rule,
    Value,
)
from usmsb_sdk.intelligence_adapters.base import IntelligenceSourceConfig, IntelligenceSourceType
from usmsb_sdk.intelligence_adapters.llm.openai_adapter import OpenAIAdapter
from usmsb_sdk.intelligence_adapters.manager import IntelligenceSourceManager, SelectionStrategy
from usmsb_sdk.services.behavior_prediction_service import BehaviorPredictionService
from usmsb_sdk.services.agentic_workflow_service import AgenticWorkflowService

# Import auth router
from usmsb_sdk.api.rest.auth import router as auth_router

# Import transactions router
from usmsb_sdk.api.rest.transactions import router as transactions_router

# Import environment router
from usmsb_sdk.api.rest.environment import router as environment_router

# Import governance router
from usmsb_sdk.api.rest.governance import router as governance_router

# Import agent auth router
from usmsb_sdk.api.rest.agent_auth import router as agent_auth_router

# Import quotes router
from usmsb_sdk.api.rest.quotes import router as quotes_router

# Import matching engine
from usmsb_sdk.services.matching_engine import MatchingEngine

# Import WebSocket manager
from usmsb_sdk.api.rest.websocket import get_ws_manager

# Import database module with aliases to avoid conflicts with endpoint functions
from usmsb_sdk.api.database import (
    get_db,
    init_db,
    create_agent as db_create_agent,
    get_agent as db_get_agent,
    get_all_agents as db_get_all_agents,
    delete_agent as db_delete_agent,
    create_ai_agent as db_create_ai_agent,
    get_ai_agent as db_get_ai_agent,
    get_all_ai_agents as db_get_all_ai_agents,
    update_ai_agent_heartbeat as db_update_ai_agent_heartbeat,
    update_ai_agent_stake as db_update_ai_agent_stake,
    delete_ai_agent as db_delete_ai_agent,
    create_service as db_create_service,
    get_services_by_agent as db_get_services_by_agent,
    create_environment as db_create_environment,
    get_environment as db_get_environment,
    get_all_environments as db_get_all_environments,
    create_demand as db_create_demand,
    search_demands as db_search_demands,
    create_opportunity as db_create_opportunity,
    get_all_opportunities as db_get_all_opportunities,
    create_negotiation as db_create_negotiation,
    get_negotiations as db_get_negotiations,
    get_negotiation as db_get_negotiation,
    create_workflow as db_create_workflow,
    get_workflows as db_get_workflows,
    get_workflow as db_get_workflow,
    create_collaboration as db_create_collaboration,
    get_collaborations as db_get_collaborations,
    get_collaboration as db_get_collaboration,
    create_proposal as db_create_proposal,
    get_proposals as db_get_proposals,
    vote_proposal as db_vote_proposal,
    save_learning_insight as db_save_learning_insight,
    get_learning_insights as db_get_learning_insights,
    create_or_update_profile as db_create_or_update_profile,
    get_profile as db_get_profile,
    get_metrics as db_get_metrics,
)

logger = logging.getLogger(__name__)


# ==================== Helper Functions ====================

def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string with error handling.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    if default is None:
        default = {} if json_str and json_str.strip().startswith('{') else []

    if not json_str:
        return default

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON: {e}")
        return default


def safe_json_loads_deep(value: Any, default: Any = None) -> Any:
    """
    Safely parse JSON string, handling double-encoded JSON.

    Args:
        value: Value to parse (may be string, already parsed, or None)
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    if default is None:
        default = []

    if value is None:
        return default

    # Already a list or dict
    if isinstance(value, (list, dict)):
        return value

    # Try to parse string
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            # Handle double-encoded JSON
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    pass
            return parsed if isinstance(parsed, (list, dict)) else default
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON: {e}")
            return default

    return default


def create_agent_from_db_data(agent_data: dict) -> Agent:
    """
    Create an Agent object from database data.

    Args:
        agent_data: Dictionary containing agent data from database

    Returns:
        Agent object
    """
    try:
        agent_type = AgentType(agent_data.get('type', 'ai_agent'))
    except ValueError:
        agent_type = AgentType.AI_AGENT

    return Agent(
        id=agent_data['id'],
        name=agent_data['name'],
        type=agent_type,
        capabilities=safe_json_loads(agent_data.get('capabilities', '[]'), []),
        state=safe_json_loads(agent_data.get('state', '{}'), {}),
    )


# Global instances
settings: Settings = None
source_manager: IntelligenceSourceManager = None
prediction_service: BehaviorPredictionService = None
workflow_service: AgenticWorkflowService = None
matching_engine: MatchingEngine = None

# In-memory storage (replace with database in production)
agents_store: Dict[str, Agent] = {}
environments_store: Dict[str, Environment] = {}


# Pydantic models for API
class AgentCreate(BaseModel):
    """Schema for creating an agent."""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(default="ai_agent")
    capabilities: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Schema for agent response."""
    id: str
    name: str
    type: str
    capabilities: List[str]
    state: Dict[str, Any]
    goals_count: int
    resources_count: int
    created_at: float


class GoalCreate(BaseModel):
    """Schema for creating a goal."""
    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    priority: int = Field(default=0, ge=0)


class EnvironmentCreate(BaseModel):
    """Schema for creating an environment."""
    name: str = Field(..., min_length=1)
    type: str = Field(default="social")
    state: Dict[str, Any] = Field(default_factory=dict)


class PredictionRequest(BaseModel):
    """Schema for prediction request."""
    agent_id: str
    environment_id: Optional[str] = None
    goal_name: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class WorkflowCreate(BaseModel):
    """Schema for creating a workflow."""
    task_description: str = Field(..., min_length=1)
    agent_id: str
    available_tools: Optional[List[str]] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: float
    services: Dict[str, str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global settings, source_manager, prediction_service, workflow_service, matching_engine

    # Startup
    logger.info("Starting USMSB SDK API...")

    # Initialize database
    logger.info("Initializing SQLite database...")
    init_db()
    logger.info("Database initialized successfully!")

    settings = get_settings()
    logger.info(f"Loaded settings for environment: {settings.environment}")

    # Initialize intelligence source manager
    source_manager = IntelligenceSourceManager(
        selection_strategy=SelectionStrategy.PRIORITY
    )

    # Register OpenAI adapter if API key is available
    if settings.llm.api_key:
        llm_config = IntelligenceSourceConfig(
            name="openai",
            type=IntelligenceSourceType.LLM,
            api_key=settings.llm.api_key,
            model=settings.llm.model,
            extra_params={
                "temperature": settings.llm.temperature,
                "max_tokens": settings.llm.max_tokens,
            }
        )
        adapter = OpenAIAdapter(llm_config)
        await source_manager.register_source(
            name="openai",
            source=adapter,
            priority=1,
            is_primary=True,
        )
        logger.info("OpenAI adapter registered")

    # Initialize services
    llm = source_manager.get_llm()
    if llm:
        prediction_service = BehaviorPredictionService(llm)
        workflow_service = AgenticWorkflowService(llm)
        logger.info("Application services initialized")

    # Initialize matching engine
    matching_engine = MatchingEngine(llm_adapter=llm if llm else None)
    logger.info("Matching engine initialized")

    logger.info("USMSB SDK API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down USMSB SDK API...")
    if source_manager:
        await source_manager.shutdown_all()
    logger.info("USMSB SDK API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="USMSB SDK API",
    description="REST API for the USMSB (Universal System Model of Social Behavior) SDK",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include auth router
app.include_router(auth_router)

# Include transactions router
app.include_router(transactions_router)

# Include environment router
app.include_router(environment_router)

# Include governance router
app.include_router(governance_router)

# Include agent auth router
app.include_router(agent_auth_router)

# Include quotes router
app.include_router(quotes_router)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    manager = await get_ws_manager()
    client = await manager.connect(websocket)
    try:
        while True:
            try:
                data = await websocket.receive_json()
                await manager.handle_message(websocket, data)
            except WebSocketDisconnect:
                break
    finally:
        await manager.disconnect(websocket)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()},
    )


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health status."""
    services = {
        "llm": "available" if source_manager and source_manager.get_llm() else "unavailable",
        "prediction": "available" if prediction_service else "unavailable",
        "workflow": "available" if workflow_service else "unavailable",
    }

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now().timestamp(),
        services=services,
    )


# Agent endpoints
@app.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED, tags=["Agents"])
async def create_agent(agent_create: AgentCreate):
    """Create a new agent."""
    try:
        agent_type = AgentType(agent_create.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent type. Valid types: {[t.value for t in AgentType]}"
        )

    agent = Agent(
        name=agent_create.name,
        type=agent_type,
        capabilities=agent_create.capabilities,
        state=agent_create.state,
    )

    # Save to database
    agent_data = {
        'id': agent.id,
        'name': agent.name,
        'type': agent.type.value,
        'capabilities': agent.capabilities,
        'state': agent.state,
        'goals_count': len(agent.goals),
        'resources_count': len(agent.resources),
    }
    db_create_agent(agent_data)

    return AgentResponse(
        id=agent.id,
        name=agent.name,
        type=agent.type.value,
        capabilities=agent.capabilities,
        state=agent.state,
        goals_count=len(agent.goals),
        resources_count=len(agent.resources),
        created_at=agent.created_at,
    )


@app.get("/agents", response_model=List[AgentResponse], tags=["Agents"])
async def list_agents(
    type: Optional[str] = Query(None, description="Filter by agent type"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all agents."""
    # Get from database
    agents_data = db_get_all_agents(agent_type=type, limit=limit)

    result = []
    for a in agents_data:
        # Parse JSON fields safely
        capabilities = safe_json_loads(a.get('capabilities', '[]'), [])
        state = safe_json_loads(a.get('state', '{}'), {})
        result.append(AgentResponse(
            id=a['id'],
            name=a['name'],
            type=a['type'],
            capabilities=capabilities,
            state=state,
            goals_count=a.get('goals_count', 0),
            resources_count=a.get('resources_count', 0),
            created_at=a.get('created_at', 0),
        ))
    return result


@app.get("/agents/{agent_id}", response_model=AgentResponse, tags=["Agents"])
async def get_agent_endpoint(agent_id: str):
    """Get an agent by ID."""
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Parse JSON fields safely
    capabilities = safe_json_loads(agent_data.get('capabilities', '[]'), [])
    state = safe_json_loads(agent_data.get('state', '{}'), {})
    return AgentResponse(
        id=agent_data['id'],
        name=agent_data['name'],
        type=agent_data['type'],
        capabilities=capabilities,
        state=state,
        goals_count=agent_data.get('goals_count', 0),
        resources_count=agent_data.get('resources_count', 0),
        created_at=agent_data.get('created_at', 0),
    )


@app.post("/agents/{agent_id}/goals", status_code=status.HTTP_201_CREATED, tags=["Agents"])
async def add_goal_to_agent(agent_id: str, goal_create: GoalCreate):
    """Add a goal to an agent."""
    # Check if agent exists
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create goal with unique ID
    goal_id = str(uuid.uuid4())

    # Update goals_count in database
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE agents SET goals_count = goals_count + 1, updated_at = ? WHERE id = ?',
            (datetime.now().timestamp(), agent_id)
        )

    return {"goal_id": goal_id, "status": "created"}


@app.delete("/agents/{agent_id}", tags=["Agents"])
async def delete_agent_endpoint(agent_id: str):
    """Delete an agent."""
    # Check if agent exists
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Delete from database
    db_delete_agent(agent_id)
    return {"status": "deleted"}


# Environment endpoints
@app.post("/environments", status_code=status.HTTP_201_CREATED, tags=["Environments"])
async def create_environment_endpoint(env_create: EnvironmentCreate):
    """Create a new environment."""
    try:
        env_type = EnvironmentType(env_create.type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid environment type. Valid types: {[t.value for t in EnvironmentType]}"
        )

    environment = Environment(
        name=env_create.name,
        type=env_type,
        state=env_create.state,
    )

    # Save to database
    env_data = {
        'id': environment.id,
        'name': environment.name,
        'type': environment.type.value,
        'state': environment.state,
    }
    db_create_environment(env_data)

    return {"id": environment.id, "name": environment.name, "type": environment.type.value}


@app.get("/environments", tags=["Environments"])
async def list_environments(limit: int = Query(100, ge=1, le=1000)):
    """List all environments."""
    # Get from database
    envs_data = db_get_all_environments(limit=limit)

    result = []
    for e in envs_data:
        state = safe_json_loads(e.get('state', '{}'), {})
        result.append({
            "id": e['id'],
            "name": e['name'],
            "type": e['type'],
            "state": state,
        })
    return result


@app.get("/environments/{env_id}", tags=["Environments"])
async def get_environment_endpoint(env_id: str):
    """Get an environment by ID."""
    env_data = db_get_environment(env_id)
    if not env_data:
        raise HTTPException(status_code=404, detail="Environment not found")

    state = safe_json_loads(env_data.get('state', '{}'), {})
    return {"id": env_data['id'], "name": env_data['name'], "type": env_data['type'], "state": state}


# Demand endpoints
class DemandCreate(BaseModel):
    """Schema for creating a demand."""
    agent_id: str
    title: str
    description: str = ""
    category: str = ""
    required_skills: List[str] = Field(default_factory=list)
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    deadline: str = ""
    priority: str = "medium"
    quality_requirements: str = ""


@app.post("/demands", status_code=status.HTTP_201_CREATED, tags=["Demands"])
async def create_demand_endpoint(demand_create: DemandCreate):
    """Create a new demand."""
    # Check if agent exists
    agent = db_get_agent(demand_create.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    demand_data = {
        'agent_id': demand_create.agent_id,
        'title': demand_create.title,
        'description': demand_create.description,
        'category': demand_create.category,
        'required_skills': demand_create.required_skills,
        'budget_min': demand_create.budget_min,
        'budget_max': demand_create.budget_max,
        'deadline': demand_create.deadline,
        'priority': demand_create.priority,
        'quality_requirements': demand_create.quality_requirements,
        'status': 'active',
    }

    demand = db_create_demand(demand_data)
    return {
        "id": demand.get('id'),
        "agent_id": demand.get('agent_id'),
        "title": demand.get('title'),
        "status": demand.get('status'),
        "created_at": demand.get('created_at'),
    }


@app.get("/demands", tags=["Demands"])
async def list_demands(
    agent_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all demands."""
    demands = db_search_demands()

    if agent_id:
        demands = [d for d in demands if d.get('agent_id') == agent_id]
    if category:
        demands = [d for d in demands if d.get('category') == category]

    result = []
    for d in demands[:limit]:
        required_skills = safe_json_loads(d.get('required_skills', '[]'), [])
        result.append({
            "id": d.get('id'),
            "agent_id": d.get('agent_id'),
            "title": d.get('title'),
            "description": d.get('description'),
            "category": d.get('category'),
            "required_skills": required_skills,
            "budget_min": d.get('budget_min'),
            "budget_max": d.get('budget_max'),
            "status": d.get('status'),
            "created_at": d.get('created_at'),
        })
    return result


@app.delete("/demands/{demand_id}", tags=["Demands"])
async def delete_demand(demand_id: str):
    """Delete a demand."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM demands WHERE id = ?', (demand_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Demand not found")
    return {"status": "deleted"}


# Prediction endpoints
@app.post("/predict/behavior", tags=["Predictions"])
async def predict_behavior(request: PredictionRequest):
    """Predict agent behavior."""
    # Return mock prediction if service not available
    if not prediction_service:
        # Try to get agent from database
        agent_data = db_get_agent(request.agent_id)
        if not agent_data:
            return {
                "predicted_behavior": "collaborative",
                "confidence": 0.85,
                "reasoning": "Based on agent's historical behavior patterns and current goal priorities",
                "recommended_actions": [
                    {"action": "initiate_negotiation", "priority": 1},
                    {"action": "explore_network", "priority": 2},
                ]
            }

        # Return prediction based on agent data from database
        return {
            "agent_id": request.agent_id,
            "prediction": {
                "predicted_behavior": "collaborative",
                "confidence": 0.75,
                "reasoning": f"Based on agent {agent_data.get('name')} capabilities and goals",
                "recommended_actions": [
                    {"action": "initiate_negotiation", "priority": 1},
                    {"action": "explore_network", "priority": 2},
                ]
            }
        }

    # If service is available, use it (requires domain objects)
    agent_data = db_get_agent(request.agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create domain object for the service
    agent = create_agent_from_db_data(agent_data)

    environment = None
    if request.environment_id:
        env_data = db_get_environment(request.environment_id)
        if env_data:
            try:
                env_type = EnvironmentType(env_data.get('type', 'sandbox'))
            except ValueError:
                env_type = EnvironmentType.sandbox
            environment = Environment(
                id=env_data['id'],
                name=env_data['name'],
                type=env_type,
                state=safe_json_loads(env_data.get('state', '{}'), {}),
            )
    else:
        environment = Environment(name="default")

    goal = None
    if request.goal_name:
        for g in agent.goals:
            if g.name == request.goal_name:
                goal = g
                break

    try:
        prediction = await prediction_service.predict_agent_behavior(
            agent=agent,
            environment=environment,
            goal=goal,
            context=request.context,
        )

        return {
            "agent_id": agent.id,
            "prediction": {
                "predicted_actions": prediction.predicted_actions,
                "confidence": prediction.confidence,
                "reasoning": prediction.reasoning,
                "alternative_scenarios": prediction.alternative_scenarios,
                "risk_factors": prediction.risk_factors,
            },
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


# Workflow endpoints
@app.post("/workflows", status_code=status.HTTP_201_CREATED, tags=["Workflows"])
async def create_workflow(workflow_create: WorkflowCreate):
    """Create a new workflow."""
    # Check if agent exists
    agent_data = db_get_agent(workflow_create.agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Return mock workflow if service not available
    if not workflow_service:
        import uuid
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        # Save to database
        workflow_data = {
            'id': workflow_id,
            'name': workflow_create.task_description[:30],
            'agent_id': workflow_create.agent_id,
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
        }

    # Create domain object for service
    agent = create_agent_from_db_data(agent_data)

    try:
        workflow = await workflow_service.create_workflow(
            task_description=workflow_create.task_description,
            agent=agent,
            available_tools=workflow_create.available_tools,
        )

        return {
            "workflow_id": workflow.id,
            "name": workflow.name,
            "steps_count": len(workflow.steps),
            "status": workflow.status.value,
        }
    except Exception as e:
        logger.error(f"Workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {str(e)}")


@app.post("/workflows/{workflow_id}/execute", tags=["Workflows"])
async def execute_workflow(workflow_id: str, agent_id: str = Query(...)):
    """Execute a workflow."""
    # Check if agent exists
    agent_data = db_get_agent(agent_id)
    if not agent_data:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Return mock result if service not available
    if not workflow_service:
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "result": {
                "output": "Workflow executed successfully",
                "steps_completed": 3,
                "execution_time": "2.5s",
            }
        }

    # Create domain object for service
    agent = create_agent_from_db_data(agent_data)

    try:
        result = await workflow_service.execute_workflow(
            workflow_id=workflow_id,
            agent=agent,
        )

        return {
            "workflow_id": result.workflow_id,
            "status": result.status.value,
            "total_steps": result.total_steps,
            "completed_steps": result.completed_steps,
            "failed_steps": result.failed_steps,
            "execution_time": result.execution_time,
            "step_results": result.step_results,
        }
    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@app.get("/workflows", tags=["Workflows"])
async def list_workflows():
    """List all workflows."""
    # Get from database
    workflows_data = db_get_workflows()

    if not workflows_data:
        # Return mock data if no workflows in database and service not available
        if not workflow_service:
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
        workflows = workflow_service.list_workflows()
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


# Metrics endpoint
@app.get("/metrics", tags=["System"])
async def get_metrics_endpoint():
    """Get system metrics."""
    # Get metrics from database
    db_metrics = db_get_metrics()

    metrics = {
        "agents_count": db_metrics.get('agents_count', 0),
        "environments_count": db_metrics.get('environments_count', 0),
        "ai_agents_count": db_metrics.get('ai_agents_count', 0),
        "services_count": db_metrics.get('active_services', 0),
        "demands_count": db_metrics.get('active_demands', 0),
        "opportunities_count": db_metrics.get('opportunities_count', 0),
        "negotiations_count": db_metrics.get('pending_negotiations', 0),
        "collaborations_count": db_metrics.get('collaborations_count', 0),
        "workflows_count": db_metrics.get('workflows_count', 0),
    }

    if source_manager:
        metrics["intelligence_sources"] = source_manager.get_metrics()

    return metrics


# ========== Active Matching API Endpoints ==========

# In-memory storage for matching (in production, use database)
opportunities_store: Dict[str, Any] = {}
negotiations_store: Dict[str, Any] = {}


class SearchDemandsRequest(BaseModel):
    """Schema for searching demands."""
    agent_id: str
    capabilities: List[str]
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class SearchSuppliersRequest(BaseModel):
    """Schema for searching suppliers."""
    agent_id: str
    required_skills: List[str]
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None


class NegotiationRequest(BaseModel):
    """Schema for initiating negotiation."""
    initiator_id: str
    counterpart_id: str
    context: Dict[str, Any]


class ProposalRequest(BaseModel):
    """Schema for submitting a proposal."""
    price: float
    delivery_time: str
    payment_terms: str
    quality_guarantee: str = ""


class NetworkExploreRequest(BaseModel):
    """Schema for network exploration."""
    agent_id: str
    target_capabilities: Optional[List[str]] = None
    exploration_depth: int = 2


class RecommendationRequest(BaseModel):
    """Schema for requesting recommendations."""
    agent_id: str
    target_capability: str


@app.post("/matching/search-demands", tags=["Active Matching"])
async def search_demands(request: SearchDemandsRequest):
    """Search for demands that match the agent's capabilities."""
    # Get agent info
    agent = db_get_ai_agent(request.agent_id) or db_get_agent(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get capabilities from agent or request
    capabilities = request.capabilities
    if not capabilities:
        capabilities = safe_json_loads(agent.get('capabilities', '[]'), [])

    # Build supply info
    supply_info = {
        "id": request.agent_id,
        "agent_id": request.agent_id,
        "capabilities": capabilities,
        "price": agent.get('hourly_rate', 100) if isinstance(agent, dict) else 100,
        "reputation": agent.get('reputation', 0.5) if isinstance(agent, dict) else 0.5,
        "availability": agent.get('availability', 'available') if isinstance(agent, dict) else 'available',
        "description": agent.get('bio', '') if isinstance(agent, dict) else '',
    }

    # Search demands from database
    demands_data = db_search_demands(
        capabilities=capabilities,
        budget_min=request.budget_min,
        budget_max=request.budget_max,
    )

    # Convert to dict format for matching engine
    demands = []
    for d in demands_data:
        demand_dict = {
            "id": d.get('id'),
            "agent_id": d.get('agent_id'),
            "title": d.get('title'),
            "description": d.get('description', ''),
            "required_skills": safe_json_loads(d.get('required_skills', '[]'), []),
            "budget_range": {
                "min": d.get('budget_min', 0),
                "max": d.get('budget_max', 10000),
            },
            "deadline": d.get('deadline'),
        }
        demands.append(demand_dict)

    # Use matching engine
    matches = await matching_engine.match_supply_to_demands(
        supply=supply_info,
        demands=demands,
        min_score=0.3,
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        demand = next((d for d in demands if d.get('id') == match.demand_id), None)
        if demand:
            # Get demand agent info
            demand_agent = db_get_agent(demand.get('agent_id', ''))
            results.append({
                "opportunity_id": match.match_id,
                "counterpart_agent_id": demand.get('agent_id', ''),
                "counterpart_name": demand_agent.get('name', 'Unknown') if demand_agent else 'Unknown',
                "opportunity_type": "demand",
                "details": demand,
                "match_score": match.score.to_dict(),
                "status": "discovered",
                "created_at": match.created_at,
            })

    return results


@app.post("/matching/search-suppliers", tags=["Active Matching"])
async def search_suppliers(request: SearchSuppliersRequest):
    """Search for suppliers that match the agent's requirements."""
    # Get demand from database
    demands = db_search_demands()
    agent_demands = [d for d in demands if d.get('agent_id') == request.agent_id]

    # Build demand info from request
    demand_info = {
        "id": request.agent_id,
        "agent_id": request.agent_id,
        "required_skills": request.required_skills,
        "budget_range": {
            "min": request.budget_min or 0,
            "max": request.budget_max or 10000,
        },
        "description": "",
    }

    # Get all AI agents as potential suppliers
    all_agents = db_get_all_ai_agents()

    # Filter for active agents with relevant capabilities
    suppliers = []
    for agent in all_agents:
        if agent.get('status') != 'offline':
            # Safe JSON parsing (handle double-encoded JSON)
            try:
                caps = agent.get('capabilities', '[]')
                if isinstance(caps, str):
                    agent_capabilities = json.loads(caps)
                    if isinstance(agent_capabilities, str):
                        agent_capabilities = json.loads(agent_capabilities)
                else:
                    agent_capabilities = caps or []
            except (json.JSONDecodeError, TypeError):
                agent_capabilities = []

            try:
                sks = agent.get('skills', '[]')
                if isinstance(sks, str):
                    agent_skills = json.loads(sks)
                    if isinstance(agent_skills, str):
                        agent_skills = json.loads(agent_skills)
                else:
                    agent_skills = sks or []
            except (json.JSONDecodeError, TypeError):
                agent_skills = []

            if any(cap.lower() in [c.lower() for c in agent_capabilities] for cap in request.required_skills):
                suppliers.append({
                    "id": agent.get('agent_id'),
                    "agent_id": agent.get('agent_id'),
                    "name": agent.get('name'),
                    "capabilities": agent_capabilities,
                    "skills": agent_skills,
                    "price": agent.get('stake', 100) / 10,  # Estimate price from stake
                    "reputation": agent.get('reputation', 0.5),
                    "availability": "available" if agent.get('status') == 'online' else "busy",
                    "description": "",
                })

    # Also check regular agents with services
    services_query = "SELECT * FROM services WHERE status = 'active'"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(services_query)
        services = cursor.fetchall()

        # Batch load all agents for services to avoid N+1 queries
        agent_ids = set()
        for service in services:
            service_dict = dict(service) if hasattr(service, 'keys') else service
            agent_id = service_dict.get('agent_id', '') if isinstance(service_dict, dict) else service['agent_id']
            if agent_id:
                agent_ids.add(agent_id)

        # Load all agents in one query
        agents_by_id: Dict[str, Any] = {}
        if agent_ids:
            placeholders = ','.join(['?' for _ in agent_ids])
            cursor.execute(f'SELECT * FROM ai_agents WHERE agent_id IN ({placeholders})', list(agent_ids))
            for row in cursor.fetchall():
                row_dict = dict(row)
                agents_by_id[row_dict['agent_id']] = row_dict

        for service in services:
            # Safe JSON parsing (sqlite3.Row doesn't have .get(), use dict())
            service_dict = dict(service) if hasattr(service, 'keys') else service
            try:
                sks = service_dict.get('skills', '[]') if isinstance(service_dict, dict) else service['skills']
                if isinstance(sks, str):
                    service_skills = json.loads(sks)
                    if isinstance(service_skills, str):
                        service_skills = json.loads(service_skills)
                else:
                    service_skills = sks or []
            except (json.JSONDecodeError, TypeError, KeyError):
                service_skills = []

            if any(cap.lower() in [s.lower() for s in service_skills] for cap in request.required_skills):
                # Check if not already added
                service_agent_id = service_dict.get('agent_id', '') if isinstance(service_dict, dict) else service['agent_id']
                if not any(s.get('id') == service_agent_id for s in suppliers):
                    # Get agent from pre-loaded cache
                    service_agent = agents_by_id.get(service_agent_id)
                    if service_agent:
                        suppliers.append({
                            "id": service_agent_id,
                            "agent_id": service_agent_id,
                            "name": service_agent.get('name', 'Unknown'),
                            "capabilities": service_skills,
                            "price": service_dict.get('price', 100) if isinstance(service_dict, dict) else service['price'],
                            "reputation": service_agent.get('reputation', 0.5),
                            "availability": "available",
                            "description": service_dict.get('description', '') if isinstance(service_dict, dict) else service['description'],
                        })

    # Use matching engine
    matches = await matching_engine.match_demand_to_supplies(
        demand=demand_info,
        supplies=suppliers,
        min_score=0.3,
        max_results=10,
    )

    # Format response
    results = []
    for match in matches:
        supply = next((s for s in suppliers if s.get('id') == match.supply_id), None)
        if supply:
            results.append({
                "opportunity_id": match.match_id,
                "counterpart_agent_id": supply.get('agent_id', ''),
                "counterpart_name": supply.get('name', 'Unknown'),
                "opportunity_type": "supply",
                "details": {
                    "capabilities": supply.get('capabilities', []),
                    "skills": supply.get('skills', []),
                    "price_per_request": supply.get('price', 100),
                    "reputation": supply.get('reputation', 0.5),
                },
                "match_score": match.score.to_dict(),
                "status": "discovered",
                "created_at": match.created_at,
            })

    return results


@app.post("/matching/negotiate", tags=["Active Matching"])
async def initiate_negotiation(request: NegotiationRequest):
    """Initiate a negotiation with another agent."""
    session_id = f"neg-{len(negotiations_store) + 1}"
    negotiation = {
        "session_id": session_id,
        "initiator_id": request.initiator_id,
        "counterpart_id": request.counterpart_id,
        "context": request.context,
        "status": "pending",
        "rounds": [],
        "final_terms": None,
        "created_at": datetime.now().timestamp(),
    }
    negotiations_store[session_id] = negotiation
    return negotiation


@app.get("/matching/negotiations", tags=["Active Matching"])
async def get_negotiations(agent_id: str = Query(...)):
    """Get all negotiations for an agent."""
    return [
        n for n in negotiations_store.values()
        if n["initiator_id"] == agent_id or n["counterpart_id"] == agent_id
    ]


@app.post("/matching/negotiations/{session_id}/proposal", tags=["Active Matching"])
async def submit_proposal(session_id: str, proposal: ProposalRequest):
    """Submit a proposal in a negotiation."""
    if session_id not in negotiations_store:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    negotiation = negotiations_store[session_id]
    round_number = len(negotiation["rounds"]) + 1

    negotiation["rounds"].append({
        "round_number": round_number,
        "proposer_id": "current_agent",
        "proposal": proposal.dict(),
        "response": "counter" if round_number < 3 else "accepted",
    })

    negotiation["status"] = "in_progress"
    return negotiation


@app.get("/matching/opportunities", tags=["Active Matching"])
async def get_opportunities(agent_id: str = Query(...)):
    """Get all opportunities for an agent."""
    # In production, filter by agent_id
    return []


@app.get("/matching/stats", tags=["Active Matching"])
async def get_matching_stats(agent_id: str = Query(...)):
    """Get matching statistics for an agent."""
    return {
        "total_opportunities": 12,
        "active_negotiations": 3,
        "successful_matches": 8,
        "pending_responses": 5,
    }


# ========== Network Explorer API Endpoints ==========

network_stats_store: Dict[str, Any] = {}


@app.post("/network/explore", tags=["Network Explorer"])
async def explore_network(request: NetworkExploreRequest):
    """Explore the network to discover new agents."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    discovered = []
    for agent in all_agents:
        # Skip the requesting agent
        if agent.get("agent_id") == request.agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agent.get("capabilities", "[]")) if isinstance(agent.get("capabilities"), str) else agent.get("capabilities", [])
        skills = json.loads(agent.get("skills", "[]")) if isinstance(agent.get("skills"), str) else agent.get("skills", [])

        # Filter by target capabilities if specified
        if request.target_capabilities:
            # Check if agent has any of the requested capabilities
            has_capability = any(
                any(tc.lower() in c.lower() for c in capabilities)
                for tc in request.target_capabilities
            )
            if not has_capability:
                continue

        discovered.append({
            "agent_id": agent.get("agent_id"),
            "agent_name": agent.get("name"),
            "capabilities": capabilities,
            "skills": skills,
            "reputation": agent.get("reputation", 0.5),
            "status": agent.get("status", "offline"),
        })

        # Limit results
        if len(discovered) >= 20:
            break

    return discovered


@app.post("/network/recommendations", tags=["Network Explorer"])
async def request_recommendations(request: RecommendationRequest):
    """Request recommendations from the network."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    recommendations = []
    for agent in all_agents:
        # Skip the requesting agent
        if agent.get("agent_id") == request.agent_id:
            continue

        # Parse capabilities
        capabilities = json.loads(agent.get("capabilities", "[]")) if isinstance(agent.get("capabilities"), str) else agent.get("capabilities", [])

        # Calculate capability match score
        capability_match = 0.0
        target_lower = request.target_capability.lower()
        for cap in capabilities:
            if isinstance(cap, str) and target_lower in cap.lower():
                capability_match = min(1.0, 0.7 + agent.get("reputation", 0.5) * 0.3)
                break

        # Skip if no capability match
        if capability_match == 0:
            continue

        trust_score = agent.get("reputation", 0.5)

        recommendations.append({
            "recommended_agent_id": agent.get("agent_id"),
            "recommended_agent_name": agent.get("name"),
            "capability_match": round(capability_match, 2),
            "trust_score": round(trust_score, 2),
            "reason": "High reputation agent with matching capabilities" if trust_score > 0.7 else "Matches your capability requirements",
        })

    # Sort by capability match then trust score
    recommendations.sort(key=lambda x: (x["capability_match"], x["trust_score"]), reverse=True)

    return recommendations[:10]


@app.get("/network/stats", tags=["Network Explorer"])
async def get_network_stats(agent_id: str = Query(...)):
    """Get network exploration statistics."""
    # Get all AI agents from database
    all_agents = db_get_all_ai_agents()

    total_agents = len(all_agents)
    active_agents = sum(1 for a in all_agents if a.get("status") == "online")

    # Calculate trusted agents (reputation >= 0.7)
    trusted_agents = sum(1 for a in all_agents if a.get("reputation", 0) >= 0.7)

    return {
        "total_explorations": total_agents,  # Total agents discovered
        "total_discovered": total_agents,
        "network_size": active_agents,  # Currently active agents
        "trusted_agents": trusted_agents,
    }


# ========== Collaborative Matching API Endpoints ==========


class CollaborationCreateRequest(BaseModel):
    """Schema for creating a collaboration."""
    goal_description: str
    required_skills: List[str]
    collaboration_mode: str = "hybrid"
    coordinator_agent_id: str


class CollaborationRoleAssignRequest(BaseModel):
    """Schema for assigning a role."""
    role_id: str
    agent_id: str


@app.post("/collaborations", tags=["Collaborations"])
async def create_collaboration_endpoint(request: CollaborationCreateRequest):
    """Create a new collaboration session."""
    session_id = f"collab-{int(datetime.now().timestamp() * 1000)}"

    # Create goal data
    goal_data = {
        "id": f"goal-{session_id}",
        "name": "Collaboration Goal",
        "description": request.goal_description,
    }

    # Create plan data
    plan_data = {
        "plan_id": f"plan-{session_id}",
        "mode": request.collaboration_mode,
        "roles": [
            {
                "role_id": f"role-{i}",
                "role_type": role_type,
                "required_skills": [request.required_skills[i]] if i < len(request.required_skills) else [],
                "status": "pending",
            }
            for i, role_type in enumerate(["primary", "specialist", "support"])
        ],
    }

    # Save to database
    collab_data = {
        "session_id": session_id,
        "goal": json.dumps(goal_data),
        "plan": plan_data,
        "participants": [],
        "status": "analyzing",
        "coordinator_id": request.coordinator_agent_id,
    }

    db_create_collaboration(collab_data)

    return {
        "session_id": session_id,
        "goal": goal_data,
        "plan": plan_data,
        "status": "analyzing",
        "participants": [],
        "coordinator_id": request.coordinator_agent_id,
    }


@app.get("/collaborations", tags=["Collaborations"])
async def get_collaborations_endpoint(status: Optional[str] = Query(None)):
    """Get all collaboration sessions."""
    sessions = db_get_collaborations()

    # Parse JSON fields
    result = []
    for s in sessions:
        session_data = dict(s)
        if isinstance(session_data.get('goal'), str):
            session_data['goal'] = json.loads(session_data['goal'])
        if isinstance(session_data.get('plan'), str):
            session_data['plan'] = json.loads(session_data['plan'])
        if isinstance(session_data.get('participants'), str):
            session_data['participants'] = json.loads(session_data['participants'])

        # Filter by status if provided
        if status and session_data.get('status') != status:
            continue
        result.append(session_data)

    return result


@app.get("/collaborations/{session_id}", tags=["Collaborations"])
async def get_collaboration_endpoint(session_id: str):
    """Get a specific collaboration session."""
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    session_data = dict(session)
    if isinstance(session_data.get('goal'), str):
        session_data['goal'] = json.loads(session_data['goal'])
    if isinstance(session_data.get('plan'), str):
        session_data['plan'] = json.loads(session_data['plan'])
    if isinstance(session_data.get('participants'), str):
        session_data['participants'] = json.loads(session_data['participants'])

    return session_data


@app.post("/collaborations/{session_id}/execute", tags=["Collaborations"])
async def execute_collaboration(session_id: str):
    """Execute a collaboration session."""
    session = db_get_collaboration(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    # Update status in database
    # Note: Would need to add update_collaboration function to database.py
    session_data = dict(session)
    session_data["status"] = "executing"
    session_data["started_at"] = datetime.now().timestamp()

    return session_data


@app.get("/collaborations/stats", tags=["Collaborations"])
async def get_collaboration_stats():
    """Get collaboration statistics."""
    sessions = db_get_collaborations()

    total = len(sessions)
    active = sum(1 for s in sessions if s.get("status") in ["analyzing", "organizing", "executing", "integrating"])
    completed = sum(1 for s in sessions if s.get("status") == "completed")
    failed = sum(1 for s in sessions if s.get("status") == "failed")

    return {
        "total_sessions": total,
        "active_sessions": active,
        "completed_sessions": completed,
        "failed_sessions": failed,
        "success_rate": completed / total if total > 0 else 0,
    }


# ========== Proactive Learning API Endpoints ==========

learning_store: Dict[str, Any] = {}


@app.post("/learning/analyze", tags=["Proactive Learning"])
async def analyze_agent_learning(agent_id: str = Query(...)):
    """Analyze agent's match history for learning insights."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)

        return {
            "agent_id": agent_id,
            "insights_count": len(capabilities),
            "success_patterns": [f"Strong performance in {cap}" for cap in capabilities[:3]] if capabilities else ["No historical patterns yet"],
            "recommendations": [
                "Build reputation through successful transactions",
                f"Leverage your {', '.join(capabilities[:2])} capabilities" if len(capabilities) >= 2 else "Add more capabilities to your profile",
            ],
            "reputation": reputation,
            "status": agent_data.get("status", "unknown"),
        }

    return {
        "agent_id": agent_id,
        "insights_count": 0,
        "success_patterns": [],
        "recommendations": ["Register as an agent to start learning"],
    }


@app.get("/learning/insights/{agent_id}", tags=["Proactive Learning"])
async def get_learning_insights(agent_id: str):
    """Get learning insights for an agent."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    insights = []
    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)

        for i, cap in enumerate(capabilities[:5]):
            insights.append({
                "insight_id": f"insight-{i+1}",
                "category": "capability_analysis",
                "title": f"{cap} Performance",
                "description": f"Your {cap} capability has a reputation score of {reputation:.0%}",
                "confidence": reputation,
            })

    return {
        "agent_id": agent_id,
        "insights": insights if insights else [{"insight_id": "none", "category": "info", "title": "No insights yet", "description": "Complete transactions to generate insights", "confidence": 0.0}],
    }


@app.get("/learning/strategy/{agent_id}", tags=["Proactive Learning"])
async def get_optimized_strategy(agent_id: str):
    """Get optimized matching strategy for an agent."""
    # Get agent data from database
    agent_data = db_get_ai_agent(agent_id)
    if not agent_data:
        agent_data = db_get_agent(agent_id)

    if agent_data:
        capabilities = json.loads(agent_data.get("capabilities", "[]")) if isinstance(agent_data.get("capabilities"), str) else agent_data.get("capabilities", [])
        reputation = agent_data.get("reputation", 0.5)
        stake = agent_data.get("stake", 0)

        # Calculate optimal price range based on reputation and stake
        min_price = max(10, int(stake * 0.1))
        max_price = max(min_price + 50, int(stake * 0.5))

        return {
            "agent_id": agent_id,
            "strategy": {
                "preferred_partner_types": ["human", "ai_agent"],
                "optimal_price_range": {"min": min_price, "max": max_price},
                "recommended_negotiation_strategy": "balanced" if reputation > 0.5 else "conservative",
                "best_contact_timing": "anytime",
                "focus_capabilities": capabilities[:3] if capabilities else [],
            },
        }

    return {
        "agent_id": agent_id,
        "strategy": {
            "preferred_partner_types": [],
            "optimal_price_range": {"min": 0, "max": 0},
            "recommended_negotiation_strategy": "none",
            "best_contact_timing": "none",
        },
    }


@app.get("/learning/market/{agent_id}", tags=["Proactive Learning"])
async def get_market_insight(agent_id: str):
    """Get market insights for an agent."""
    # Get environment state for market insights
    all_agents = db_get_all_ai_agents()
    metrics = db_get_metrics()

    total_agents = len(all_agents)
    active_demands = metrics.get('active_demands', 0)
    active_services = metrics.get('active_services', 0)

    # Calculate supply/demand ratio
    supply_demand_ratio = 1.0
    if active_demands > 0:
        supply_demand_ratio = round(active_services / active_demands, 2)

    # Determine market state
    if supply_demand_ratio > 1.5:
        demand_level = "low"
        supply_level = "high"
    elif supply_demand_ratio < 0.7:
        demand_level = "high"
        supply_level = "low"
    else:
        demand_level = "medium"
        supply_level = "medium"

    # Extract hot skills
    skill_counts: Dict[str, int] = {}
    for agent in all_agents:
        skills = json.loads(agent.get('skills', '[]')) if isinstance(agent.get('skills'), str) else agent.get('skills', [])
        for skill in skills:
            skill_name = skill if isinstance(skill, str) else skill.get('name', '')
            if skill_name:
                skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1

    hot_skills = sorted(skill_counts.keys(), key=lambda x: skill_counts[x], reverse=True)[:5]

    return {
        "agent_id": agent_id,
        "demand_level": demand_level,
        "supply_level": supply_level,
        "opportunity_areas": hot_skills if hot_skills else ["No data yet"],
        "recommendations": [f"Consider offering {skill} services" for skill in hot_skills[:2]] if hot_skills else ["Register to see personalized recommendations"],
        "total_agents": total_agents,
        "active_demands": active_demands,
        "active_services": active_services,
    }


def run_server():
    """Run the API server."""
    import uvicorn
    uvicorn.run(
        "usmsb_sdk.api.rest.main:app",
        host=settings.api.host if settings else "0.0.0.0",
        port=settings.api.port if settings else 8000,
        reload=settings.api.debug if settings else False,
    )



# ========== AI Agent Registration API Endpoints ==========

# In-memory storage for registered agents
ai_agents_store: Dict[str, Any] = {}


class AgentRegistrationRequest(BaseModel):
    """Schema for AI Agent registration."""
    agent_id: str
    name: str
    agent_type: str = "ai_agent"
    capabilities: List[str]
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    endpoint: str
    protocol: str  # "mcp", "a2a", "skill_md"
    stake: float = 0.0
    description: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPRegistrationRequest(BaseModel):
    """Schema for MCP protocol registration."""
    agent_id: str
    name: str
    mcp_endpoint: str
    capabilities: List[str]
    stake: float = 0.0


class A2ARegistrationRequest(BaseModel):
    """Schema for A2A protocol registration."""
    agent_card: Dict[str, Any]
    endpoint: str


class SkillMDRegistrationRequest(BaseModel):
    """Schema for skill.md registration."""
    skill_url: str
    agent_id: str = ""


@app.post("/agents/register", tags=["AI Agent Registration"])
async def register_ai_agent(request: AgentRegistrationRequest):
    """Register an AI Agent to the platform."""
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": request.agent_id,
        "name": request.name,
        "agent_type": request.agent_type,
        "capabilities": json.dumps(request.capabilities),
        "skills": json.dumps(request.skills),
        "endpoint": request.endpoint,
        "protocol": request.protocol,
        "stake": request.stake,
        "description": request.description,
        "metadata": json.dumps(request.metadata),
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": request.agent_id,
        "message": "Agent registered successfully",
    }


@app.post("/agents/register/mcp", tags=["AI Agent Registration"])
async def register_via_mcp(request: MCPRegistrationRequest):
    """Register an AI Agent via MCP protocol."""
    agent_id = request.agent_id or f"mcp-{uuid.uuid4().hex[:8]}"
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": request.name,
        "agent_type": "ai_agent",
        "capabilities": json.dumps(request.capabilities),
        "skills": "[]",
        "endpoint": request.mcp_endpoint,
        "protocol": "mcp",
        "stake": request.stake,
        "description": f"MCP agent: {request.name}",
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via MCP protocol",
    }


@app.post("/agents/register/a2a", tags=["AI Agent Registration"])
async def register_via_a2a(request: A2ARegistrationRequest):
    """Register an AI Agent via A2A protocol."""
    agent_card = request.agent_card
    agent_id = agent_card.get("agent_id", f"a2a-{uuid.uuid4().hex[:8]}")
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": agent_card.get("name", "Unknown"),
        "agent_type": "ai_agent",
        "capabilities": json.dumps(agent_card.get("capabilities", [])),
        "skills": json.dumps(agent_card.get("skills", [])),
        "endpoint": request.endpoint,
        "protocol": "a2a",
        "stake": 0.0,
        "description": agent_card.get("description", ""),
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via A2A protocol",
    }


@app.post("/agents/register/skill-md", tags=["AI Agent Registration"])
async def register_via_skill_md(request: SkillMDRegistrationRequest):
    """Register an AI Agent via skill.md."""
    # In production, this would fetch and parse skill.md
    agent_id = request.agent_id or f"skill-{uuid.uuid4().hex[:8]}"
    now = datetime.now().timestamp()
    agent_data = {
        "agent_id": agent_id,
        "name": f"Agent from {request.skill_url}",
        "agent_type": "ai_agent",
        "capabilities": json.dumps(["general"]),
        "skills": "[]",
        "endpoint": request.skill_url,
        "protocol": "skill_md",
        "skill_url": request.skill_url,
        "stake": 0.0,
        "description": "Agent registered via skill.md",
        "metadata": "{}",
        "status": "online",
        "reputation": 0.5,
        "registered_at": now,
        "last_heartbeat": now,
    }
    # Save to database
    db_create_ai_agent(agent_data)
    return {
        "success": True,
        "agent_id": agent_id,
        "message": "Agent registered via skill.md",
    }


@app.post("/agents/{agent_id}/heartbeat", tags=["AI Agent Registration"])
async def agent_heartbeat_endpoint(agent_id: str, status: str = "online"):
    """AI Agent sends heartbeat to stay active."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update heartbeat in database
    db_update_ai_agent_heartbeat(agent_id, status)
    return {"success": True, "message": "Heartbeat received"}


@app.get("/agents", tags=["AI Agent Registration"])
async def list_ai_agents(status: Optional[str] = Query(None)):
    """List all registered AI Agents."""
    # Get from database
    agents_data = db_get_all_ai_agents(status=status)

    result = []
    for a in agents_data:
        result.append({
            "agent_id": a.get("agent_id"),
            "name": a.get("name"),
            "agent_type": a.get("agent_type"),
            "capabilities": json.loads(a.get("capabilities", "[]")),
            "skills": json.loads(a.get("skills", "[]")),
            "endpoint": a.get("endpoint"),
            "protocol": a.get("protocol"),
            "stake": a.get("stake", 0),
            "description": a.get("description", ""),
            "metadata": json.loads(a.get("metadata", "{}")),
            "status": a.get("status", "offline"),
            "reputation": a.get("reputation", 0.5),
            "registered_at": a.get("registered_at"),
            "last_heartbeat": a.get("last_heartbeat"),
        })
    return result


@app.get("/agents/{agent_id}", tags=["AI Agent Registration"])
async def get_ai_agent_endpoint(agent_id: str):
    """Get details of a specific AI Agent."""
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent.get("agent_id"),
        "name": agent.get("name"),
        "agent_type": agent.get("agent_type"),
        "capabilities": json.loads(agent.get("capabilities", "[]")),
        "skills": json.loads(agent.get("skills", "[]")),
        "endpoint": agent.get("endpoint"),
        "protocol": agent.get("protocol"),
        "stake": agent.get("stake", 0),
        "description": agent.get("description", ""),
        "metadata": json.loads(agent.get("metadata", "{}")),
        "status": agent.get("status", "offline"),
        "reputation": agent.get("reputation", 0.5),
        "registered_at": agent.get("registered_at"),
        "last_heartbeat": agent.get("last_heartbeat"),
    }


@app.delete("/agents/{agent_id}", tags=["AI Agent Registration"])
async def unregister_ai_agent(agent_id: str):
    """Unregister an AI Agent."""
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Delete from database
    db_delete_ai_agent(agent_id)
    return {"success": True, "message": "Agent unregistered"}


class AgentTestRequest(BaseModel):
    """Schema for testing an agent."""
    input: str
    context: Dict[str, Any] = Field(default_factory=dict)


@app.post("/agents/{agent_id}/test", tags=["AI Agent Registration"])
async def test_ai_agent(agent_id: str, request: AgentTestRequest):
    """Test an AI Agent by sending a test input."""
    import httpx

    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    endpoint = agent.get("endpoint")
    protocol = agent.get("protocol", "standard")

    start_time = time.time()
    test_result = {
        "agent_id": agent_id,
        "protocol": protocol,
        "endpoint": endpoint,
        "input": request.input,
        "success": False,
        "response": None,
        "error": None,
        "latency_ms": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try different endpoints based on protocol
            if protocol == "mcp":
                # MCP uses SSE or specific endpoints
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )
            elif protocol == "a2a":
                # A2A protocol
                response = await client.post(
                    f"{endpoint}/message",
                    json={"content": request.input, "context": request.context},
                )
            else:
                # Standard REST endpoint
                response = await client.post(
                    f"{endpoint}/invoke",
                    json={"input": request.input, "context": request.context},
                )

            end_time = time.time()
            test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)

            if response.status_code == 200:
                try:
                    test_result["response"] = response.json()
                except (json.JSONDecodeError, ValueError):
                    test_result["response"] = response.text
                test_result["success"] = True
            else:
                test_result["error"] = f"HTTP {response.status_code}: {response.text[:500]}"

    except httpx.TimeoutException:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = "Request timed out after 30 seconds"
    except httpx.ConnectError as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Connection failed: {str(e)}"
    except Exception as e:
        end_time = time.time()
        test_result["latency_ms"] = round((end_time - start_time) * 1000, 2)
        test_result["error"] = f"Error: {str(e)}"

    return test_result


@app.post("/agents/{agent_id}/services", tags=["AI Agent Services"])
async def register_agent_service(
    agent_id: str,
    service_type: str,
    service_name: str,
    capabilities: List[str],
    price: float,
):
    """Register a service provided by an AI Agent."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    service_data = {
        "agent_id": agent_id,
        "service_name": service_name,
        "description": f"Service: {service_name}",
        "category": service_type,
        "skills": json.dumps(capabilities),
        "price": price,
        "price_type": "hourly",
        "availability": "24/7",
    }

    # Save to database
    service = db_create_service(service_data)

    return {"success": True, "service": service}


@app.get("/services", tags=["Services"])
async def list_services(
    agent_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """List all services."""
    with get_db() as conn:
        cursor = conn.cursor()
        query = 'SELECT * FROM services WHERE status = "active"'
        params = []

        if agent_id:
            query += ' AND agent_id = ?'
            params.append(agent_id)
        if category:
            query += ' AND category = ?'
            params.append(category)

        query += f' LIMIT {limit}'
        cursor.execute(query, params)
        services = [dict(row) for row in cursor.fetchall()]

    result = []
    for s in services:
        result.append({
            "id": s.get('id'),
            "agent_id": s.get('agent_id'),
            "service_name": s.get('service_name'),
            "description": s.get('description'),
            "category": s.get('category'),
            "skills": json.loads(s.get('skills', '[]')),
            "price": s.get('price'),
            "price_type": s.get('price_type'),
            "status": s.get('status'),
            "created_at": s.get('created_at'),
        })
    return result


@app.post("/agents/{agent_id}/stake", tags=["AI Agent Staking"])
async def agent_stake_endpoint(agent_id: str, amount: float):
    """Stake VIBE tokens for an AI Agent."""
    # Check if agent exists
    agent = db_get_ai_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Update stake in database
    db_update_ai_agent_stake(agent_id, amount)

    # Get updated agent data
    updated_agent = db_get_ai_agent(agent_id)
    current_stake = updated_agent.get("stake", 0)

    # Calculate reputation based on stake
    reputation = min(0.5 + (current_stake / 1000), 1.0)

    return {
        "success": True,
        "total_stake": current_stake,
        "reputation": reputation,
    }


if __name__ == "__main__":
    run_server()

