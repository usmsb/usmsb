"""
后台任务处理器

设计初衷：
============

1. background_task() 的原始问题：
   - 之前：后台任务会重新调用 _chat_with_llm()，导致已执行的工具被重复执行
   - 现在：后台任务接收 ChatResult 作为输入，知道哪些工具已经执行过

2. 两种后台处理场景：

   场景 A - 工具参数错误重试 (tool_retry)：
   - 原因：工具调用时参数值不正确（如 API Key 错误、缺少必要参数）
   - 处理：从历史记录中找到正确参数 → 修正参数 → 只重新执行失败的工具
   - 注意：不是重新执行所有工具，只重试失败的那个

   场景 B - 任务继续处理 (continuation)：
   - 原因：LLM 返回"正在处理中"但实际上后续没有继续
   - 处理：传入"继续处理"的提示，让 LLM 完成任务
   - 注意：不重新执行工具，只是让 LLM 基于已有结果生成回复

3. 核心原则：
   - 后台任务是"延续/补救"，不是"重新开始"
   - 避免重复执行已成功的工具
   - 只在必要时调用 LLM

使用方式：
==========

    # 在 chat() 方法中
    chat_result = await self._chat_with_llm(...)

    if chat_result.needs_background:
        processor = BackgroundTaskProcessor(self)

        if chat_result.needs_tool_retry:
            await processor.handle_tool_retry(...)
        else:
            await processor.handle_continuation(...)
"""

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..models.chat_result import (
    BackgroundTaskContext,
    ChatResult,
    ToolRetryInfo,
)
from ..memory.conversation import MessageRole

if TYPE_CHECKING:
    from ..agent import MetaAgent

logger = logging.getLogger(__name__)


