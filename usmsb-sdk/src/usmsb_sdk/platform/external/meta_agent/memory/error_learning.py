"""
错误驱动学习系统
核心思路：错误发生 → 问LLM解决 → 记住经验 → 下次直接用

基于 USMSB 设计文档 v1.0 实现
"""

import asyncio
import json
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """错误类型"""
    JSON_FORMAT = "json_format"            # JSON格式错误
    PARAMETER_ERROR = "parameter_error"    # 参数错误
    CONTEXT_OVERFLOW = "context_overflow"  # 上下文超限
    PERMISSION_ERROR = "permission_error"  # 权限错误
    NETWORK_ERROR = "network_error"       # 网络错误
    TIMEOUT_ERROR = "timeout_error"        # 超时错误
    TOOL_NOT_FOUND = "tool_not_found"      # 工具未找到
    EXECUTION_ERROR = "execution_error"    # 执行错误
    UNKNOWN_ERROR = "unknown_error"        # 未知错误


class SolutionType(str, Enum):
    """解决方案类型"""
    RETRY = "retry"                      # 重试
    FIX_PARAMS = "fix_params"            # 修复参数
    USE_ALTERNATIVE = "use_alternative"   # 使用替代方案
    SKIP = "skip"                        # 跳过
    ESCALATE = "escalate"                 # 升级


@dataclass
class ErrorRecord:
    """错误记录"""
    id: str = field(default_factory=lambda: str(uuid4()))
    error_type: ErrorType = ErrorType.UNKNOWN_ERROR
    error_message: str = ""
    error_traceback: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    tool_name: Optional[str] = None
    occurrence_count: int = 1
    first_occurred: float = field(default_factory=lambda: datetime.now().timestamp())
    last_occurred: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Solution:
    """解决方案"""
    id: str = field(default_factory=lambda: str(uuid4()))
    solution_type: SolutionType = SolutionType.RETRY
    solution_data: Dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    prevent_future: str = ""
    success_rate: float = 0.0
    times_used: int = 0
    times_succeeded: int = 0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


