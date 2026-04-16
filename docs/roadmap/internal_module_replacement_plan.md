# MetaAgent 内部模块替换计划

**状态**: 待确认
**日期**: 2026-04-17

---

## 一、目标

将 MetaAgent 内部实现逐步替换为 SDK（L1-L5），
同时保持双轨策略模式（内部 vs SDK 并行，LLM 智能选择）。

---

## 二、现状差距分析

### 2.1 goals/engine.py（GoalEngine）

**当前实现**：
- 纯列表管理（`self.goals = []`）
- 硬编码永久目标（platform_health, user_satisfaction...）
- 无 LLM，无目标生成能力

**SDK 对应**：
- `l3/purpose_generator.py`（PurposeGenerator）：LLM 驱动的目标生成
- `l3/intrinsic_motivation.py`（IntrinsicMotivationEngine）：内在动机驱动

**接口差距**：
```
IL3 接口要求：
  generate_goal(context: dict) -> Goal
  evaluate_outcome(goal, result) -> float
  detect_intrinsic_motivation(state) -> MotivationSignal

SDK PurposeGenerator 实际：
  generate_purpose() -> Purpose        # 签名不匹配
  purpose_to_goal(purpose) -> Goal    # 手动转换

SDK IntrinsicMotivationEngine 实际：
  generate_needs(agent_state) -> list[IntrinsicNeed]  # 已有
  satisfy_need(need, satisfaction)  # 已有
  decay_motivations(delta_time)     # 已有
```

**差距结论**：
- ❌ PurposeGenerator 签名不匹配（需适配器）
- ❌ 缺少 `evaluate_outcome()`
- ❌ 缺少 `detect_intrinsic_motivation()`
- ⚠️  GoalEngine 需要重写为 LLM 驱动

---

### 2.2 evolution_v2/engine.py（SelfEvolutionEngine）

**当前实现**：
- 已集成 SDK 的 `goal_generator`、`capability_assessor`、`curiosity_engine` 等
- 自包含完整，不需要替换

**SDK 对应**：
- `l3/purpose_generator.py`
- `l3/intrinsic_motivation.py`
- `l4/` 全部

**评估**：✅ 已有较好集成，无需大改

---

### 2.3 L4 接口差距（IL4 vs SDK）

```
IL4 接口要求：
  build_self_model(experience) -> SelfModel
  metacognize(thought) -> MetacognitionResult
  infer_mind(other_agent, history) -> TheoryOfMindResult
  feel(stimulus) -> EmotionResponse

SDK L4Agent 实际：
  build_self_model(experience) -> SelfModel  ✅
  metacognize(thought) -> dict             ⚠️ 返回类型不匹配
  infer_mind(other_agent, history) -> dict  ⚠️ 返回类型不匹配
  feel(stimulus) -> dict                   ⚠️ 返回类型不匹配
```

**差距结论**：
- 需要补齐 L4Agent 的接口，返回类型用 dataclass 包装

---

## 三、替换路线图

### Phase 1: 修复 IL3 接口适配器（优先级 P0）

**目标**：让 PurposeGenerator 符合 IL3 接口

**新增文件**：
```
meta_agent/adapters/
├── __init__.py
├── l3_adapter.py     # PurposeGenerator → IL3 适配器
```

**l3_adapter.py 内容**：

```python
"""
L3 IL3Component Adapter - 让 PurposeGenerator 符合 IL3 接口
"""

from typing import Any

from ...l3.purpose_generator import PurposeGenerator as SDKPurposeGenerator
from ...l3.intrinsic_motivation import IntrinsicMotivationEngine as SDKIntrinsicMotivation


class IL3Adapter:
    """
    IL3 接口适配器。

    将 SDK 的 PurposeGenerator + IntrinsicMotivationEngine
    适配为 IL3Component 接口。

    同时保留内部实现作为 internal 策略。
    """

    def __init__(
        self,
        agent_id: str,
        llm_client=None,
        internal_goals_engine=None,  # 当前 goals/engine.py
    ):
        self.agent_id = agent_id

        # SDK 实现
        self._sdk_purpose = SDKPurposeGenerator(
            agent_id=agent_id,
            llm_client=llm_client,
        )
        self._sdk_motivation = SDKIntrinsicMotivation()

        # 内部实现（internal 策略）
        self._internal_engine = internal_goals_engine

    # ── IL3Component 接口 ──────────────────────────────────

    async def generate_goal(self, context: dict) -> Goal:
        """
        生成目标。

        策略：使用 PurposeGenerator（SDK），
        内部 engine 作为 fallback。
        """
        purpose = self._sdk_purpose.generate_purpose()
        goal = self._sdk_purpose.purpose_to_goal(purpose)
        return goal

    async def evaluate_outcome(self, goal: Goal, result: Any) -> float:
        """
        评估目标执行结果。

        简化实现：基于 result 类型打分。
        """
        if result is None:
            return 0.0
        if isinstance(result, dict) and "error" in result:
            return 0.1
        if isinstance(result, dict) and result.get("success"):
            return 0.9
        if isinstance(result, str) and len(result) > 10:
            return 0.7
        return 0.5

    async def detect_intrinsic_motivation(self, state: dict) -> MotivationSignal:
        """
        检测内在动机。

        使用 SDK 的 IntrinsicMotivationEngine。
        """
        needs = self._sdk_motivation.generate_needs(state)
        dominant = self._sdk_motivation.get_dominant_motivation()
        return MotivationSignal(
            needs=needs,
            dominant=dominant,
            intensity=self._sdk_motivation.get_motivation_state(dominant or "curiosity"),
        )

    # ── 内部引擎接口（internal 策略用） ──────────────────────

    async def add_goal(self, goal: dict):
        if self._internal_engine:
            await self._internal_engine.add_goal(goal)

    async def update_goal(self, goal_id: str, status: str):
        if self._internal_engine:
            await self._internal_engine.update_goal(goal_id, status)

    async def get_active_goals(self) -> list[dict]:
        if self._internal_engine:
            return self._internal_engine.goals + self._internal_engine.eternal_goals
        return []
```

