"""
USMSB Universal Action Interfaces and Implementations

This module provides the 9 universal action interfaces defined in the USMSB model:
1. Perception - 感知
2. Decision - 决策
3. Execution - 执行
4. Interaction - 交互
5. Transformation - 转化
6. Evaluation - 评估
7. Feedback - 反馈
8. Learning - 学习
9. RiskManagement - 风险管理

Each interface has an LLM-powered implementation.
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============== Action Result Types ==============

class ActionResultStatus(StrEnum):
    """Status of an action result."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    PENDING = "pending"


@dataclass
class ActionResult(Generic[T]):
    """Result of an action execution."""
    status: ActionResultStatus
    data: T | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ============== 9 Universal Action Interfaces ==============

class IPerceptionService(ABC):
    """
    感知服务接口

    提供感知能力，如文本理解、图像识别、数据分析等。
    从环境中获取并理解信息。
    """

    @abstractmethod
    async def perceive(
        self,
        input_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        感知输入数据，提取结构化信息。

        Args:
            input_data: 输入数据（文本、图像、音频等）
            context: 感知上下文

        Returns:
            感知结果，包含提取的信息
        """
        pass

    @abstractmethod
    async def extract_entities(
        self,
        text: str,
        entity_types: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """从文本中提取实体。"""
        pass

    @abstractmethod
    async def analyze_sentiment(
        self,
        text: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """分析文本情感。"""
        pass


class IDecisionService(ABC):
    """
    决策服务接口

    提供决策能力，如行动选择、策略生成、路径规划等。
    根据目标、规则、信息等选择行动方案或策略。
    """

    @abstractmethod
    async def decide(
        self,
        agent: Any,
        goal: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        为Agent做出决策。

        Args:
            agent: 决策主体
            goal: 决策目标
            context: 决策上下文

        Returns:
            决策结果，包含行动方案
        """
        pass

    @abstractmethod
    async def plan_actions(
        self,
        goal: Any,
        constraints: dict[str, Any] | None = None,
        available_actions: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """规划行动序列以达成目标。"""
        pass

    @abstractmethod
    async def select_strategy(
        self,
        situation: dict[str, Any],
        strategies: list[dict[str, Any]],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """从多个策略中选择最优策略。"""
        pass


class IExecutionService(ABC):
    """
    执行服务接口

    提供执行能力，如代码执行、API调用、模拟操作等。
    实施决策，将抽象行动转化为具体操作。
    """

    @abstractmethod
    async def execute(
        self,
        action: dict[str, Any],
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        执行一个行动。

        Args:
            action: 行动描述
            agent: 执行主体
            context: 执行上下文

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行代码。"""
        pass

    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """调用外部工具。"""
        pass


class IInteractionService(ABC):
    """
    交互服务接口

    提供交互能力，如多Agent通信、人机对话等。
    Agent之间或Agent与环境/用户之间的信息交换和协作。
    """

    @abstractmethod
    async def interact(
        self,
        sender: Any,
        receiver: Any,
        message: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        在两个实体之间进行交互。

        Args:
            sender: 发送方
            receiver: 接收方
            message: 消息内容
            context: 交互上下文

        Returns:
            交互结果
        """
        pass

    @abstractmethod
    async def broadcast(
        self,
        sender: Any,
        recipients: list[Any],
        message: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """广播消息给多个接收者。"""
        pass

    @abstractmethod
    async def negotiate(
        self,
        parties: list[Any],
        topic: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """在多方之间进行协商。"""
        pass


class ITransformationService(ABC):
    """
    转化服务接口

    提供转化能力，如数据格式转换、资源形态转换等。
    资源形态、数据格式等的改变，实现价值增值。
    """

    @abstractmethod
    async def transform(
        self,
        input_data: Any,
        target_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        将输入转化为目标类型。

        Args:
            input_data: 输入数据
            target_type: 目标类型
            context: 转化上下文

        Returns:
            转化结果
        """
        pass

    @abstractmethod
    async def convert_format(
        self,
        data: Any,
        from_format: str,
        to_format: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """转换数据格式。"""
        pass

    @abstractmethod
    async def synthesize(
        self,
        inputs: list[Any],
        synthesis_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """合成多个输入为新的输出。"""
        pass


class IEvaluationService(ABC):
    """
    评估服务接口

    提供评估能力，如效果评估、风险评估、价值评估等。
    衡量行动结果、系统状态与目标的符合程度。
    """

    @abstractmethod
    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        根据标准评估项目。

        Args:
            item: 待评估项目
            criteria: 评估标准
            context: 评估上下文

        Returns:
            评估结果
        """
        pass

    @abstractmethod
    async def compare(
        self,
        items: list[Any],
        criteria: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """比较多个项目。"""
        pass

    @abstractmethod
    async def measure_performance(
        self,
        entity: Any,
        metrics: list[str],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """测量实体性能。"""
        pass


class IFeedbackService(ABC):
    """
    反馈服务接口

    提供反馈处理能力，如用户反馈分析、系统自适应调整等。
    处理评估结果，将其作为输入调整后续行动或策略。
    """

    @abstractmethod
    async def process_feedback(
        self,
        feedback_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        处理反馈数据。

        Args:
            feedback_data: 反馈数据
            context: 处理上下文

        Returns:
            处理结果，包含调整建议
        """
        pass

    @abstractmethod
    async def collect_feedback(
        self,
        source: Any,
        feedback_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """收集反馈。"""
        pass

    @abstractmethod
    async def generate_adjustments(
        self,
        feedback_history: list[Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """根据反馈历史生成调整建议。"""
        pass


class ILearningService(ABC):
    """
    学习服务接口

    提供学习能力，如模型微调、知识更新、行为优化等。
    从经验中获取知识，优化Agent的行为模式和能力。
    """

    @abstractmethod
    async def learn(
        self,
        experience_data: Any,
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        从经验中学习。

        Args:
            experience_data: 经验数据
            agent: 学习主体
            context: 学习上下文

        Returns:
            学习结果
        """
        pass

    @abstractmethod
    async def update_knowledge(
        self,
        knowledge: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """更新知识库。"""
        pass

    @abstractmethod
    async def optimize_behavior(
        self,
        agent: Any,
        performance_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """优化Agent行为。"""
        pass


class IRiskManagementService(ABC):
    """
    风险管理服务接口

    提供风险管理能力，如风险识别、风险规避、风险缓解等。
    识别、评估、规避和缓解潜在风险。
    """

    @abstractmethod
    async def manage_risk(
        self,
        risk: Any,
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """
        管理风险。

        Args:
            risk: 风险对象
            agent: 风险管理主体
            context: 管理上下文

        Returns:
            风险管理结果
        """
        pass

    @abstractmethod
    async def identify_risks(
        self,
        situation: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """识别潜在风险。"""
        pass

    @abstractmethod
    async def assess_risk(
        self,
        risk: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """评估风险等级。"""
        pass

    @abstractmethod
    async def mitigate_risk(
        self,
        risk: Any,
        strategy: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """缓解风险。"""
        pass


# ============== LLM-Powered Implementations ==============

class LLMPerceptionService(IPerceptionService):
    """LLM驱动的感知服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def perceive(
        self,
        input_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM进行感知。"""
        start_time = time.time()
        try:
            if isinstance(input_data, str):
                # 文本感知
                prompt = f"""分析以下输入，提取关键信息和结构化数据：

输入：{input_data}

请以JSON格式返回提取的信息，包含以下字段：
- type: 输入类型
- entities: 识别的实体列表
- key_information: 关键信息
- sentiment: 情感倾向
- intent: 可能的意图"""

                response = await self.llm.generate_text(prompt, context)

                return ActionResult(
                    status=ActionResultStatus.SUCCESS,
                    data={"analysis": response, "input_type": "text"},
                    execution_time=time.time() - start_time
                )
            else:
                # 其他类型数据
                return ActionResult(
                    status=ActionResultStatus.PARTIAL,
                    data={"input": input_data, "note": "Non-text input processed"},
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            logger.error(f"Perception failed: {e}")
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def extract_entities(
        self,
        text: str,
        entity_types: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM提取实体。"""
        start_time = time.time()
        try:
            entity_hint = f"关注以下实体类型：{', '.join(entity_types)}" if entity_types else ""
            prompt = f"""从以下文本中提取所有实体：

{text}

{entity_hint}

请以JSON格式返回，格式为：{{"entities": [{{"name": "...", "type": "...", "relevance": 0.0-1.0}}]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"raw_response": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def analyze_sentiment(
        self,
        text: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM分析情感。"""
        start_time = time.time()
        try:
            prompt = f"""分析以下文本的情感倾向：

{text}

请返回JSON格式的分析结果：{{"sentiment": "positive/negative/neutral", "confidence": 0.0-1.0, "emotions": ["emotion1", "emotion2"]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"raw_response": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMDecisionService(IDecisionService):
    """LLM驱动的决策服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def decide(
        self,
        agent: Any,
        goal: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM进行决策。"""
        start_time = time.time()
        try:
            agent_info = getattr(agent, 'name', str(agent)) if agent else "Unknown Agent"
            goal_info = getattr(goal, 'name', str(goal)) if goal else "Unknown Goal"

            prompt = f"""作为一个决策系统，请为以下情况做出决策：

Agent: {agent_info}
Goal: {goal_info}
Context: {json.dumps(context) if context else 'None'}

请分析当前情况，考虑可能的行动选项，并给出最佳决策。
返回JSON格式：{{"decision": "...", "reasoning": "...", "confidence": 0.0-1.0, "alternatives": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"decision": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def plan_actions(
        self,
        goal: Any,
        constraints: dict[str, Any] | None = None,
        available_actions: list[str] | None = None,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM规划行动序列。"""
        start_time = time.time()
        try:
            goal_info = getattr(goal, 'name', str(goal)) if goal else str(goal)

            prompt = f"""规划一个行动序列来达成以下目标：

目标：{goal_info}
约束条件：{json.dumps(constraints) if constraints else '无'}
可用行动：{', '.join(available_actions) if available_actions else '无限制'}

请返回详细的行动计划，格式为JSON：
{{"plan": [{{"step": 1, "action": "...", "expected_outcome": "...", "dependencies": []}}], "estimated_time": "...", "risk_level": "low/medium/high"}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"plan": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def select_strategy(
        self,
        situation: dict[str, Any],
        strategies: list[dict[str, Any]],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """使用LLM选择策略。"""
        start_time = time.time()
        try:
            prompt = f"""根据当前情况，从以下策略中选择最优策略：

情况：{json.dumps(situation, ensure_ascii=False)}

可选策略：
{json.dumps(strategies, ensure_ascii=False, indent=2)}

请分析每个策略的优劣，选择最优策略并说明理由。
返回JSON格式：{{"selected_strategy": "...", "reasoning": "...", "score": 0.0-1.0, "alternatives_ranked": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"selection": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMExecutionService(IExecutionService):
    """LLM驱动的执行服务实现。"""

    def __init__(self, llm_adapter, tool_registry=None):
        self.llm = llm_adapter
        self.tool_registry = tool_registry or {}

    async def execute(
        self,
        action: dict[str, Any],
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行行动。"""
        start_time = time.time()
        try:
            action_type = action.get("type", "generic")

            if action_type == "code":
                return await self.execute_code(
                    action.get("code", ""),
                    action.get("language", "python"),
                    context
                )
            elif action_type == "tool_call":
                return await self.call_tool(
                    action.get("tool", ""),
                    action.get("params", {}),
                    context
                )
            else:
                # 通用执行 - 让LLM生成执行方案
                prompt = f"""执行以下行动：

行动：{json.dumps(action, ensure_ascii=False)}

请生成详细的执行步骤和预期结果。
返回JSON格式：{{"steps_executed": [...], "result": "...", "status": "success/failure"}}"""

                response = await self.llm.generate_text(prompt, context)

                return ActionResult(
                    status=ActionResultStatus.SUCCESS,
                    data={"execution_plan": response},
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def execute_code(
        self,
        code: str,
        language: str = "python",
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行代码（沙箱环境）。"""
        start_time = time.time()
        try:
            # 安全警告：生产环境应使用真正的沙箱
            if language == "python":
                import os
                import subprocess
                import tempfile

                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_file = f.name

                try:
                    result = subprocess.run(
                        ['python', temp_file],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )

                    return ActionResult(
                        status=ActionResultStatus.SUCCESS if result.returncode == 0 else ActionResultStatus.FAILURE,
                        data={
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "return_code": result.returncode,
                        },
                        execution_time=time.time() - start_time
                    )
                finally:
                    os.unlink(temp_file)
            else:
                return ActionResult(
                    status=ActionResultStatus.FAILURE,
                    error=f"Unsupported language: {language}",
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """调用工具。"""
        start_time = time.time()
        try:
            if tool_name in self.tool_registry:
                tool_func = self.tool_registry[tool_name]
                result = await tool_func(**params) if asyncio.iscoroutinefunction(tool_func) else tool_func(**params)

                return ActionResult(
                    status=ActionResultStatus.SUCCESS,
                    data={"tool": tool_name, "result": result},
                    execution_time=time.time() - start_time
                )
            else:
                return ActionResult(
                    status=ActionResultStatus.FAILURE,
                    error=f"Tool not found: {tool_name}",
                    execution_time=time.time() - start_time
                )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMInteractionService(IInteractionService):
    """LLM驱动的交互服务实现。"""

    def __init__(self, llm_adapter, communication_manager=None):
        self.llm = llm_adapter
        self.communication_manager = communication_manager

    async def interact(
        self,
        sender: Any,
        receiver: Any,
        message: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行交互。"""
        start_time = time.time()
        try:
            sender_name = getattr(sender, 'name', str(sender)) if sender else "Unknown"
            receiver_name = getattr(receiver, 'name', str(receiver)) if receiver else "Unknown"

            # 如果有通信管理器，使用它发送消息
            if self.communication_manager:
                result = await self.communication_manager.send(
                    recipient=receiver,
                    subject=f"Message from {sender_name}",
                    content=message,
                )
                return ActionResult(
                    status=ActionResultStatus.SUCCESS,
                    data={"delivered": True, "receipt": str(result)},
                    execution_time=time.time() - start_time
                )

            # 否则使用LLM模拟交互
            prompt = f"""模拟以下交互：

发送方：{sender_name}
接收方：{receiver_name}
消息：{json.dumps(message) if isinstance(message, dict) else str(message)}

请生成接收方可能的响应。
返回JSON格式：{{"response": "...", "reaction": "...", "follow_up_needed": true/false}}"""

            response = await self.llm.generate_text(prompt, context)

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data={"simulated_response": response},
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def broadcast(
        self,
        sender: Any,
        recipients: list[Any],
        message: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """广播消息。"""
        start_time = time.time()
        results = []

        for recipient in recipients:
            result = await self.interact(sender, recipient, message, context)
            results.append({
                "recipient": getattr(recipient, 'name', str(recipient)) if recipient else "Unknown",
                "status": result.status.value
            })

        return ActionResult(
            status=ActionResultStatus.SUCCESS,
            data={"broadcast_results": results, "total": len(recipients)},
            execution_time=time.time() - start_time
        )

    async def negotiate(
        self,
        parties: list[Any],
        topic: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行协商。"""
        start_time = time.time()
        try:
            parties_info = [getattr(p, 'name', str(p)) for p in parties]

            prompt = f"""模拟以下多方协商：

参与方：{', '.join(parties_info)}
协商主题：{topic}

请模拟协商过程并给出可能的协商结果。
返回JSON格式：{{"process": [...], "agreement": "...", "terms": {{}}, "participants_satisfied": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"negotiation_result": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMTransformationService(ITransformationService):
    """LLM驱动的转化服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def transform(
        self,
        input_data: Any,
        target_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行转化。"""
        start_time = time.time()
        try:
            prompt = f"""将以下输入转化为{target_type}格式：

输入：{json.dumps(input_data, ensure_ascii=False) if isinstance(input_data, (dict, list)) else str(input_data)}

请执行转化并返回结果。"""

            response = await self.llm.generate_text(prompt, context)

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data={"transformed": response, "target_type": target_type},
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def convert_format(
        self,
        data: Any,
        from_format: str,
        to_format: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """转换格式。"""
        start_time = time.time()
        try:
            import json as json_module

            import yaml

            result = data

            # 尝试实际转换
            if from_format == "json" and to_format == "yaml":
                if isinstance(data, str):
                    data = json_module.loads(data)
                result = yaml.dump(data, default_flow_style=False)
            elif from_format == "yaml" and to_format == "json":
                if isinstance(data, str):
                    data = yaml.safe_load(data)
                result = json_module.dumps(data, indent=2)
            elif from_format == "dict" and to_format == "json":
                result = json_module.dumps(data, indent=2)
            else:
                # 使用LLM进行复杂转换
                result = await self.transform(data, to_format, context)
                result = result.data.get("transformed", str(data))

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data={"converted": result, "from": from_format, "to": to_format},
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def synthesize(
        self,
        inputs: list[Any],
        synthesis_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """合成多个输入。"""
        start_time = time.time()
        try:
            prompt = f"""将以下多个输入合成为{synthesis_type}：

输入：
{json.dumps(inputs, ensure_ascii=False, indent=2)}

请执行合成并返回结果。"""

            response = await self.llm.generate_text(prompt, context)

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data={"synthesized": response, "type": synthesis_type},
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMEvaluationService(IEvaluationService):
    """LLM驱动的评估服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def evaluate(
        self,
        item: Any,
        criteria: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """执行评估。"""
        start_time = time.time()
        try:
            prompt = f"""根据以下标准评估项目：

项目：{json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)}

评估标准：{criteria}

请给出详细评估，返回JSON格式：
{{"score": 0.0-1.0, "analysis": "...", "strengths": [...], "weaknesses": [...], "recommendations": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"evaluation": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def compare(
        self,
        items: list[Any],
        criteria: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """比较多个项目。"""
        start_time = time.time()
        try:
            prompt = f"""根据以下标准比较多个项目：

项目：{json.dumps(items, ensure_ascii=False, indent=2)}

比较标准：{criteria}

请给出比较结果，返回JSON格式：
{{"rankings": [...], "comparison_matrix": {{}}, "analysis": "..."}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"comparison": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def measure_performance(
        self,
        entity: Any,
        metrics: list[str],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """测量性能。"""
        start_time = time.time()
        try:
            entity_name = getattr(entity, 'name', str(entity)) if entity else "Unknown"

            prompt = f"""测量以下实体的性能：

实体：{entity_name}
指标：{', '.join(metrics)}

请根据可用信息给出性能测量结果。
返回JSON格式：{{"metrics": {{}}, "overall_score": 0.0-1.0, "analysis": "..."}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"performance": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMFeedbackService(IFeedbackService):
    """LLM驱动的反馈服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def process_feedback(
        self,
        feedback_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """处理反馈。"""
        start_time = time.time()
        try:
            prompt = f"""分析以下反馈数据并生成改进建议：

反馈数据：{json.dumps(feedback_data, ensure_ascii=False) if isinstance(feedback_data, (dict, list)) else str(feedback_data)}

请分析反馈内容，识别问题，并生成具体的改进建议。
返回JSON格式：{{"analysis": "...", "issues_identified": [...], "recommendations": [...], "priority": "high/medium/low"}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"feedback_analysis": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def collect_feedback(
        self,
        source: Any,
        feedback_type: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """收集反馈。"""
        start_time = time.time()
        # 在实际实现中，这里会从实际来源收集反馈
        return ActionResult(
            status=ActionResultStatus.SUCCESS,
            data={
                "source": getattr(source, 'name', str(source)) if source else "Unknown",
                "type": feedback_type,
                "collected": True
            },
            execution_time=time.time() - start_time
        )

    async def generate_adjustments(
        self,
        feedback_history: list[Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """生成调整建议。"""
        start_time = time.time()
        try:
            prompt = f"""根据以下反馈历史生成系统调整建议：

反馈历史：{json.dumps(feedback_history, ensure_ascii=False, indent=2)}

请分析历史趋势，识别模式，并生成具体的调整建议。
返回JSON格式：{{"trends": [...], "adjustments": [...], "expected_improvements": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"adjustments": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMLearningService(ILearningService):
    """LLM驱动的学习服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter
        self._learned_knowledge: dict[str, Any] = {}

    async def learn(
        self,
        experience_data: Any,
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """从经验中学习。"""
        start_time = time.time()
        try:
            agent_name = getattr(agent, 'name', str(agent)) if agent else "Unknown"

            prompt = f"""分析以下经验数据并提取学习内容：

经验数据：{json.dumps(experience_data, ensure_ascii=False) if isinstance(experience_data, (dict, list)) else str(experience_data)}
学习主体：{agent_name}

请分析经验，提取关键学习内容，并生成行为改进建议。
返回JSON格式：{{"learnings": [...], "knowledge_gained": {{}}, "behavior_adjustments": [...], "confidence": 0.0-1.0}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
                # 存储学习到的知识
                self._learned_knowledge[agent_name] = data.get("knowledge_gained", {})
            except:
                data = {"learning_result": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def update_knowledge(
        self,
        knowledge: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """更新知识。"""
        start_time = time.time()
        # 存储新知识
        knowledge_id = str(uuid.uuid4())[:8]
        self._learned_knowledge[knowledge_id] = knowledge

        return ActionResult(
            status=ActionResultStatus.SUCCESS,
            data={"knowledge_id": knowledge_id, "stored": True},
            execution_time=time.time() - start_time
        )

    async def optimize_behavior(
        self,
        agent: Any,
        performance_data: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """优化行为。"""
        start_time = time.time()
        try:
            agent_name = getattr(agent, 'name', str(agent)) if agent else "Unknown"

            prompt = f"""根据性能数据优化Agent行为：

Agent：{agent_name}
性能数据：{json.dumps(performance_data, ensure_ascii=False)}

请分析性能瓶颈并生成行为优化建议。
返回JSON格式：{{"optimizations": [...], "expected_improvement": "...", "priority_actions": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"optimization_result": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


class LLMRiskManagementService(IRiskManagementService):
    """LLM驱动的风险管理服务实现。"""

    def __init__(self, llm_adapter):
        self.llm = llm_adapter

    async def manage_risk(
        self,
        risk: Any,
        agent: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """管理风险。"""
        start_time = time.time()
        try:
            risk_info = getattr(risk, 'name', str(risk)) if risk else "Unknown Risk"
            agent_name = getattr(agent, 'name', str(agent)) if agent else "Unknown Agent"

            prompt = f"""管理以下风险：

风险：{risk_info}
风险管理主体：{agent_name}

请制定风险管理策略并给出具体行动建议。
返回JSON格式：{{"strategy": "...", "actions": [...], "mitigation_steps": [...], "monitoring_points": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"risk_management": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def identify_risks(
        self,
        situation: dict[str, Any],
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """识别风险。"""
        start_time = time.time()
        try:
            prompt = f"""识别以下情况中的潜在风险：

情况：{json.dumps(situation, ensure_ascii=False, indent=2)}

请全面分析并列出所有潜在风险。
返回JSON格式：{{"risks": [{{"name": "...", "type": "...", "probability": 0.0-1.0, "impact": 0.0-1.0}}], "overall_risk_level": "low/medium/high"}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"risks_identified": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def assess_risk(
        self,
        risk: Any,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """评估风险。"""
        start_time = time.time()
        try:
            risk_info = getattr(risk, 'name', str(risk)) if risk else str(risk)

            prompt = f"""评估以下风险：

风险：{risk_info if isinstance(risk_info, str) else json.dumps(risk_info, ensure_ascii=False)}

请给出详细的风险评估。
返回JSON格式：{{"probability": 0.0-1.0, "impact": 0.0-1.0, "severity": "low/medium/high/critical", "affected_areas": [...], "assessment_reasoning": "..."}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"risk_assessment": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )

    async def mitigate_risk(
        self,
        risk: Any,
        strategy: str,
        context: dict[str, Any] | None = None
    ) -> ActionResult:
        """缓解风险。"""
        start_time = time.time()
        try:
            risk_info = getattr(risk, 'name', str(risk)) if risk else str(risk)

            prompt = f"""使用{strategy}策略缓解以下风险：

风险：{risk_info if isinstance(risk_info, str) else json.dumps(risk_info, ensure_ascii=False)}

请制定详细的缓解计划。
返回JSON格式：{{"mitigation_plan": [...], "resources_needed": [...], "timeline": "...", "success_metrics": [...]}}"""

            response = await self.llm.generate_text(prompt, context)

            try:
                data = json.loads(response)
            except:
                data = {"mitigation": response}

            return ActionResult(
                status=ActionResultStatus.SUCCESS,
                data=data,
                execution_time=time.time() - start_time
            )
        except Exception as e:
            return ActionResult(
                status=ActionResultStatus.FAILURE,
                error=str(e),
                execution_time=time.time() - start_time
            )


# ============== Service Factory ==============

class UniversalActionServiceFactory:
    """通用行动服务工厂。"""

    @staticmethod
    def create_all_services(llm_adapter) -> dict[str, Any]:
        """创建所有通用行动服务。"""
        return {
            "perception": LLMPerceptionService(llm_adapter),
            "decision": LLMDecisionService(llm_adapter),
            "execution": LLMExecutionService(llm_adapter),
            "interaction": LLMInteractionService(llm_adapter),
            "transformation": LLMTransformationService(llm_adapter),
            "evaluation": LLMEvaluationService(llm_adapter),
            "feedback": LLMFeedbackService(llm_adapter),
            "learning": LLMLearningService(llm_adapter),
            "risk_management": LLMRiskManagementService(llm_adapter),
        }
