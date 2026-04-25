"""
StrategyRouter - LLM 驱动的策略路由器

双轨并行：内部实现 vs SDK 实现，由 LLM 智能选择
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from .llm.manager import LLMManager

logger = logging.getLogger(__name__)


SCENARIO_CLASSIFICATION_PROMPT = """
你是一个智能任务分类器。请分析以下任务输入，判断其**场景类型**和**复杂度**。

## 场景类型（选一个）
- INFO: 信息类任务（检索、查询、简单执行）
- PLAN: 规划类任务（目标生成、项目规划、多步分解）
- COG: 认知类任务（自我反思、情绪处理、心智推断）
- COLLAB: 协作类任务（多Agent协调、集体决策）

## 复杂度（选一个）
- SIMPLE: 单一目标，步骤≤3，无需深度推理
- COMPLEX: 多目标或步骤>3，或需要深度推理

## 输出格式（严格JSON）
{
  "scenario": "INFO|PLAN|COG|COLLAB",
  "complexity": "SIMPLE|COMPLEX",
  "confidence": 0.0-1.0,
  "reasoning": "简短推理过程（20字内）",
  "suggested_layer": "L2|L3|L4|L5",
  "strategy_preference": "internal|sdk|both"
}

## 任务输入
{task_text}
"""

STRATEGY_EVALUATION_PROMPT = """
你是一个策略评估专家。请对比以下两个策略的执行结果，选择更优的一个。

## 任务目标
{task_description}

## 策略A：{strategy_a_name}
结果：{result_a}
执行时间：{time_a}s | Token消耗：{token_a}

## 策略B：{strategy_b_name}
结果：{result_b}
执行时间：{time_b}s | Token消耗：{token_b}

## 评估维度（权重）
- 响应质量（40%）：结果是否准确、完整、有价值
- 推理深度（30%）：思维链是否清晰、有逻辑
- 执行效率（20%）：时间+Token消耗是否合理
- 用户价值（10%）：是否真正解决用户问题

