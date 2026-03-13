# Meta Agent Usage Guide

> In-depth guide to Meta Agent's Memory, Knowledge, Tools, and Skills System

---

## 1. Meta Agent Overview

Meta Agent is a super agent built on the USMSB model with the following core capabilities:

- **Nine Universal Actions**: Perception, Decision, Execution, Interaction, Transformation, Evaluation, Feedback, Learning, RiskManagement
- **Multi-layer Memory System**: Short-term memory, Summary memory, User profile
- **Dynamic Knowledge Graph**: Supports entity relationships, causal chains, and temporal evolution
- **Skills System**: Dynamic loading and execution of skills
- **Tools System**: Integration with external tools and services

---

## 2. Memory System

Meta Agent uses a three-layer memory architecture that simulates how human memory works.

### 2.1 Short-term Memory

**Function**: Save the most recent N conversation messages

**Configuration Parameters**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import MemoryConfig

config = MemoryConfig(
    short_term_messages=20,    # Keep last 20 messages
    summary_threshold=30        # Trigger summary when exceeding 30
)
```

**Characteristics**:
- Store raw conversation messages
- Maintain conversation context continuity
- Automatically manage message count
- Automatically trigger summarization when threshold is exceeded

### 2.2 Summary Memory

**Function**: Compress longer conversations into summaries, preserving key information

**Trigger Conditions**:
- Short-term memory exceeds `summary_threshold` (default 30)
- User explicitly requests summarization
- Conversation naturally ends

**Extracted Content**:
- Key topics (`key_topics`)
- Important decisions (`decisions`)
- Commitments (`commitments`)
- Key data (`key_data`)

**Example**:
```python
# Summary memory automatically extracts from conversation
summary = {
    "key_topics": ["project plan", "budget allocation", "timeline"],
    "decisions": ["Confirm agile development", "Budget set to 100k"],
    "message_count": 35
}
```

### 2.3 User Profile

**Function**: Long-term storage of user preferences, commitments, and knowledge

**Data Content**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import UserProfile

profile = UserProfile(
    user_id="user_123",
    preferences={
        "communication_style": "concise",
        "preferred_language": "English",
        "notification_time": "9am"
    },
    commitments=["Submit draft by next Monday", "Complete testing by Friday"],
    knowledge={
        "skills": ["Python", "JavaScript"],
        "projects": ["E-commerce platform", "Data analysis"]
    }
)
```

**Persistence**:
- Persistently stored using SQLite database
- Support cross-session memory
- Automatic updates and synchronization

### 2.4 Memory Manager

**Initialization**:
```python
from usmsb_sdk.platform.external.meta_agent.memory import MemoryManager, MemoryConfig

# Create configuration
config = MemoryConfig(
    short_term_messages=20,
    summary_threshold=30,
    max_summaries=10,
    extract_preferences=True,
    importance_threshold=0.7
)

# Initialize manager
memory = MemoryManager(
    db_path="./data/memory.db",
    config=config,
    llm_manager=llm_manager  # Optional, used for summary generation
)

await memory.init()
```

**Core Methods**:
```python
# Add conversation message
await memory.add_message(
    conversation_id="conv_123",
    role="user",
    content="I want to develop an e-commerce website"
)

# Get memory context
context = await memory.get_context(
    conversation_id="conv_123",
    include_short_term=True,
    include_summaries=True,
    include_profile=True
)

# Extract user preferences
await memory.extract_preferences(
    conversation_id="conv_123",
    user_id="user_123"
)

# Save commitment
await memory.add_commitment(
    user_id="user_123",
    commitment="Submit draft by next Monday",
    due_date="2026-03-02"
)
```

---

## 3. Knowledge Graph System

Meta Agent is equipped with a dynamic knowledge graph supporting entity relationships, causal chains, and temporal evolution.

### 3.1 Knowledge Node

**Structure**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import KnowledgeNode, KnowledgeStatus

node = KnowledgeNode(
    id="node_001",
    content="Python is a high-level programming language",
    usmsb_element="info",  # USMSB element mapping
    status=KnowledgeStatus.NEW,
    confidence=0.9,         # Confidence 0-1
    importance=0.8,         # Importance 0-1
    source="user_input"    # Source
)
```

### 3.2 Knowledge Edge

**Relation Types**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import RelationType

# Supported relation types
IS_A = "is_a"           # Classification relationship
HAS_A = "has_a"         # Ownership relationship
CAUSES = "causes"        # Causal relationship
USES = "uses"           # Usage relationship
RELATES = "relates"      # General association

# USMSB element relations
USMSB_AGENT = "agent"    # Subject
USMSB_OBJECT = "object"  # Object
USMSB_GOAL = "goal"     # Goal
USMSB_RESOURCE = "resource"  # Resource
USMSB_RULE = "rule"     # Rule
USMSB_INFO = "info"     # Information
USMSB_VALUE = "value"   # Value
USMSB_RISK = "risk"     # Risk
USMSB_ENV = "environment"  # Environment
```

