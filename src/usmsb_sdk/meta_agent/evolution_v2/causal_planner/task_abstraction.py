"""
任务抽象

CausalPlanner 的组件

用 LLM 提取任务的关键实体和因果关系
"""

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class TaskAbstraction:
    """任务抽象"""
    entities: list[str]
    relations: list[dict[str, str]]
    goal: str
    causal_subgraph: Any = None


class TaskAbstractionEngine:
    """
    任务抽象引擎

    用 LLM 理解任务结构，提取关键实体和因果关系
    """

    def __init__(self, llm_manager=None):
        self.llm = llm_manager

    async def abstract(
        self,
        task: Any,
        context: dict[str, Any] | None = None,
    ) -> TaskAbstraction:
        """
        抽象任务

        Args:
            task: 任务描述
            context: 上下文

        Returns:
            任务抽象
        """
        if not self.llm:
            return self._default_abstract(task)

        prompt = f"""
        分析任务描述，提取关键实体和它们之间的因果关系。

        任务：{task.description if hasattr(task, 'description') else task}

        输出格式（JSON）：
        {{
            "entities": ["实体1", "实体2", ...],
            "relations": [
                {{"from": "实体1", "to": "实体2", "type": "causal"}},
                ...
            ],
            "goal": "最终目标"
        }}
        """

        try:
            response = await self.llm.analyze(prompt)
            return self._parse_abstract(response)
        except Exception:
            return self._default_abstract(task)

    def _parse_abstract(self, response: str) -> TaskAbstraction:
        """解析抽象结果"""
        try:
            # 尝试解析 JSON
            data = json.loads(response)
            return TaskAbstraction(
                entities=data.get("entities", []),
                relations=data.get("relations", []),
                goal=data.get("goal", ""),
            )
        except Exception:
            return self._default_abstract(response)

    def _default_abstract(self, task: Any) -> TaskAbstraction:
        """默认抽象"""
        task_text = task.description if hasattr(task, "description") else str(task)
        return TaskAbstraction(
            entities=[task_text[:50]],
            relations=[],
            goal=task_text,
        )


class TaskFeatureExtractor:
    """
    任务特征提取器

    从任务描述中提取结构化特征
    """

    def __init__(self):
        pass

    def extract(self, task: Any) -> dict[str, Any]:
        """
        提取任务特征

        Args:
            task: 任务

        Returns:
            特征字典
        """
        task_text = task.description if hasattr(task, "description") else str(task)
        task_text_lower = task_text.lower()

        features = {
            "input_size": "medium",
            "input_type": "mixed",
            "has_api": False,
            "has_database": False,
            "is_real_time": False,
            "domain_area": "general",
            "accuracy_required": 0.7,
            "creativity_required": 0.3,
        }

        # 检测输入大小
        if any(kw in task_text_lower for kw in ["大量", "批量", "批量处理", "large", "batch"]):
            features["input_size"] = "large"
        elif any(kw in task_text_lower for kw in ["少量", "简单", "small", "simple"]):
            features["input_size"] = "small"

        # 检测输入类型
        if any(kw in task_text_lower for kw in ["代码", "code", "编程", "program"]):
            features["input_type"] = "code"
        elif any(kw in task_text_lower for kw in ["数据", "分析", "data", "analyze"]):
            features["input_type"] = "data"
        elif any(kw in task_text_lower for kw in ["文档", "文档处理", "document"]):
            features["input_type"] = "text"

        # 检测 API
        if any(kw in task_text_lower for kw in ["api", "接口", "调用", "http", "rest"]):
            features["has_api"] = True

        # 检测数据库
        if any(kw in task_text_lower for kw in ["数据库", "db", "sql", "存储", "database"]):
            features["has_database"] = True

        # 检测实时性
        if any(kw in task_text_lower for kw in ["实时", "流", "realtime", "stream"]):
            features["is_real_time"] = True

        # 检测领域
        if any(kw in task_text_lower for kw in ["金融", "股票", "financial"]):
            features["domain_area"] = "finance"
        elif any(kw in task_text_lower for kw in ["图像", "图片", "视觉", "image", "vision"]):
            features["domain_area"] = "computer_vision"
        elif any(kw in task_text_lower for kw in ["文本", "nlp", "语言", "text", "language"]):
            features["domain_area"] = "nlp"

        # 检测质量要求
        if any(kw in task_text_lower for kw in ["准确", "精确", "accuracy", "precise"]):
            features["accuracy_required"] = 0.9

        if any(kw in task_text_lower for kw in ["创意", "新颖", "creative", "novel"]):
            features["creativity_required"] = 0.8

        return features
