"""L4/L5 可选插件开关单测（#4：兑现双坐标"认知模块不进主干"）。

用 MetaAgent.__new__ 绕过重型 __init__，只测 _maybe_init_cognitive_plugins 的门控。
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from usmsb_sdk.meta_agent.agent import MetaAgent
from usmsb_sdk.meta_agent.meta_agent_config import MetaAgentConfig


def test_config_default_and_toggle():
    cfg = MetaAgentConfig()
    assert cfg.enable_cognitive_plugins is True       # 默认保持向后兼容
    cfg2 = MetaAgentConfig(enable_cognitive_plugins=False)
    assert cfg2.enable_cognitive_plugins is False


async def test_disabled_skips_l4_l5():
    a = MetaAgent.__new__(MetaAgent)
    a.config = SimpleNamespace(enable_cognitive_plugins=False)
    a.l4_agent = "sentinel"
    a.l5_collective = "sentinel"
    called = {"l4": False, "l5": False}

    async def _l4():
        called["l4"] = True

    async def _l5():
        called["l5"] = True

    a._init_l4_agent = _l4
    a._init_l5_collective = _l5

    await a._maybe_init_cognitive_plugins()
    assert called == {"l4": False, "l5": False}        # 未调用
    assert a.l4_agent is None and a.l5_collective is None  # 显式清空


async def test_enabled_initializes_l4_l5():
    a = MetaAgent.__new__(MetaAgent)
    a.config = SimpleNamespace(enable_cognitive_plugins=True)
    called = {"l4": False, "l5": False}

    async def _l4():
        called["l4"] = True

    async def _l5():
        called["l5"] = True

    a._init_l4_agent = _l4
    a._init_l5_collective = _l5

    await a._maybe_init_cognitive_plugins()
    assert called == {"l4": True, "l5": True}           # 都被调用


async def test_default_missing_attr_treated_as_enabled():
    a = MetaAgent.__new__(MetaAgent)
    a.config = SimpleNamespace()                          # 无该属性
    called = {"l4": False}

    async def _l4():
        called["l4"] = True

    async def _l5():
        pass

    a._init_l4_agent = _l4
    a._init_l5_collective = _l5
    await a._maybe_init_cognitive_plugins()
    assert called["l4"] is True                           # getattr 默认 True