**Example**:
```python
edge = KnowledgeEdge(
    id="edge_001",
    source_id="node_python",
    target_id="node_programming_language",
    relation_type=RelationType.IS_A,
    weight=1.0,
    confidence=0.95
)
```

### 3.3 Knowledge Graph Manager

**Initialization and Usage**:
```python
from usmsb_sdk.platform.external.meta_agent.agi_core.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph(
    db_path="./data/knowledge.db"
)

await kg.init()

# Add node
node_id = await kg.add_node(
    content="Python is a high-level programming language",
    usmsb_element="info"
)

# Add relationship
await kg.add_edge(
    source_id=node_id,
    target_id="node_language",
    relation_type=RelationType.IS_A
)

# Query knowledge
results = await kg.query(
    keyword="Python",
    relation_type=RelationType.USES,
    min_confidence=0.7
)

# Reasoning query
inferences = await kg.query_with_reasoning(
    start_node="node_problem",
    max_depth=3
)
```

### 3.4 USMSB Element Knowledge Mapping

The knowledge graph corresponds to the nine USMSB elements:

| USMSB Element | Knowledge Type | Example |
|---------------|----------------|---------|
| Agent | Subject knowledge | User info, Agent capabilities |
| Object | Object knowledge | Products, services, data |
| Goal | Goal knowledge | Tasks, plans, expectations |
| Resource | Resource knowledge | Tools, funds, time |
| Rule | Rule knowledge | Policies, agreements, standards |
| Information | Information knowledge | Facts, data, messages |
| Value | Value knowledge | Preferences, priorities, beliefs |
| Risk | Risk knowledge | Threats, limitations, precautions |
| Environment | Environment knowledge | Context, scenario, background |

---

## 4. Skills System

Skills are the extensible capability units of Meta Agent.

### 4.1 Defining Skills

**Basic Structure**:
```python
from usmsb_sdk.core.skills import Skill, SkillMetadata, SkillCategory, SkillStatus, SkillParameter

class DataAnalysisSkill(Skill):
    def __init__(self):
        metadata = SkillMetadata(
            name="data_analysis",
            version="1.0.0",
            description="Data analysis skill",
            category=SkillCategory.ANALYSIS,
            status=SkillStatus.ACTIVE
        )
        super().__init__(metadata)

        # Define parameters
        self.parameters = {
            "data_source": SkillParameter(
                name="data_source",
                type="string",
                description="Data source path or URL",
                required=True
            ),
            "analysis_type": SkillParameter(
                name="analysis_type",
                type="string",
                description="Analysis type",
                enum=["statistical", "predictive", "clustering"],
                required=True
            )
        }

        # Define outputs
        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="object",
                description="Analysis result"
            )
        }

    async def execute(self, inputs, context=None):
        data = inputs["data_source"]
        analysis_type = inputs["analysis_type"]

        # Execute analysis logic
        result = await self._analyze(data, analysis_type)

        return {"result": result}
```

### 4.2 Skill Categories

| Category | Description | Examples |
|----------|-------------|----------|
| ANALYSIS | Analysis skills | Data analysis, trend analysis |
| GENERATION | Generation skills | Text generation, code generation |
| TRANSFORMATION | Transformation skills | Format conversion, language translation |
| COMMUNICATION | Communication skills | Chat, email |
| REASONING | Reasoning skills | Logic reasoning, causal analysis |
| ACTION | Action skills | Automated tasks |
| PERCEPTION | Perception skills | Image recognition, speech recognition |
| LEARNING | Learning skills | Knowledge extraction |
| PLANNING | Planning skills | Task planning |
| EVALUATION | Evaluation skills | Quality assessment |

### 4.3 Skill Registration and Usage

```python
from usmsb_sdk.agent_sdk import BaseAgent, AgentConfig, SkillDefinition

# Define skill
skill = SkillDefinition(
    name="python_code",
    description="Generate Python code",
    parameters=[
        {
            "name": "task",
            "type": "string",
            "description": "Task to complete"
        }
    ],
    returns="string",
    timeout=60
)

# Create agent and add skill
config = AgentConfig(
    name="coder_agent",
    description="Code generation Agent",
    skills=[skill]
)

agent = MyAgent(config)

# Execute skill
result = await agent.execute_skill(
    "python_code",
    {"task": "Implement quicksort"}
)
```