class ErrorDrivenLearning:
    """
    错误驱动学习系统

    核心机制：
    1. 识别错误类型
    2. 检查已知解决方案
    3. 如果没有，问LLM
    4. 应用解决方案
    5. 记录和更新经验
    """

    def __init__(self, llm_manager, experience_db=None):
        """
        初始化错误驱动学习系统

        Args:
            llm_manager: LLM管理器
            experience_db: 经验数据库（可选）
        """
        self.llm = llm_manager
        self.experience_db = experience_db

        # 错误记录缓存
        self._error_cache: Dict[str, ErrorRecord] = {}

        # 解决方案缓存
        self._solutions_cache: Dict[str, Solution] = {}

        # 错误类型识别器
        self.error_classifiers = {
            ErrorType.JSON_FORMAT: self._is_json_error,
            ErrorType.PARAMETER_ERROR: self._is_parameter_error,
            ErrorType.CONTEXT_OVERFLOW: self._is_context_overflow,
            ErrorType.PERMISSION_ERROR: self._is_permission_error,
            ErrorType.NETWORK_ERROR: self._is_network_error,
            ErrorType.TIMEOUT_ERROR: self._is_timeout_error,
            ErrorType.TOOL_NOT_FOUND: self._is_tool_not_found,
            ErrorType.EXECUTION_ERROR: self._is_execution_error,
        }

        # 配置
        self.max_retries = 5
        self.solution_confidence_threshold = 0.5

    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        tool_registry: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理错误的完整流程

        Args:
            error: 异常对象
            context: 上下文信息
            tool_registry: 工具注册表

        Returns:
            解决方案结果
        """
        error_msg = str(error)
        error_key = self._get_error_key(error_msg, context)

        # Step 1: 识别错误类型
        error_type = self._classify_error(error, context)

        # 更新错误记录
        error_record = await self._update_error_record(
            error_key, error_type, error_msg, context
        )

        # Step 2: 检查已知解决方案
        solution = await self._check_known_solution(
            error_type, error_msg, context
        )

        if solution:
            logger.info(f"Found known solution for {error_type.value}: {solution.solution_type.value}")
            # 应用并记录结果
            result = await self._apply_solution(solution, context)
            await self._record_solution_result(solution, result.get("success", False))
            return result

        # Step 3: 没有已知方案，问LLM
        logger.info(f"No known solution for {error_type.value}, asking LLM...")
        solution = await self._ask_llm_solution(
            error_type, error, context, tool_registry
        )

        if solution:
            # Step 4: 应用解决方案
            result = await self._apply_solution(solution, context)

            # Step 5: 记录经验
            await self._record_experience(error_type, error_msg, solution, context)

            return result

        # 无法解决
        logger.error(f"Cannot resolve error: {error_msg}")
        return {
            "action": "cannot_resolve",
            "error": error_msg,
            "context": context
        }

    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorType:
        """识别错误类型"""
        error_msg = str(error)

        for error_type, classifier in self.error_classifiers.items():
            if classifier(error_msg, context):
                return error_type

        return ErrorType.UNKNOWN_ERROR

    def _is_json_error(self, error_msg: str, context: Dict) -> bool:
        """是否是JSON格式错误"""
        json_indicators = ["json", "expecting", "decode", "invalid json", "JSONDecodeError"]
        return any(ind in error_msg.lower() for ind in json_indicators)

    def _is_parameter_error(self, error_msg: str, context: Dict) -> bool:
        """是否是参数错误"""
        param_indicators = ["parameter", "argument", "missing", "required", "TypeError"]
        return any(ind in error_msg.lower() for ind in param_indicators)

    def _is_context_overflow(self, error_msg: str, context: Dict) -> bool:
        """是否是上下文超限"""
        context_indicators = ["context", "length", "maximum", "tokens", "too long", "context_length"]
        return any(ind in error_msg.lower() for ind in context_indicators)

    def _is_permission_error(self, error_msg: str, context: Dict) -> bool:
        """是否是权限错误"""
        perm_indicators = ["permission", "denied", "unauthorized", "forbidden", "access denied"]
        return any(ind in error_msg.lower() for ind in perm_indicators)

    def _is_network_error(self, error_msg: str, context: Dict) -> bool:
        """是否是网络错误"""
        net_indicators = ["connection", "network", "dns", "refused", "ConnectionError"]
        return any(ind in error_msg.lower() for ind in net_indicators)

    def _is_timeout_error(self, error_msg: str, context: Dict) -> bool:
        """是否是超时错误"""
        return "timeout" in error_msg.lower()

    def _is_tool_not_found(self, error_msg: str, context: Dict) -> bool:
        """是否是工具未找到"""
        return "not found" in error_msg.lower() or "does not exist" in error_msg.lower()

    def _is_execution_error(self, error_msg: str, context: Dict) -> bool:
        """是否是执行错误"""
        exec_indicators = ["execution", "failed", "error", "exception"]
        return any(ind in error_msg.lower() for ind in exec_indicators)

    async def _update_error_record(
        self,
        error_key: str,
        error_type: ErrorType,
        error_msg: str,
        context: Dict[str, Any]
    ) -> ErrorRecord:
        """更新错误记录"""
        if error_key in self._error_cache:
            record = self._error_cache[error_key]
            record.occurrence_count += 1
            record.last_occurred = datetime.now().timestamp()
            record.error_message = error_msg
            return record

        record = ErrorRecord(
            error_type=error_type,
            error_message=error_msg,
            context=context,
            tool_name=context.get("tool_name")
        )
        self._error_cache[error_key] = record
        return record

    def _get_error_key(self, error_msg: str, context: Dict[str, Any]) -> str:
        """生成错误唯一键"""
        tool_name = context.get("tool_name", "unknown")
        # 只取错误消息前50个字符作为键
        error_prefix = error_msg[:50].replace(" ", "_")
        return f"{tool_name}_{error_prefix}"

    async def _check_known_solution(
        self,
        error_type: ErrorType,
        error_msg: str,
        context: Dict[str, Any]
    ) -> Optional[Solution]:
        """检查已知解决方案"""
        # 先检查内存缓存
        error_key = self._get_error_key(error_msg, context)
        if error_key in self._solutions_cache:
            return self._solutions_cache[error_key]

        # 从经验库查询
        if self.experience_db:
            try:
                solutions = await self.experience_db.search_solutions(
                    error_type=error_type.value,
                    tool_name=context.get("tool_name")
                )
                if solutions:
                    solution = solutions[0]
                    self._solutions_cache[error_key] = solution
                    return solution
            except Exception as e:
                logger.warning(f"Failed to search solutions from DB: {e}")

        return None

    async def _ask_llm_solution(
        self,
        error_type: ErrorType,
        error: Exception,
        context: Dict[str, Any],
        tool_registry: Optional[Dict[str, Any]] = None
    ) -> Optional[Solution]:
        """调用LLM获取解决方案"""
        tool_list = list(tool_registry.keys()) if tool_registry else []

        prompt = f"""作为错误解决专家，请为以下错误提供解决方案。

错误类型: {error_type.value}
错误信息: {str(error)}
错误堆栈:
{traceback.format_exc()[:1000]}

上下文:
{json.dumps(context, ensure_ascii=False, indent=2)[:1000]}

可用工具: {tool_list[:20]}

