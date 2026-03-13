# USMSB SDK API Reference

**Universal System Model of Social Behavior - API Interface Documentation**

Version: 1.0.0

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication](#2-authentication)
3. [REST API Endpoints](#3-rest-api-endpoints)
4. [WebSocket API](#4-websocket-api)
5. [Python SDK Reference](#5-python-sdk-reference)
6. [External Integration APIs](#6-external-integration-apis)
7. [Error Codes](#7-error-codes)
8. [Rate Limits](#8-rate-limits)

---

## 1. Overview

### 1.1 Base URL

> **Note**: The following URLs are example URLs. Replace with your platform address in actual deployment.

```
Production: https://api.usmsb-sdk.io/v1  (example)
Development: https://dev-api.usmsb-sdk.io/v1  (example)
Local Development: http://localhost:8000/v1
```

### 1.2 API Versioning

The API uses URL-based versioning. All endpoints are prefixed with the version number (e.g., `/v1/`).

### 1.3 Content Type

All API requests and responses use JSON format:

```
Content-Type: application/json
```

### 1.4 Response Format

All API responses follow a standard format:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

Error response format:

```json
{
  "success": false,
  "error": {
    "code": "USMSB_ERROR_CODE",
    "message": "Human readable error message",
    "details": { ... }
  },
  "meta": {
    "timestamp": "2025-01-15T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

---

## 2. Authentication

### 2.1 API Key Authentication

USMSB SDK uses API keys for authentication. Include your API key in the request header:

```http
Authorization: Bearer YOUR_API_KEY
X-API-Key: YOUR_API_KEY
```

### 2.2 Obtaining an API Key

> **Note**: The following is an example flow. Refer to your platform deployment configuration for actual operations.

1. Register at USMSB Developer Portal (if deployed)
2. Create a new application
3. Generate an API key from the dashboard

Or use the default API key provided by the platform for testing.

### 2.3 API Key Types

| Key Type | Description | Rate Limit |
|----------|-------------|------------|
| `development` | For testing and development | 100 req/min |
| `production` | For production applications | 1000 req/min |
| `enterprise` | Custom limits for enterprise clients | Custom |

### 2.4 OAuth 2.0 (Optional)

For applications requiring user-specific access:

```http
POST /oauth/token
Content-Type: application/json

{
  "grant_type": "client_credentials",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scope": "read write"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "read write"
}
```

---

## 3. REST API Endpoints

### 3.1 Agent Management

#### 3.1.1 Create Agent

Creates a new Agent instance.

```http
POST /v1/agents
```

**Request Body:**

```json
{
  "name": "string",
  "type": "human | ai_agent | organization",
  "capabilities": ["string"],
  "state": {
    "key": "value"
  },
  "goals": [
    {
      "name": "string",
      "description": "string",
      "priority": 0
    }
  ],
  "resources": [
    {
      "name": "string",
      "type": "tangible | intangible",
      "quantity": 0
    }
  ],
  "rules": [
    {
      "name": "string",
      "type": "legal | social | algorithmic",
      "scope": ["string"]
    }
  ],
  "metadata": {
    "key": "value"
  }
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "agent_abc123",
    "name": "Alice",
    "type": "human",
    "capabilities": ["learn", "decide", "interact"],
    "state": {},
    "goals": [],
    "resources": [],
    "rules": [],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

#### 3.1.2 Get Agent

Retrieves an Agent by ID.

```http
GET /v1/agents/{agent_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Unique Agent identifier |

**Response:** `200 OK`

```json
{
  "success": true,
  "data": {
    "id": "agent_abc123",
    "name": "Alice",
    "type": "human",
    "capabilities": ["learn", "decide"],
    "state": {},
    "goals": [
      {
        "id": "goal_xyz",
        "name": "Complete Project",
        "description": "Finish the quarterly project",
        "priority": 1,
        "status": "in_progress"
      }
    ],
    "resources": [],
    "rules": [],
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:35:00Z"
  }
}
```

#### 3.1.3 List Agents

Retrieves a list of Agents with optional filtering.

```http
GET /v1/agents
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | - | Filter by agent type |
| `capability` | string | - | Filter by capability |
| `limit` | integer | 20 | Number of results per page |
| `offset` | integer | 0 | Pagination offset |
| `sort_by` | string | created_at | Sort field |
| `sort_order` | string | desc | Sort order (asc/desc) |

**Response:** `200 OK`

```json
{
  "success": true,
  "data": {
    "agents": [...],
    "pagination": {
      "total": 100,
      "limit": 20,
      "offset": 0,
      "has_more": true
    }
  }
}
```

#### 3.1.4 Update Agent

Updates an existing Agent.

```http
PATCH /v1/agents/{agent_id}
```

**Request Body:**

```json
{
  "name": "string",
  "capabilities": ["string"],
  "state": {
    "key": "value"
  }
}
```

**Response:** `200 OK`

#### 3.1.5 Delete Agent

Deletes an Agent.

```http
DELETE /v1/agents/{agent_id}
```

**Response:** `204 No Content`

---

### 3.2 Environment Management

#### 3.2.1 Create Environment

```http
POST /v1/environments
```

**Request Body:**

```json
{
  "name": "string",
  "type": "natural | social | technological | economic",
  "state": {
    "key": "value"
  },
  "influencing_factors": ["string"]
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "env_xyz789",
    "name": "Smart City",
    "type": "technological",
    "state": {
      "traffic_flow": "normal",
      "temperature": 25
    },
    "influencing_factors": ["weather", "events", "time_of_day"],
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### 3.2.2 Get Environment

```http
GET /v1/environments/{environment_id}
```

#### 3.2.3 List Environments

```http
GET /v1/environments
```

#### 3.2.4 Update Environment State

```http
PATCH /v1/environments/{environment_id}/state
```

**Request Body:**

```json
{
  "state": {
    "traffic_flow": "heavy"
  }
}
```

---

### 3.3 Goal Management

#### 3.3.1 Create Goal

```http
POST /v1/agents/{agent_id}/goals
```

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "priority": 0,
  "deadline": "2025-12-31T23:59:59Z",
  "sub_goals": [
    {
      "name": "string",
      "description": "string"
    }
  ]
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "goal_abc123",
    "name": "Reduce Commute Time",
    "description": "Optimize daily commute to save time",
    "priority": 1,
    "status": "pending",
    "progress": 0,
    "deadline": "2025-12-31T23:59:59Z",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### 3.3.2 Update Goal Status

```http
PATCH /v1/agents/{agent_id}/goals/{goal_id}/status
```

**Request Body:**

```json
{
  "status": "in_progress | completed | cancelled"
}
```

#### 3.3.3 Get Goal Progress

```http
GET /v1/agents/{agent_id}/goals/{goal_id}/progress
```

**Response:**

```json
{
  "success": true,
  "data": {
    "goal_id": "goal_abc123",
    "status": "in_progress",
    "progress": 0.65,
    "sub_goals": [
      {
        "id": "subgoal_1",
        "name": "Research routes",
        "status": "completed",
        "progress": 1.0
      },
      {
        "id": "subgoal_2",
        "name": "Test alternatives",
        "status": "in_progress",
        "progress": 0.3
      }
    ],
    "estimated_completion": "2025-03-15T00:00:00Z"
  }
}
```

---

### 3.4 Resource Management

#### 3.4.1 Create Resource

```http
POST /v1/agents/{agent_id}/resources
```

**Request Body:**

```json
{
  "name": "string",
  "type": "tangible | intangible",
  "quantity": 0,
  "unit": "string",
  "value": 0
}
```

#### 3.4.2 Allocate Resource

Allocates a resource to an agent or task.

```http
POST /v1/resources/{resource_id}/allocate
```

**Request Body:**

```json
{
  "target_agent_id": "string",
  "quantity": 0,
  "purpose": "string"
}
```

#### 3.4.3 Transfer Resource

Transfers a resource between agents.

```http
POST /v1/resources/{resource_id}/transfer
```

**Request Body:**

```json
{
  "from_agent_id": "string",
  "to_agent_id": "string",
  "quantity": 0
}
```

---

### 3.5 Rule Management

#### 3.5.1 Create Rule

```http
POST /v1/rules
```

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "type": "legal | social | algorithmic",
  "scope": ["string"],
  "priority": 0,
  "conditions": [
    {
      "field": "string",
      "operator": "eq | neq | gt | lt | gte | lte",
      "value": "any"
    }
  ],
  "actions": [
    {
      "type": "allow | deny | modify",
      "params": {}
    }
  ]
}
```

#### 3.5.2 Evaluate Rules

Evaluates rules against a given context.

```http
POST /v1/rules/evaluate
```

**Request Body:**

```json
{
  "agent_id": "string",
  "action": "string",
  "context": {
    "key": "value"
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "allowed": true,
    "matched_rules": [
      {
        "id": "rule_123",
        "name": "Business Hours Rule",
        "action": "allow"
      }
    ],
    "violations": []
  }
}
```

---

### 3.6 Information Management

#### 3.6.1 Create Information

```http
POST /v1/information
```

**Request Body:**

```json
{
  "content": "any",
  "type": "text | image | data | event",
  "source": "string",
  "quality": 1.0,
  "tags": ["string"]
}
```

#### 3.6.2 Query Information

```http
GET /v1/information
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | Information type |
| `source` | string | Source identifier |
| `tags` | string | Comma-separated tags |
| `from` | datetime | Start timestamp |
| `to` | datetime | End timestamp |
| `min_quality` | float | Minimum quality score |

#### 3.6.3 Search Information (Semantic)

Performs semantic search using vector embeddings.

```http
POST /v1/information/search
```

**Request Body:**

```json
{
  "query": "string",
  "limit": 10,
  "filters": {
    "type": "text",
    "tags": ["important"]
  }
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": "info_abc123",
        "content": "...",
        "relevance_score": 0.95,
        "source": "sensor_network",
        "timestamp": "2025-01-15T10:30:00Z"
      }
    ]
  }
}
```

---

### 3.7 Decision Services

#### 3.7.1 Request Decision

Requests a decision from the decision support service.

```http
POST /v1/decisions
```

**Request Body:**

```json
{
  "agent_id": "string",
  "goal_id": "string",
  "context": {
    "environment_id": "string",
    "constraints": ["string"],
    "preferences": {}
  },
  "options": [
    {
      "id": "option_1",
      "name": "Option A",
      "description": "string"
    }
  ],
  "criteria": [
    {
      "name": "cost",
      "weight": 0.3
    },
    {
      "name": "time",
      "weight": 0.7
    }
  ]
}
```

**Response:** `200 OK`

```json
{
  "success": true,
  "data": {
    "decision_id": "dec_xyz789",
    "recommended_option": {
      "id": "option_1",
      "name": "Option A",
      "score": 0.85
    },
    "analysis": {
      "option_1": {
        "score": 0.85,
        "breakdown": {
          "cost": 0.7,
          "time": 0.95
        }
      },
      "option_2": {
        "score": 0.72,
        "breakdown": {
          "cost": 0.9,
          "time": 0.6
        }
      }
    },
    "reasoning": "Option A is recommended because...",
    "confidence": 0.85,
    "risks": [
      {
        "type": "execution",
        "probability": 0.2,
        "impact": "medium"
      }
    ]
  }
}
```

#### 3.7.2 Get Decision History

```http
GET /v1/agents/{agent_id}/decisions
```

---

### 3.8 Behavior Prediction

#### 3.8.1 Predict Behavior

Predicts future behavior of an agent.

```http
POST /v1/predictions/behavior
```

**Request Body:**

```json
{
  "agent_id": "string",
  "environment_id": "string",
  "goal_id": "string",
  "time_horizon": "1h | 24h | 7d | 30d",
  "include_alternatives": true
}
```

**Response:** `200 OK`

```json
{
  "success": true,
  "data": {
    "prediction_id": "pred_abc123",
    "agent_id": "agent_xyz",
    "predicted_actions": [
      {
        "sequence": 1,
        "action": "search_routes",
        "probability": 0.9,
        "expected_time": "2025-01-15T11:00:00Z"
      },
      {
        "sequence": 2,
        "action": "compare_options",
        "probability": 0.85,
        "expected_time": "2025-01-15T11:15:00Z"
      },
      {
        "sequence": 3,
        "action": "make_decision",
        "probability": 0.8,
        "expected_time": "2025-01-15T11:30:00Z"
      }
    ],
    "alternative_scenarios": [
      {
        "scenario": "traffic_jam",
        "probability": 0.3,
        "modified_actions": [...]
      }
    ],
    "confidence": 0.82,
    "factors": [
      {
        "name": "historical_behavior",
        "weight": 0.5
      },
      {
        "name": "environment_state",
        "weight": 0.3
      },
      {
        "name": "goal_urgency",
        "weight": 0.2
      }
    ]
  }
}
```

#### 3.8.2 Predict System Evolution

Predicts the evolution of the entire system.

```http
POST /v1/predictions/system
```

**Request Body:**

```json
{
  "environment_id": "string",
  "agent_ids": ["string"],
  "simulation_steps": 100,
  "variables": ["traffic_flow", "resource_consumption"]
}
```

---

### 3.9 System Simulation

#### 3.9.1 Create Simulation

```http
POST /v1/simulations
```

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "environment_id": "string",
  "agent_ids": ["string"],
  "parameters": {
    "duration": 3600,
    "time_step": 60,
    "random_seed": 42
  },
  "initial_state": {
    "key": "value"
  }
}
```

**Response:** `201 Created`

```json
{
  "success": true,
  "data": {
    "id": "sim_abc123",
    "name": "Traffic Simulation",
    "status": "created",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### 3.9.2 Start Simulation

```http
POST /v1/simulations/{simulation_id}/start
```

#### 3.9.3 Stop Simulation

```http
POST /v1/simulations/{simulation_id}/stop
```

#### 3.9.4 Get Simulation Status

```http
GET /v1/simulations/{simulation_id}/status
```

**Response:**

```json
{
  "success": true,
  "data": {
    "id": "sim_abc123",
    "status": "running",
    "progress": 0.45,
    "current_step": 45,
    "total_steps": 100,
    "elapsed_time": 120,
    "estimated_remaining": 150
  }
}
```

#### 3.9.5 Get Simulation Results

```http
GET /v1/simulations/{simulation_id}/results
```

**Response:**

```json
{
  "success": true,
  "data": {
    "simulation_id": "sim_abc123",
    "status": "completed",
    "summary": {
      "total_events": 15000,
      "unique_interactions": 500,
      "emergent_patterns": 3
    },
    "metrics": {
      "average_agent_satisfaction": 0.75,
      "resource_efficiency": 0.82,
      "goal_completion_rate": 0.68
    },
    "emergent_behaviors": [
      {
        "pattern": "route_optimization_cascade",
        "description": "Agents began sharing route information...",
        "significance": "high"
      }
    ],
    "timeline": [
      {
        "step": 0,
        "state": {...}
      },
      {
        "step": 100,
        "state": {...}
      }
    ]
  }
}
```

---

### 3.10 Workflow Management

#### 3.10.1 Create Workflow

```http
POST /v1/workflows
```

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "trigger": {
    "type": "event | schedule | manual",
    "config": {}
  },
  "steps": [
    {
      "id": "step_1",
      "name": "Perception",
      "type": "perception",
      "config": {
        "input_source": "environment"
      }
    },
    {
      "id": "step_2",
      "name": "Decision",
      "type": "decision",
      "depends_on": ["step_1"],
      "config": {
        "strategy": "multi_criteria"
      }
    },
    {
      "id": "step_3",
      "name": "Execution",
      "type": "execution",
      "depends_on": ["step_2"],
      "config": {
        "timeout": 300
      }
    }
  ],
  "error_handling": {
    "strategy": "retry | skip | abort",
    "max_retries": 3
  }
}
```

#### 3.10.2 Execute Workflow

```http
POST /v1/workflows/{workflow_id}/execute
```

**Request Body:**

```json
{
  "agent_id": "string",
  "input": {
    "key": "value"
  }
}
```

#### 3.10.3 Get Workflow Execution Status

```http
GET /v1/workflows/{workflow_id}/executions/{execution_id}
```

---

## 4. WebSocket API

### 4.1 Connection

Connect to the WebSocket endpoint for real-time communication:

```
wss://api.usmsb-sdk.io/v1/ws  (example)
Local Development: ws://localhost:8000/v1/ws
```

**Authentication:**

Include the API key in the connection URL or as the first message:

```javascript
// Example
const ws = new WebSocket('wss://api.usmsb-sdk.io/v1/ws?api_key=YOUR_API_KEY');
// Local Development
const wsLocal = new WebSocket('ws://localhost:8000/v1/ws?api_key=YOUR_API_KEY');
```

### 4.2 Message Format

All WebSocket messages follow this format:

```json
{
  "type": "event_type",
  "channel": "channel_name",
  "data": { ... },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4.3 Subscribing to Channels

```json
{
  "type": "subscribe",
  "channel": "agent.agent_abc123.events"
}
```

### 4.4 Available Channels

| Channel | Description |
|---------|-------------|
| `agent.{id}.events` | Agent state changes and actions |
| `environment.{id}.updates` | Environment state updates |
| `simulation.{id}.progress` | Simulation progress updates |
| `system.notifications` | System-wide notifications |

### 4.5 Event Types

#### Agent Events

```json
{
  "type": "agent.action",
  "channel": "agent.agent_abc123.events",
  "data": {
    "agent_id": "agent_abc123",
    "action": "decision",
    "result": {
      "decision_id": "dec_xyz",
      "option_selected": "option_1"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Environment Events

```json
{
  "type": "environment.update",
  "channel": "environment.env_xyz.updates",
  "data": {
    "environment_id": "env_xyz",
    "changes": {
      "traffic_flow": "heavy"
    }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

#### Simulation Events

```json
{
  "type": "simulation.step",
  "channel": "simulation.sim_abc.progress",
  "data": {
    "simulation_id": "sim_abc",
    "step": 50,
    "progress": 0.5,
    "state": { ... }
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### 4.6 Real-time Decision Support

Request real-time decision support via WebSocket:

```json
{
  "type": "decision.request",
  "data": {
    "request_id": "req_123",
    "agent_id": "agent_abc123",
    "goal_id": "goal_xyz",
    "context": { ... }
  }
}
```

Response:

```json
{
  "type": "decision.response",
  "data": {
    "request_id": "req_123",
    "recommendation": { ... },
    "confidence": 0.85
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## 5. Python SDK Reference

### 5.1 Installation

```bash
pip install usmsb-sdk
```

### 5.2 Quick Start

```python
from usmsb_sdk import USMSBManager, Agent, Goal, Environment

async def main():
    # Initialize SDK
    sdk = USMSBManager(config_path="./config.yaml")
    await sdk.initialize()

    # Create an Agent
    agent = Agent(
        id="user_1",
        name="Alice",
        type="human",
        capabilities=["learn", "decide"]
    )

    # Create an Environment
    env = Environment(
        id="city_1",
        name="Smart City",
        type="technological",
        state={"traffic_flow": "normal"}
    )

    # Get decision service
    decision_service = sdk.get_service("DecisionSupportService")

    # Request a decision
    result = await decision_service.decide(
        agent=agent,
        goal=Goal(id="g1", name="Optimize Commute"),
        context={"environment": env}
    )

    print(f"Recommended action: {result['recommendation']}")

    # Cleanup
    await sdk.shutdown()

asyncio.run(main())
```

### 5.3 Core Classes

#### USMSBManager

```python
class USMSBManager:
    def __init__(self, config_path: str = None, config: Dict = None):
        """Initialize the SDK manager."""

    async def initialize(self) -> None:
        """Initialize all SDK components."""

    async def shutdown(self) -> None:
        """Gracefully shutdown the SDK."""

    def get_service(self, service_name: str) -> Any:
        """Get a service instance by name."""

    def register_intelligence_source(self, source: IIntelligenceSource) -> None:
        """Register a custom intelligence source."""
```

#### Agent

```python
@dataclass
class Agent:
    id: str
    name: str
    type: str  # "human", "ai_agent", "organization"
    capabilities: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    goals: List[Goal] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)

    def add_goal(self, goal: Goal) -> None:
        """Add a goal to the agent."""

    def add_resource(self, resource: Resource) -> None:
        """Add a resource to the agent."""

    def update_state(self, key: str, value: Any) -> None:
        """Update agent state."""
```

#### Goal

```python
@dataclass
class Goal:
    id: str
    name: str
    description: str = ""
    priority: int = 0
    status: str = "pending"  # "pending", "in_progress", "completed", "cancelled"
    deadline: Optional[datetime] = None
    sub_goals: List[Goal] = field(default_factory=list)
    associated_agent_id: Optional[str] = None
```

#### Environment

```python
@dataclass
class Environment:
    id: str
    name: str
    type: str  # "natural", "social", "technological", "economic"
    state: Dict[str, Any] = field(default_factory=dict)
    influencing_factors: List[str] = field(default_factory=list)

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update environment state."""

    def get_factor(self, factor_name: str) -> Any:
        """Get a specific influencing factor."""
```

### 5.4 Services

#### BehaviorPredictionService

```python
class BehaviorPredictionService:
    async def predict_behavior(
        self,
        agent: Agent,
        environment: Environment,
        goal: Goal = None,
        time_horizon: str = "24h"
    ) -> Dict[str, Any]:
        """Predict agent behavior."""

    async def predict_system_evolution(
        self,
        agents: List[Agent],
        environment: Environment,
        steps: int = 100
    ) -> Dict[str, Any]:
        """Predict system evolution."""
```

#### DecisionSupportService

```python
class DecisionSupportService:
    async def decide(
        self,
        agent: Agent,
        goal: Goal,
        context: Dict[str, Any] = None,
        options: List[Dict] = None
    ) -> Dict[str, Any]:
        """Get decision recommendation."""

    async def evaluate_options(
        self,
        options: List[Dict],
        criteria: List[Dict],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Evaluate multiple options."""
```

#### SystemSimulationService

```python
class SystemSimulationService:
    async def create_simulation(
        self,
        name: str,
        environment: Environment,
        agents: List[Agent],
        parameters: Dict[str, Any] = None
    ) -> Simulation:
        """Create a new simulation."""

    async def run_simulation(
        self,
        simulation: Simulation,
        callback: Callable = None
    ) -> Dict[str, Any]:
        """Run a simulation with optional progress callback."""

    async def analyze_results(
        self,
        simulation_id: str
    ) -> Dict[str, Any]:
        """Analyze simulation results."""
```

#### AgenticWorkflowService

```python
class AgenticWorkflowService:
    async def create_workflow(
        self,
        name: str,
        steps: List[Dict],
        trigger: Dict = None
    ) -> Workflow:
        """Create a new workflow."""

    async def execute_workflow(
        self,
        workflow: Workflow,
        agent: Agent,
        input_data: Dict = None
    ) -> Dict[str, Any]:
        """Execute a workflow."""

    async def get_execution_status(
        self,
        execution_id: str
    ) -> Dict[str, Any]:
        """Get workflow execution status."""
```

---

## 6. External Integration APIs

### 6.1 LLM Integration

USMSB SDK supports integration with multiple LLM providers.

#### OpenAI Integration

```python
from usmsb_sdk.adapters import OpenAIGPTAdapter

adapter = OpenAIGPTAdapter(
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)

await sdk.register_intelligence_source(adapter)
```

#### Anthropic Integration

```python
from usmsb_sdk.adapters import AnthropicClaudeAdapter

adapter = AnthropicClaudeAdapter(
    api_key="sk-ant-...",
    model="claude-3-opus"
)

await sdk.register_intelligence_source(adapter)
```

#### Google Gemini Integration

```python
from usmsb_sdk.adapters import GeminiLLMAdapter

adapter = GeminiLLMAdapter(
    api_key="...",
    model="gemini-pro"
)

await sdk.register_intelligence_source(adapter)
```

### 6.2 Knowledge Base Integration

#### Vector Database (Pinecone)

```python
from usmsb_sdk.adapters import PineconeKnowledgeBaseAdapter

kb_adapter = PineconeKnowledgeBaseAdapter(
    api_key="...",
    environment="us-west1-gcp",
    index_name="usmsb-knowledge"
)

await sdk.register_intelligence_source(kb_adapter)
```

#### Graph Database (Neo4j)

```python
from usmsb_sdk.adapters import Neo4jKnowledgeBaseAdapter

neo4j_adapter = Neo4jKnowledgeBaseAdapter(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="..."
)

await sdk.register_intelligence_source(neo4j_adapter)
```

### 6.3 Agentic Framework Integration

#### LangChain Integration

```python
from usmsb_sdk.adapters import LangChainAgenticAdapter

langchain_adapter = LangChainAgenticAdapter(
    llm=OpenAI(temperature=0),
    tools=[...],
    agent_type="zero-shot-react-description"
)

await sdk.register_intelligence_source(langchain_adapter)
```

#### AutoGen Integration

```python
from usmsb_sdk.adapters import AutoGenAgenticAdapter

autogen_adapter = AutoGenAgenticAdapter(
    config_list=[{
        "model": "gpt-4",
        "api_key": "..."
    }]
)

await sdk.register_intelligence_source(autogen_adapter)
```

### 6.4 External API Webhooks

Configure webhooks to receive notifications:

```http
POST /v1/webhooks
```

**Request Body:**

```json
{
  "url": "https://your-app.com/webhook",
  "events": [
    "agent.created",
    "agent.action.completed",
    "simulation.completed",
    "decision.made"
  ],
  "secret": "your-webhook-secret"
}
```

**Webhook Payload:**

```json
{
  "event": "agent.action.completed",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "agent_id": "agent_abc123",
    "action": "decision",
    "result": {...}
  },
  "signature": "sha256=..."
}
```

---

## 7. Error Codes

### 7.1 Error Code Format

Error codes follow the format: `USMSB_[CATEGORY]_[CODE]`

### 7.2 Authentication Errors (AUTH)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_AUTH_001` | 401 | Invalid API key |
| `USMSB_AUTH_002` | 401 | Expired API key |
| `USMSB_AUTH_003` | 403 | Insufficient permissions |
| `USMSB_AUTH_004` | 401 | Missing authentication header |
| `USMSB_AUTH_005` | 401 | Invalid OAuth token |

### 7.3 Validation Errors (VALID)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_VALID_001` | 400 | Invalid request body |
| `USMSB_VALID_002` | 400 | Missing required field |
| `USMSB_VALID_003` | 400 | Invalid field value |
| `USMSB_VALID_004` | 400 | Invalid data type |
| `USMSB_VALID_005` | 400 | Value out of range |

### 7.4 Resource Errors (RES)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_RES_001` | 404 | Resource not found |
| `USMSB_RES_002` | 409 | Resource already exists |
| `USMSB_RES_003` | 410 | Resource has been deleted |
| `USMSB_RES_004` | 403 | Resource access denied |
| `USMSB_RES_005` | 409 | Resource conflict |

### 7.5 Agent Errors (AGENT)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_AGENT_001` | 404 | Agent not found |
| `USMSB_AGENT_002` | 400 | Invalid agent type |
| `USMSB_AGENT_003` | 400 | Invalid capability |
| `USMSB_AGENT_004` | 409 | Agent goal conflict |
| `USMSB_AGENT_005` | 500 | Agent execution failed |

### 7.6 Decision Errors (DEC)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_DEC_001` | 400 | Invalid decision context |
| `USMSB_DEC_002` | 400 | No valid options provided |
| `USMSB_DEC_003` | 500 | Decision service unavailable |
| `USMSB_DEC_004` | 408 | Decision timeout |
| `USMSB_DEC_005` | 500 | LLM inference error |

### 7.7 Simulation Errors (SIM)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_SIM_001` | 404 | Simulation not found |
| `USMSB_SIM_002` | 400 | Invalid simulation parameters |
| `USMSB_SIM_003` | 500 | Simulation execution error |
| `USMSB_SIM_004` | 409 | Simulation already running |
| `USMSB_SIM_005` | 503 | Simulation capacity exceeded |

### 7.8 Rate Limit Errors (RATE)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_RATE_001` | 429 | Rate limit exceeded |
| `USMSB_RATE_002` | 429 | Concurrent request limit exceeded |
| `USMSB_RATE_003` | 429 | Daily quota exceeded |

### 7.9 System Errors (SYS)

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USMSB_SYS_001` | 500 | Internal server error |
| `USMSB_SYS_002` | 503 | Service unavailable |
| `USMSB_SYS_003` | 504 | Gateway timeout |
| `USMSB_SYS_004` | 500 | Database error |
| `USMSB_SYS_005` | 500 | Configuration error |

---

## 8. Rate Limits

### 8.1 Default Limits

| API Key Type | Requests/min | Requests/day | Concurrent |
|--------------|--------------|--------------|------------|
| Development | 100 | 10,000 | 5 |
| Production | 1,000 | 100,000 | 20 |
| Enterprise | Custom | Custom | Custom |

### 8.2 Endpoint-Specific Limits

| Endpoint | Rate Limit |
|----------|------------|
| `/v1/decisions` | 50 req/min |
| `/v1/predictions/*` | 30 req/min |
| `/v1/simulations/*` | 10 req/min |
| `/v1/information/search` | 100 req/min |
| WebSocket connections | 5 per API key |

### 8.3 Rate Limit Headers

All responses include rate limit headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1704287400
X-RateLimit-Retry-After: 60
```

### 8.4 Handling Rate Limits

```python
import time
from usmsb_sdk import USMSBManager

async def handle_rate_limit():
    sdk = USMSBManager(api_key="your_key")

    try:
        result = await sdk.some_operation()
    except RateLimitError as e:
        retry_after = e.retry_after
        print(f"Rate limited. Retrying in {retry_after} seconds...")
        time.sleep(retry_after)
        result = await sdk.some_operation()

    return result
```

---

## Appendix A: Data Types

### AgentType

```
"human" | "ai_agent" | "organization"
```

### GoalStatus

```
"pending" | "in_progress" | "completed" | "cancelled"
```

### ResourceType

```
"tangible" | "intangible"
```

### RuleType

```
"legal" | "social" | "algorithmic"
```

### InformationType

```
"text" | "image" | "data" | "event"
```

### EnvironmentType

```
"natural" | "social" | "technological" | "economic"
```

### ValueType

```
"economic" | "social" | "health" | "emotional"
```

### RiskType

```
"market" | "technical" | "operational" | "legal" | "relationship"
```

---

## Appendix B: Changelog

### v1.0.0 (2025-01-15)
- Initial API release
- Core Agent, Environment, Goal management
- Decision support service
- Behavior prediction service
- System simulation service
- WebSocket real-time events
- Python SDK

---

**Document Information**

- **Version**: 1.0.0
- **Author**: USMSB SDK Team
- **Last Updated**: 2025
- **License**: Apache 2.0

---

*For more information, please refer to the platform documentation or contact the platform operator.*
