"""
System Simulation Service

Service for simulating multi-agent systems based on USMSB model.
Supports discrete event simulation, Monte Carlo simulation, and
agent-based modeling.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from usmsb_sdk.core.elements import Agent, Environment, Goal, Resource, Risk
from usmsb_sdk.intelligence_adapters.base import ILLMAdapter

logger = logging.getLogger(__name__)


class SimulationType(Enum):
    """Types of simulation."""
    DISCRETE_EVENT = "discrete_event"
    AGENT_BASED = "agent_based"
    MONTE_CARLO = "monte_carlo"
    SYSTEM_DYNAMICS = "system_dynamics"
    HYBRID = "hybrid"


class SimulationStatus(Enum):
    """Status of a simulation run."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(Enum):
    """Types of simulation events."""
    AGENT_ACTION = "agent_action"
    AGENT_INTERACTION = "agent_interaction"
    RESOURCE_CHANGE = "resource_change"
    ENVIRONMENT_CHANGE = "environment_change"
    GOAL_UPDATE = "goal_update"
    RISK_EVENT = "risk_event"
    SYSTEM_EVENT = "system_event"


@dataclass
class SimulationEvent:
    """A single simulation event."""
    event_type: EventType
    timestamp: float
    source: str
    target: Optional[str]
    data: Dict[str, Any]
    priority: int = 0

    def __lt__(self, other):
        """Compare by timestamp then priority."""
        if self.timestamp == other.timestamp:
            return self.priority < other.priority
        return self.timestamp < other.timestamp


