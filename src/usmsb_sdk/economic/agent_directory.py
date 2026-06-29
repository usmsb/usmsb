"""Agent 目录 —— 让能力发现从"市场本地名录"扩到"全网"。

CapabilityDiscovery 原本只在 PeaMarket 手动注册的 suppliers 里检索。DirectoryProvider
把候选来源抽象出来：可以是市场本地名录、core_services.AgentRegistry（全网在线 agent）、
或 souls 目录。发现层据此对"全网" agent 按 LLM 语义×声誉排序。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from usmsb_sdk.economic.pea_market import SupplierInfo


@runtime_checkable
class DirectoryProvider(Protocol):
    """供应商目录来源：列出可被发现的 agent（带能力描述与声誉）。"""

    async def list_suppliers(self) -> list[SupplierInfo]: ...


class StaticDirectoryProvider:
    """静态目录（测试/固定名录用）。"""

    def __init__(self, suppliers: list[SupplierInfo]):
        self._suppliers = list(suppliers)

    async def list_suppliers(self) -> list[SupplierInfo]:
        return list(self._suppliers)


class RegistryDirectoryProvider:
    """把 core_services.AgentRegistry 的在线 agent 暴露为供应商目录（全网能力发现）。

    用 AgentProfile 的 description+capabilities 作为能力文本、reputation 作为声誉，
    交给 LLM 语义匹配。runtime 留空（远程 A2A 端点解析是后续工作；当前用于"发现/排序"）。
    """

    def __init__(self, registry: Any, *, online_only: bool = True, min_reputation: float = 0.0):
        self.registry = registry
        self.online_only = online_only
        self.min_reputation = min_reputation

    async def list_suppliers(self) -> list[SupplierInfo]:
        if self.online_only and hasattr(self.registry, "get_online_agents"):
            agents = self.registry.get_online_agents()
        elif hasattr(self.registry, "discover"):
            agents = self.registry.discover(min_reputation=self.min_reputation)
        else:
            agents = []
        out: list[SupplierInfo] = []
        for a in agents:
            rep = float(getattr(a, "reputation", 0.5) or 0.5)
            if rep < self.min_reputation:
                continue
            caps = ", ".join(getattr(a, "capabilities", []) or [])
            desc = getattr(a, "description", "") or ""
            text = f"{desc} | 能力：{caps}".strip(" |")
            # 远程 A2A 端点 URL（profile.metadata.a2a_url）→ 可跨进程派单
            meta = getattr(a, "metadata", {}) or {}
            url = str(meta.get("a2a_url", "")) if isinstance(meta, dict) else ""
            out.append(SupplierInfo(agent_id=a.id, capabilities=text or a.id, reputation=rep, url=url))
        return out


class CompositeDirectoryProvider:
    """合并多个目录来源（如 全网注册表 + 市场本地名录），按 agent_id 去重。"""

    def __init__(self, *providers: DirectoryProvider):
        self.providers = providers

    async def list_suppliers(self) -> list[SupplierInfo]:
        seen: dict[str, SupplierInfo] = {}
        for p in self.providers:
            for s in await p.list_suppliers():
                seen.setdefault(s.agent_id, s)  # 先到先得（前面的来源优先）
        return list(seen.values())
