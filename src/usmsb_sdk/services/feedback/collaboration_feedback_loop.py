"""
Collaboration Feedback Loop

Phase 3 of USMSB Agent Platform implementation.

Implements the USMSB Feedback Loop:
- Contract completion → Evaluation → Soul Update → Adaptation

This is the core mechanism that makes the platform "learn":
- Each completed contract updates the agents' Inferred Souls
- Inferred Souls are used for better matching
- AdaptationEngine records patterns for platform evolution

Also updates ReputationService based on InferredSoul data.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from usmsb_sdk.services.agent_soul import AgentSoulManager
from usmsb_sdk.services.agent_soul.models import AgentSoul
from usmsb_sdk.services.schema import (
    ContractValueFlowDB,
    FeedbackEventDB,
    ReputationSnapshotDB,
)
from usmsb_sdk.services.value_contract import ValueContractService
from usmsb_sdk.services.value_contract.models import BaseValueContract

logger = logging.getLogger(__name__)


@dataclass
class ValueDeliveryEvaluation:
    """
    Evaluation result after a contract completes.

    Compares promised value vs actual delivery.
    """
    contract_id: str
    success: bool

    # Value match scores (0.0 ~ 1.0)
    value_match_score: float = 0.0
    quality_score: float = 0.0
    on_time_score: float = 0.0
    overall_score: float = 0.0

    # What was promised
    promised_value: dict[str, Any] = field(default_factory=dict)
    # What was delivered
    actual_delivery: dict[str, Any] = field(default_factory=dict)

    # Disputes or issues
    issues: list[str] = field(default_factory=list)

    # Timestamp
    evaluated_at: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "success": self.success,
            "value_match_score": self.value_match_score,
            "quality_score": self.quality_score,
            "on_time_score": self.on_time_score,
            "overall_score": self.overall_score,
            "promised_value": self.promised_value,
            "actual_delivery": self.actual_delivery,
            "issues": self.issues,
            "evaluated_at": self.evaluated_at,
        }


@dataclass
class AdaptationRecord:
    """
    Record of an experience for the AdaptationEvolutionEngine.

    Sent to USMSB Core's AdaptationEvolutionEngine for learning.
    """
    record_id: str
    agent_id: str
    contract_id: str
    adaptation_type: str  # "soul_update" | "capability_added" | "risk_learned"
    experience: dict[str, Any]  # What happened
    outcome: dict[str, Any]  # Result
    timestamp: float = 0.0


class CollaborationFeedbackLoop:
    """
    Feedback Loop for contract completion.

    Flow:
    1. Contract completes (confirmed delivery)
    2. Evaluate delivery against promises
    3. Update each party's InferredSoul
    4. Record AdaptationRecord for Core engine
    5. Update ReputationSnapshot

    This is event-driven - triggered when confirm_delivery is called.
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.soul_manager = AgentSoulManager(db_session)
        self.contract_service = ValueContractService(db_session)

    async def process_contract_completion(
        self,
        contract_id: str,
        actual_outcome: dict[str, Any],
        delivery_data: dict[str, Any],
    ) -> ValueDeliveryEvaluation:
        """
        Process a contract completion event.

        This is called when a contract's delivery is confirmed.

        Args:
            contract_id: Contract that completed
            actual_outcome: Actual outcome from delivery confirmation
            delivery_data: Detailed delivery data

        Returns:
            ValueDeliveryEvaluation
        """
        contract = await self.contract_service.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Step 1: Evaluate value delivery
        evaluation = await self._evaluate_value_delivery(
            contract, actual_outcome, delivery_data
        )

        # Step 2: Create feedback event
        await self._create_feedback_event(contract, evaluation)

        # Step 3: Update each party's InferredSoul
        for party_id in contract.parties:
            await self._update_agent_soul_inferred(
                party_id, contract_id, evaluation, delivery_data
            )

        # Step 4: Record adaptation
        await self._record_adaptation(contract, evaluation)

        # Step 5: Update reputation snapshots
        for party_id in contract.parties:
            await self._update_reputation_snapshot(party_id, evaluation)

        logger.info(f"Feedback loop processed for contract {contract_id}: success={evaluation.success}")
        return evaluation

    async def _evaluate_value_delivery(
        self,
        contract: BaseValueContract,
        actual_outcome: dict[str, Any],
        delivery_data: dict[str, Any],
    ) -> ValueDeliveryEvaluation:
        """
        Evaluate how well the contract was fulfilled.

        Compares:
        - Promised deliverables vs actual delivery
        - Timeline adherence
        - Quality assessment
        """
        evaluation = ValueDeliveryEvaluation(
            contract_id=contract.contract_id,
            success=actual_outcome.get("success", False),
            evaluated_at=time.time(),
        )

        # Extract promised values
        promised = {}
        if hasattr(contract, "price_vibe"):
            promised["price_vibe"] = contract.price_vibe
        if hasattr(contract, "task_definition"):
            promised["deliverables"] = contract.task_definition.get("deliverables", [])
        if contract.transformation_path:
            promised["transformation_path"] = contract.transformation_path

        evaluation.promised_value = promised
        evaluation.actual_delivery = delivery_data

        # Calculate scores
        if evaluation.success:
            # Quality assessment
            # D7 Fix: Use conservative default 0.5 instead of 0.8 when missing
            quality = delivery_data.get("quality_score", 0.5)
            evaluation.quality_score = min(1.0, max(0.0, quality))

            # On-time assessment
            if hasattr(contract, "deadline") and contract.deadline > 0:
                delivered_at = delivery_data.get("delivered_at", time.time())
                if delivered_at <= contract.deadline:
                    evaluation.on_time_score = 1.0
                else:
                    delay_hours = (delivered_at - contract.deadline) / 3600
                    evaluation.on_time_score = max(0.0, 1.0 - delay_hours / 24.0)
            else:
                evaluation.on_time_score = 0.8  # No deadline = assume ok

            # Value match
            evaluation.value_match_score = evaluation.quality_score * evaluation.on_time_score

            # Overall
            evaluation.overall_score = (
                evaluation.quality_score * 0.5 +
                evaluation.on_time_score * 0.3 +
                evaluation.value_match_score * 0.2
            )
        else:
            # Failed delivery
            evaluation.quality_score = 0.0
            evaluation.on_time_score = 0.0
            evaluation.value_match_score = 0.0
            evaluation.overall_score = 0.0
            evaluation.issues = actual_outcome.get("issues", ["Delivery failed"])

        return evaluation

    async def _create_feedback_event(
        self,
        contract: BaseValueContract,
        evaluation: ValueDeliveryEvaluation,
    ) -> None:
        """Record feedback event for analytics."""
        demand_agent = contract.parties[0] if contract.parties else ""
        supply_agent = contract.parties[1] if len(contract.parties) > 1 else ""

        event = FeedbackEventDB(
            event_id=f"evt-{int(time.time())}-{contract.contract_id[:8]}",
            contract_id=contract.contract_id,
            demand_agent_id=demand_agent,
            supply_agent_id=supply_agent,
            event_type="completion",
            event_data=evaluation.to_dict(),
            process_status="processed",
            processed_at=time.time(),
            created_at=time.time(),
        )

        self.db.add(event)
        self.db.commit()

    async def _update_agent_soul_inferred(
        self,
        agent_id: str,
        contract_id: str,
        evaluation: ValueDeliveryEvaluation,
        delivery_data: dict[str, Any],
    ) -> None:
        """Update an agent's InferredSoul from contract outcome."""
        try:
            behavior_event = {
                "contract_id": contract_id,
                "success": evaluation.success,
                "response_time_minutes": delivery_data.get("response_time_minutes", 0),
                "quality_score": evaluation.quality_score,
                "value_match_score": evaluation.value_match_score,
                "on_time": evaluation.on_time_score > 0.8,
                "timestamp": time.time(),
                "capability": delivery_data.get("capability"),
            }

            await self.soul_manager.update_inferred_from_event(agent_id, behavior_event)

            # Also add to negotiation history if applicable
            if evaluation.success:
                await self.soul_manager.add_negotiation_result(
                    agent_id,
                    {
                        "session_id": contract_id,
                        "result": "success",
                        "counterparty_id": None,
                        "timestamp": time.time(),
                    }
                )

        except Exception as e:
            logger.error(f"Failed to update InferredSoul for {agent_id}: {e}")

    async def _record_adaptation(
        self,
        contract: BaseValueContract,
        evaluation: ValueDeliveryEvaluation,
    ) -> None:
        """
        Record adaptation experience for USMSB Core's AdaptationEvolutionEngine.

        This sends data to the Core engine for platform-wide learning.

        D3 Fix: Now actually calls the USMSB Core AdaptationEvolutionEngine.
        """
        from usmsb_sdk.core.logic.core_engines import (
            AdaptationRecord,
            AdaptationEvolutionEngine,
        )
        from usmsb_sdk.core.logic.core_engines import LogicEngineRegistry

        for party_id in contract.parties:
            record = AdaptationRecord(
                record_id=f"adapt-{int(time.time())}-{party_id[:8]}",
                agent_id=party_id,
                contract_id=contract.contract_id,
                adaptation_type="soul_update",
                experience={
                    "contract_type": contract.contract_type,
                    "quality_score": evaluation.quality_score,
                    "value_match": evaluation.value_match_score,
                    "on_time": evaluation.on_time_score > 0.8,
                    "overall_score": evaluation.overall_score,
                },
                outcome={
                    "success": evaluation.success,
                    "overall_score": evaluation.overall_score,
                },
                timestamp=time.time(),
            )

            # D3 Fix: Actually call the Core Engine instead of just logging
            try:
                # Get the global engine registry
                engine_registry = LogicEngineRegistry()
                adaptation_engine = engine_registry.get("adaptation")

                if adaptation_engine is not None:
                    await adaptation_engine.record(record)
                    logger.info(
                        f"Adaptation record sent to Core engine for {party_id}: "
                        f"type={record.adaptation_type}, score={evaluation.overall_score:.2f}"
                    )
                else:
                    # Fallback: record locally if Core engine not initialized
                    logger.warning(
                        f"AdaptationEvolutionEngine not available, recording locally for {party_id}"
                    )
                    self._record_adaptation_locally(record)

            except Exception as e:
                logger.error(f"Failed to send adaptation record to Core engine: {e}")
                # Fallback: record locally
                self._record_adaptation_locally(record)

    def _record_adaptation_locally(self, record) -> None:
        """
        Fallback: Record adaptation locally when Core engine unavailable.

        This stores adaptation records in memory for later sync.
        """
        if not hasattr(self, "_local_adaptation_records"):
            self._local_adaptation_records = []

        self._local_adaptation_records.append({
            "record_id": record.record_id,
            "agent_id": record.agent_id,
            "contract_id": record.contract_id,
            "adaptation_type": record.adaptation_type,
            "experience": record.experience,
            "outcome": record.outcome,
            "timestamp": record.timestamp,
            "synced": False,
        })

        # Keep last 1000 local records
        if len(self._local_adaptation_records) > 1000:
            self._local_adaptation_records = self._local_adaptation_records[-1000:]

        logger.info(f"Adaptation record stored locally: {record.record_id}")

    def sync_local_adaptation_records(self) -> int:
        """
        Sync locally stored adaptation records to Core engine.

        Returns number of records synced.
        """
        from usmsb_sdk.core.logic.core_engines import (
            AdaptationRecord,
            AdaptationEvolutionEngine,
        )
        from usmsb_sdk.core.logic.core_engines import LogicEngineRegistry

        if not hasattr(self, "_local_adaptation_records"):
            return 0

        synced_count = 0
        engine_registry = LogicEngineRegistry()
        adaptation_engine = engine_registry.get("adaptation")

        if adaptation_engine is None:
            logger.warning("Cannot sync: AdaptationEvolutionEngine not available")
            return 0

        for local_record in self._local_adaptation_records:
            if local_record.get("synced"):
                continue

            try:
                record = AdaptationRecord(
                    record_id=local_record["record_id"],
                    agent_id=local_record["agent_id"],
                    contract_id=local_record["contract_id"],
                    adaptation_type=local_record["adaptation_type"],
                    experience=local_record["experience"],
                    outcome=local_record["outcome"],
                    timestamp=local_record["timestamp"],
                )

                import asyncio
                loop = asyncio.get_event_loop()
                loop.run_until_complete(adaptation_engine.record(record))

                local_record["synced"] = True
                synced_count += 1

            except Exception as e:
                logger.error(f"Failed to sync adaptation record {local_record['record_id']}: {e}")

        # Remove synced records
        self._local_adaptation_records = [
            r for r in self._local_adaptation_records if not r.get("synced")
        ]

        logger.info(f"Synced {synced_count} adaptation records to Core engine")
        return synced_count

    async def _update_reputation_snapshot(
        self,
        agent_id: str,
        evaluation: ValueDeliveryEvaluation,
    ) -> None:
        """Update reputation snapshot for audit trail."""
        soul = await self.soul_manager.get_soul(agent_id)

        if not soul or not soul.inferred:
            return

        snapshot = ReputationSnapshotDB(
            snapshot_id=f"snap-{int(time.time())}-{agent_id[:8]}",
            agent_id=agent_id,
            success_rate=soul.inferred.actual_success_rate,
            response_time_score=max(0.0, 1.0 - soul.inferred.avg_response_time_minutes / 3600),
            value_alignment_score=soul.inferred.value_alignment_score,
            collaboration_count=soul.inferred.collaboration_count,
            overall_score=await self.soul_manager.get_reputation(agent_id),
            source="inferred_from_behavior",
            created_at=time.time(),
        )

        self.db.add(snapshot)
        self.db.commit()


class FeedbackLoopProcessor:
    """
    Processes pending feedback events.

    Used for batch processing of feedback events that couldn't be processed
    immediately (e.g., async evaluation).
    """

    def __init__(self, db_session: Session):
        self.db = db_session
        self.feedback_loop = CollaborationFeedbackLoop(db_session)

    async def process_pending_events(self, batch_size: int = 100) -> int:
        """
        Process pending feedback events.

        Args:
            batch_size: Maximum events to process in one batch

        Returns:
            Number of events processed
        """
        events = self.db.query(FeedbackEventDB).filter(
            FeedbackEventDB.process_status == "pending"
        ).limit(batch_size).all()

        processed = 0
        for event in events:
            try:
                actual_outcome = event.event_data or {}
                delivery_data = actual_outcome.get("delivery_data", {})

                await self.feedback_loop.process_contract_completion(
                    contract_id=event.contract_id,
                    actual_outcome=actual_outcome,
                    delivery_data=delivery_data,
                )

                event.process_status = "processed"
                event.processed_at = time.time()
                processed += 1

            except Exception as e:
                logger.error(f"Failed to process event {event.event_id}: {e}")
                event.process_status = "failed"

        self.db.commit()
        return processed
