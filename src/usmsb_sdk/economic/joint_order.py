"""联合订单分账：Shapley 值（多 PEA 组队，公平分配协同收益）。

原则边界：
- **判断/智能**（每个成员贡献多大）→ LLM（LLMContributionAssessor）。
- **公平分配**（Shapley 值）→ 数学（确定性算法，不是"智能"，用代码）。

Shapley 值 = 每个成员在所有加入顺序下的平均边际贡献，是合作博弈里唯一同时满足
有效性/对称性/虚拟性/可加性的分配，天然公平。N 小（组队 2~5 人）时精确计算即可。
"""

from __future__ import annotations

import json
import logging
from itertools import permutations
from typing import Any, Callable

logger = logging.getLogger(__name__)

# 特征函数：给定参与者子集 → 该联盟能创造的价值
CharacteristicFn = Callable[[frozenset], float]


def shapley_values(players: list[str], v: CharacteristicFn) -> dict[str, float]:
    """精确 Shapley 值：对所有加入顺序求平均边际贡献。"""
    n = len(players)
    if n == 0:
        return {}
    if n == 1:
        return {players[0]: v(frozenset(players))}
    shap = {p: 0.0 for p in players}
    perms = list(permutations(players))
    for perm in perms:
        coalition: set[str] = set()
        prev = v(frozenset())
        for p in perm:
            coalition.add(p)
            cur = v(frozenset(coalition))
            shap[p] += cur - prev
            prev = cur
    factor = len(perms)
    return {p: shap[p] / factor for p in players}


def additive_with_synergy(base: dict[str, float], synergy_bonus: float = 0.0) -> CharacteristicFn:
    """构造特征函数：联盟价值 = 成员基值之和 + 协同奖励（成员越多协同越大）。

    synergy_bonus=0 时退化为可加，Shapley 即各自基值；>0 时协同收益由 Shapley 公平分摊。
    """
    def v(coalition: frozenset) -> float:
        if not coalition:
            return 0.0
        total = sum(base.get(p, 0.0) for p in coalition)
        if len(coalition) >= 2:
            total += synergy_bonus * (len(coalition) - 1)
        return total
    return v


def distribute(total_reward: float, shapley: dict[str, float]) -> dict[str, float]:
    """把固定总报酬按 Shapley 值比例分配（保证求和精确=总报酬）。

    末位成员拿"余额"而非独立计算，避免浮点累积误差导致求和略超总额、
    进而在按额托管释放时尾款付不出。
    """
    if not shapley:
        return {}
    s = sum(max(0.0, x) for x in shapley.values())
    items = list(shapley.items())
    if s <= 0:
        per = total_reward / len(items)
        return {p: per for p, _ in items}
    payouts: dict[str, float] = {}
    allocated = 0.0
    for i, (p, val) in enumerate(items):
        if i == len(items) - 1:
            payouts[p] = total_reward - allocated  # 末位拿余额 → 精确求和
        else:
            amt = total_reward * (max(0.0, val) / s)
            payouts[p] = amt
            allocated += amt
    return payouts


class LLMContributionAssessor:
    """用 LLM 评估各成员对联合交付的贡献基值（0..1）。fallback=均等。"""

    _SYS = (
        "你是联合项目的贡献评审。根据【任务】和【各成员交付】，给每个成员一个 0~1 的贡献基值"
        "（看实质贡献，不必归一）。严格返回 JSON：{\"成员id\":分数, ...}。"
    )

    def __init__(self, chat: Any | None):
        self.chat = chat

    async def assess(self, task: str, deliveries: dict[str, str]) -> dict[str, float]:
        members = list(deliveries)
        if not members:
            return {}
        if self.chat is None:
            return {m: 1.0 for m in members}  # 均等
        listing = "\n".join(f"- {m}: {(d or '')[:200]}" for m, d in deliveries.items())
        try:
            raw = await self.chat.complete([
                {"role": "system", "content": self._SYS},
                {"role": "user", "content": f"任务：{task}\n各成员交付：\n{listing}"},
            ])
            parsed = self._parse(raw)
            scores = {m: max(0.0, min(1.0, float(parsed.get(m, 0.0)))) for m in members}
            if sum(scores.values()) <= 0:
                return {m: 1.0 for m in members}  # 全 0 → 均等兜底
            return scores
        except Exception as e:  # noqa: BLE001
            logger.warning("[contribution] LLM 评估失败：%s，均等", e)
            return {m: 1.0 for m in members}

    @staticmethod
    def _parse(raw: str) -> dict[str, float]:
        s = (raw or "").strip()
        st, en = s.find("{"), s.rfind("}")
        if st >= 0 and en > st:
            try:
                obj = json.loads(s[st:en + 1])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
        return {}
