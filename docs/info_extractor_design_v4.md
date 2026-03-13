# Information Extractor Refactoring Design v4

**[English](#information-extractor-refactoring-design-v4) | [中文](#信息提取器重构设计方案-v4)**

---

## Core Concept

**Fully decided by LLM, no hardcoded trigger conditions:**

1. **LLM judges whether to retry** - After task execution, let LLM judge if result is successful
2. **LLM decides what's needed** - No preset info_type, format_hint, etc.
3. **Retry during tool execution** - When tool call fails, immediately let LLM judge
4. **Two trigger methods** - Tool actively calls + background task detection

---

## Core Changes

### 1. max_tokens adjustment

```python
# Original
max_tokens=2000

# Modified
max_tokens=80000  # or larger
```

### 2. Remove InfoAvailabilityChecker

**Reason**:
- Hardcoded specific formats (like xialiao_, github.com)
- At this point, LLM/tool hasn't been executed, cannot truly verify if information is valid

---

## Complete Background Task Execution Flow

```python
# File: agent.py - Complete background task

async def background_task():
    """
    Background task execution flow

    1. LLM judges next step (needs tool or direct return)
    2. Execute tool call
    3. After tool call → LLM judges if retry needed
    4. After LLM returns → LLM judges if retry needed
    5. If info needed → InfoExtractor extracts → retry
    """

    max_retries = 3
    current_messages = messages

    for attempt in range(max_retries):
        # ========== Step 1: LLM call ==========
        llm_response = await self._chat_with_llm(
            current_messages,
            tools=tools_schema,
            skills=skills_schema,
            conversation_id=str(conversation.id),
            user_session=user_session,
        )

        # ========== Step 2: Judge after LLM returns ==========
        # Let LLM judge if return result needs retry
        llm_retry_decision = await self._llm_judge_response_retry(
            response=llm_response,
            attempt=attempt,
            max_retries=max_retries
        )

        if not llm_retry_decision.get("need_retry"):
            # LLM says no retry needed, complete
            result_text = llm_response
            break

        # ========== Step 3: If need to supplement info ==========
        if llm_retry_decision.get("need_info"):
            info_description = llm_retry_decision.get("info_description", "")

            need = InfoNeed(
                need_id=f"llm_retry_{attempt}",
                name=info_description,
                description=info_description,
                info_type=llm_retry_decision.get("info_type", "other"),
                format_hint=llm_retry_decision.get("format_hint", "")
            )

            extracted = await self.info_extractor.extract([need], owner_id)

            if extracted and need.need_id in extracted:
                # Inject extracted info, retry
                current_messages = self._inject_extracted_info(
                    current_messages, need.name, extracted[need.need_id]
                )
                continue  # Continue loop

        # ========== Step 4: Parse tool calls ==========
        tool_calls = self._parse_tool_calls(llm_response)

        if not tool_calls:
            # No tool call needed, continue loop
            current_messages = self._add_response_to_messages(current_messages, llm_response)
            continue

        # ========== Step 5: Execute tool calls ==========
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            tool_result = await self._execute_tool(
                tool_name,
                tool_args,
                user_session
            )

            tool_results.append({
                "tool": tool_name,
                "result": tool_result,
                "success": tool_result.get("success", False)
            })

        # ========== Step 6: Judge after tool call ==========
        # Let LLM judge if tool execution result needs retry
        tool_retry_decision = await self._llm_judge_tool_retry(
            tool_results=tool_results,
            attempt=attempt,
            max_retries=max_retries
        )

        if not tool_retry_decision.get("need_retry"):
            # LLM says no retry needed
            result_text = self._format_tool_results(tool_results)
            break

        # ========== Step 7: If tool call needs to supplement info ==========
        if tool_retry_decision.get("need_info"):
            info_description = tool_retry_decision.get("info_description", "")

            need = InfoNeed(
                need_id=f"tool_retry_{attempt}",
                name=info_description,
                description=info_description,
                info_type=tool_retry_decision.get("info_type", "other"),
                format_hint=tool_retry_decision.get("format_hint", "")
            )

            extracted = await self.info_extractor.extract([need], owner_id)

            if extracted and need.need_id in extracted:
                # Info extracted, fix params and retry
                fixed_tool_args = self._fix_tool_args(
                    tool_args,
                    need.name,
                    extracted[need.need_id]
                )

                # Retry tool call
                tool_result = await self._execute_tool(
                    tool_name,
                    fixed_tool_args,
                    user_session
                )

                tool_results = [{"tool": tool_name, "result": tool_result}]

        # ========== Step 8: Add tool results to context ==========
        current_messages = self._add_tool_results_to_messages(
            current_messages,
            llm_response,
            tool_results
        )

        # Continue loop, let LLM handle

    # Return final result
    result_text = await self._chat_with_llm(
        current_messages,
        tools=[],
        skills=[],
        conversation_id=str(conversation.id),
        user_session=user_session,
    )
```

---

## Two LLM Judgment Methods

### 1. Judge after LLM returns

```python
async def _llm_judge_response_retry(
    self,
    response: str,
    attempt: int,
    max_retries: int
) -> Dict:
    """
    After LLM call returns, let LLM judge if retry is needed
    """

    prompt = f"""Judge whether current response needs retry.

Current attempt: {attempt + 1}/{max_retries}

LLM response:
{response[:3000]}

Please return JSON:
{{
    "need_retry": true/false,
    "reason": "judgment reason",
    "need_info": true/false,
    "info_description": "what info is needed",
    "info_type": "credential/param/url/other",
    "format_hint": "format hint (optional)"
}}

Note: Judge purely based on actual response, do not preset any conditions.
"""

    response = await self.llm_manager.chat(prompt)
    # Parse JSON ...
    return data
```

### 2. Judge after tool call

```python
async def _llm_judge_tool_retry(
    self,
    tool_results: List[Dict],
    attempt: int,
    max_retries: int
) -> Dict:
    """
    After tool call, let LLM judge if retry is needed
    """

    prompt = f"""Judge whether tool execution result needs retry.

Current attempt: {attempt + 1}/{max_retries}

Tool execution result:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

Please return JSON:
{{
    "need_retry": true/false,
    "reason": "judgment reason",
    "need_info": true/false,
    "info_description": "what info is needed",
    "info_type": "credential/param/url/other",
    "format_hint": "format hint (optional)"
}}

Note: Judge purely based on actual tool execution result, do not preset any conditions.
"""

    response = await self.llm_manager.chat(prompt)
    # Parse JSON ...
    return data
```

---

## LLM Judgment Method

```python
async def _llm_judge_tool_retry(
    self,
    tool_results: List[Dict],
    attempt: int,
    max_retries: int
) -> Dict:
    """
    Let LLM judge if retry is needed after tool execution failure

    Fully decided by LLM, no preset conditions
    """

    prompt = f"""Judge if retry is needed after tool execution failure.

Current attempt: {attempt + 1}/{max_retries}

Tool execution result:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

Please return JSON:
{{
    "need_retry": true/false,
    "reason": "judgment reason",
    "need_info": true/false,
    "info_description": "what info is needed (e.g., API Key, param value, account, etc.)",
    "info_type": "credential/param/url/other",
    "format_hint": "format hint (optional)"
}}

Note:
- need_retry: After tool execution failure, whether retry is needed
- need_info: Whether need to extract info from user historical conversation to fix failure
- Judge purely based on actual tool execution result, do not preset any conditions
"""

    response = await self.llm_manager.chat(prompt)
    # Parse JSON ...
    return data
```

---

## Key Flowchart

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Background Task Execution Flow                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ LLM judges next step │ ← Judge what tool needed/direct return  │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │ Execute tool │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│   Tool execution successful?                                          │
│      │                                                              │
│      ├──────────┐                                                   │
│      │          │                                                   │
│     Yes         No                                                  │
│      │          │                                                   │
│      ▼          ▼                                                   │
│  ┌────────┐  ┌────────────────────┐                                 │
│  │Continue│  │LLM judges if retry │                                 │
│  │  loop │  └─────────┬──────────┘                                 │
│  └────────┘                        │                                 │
│                             need_retry?                              │
│                               │        │                              │
│                              Yes       No                            │
│                               │        │                              │
│                               ▼        ▼                             │
│                  ┌──────────────────┐                                │
│                  │ need_info?       │                                │
│                  └────────┬─────────┘                                │
│                           │                                          │
│                      Yes    │ No                                    │
│                       │     │                                       │
│                       ▼     ▼                                       │
│            ┌─────────────────┐  ┌─────────────────┐              │
│            │ Call InfoExtractor │  │Retry tool call  │              │
│            │ Extract info     │  │   directly      │              │
│            └────────┬────────┘  └─────────────────┘                   │
│                      │                                              │
│                      ▼                                              │
│            ┌─────────────────┐                                     │
│            │ Fix params and  │                                     │
│            │ retry tool call │                                     │
│            └────────┬────────┘                                     │
│                      │                                              │
│                      └───────────────────────→ Continue loop        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Two Trigger Methods

### Method 1: Register as Tool

```python
# Register to ToolRegistry
{
    "name": "retrieve_user_info",
    "description": "Extract needed info from user historical conversation"
}
```

### Method 2: Background task auto-trigger

- After tool execution fails
- When LLM judges retry needed and info needed
- Automatically call InfoExtractor

---

## Simplified File Structure

```
info/
├── types.py              # Data types (InfoNeed, RetrievalIntent, etc.)
├── extractor.py          # InfoExtractor (extract from historical messages)
├── intent_analyzer.py    # IntentAnalyzer
├── candidate_search.py   # CandidateSearch (full-text search)
├── llm_extractor.py     # LLMExtractor (extract item by item)
├── validator.py          # Validator
└── tool_wrapper.py      # Tool wrapper
```

---

## Summary

Is this understanding correct? Core is:

1. **Detect failure during tool execution**
2. **LLM judges if retry needed**
3. **Need info** → InfoExtractor extracts → Fix params → Retry tool
4. **No need info** → Retry tool directly

<details>
<summary><h2>中文翻译</h2></summary>

# 信息提取器重构设计方案 v4

## 核心思路

**完全由 LLM 决定，不写死任何触发条件：**

1. **LLM 判断是否需要重试** - 任务执行后让 LLM 判断结果是否成功
2. **LLM 决定需要什么** - 不预设 info_type、format_hint 等
3. **工具执行过程中重试** - 工具调用失败时立即让 LLM 判断
4. **两种触发方式** - Tool 主动调用 + 后台任务检测

---

## 核心改动

### 1. max_tokens 调整

```python
# 原有
max_tokens=2000

# 修改后
max_tokens=80000  # 或更大
```

### 2. 移除 InfoAvailabilityChecker

**原因**：
- 写死了特定格式（如 xialiao_, github.com）
- 这时没有执行 LLM/tool，无法真正验证信息是否有效

---

## 完整的后台任务执行流程

```python
# 文件: agent.py - 完整的后台任务

async def background_task():
    """
    后台任务执行流程

    1. LLM 判断下一步（需要工具还是直接返回）
    2. 执行工具调用
    3. 工具调用后 → LLM 判断是否需要重试
    4. LLM 返回后 → LLM 判断是否需要重试
    5. 如果需要信息 → InfoExtractor 提取 → 重试
    """

    max_retries = 3
    current_messages = messages

    for attempt in range(max_retries):
        # ========== Step 1: LLM 调用 ==========
        llm_response = await self._chat_with_llm(
            current_messages,
            tools=tools_schema,
            skills=skills_schema,
            conversation_id=str(conversation.id),
            user_session=user_session,
        )

        # ========== Step 2: LLM 返回后判断 ==========
        # 让 LLM 判断返回结果是否需要重试
        llm_retry_decision = await self._llm_judge_response_retry(
            response=llm_response,
            attempt=attempt,
            max_retries=max_retries
        )

        if not llm_retry_decision.get("need_retry"):
            # LLM 说不需要重试，完成
            result_text = llm_response
            break

        # ========== Step 3: 如果需要补充信息 ==========
        if llm_retry_decision.get("need_info"):
            info_description = llm_retry_decision.get("info_description", "")

            need = InfoNeed(
                need_id=f"llm_retry_{attempt}",
                name=info_description,
                description=info_description,
                info_type=llm_retry_decision.get("info_type", "other"),
                format_hint=llm_retry_decision.get("format_hint", "")
            )

            extracted = await self.info_extractor.extract([need], owner_id)

            if extracted and need.need_id in extracted:
                # 注入提取到的信息，重试
                current_messages = self._inject_extracted_info(
                    current_messages, need.name, extracted[need.need_id]
                )
                continue  # 继续循环

        # ========== Step 4: 解析工具调用 ==========
        tool_calls = self._parse_tool_calls(llm_response)

        if not tool_calls:
            # 不需要工具调用，直接继续循环
            current_messages = self._add_response_to_messages(current_messages, llm_response)
            continue

        # ========== Step 5: 执行工具调用 ==========
        tool_results = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            tool_result = await self._execute_tool(
                tool_name,
                tool_args,
                user_session
            )

            tool_results.append({
                "tool": tool_name,
                "result": tool_result,
                "success": tool_result.get("success", False)
            })

        # ========== Step 6: 工具调用后判断 ==========
        # 让 LLM 判断工具执行结果是否需要重试
        tool_retry_decision = await self._llm_judge_tool_retry(
            tool_results=tool_results,
            attempt=attempt,
            max_retries=max_retries
        )

        if not tool_retry_decision.get("need_retry"):
            # LLM 说不需要重试
            result_text = self._format_tool_results(tool_results)
            break

        # ========== Step 7: 如果工具调用需要补充信息 ==========
        if tool_retry_decision.get("need_info"):
            info_description = tool_retry_decision.get("info_description", "")

            need = InfoNeed(
                need_id=f"tool_retry_{attempt}",
                name=info_description,
                description=info_description,
                info_type=tool_retry_decision.get("info_type", "other"),
                format_hint=tool_retry_decision.get("format_hint", "")
            )

            extracted = await self.info_extractor.extract([need], owner_id)

            if extracted and need.need_id in extracted:
                # 提取到信息，修复参数后重试
                fixed_tool_args = self._fix_tool_args(
                    tool_args,
                    need.name,
                    extracted[need.need_id]
                )

                # 重试工具调用
                tool_result = await self._execute_tool(
                    tool_name,
                    fixed_tool_args,
                    user_session
                )

                tool_results = [{"tool": tool_name, "result": tool_result}]

        # ========== Step 8: 将工具结果加入上下文 ==========
        current_messages = self._add_tool_results_to_messages(
            current_messages,
            llm_response,
            tool_results
        )

        # 继续循环，让 LLM 处理

    # 返回最终结果
    result_text = await self._chat_with_llm(
        current_messages,
        tools=[],
        skills=[],
        conversation_id=str(conversation.id),
        user_session=user_session,
    )
```

---

## 两个 LLM 判断方法

### 1. LLM 返回后判断

```python
async def _llm_judge_response_retry(
    self,
    response: str,
    attempt: int,
    max_retries: int
) -> Dict:
    """
    LLM 调用返回后，让 LLM 判断是否需要重试
    """

    prompt = f"""判断当前响应是否需要重试。

当前尝试: {attempt + 1}/{max_retries}

LLM 响应:
{response[:3000]}

请返回JSON:
{{
    "need_retry": true/false,
    "reason": "判断理由",
    "need_info": true/false,
    "info_description": "需要什么信息",
    "info_type": "credential/param/url/other",
    "format_hint": "格式提示（可选）"
}}

注意：完全根据实际响应判断，不要预设任何条件。
"""

    response = await self.llm_manager.chat(prompt)
    # 解析 JSON ...
    return data
```

### 2. 工具调用后判断

```python
async def _llm_judge_tool_retry(
    self,
    tool_results: List[Dict],
    attempt: int,
    max_retries: int
) -> Dict:
    """
    工具调用后，让 LLM 判断是否需要重试
    """

    prompt = f"""判断工具执行结果是否需要重试。

当前尝试: {attempt + 1}/{max_retries}

工具执行结果:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

请返回JSON:
{{
    "need_retry": true/false,
    "reason": "判断理由",
    "need_info": true/false,
    "info_description": "需要什么信息",
    "info_type": "credential/param/url/other",
    "format_hint": "格式提示（可选）"
}}

注意：完全根据实际工具执行结果判断，不要预设任何条件。
"""

    response = await self.llm_manager.chat(prompt)
    # 解析 JSON ...
    return data
```

---

## LLM 判断方法

```python
async def _llm_judge_tool_retry(
    self,
    tool_results: List[Dict],
    attempt: int,
    max_retries: int
) -> Dict:
    """
    让 LLM 判断工具执行失败后是否需要重试

    完全由 LLM 判断，不预设任何条件
    """

    prompt = f"""判断工具执行失败后是否需要重试。

当前尝试: {attempt + 1}/{max_retries}

工具执行结果:
{json.dumps(tool_results, ensure_ascii=False, indent=2)}

请返回JSON:
{{
    "need_retry": true/false,
    "reason": "判断理由",
    "need_info": true/false,
    "info_description": "需要什么信息（如：API Key、参数值、账号等）",
    "info_type": "credential/param/url/other",
    "format_hint": "格式提示（可选）"
}}

注意：
- need_retry: 工具执行失败后，是否需要重试
- need_info: 是否需要从用户历史对话中提取信息来修复失败
- 完全根据实际工具执行结果判断，不要预设任何条件
"""

    response = await self.llm_manager.chat(prompt)
    # 解析 JSON ...
    return data
```

---

## 关键流程图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    后台任务执行流程                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ LLM 判断下一步 │ ← 判断需要什么工具/直接返回                      │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │  执行工具    │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│   工具执行成功?                                                      │
│      │                                                              │
│      ├──────────┐                                                   │
│      │          │                                                   │
│     Yes         No                                                  │
│      │          │                                                   │
│      ▼          ▼                                                   │
│  ┌────────┐  ┌────────────────────┐                                 │
│  │继续循环│  │ LLM判断是否需要重试  │                                 │
│  └────────┘  └─────────┬──────────┘                                 │
│                        │                                             │
│                   need_retry?                                       │
│                     │        │                                      │
│                    Yes       No                                    │
│                     │        │                                      │
│                     ▼        ▼                                      │
│          ┌──────────────────┐                                       │
│          │ need_info?       │                                       │
│          └────────┬─────────┘                                       │
│                   │                                                 │
│              Yes    │ No                                           │
│               │     │                                              │
│               ▼     ▼                                              │
│     ┌─────────────────┐  ┌─────────────────┐                      │
│     │ 调用InfoExtractor │  │ 直接重试工具调用 │                      │
│     │ 提取补充信息      │  └─────────────────┘                      │
│     └────────┬────────┘                                            │
│              │                                                      │
│              ▼                                                      │
│     ┌─────────────────┐                                            │
│     │ 修复参数后重试   │                                            │
│     │   工具调用      │                                            │
│     └────────┬────────┘                                            │
│              │                                                      │
│              └───────────────────────→ 继续循环                    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 两种触发方式

### 方式一：作为 Tool 注册

```python
# 注册到 ToolRegistry
{
    "name": "retrieve_user_info",
    "description": "从用户历史对话中提取需要的信息"
}
```

### 方式二：后台任务自动触发

- 工具执行失败后
- LLM 判断需要重试且需要信息时
- 自动调用 InfoExtractor

---

## 简化后的文件结构

```
info/
├── types.py              # 数据类型 (InfoNeed, RetrievalIntent 等)
├── extractor.py          # InfoExtractor（从历史消息提取信息）
├── intent_analyzer.py    # IntentAnalyzer
├── candidate_search.py   # CandidateSearch（全文本搜索）
├── llm_extractor.py     # LLMExtractor（逐条提取）
├── validator.py          # Validator（验证）
└── tool_wrapper.py      # Tool 封装
```

---

## 这样理解对吗？核心是：

1. **工具执行过程中**就检测失败
2. **LLM 判断**是否需要重试
3. **需要信息** → InfoExtractor 提取 → 修复参数 → 重试工具
4. **不需要信息** → 直接重试

</details>
