"""ButlerPea —— 超级个体大管家（v3.0 重写，替代已退役的 ButlerAgent 旧 stub）。

旧 `butler.ButlerAgent` 的问题：导入链断裂（l3_orchestrator → 已不存在的 GoogleAgentCard）、
全是 print()、team 侧是 dict CRUD、无真实 LLM、与 v3.0「harness 为主循环」方向冲突。

新实现把"超级个体大管家"表达为**角色轴 R4 的 PEA**：
- 继承 PeaHarness → 自带「一切皆 LLM」循环 + guard（限额/红线/未知工具→人工闸门）+ 钱包。
- 晨/晚汇报从 stub 类降级为 **prompt skill**：generate_briefing 工具用 LLM 即时生成。
- 给专家/其他 PEA 派活（delegate_to_specialist）是花钱的副作用 → 自动过 guard 限额。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from usmsb_sdk.economic.pea import PeaHarness, PersonalEconomicAgent
from usmsb_sdk.harness.base_harness import ChatProvider

_MORNING_SYS = "你是用户的私人大管家。基于用户画像与待办，生成简洁、可执行的今日晨间简报（要点式，<150字）。"
_EVENING_SYS = "你是用户的私人大管家。基于今日完成情况，生成晚间复盘（成果/未完成/明日建议，要点式，<150字）。"


@dataclass
class ButlerProfile:
    user_name: str
    bio: str = ""
    goals: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)


class ButlerPea(PeaHarness):
    """超级个体大管家 PEA（角色轴 R4，成熟度 M1）。"""

    _READ = {"read_user_profile", "list_tasks", "generate_briefing"}
    _SIDE_EFFECT = {"add_task", "delegate_to_specialist"}

    def __init__(
        self,
        pea: PersonalEconomicAgent,
        chat: ChatProvider,
        profile: ButlerProfile,
        tasks: list[dict[str, Any]] | None = None,
    ):
        super().__init__(pea)
        self._chat = chat
        self.profile = profile
        self.tasks: list[dict[str, Any]] = list(tasks or [])

    @property
    def system_prompt(self) -> str:
        return (
            f"你是 {self.profile.user_name} 的私人大管家（超级个体 AI）。"
            "在主人设定的钱包与规则边界内自主打理事务。\n"
            "用 JSON 动作协议逐步行动：\n"
            '  {"action":"tool","name":"<工具>","args":{...}}\n'
            '  {"action":"say","text":"<给主人的话>"}\n'
            '  {"action":"request_human","reason":"<需主人确认的事>"}\n'
            "可用工具：read_user_profile(读画像) / list_tasks(读待办) / "
            "add_task(加待办) / generate_briefing(args.kind=morning|evening 生成简报) / "
            "delegate_to_specialist(args.task, args.vibe_cost 给专家/PEA 派活，花 VIBE)。\n"
            "花钱或越界的动作会被安全闸门拦截并转人工确认。完成后用 say 汇报。"
        )

    @property
    def chat(self) -> ChatProvider:
        return self._chat

    def known_tool(self, name: str) -> bool:
        return name in self._READ or name in self._SIDE_EFFECT

    def tool_is_side_effect(self, name: str) -> bool:
        return name in self._SIDE_EFFECT

    async def dispatch(self, conv: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "read_user_profile":
            return {
                "user": self.profile.user_name,
                "bio": self.profile.bio,
                "goals": self.profile.goals,
                "values": self.profile.values,
            }
        if name == "list_tasks":
            return {"tasks": self.tasks}
        if name == "add_task":
            task = {"title": args.get("title", ""), "status": "pending"}
            self.tasks.append(task)
            return {"added": task, "total": len(self.tasks)}
        if name == "generate_briefing":
            return await self._generate_briefing(str(args.get("kind", "morning")))
        if name == "delegate_to_specialist":
            cost = self.estimate_cost(name, args)  # guard 已在外层校验过限额
            return {"delegated": args.get("task"), "cost": cost}
        return {"ok": True}

    async def _generate_briefing(self, kind: str) -> dict[str, Any]:
        """晨/晚汇报：prompt skill —— 用 LLM 即时生成（不再是 stub 类）。"""
        sys = _EVENING_SYS if kind == "evening" else _MORNING_SYS
        ctx = (
            f"用户：{self.profile.user_name}\n目标：{', '.join(self.profile.goals) or '（未设置）'}\n"
            f"待办：{[t.get('title') for t in self.tasks] or '（无）'}"
        )
        text = await self.chat.complete(
            [{"role": "system", "content": sys}, {"role": "user", "content": ctx}]
        )
        return {"kind": kind, "briefing": text}