请提供具体解决方案，返回JSON格式:
{{
    "solution_type": "retry|fix_params|use_alternative|skip|escalate",
    "solution_data": {{
        // retry: {{"wait_seconds": 1}}
        // fix_params: {{"fixed_params": {{"param1": "value1"}}}}
        // use_alternative: {{"alternative_tool": "tool_name", "params": {{}}}}
        // skip: {{"reason": "..."}}
        // escalate: {{"reason": "..."}}
    }},
    "reasoning": "为什么这样解决",
    "prevent_future": "如何预防此类错误"
}}"""

        try:
            response = await self.llm.chat(prompt)

            # 解析JSON
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            data = json.loads(response.strip())

            solution = Solution(
                solution_type=SolutionType(data.get("solution_type", "retry")),
                solution_data=data.get("solution_data", {}),
                reasoning=data.get("reasoning", ""),
                prevent_future=data.get("prevent_future", "")
            )

            return solution

        except Exception as e:
            logger.error(f"Failed to get LLM solution: {e}")
            return None

    async def _apply_solution(
        self,
        solution: Solution,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """应用解决方案"""
        solution.times_used += 1

        if solution.solution_type == SolutionType.RETRY:
            wait_seconds = solution.solution_data.get("wait_seconds", 1)
            logger.info(f"Retrying after {wait_seconds}s...")
            await asyncio.sleep(wait_seconds)
            return {"action": "retry", "context": context}

        elif solution.solution_type == SolutionType.FIX_PARAMS:
            fixed_params = solution.solution_data.get("fixed_params", {})
            context["params"] = {**context.get("params", {}), **fixed_params}
            return {"action": "retry_with_fixed_params", "context": context}

        elif solution.solution_type == SolutionType.USE_ALTERNATIVE:
            alt_tool = solution.solution_data.get("alternative_tool")
            alt_params = solution.solution_data.get("params", {})
            return {
                "action": "use_alternative",
                "tool": alt_tool,
                "params": {**context.get("params", {}), **alt_params}
            }

        elif solution.solution_type == SolutionType.SKIP:
            return {
                "action": "skip",
                "reason": solution.solution_data.get("reason", "Skipped by solution")
            }

        else:
            return {"action": "cannot_resolve"}

    async def _record_solution_result(
        self,
        solution: Solution,
        success: bool
    ):
        """记录解决方案应用结果"""
        if success:
            solution.times_succeeded += 1

        # 更新成功率
        if solution.times_used > 0:
            solution.success_rate = solution.times_succeeded / solution.times_used

    async def _record_experience(
        self,
        error_type: ErrorType,
        error_msg: str,
        solution: Solution,
        context: Dict[str, Any]
    ):
        """记录经验到经验库"""
        # 更新缓存
        error_key = self._get_error_key(error_msg, context)
        self._solutions_cache[error_key] = solution

        # 记录到数据库
        if self.experience_db:
            try:
                experience = {
                    "type": "error_solution",
                    "error_type": error_type.value,
                    "error_message": error_msg[:500],
                    "solution_type": solution.solution_type.value,
                    "solution_data": solution.solution_data,
                    "reasoning": solution.reasoning,
                    "prevent_future": solution.prevent_future,
                    "tool_name": context.get("tool_name"),
                    "timestamp": datetime.now().timestamp()
                }
                await self.experience_db.add(experience)
                logger.info(f"Recorded error experience: {error_type.value}")
            except Exception as e:
                logger.warning(f"Failed to record experience: {e}")


class AgentWithSelfHealing:
    """集成错误驱动学习的Agent执行器"""

    def __init__(self, llm_manager, experience_db=None):
        self.llm = llm_manager
        self.error_learning = ErrorDrivenLearning(llm_manager, experience_db)

    async def execute_with_self_healing(
        self,
        executor: Callable,
        tool_name: str,
        params: Dict[str, Any],
        tool_registry: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        带自愈的执行

        Args:
            executor: 执行函数
            tool_name: 工具名
            params: 参数
            tool_registry: 工具注册表

        Returns:
            执行结果
        """
        context = {
            "tool_name": tool_name,
            "params": params,
            "attempt": 0
        }

        last_error = None

        while context["attempt"] < self.error_learning.max_retries:
            context["attempt"] += 1

            try:
                # 尝试执行
                result = await executor(tool_name, params)
                logger.info(f"Execution succeeded on attempt {context['attempt']}")
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Execution failed (attempt {context['attempt']}): {e}")

                # 处理错误
                solution = await self.error_learning.handle_error(e, context, tool_registry)

                action = solution.get("action")

                if action == "retry":
                    continue

                elif action == "retry_with_fixed_params":
                    params = solution["context"].get("params", params)
                    continue

                elif action == "use_alternative":
                    tool_name = solution["tool"]
                    params = solution["params"]
                    continue

                elif action == "skip":
                    return {"skipped": True, "reason": solution.get("reason")}

                else:
                    # 无法解决
                    break

        # 达到最大重试次数
        raise last_error or Exception(f"Max attempts reached for {tool_name}")

    async def execute_tool_with_fallback(
        self,
        tool_name: str,
        primary_executor: Callable,
        fallback_executors: List[Callable],
        params: Dict[str, Any]
    ) -> Any:
        """使用回退执行器执行"""
        # 尝试主执行器
        try:
            return await primary_executor(tool_name, params)
        except Exception as e:
            logger.warning(f"Primary executor failed: {e}")

            # 尝试回退执行器
            for i, fallback in enumerate(fallback_executors):
                try:
                    logger.info(f"Trying fallback executor {i+1}...")
                    return await fallback(tool_name, params)
                except Exception as fallback_error:
                    logger.warning(f"Fallback executor {i+1} failed: {fallback_error}")
                    continue

            # 全部失败
            raise e