@dataclass
class SimulationStep:
    """A single step in the simulation."""
    step_number: int
    timestamp: float
    events: List[SimulationEvent]
    state_snapshot: Dict[str, Any]
    metrics: Dict[str, float]


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    simulation_type: SimulationType
    max_steps: int = 1000
    time_limit: float = 3600.0  # seconds
    seed: Optional[int] = None
    snapshot_interval: int = 10
    parallel_agents: bool = True
    event_queue_size: int = 10000
    enable_logging: bool = True
    stop_conditions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Result of a simulation run."""
    simulation_id: str
    status: SimulationStatus
    steps: List[SimulationStep]
    final_state: Dict[str, Any]
    metrics: Dict[str, float]
    events: List[SimulationEvent]
    duration: float
    agent_stats: Dict[str, Dict[str, Any]]
    resource_stats: Dict[str, Dict[str, Any]]
    emergent_patterns: List[Dict[str, Any]]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class AgentState:
    """State of an agent in simulation."""
    agent_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    resources: Dict[str, float] = field(default_factory=dict)
    goals: List[str] = field(default_factory=list)
    active_goal: Optional[str] = None
    health: float = 1.0
    energy: float = 1.0
    status: str = "idle"
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnvironmentState:
    """State of the simulation environment."""
    resources: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, float] = field(default_factory=dict)
    spatial_grid: Optional[Dict[Tuple[int, int, int], Any]] = None


class SystemSimulationService:
    """
    System Simulation Service.

    Provides comprehensive simulation capabilities:
    - Agent-based modeling
    - Discrete event simulation
    - Monte Carlo analysis
    - System dynamics
    - Emergent behavior detection
    """

    def __init__(
        self,
        llm_adapter: Optional[ILLMAdapter] = None,
        default_config: Optional[SimulationConfig] = None,
    ):
        """
        Initialize the Simulation Service.

        Args:
            llm_adapter: Optional LLM adapter for intelligent simulation
            default_config: Default simulation configuration
        """
        self.llm = llm_adapter
        self.default_config = default_config or SimulationConfig(
            simulation_type=SimulationType.AGENT_BASED
        )
        self._active_simulations: Dict[str, Dict[str, Any]] = {}
        self._event_handlers: Dict[EventType, List[Callable]] = {}

    async def create_simulation(
        self,
        agents: List[Agent],
        environment: Environment,
        config: Optional[SimulationConfig] = None,
    ) -> str:
        """
        Create a new simulation.

        Args:
            agents: List of agents to simulate
            environment: Simulation environment
            config: Simulation configuration

        Returns:
            Simulation ID
        """
        import uuid
        simulation_id = str(uuid.uuid4())[:8]

        config = config or self.default_config

        # Initialize random seed
        if config.seed is not None:
            random.seed(config.seed)

        # Initialize agent states
        agent_states = {}
        for agent in agents:
            agent_states[agent.id] = AgentState(
                agent_id=agent.id,
                resources={r.id: r.quantity for r in agent.resources},
                goals=[g.id for g in agent.goals],
                active_goal=agent.get_highest_priority_goal().id if agent.goals else None,
                attributes={"capabilities": agent.capabilities, "type": agent.type.value},
            )

        # Initialize environment state
        env_state = EnvironmentState(
            resources={r.id: {"name": r.name, "quantity": r.quantity} for r in environment.resources},
            constraints=environment.constraints,
            conditions={"stability": 1.0, "complexity": 0.5},
        )

        self._active_simulations[simulation_id] = {
            "config": config,
            "agents": agents,
            "agent_states": agent_states,
            "environment": environment,
            "env_state": env_state,
            "status": SimulationStatus.CREATED,
            "current_step": 0,
            "event_queue": [],
            "completed_events": [],
            "steps": [],
            "metrics": {},
            "start_time": None,
        }

        logger.info(f"Created simulation {simulation_id} with {len(agents)} agents")
        return simulation_id

    async def run_simulation(
        self,
        simulation_id: str,
        steps: Optional[int] = None,
    ) -> SimulationResult:
        """
        Run a simulation.

        Args:
            simulation_id: ID of the simulation to run
            steps: Number of steps to run (uses config.max_steps if None)

        Returns:
            SimulationResult with simulation outcomes
        """
        if simulation_id not in self._active_simulations:
            raise ValueError(f"Simulation {simulation_id} not found")

        sim = self._active_simulations[simulation_id]
        config = sim["config"]

        max_steps = steps or config.max_steps
        sim["status"] = SimulationStatus.RUNNING
        sim["start_time"] = datetime.now()

        logger.info(f"Starting simulation {simulation_id} for {max_steps} steps")

        try:
            for step_num in range(max_steps):
                sim["current_step"] = step_num

                # Check stop conditions
                if await self._check_stop_conditions(sim):
                    logger.info(f"Stop condition met at step {step_num}")
                    break

                # Execute simulation step
                step_result = await self._execute_step(simulation_id, step_num)
                sim["steps"].append(step_result)

                # Update metrics
                sim["metrics"] = self._calculate_metrics(sim)

                # Take snapshot
                if step_num % config.snapshot_interval == 0:
                    await self._take_snapshot(sim)

                # Detect emergent patterns
                if step_num % 50 == 0:
                    patterns = await self._detect_emergent_patterns(sim)
                    sim.setdefault("emergent_patterns", []).extend(patterns)

            sim["status"] = SimulationStatus.COMPLETED

        except Exception as e:
            logger.error(f"Simulation {simulation_id} failed: {e}")
            sim["status"] = SimulationStatus.FAILED
            raise

        # Compile results
        duration = (datetime.now() - sim["start_time"]).total_seconds()

        result = SimulationResult(
            simulation_id=simulation_id,
            status=sim["status"],
            steps=sim["steps"],
            final_state=self._get_state_snapshot(sim),
            metrics=sim["metrics"],
            events=sim["completed_events"],
            duration=duration,
            agent_stats=self._compile_agent_stats(sim),
            resource_stats=self._compile_resource_stats(sim),
            emergent_patterns=sim.get("emergent_patterns", []),
        )

        return result

    async def run_monte_carlo(
        self,
        agents: List[Agent],
        environment: Environment,
        num_runs: int = 100,
        config: Optional[SimulationConfig] = None,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation.

        Args:
            agents: List of agents to simulate
            environment: Simulation environment
            num_runs: Number of simulation runs
            config: Base configuration

        Returns:
            Aggregated Monte Carlo results
        """
        config = config or SimulationConfig(simulation_type=SimulationType.MONTE_CARLO)

        results = []
        for run in range(num_runs):
            # Vary seed for each run
            config.seed = random.randint(1, 1000000)

            sim_id = await self.create_simulation(agents, environment, config)
            result = await self.run_simulation(sim_id)
            results.append(result)

            # Cleanup
            del self._active_simulations[sim_id]

        # Aggregate results
        aggregated = self._aggregate_monte_carlo_results(results)

        return {
            "num_runs": num_runs,
            "aggregated_metrics": aggregated,
            "confidence_intervals": self._calculate_confidence_intervals(results),
            "distribution_stats": self._calculate_distribution_stats(results),
            "outliers": self._identify_outliers(results),
        }

    async def step_simulation(
        self,
        simulation_id: str,
        num_steps: int = 1,
    ) -> List[SimulationStep]:
        """
        Execute a specific number of steps.

        Args:
            simulation_id: ID of the simulation
            num_steps: Number of steps to execute

        Returns:
            List of step results
        """
        if simulation_id not in self._active_simulations:
            raise ValueError(f"Simulation {simulation_id} not found")

        sim = self._active_simulations[simulation_id]
        steps = []

        for i in range(num_steps):
            step_result = await self._execute_step(simulation_id, sim["current_step"] + i)
            sim["steps"].append(step_result)
            steps.append(step_result)

        sim["current_step"] += num_steps
        return steps

    async def _execute_step(
        self,
        simulation_id: str,
        step_num: int,
    ) -> SimulationStep:
        """Execute a single simulation step."""
        sim = self._active_simulations[simulation_id]
        config = sim["config"]
        timestamp = step_num * 1.0  # Time unit per step

        events = []

        # Process agent actions based on simulation type
        if config.simulation_type == SimulationType.AGENT_BASED:
            events = await self._agent_based_step(sim, step_num)
        elif config.simulation_type == SimulationType.DISCRETE_EVENT:
            events = await self._discrete_event_step(sim, step_num)
        else:
            events = await self._hybrid_step(sim, step_num)

        # Record events
        sim["completed_events"].extend(events)

        # Create step result
        step_result = SimulationStep(
            step_number=step_num,
            timestamp=timestamp,
            events=events,
            state_snapshot=self._get_state_snapshot(sim),
            metrics=self._calculate_step_metrics(sim, events),
        )

        return step_result

    async def _agent_based_step(
        self,
        sim: Dict[str, Any],
        step_num: int,
    ) -> List[SimulationEvent]:
        """Execute agent-based simulation step."""
        events = []
        agents = sim["agents"]
        agent_states = sim["agent_states"]

        # Process each agent
        for agent in agents:
            state = agent_states[agent.id]

            # Skip inactive agents
            if state.health <= 0 or state.energy <= 0:
                continue

            # Determine agent action
            action = await self._determine_agent_action(agent, state, sim, step_num)

            # Create action event
            event = SimulationEvent(
                event_type=EventType.AGENT_ACTION,
                timestamp=step_num,
                source=agent.id,
                target=action.get("target"),
                data=action,
            )
            events.append(event)

            # Apply action effects
            await self._apply_action_effects(agent, state, action, sim)

            # Process interactions
            if action.get("type") == "interact":
                interaction_events = await self._process_interaction(
                    agent, action, sim, step_num
                )
                events.extend(interaction_events)

        return events

    async def _discrete_event_step(
        self,
        sim: Dict[str, Any],
        step_num: int,
    ) -> List[SimulationEvent]:
        """Execute discrete event simulation step."""
        events = []
        event_queue = sim["event_queue"]

        # Process events scheduled for this time
        while event_queue and event_queue[0].timestamp <= step_num:
            import heapq
            event = heapq.heappop(event_queue)

            # Process the event
            new_events = await self._process_event(event, sim)
            events.append(event)
            events.extend(new_events)

            # Schedule follow-up events
            for follow_up in new_events:
                heapq.heappush(event_queue, follow_up)

        return events

    async def _hybrid_step(
        self,
        sim: Dict[str, Any],
        step_num: int,
    ) -> List[SimulationEvent]:
        """Execute hybrid simulation step."""
        # Combine agent-based and discrete event
        events = await self._agent_based_step(sim, step_num)
        events.extend(await self._discrete_event_step(sim, step_num))
        return events

    async def _determine_agent_action(
        self,
        agent: Agent,
        state: AgentState,
        sim: Dict[str, Any],
        step_num: int,
    ) -> Dict[str, Any]:
        """Determine what action an agent takes."""
        # Use LLM for intelligent decision if available
        if self.llm:
            return await self._llm_determine_action(agent, state, sim, step_num)

        # Default behavior based on goals and state
        action_types = ["move", "gather", "interact", "rest", "produce", "consume"]

        # Weight by agent state
        weights = {
            "rest": max(0, 1.0 - state.energy) * 2,
            "gather": 0.5 if state.energy > 0.2 else 0.1,
            "produce": 0.3 if state.energy > 0.3 else 0.1,
            "interact": 0.4,
            "move": 0.3,
            "consume": 0.5 if state.energy < 0.5 else 0.1,
        }

        # Normalize weights
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        # Select action
        action_type = random.choices(
            list(weights.keys()),
            weights=list(weights.values()),
        )[0]

        return {
            "type": action_type,
            "agent_id": agent.id,
            "timestamp": step_num,
            "target": random.choice([a.id for a in sim["agents"] if a.id != agent.id]) if action_type == "interact" else None,
        }

    async def _llm_determine_action(
        self,
        agent: Agent,
        state: AgentState,
        sim: Dict[str, Any],
        step_num: int,
    ) -> Dict[str, Any]:
        """Use LLM to determine agent action."""
        prompt = f"""Determine the next action for an agent in a simulation.

AGENT:
- ID: {agent.id}
- Name: {agent.name}
- Type: {agent.type.value}
- Capabilities: {agent.capabilities}
- Health: {state.health:.2f}
- Energy: {state.energy:.2f}
- Resources: {state.resources}
- Active Goal: {state.active_goal}

ENVIRONMENT:
- Step: {step_num}
- Available Resources: {sim['env_state'].resources}

Choose an action type from: move, gather, interact, rest, produce, consume
Provide response in JSON format: {{"type": "action_type", "target": "target_id_or_null", "reasoning": "brief reason"}}"""

        try:
            response = await self.llm.generate_text(prompt, temperature=0.7)
            import json
            import re
            json_match = re.search(r'\{[\s\S]*?\}', response)
            if json_match:
                action = json.loads(json_match.group())
                action["agent_id"] = agent.id
                action["timestamp"] = step_num
                return action
        except Exception as e:
            logger.debug(f"LLM action determination failed: {e}")

        # Fallback to default
        return await self._determine_agent_action(agent, state, sim, step_num)

    async def _apply_action_effects(
        self,
        agent: Agent,
        state: AgentState,
        action: Dict[str, Any],
        sim: Dict[str, Any],
    ) -> None:
        """Apply the effects of an action to agent state."""
        action_type = action.get("type", "rest")

        if action_type == "rest":
            state.energy = min(1.0, state.energy + 0.2)
            state.status = "resting"

        elif action_type == "move":
            state.energy = max(0, state.energy - 0.1)
            # Update position
            dx, dy, dz = random.uniform(-1, 1), random.uniform(-1, 1), 0
            state.position = (
                state.position[0] + dx,
                state.position[1] + dy,
                state.position[2] + dz,
            )
            state.status = "moving"

        elif action_type == "gather":
            state.energy = max(0, state.energy - 0.15)
            # Add random resource
            resource_type = random.choice(["food", "materials", "energy"])
            state.resources[resource_type] = state.resources.get(resource_type, 0) + random.uniform(0.5, 1.5)
            state.status = "gathering"

        elif action_type == "produce":
            state.energy = max(0, state.energy - 0.2)
            # Convert resources to value
            if state.resources.get("materials", 0) >= 1:
                state.resources["materials"] -= 1
                state.resources["products"] = state.resources.get("products", 0) + 1
            state.status = "producing"

        elif action_type == "consume":
            if state.resources.get("food", 0) >= 0.5:
                state.resources["food"] -= 0.5
                state.energy = min(1.0, state.energy + 0.3)
                state.health = min(1.0, state.health + 0.1)
            state.status = "consuming"

        elif action_type == "interact":
            state.energy = max(0, state.energy - 0.1)
            state.status = "interacting"

    async def _process_interaction(
        self,
        agent: Agent,
        action: Dict[str, Any],
        sim: Dict[str, Any],
        step_num: int,
    ) -> List[SimulationEvent]:
        """Process interaction between agents."""
        events = []
        target_id = action.get("target")

        if not target_id or target_id not in sim["agent_states"]:
            return events

        target_state = sim["agent_states"][target_id]

        # Determine interaction outcome
        interaction_types = ["trade", "collaborate", "compete", "communicate"]
        interaction_type = random.choice(interaction_types)

        event = SimulationEvent(
            event_type=EventType.AGENT_INTERACTION,
            timestamp=step_num,
            source=agent.id,
            target=target_id,
            data={
                "type": interaction_type,
                "outcome": "success" if random.random() > 0.3 else "failure",
            },
        )
        events.append(event)

        # Apply interaction effects
        if interaction_type == "trade":
            # Simple resource exchange
            for res in ["food", "materials"]:
                if sim["agent_states"][agent.id].resources.get(res, 0) > 0:
                    sim["agent_states"][agent.id].resources[res] -= 0.5
                    target_state.resources[res] = target_state.resources.get(res, 0) + 0.5
                    break

        return events

    async def _process_event(
        self,
        event: SimulationEvent,
        sim: Dict[str, Any],
    ) -> List[SimulationEvent]:
        """Process a discrete event and generate follow-up events."""
        follow_ups = []

        # Call registered handlers
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            result = await handler(event, sim)
            if result:
                follow_ups.extend(result)

        return follow_ups

    async def _check_stop_conditions(self, sim: Dict[str, Any]) -> bool:
        """Check if stop conditions are met."""
        config = sim["config"]

        for condition in config.stop_conditions:
            cond_type = condition.get("type")

            if cond_type == "goal_achieved":
                # Check if any agent achieved their goal
                for agent_id, state in sim["agent_states"].items():
                    if condition.get("goal_id") in state.goals:
                        return True

            elif cond_type == "resource_depleted":
                resource_id = condition.get("resource_id")
                if resource_id in sim["env_state"].resources:
                    if sim["env_state"].resources[resource_id].get("quantity", 0) <= 0:
                        return True

            elif cond_type == "step_count":
                max_steps = condition.get("max_steps", config.max_steps)
                if sim["current_step"] >= max_steps:
                    return True

            elif cond_type == "agent_count":
                min_agents = condition.get("min_agents", 0)
                active_agents = sum(
                    1 for s in sim["agent_states"].values()
                    if s.health > 0
                )
                if active_agents < min_agents:
                    return True

        return False

    async def _detect_emergent_patterns(
        self,
        sim: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Detect emergent patterns in simulation."""
        patterns = []

        # Check for clustering behavior
        positions = [s.position for s in sim["agent_states"].values()]
        if positions:
            avg_dist = sum(
                ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                for i, p1 in enumerate(positions)
                for p2 in positions[i+1:]
            ) / max(1, len(positions) * (len(positions)-1) / 2)

            if avg_dist < 5.0:
                patterns.append({
                    "type": "clustering",
                    "description": "Agents are clustering together",
                    "metric": avg_dist,
                    "step": sim["current_step"],
                })

        # Check for resource specialization
        resource_counts = {}
        for state in sim["agent_states"].values():
            dominant_resource = max(
                state.resources.keys(),
                key=lambda r: state.resources.get(r, 0)
            ) if state.resources else None
            if dominant_resource:
                resource_counts[dominant_resource] = resource_counts.get(dominant_resource, 0) + 1

        if len(resource_counts) > 2:
            patterns.append({
                "type": "specialization",
                "description": "Agents are specializing in different resources",
                "distribution": resource_counts,
                "step": sim["current_step"],
            })

        return patterns

    async def _take_snapshot(self, sim: Dict[str, Any]) -> None:
        """Take a snapshot of simulation state."""
        # Snapshots are stored in step results
        pass

    def _get_state_snapshot(self, sim: Dict[str, Any]) -> Dict[str, Any]:
        """Get a snapshot of the current state."""
        return {
            "step": sim["current_step"],
            "agents": {
                aid: {
                    "position": state.position,
                    "health": state.health,
                    "energy": state.energy,
                    "resources": state.resources.copy(),
                    "status": state.status,
                }
                for aid, state in sim["agent_states"].items()
            },
            "environment": {
                "resources": sim["env_state"].resources.copy(),
                "conditions": sim["env_state"].conditions.copy(),
            },
        }

    def _calculate_metrics(self, sim: Dict[str, Any]) -> Dict[str, float]:
        """Calculate simulation metrics."""
        agent_states = list(sim["agent_states"].values())

        if not agent_states:
            return {}

        return {
            "avg_health": sum(s.health for s in agent_states) / len(agent_states),
            "avg_energy": sum(s.energy for s in agent_states) / len(agent_states),
            "active_agents": sum(1 for s in agent_states if s.health > 0),
            "total_resources": sum(
                sum(s.resources.values()) for s in agent_states
            ),
            "steps_completed": sim["current_step"],
        }

    def _calculate_step_metrics(
        self,
        sim: Dict[str, Any],
        events: List[SimulationEvent],
    ) -> Dict[str, float]:
        """Calculate metrics for a single step."""
        return {
            "events_count": len(events),
            "action_events": sum(1 for e in events if e.event_type == EventType.AGENT_ACTION),
            "interaction_events": sum(1 for e in events if e.event_type == EventType.AGENT_INTERACTION),
        }

    def _compile_agent_stats(self, sim: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Compile statistics for each agent."""
        return {
            aid: {
                "final_health": state.health,
                "final_energy": state.energy,
                "total_resources": sum(state.resources.values()),
                "status": state.status,
            }
            for aid, state in sim["agent_states"].items()
        }

    def _compile_resource_stats(self, sim: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Compile resource statistics."""
        return sim["env_state"].resources.copy()

    def _aggregate_monte_carlo_results(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, float]:
        """Aggregate Monte Carlo results."""
        if not results:
            return {}

        metrics_keys = set()
        for r in results:
            metrics_keys.update(r.metrics.keys())

        aggregated = {}
        for key in metrics_keys:
            values = [r.metrics.get(key, 0) for r in results]
            aggregated[key] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "std": (sum((v - sum(values)/len(values))**2 for v in values) / len(values))**0.5,
            }

        return aggregated

    def _calculate_confidence_intervals(
        self,
        results: List[SimulationResult],
        confidence: float = 0.95,
    ) -> Dict[str, Tuple[float, float]]:
        """Calculate confidence intervals for metrics."""
        import math

        intervals = {}
        metrics_keys = set()
        for r in results:
            metrics_keys.update(r.metrics.keys())

        n = len(results)
        if n < 2:
            return intervals

        # Use t-distribution for small samples
        t_value = 1.96 if n > 30 else 2.0  # Simplified

        for key in metrics_keys:
            values = [r.metrics.get(key, 0) for r in results]
            mean = sum(values) / n
            std = (sum((v - mean)**2 for v in values) / (n-1))**0.5 if n > 1 else 0
            margin = t_value * std / math.sqrt(n)
            intervals[key] = (mean - margin, mean + margin)

        return intervals

    def _calculate_distribution_stats(
        self,
        results: List[SimulationResult],
    ) -> Dict[str, Dict[str, float]]:
        """Calculate distribution statistics."""
        # Percentiles, skewness, kurtosis would go here
        return {}

    def _identify_outliers(
        self,
        results: List[SimulationResult],
    ) -> List[Dict[str, Any]]:
        """Identify outlier simulations."""
        outliers = []

        # Use IQR method
        if len(results) < 4:
            return outliers

        durations = sorted([r.duration for r in results])
        q1 = durations[len(durations) // 4]
        q3 = durations[3 * len(durations) // 4]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        for r in results:
            if r.duration < lower_bound or r.duration > upper_bound:
                outliers.append({
                    "simulation_id": r.simulation_id,
                    "duration": r.duration,
                    "reason": "Duration outlier",
                })

        return outliers

    def register_event_handler(
        self,
        event_type: EventType,
        handler: Callable,
    ) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def get_simulation_status(self, simulation_id: str) -> Optional[SimulationStatus]:
        """Get the status of a simulation."""
        if simulation_id in self._active_simulations:
            return self._active_simulations[simulation_id]["status"]
        return None

    def pause_simulation(self, simulation_id: str) -> bool:
        """Pause a running simulation."""
        if simulation_id in self._active_simulations:
            sim = self._active_simulations[simulation_id]
            if sim["status"] == SimulationStatus.RUNNING:
                sim["status"] = SimulationStatus.PAUSED
                return True
        return False

    def resume_simulation(self, simulation_id: str) -> bool:
        """Resume a paused simulation."""
        if simulation_id in self._active_simulations:
            sim = self._active_simulations[simulation_id]
            if sim["status"] == SimulationStatus.PAUSED:
                sim["status"] = SimulationStatus.RUNNING
                return True
        return False

    def stop_simulation(self, simulation_id: str) -> bool:
        """Stop a simulation."""
        if simulation_id in self._active_simulations:
            self._active_simulations[simulation_id]["status"] = SimulationStatus.COMPLETED
            return True
        return False

    def cleanup_simulation(self, simulation_id: str) -> bool:
        """Remove a completed simulation."""
        if simulation_id in self._active_simulations:
            del self._active_simulations[simulation_id]
            return True
        return False
