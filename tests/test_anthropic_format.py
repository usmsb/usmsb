"""
Test Anthropic API Format
测试 Anthropic API 格式的消息构建是否正确
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json


def test_message_format_conversion():
    """测试消息格式转换是否正确"""

    print("\n" + "="*60)
    print("Test: Anthropic message format conversion")
    print("="*60)

    # 模拟 LLM 响应
    llm_response = {
        "content": "我来帮您查询天气。",
        "tool_calls": [
            {
                "id": "toolu_01234",
                "function": {
                    "name": "get_weather",
                    "arguments": {"city": "北京"}
                }
            }
        ],
        "raw_content_blocks": [
            {"type": "text", "text": "我来帮您查询天气。"},
            {
                "type": "tool_use",
                "id": "toolu_01234",
                "name": "get_weather",
                "input": {"city": "北京"}
            }
        ]
    }

    # 模拟工具执行结果
    tool_results = [
        {
            "tool": "get_weather",
            "result": {"temperature": 25, "condition": "晴天"},
            "success": True
        }
    ]

    tool_calls = llm_response.get("tool_calls", [])

    # 构建 assistant 消息（Anthropic 格式）
    raw_content_blocks = llm_response.get("raw_content_blocks", [])

    assistant_message = {
        "role": "assistant",
        "content": raw_content_blocks,
    }

    # 构建 tool_result blocks
    tool_result_blocks = []
    for tool_result in tool_results:
        tool_call_id = None
        for tc in tool_calls:
            if tc["function"]["name"] == tool_result.get("tool"):
                tool_call_id = tc["id"]
                break

        tool_result_blocks.append({
            "type": "tool_result",
            "tool_use_id": tool_call_id,
            "content": json.dumps(tool_result, ensure_ascii=False),
        })

    user_message = {
        "role": "user",
        "content": tool_result_blocks,
    }

    # 打印结果
    print("\n1. Assistant message (with tool_use):")
    print(json.dumps(assistant_message, indent=2, ensure_ascii=False))

    print("\n2. User message (with tool_result):")
    print(json.dumps(user_message, indent=2, ensure_ascii=False))

    # 验证格式
    assert assistant_message["role"] == "assistant"
    assert isinstance(assistant_message["content"], list)
    assert len(assistant_message["content"]) == 2
    assert assistant_message["content"][0]["type"] == "text"
    assert assistant_message["content"][1]["type"] == "tool_use"
    assert assistant_message["content"][1]["id"] == "toolu_01234"

    assert user_message["role"] == "user"
    assert isinstance(user_message["content"], list)
    assert len(user_message["content"]) == 1
    assert user_message["content"][0]["type"] == "tool_result"
    assert user_message["content"][0]["tool_use_id"] == "toolu_01234"

    print("\n✓ All assertions passed!")
    print("\nTest PASSED!")


def test_openai_format():
    """测试 OpenAI 格式的消息构建"""

    print("\n" + "="*60)
    print("Test: OpenAI message format")
    print("="*60)

    # 模拟 LLM 响应（OpenAI 格式）
    llm_response = {
        "content": "我来帮您查询天气。",
        "tool_calls": [
            {
                "id": "call_01234",
                "function": {
                    "name": "get_weather",
                    "arguments": '{"city": "北京"}'
                }
            }
        ]
    }

    tool_results = [
        {
            "tool": "get_weather",
            "result": {"temperature": 25, "condition": "晴天"},
            "success": True
        }
    ]

    tool_calls = llm_response.get("tool_calls", [])

    # 构建 assistant 消息（OpenAI 格式）
    assistant_message = {
        "role": "assistant",
        "content": llm_response.get("content", ""),
        "tool_calls": tool_calls,
    }

    # 构建 tool 消息（OpenAI 格式）
    tool_messages = []
    for tool_result in tool_results:
        tool_call_id = tool_calls[0].get("id") if tool_calls else None
        tool_messages.append({
            "role": "tool",
            "content": json.dumps(tool_result, ensure_ascii=False),
            "tool_call_id": tool_call_id,
        })

    # 打印结果
    print("\n1. Assistant message (with tool_calls):")
    print(json.dumps(assistant_message, indent=2, ensure_ascii=False))

    print("\n2. Tool message:")
    print(json.dumps(tool_messages, indent=2, ensure_ascii=False))

    # 验证格式
    assert assistant_message["role"] == "assistant"
    assert "tool_calls" in assistant_message
    assert len(assistant_message["tool_calls"]) == 1

    assert tool_messages[0]["role"] == "tool"
    assert tool_messages[0]["tool_call_id"] == "call_01234"

    print("\n✓ All assertions passed!")
    print("\nTest PASSED!")


def test_anthropic_adapter_response_parsing():
    """测试 Anthropic adapter 的响应解析"""

    print("\n" + "="*60)
    print("Test: Simulate Anthropic response parsing")
    print("="*60)

    # 模拟 Anthropic API 响应的 content blocks
    class MockBlock:
        def __init__(self, block_type, **kwargs):
            self.type = block_type
            for k, v in kwargs.items():
                setattr(self, k, v)

    # 模拟响应
    mock_blocks = [
        MockBlock("text", text="我来帮您查询天气。"),
        MockBlock("tool_use", id="toolu_abc123", name="get_weather", input={"city": "北京"}),
    ]

    # 解析响应（模拟 adapter 中的逻辑）
    text_content = ""
    tool_calls = []
    raw_content_blocks = []

    for block in mock_blocks:
        block_dict = None
        block_type = block.type

        if block_type == "text" and hasattr(block, "text") and block.text:
            text_content += block.text
            block_dict = {"type": "text", "text": block.text}

        elif block_type == "tool_use":
            tool_call = {
                "id": block.id,
                "function": {
                    "name": block.name,
                    "arguments": block.input,
                },
            }
            tool_calls.append(tool_call)
            block_dict = {
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            }

        if block_dict:
            raw_content_blocks.append(block_dict)

    result = {
        "content": text_content,
        "tool_calls": tool_calls,
        "raw_content_blocks": raw_content_blocks,
    }

    print("\nParsed result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # 验证
    assert result["content"] == "我来帮您查询天气。"
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["id"] == "toolu_abc123"
    assert result["tool_calls"][0]["function"]["name"] == "get_weather"
    assert len(result["raw_content_blocks"]) == 2
    assert result["raw_content_blocks"][1]["type"] == "tool_use"

    print("\n✓ All assertions passed!")
    print("\nTest PASSED!")


def test_multiturn_conversation_flow():
    """测试多轮对话的完整流程"""

    print("\n" + "="*60)
    print("Test: Multi-turn conversation flow simulation")
    print("="*60)

    # 初始消息
    messages = [
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "北京今天天气怎么样？"},
    ]

    print("\n--- Round 1: Initial request ---")
    print(json.dumps(messages, indent=2, ensure_ascii=False))

    # 模拟第一轮 LLM 响应
    llm_response_1 = {
        "content": "",
        "tool_calls": [
            {
                "id": "toolu_001",
                "function": {"name": "get_weather", "arguments": {"city": "北京"}}
            }
        ],
        "raw_content_blocks": [
            {
                "type": "tool_use",
                "id": "toolu_001",
                "name": "get_weather",
                "input": {"city": "北京"}
            }
        ]
    }

    # 添加 assistant 消息
    messages.append({
        "role": "assistant",
        "content": llm_response_1["raw_content_blocks"],
    })

    # 添加 tool_result
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_001",
                "content": '{"temperature": 25, "condition": "晴天"}',
            }
        ]
    })

    print("\n--- Round 2: After tool execution ---")
    for i, msg in enumerate(messages):
        print(f"\nMessage {i}: role={msg['role']}")
        if isinstance(msg['content'], list):
            for block in msg['content']:
                print(f"  - type={block.get('type')}")
        else:
            print(f"  - text: {msg['content'][:50]}..." if len(str(msg['content'])) > 50 else f"  - text: {msg['content']}")

    # 模拟第二轮 LLM 响应（不再需要工具）
    llm_response_2 = {
        "content": "北京今天天气很好，气温25度，是晴天。",
        "tool_calls": [],
        "raw_content_blocks": [
            {"type": "text", "text": "北京今天天气很好，气温25度，是晴天。"}
        ]
    }

    print("\n--- Final Response ---")
    print(f"Content: {llm_response_2['content']}")

    # 验证多轮对话消息格式正确
    assert len(messages) == 4  # system + user + assistant + user(tool_result)
    assert messages[2]["role"] == "assistant"
    assert isinstance(messages[2]["content"], list)
    assert messages[2]["content"][0]["type"] == "tool_use"
    assert messages[3]["role"] == "user"
    assert isinstance(messages[3]["content"], list)
    assert messages[3]["content"][0]["type"] == "tool_result"

    print("\n✓ All assertions passed!")
    print("\nTest PASSED!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Running Anthropic Format Tests")
    print("="*60)

    test_message_format_conversion()
    test_openai_format()
    test_anthropic_adapter_response_parsing()
    test_multiturn_conversation_flow()

    print("\n" + "="*60)
    print("All tests completed successfully!")
    print("="*60)
