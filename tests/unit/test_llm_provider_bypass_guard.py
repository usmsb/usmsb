from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check_llm_provider_bypasses.py"
SPEC = importlib.util.spec_from_file_location("usmsb_llm_provider_bypass_guard", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = guard
SPEC.loader.exec_module(guard)


def _reasons(source: str) -> list[str]:
    visitor = guard.Guard()
    visitor.visit(ast.parse(source))
    return [reason for _, reason in visitor.findings]


def test_guard_detects_sdk_import_calls_aliases_and_dynamic_imports():
    reasons = _reasons(
        """
import importlib
from openai import AsyncOpenAI

create_response = client.responses.create
create_response(model="gpt-test", input="hello")
importlib.import_module("openai.resources")
"""
    )

    assert any("provider SDK import" in reason for reason in reasons)
    assert any("provider SDK call" in reason for reason in reasons)
    assert any("dynamic provider SDK import" in reason for reason in reasons)


def test_guard_detects_relative_http_and_second_positional_request_targets():
    reasons = _reasons(
        """
import httpx
import requests

client = httpx.AsyncClient(base_url="https://api.openai.com/v1")

async def invoke(payload):
    await client.post("/custom-generation", json=payload)
    return requests.request("POST", "https://api.minimaxi.com/v1/embeddings", json=payload)
"""
    )

    assert len([reason for reason in reasons if "provider HTTP call" in reason]) == 2


def test_guard_does_not_flag_business_http_or_route_registration():
    reasons = _reasons(
        """
@router.post("/v1/responses")
async def compatibility_route():
    return {"ok": True}

async def send_business_message(client, payload):
    return await client.post("/api/messages/send", json=payload)
"""
    )

    assert reasons == []
