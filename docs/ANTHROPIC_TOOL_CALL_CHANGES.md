# Anthropic API Tool Calling 修改说明

## 修改概述

修改了 `minimax_adapter.py` 和 `agent.py` 以正确支持 Anthropic API 格式的 function calling (tool_use/tool_result)。

## 关键修改

### 1. `minimax_adapter.py` - `chat_with_tools()` 方法

**修改前的问题：**
- 只提取 text 和 tool_calls，没有保留完整的 content blocks 结构
- 多轮对话时无法正确传递 assistant 消息

**修改后：**
```python
# 返回结构
{
    "content": "文本内容",
    "tool_calls": [{"id": "...", "function": {...}}],
    "raw_content_blocks": [  # 新增：用于多轮对话
        {"type": "text", "text": "..."},
        {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
    ],
    "stop_reason": "end_turn" | "tool_use" | ...
}
```

支持的 content block 类型：
- `text` - 文本内容
- `thinking` - 思维链（Extended Thinking）
- `tool_use` - 工具调用
- `redacted_thinking` - 脱敏的思考内容

### 2. `agent.py` - `_chat_with_llm()` 方法

**Anthropic API 格式（用于 MiniMax）：**

```python
# Assistant 消息（包含 tool_use）
{
    "role": "assistant",
    "content": [
        {"type": "text", "text": "让我帮您查询天气。"},
        {"type": "tool_use", "id": "toolu_001", "name": "get_weather", "input": {"city": "北京"}}
    ]
}

# User 消息（包含 tool_result）
{
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": "toolu_001", "content": "{\"temperature\": 25}"}
    ]
}
```

**OpenAI API 格式（保留原有逻辑）：**

```python
# Assistant 消息
{
    "role": "assistant",
    "content": "让我帮您查询天气。",
    "tool_calls": [{"id": "call_001", "function": {"name": "get_weather", "arguments": "..."}}]
}

# Tool 消息
{
    "role": "tool",
    "tool_call_id": "call_001",
    "content": "{\"temperature\": 25}"
}
```

## 测试方法

### 方法 1：运行单元测试
```bash
cd usmsb-sdk
python tests/test_anthropic_format.py
```

### 方法 2：启动服务器并通过 API 测试
```bash
cd usmsb-sdk
python -m uvicorn usmsb_sdk.api.rest.main:app --reload --port 8000
```

然后发送测试请求：
```bash
curl -X POST http://localhost:8000/meta-agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "请查询系统状态", "wallet_address": "test_wallet"}'
```

### 方法 3：运行完整集成测试
```bash
cd usmsb-sdk
python tests/test_chat_tool_call.py
```

## 注意事项

1. **多轮对话连续性**：在多轮 Function Call 对话中，完整的 assistant 消息（包含所有 content blocks）必须被添加到对话历史，以保持思维链的连续性。

2. **tool_use_id 匹配**：`tool_result` 的 `tool_use_id` 必须与对应的 `tool_use` 的 `id` 匹配。

3. **消息格式**：
   - Anthropic 格式：content 是列表，包含多个 block
   - OpenAI 格式：content 是字符串，tool_calls 是单独字段

## 参考资料

- [Anthropic API - Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- [Anthropic API - Messages](https://docs.anthropic.com/claude/reference/messages)
