"""TeamLeaderPea —— 团队版 v3.0（多 PEA over A2A，替代 team_leader.py 旧 dict-CRUD stub）。

旧 TeamLeader 是内存 dict 增删改查、print()、无智能、无经济。新实现把"团队"表达为
**一个协调者 PEA 用 VIBE 买一组独立 PEA 的服务**——市场关系，不是雇佣关系：

    LLM 拆解目标 → 能力发现组队（语义×声誉）→ 联合订单（一次托管）
    → 各成员经 A2A 交付 → LLM 评贡献 → Shapley 公平分账。

无中心化老板：成员各有钱包、各自独立、按贡献分钱。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from usmsb_sdk.economic.joint_order import LLMContributionAssessor
from usmsb_sdk.economic.pea_market import PeaMarket
from usmsb_sdk.harness.base_harness import ChatProvider

logger = logging.getLogger(__name__)


class LLMTaskDecomposer:
    """用 LLM 把目标拆成可独立交付的子任务。fallback（无 LLM）：整体作为单一任务。"""

    _SYS = (
        "你是项目拆解器。把【目标】拆成 2~N 个可由不同专业方独立交付的子任务"
        "（每个子任务一句话，说明要交付什么）。严格返回 JSON："
        '{"subtasks":["子任务1","子任务2", ...]}。'
    )

    def __init__(self, chat: ChatProvider | None):
        self.chat = chat

    async def decompose(self, goal: str, max_subtasks: int = 5) -> list[str]:
        if self.chat is None or not goal.strip():
            return [goal] if goal.strip() else []
        try:
            raw = await self.chat.complete([
                {"role": "system", "content": self._SYS},
                {"role": "user", "content": f"目标：{goal}"},
            ])
            subs = self._parse(raw)
            return subs[:max_subtasks] if subs else [goal]
        except Exception as e:  # noqa: BLE001
            logger.warning("[decomposer] LLM 拆解失败：%s，整体作为单任务", e)
            return [goal]

    @staticmethod
    def _parse(raw: str) -> list[str]:
        s = (raw or "").strip()
        st, en = s.find("{"), s.rfind("}")
        if st >= 0 and en > st:
            try:
                obj = json.loads(s[st:en + 1])
                subs = obj.get("subtasks")
                if isinstance(subs, list):
                    return [str(x).strip() for x in subs if str(x).strip()]
            except json.JSONDecodeError:
                pass
        return []


class TeamLeaderPea:
    """团队协调者 PEA：拆解 → 组队 → 联合订单分账。"""

    def __init__(
        self,
        leader_id: str,
        market: PeaMarket,
        decomposer: LLMTaskDecomposer,
        *,
        contribution_assessor: LLMContributionAssessor | None = None,
    ):
        self.leader_id = leader_id
        self.market = market
        self.decomposer = decomposer
        self.contribution_assessor = contribution_assessor

    async def _pick_member(self, subtask: str) -> str | None:
        """为子任务选成员：优先全网目录发现，否则本地名录（能力发现/撮合器）。"""
        market = self.market
        if market.discovery is not None and market.directory is not None:
            ranked = await market.discovery.discover(subtask, market.directory, top_k=10)
            for r in ranked:
                if r.agent_id != self.leader_id and r.agent_id in market.suppliers:
                    return r.agent_id
        cands = [s for s in market.suppliers.values() if s.agent_id != self.leader_id]
        if not cands:
            return None
        if market.discovery is not None:
            return await market.discovery.best(subtask, cands)
        return await market.matcher.pick(subtask, cands)

    async def run_project(
        self, goal: str, total_reward: float, *, max_subtasks: int = 5,
    ) -> dict[str, Any]:
        """跑一个团队项目：返回拆解、组队、分账结果。"""
        subtasks = await self.decomposer.decompose(goal, max_subtasks)
        assignments: dict[str, str] = {}
        unmatched: list[str] = []
        for st in subtasks:
            member = await self._pick_member(st)
            if member is None:
                unmatched.append(st)
                continue
            # 同一成员被分到多个子任务 → 合并
            assignments[member] = f"{assignments[member]}；{st}" if member in assignments else st

        if not assignments:
            return {"status": "no_team", "subtasks": subtasks, "unmatched": unmatched}

        result = await self.market.joint_order(
            from_id=self.leader_id, task=goal, assignments=assignments,
            total_reward=total_reward, contribution_assessor=self.contribution_assessor,
        )
        result.update({"subtasks": subtasks, "assignments": assignments, "unmatched": unmatched})
        return result