## 输出格式（严格JSON）
{{
  "winner": "A|B|TIE",
  "quality_a": 0.0-1.0,
  "quality_b": 0.0-1.0,
  "reasoning": "对比分析（50字内）",
  "improvement_a": "策略A的改进建议（如有）",
  "improvement_b": "策略B的改进建议（如有）"
}}
"""


@dataclass
class ScenarioTag:
    scenario: str      # INFO/PLAN/COG/COLLAB
    complexity: str    # SIMPLE/COMPLEX
    confidence: float
    reasoning: str
    suggested_layer: str
    strategy_preference: str  # internal/sdk/both


@dataclass
class StrategyResult:
    strategy_name: str
    result: Any
    quality_score: float
    execution_time: float
    token_cost: int
    error: str | None = None


@dataclass
class StrategyExperience:
    id: str
    scenario: str
    complexity: str
    task_hash: str
    task_text: str
    strategy: str
    layer: str
    quality_score: float
    response_quality: float
    reasoning_depth: float
    execution_time: float
    token_cost: int
    result_summary: str
    selected: bool
    improvement_notes: str
    timestamp: datetime
    embedding: list[float] | None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


class StrategyRouter:
    """
    LLM 驱动的策略路由器。

    核心流程：
    1. LLM 场景分类
    2. LLM 选择策略（参考历史经验）
    3. 双轨并行执行（内部 vs SDK）
    4. LLM 评估结果，选择最优
    5. 记录经验，供下次参考
    """

    def __init__(
        self,
        llm_manager: LLMManager,
        experience_db_path: str = "data/strategy_experience.db",
    ):
        self.llm = llm_manager
        self.experience_db_path = experience_db_path
        self._experience_cache: dict[str, list[StrategyExperience]] = {}
        self._init_db()

    def _init_db(self):
        """初始化经验库（SQLite）"""
        import sqlite3
        import os
        os.makedirs(os.path.dirname(self.experience_db_path), exist_ok=True)
        conn = sqlite3.connect(self.experience_db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strategy_experience (
                id TEXT PRIMARY KEY,
                scenario TEXT NOT NULL,
                complexity TEXT NOT NULL,
                task_hash TEXT NOT NULL,
                task_text TEXT NOT NULL,
                strategy TEXT NOT NULL,
                layer TEXT NOT NULL,
                quality_score REAL NOT NULL,
                response_quality REAL NOT NULL,
                reasoning_depth REAL NOT NULL,
                execution_time REAL NOT NULL,
                token_cost INTEGER NOT NULL,
                result_summary TEXT NOT NULL,
                selected INTEGER NOT NULL,
                improvement_notes TEXT,
                timestamp TEXT NOT NULL,
                embedding BLOB
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_scenario_layer
            ON strategy_experience(scenario, layer)
        """)
        conn.commit()
        conn.close()

    async def route(self, task_text: str, layer: str, internal_fn, sdk_fn) -> StrategyResult:
        """
        路由主流程。

        Args:
            task_text: 任务文本
            layer: 调用层（L2/L3/L4/L5）
            internal_fn: 内部实现 async 函数 (task_text) -> Any
            sdk_fn: SDK 实现 async 函数 (task_text) -> Any

        Returns:
            StrategyResult: 最优策略的执行结果
        """
        logger.info(f"[StrategyRouter] Routing task to {layer} layer")

        # Step 1: LLM 场景分类
        scenario_tag = await self._classify_scenario(task_text)
        logger.info(f"[StrategyRouter] Scenario: {scenario_tag.scenario}, "
                    f"Complexity: {scenario_tag.complexity}, "
                    f"Preference: {scenario_tag.strategy_preference}")

        # Step 2: 查历史经验，获取该场景+layer的策略质量记录
        history = await self._get_relevant_experience(
            scenario_tag.scenario, layer
        )

        # Step 3: 确定要执行哪些策略
        if scenario_tag.strategy_preference == "internal":
            strategies = ["internal"]
        elif scenario_tag.strategy_preference == "sdk":
            strategies = ["sdk"]
        elif scenario_tag.strategy_preference == "both":
            # 查历史，看哪个策略在该场景+layer上质量更高
            if history:
                internal_avg = self._avg_quality(history, "internal")
                sdk_avg = self._avg_quality(history, "sdk")
                if internal_avg > sdk_avg + 0.1:
                    strategies = ["internal"]
                elif sdk_avg > internal_avg + 0.1:
                    strategies = ["sdk"]
                else:
                    strategies = ["internal", "sdk"]  # 并行
            else:
                strategies = ["internal", "sdk"]  # 无历史，并行
        else:
            strategies = ["internal", "sdk"]

        # Step 4: 真·并行执行（asyncio.gather）
        results: dict[str, StrategyResult] = {}
        if len(strategies) == 2:
            # 真正并行：同时执行 internal 和 sdk
            internal_task = asyncio.create_task(
                self._execute_with_timing("internal", internal_fn, task_text)
            )
            sdk_task = asyncio.create_task(
                self._execute_with_timing("sdk", sdk_fn, task_text)
            )
            internal_res, sdk_res = await asyncio.gather(internal_task, sdk_task)
            results["internal"] = internal_res
            results["sdk"] = sdk_res
        elif strategies == ["internal"]:
            results["internal"] = await self._execute_with_timing("internal", internal_fn, task_text)
        elif strategies == ["sdk"]:
            results["sdk"] = await self._execute_with_timing("sdk", sdk_fn, task_text)

        if len(results) == 1:
            best = list(results.values())[0]
        else:
            # Step 5: LLM 评估，选最优
            best = await self._llm_evaluate_and_select(
                task_text, results, scenario_tag
            )

        # Step 6: 记录经验
        await self._record_experience(
            task_text, layer, scenario_tag, results, best
        )

        return best

    async def _classify_scenario(self, task_text: str) -> ScenarioTag:
        """LLM 场景分类"""
        prompt = SCENARIO_CLASSIFICATION_PROMPT.replace("{task_text}", task_text)
        response = await self.llm.generate(prompt)
        
        try:
            # 尝试解析 JSON
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            return ScenarioTag(
                scenario=data["scenario"],
                complexity=data["complexity"],
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                suggested_layer=data.get("suggested_layer", "L2"),
                strategy_preference=data.get("strategy_preference", "both"),
            )
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"[StrategyRouter] Failed to parse scenario, defaulting")
            return ScenarioTag(
                scenario="INFO",
                complexity="SIMPLE",
                confidence=0.3,
                reasoning="解析失败，默认",
                suggested_layer="L2",
                strategy_preference="both",
            )

    async def _execute_with_timing(
        self, strategy_name: str, fn, task_text: str
    ) -> StrategyResult:
        """包装执行，统计时间和Token"""
        start = time.time()
        token_count = 0
        try:
            result = await fn(task_text)
            elapsed = time.time() - start
            # 估算token（调用方可在result中附上）
            token_cost = getattr(result, '_token_cost', 0) if hasattr(result, '_token_cost') else 0
            return StrategyResult(
                strategy_name=strategy_name,
                result=result,
                quality_score=0.0,  # 待评估
                execution_time=elapsed,
                token_cost=token_cost,
            )
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[StrategyRouter] {strategy_name} failed: {e}")
            return StrategyResult(
                strategy_name=strategy_name,
                result=None,
                quality_score=0.0,
                execution_time=elapsed,
                token_cost=0,
                error=str(e),
            )

    async def _llm_evaluate_and_select(
        self, task_text: str, results: dict[str, StrategyResult], scenario_tag: ScenarioTag
    ) -> StrategyResult:
        """LLM 对比评估，选择最优"""
        if len(results) < 2:
            return list(results.values())[0]

        r_a = results.get("internal")
        r_b = results.get("sdk")
        if not r_a or not r_b:
            return r_a or r_b

        prompt = (
            STRATEGY_EVALUATION_PROMPT
            .replace("{task_description}", task_text)
            .replace("{strategy_a_name}", "内部实现")
            .replace("{result_a}", str(r_a.result)[:500] if r_a.result else f"错误: {r_a.error}")
            .replace("{time_a}", str(round(r_a.execution_time, 2)))
            .replace("{token_a}", str(r_a.token_cost))
            .replace("{strategy_b_name}", "SDK实现")
            .replace("{result_b}", str(r_b.result)[:500] if r_b.result else f"错误: {r_b.error}")
            .replace("{time_b}", str(round(r_b.execution_time, 2)))
            .replace("{token_b}", str(r_b.token_cost))
        )

        response = await self.llm.generate(prompt)

        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text.strip())
            winner = data["winner"]
            if winner == "A":
                r_a.quality_score = float(data["quality_a"])
                return r_a
            elif winner == "B":
                r_b.quality_score = float(data["quality_b"])
                return r_b
            else:
                # TIE，返回执行时间短的
                return r_a if r_a.execution_time < r_b.execution_time else r_b
        except (json.JSONDecodeError, KeyError):
            logger.warning("[StrategyRouter] Failed to parse evaluation, defaulting to faster")
            return r_a if r_a.execution_time < r_b.execution_time else r_b

    async def _get_relevant_experience(
        self, scenario: str, layer: str, limit: int = 10
    ) -> list[StrategyExperience]:
        """查询历史经验"""
        import sqlite3
        conn = sqlite3.connect(self.experience_db_path)
        rows = conn.execute("""
            SELECT * FROM strategy_experience
            WHERE scenario = ? AND layer = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (scenario, layer, limit)).fetchall()
        conn.close()

        if not rows:
            return []

        cols = ["id", "scenario", "complexity", "task_hash", "task_text",
                "strategy", "layer", "quality_score", "response_quality",
                "reasoning_depth", "execution_time", "token_cost",
                "result_summary", "selected", "improvement_notes",
                "timestamp", "embedding"]
        
        experiences = []
        for row in rows:
            d = dict(zip(cols, row))
            d['selected'] = bool(d['selected'])
            d['timestamp'] = datetime.fromisoformat(d['timestamp'])
            experiences.append(StrategyExperience(**d))
        return experiences

    def _avg_quality(self, history: list[StrategyExperience], strategy: str) -> float:
        records = [e for e in history if e.strategy == strategy]
        if not records:
            return 0.5  # 无历史，默认中立
        return sum(e.quality_score for e in records) / len(records)

    async def _record_experience(
        self,
        task_text: str,
        layer: str,
        scenario_tag: ScenarioTag,
        results: dict[str, StrategyResult],
        selected: StrategyResult,
    ):
        """记录策略执行经验到数据库"""
        import sqlite3
        import uuid

        task_hash = hashlib.md5(task_text.encode()).hexdigest()[:16]
        timestamp = datetime.now()

        for name, result in results.items():
            summary = str(result.result)[:200] if result.result else f"Error: {result.error}"
            exp = StrategyExperience(
                id=str(uuid.uuid4()),
                scenario=scenario_tag.scenario,
                complexity=scenario_tag.complexity,
                task_hash=task_hash,
                task_text=task_text[:200],
                strategy=name,
                layer=layer,
                quality_score=result.quality_score,
                response_quality=result.quality_score * 0.7,
                reasoning_depth=result.quality_score * 0.3,
                execution_time=result.execution_time,
                token_cost=result.token_cost,
                result_summary=summary,
                selected=(name == selected.strategy_name),
                improvement_notes="",
                timestamp=timestamp,
                embedding=None,
            )
            try:
                conn = sqlite3.connect(self.experience_db_path)
                conn.execute("""
                    INSERT INTO strategy_experience VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                """, [
                    exp.id, exp.scenario, exp.complexity, exp.task_hash,
                    exp.task_text, exp.strategy, exp.layer, exp.quality_score,
                    exp.response_quality, exp.reasoning_depth, exp.execution_time,
                    exp.token_cost, exp.result_summary, int(exp.selected),
                    exp.improvement_notes, exp.timestamp.isoformat(), None
                ])
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"[StrategyRouter] Failed to record experience: {e}")