class BackgroundTaskProcessor:
    """
    后台任务处理器

    职责：处理第一次 _chat_with_llm() 调用后未完成的任务
    原则：延续/补救，不重复执行
    """

    def __init__(self, agent: "MetaAgent"):
        self.agent = agent

    async def process(
        self,
        conversation_id: str,
        owner_id: str,
        chat_result: ChatResult,
        messages: List[Dict[str, str]],
        user_session,
        wallet_address: Optional[str] = None,
    ) -> None:
        """
        处理后台任务的主入口

        根据 chat_result 的状态决定处理方式：
        1. needs_tool_retry=True → 工具参数错误重试
        2. needs_continuation=True → 任务继续处理
        3. 其他 → 默认继续处理

        Args:
            conversation_id: 会话 ID
            owner_id: 用户 ID
            chat_result: 第一次 LLM 调用的结果
            messages: 对话消息列表
            user_session: 用户会话对象
            wallet_address: 用户钱包地址
        """
        logger.info(f"[BACKGROUND] Starting background task for conversation {conversation_id}")
        logger.info(f"[BACKGROUND] Task status: retry={chat_result.needs_tool_retry}, continuation={chat_result.needs_continuation}")
        logger.info(f"[BACKGROUND] Already executed tools: {chat_result.executed_tools}")

        try:
            # 添加开始日志
            await self._add_background_log(
                conversation_id=conversation_id,
                content=self.agent.chat_config.background_task_start_message,
            )

            result_text = ""

            # 根据处理类型分发
            if chat_result.needs_tool_retry:
                # 场景 A：工具参数错误，需要修正后重试
                result_text = await self._handle_tool_retry(
                    conversation_id=conversation_id,
                    owner_id=owner_id,
                    chat_result=chat_result,
                    messages=messages,
                    user_session=user_session,
                )

            elif chat_result.needs_continuation:
                # 场景 B：LLM 匆忙结束，需要继续处理
                result_text = await self._handle_continuation(
                    conversation_id=conversation_id,
                    chat_result=chat_result,
                    messages=messages,
                    user_session=user_session,
                )

            else:
                # 默认：尝试继续处理
                result_text = await self._handle_continuation(
                    conversation_id=conversation_id,
                    chat_result=chat_result,
                    messages=messages,
                    user_session=user_session,
                )

            # 保存结果
            if result_text:
                await self._add_background_complete(conversation_id, result_text)
                logger.info(f"[BACKGROUND] Task completed for conversation {conversation_id}")
            else:
                await self._add_background_error(
                    conversation_id,
                    "任务处理完成，但没有生成有效结果。",
                )

        except Exception as e:
            logger.error(f"[BACKGROUND] Task failed: {e}", exc_info=True)
            await self._add_background_error(
                conversation_id,
                f"后台任务执行失败：{str(e)}",
            )

    # ==================== 场景 A：工具参数错误重试 ====================

    async def _handle_tool_retry(
        self,
        conversation_id: str,
        owner_id: str,
        chat_result: ChatResult,
        messages: List[Dict[str, str]],
        user_session,
    ) -> str:
        """
        处理工具参数错误的重试

        设计初衷：
        - 工具调用失败是因为参数值不正确（如 API Key 错误、缺少必要参数）
        - 用户可能在历史对话中提供过正确的参数值
        - 从历史记录中找到正确参数 → 修正参数 → 只重新执行失败的工具

        注意：
        - 不是重新执行所有工具
        - 不是重新调用整个 _chat_with_llm()
        - 只重试失败的那个工具

        Args:
            conversation_id: 会话 ID
            owner_id: 用户 ID（用于搜索历史记录）
            chat_result: 第一次调用的结果，包含重试信息
            messages: 对话消息列表
            user_session: 用户会话对象

        Returns:
            最终回复文本
        """
        max_retries = 3
        retry_info = chat_result.retry_info

        if not retry_info:
            return "无法获取重试信息，请重新描述您的需求。"

        tool_name = retry_info.get("tool_name", "")
        original_args = retry_info.get("original_args", {})
        missing_param = retry_info.get("param_name", "")
        info_type = retry_info.get("info_type", "other")
        description = retry_info.get("description", "")

        logger.info(f"[TOOL_RETRY] Retrying tool: {tool_name}, missing param: {missing_param}")

        for attempt in range(max_retries):
            logger.info(f"[TOOL_RETRY] Attempt {attempt + 1}/{max_retries}")

            # Step 1: 从历史记录中提取正确的参数值
            extracted_value = await self._extract_correct_param(
                owner_id=owner_id,
                param_name=missing_param,
                info_type=info_type,
                description=description,
            )

            if not extracted_value:
                # 找不到正确参数，询问用户
                return f"需要更多信息：{description}\n\n请在对话中提供正确的{missing_param or '参数'}。"

            # Step 2: 修正参数
            fixed_args = dict(original_args)
            fixed_args[missing_param] = extracted_value

            logger.info(f"[TOOL_RETRY] Fixed args for {missing_param}: {extracted_value[:20]}...")

            # Step 3: 只重新执行失败的工具（不是所有工具！）
            tool_result = await self.agent._execute_tool(
                tool_name=tool_name,
                tool_args=fixed_args,
                user_session=user_session,
            )

            if tool_result.get("success"):
                logger.info(f"[TOOL_RETRY] Tool {tool_name} executed successfully")

                # Step 4: 工具执行成功，让 LLM 基于结果生成回复
                # 注意：这里不重新执行所有工具，只是让 LLM 处理成功的结果
                final_response = await self._generate_response_from_tool_result(
                    user_message=messages[-1].get("content", "") if messages else "",
                    tool_name=tool_name,
                    tool_result=tool_result,
                    previous_results=chat_result.tool_results,
                )
                return final_response

            # 仍然失败，检查是否需要更新重试信息
            error_msg = tool_result.get("result", {}).get("error", str(tool_result))
            logger.warning(f"[TOOL_RETRY] Tool still failed: {error_msg}")

            # 更新重试信息，可能需要其他参数
            new_retry_info = self._analyze_tool_failure(
                tool_name=tool_name,
                args=fixed_args,
                error=error_msg,
            )

            if new_retry_info:
                retry_info = new_retry_info
                missing_param = new_retry_info.get("param_name", "")
                description = new_retry_info.get("description", "")
            else:
                # 无法分析出新的缺失参数
                break

        return f"多次尝试后仍无法完成操作：{description}\n\n请确认您提供的信息是否正确。"

    async def _extract_correct_param(
        self,
        owner_id: str,
        param_name: str,
        info_type: str,
        description: str,
    ) -> Optional[str]:
        """
        从历史记录中提取正确的参数值

        Args:
            owner_id: 用户 ID
            param_name: 参数名
            info_type: 参数类型
            description: 参数描述

        Returns:
            提取到的参数值，如果找不到返回 None
        """
        if not self.agent.info_extractor:
            logger.warning("[EXTRACT] Info extractor not available")
            return None

        try:
            from ..info.types import InfoNeed, InfoNeedType

            # 转换 info_type
            try:
                need_type = InfoNeedType(info_type)
            except ValueError:
                need_type = InfoNeedType.OTHER

            need = InfoNeed(
                need_id=f"tool_retry_{param_name}",
                name=param_name or "未知参数",
                info_type=need_type,
                description=description,
            )

            logger.info(f"[EXTRACT] Extracting param: {param_name}, type: {info_type}")

            extracted = await self.agent.info_extractor.extract([need], owner_id)

            if extracted and need.need_id in extracted:
                value = extracted[need.need_id]
                logger.info(f"[EXTRACT] Found value for {param_name}: {str(value)[:30]}...")
                return value

            logger.warning(f"[EXTRACT] No value found for {param_name}")
            return None

        except Exception as e:
            logger.error(f"[EXTRACT] Failed to extract param: {e}")
            return None

    def _analyze_tool_failure(
        self,
        tool_name: str,
        args: Dict[str, Any],
        error: str,
    ) -> Optional[Dict[str, Any]]:
        """
        分析工具失败原因，提取重试信息

        Args:
            tool_name: 工具名称
            args: 调用参数
            error: 错误信息

        Returns:
            重试信息字典，如果无法分析则返回 None
        """
        error_lower = error.lower()

        # 常见错误模式检测
        patterns = {
            "api_key": ["api key", "apikey", "api_key", "unauthorized", "认证"],
            "password": ["password", "密码", "credential"],
            "token": ["token", "令牌", "bearer"],
            "url": ["url", "地址", "endpoint"],
            "param": ["missing", "required", "参数", "invalid"],
        }

        for param_type, keywords in patterns.items():
            for kw in keywords:
                if kw in error_lower:
                    return {
                        "tool_name": tool_name,
                        "original_args": args,
                        "param_name": param_type,
                        "info_type": "credential" if param_type in ["api_key", "password", "token"] else "param",
                        "description": f"需要正确的{param_type}",
                        "error_message": error,
                    }

        return None

    # ==================== 场景 B：任务继续处理 ====================

    async def _handle_continuation(
        self,
        conversation_id: str,
        chat_result: ChatResult,
        messages: List[Dict[str, str]],
        user_session,
    ) -> str:
        """
        处理 LLM 匆忙结束的情况

        设计初衷：
        - LLM 返回了"正在处理中"但实际上后续没有继续
        - LLM 返回的结果没有真正解决用户的问题

        处理方式：
        - 传入"继续处理"的提示
        - 让 LLM 基于已有的工具结果生成最终回复
        - 不重新执行工具！

        Args:
            conversation_id: 会话 ID
            chat_result: 第一次调用的结果
            messages: 对话消息列表
            user_session: 用户会话对象

        Returns:
            最终回复文本
        """
        logger.info("[CONTINUATION] Handling task continuation")

        # 检查是否有工具结果可用
        if not chat_result.tool_results:
            # 没有工具结果，直接让 LLM 重新回答
            return await self._simple_continuation(messages)

        # 有工具结果，让 LLM 基于结果生成回复
        return await self._continuation_with_results(
            messages=messages,
            tool_results=chat_result.tool_results,
            executed_tools=chat_result.executed_tools,
        )

    async def _simple_continuation(
        self,
        messages: List[Dict[str, str]],
    ) -> str:
        """
        简单继续处理：没有工具结果时的处理

        只让 LLM 继续生成回复，不执行工具
        """
        user_message = messages[-1].get("content", "") if messages else ""

        continuation_prompt = f"""请继续完成用户的请求，直接给出最终结果。

用户请求：{user_message}

注意：
1. 不要说"正在处理中"或"请稍后"
2. 直接给出完整的答案
3. 如果确实无法完成，请说明原因并询问用户需要什么信息
"""

        try:
            response = await self.agent.llm_manager.chat(continuation_prompt)
            return response
        except Exception as e:
            logger.error(f"[CONTINUATION] Simple continuation failed: {e}")
            return "抱歉，处理您的请求时遇到了问题。请稍后重试或提供更多信息。"

    async def _continuation_with_results(
        self,
        messages: List[Dict[str, str]],
        tool_results: List[Dict[str, Any]],
        executed_tools: List[str],
    ) -> str:
        """
        基于工具结果继续处理

        让 LLM 基于已有的工具执行结果生成最终回复
        不重新执行工具
        """
        user_message = messages[-1].get("content", "") if messages else ""

        # 格式化工具结果
        results_text = self._format_tool_results_for_llm(tool_results)

        continuation_prompt = f"""请基于工具执行结果，完成用户的请求。

用户请求：{user_message}

已执行的工具：{', '.join(executed_tools)}

工具执行结果：
{results_text}

请直接给出最终答案，不要说"正在处理中"。
"""

        try:
            response = await self.agent.llm_manager.chat(continuation_prompt)
            return response
        except Exception as e:
            logger.error(f"[CONTINUATION] Continuation with results failed: {e}")
            # 降级：直接返回工具结果的摘要
            return f"操作已完成。执行了以下工具：{', '.join(executed_tools)}\n\n结果：{results_text[:500]}..."

    def _format_tool_results_for_llm(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        """格式化工具结果给 LLM"""
        parts = []
        for result in tool_results:
            tool_name = result.get("tool", "unknown")
            success = result.get("success", False)
            result_data = result.get("result", {})

            if success:
                parts.append(f"【{tool_name}】执行成功")
                if isinstance(result_data, dict):
                    # 格式化字典结果
                    for k, v in result_data.items():
                        v_str = str(v)[:200] if v else "无"
                        parts.append(f"  - {k}: {v_str}")
                else:
                    parts.append(f"  结果: {str(result_data)[:300]}")
            else:
                error = result_data.get("error", "未知错误") if isinstance(result_data, dict) else str(result_data)
                parts.append(f"【{tool_name}】执行失败: {error}")

        return "\n".join(parts)

    async def _generate_response_from_tool_result(
        self,
        user_message: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        previous_results: List[Dict[str, Any]],
    ) -> str:
        """
        基于工具执行成功的结果生成最终回复

        Args:
            user_message: 用户原始消息
            tool_name: 成功执行的工具名称
            tool_result: 工具执行结果
            previous_results: 之前的工具结果

        Returns:
            最终回复文本
        """
        result_data = tool_result.get("result", {})

        # 格式化结果
        if isinstance(result_data, dict):
            result_text = json.dumps(result_data, ensure_ascii=False, indent=2)[:2000]
        else:
            result_text = str(result_data)[:2000]

        prompt = f"""请根据工具执行结果，回答用户的问题。

用户问题：{user_message}

执行的工具有效，结果如下：
{result_text}

请用自然语言回答用户的问题，不要提及"工具"、"执行"等技术细节。
"""

        try:
            response = await self.agent.llm_manager.chat(prompt)
            return response
        except Exception as e:
            logger.error(f"[GENERATE] Failed to generate response: {e}")
            return f"操作已成功完成。结果：{result_text[:500]}"

    # ==================== 辅助方法 ====================

    async def _add_background_log(
        self,
        conversation_id: str,
        content: str,
        tool_calls: Optional[List] = None,
    ) -> None:
        """添加后台任务日志消息"""
        try:
            await self.agent.conversation_manager.add_message(
                conversation_id=conversation_id,
                role=MessageRole.BACKGROUND_TASK,
                content=content,
                tool_calls=tool_calls,
            )
        except Exception as e:
            logger.warning(f"Failed to add background log: {e}")

    async def _add_background_complete(
        self,
        conversation_id: str,
        content: str,
    ) -> None:
        """添加后台任务完成消息"""
        try:
            await self.agent.conversation_manager.add_message(
                conversation_id=conversation_id,
                role=MessageRole.BACKGROUND_COMPLETE,
                content=self.agent.chat_config.background_task_complete_template.format(result=content),
            )
        except Exception as e:
            logger.warning(f"Failed to add background complete: {e}")

    async def _add_background_error(
        self,
        conversation_id: str,
        error: str,
    ) -> None:
        """添加后台任务错误消息"""
        try:
            await self.agent.conversation_manager.add_message(
                conversation_id=conversation_id,
                role=MessageRole.BACKGROUND_ERROR,
                content=self.agent.chat_config.background_task_error_template.format(error=error),
            )
        except Exception as e:
            logger.warning(f"Failed to add background error: {e}")