### 4.4 Skill Marketplace

```python
from usmsb_sdk.agent_sdk import MarketplaceManager

marketplace = MarketplaceManager(platform_url="http://localhost:8000")

# Publish skill
await marketplace.publish_skill(
    skill_definition=skill,
    price=0.01,  # Token per use
    share_level="public"  # Public/Private
)

# Search skills
skills = await marketplace.search_skills(
    category="analysis",
    min_rating=4.5
)
```

---

## 5. Tools System

Tools are Meta Agent's capabilities to interact with external systems.

### 5.1 Built-in Tools

**Platform Management Tools**:
| Tool Name | Function |
|-----------|----------|
| `start_node` | Start node |
| `stop_node` | Stop node |
| `get_node_status` | Get node status |
| `get_config` | Get configuration |
| `update_config` | Update configuration |

**Blockchain Tools**:
| Tool Name | Function |
|-----------|----------|
| `create_wallet` | Create wallet |
| `get_balance` | Query balance |
| `stake` | Stake tokens |
| `unstake` | Unstake |
| `vote` | Vote |
| `submit_proposal` | Submit proposal |

**Communication Tools**:
| Tool Name | Function |
|-----------|----------|
| `chat_with_agent` | Chat with Agent |
| `chat_with_human` | Chat with human |
| `broadcast_message` | Broadcast message |

### 5.2 Custom Tools

```python
from usmsb_sdk.agent_sdk.tools import Tool, ToolRegistry

class WebSearchTool(Tool):
    name = "web_search"
    description = "Search web information"
    parameters = {
        "query": {"type": "string", "description": "Search query"}
    }

    async def execute(self, query: str):
        # Implement search logic
        results = await self._search(query)
        return {"results": results}

# Register tool
registry = ToolRegistry()
registry.register(WebSearchTool())
```

### 5.3 Tool Invocation

```python
# Invoke tool through Agent
response = await agent.execute_tool(
    "web_search",
    {"query": "What is the USMSB model"}
)
```

---

## 6. Conversation Flow

### 6.1 Complete Conversation Flow

```
User Input
    │
    ▼
┌─────────────────────┐
│ 1. Perception       │
│  - Parse input      │
│  - Extract intent   │
│  - Recognize entities│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 2. Memory Retrieval │
│  - Short-term memory│
│  - Summary memory   │
│  - User profile     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 3. Knowledge Query  │
│  - Knowledge graph  │
│  - Related info     │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 4. Decision         │
│  - Plan action      │
│  - Select tools/skills│
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 5. Execution        │
│  - Invoke tools     │
│  - Execute skills  │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 6. Evaluation       │
│  - Check results    │
│  - Quality verify   │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│ 7. Memory Update    │
│  - Save conversation│
│  - Update profile   │
│  - Update knowledge │
└─────────────────────┘
    │
    ▼
  User Output
```

### 6.2 Code Example

```python
from usmsb_sdk.platform.external.meta_agent import MetaAgent, AgentConfig

# Initialize Meta Agent
config = AgentConfig(
    name="my_meta_agent",
    description="Personal AI Assistant",
    skills=[...],      # Skill list
    capabilities=[...] # Capability list
)

agent = MetaAgent(config)
await agent.start()

# Chat
response = await agent.chat(
    message="Analyze last week's sales data for me",
    user_id="user_123",
    conversation_id="conv_001"
)

print(response.content)
```

---

## 7. Configuration Options

### 7.1 AgentConfig Complete Configuration

```python
from usmsb_sdk.agent_sdk import AgentConfig, ProtocolConfig, ProtocolType

config = AgentConfig(
    # Identity
    name="my_agent",
    description="My Agent",
    agent_id="agent_001",  # Auto-generated
    version="1.0.0",
    owner="owner_wallet_address",
    tags=["ai", "assistant"],

    # Capabilities and skills
    capabilities=[
        CapabilityDefinition(
            name="text_generation",
            description="Text generation",
            category="nlp",
            level="advanced"
        )
    ],
    skills=[skill1, skill2],

    # Protocol configuration
    protocols={
        ProtocolType.A2A: ProtocolConfig(
            protocol_type=ProtocolType.A2A,
            enabled=True,
            host="0.0.0.0",
            port=8000
        ),
        ProtocolType.HTTP: ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            enabled=True
        )
    },

    # Network configuration
    network=NetworkConfig(
        platform_endpoints=["http://localhost:8000"],
        p2p_listen_port=9000
    ),

    # Security configuration
    security=SecurityConfig(
        auth_enabled=True,
        api_key="your_api_key"
    ),

    # Runtime settings
    auto_register=True,
    auto_discover=True,
    log_level="INFO",
    health_check_interval=30,
    heartbeat_interval=30
)
```