---

### Phase 2: 重写 GoalEngine（优先级 P1）

**目标**：让 GoalEngine 委托给 IL3Adapter

```python
# goals/engine.py 重写

class GoalEngine:
    """
    目标引擎 - LLM 驱动版

    策略模式：
    - internal: 使用内建的启发式逻辑
    - sdk: 使用 IL3Adapter（→ PurposeGenerator）
    """

    def __init__(self, llm_client=None, agent_id="meta_agent"):
        self.agent_id = agent_id
        self.llm = llm_client

        # internal 策略：内建目标
        self.goals = []
        self.eternal_goals = [
            {"id": "platform_health", "name": "平台健康运营", "status": "in_progress"},
            {"id": "user_satisfaction", "name": "用户满意度", "status": "in_progress"},
            {"id": "system_optimization", "name": "系统优化", "status": "in_progress"},
            {"id": "learning_evolution", "name": "自主学习进化", "status": "in_progress"},
        ]

        # sdk 策略：IL3Adapter
        from ..adapters.l3_adapter import IL3Adapter
        self._sdk_adapter = IL3Adapter(
            agent_id=agent_id,
            llm_client=llm_client,
            internal_goals_engine=self,
        )

        # 当前策略
        self._use_sdk = True

    async def start(self):
        logger.info("Goal Engine (LLM) started")

    async def stop(self):
        logger.info("Goal Engine stopped")

    async def check_goals(self):
        """检查目标状态 - SDK 策略"""
        if self._use_sdk:
            # 使用 SDK 检测内在动机
            state = self._get_current_state()
            signal = await self._sdk_adapter.detect_intrinsic_motivation(state)
            if signal.intensity > 0.6:
                # 动机强烈，生成新目标
                goal = await self._sdk_adapter.generate_goal(state)
                await self.add_goal(goal)
        # internal 策略不做任何事（被动列表）

    async def add_goal(self, goal):
        self.goals.append(goal)

    async def update_goal(self, goal_id: str, status: str):
        for goal in self.goals + self.eternal_goals:
            if goal.get("id") == goal_id:
                goal["status"] = status
```

---

### Phase 3: 补齐 L4 接口（优先级 P2）

**目标**：让 L4Agent 的方法返回类型符合 IL4

```python
# l4/l4_agent.py 补齐

@dataclass
class MetacognitionResult:
    thought: str
    analysis: str
    confidence: float

@dataclass
class TheoryOfMindResult:
    other_agent_id: str
    inferred_intent: str
    confidence: float

@dataclass
class EmotionResponse:
    emotion: str          # joy/sadness/anger/fear/surprise
    intensity: float       # 0-1
    action_tendency: str   # 行动倾向

class L4Agent:
    async def metacognize(self, thought: str) -> MetacognitionResult:
        # ... 现有逻辑 ...
        return MetacognitionResult(
            thought=thought,
            analysis=analysis_text,
            confidence=0.7,
        )

    async def infer_mind(self, other_agent_id: str, history: list) -> TheoryOfMindResult:
        # ... 现有逻辑 ...
        return TheoryOfMindResult(
            other_agent_id=other_agent_id,
            inferred_intent=intent_text,
            confidence=0.6,
        )

    async def feel(self, stimulus: dict) -> EmotionResponse:
        # ... 现有逻辑 ...
        return EmotionResponse(
            emotion=detected_emotion,
            intensity=intensity_value,
            action_tendency=tendency_text,
        )
```

---

## 四、执行顺序

```
Phase 1（P0）
  → 新建 meta_agent/adapters/l3_adapter.py
  → 实现 IL3Adapter（PurposeGenerator → IL3）

Phase 2（P1）
  → 重写 meta_agent/goals/engine.py（委托给 IL3Adapter）
  → StrategyRouter 自然支持 internal/sdk 切换

Phase 3（P2）
  → 补齐 l4/l4_agent.py 接口返回类型
  → 确保 IL4 接口完全合规

Phase 4（P3）
  → 将 SkillLoader 的 L3Loader 对接 IL3Adapter
  → 将 SkillRouter 接入 StrategyRouter 经验库
```

---

## 五、风险与注意事项

1. **PurposeGenerator 需要 agent_id**：MetaAgent 需要把自己的 agent_id 传进去
2. **LLM Client 共享**：IL3Adapter 和 PurposeGenerator 共用同一个 LLMClient
3. **向后兼容**：GoalEngine 的 `add_goal/update_goal` 接口保持不变，确保现有调用方不崩溃
4. **策略渐进切换**：先让 GoalEngine 内部默认用 SDK，internal 作为 fallback，逐步减少 internal 使用

---

*创建时间: 2026-04-17*
