"""Adversarial economic safety checks; no provider/model/wallet network calls."""
import asyncio

import pytest

from usmsb_sdk.economic.pea_market import LLMQualityGate, LLMCapabilityMatcher, PeaMarket, SupplierInfo
from usmsb_sdk.economic.vibe_settlement import VibeSettlementBackend, make_ledger_transfer_fn, make_wallet_transfer_fn, WalletRegistry
from usmsb_sdk.services.zk_credential_service import ZKCredentialService, ZKProof, CredentialType, PrivateInputs


@pytest.mark.parametrize("raw", [None, "garbage", '{}', '{"verdict":"yes"}', '{"verdict":true}', '{"verdict":null}', '[{}]'])
def test_invalid_reviews_do_not_pass(raw):
    assert LLMQualityGate._parse(raw).verdict == "unknown"


async def test_reviewer_error_is_not_acceptance():
    class Offline:
        async def complete(self, *args):
            raise TimeoutError()
    assert (await LLMQualityGate(Offline()).judge("task", "delivery")).verdict == "unknown"


async def test_open_idempotency_and_concurrent_release(tmp_path):
    ledger = {"buyer": 100}
    path = str(tmp_path / "escrows.db")
    a = VibeSettlementBackend(make_ledger_transfer_fn(ledger), journal_path=path)
    b = VibeSettlementBackend(make_ledger_transfer_fn(ledger), journal_path=path)
    args = dict(escrow_id="one", payer="buyer", payee="seller", amount=100)
    assert await a.open_escrow(**args)
    assert await b.open_escrow(**args)
    assert not await b.open_escrow(**{**args, "amount": 99})
    result = await asyncio.gather(a.release_escrow(escrow_id="one"), b.refund_escrow(escrow_id="one"))
    assert sum(result) == 1
    assert ledger["buyer"] == 0 and ledger["seller"] == 100
    a.close()
    b.close()


@pytest.mark.parametrize("mode", ["false", "timeout", "cancel"])
async def test_partial_payout_survives_restart_and_never_retries(tmp_path, mode):
    calls = []
    async def transfer(source, target, amount):
        calls.append((source, target, amount))
        if target == "second":
            if mode == "timeout":
                raise TimeoutError()
            if mode == "cancel":
                raise asyncio.CancelledError()
            return False
        return True
    path = str(tmp_path / "escrows.db")
    backend = VibeSettlementBackend(transfer, journal_path=path)
    assert await backend.open_escrow(escrow_id="one", payer="buyer", payee="pool", amount=100)
    if mode == "cancel":
        with pytest.raises(asyncio.CancelledError):
            await backend.settle_split(escrow_id="one", splits={"first": 60, "second": 40})
    else:
        assert not await backend.settle_split(escrow_id="one", splits={"first": 60, "second": 40})
    backend.close()
    reopened = VibeSettlementBackend(transfer, journal_path=path)
    assert reopened.escrow_state("one") == "uncertain"
    assert reopened.escrow_record("one")["attempts"][1]["status"] == "confirmed"
    assert not await reopened.settle_split(escrow_id="one", splits={"first": 60, "second": 40})
    assert not await reopened.refund_escrow(escrow_id="one")
    assert not await reopened.open_escrow(escrow_id="one", payer="buyer", payee="pool", amount=100)
    assert len(calls) == 3
    reopened.close()


@pytest.mark.parametrize("splits", [{}, None, {"seller": float("nan")}, {"seller": float("inf")},
    {"seller": -1}, {"seller": 99}, {"seller": 101}, {"__vibe_escrow__": 100}])
async def test_invalid_split_does_not_move_money(splits):
    ledger = {"buyer": 100}
    backend = VibeSettlementBackend(make_ledger_transfer_fn(ledger))
    assert await backend.open_escrow(escrow_id="one", payer="buyer", payee="seller", amount=100)
    assert not await backend.settle_split(escrow_id="one", splits=splits)
    assert backend.escrow_state("one") == "open"
    assert ledger["__vibe_escrow__"] == 100
    backend.close()


def test_wallet_cannot_use_ephemeral_journal():
    with pytest.raises(ValueError, match="durable"):
        VibeSettlementBackend(make_wallet_transfer_fn(WalletRegistry()))


async def test_joint_order_does_not_treat_missing_quality_as_pass():
    class Supplier:
        async def submit(self, params):
            return {"status": {"state": "completed"}, "metadata": {}}
    market = PeaMarket(ledger={"buyer": 100}, matcher=LLMCapabilityMatcher(None))
    market.register_supplier(SupplierInfo("seller", "writing", runtime=Supplier()))
    result = await market.joint_order(from_id="buyer", task="write", assignments={"seller": "write"}, total_reward=100)
    assert result["status"] == "review_required"
    assert market.settlement.escrow_state(result["escrow_id"]) == "open"
    assert market.ledger.get("seller", 0) == 0


async def test_joint_order_reports_failed_split(monkeypatch):
    class Supplier:
        async def submit(self, params):
            return {"status": {"state": "completed", "message": {"parts": [{"text": "work"}]}},
                    "metadata": {"quality_gate": "passed"}}
    market = PeaMarket(ledger={"buyer": 100}, matcher=LLMCapabilityMatcher(None))
    market.register_supplier(SupplierInfo("seller", "writing", runtime=Supplier()))
    async def failure(**kwargs):
        return False
    monkeypatch.setattr(market.settlement, "settle_split", failure)
    result = await market.joint_order(from_id="buyer", task="write", assignments={"seller": "write"}, total_reward=100)
    assert result["status"] == "settlement_unconfirmed"


async def test_zk_placeholder_never_grants_credentials():
    service = ZKCredentialService()
    assert await service.generate_proof(CredentialType.IDENTITY, PrivateInputs(90, 100, True, 42), {}) is None
    forged = ZKProof((1, 2), ((3, 4), (5, 6)), (7, 8), [123, 456])
    assert await service.issue_credential("holder", CredentialType.IDENTITY, 86400, forged, 99) is None
    assert not await service.verify_credential("credential", forged)
    assert not service.has_credential_type("holder", CredentialType.IDENTITY)
