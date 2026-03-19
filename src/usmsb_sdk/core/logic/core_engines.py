"""
USMSB Core Logic Engines

This module implements the 6 core logic engines of the USMSB model:

1. Goal-Action-Outcome Loop (目标-行动-结果循环) - Already implemented
2. Resource-Transformation-Value Chain (资源-转化-价值增值链)
3. Information-Decision-Control Loop (信息-决策-控制回路)
4. System-Environment Interaction (系统-环境互动)
5. Emergence and Self-organization (涌现与自组织)
6. Adaptation and Evolution (适应与演化)

Each engine coordinates USMSB elements and universal actions to form
complete system behaviors.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ============== Engine Base Classes ==============

class EngineStatus(StrEnum):
    """Status of a logic engine."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class EngineState:
    """State of a logic engine."""
    engine_id: str
    engine_type: str
    status: EngineStatus = EngineStatus.IDLE
    iteration: int = 0
    last_update: float = field(default_factory=time.time)
    metrics: dict[str, Any] = field(default_factory=dict)


class ILogicEngine(ABC):
    """Abstract base class for all logic engines."""

    def __init__(self, engine_id: str | None = None):
        self.engine_id = engine_id or str(uuid.uuid4())[:8]
        self.state = EngineState(
            engine_id=self.engine_id,
            engine_type=self.__class__.__name__
        )
        self._callbacks: list[Callable] = []

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the engine logic."""
        pass

    @abstractmethod
    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one step of the engine."""
        pass

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for engine events."""
        self._callbacks.append(callback)

    async def _notify_callbacks(self, event: str, data: dict[str, Any]) -> None:
        """Notify all registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, data)
                else:
                    callback(event, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_state(self) -> EngineState:
        """Get current engine state."""
        return self.state


# ============== 2. Resource-Transformation-Value Chain ==============

@dataclass
class ResourceState:
    """State of a resource in the transformation chain."""
    resource_id: str
    resource_type: str
    quantity: float
    quality: float = 1.0
    location: str | None = None
    owner: str | None = None
    transformation_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ValueCreation:
    """Record of value creation."""
    value_id: str
    source_resources: list[str]
    transformation_type: str
    value_amount: float
    value_type: str  # economic, social, environmental, etc.
    created_at: float = field(default_factory=time.time)
    beneficiaries: list[str] = field(default_factory=list)


class ResourceTransformationValueEngine(ILogicEngine):
    """
    资源-转化-价值增值链引擎

    负责管理Agent的资源分配、消耗和状态更新。
    当资源被用于某个行动时，调用转化服务模拟资源的转化过程，
    并评估其产生的价值。
    """

    def __init__(self, transformation_service=None, evaluation_service=None):
        super().__init__()
        self.transformation_service = transformation_service
        self.evaluation_service = evaluation_service
        self._resources: dict[str, ResourceState] = {}
        self._values: dict[str, ValueCreation] = {}
        self._resource_history: list[dict[str, Any]] = []

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the complete transformation chain."""
        self.state.status = EngineStatus.RUNNING

        resources = context.get("resources", [])
        transformation_plan = context.get("transformation_plan", {})
        agent = context.get("agent")

        results = {
            "transformations": [],
            "values_created": [],
            "resource_changes": [],
        }

        for step in transformation_plan.get("steps", []):
            step_result = await self.step({
                "step": step,
                "agent": agent,
                "resources": resources,
            })
            results["transformations"].append(step_result)
            if step_result.get("value_created"):
                results["values_created"].append(step_result["value_created"])

        self.state.status = EngineStatus.COMPLETED
        self.state.iteration += 1

        await self._notify_callbacks("chain_completed", results)
        return results

    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one transformation step."""
        step = context.get("step", {})
        input_resources = step.get("inputs", [])
        transformation_type = step.get("type", "generic")
        context.get("agent")

        result = {
            "step_id": str(uuid.uuid4())[:8],
            "transformation_type": transformation_type,
            "inputs": input_resources,
            "outputs": [],
            "value_created": None,
            "efficiency": 0.0,
        }

        try:
            # Execute transformation
            if self.transformation_service:
                transform_result = await self.transformation_service.transform(
                    input_data=input_resources,
                    target_type=step.get("output_type", "transformed"),
                    context=context
                )
                result["outputs"] = transform_result.data if transform_result.data else []

            # Evaluate value created
            if self.evaluation_service:
                eval_result = await self.evaluation_service.evaluate(
                    item=result["outputs"],
                    criteria="value_creation",
                    context=context
                )
                if eval_result.data:
                    value_creation = ValueCreation(
                        value_id=str(uuid.uuid4())[:8],
                        source_resources=input_resources,
                        transformation_type=transformation_type,
                        value_amount=eval_result.data.get("score", 0.0),
                        value_type=eval_result.data.get("value_type", "economic"),
                    )
                    self._values[value_creation.value_id] = value_creation
                    result["value_created"] = {
                        "id": value_creation.value_id,
                        "amount": value_creation.value_amount,
                        "type": value_creation.value_type,
                    }

            # Calculate efficiency
            if result["value_created"]:
                result["efficiency"] = (
                    result["value_created"]["amount"] / max(len(input_resources), 1)
                )

            # Record history
            self._resource_history.append({
                "timestamp": time.time(),
                "transformation": transformation_type,
                "inputs": input_resources,
                "outputs": result["outputs"],
                "value": result["value_created"]["amount"] if result["value_created"] else 0,
            })

        except Exception as e:
            logger.error(f"Transformation step failed: {e}")
            result["error"] = str(e)

        return result

    def register_resource(self, resource: ResourceState) -> None:
        """Register a resource for tracking."""
        self._resources[resource.resource_id] = resource

    def get_resource_state(self, resource_id: str) -> ResourceState | None:
        """Get current state of a resource."""
        return self._resources.get(resource_id)

    def get_value_history(self) -> list[ValueCreation]:
        """Get history of value creations."""
        return list(self._values.values())

    def get_resource_flow(self) -> list[dict[str, Any]]:
        """Get the flow of resources through transformations."""
        return self._resource_history.copy()


# ============== 3. Information-Decision-Control Loop ==============

@dataclass
class InformationPacket:
    """A packet of information in the loop."""
    packet_id: str
    content: Any
    source: str
    timestamp: float = field(default_factory=time.time)
    quality: float = 1.0
    processed: bool = False


@dataclass
class DecisionRecord:
    """Record of a decision made."""
    decision_id: str
    input_information: list[str]
    decision_content: dict[str, Any]
    confidence: float = 0.0
    reasoning: str | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class ControlInstruction:
    """A control instruction generated from a decision."""
    instruction_id: str
    target: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    created_at: float = field(default_factory=time.time)


class InformationDecisionControlEngine(ILogicEngine):
    """
    信息-决策-控制回路引擎

    从感知服务接收原始数据，转化为结构化信息。
    信息被传递给决策服务进行决策。决策结果作为控制指令，
    作用于客体或环境。执行结果又产生新的信息，形成闭环。
    """

    def __init__(self, perception_service=None, decision_service=None, execution_service=None):
        super().__init__()
        self.perception_service = perception_service
        self.decision_service = decision_service
        self.execution_service = execution_service
        self._information_buffer: asyncio.Queue = asyncio.Queue()
        self._decisions: dict[str, DecisionRecord] = {}
        self._control_instructions: dict[str, ControlInstruction] = {}
        self._loop_history: list[dict[str, Any]] = []

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run the complete information-decision-control loop."""
        self.state.status = EngineStatus.RUNNING

        raw_inputs = context.get("inputs", [])
        agent = context.get("agent")
        goals = context.get("goals", [])

        results = {
            "information_processed": [],
            "decisions_made": [],
            "control_instructions": [],
            "actions_executed": [],
        }

        for raw_input in raw_inputs:
            # Step 1: Process information
            info_result = await self.process_information(raw_input, context)
            results["information_processed"].append(info_result)

            # Step 2: Make decision
            decision_result = await self.make_decision(
                info_result.get("structured_info", {}),
                agent,
                goals,
                context
            )
            results["decisions_made"].append(decision_result)

            # Step 3: Generate control instruction
            if decision_result.get("decision"):
                control_result = await self.generate_control(
                    decision_result["decision"],
                    context
                )
                results["control_instructions"].append(control_result)

                # Step 4: Execute control
                if control_result.get("instruction"):
                    exec_result = await self.execute_control(
                        control_result["instruction"],
                        agent,
                        context
                    )
                    results["actions_executed"].append(exec_result)

        self.state.status = EngineStatus.COMPLETED
        self.state.iteration += 1

        await self._notify_callbacks("loop_completed", results)
        return results

    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one step of the loop."""
        step_type = context.get("step_type", "perceive")

        if step_type == "perceive":
            return await self.process_information(context.get("input"), context)
        elif step_type == "decide":
            return await self.make_decision(
                context.get("information"),
                context.get("agent"),
                context.get("goals", []),
                context
            )
        elif step_type == "control":
            return await self.generate_control(context.get("decision"), context)
        elif step_type == "execute":
            return await self.execute_control(
                context.get("instruction"),
                context.get("agent"),
                context
            )
        else:
            return {"error": f"Unknown step type: {step_type}"}

    async def process_information(
        self,
        raw_input: Any,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Process raw input into structured information."""
        result = {
            "input": raw_input,
            "structured_info": None,
            "quality": 0.0,
        }

        if self.perception_service:
            perception_result = await self.perception_service.perceive(
                input_data=raw_input,
                context=context
            )
            if perception_result.data:
                result["structured_info"] = perception_result.data
                result["quality"] = perception_result.data.get("quality", 1.0)

        # Create information packet
        packet = InformationPacket(
            packet_id=str(uuid.uuid4())[:8],
            content=result["structured_info"],
            source="perception_service",
            quality=result["quality"],
        )
        await self._information_buffer.put(packet)

        return result

    async def make_decision(
        self,
        information: Any,
        agent: Any,
        goals: list[Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Make a decision based on information and goals."""
        result = {
            "decision": None,
            "confidence": 0.0,
            "reasoning": None,
        }

        if self.decision_service and goals:
            # Use the primary goal for decision
            primary_goal = goals[0] if goals else None
            decision_result = await self.decision_service.decide(
                agent=agent,
                goal=primary_goal,
                context={**context, "information": information}
            )

            if decision_result.data:
                result["decision"] = decision_result.data
                result["confidence"] = decision_result.data.get("confidence", 0.0)
                result["reasoning"] = decision_result.data.get("reasoning")

                # Record decision
                decision_record = DecisionRecord(
                    decision_id=str(uuid.uuid4())[:8],
                    input_information=[str(information)],
                    decision_content=decision_result.data,
                    confidence=result["confidence"],
                    reasoning=result["reasoning"],
                )
                self._decisions[decision_record.decision_id] = decision_record
                result["decision_id"] = decision_record.decision_id

        return result

    async def generate_control(
        self,
        decision: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate control instruction from decision."""
        result = {
            "instruction": None,
            "priority": 0,
        }

        if decision:
            # Extract action from decision
            action = decision.get("decision", decision.get("action", "unknown"))
            target = decision.get("target", "environment")
            parameters = decision.get("parameters", {})
            priority = decision.get("priority", 0)

            instruction = ControlInstruction(
                instruction_id=str(uuid.uuid4())[:8],
                target=target,
                action=action,
                parameters=parameters,
                priority=priority,
            )

            self._control_instructions[instruction.instruction_id] = instruction
            result["instruction"] = {
                "id": instruction.instruction_id,
                "target": instruction.target,
                "action": instruction.action,
                "parameters": instruction.parameters,
            }
            result["priority"] = priority

        return result

    async def execute_control(
        self,
        instruction: dict[str, Any],
        agent: Any,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a control instruction."""
        result = {
            "instruction_id": instruction.get("id"),
            "executed": False,
            "outcome": None,
        }

        if self.execution_service:
            exec_result = await self.execution_service.execute(
                action={
                    "type": instruction.get("action"),
                    "target": instruction.get("target"),
                    **instruction.get("parameters", {})
                },
                agent=agent,
                context=context
            )
            result["executed"] = exec_result.status.value == "success"
            result["outcome"] = exec_result.data

        # Record in history
        self._loop_history.append({
            "timestamp": time.time(),
            "instruction": instruction,
            "result": result,
        })

        return result

    def get_decision_history(self) -> list[DecisionRecord]:
        """Get history of decisions."""
        return list(self._decisions.values())

    def get_pending_instructions(self) -> list[ControlInstruction]:
        """Get pending control instructions."""
        return list(self._control_instructions.values())


# ============== 4. System-Environment Interaction ==============

@dataclass
class EnvironmentState:
    """State of the environment."""
    environment_id: str
    name: str
    type: str
    state: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, float] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    last_updated: float = field(default_factory=time.time)


@dataclass
class EnvironmentEvent:
    """An event in the environment."""
    event_id: str
    event_type: str
    source: str
    impact: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    duration: float | None = None


class SystemEnvironmentEngine(ILogicEngine):
    """
    系统-环境互动引擎

    维护环境实例的状态，提供接口供Agent感知环境变化，
    或通过执行服务对环境施加影响。支持模拟环境变化或接入真实环境数据。
    处理环境对Agent的反馈，例如资源枯竭、规则变化等。
    """

    def __init__(self, perception_service=None, execution_service=None):
        super().__init__()
        self.perception_service = perception_service
        self.execution_service = execution_service
        self._environments: dict[str, EnvironmentState] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._interaction_history: list[dict[str, Any]] = []
        self._environment_rules: dict[str, list[Callable]] = defaultdict(list)

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run system-environment interaction cycle."""
        self.state.status = EngineStatus.RUNNING

        environment_id = context.get("environment_id")
        agents = context.get("agents", [])
        actions = context.get("actions", [])

        results = {
            "environment_changes": [],
            "agent_perceptions": [],
            "feedback_generated": [],
        }

        # Process environment changes from actions
        for action in actions:
            change_result = await self.apply_action(environment_id, action, context)
            results["environment_changes"].append(change_result)

        # Update environment state
        await self.update_environment(environment_id, context)

        # Generate perceptions for agents
        for agent in agents:
            perception = await self.generate_perception(environment_id, agent, context)
            results["agent_perceptions"].append(perception)

        # Generate feedback
        feedback = await self.generate_feedback(environment_id, context)
        results["feedback_generated"] = feedback

        self.state.status = EngineStatus.COMPLETED
        self.state.iteration += 1

        await self._notify_callbacks("interaction_completed", results)
        return results

    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one interaction step."""
        step_type = context.get("step_type", "update")

        if step_type == "apply_action":
            return await self.apply_action(
                context.get("environment_id"),
                context.get("action"),
                context
            )
        elif step_type == "update":
            await self.update_environment(context.get("environment_id"), context)
            return {"updated": True}
        elif step_type == "perceive":
            return await self.generate_perception(
                context.get("environment_id"),
                context.get("agent"),
                context
            )
        else:
            return {"error": f"Unknown step type: {step_type}"}

    def register_environment(self, environment: EnvironmentState) -> None:
        """Register an environment."""
        self._environments[environment.environment_id] = environment

    def get_environment(self, environment_id: str) -> EnvironmentState | None:
        """Get environment state."""
        return self._environments.get(environment_id)

    async def apply_action(
        self,
        environment_id: str,
        action: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Apply an action to the environment."""
        result = {
            "action": action,
            "environment_id": environment_id,
            "applied": False,
            "effects": [],
        }

        environment = self._environments.get(environment_id)
        if not environment:
            result["error"] = "Environment not found"
            return result

        # Apply action effects to environment state
        action_type = action.get("type", "unknown")
        parameters = action.get("parameters", {})

        # Process based on action type
        if action_type == "modify_state":
            for key, value in parameters.get("changes", {}).items():
                if key in environment.state:
                    environment.state[key] = value
                    result["effects"].append({"variable": key, "new_value": value})

        elif action_type == "consume_resource":
            resource = parameters.get("resource")
            amount = parameters.get("amount", 0)
            if resource in environment.variables:
                environment.variables[resource] -= amount
                result["effects"].append({"resource": resource, "consumed": amount})

        environment.last_updated = time.time()
        result["applied"] = True

        # Record interaction
        self._interaction_history.append({
            "timestamp": time.time(),
            "action": action,
            "environment_id": environment_id,
            "effects": result["effects"],
        })

        return result

    async def update_environment(
        self,
        environment_id: str,
        context: dict[str, Any]
    ) -> None:
        """Update environment state based on rules and time."""
        environment = self._environments.get(environment_id)
        if not environment:
            return

        # Apply environment rules
        for rule in self._environment_rules.get(environment_id, []):
            try:
                if asyncio.iscoroutinefunction(rule):
                    await rule(environment, context)
                else:
                    rule(environment, context)
            except Exception as e:
                logger.error(f"Environment rule error: {e}")

        environment.last_updated = time.time()

    async def generate_perception(
        self,
        environment_id: str,
        agent: Any,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate perception for an agent from the environment."""
        environment = self._environments.get(environment_id)
        if not environment:
            return {"error": "Environment not found"}

        perception = {
            "agent_id": getattr(agent, 'id', str(agent)) if agent else "unknown",
            "environment_state": environment.state.copy(),
            "environment_variables": environment.variables.copy(),
            "relevant_changes": [],
        }

        # Find relevant changes for this agent
        recent_interactions = [
            i for i in self._interaction_history[-10:]
            if i["environment_id"] == environment_id
        ]
        perception["recent_changes"] = recent_interactions

        # Use perception service if available
        if self.perception_service:
            per_result = await self.perception_service.perceive(
                input_data=environment.state,
                context={**context, "agent": agent}
            )
            perception["structured_perception"] = per_result.data

        return perception

    async def generate_feedback(
        self,
        environment_id: str,
        context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate feedback from environment to agents."""
        environment = self._environments.get(environment_id)
        if not environment:
            return []

        feedback_list = []

        # Check for resource depletion
        for resource, value in environment.variables.items():
            if value < 0.1 * environment.constraints.get(f"{resource}_initial", value):
                feedback_list.append({
                    "type": "resource_depletion",
                    "resource": resource,
                    "current_level": value,
                    "warning": f"Resource {resource} is running low",
                })

        # Check for constraint violations
        for constraint, value in environment.constraints.items():
            if constraint.endswith("_max"):
                var_name = constraint[:-4]
                if var_name in environment.variables and environment.variables[var_name] > value:
                    feedback_list.append({
                        "type": "constraint_violation",
                        "constraint": constraint,
                        "current_value": environment.variables[var_name],
                        "max_value": value,
                    })

        return feedback_list

    def add_environment_rule(
        self,
        environment_id: str,
        rule: Callable
    ) -> None:
        """Add a rule that affects environment state."""
        self._environment_rules[environment_id].append(rule)

    async def emit_event(
        self,
        environment_id: str,
        event_type: str,
        impact: dict[str, Any]
    ) -> EnvironmentEvent:
        """Emit an environment event."""
        event = EnvironmentEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            source="environment_engine",
            impact=impact,
        )
        await self._event_queue.put(event)
        await self._notify_callbacks("environment_event", {
            "event_id": event.event_id,
            "type": event_type,
            "impact": impact,
        })
        return event


# ============== 5. Emergence and Self-organization ==============

@dataclass
class EmergentPattern:
    """A detected emergent pattern."""
    pattern_id: str
    pattern_type: str
    description: str
    participants: list[str]
    strength: float  # 0.0 to 1.0
    first_observed: float
    last_observed: float
    occurrences: int = 1
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfOrganizationState:
    """State of self-organization in the system."""
    organization_id: str
    participants: list[str]
    organization_type: str
    structure: dict[str, Any]
    stability: float
    created_at: float = field(default_factory=time.time)


class EmergenceSelfOrganizationEngine(ILogicEngine):
    """
    涌现与自组织引擎

    通过收集和分析多Agent交互数据，识别和可视化系统中
    涌现的宏观模式和自组织行为。涉及到复杂网络分析、统计模式识别等。
    """

    def __init__(self):
        super().__init__()
        self._interaction_data: list[dict[str, Any]] = []
        self._emergent_patterns: dict[str, EmergentPattern] = {}
        self._organizations: dict[str, SelfOrganizationState] = {}
        self._pattern_detectors: list[Callable] = []

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run emergence detection and self-organization analysis."""
        self.state.status = EngineStatus.RUNNING

        interactions = context.get("interactions", [])
        agents = context.get("agents", [])

        results = {
            "patterns_detected": [],
            "organizations_identified": [],
            "network_metrics": {},
            "predictions": [],
        }

        # Collect interaction data
        self._interaction_data.extend(interactions)

        # Detect emergent patterns
        patterns = await self.detect_patterns(agents, interactions, context)
        results["patterns_detected"] = patterns

        # Analyze self-organization
        organizations = await self.analyze_organization(agents, interactions, context)
        results["organizations_identified"] = organizations

        # Calculate network metrics
        metrics = await self.calculate_network_metrics(agents, interactions)
        results["network_metrics"] = metrics

        self.state.status = EngineStatus.COMPLETED
        self.state.iteration += 1

        await self._notify_callbacks("emergence_analysis_completed", results)
        return results

    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one analysis step."""
        step_type = context.get("step_type", "detect_patterns")

        if step_type == "detect_patterns":
            return {"patterns": await self.detect_patterns(
                context.get("agents", []),
                context.get("interactions", []),
                context
            )}
        elif step_type == "analyze_organization":
            return {"organizations": await self.analyze_organization(
                context.get("agents", []),
                context.get("interactions", []),
                context
            )}
        else:
            return {"error": f"Unknown step type: {step_type}"}

    async def detect_patterns(
        self,
        agents: list[Any],
        interactions: list[dict[str, Any]],
        context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect emergent patterns from interactions."""
        detected = []

        # Analyze interaction patterns
        agent_interaction_counts = defaultdict(int)
        agent_pairs = defaultdict(int)

        for interaction in interactions:
            sender = interaction.get("sender")
            receiver = interaction.get("receiver")
            if sender and receiver:
                agent_interaction_counts[sender] += 1
                agent_interaction_counts[receiver] += 1
                pair = tuple(sorted([sender, receiver]))
                agent_pairs[pair] += 1

        # Detect collaboration patterns (high interaction pairs)
        for pair, count in agent_pairs.items():
            if count >= 5:  # Threshold for pattern
                pattern_id = f"collab_{pair[0]}_{pair[1]}"
                if pattern_id not in self._emergent_patterns:
                    pattern = EmergentPattern(
                        pattern_id=pattern_id,
                        pattern_type="collaboration",
                        description=f"Frequent collaboration between {pair[0]} and {pair[1]}",
                        participants=list(pair),
                        strength=min(count / 10.0, 1.0),
                        first_observed=time.time(),
                        last_observed=time.time(),
                    )
                    self._emergent_patterns[pattern_id] = pattern
                    detected.append({
                        "id": pattern.pattern_id,
                        "type": pattern.pattern_type,
                        "participants": pattern.participants,
                        "strength": pattern.strength,
                    })
                else:
                    self._emergent_patterns[pattern_id].occurrences += 1
                    self._emergent_patterns[pattern_id].last_observed = time.time()

        # Detect hub patterns (agents with many interactions)
        for agent_id, count in agent_interaction_counts.items():
            if count >= 10:  # Hub threshold
                pattern_id = f"hub_{agent_id}"
                if pattern_id not in self._emergent_patterns:
                    pattern = EmergentPattern(
                        pattern_id=pattern_id,
                        pattern_type="hub",
                        description=f"Agent {agent_id} is a communication hub",
                        participants=[agent_id],
                        strength=min(count / 20.0, 1.0),
                        first_observed=time.time(),
                        last_observed=time.time(),
                    )
                    self._emergent_patterns[pattern_id] = pattern
                    detected.append({
                        "id": pattern.pattern_id,
                        "type": pattern.pattern_type,
                        "participants": pattern.participants,
                        "strength": pattern.strength,
                    })

        # Run custom pattern detectors
        for detector in self._pattern_detectors:
            try:
                custom_patterns = await detector(agents, interactions, context) if asyncio.iscoroutinefunction(detector) else detector(agents, interactions, context)
                detected.extend(custom_patterns)
            except Exception as e:
                logger.error(f"Pattern detector error: {e}")

        return detected

    async def analyze_organization(
        self,
        agents: list[Any],
        interactions: list[dict[str, Any]],
        context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Analyze self-organization in the system."""
        organizations = []

        # Build interaction network
        network = defaultdict(set)
        for interaction in interactions:
            sender = interaction.get("sender")
            receiver = interaction.get("receiver")
            if sender and receiver:
                network[sender].add(receiver)
                network[receiver].add(sender)

        # Detect communities (simplified)
        visited = set()
        for agent_id in network:
            if agent_id in visited:
                continue

            # BFS to find connected component
            community = set()
            queue = [agent_id]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                community.add(current)
                for neighbor in network[current]:
                    if neighbor not in visited:
                        queue.append(neighbor)

            if len(community) >= 3:  # Minimum community size
                org_id = f"org_{'_'.join(sorted(community)[:3])}"
                if org_id not in self._organizations:
                    org = SelfOrganizationState(
                        organization_id=org_id,
                        participants=list(community),
                        organization_type="community",
                        structure={"type": "network", "members": len(community)},
                        stability=len(community) / len(network) if network else 0,
                    )
                    self._organizations[org_id] = org
                    organizations.append({
                        "id": org.organization_id,
                        "type": org.organization_type,
                        "participants": org.participants,
                        "stability": org.stability,
                    })

        return organizations

    async def calculate_network_metrics(
        self,
        agents: list[Any],
        interactions: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Calculate network-level metrics."""
        metrics = {
            "total_agents": len(agents),
            "total_interactions": len(interactions),
            "avg_interactions_per_agent": 0,
            "network_density": 0,
            "clustering_coefficient": 0,
        }

        if not agents or not interactions:
            return metrics

        # Calculate average interactions
        agent_counts = defaultdict(int)
        for interaction in interactions:
            agent_counts[interaction.get("sender")] += 1
            agent_counts[interaction.get("receiver")] += 1

        if agent_counts:
            metrics["avg_interactions_per_agent"] = sum(agent_counts.values()) / len(agent_counts)

        # Calculate network density
        possible_edges = len(agents) * (len(agents) - 1)
        actual_edges = len({
            tuple(sorted([i.get("sender"), i.get("receiver")]))
            for i in interactions
            if i.get("sender") and i.get("receiver")
        })
        if possible_edges > 0:
            metrics["network_density"] = actual_edges / possible_edges

        return metrics

    def add_pattern_detector(self, detector: Callable) -> None:
        """Add a custom pattern detector."""
        self._pattern_detectors.append(detector)

    def get_patterns(self) -> list[EmergentPattern]:
        """Get all detected patterns."""
        return list(self._emergent_patterns.values())

    def get_organizations(self) -> list[SelfOrganizationState]:
        """Get all identified organizations."""
        return list(self._organizations.values())


# ============== 6. Adaptation and Evolution ==============

@dataclass
class AdaptationRecord:
    """Record of an adaptation made."""
    adaptation_id: str
    agent_id: str
    adaptation_type: str  # capability, rule, goal_priority, behavior
    before_state: dict[str, Any]
    after_state: dict[str, Any]
    trigger: str
    effectiveness: float | None = None
    created_at: float = field(default_factory=time.time)


@dataclass
class EvolutionMetric:
    """Metric tracking evolution progress."""
    metric_name: str
    initial_value: float
    current_value: float
    target_value: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


class AdaptationEvolutionEngine(ILogicEngine):
    """
    适应与演化引擎

    协调学习服务和反馈服务，根据Agent的长期表现和环境变化，
    触发Agent自身能力、规则集或目标优先级的调整。
    涉及到强化学习、元学习或基于规则的自适应机制。
    """

    def __init__(self, learning_service=None, feedback_service=None):
        super().__init__()
        self.learning_service = learning_service
        self.feedback_service = feedback_service
        self._adaptations: dict[str, AdaptationRecord] = {}
        self._evolution_metrics: dict[str, EvolutionMetric] = {}
        self._adaptation_rules: list[Callable] = []
        self._agent_performance: dict[str, list[float]] = defaultdict(list)

    async def run(self, context: dict[str, Any]) -> dict[str, Any]:
        """Run adaptation and evolution cycle."""
        self.state.status = EngineStatus.RUNNING

        agents = context.get("agents", [])
        performance_data = context.get("performance_data", {})
        feedback_history = context.get("feedback_history", [])

        results = {
            "adaptations_made": [],
            "learning_applied": [],
            "evolution_metrics": {},
            "recommendations": [],
        }

        for agent in agents:
            agent_id = getattr(agent, 'id', str(agent)) if agent else "unknown"

            # Collect performance data
            if agent_id in performance_data:
                self._agent_performance[agent_id].extend(performance_data[agent_id])

            # Analyze and adapt
            adaptation_result = await self.analyze_and_adapt(agent, context)
            if adaptation_result:
                results["adaptations_made"].append(adaptation_result)

            # Apply learning
            learning_result = await self.apply_learning(agent, feedback_history, context)
            if learning_result:
                results["learning_applied"].append(learning_result)

        # Update evolution metrics
        metrics_result = await self.update_evolution_metrics(agents, context)
        results["evolution_metrics"] = metrics_result

        # Generate recommendations
        recommendations = await self.generate_recommendations(agents, context)
        results["recommendations"] = recommendations

        self.state.status = EngineStatus.COMPLETED
        self.state.iteration += 1

        await self._notify_callbacks("evolution_cycle_completed", results)
        return results

    async def step(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute one adaptation step."""
        step_type = context.get("step_type", "adapt")

        if step_type == "adapt":
            return await self.analyze_and_adapt(context.get("agent"), context)
        elif step_type == "learn":
            return await self.apply_learning(
                context.get("agent"),
                context.get("feedback_history", []),
                context
            )
        elif step_type == "metrics":
            return await self.update_evolution_metrics(context.get("agents", []), context)
        else:
            return {"error": f"Unknown step type: {step_type}"}

    async def analyze_and_adapt(
        self,
        agent: Any,
        context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Analyze agent performance and trigger adaptations."""
        if not agent:
            return None

        agent_id = getattr(agent, 'id', str(agent))
        performance = self._agent_performance.get(agent_id, [])

        if len(performance) < 5:  # Need enough data
            return None

        # Calculate performance trend
        recent_avg = sum(performance[-5:]) / 5
        historical_avg = sum(performance) / len(performance)

        adaptation = None

        # Check for declining performance
        if recent_avg < historical_avg * 0.8:
            adaptation = await self.trigger_adaptation(
                agent=agent,
                adaptation_type="behavior",
                trigger="performance_decline",
                context=context
            )

        # Check for stagnation
        if len(set(performance[-10:])) == 1 if len(performance) >= 10 else False:
            adaptation = await self.trigger_adaptation(
                agent=agent,
                adaptation_type="capability",
                trigger="stagnation",
                context=context
            )

        # Run custom adaptation rules
        for rule in self._adaptation_rules:
            try:
                rule_adaptation = await rule(agent, performance, context) if asyncio.iscoroutinefunction(rule) else rule(agent, performance, context)
                if rule_adaptation:
                    adaptation = rule_adaptation
            except Exception as e:
                logger.error(f"Adaptation rule error: {e}")

        return adaptation

    async def trigger_adaptation(
        self,
        agent: Any,
        adaptation_type: str,
        trigger: str,
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Trigger an adaptation for an agent."""
        agent_id = getattr(agent, 'id', str(agent)) if agent else "unknown"

        # Capture before state
        before_state = {
            "capabilities": list(getattr(agent, 'capabilities', [])),
            "goals": [str(g) for g in getattr(agent, 'goals', [])],
            "rules": [str(r) for r in getattr(agent, 'rules', [])],
        }

        # Determine adaptation
        adaptation_actions = {
            "behavior": self._adapt_behavior,
            "capability": self._adapt_capability,
            "rule": self._adapt_rules,
            "goal_priority": self._adapt_goal_priority,
        }

        after_state = before_state.copy()
        if adaptation_type in adaptation_actions:
            after_state = await adaptation_actions[adaptation_type](agent, before_state, context)

        # Record adaptation
        record = AdaptationRecord(
            adaptation_id=str(uuid.uuid4())[:8],
            agent_id=agent_id,
            adaptation_type=adaptation_type,
            before_state=before_state,
            after_state=after_state,
            trigger=trigger,
        )
        self._adaptations[record.adaptation_id] = record

        return {
            "adaptation_id": record.adaptation_id,
            "agent_id": agent_id,
            "type": adaptation_type,
            "trigger": trigger,
            "changes": {
                k: {"before": before_state.get(k), "after": after_state.get(k)}
                for k in before_state if before_state.get(k) != after_state.get(k)
            }
        }

    async def _adapt_behavior(
        self,
        agent: Any,
        current_state: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Adapt agent behavior patterns."""
        # Use learning service to suggest behavior changes
        if self.learning_service:
            result = await self.learning_service.optimize_behavior(
                agent=agent,
                performance_data=self._agent_performance.get(getattr(agent, 'id', ''), []),
                context=context
            )
            if result.data:
                return {"behavior_adjustments": result.data.get("optimizations", [])}
        return current_state

    async def _adapt_capability(
        self,
        agent: Any,
        current_state: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Adapt agent capabilities."""
        new_capabilities = list(current_state.get("capabilities", []))

        # Suggest new capability based on context
        suggested = context.get("suggested_capabilities", [])
        for cap in suggested:
            if cap not in new_capabilities:
                new_capabilities.append(cap)

        return {"capabilities": new_capabilities}

    async def _adapt_rules(
        self,
        agent: Any,
        current_state: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Adapt agent rules."""
        # Simplified rule adaptation
        return current_state

    async def _adapt_goal_priority(
        self,
        agent: Any,
        current_state: dict[str, Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Adapt agent goal priorities."""
        goals = list(getattr(agent, 'goals', []))
        if len(goals) > 1:
            # Re-prioritize goals
            goals.sort(key=lambda g: getattr(g, 'priority', 0), reverse=True)
        return {"goals": [str(g) for g in goals]}

    async def apply_learning(
        self,
        agent: Any,
        feedback_history: list[Any],
        context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Apply learning from feedback."""
        if not self.learning_service or not agent:
            return None

        agent_id = getattr(agent, 'id', str(agent))

        # Collect relevant feedback
        relevant_feedback = [
            f for f in feedback_history
            if f.get("agent_id") == agent_id
        ]

        if not relevant_feedback:
            return None

        # Apply learning
        result = await self.learning_service.learn(
            experience_data={
                "feedback": relevant_feedback,
                "performance": self._agent_performance.get(agent_id, []),
            },
            agent=agent,
            context=context
        )

        return {
            "agent_id": agent_id,
            "learnings": result.data.get("learnings", []) if result.data else [],
        }

    async def update_evolution_metrics(
        self,
        agents: list[Any],
        context: dict[str, Any]
    ) -> dict[str, Any]:
        """Update and return evolution metrics."""
        metrics = {}

        # Population performance
        all_performance = []
        for agent in agents:
            agent_id = getattr(agent, 'id', str(agent)) if agent else None
            if agent_id and agent_id in self._agent_performance:
                all_performance.extend(self._agent_performance[agent_id])

        if all_performance:
            metrics["population_avg_performance"] = sum(all_performance) / len(all_performance)
            metrics["population_max_performance"] = max(all_performance)
            metrics["population_min_performance"] = min(all_performance)

        # Adaptation count
        metrics["total_adaptations"] = len(self._adaptations)
        metrics["adaptation_types"] = defaultdict(int)
        for adaptation in self._adaptations.values():
            metrics["adaptation_types"][adaptation.adaptation_type] += 1

        return metrics

    async def generate_recommendations(
        self,
        agents: list[Any],
        context: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Generate evolution recommendations."""
        recommendations = []

        for agent in agents:
            agent_id = getattr(agent, 'id', str(agent)) if agent else None
            if not agent_id:
                continue

            performance = self._agent_performance.get(agent_id, [])
            if len(performance) < 5:
                continue

            avg_performance = sum(performance[-5:]) / 5

            if avg_performance < 0.5:
                recommendations.append({
                    "agent_id": agent_id,
                    "type": "training",
                    "recommendation": "Consider additional training or capability enhancement",
                    "priority": "high",
                })
            elif avg_performance < 0.8:
                recommendations.append({
                    "agent_id": agent_id,
                    "type": "optimization",
                    "recommendation": "Fine-tune behavior parameters",
                    "priority": "medium",
                })

        return recommendations

    def add_adaptation_rule(self, rule: Callable) -> None:
        """Add a custom adaptation rule."""
        self._adaptation_rules.append(rule)

    async def record(self, record: Any) -> None:
        """
        Record an adaptation from external source (e.g., feedback loop).

        This allows the feedback loop to send adaptation data to the Core engine
        for platform-wide learning.

        Args:
            record: Adaptation record, typically a dict with fields:
                - record_id: Unique identifier
                - agent_id: Agent identifier
                - adaptation_type: Type of adaptation (e.g., "soul_update")
                - experience: Dict with adaptation experience data
                - outcome: Dict with adaptation outcome
                - timestamp: When the adaptation occurred
        """
        adaptation_id = getattr(record, 'record_id', None) or getattr(record, 'adaptation_id', str(uuid.uuid4())[:8])
        agent_id = getattr(record, 'agent_id', 'unknown')
        adaptation_type = getattr(record, 'adaptation_type', 'unknown')

        # Convert experience/outcome to before_state/after_state format
        experience = getattr(record, 'experience', {})
        outcome = getattr(record, 'outcome', {})

        before_state = {
            "experience": experience,
            "timestamp": getattr(record, 'timestamp', time.time()),
        }
        after_state = {
            "outcome": outcome,
            "recorded_at": time.time(),
        }

        # Create core AdaptationRecord
        core_record = AdaptationRecord(
            adaptation_id=adaptation_id,
            agent_id=agent_id,
            adaptation_type=adaptation_type,
            before_state=before_state,
            after_state=after_state,
            trigger="feedback_loop",
            effectiveness=outcome.get("overall_score") if isinstance(outcome, dict) else None,
            created_at=getattr(record, 'timestamp', time.time()),
        )

        # Store in internal dict
        self._adaptations[core_record.adaptation_id] = core_record

        # Also track performance data if available
        if isinstance(outcome, dict) and "overall_score" in outcome:
            if agent_id not in self._agent_performance:
                self._agent_performance[agent_id] = []
            self._agent_performance[agent_id].append(outcome["overall_score"])

        logger.info(
            f"Recorded adaptation {adaptation_id} for agent {agent_id}: "
            f"type={adaptation_type}, score={outcome.get('overall_score') if isinstance(outcome, dict) else 'N/A'}"
        )

    def get_adaptation_history(self, agent_id: str | None = None) -> list[AdaptationRecord]:
        """Get adaptation history."""
        if agent_id:
            return [a for a in self._adaptations.values() if a.agent_id == agent_id]
        return list(self._adaptations.values())


# ============== Engine Registry ==============

class LogicEngineRegistry:
    """Registry for all logic engines."""

    _engines: dict[str, ILogicEngine] = {}

    @classmethod
    def register(cls, name: str, engine: ILogicEngine) -> None:
        """Register an engine."""
        cls._engines[name] = engine

    @classmethod
    def get(cls, name: str) -> ILogicEngine | None:
        """Get an engine by name."""
        return cls._engines.get(name)

    @classmethod
    def list_engines(cls) -> list[str]:
        """List all registered engines."""
        return list(cls._engines.keys())

    @classmethod
    def create_all_engines(
        cls,
        perception_service=None,
        decision_service=None,
        execution_service=None,
        transformation_service=None,
        evaluation_service=None,
        learning_service=None,
        feedback_service=None,
    ) -> dict[str, ILogicEngine]:
        """Create and register all engines."""
        engines = {
            "resource_value": ResourceTransformationValueEngine(
                transformation_service=transformation_service,
                evaluation_service=evaluation_service,
            ),
            "info_decision_control": InformationDecisionControlEngine(
                perception_service=perception_service,
                decision_service=decision_service,
                execution_service=execution_service,
            ),
            "system_environment": SystemEnvironmentEngine(
                perception_service=perception_service,
                execution_service=execution_service,
            ),
            "emergence": EmergenceSelfOrganizationEngine(),
            "adaptation": AdaptationEvolutionEngine(
                learning_service=learning_service,
                feedback_service=feedback_service,
            ),
        }

        for name, engine in engines.items():
            cls.register(name, engine)

        return engines