### 7.2 Runtime Configuration

```python
# Set callbacks
agent.on_state_change = async def(old_state, new_state):
    print(f"State change: {old_state} -> {new_state}")

agent.on_message = async def(message):
    print(f"Received message: {message}")

# Get status
print(agent.state)  # AgentState.RUNNING
print(agent.is_running)  # True

# Get metrics
metrics = agent.metrics
print(metrics)
# {
#     "messages_received": 10,
#     "messages_sent": 8,
#     "skills_executed": 5,
#     "errors": 0,
#     "uptime": 3600.0
# }
```

---

## 8. Best Practices

### 8.1 Memory System Usage Recommendations

1. **Set thresholds appropriately**: Adjust `short_term_messages` and `summary_threshold` based on conversation frequency
2. **Extract preferences regularly**: Call `extract_preferences()` after key interactions
3. **Manage commitments**: Use `add_commitment()` to record important commitments and set reminders

### 8.2 Knowledge Graph Usage Recommendations

1. **Structured storage**: Organize information as nodes and relationships
2. **Set confidence levels**: Set appropriate confidence based on information source
3. **Regular updates**: Update and strengthen knowledge through reasoning

### 8.3 Skill Design Recommendations

1. **Single responsibility**: Each skill should focus on one function
2. **Clear definitions**: Define input and output parameters in detail
3. **Error handling**: Implement robust exception handling

---

## 9. Troubleshooting

### 9.1 Common Issues and Solutions

| Category | Issue | Possible Cause | Solution |
|----------|-------|----------------|----------|
| **Memory** | Memory not persistent | Insufficient database path permissions | Check file path permissions, ensure write access |
| **Memory** | Memory not persistent | Not initialized | Confirm `await memory.init()` has been called |
| **Memory** | Summary generation failed | LLM not configured | Configure `llm_manager` parameter |
| **Skills** | Skill execution failed | Incorrect parameter definition | Check SkillParameter definition |
| **Skills** | Skill execution failed | Skill not registered | Confirm skill has been added to Agent config |
| **Skills** | Skill timeout | Execution time too long | Increase `timeout` setting |
| **Knowledge** | Knowledge query returns no results | Node doesn't exist | Check added node ID |
| **Knowledge** | Reasoning results inaccurate | Confidence threshold too high | Lower `min_confidence` parameter |
| **Tools** | Tool invocation failed | Network issue | Check network connection |
| **Tools** | Tool invocation timeout | Service response slow | Increase timeout or check service status |
| **Platform** | Cannot connect to platform | Wrong URL | Check `platform_url` configuration |
| **Platform** | Authentication failed | Wrong API Key | Check if `api_key` is correct |

### 9.2 Log Debugging

```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Agent logs
agent = MetaAgent(config)
agent.logger.setLevel(logging.DEBUG)

# Specific module logs
logging.getLogger('usmsb_sdk.agent_sdk').setLevel(logging.DEBUG)
logging.getLogger('usmsb_sdk.platform').setLevel(logging.DEBUG)
```

### 9.3 Performance Issue Troubleshooting

```python
import time
from usmsb_sdk.logging_monitoring import MetricsCollector

# Create performance monitoring
metrics = MetricsCollector(agent_name="debug_agent")

# Measure execution time
start = time.time()
result = await agent.chat(message="Test message")
duration = time.time() - start

print(f"Execution time: {duration:.3f}s")
print(f"Response time: {duration:.3f}s")

# Check metrics
print(f"Message count: {metrics.get('messages_received')}")
print(f"Error count: {metrics.get('errors')}")
```

### 9.4 Network Diagnostics

```python
import aiohttp

async def diagnose_platform_connection(platform_url: str):
    """Diagnose platform connection issues"""
    async with aiohttp.ClientSession() as session:
        # Check health endpoint
        try:
            async with session.get(f"{platform_url}/health") as resp:
                if resp.status == 200:
                    print("✓ Platform connection normal")
                else:
                    print(f"✗ Platform returned error: {resp.status}")
        except aiohttp.ClientConnectorError:
            print("✗ Cannot connect to platform")

        # Check API endpoint
        try:
            async with session.get(f"{platform_url}/api/v1/agents") as resp:
                print(f"API status: {resp.status}")
        except Exception as e:
            print(f"API error: {e}")
```

---

## 10. Related Documents

- [Agent SDK Details](./agent-sdk.md) - Complete Agent SDK documentation
- [USMSB SDK User Guide](./usmsb-sdk.md) - SDK usage guide
- [System Architecture](../03_architecture/system_architecture.md) - System architecture
