# -*- coding: utf-8 -*-
"""
AutonomousLoop - L3 自主运行循环

让 Agent 自己驱动自己跑，不是等外部请求。

核心循环：
    while running:
        1. 评估内在动机状态
        2. 生成目标（注入情绪引导）
        3. 执行目标（带超时保护）
        4. 评估结果 → 更新动机 + 触发情绪
        5. 等待下一个周期

设计原则：
- 独立运行，不依赖外部触发
- 可嵌入 MetaAgent，也可独立运行
- 带完整的生命周期管理（start/stop/pause）
- 每次循环有超时保护，单次失败不终止循环
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from usmsb_sdk.l3.intrinsic_motivation import IntrinsicMotivationEngine
    from usmsb_sdk.l3.purpose_generator import PurposeGenerator
    from usmsb_sdk.l3.emotional_goal_selector import EmotionalGoalSelector
    from usmsb_sdk.l3.llm_goal_prioritizer import LLMGoalPrioritizer
    from usmsb_sdk.l4.emotional_architecture import EmotionalArchitecture


logger = logging.getLogger(__name__)


class LoopState(Enum):
    """自主循环状态"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


class LoopEvent(Enum):
    """循环事件类型"""
    MOTIVATION_EVALUATED = "motivation_evaluated"
    GOAL_GENERATED = "goal_generated"
    GOAL_STARTED = "goal_started"
    GOAL_COMPLETED = "goal_completed"
    GOAL_FAILED = "goal_failed"
    MOTIVATION_UPDATED = "motivation_updated"
    EMOTION_TRIGGERED = "emotion_triggered"
    CYCLE_COMPLETED = "cycle_completed"


@dataclass
class CycleResult:
    """单次循环结果"""
    cycle_id: str
    state_before: dict
    goals_generated: int
    goal_executed: Any | None
    goal_succeeded: bool
    emotions_triggered: list[str]
    motivation_changes: dict[str, float]
    duration_seconds: float
    error: str | None = None


@dataclass
class LoopConfig:
    """循环配置"""
    cycle_interval: float = 60.0       # 循环间隔（秒）
    goal_timeout: float = 120.0        # 单个目标超时（秒）
    max_retries: int = 3               # 失败重试次数
    motivation_decay_interval: float = 10.0  # 动机衰减检查间隔
    log_cycles: bool = True            # 是否记录循环日志
    emotion_feedback: bool = True      # 是否将结果反馈到情绪
    num_goal_candidates: int = 3       # 每轮生成的候选目标数量（用于 LLM 优先级排序）


