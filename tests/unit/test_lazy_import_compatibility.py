"""Import order must not be an undocumented dependency of the full SDK."""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "first_import",
    [
        "usmsb_sdk.economic.pea_market",
        "usmsb_sdk.services.order_service",
        "usmsb_sdk.agent_sdk.negotiation",
        "usmsb_sdk.agent_sdk.negotiated_order_manager",
    ],
)
def test_order_adapter_compatibility_in_fresh_process(first_import):
    source = str(Path(__file__).resolve().parents[2] / "src")
    script = f"""
import importlib, sys
sys.path.insert(0, {source!r})
importlib.import_module({first_import!r})
from usmsb_sdk.agent_sdk import (
    NegotiatedOrderManager, OrderCreationResult, NegotiationToOrderConfig,
)
from usmsb_sdk.agent_sdk import negotiated_order_manager as module
for name in ('NegotiatedOrderManager', 'OrderCreationResult', 'NegotiationToOrderConfig'):
    assert globals()[name] is getattr(module, name)
import usmsb_sdk.agent_sdk as sdk
assert 'NegotiatedOrderManager' in dir(sdk)
"""
    result = subprocess.run(
        [sys.executable, "-E", "-B", "-c", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