class AutonomousLoop:
    """
    自主运行循环
    
    让 Agent 持续自主运行的核心组件。
    
    组件依赖：
    - IntrinsicMotivationEngine: 提供内在动机状态
    - PurposeGenerator: 生成目标
    - EmotionalGoalSelector: 将情绪注入目标
    - EmotionalArchitecture: 触发情绪反馈
    
    使用方式：
    ```python
    loop = AutonomousLoop(
        agent_id="my_agent",
        motivation_engine=engine,
        purpose_generator=pg,
        emotional_selector=selector,
        emotional_arch=emotions,
    )
    
    # 方式1：独立运行
    await loop.start()
    
    # 方式2：嵌入 MetaAgent，每次 MetaAgent 主循环调用 step()
    while True:
        await loop.step()
        await asyncio.sleep(loop.config.cycle_interval)
    ```
    """
    
    def __init__(
        self,
        agent_id: str,
        motivation_engine: IntrinsicMotivationEngine | None = None,
        purpose_generator: PurposeGenerator | None = None,
        emotional_selector: EmotionalGoalSelector | None = None,
        emotional_arch: EmotionalArchitecture | None = None,
        config: LoopConfig | None = None,
        executor: Callable[[Any], Any] | None = None,
        llm_goal_prioritizer: LLMGoalPrioritizer | None = None,
    ):
        self.agent_id = agent_id
        self.config = config or LoopConfig()
        
        # 组件注入
        self.motivation_engine = motivation_engine
        self.purpose_generator = purpose_generator
        self.emotional_selector = emotional_selector
        self.emotions = emotional_arch
        self.executor = executor
        self.llm_prioritizer = llm_goal_prioritizer
        
        # 状态
        self.state = LoopState.STOPPED
        self.cycles_completed = 0
        self.total_goals_completed = 0
        self.total_goals_failed = 0
        
        # 当前活跃目标
        self.active_goal: Any | None = None
        
        # 事件历史
        self.event_history: list[tuple[float, LoopEvent, Any]] = []
        
        # 统计
        self.stats = {
            "total_cycles": 0,
            "successful_goals": 0,
            "failed_goals": 0,
            "emotions_triggered": 0,
            "total_uptime_seconds": 0.0,
        }
        
        # 内部任务
        self._running_task: asyncio.Task | None = None
        self._last_cycle_time: float = 0.0
    
    # ── 生命周期 ──────────────────────────────────────────────────────────
    
    async def start(self) -> None:
        """启动自主循环（后台运行）"""
        if self.state == LoopState.RUNNING:
            logger.warning("[AutonomousLoop] Already running")
            return
        
        self.state = LoopState.RUNNING
        self._running_task = asyncio.create_task(self._run_loop())
        logger.info(f"[AutonomousLoop] {self.agent_id} started")
    
    async def stop(self) -> None:
        """停止自主循环"""
        self.state = LoopState.STOPPED
        
        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
            self._running_task = None
        
        logger.info(f"[AutonomousLoop] {self.agent_id} stopped. "
                   f"Cycles: {self.cycles_completed}, "
                   f"Goals: {self.total_goals_completed}/{self.total_goals_failed}")
    
    async def pause(self) -> None:
        """暂停循环（不终止）"""
        self.state = LoopState.PAUSED
        logger.info(f"[AutonomousLoop] {self.agent_id} paused")
    
    async def resume(self) -> None:
        """恢复循环"""
        if self.state != LoopState.PAUSED:
            return
        self.state = LoopState.RUNNING
        logger.info(f"[AutonomousLoop] {self.agent_id} resumed")
    
    async def _run_loop(self) -> None:
        """后台主循环"""
        while self.state == LoopState.RUNNING:
            try:
                result = await self._execute_cycle()
                self.cycles_completed += 1
                self.stats["total_cycles"] += 1
                
                if result and result.goal_succeeded:
                    self.total_goals_completed += 1
                    self.stats["successful_goals"] += 1
                elif result and result.error:
                    self.total_goals_failed += 1
                    self.stats["failed_goals"] += 1
                
                self._last_cycle_time = time.time()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AutonomousLoop] Cycle error: {e}", exc_info=True)
                self.state = LoopState.ERROR
                await asyncio.sleep(5)  # 错误后等待
                self.state = LoopState.RUNNING  # 尝试恢复
            
            # 等待下一个周期
            await self._wait_for_next_cycle()
    
    async def _wait_for_next_cycle(self) -> None:
        """等待下一个周期（可中断）"""
        try:
            await asyncio.sleep(self.config.cycle_interval)
        except asyncio.CancelledError:
            pass
    
    # ── 单步执行（供外部调用）───────────────────────────────────────────
    
    async def step(self) -> CycleResult | None:
        """
        执行一次循环（嵌入模式）
        
        外部系统（如 MetaAgent）调用这个方法，AutonomousLoop 不自己启动后台循环。
        
        Returns:
            CycleResult 或 None（如果暂停/停止）
        """
        if self.state not in (LoopState.RUNNING,):
            return None
        
        return await self._execute_cycle()
    
    # ── 核心循环逻辑 ────────────────────────────────────────────────────
    
    async def _execute_cycle(self) -> CycleResult | None:
        """执行一次完整的自主循环"""
        start_time = time.time()
        cycle_id = f"{self.agent_id}_{self.cycles_completed}_{int(start_time)}"
        
        # 记录动机状态
        state_before = self._capture_state()
        
        # 触发事件：动机评估
        self._record_event(LoopEvent.MOTIVATION_EVALUATED, state_before)
        
        goals_generated = 0
        goal_executed = None
        goal_succeeded = False
        emotions_triggered: list[str] = []
        motivation_changes: dict[str, float] = {}
        error_msg: str | None = None
        
        try:
            # Step 1: 评估动机状态
            needs = []
            if self.motivation_engine:
                needs = self.motivation_engine.generate_needs(state_before)
            
            # Step 2: 生成候选目标（注入情绪引导）
            candidates = await self._generate_candidates_with_emotion(state_before)
            
            # Step 2b: LLM 优先级排序（如果可用）
            if candidates and len(candidates) > 1 and self.llm_prioritizer:
                agent_state = self._build_agent_state(state_before)
                rankings = await self.llm_prioritizer.prioritize(agent_state, candidates)
                if rankings:
                    # 选择排名第一的目标
                    goal = self._goal_from_ranking(candidates, rankings[0])
                    goal.metadata = goal.metadata or {}
                    goal.metadata['llm_priority'] = rankings[0].to_dict()
                    goal.metadata['all_rankings'] = [r.to_dict() for r in rankings]
                    logger.info(f"[AutonomousLoop] LLM prioritized: {rankings[0].goal_name} "
                               f"(score={rankings[0].priority_score:.2f}, "
                               f"risk={rankings[0].risk_level}, "
                               f"reason={rankings[0].reasoning[:60]})")
            elif candidates:
                # 无 LLM：用 EmotionalGoalSelector 选择
                goal = self.emotional_selector.select_from_candidates(candidates) if self.emotional_selector else candidates[0]
            else:
                goal = None
            
            if goal:
                goals_generated = len(candidates) if candidates else 1
                goal_executed = goal
                
                # 触发事件
                self._record_event(LoopEvent.GOAL_GENERATED, goal)
                
                # Step 3: 执行目标
                self._record_event(LoopEvent.GOAL_STARTED, goal)
                result = await self._execute_goal_with_timeout(goal)
                
                # Step 4: 评估结果 → 更新动机 + 触发情绪
                goal_succeeded, emotions_triggered, motivation_changes = \
                    await self._evaluate_and_evolve(goal, result)
            
            # Step 5: 动机衰减
            if self.motivation_engine:
                delta = time.time() - self._last_cycle_time if self._last_cycle_time else self.config.cycle_interval
                self.motivation_engine.decay_motivations(delta)
            
            # 触发事件
            self._record_event(LoopEvent.GOAL_COMPLETED if goal_succeeded else LoopEvent.GOAL_FAILED, goal)
            self._record_event(LoopEvent.CYCLE_COMPLETED, None)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[AutonomousLoop] Cycle error: {e}", exc_info=True)
        
        duration = time.time() - start_time
        
        result = CycleResult(
            cycle_id=cycle_id,
            state_before=state_before,
            goals_generated=goals_generated,
            goal_executed=goal_executed,
            goal_succeeded=goal_succeeded,
            emotions_triggered=emotions_triggered,
            motivation_changes=motivation_changes,
            duration_seconds=duration,
            error=error_msg,
        )
        
        if self.config.log_cycles:
            self._log_cycle(result)
        
        return result
    
    async def _generate_candidates_with_emotion(self, state: dict) -> list[Any]:
        """
        使用情绪引导生成多个候选目标（用于 LLM 优先级排序）
        """
        emotional_ctx = None
        if self.emotional_selector:
            emotional_ctx = self.emotional_selector.get_emotional_context()
        
        num_candidates = getattr(self.config, 'num_goal_candidates', 3)
        candidates = []
        base_difficulties = [0.3, 0.5, 0.7]
        
        for i in range(min(num_candidates, 3)):
            base_diff = base_difficulties[i % 3]
            
            if self.purpose_generator and i == 0:
                purpose = self.purpose_generator.generate_purpose()
                if purpose:
                    goal = self.purpose_generator.purpose_to_goal(purpose)
                    if emotional_ctx:
                        goal = self.emotional_selector.adjust_goal_difficulty(goal, base_difficulty=base_diff)
                    candidates.append(goal)
                    continue
            
            goal = self._generate_from_pool(emotional_ctx, base_difficulty=base_diff)
            if goal:
                candidates.append(goal)
        
        return candidates
    
    def _generate_from_pool(self, emotional_ctx, base_difficulty: float = 0.5) -> Any | None:
        """从难度池生成一个目标"""
        if not self.emotional_selector:
            return None
        
        pool_result = self.emotional_selector.generate_goal_from_pool(base_difficulty=base_difficulty)
        
        class PoolGoal:
            def __init__(self, data):
                self.id = data.get("name", "")[:50]
                self.name = data["name"]
                self.description = data["description"]
                self.metadata = {
                    "difficulty": data["difficulty"],
                    "difficulty_label": data["difficulty_label"],
                    "reasoning_style": data["reasoning_style"],
                    "emotional_tendency": data["emotional_tendency"],
                    "collaborative": data["collaborative"],
                    "source": "emotional_pool",
                }
            def __repr__(self):
                return f"PoolGoal({self.name})"
        
        return PoolGoal(pool_result)
    
    def _build_agent_state(self, state: dict) -> "AgentState":
        """从内部状态构建 LLMGoalPrioritizer 的 AgentState"""
        from usmsb_sdk.l3.llm_goal_prioritizer import AgentState as LLMAgentState
        
        recent_events = self.event_history[-20:]
        goal_events = [e for _, evt, _ in recent_events if evt in (LoopEvent.GOAL_COMPLETED, LoopEvent.GOAL_FAILED)]
        if goal_events:
            completed = sum(1 for _, evt, _ in goal_events if evt == LoopEvent.GOAL_COMPLETED)
            success_rate = completed / len(goal_events)
        else:
            success_rate = 0.5
        
        dominant_mot = "curiosity"
        mot_intensity = 0.5
        if self.motivation_engine:
            dominant_mot = self.motivation_engine.get_dominant_motivation() or "curiosity"
            mot_intensity = self.motivation_engine.get_motivation_state(dominant_mot)
        
        emot_tendency = "neutral"
        diff_mult = 1.0
        collab_adj = 0.0
        ctx_val = None
        if self.emotional_selector:
            ctx_val = self.emotional_selector.get_emotional_context()
            if ctx_val:
                emot_tendency = ctx_val.tendency
                diff_mult = ctx_val.difficulty_multiplier
                collab_adj = ctx_val.collaboration_adjustment
        
        return LLMAgentState(
            agent_id=self.agent_id,
            capabilities={},
            confidence=min(1.0, 0.5 * diff_mult),
            motivation=dominant_mot,
            motivation_intensity=mot_intensity,
            resources={},
            recent_success_rate=success_rate,
            emotional_tendency=emot_tendency,
            difficulty_multiplier=diff_mult,
            collaboration_adjustment=collab_adj,
            time_allocation=ctx_val.time_allocation if ctx_val else "maintain",
            recent_goals=state.get("recent_goals", []),
        )
    
    def _goal_from_ranking(self, candidates: list[Any], ranking: "PriorityResult") -> Any | None:
        """从优先级结果中找到对应的候选目标"""
        for c in candidates:
            c_name = getattr(c, 'name', '') or getattr(c, 'id', '')
            if c_name == ranking.goal_name or ranking.goal_name in c_name:
                return c
        return candidates[0] if candidates else None
    
    async def _execute_goal_with_timeout(self, goal: Any) -> Any | None:
        """带超时的目标执行"""
        if self.executor:
            try:
                return await asyncio.wait_for(
                    self.executor(goal),
                    timeout=self.config.goal_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"[AutonomousLoop] Goal timed out after {self.config.goal_timeout}s")
                return {"error": "timeout", "goal": goal}
            except Exception as e:
                logger.error(f"[AutonomousLoop] Goal execution error: {e}")
                return {"error": str(e), "goal": goal}
        
        # 默认执行：直接返回成功（无 executor）
        await asyncio.sleep(0.1)
        return {"success": True, "goal": goal}
    
    async def _evaluate_and_evolve(
        self,
        goal: Any,
        result: Any | None,
    ) -> tuple[bool, list[str], dict[str, float]]:
        """
        评估目标结果，触发情绪，更新动机
        
        Returns:
            (goal_succeeded, emotions_triggered, motivation_changes)
        """
        emotions_triggered: list[str] = []
        motivation_changes: dict[str, float] = {}
        goal_succeeded = False
        
        # 判断成功/失败
        if isinstance(result, dict):
            goal_succeeded = result.get("success", False) and not result.get("error")
        elif result is None:
            goal_succeeded = False
        else:
            goal_succeeded = True
        
        # 触发情绪
        if self.emotions and self.config.emotion_feedback:
            event = {
                "type": "success" if goal_succeeded else "failure",
                "valence": 0.9 if goal_succeeded else 0.2,
                "intensity": 0.8 if goal_succeeded else 0.7,
                "description": f"目标{'成功' if goal_succeeded else '失败'}: {getattr(goal, 'name', 'unknown')}",
                "source": "internal",
            }
            
            # 额外情绪：成功时触发自豪/满足，失败时触发悲伤/愤怒
            if goal_succeeded:
                event["type"] = "achievement"
                event["valence"] = 0.85
            
            triggered = self.emotions.react_to_event(event)
            emotions_triggered = [e.type.value for e in triggered]
            
            # 从情绪中提取主导的动机变化
            if triggered:
                dominant = self.emotions.mood.get_dominant_emotion()
                if dominant:
                    motivation_changes[f"dominant_emotion"] = dominant.value
        
        # 更新动机引擎
        if self.motivation_engine:
            if goal_succeeded:
                # 满足需求 → 降低对应动机
                for need in getattr(self.purpose_generator, 'last_needs', []):
                    before = self.motivation_engine.get_motivation_state(
                        need.metadata.get("motivation", "curiosity") if hasattr(need, 'metadata') else "curiosity"
                    )
                    self.motivation_engine.satisfy_need(need, satisfaction=0.7)
                    after = self.motivation_engine.get_motivation_state(
                        need.metadata.get("motivation", "curiosity") if hasattr(need, 'metadata') else "curiosity"
                    )
                    motivation_changes[f"motivation_{need.metadata.get('motivation', 'unknown')}"] = after - before
            else:
                # 失败 → 增强 survival 动机（保守倾向）
                before_survival = self.motivation_engine.get_motivation_state("survival")
                self.motivation_engine.boost_motivation("survival", boost=0.1)
                after_survival = self.motivation_engine.get_motivation_state("survival")
                motivation_changes["motivation_survival"] = after_survival - before_survival
        
        return goal_succeeded, emotions_triggered, motivation_changes
    
    # ── 工具方法 ────────────────────────────────────────────────────────
    
    def _capture_state(self) -> dict:
        """捕获当前状态"""
        state = {
            "timestamp": time.time(),
            "loop_state": self.state.value,
            "cycles_completed": self.cycles_completed,
        }
        
        if self.motivation_engine:
            state["motivations"] = {
                k: self.motivation_engine.get_motivation_state(k)
                for k in ["curiosity", "growth", "social", "creation", "survival"]
            }
            state["dominant_motivation"] = self.motivation_engine.get_dominant_motivation()
        
        if self.emotions:
            ctx = self.emotional_selector.get_emotional_context() if self.emotional_selector else None
            if ctx:
                state["emotional_tendency"] = ctx.tendency
                state["difficulty_multiplier"] = ctx.difficulty_multiplier
        
        return state
    
    def _record_event(self, event: LoopEvent, data: Any) -> None:
        """记录事件"""
        self.event_history.append((time.time(), event, data))
        # 限制历史长度
        if len(self.event_history) > 1000:
            self.event_history = self.event_history[-500:]
    
    def _log_cycle(self, result: CycleResult) -> None:
        """记录循环结果"""
        status = "✅" if result.goal_succeeded else "❌" if result.error else "⚠️"
        goal_name = getattr(result.goal_executed, 'name', 'none') if result.goal_executed else 'none'
        emotions = ", ".join(result.emotions_triggered) if result.emotions_triggered else "无"
        motivations = result.motivation_changes
        
        logger.info(
            f"[AutonomousLoop] {status} Cycle #{result.cycle_id.split('_')[-2]} "
            f"goal={goal_name[:40]} "
            f"emotions=[{emotions}] "
            f"difficulty={result.duration_seconds:.1f}s"
        )
    
    # ── 状态查询 ───────────────────────────────────────────────────────
    
    def get_status(self) -> dict:
        """获取循环状态"""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "cycles_completed": self.cycles_completed,
            "goals_completed": self.total_goals_completed,
            "goals_failed": self.total_goals_failed,
            "active_goal": getattr(self.active_goal, 'name', None) if self.active_goal else None,
            "last_cycle": self._last_cycle_time,
            "uptime_seconds": time.time() - self._last_cycle_time if self._last_cycle_time else 0,
            "config": {
                "cycle_interval": self.config.cycle_interval,
                "goal_timeout": self.config.goal_timeout,
            },
            "stats": self.stats,
        }
    
    def get_recent_events(self, limit: int = 20) -> list[dict]:
        """获取最近事件"""
        recent = self.event_history[-limit:]
        return [
            {"timestamp": t, "event": e.value, "data": str(d)[:100]}
            for t, e, d in reversed(recent)
        ]
