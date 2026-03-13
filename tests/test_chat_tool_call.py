"""
Test Chat with Tool Calling
测试 Anthropic API 格式的 tool calling 功能
"""

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.platform.external.meta_agent import MetaAgent, MetaAgentConfig
from usmsb_sdk.platform.external.meta_agent.config import LLMConfig

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_chat_simple():
    """测试简单的对话（无工具调用）"""
    print("\n" + "="*60)
    print("Test 1: Simple chat (no tools)")
    print("="*60)

    config = MetaAgentConfig(
        llm=LLMConfig(
            provider="minimax",
            api_key=os.getenv("MINIMAX_API_KEY"),
            model="MiniMax-M2.5",
        )
    )

    agent = MetaAgent(config)
    await agent.start()

    try:
        response = await agent.chat(
            message="你好，请介绍一下你自己",
            wallet_address="test_wallet_001"
        )
        print(f"\nResponse: {response}")
        print("\nTest 1 PASSED!" if response and len(response) > 0 else "\nTest 1 FAILED!")
    except Exception as e:
        print(f"\nTest 1 FAILED with error: {e}")
    finally:
        await agent.stop()


async def test_chat_with_tool():
    """测试带工具调用的对话"""
    print("\n" + "="*60)
    print("Test 2: Chat with tool calling")
    print("="*60)

    config = MetaAgentConfig(
        llm=LLMConfig(
            provider="minimax",
            api_key=os.getenv("MINIMAX_API_KEY"),
            model="MiniMax-M2.5",
        )
    )

    agent = MetaAgent(config)
    await agent.start()

    try:
        # 获取可用工具
        tools = agent.get_available_tools()
        print(f"\nAvailable tools: {[t['name'] for t in tools]}")

        # 测试一个可能会触发工具调用的问题
        response = await agent.chat(
            message="请帮我查询一下平台的状态信息",
            wallet_address="test_wallet_002"
        )
        print(f"\nResponse: {response}")
        print("\nTest 2 PASSED!" if response and len(response) > 0 else "\nTest 2 FAILED!")
    except Exception as e:
        print(f"\nTest 2 FAILED with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.stop()


async def test_multi_turn_tool_call():
    """测试多轮工具调用"""
    print("\n" + "="*60)
    print("Test 3: Multi-turn conversation with tools")
    print("="*60)

    config = MetaAgentConfig(
        llm=LLMConfig(
            provider="minimax",
            api_key=os.getenv("MINIMAX_API_KEY"),
            model="MiniMax-M2.5",
        )
    )

    agent = MetaAgent(config)
    await agent.start()

    try:
        wallet = "test_wallet_003"

        # 第一轮对话
        response1 = await agent.chat(
            message="你好，我是新用户，想了解一下这个平台",
            wallet_address=wallet
        )
        print(f"\nRound 1 Response: {response1[:200]}..." if len(response1) > 200 else f"\nRound 1 Response: {response1}")

        # 第二轮对话（同一个 wallet，会话继续）
        response2 = await agent.chat(
            message="你能做什么？有哪些工具可以使用？",
            wallet_address=wallet
        )
        print(f"\nRound 2 Response: {response2[:200]}..." if len(response2) > 200 else f"\nRound 2 Response: {response2}")

        # 第三轮对话，尝试触发工具
        response3 = await agent.chat(
            message="请查询一下系统状态",
            wallet_address=wallet
        )
        print(f"\nRound 3 Response: {response3[:200]}..." if len(response3) > 200 else f"\nRound 3 Response: {response3}")

        print("\nTest 3 PASSED!")
    except Exception as e:
        print(f"\nTest 3 FAILED with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.stop()


async def test_llm_adapter_directly():
    """直接测试 LLM Adapter 的 tool calling"""
    print("\n" + "="*60)
    print("Test 4: Direct LLM Adapter test with tools")
    print("="*60)

    from usmsb_sdk.intelligence_adapters.llm.minimax_adapter import MiniMaxAdapter
    from usmsb_sdk.intelligence_adapters.base import IntelligenceSourceConfig, IntelligenceSourceType

    config = IntelligenceSourceConfig(
        name="minimax",
        type=IntelligenceSourceType.LLM,
        api_key=os.getenv("MINIMAX_API_KEY"),
        model="MiniMax-M2.5",
        extra_params={
            "base_url": "https://api.minimaxi.com/anthropic",
        }
    )

    adapter = MiniMaxAdapter(config)
    await adapter.initialize()

    try:
        # 测试带工具的调用
        messages = [
            {"role": "system", "content": "你是一个助手，可以使用工具来帮助用户。"},
            {"role": "user", "content": "今天北京天气怎么样？"},
        ]

        tools = [
            {
                "name": "get_weather",
                "description": "获取指定城市的天气信息",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名称"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]

        response = await adapter.chat_with_tools(messages, tools)
        print(f"\nResponse content: {response.get('content')}")
        print(f"Tool calls: {response.get('tool_calls')}")
        print(f"Raw content blocks: {response.get('raw_content_blocks')}")

        if response.get('tool_calls'):
            print("\n✓ Tool calling works! Model requested tool use.")

            # 模拟多轮对话：添加 assistant 消息和 tool_result
            raw_blocks = response.get('raw_content_blocks', [])
            tool_calls = response.get('tool_calls', [])

            # 构建 tool_result
            tool_result_blocks = []
            for tc in tool_calls:
                tool_result_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": '{"temperature": 25, "condition": "晴天", "humidity": 45}',
                })

            # 添加 assistant 消息（使用原始 content blocks）
            messages.append({
                "role": "assistant",
                "content": raw_blocks,
            })

            # 添加 tool_result
            messages.append({
                "role": "user",
                "content": tool_result_blocks,
            })

            print(f"\n--- Second turn messages ---")
            for i, msg in enumerate(messages):
                print(f"Message {i}: role={msg['role']}")
                if isinstance(msg['content'], list):
                    for block in msg['content']:
                        print(f"  - {block.get('type')}: {str(block)[:100]}...")
                else:
                    print(f"  - text: {msg['content'][:100]}...")

            # 继续对话
            response2 = await adapter.chat_with_tools(messages, tools)
            print(f"\nSecond turn response: {response2.get('content')}")
            print(f"Second turn tool calls: {response2.get('tool_calls')}")

            print("\nTest 4 PASSED!")
        else:
            print("\n? No tool call in this test (model chose not to use tool)")
            print("This might be normal depending on the model's decision.")

    except Exception as e:
        print(f"\nTest 4 FAILED with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adapter.shutdown()


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Starting Chat Tool Call Tests")
    print("="*60)

    # 检查 API Key
    if not os.getenv("MINIMAX_API_KEY"):
        print("\nERROR: MINIMAX_API_KEY environment variable not set!")
        print("Please set it before running tests:")
        print("  export MINIMAX_API_KEY='your-api-key'")
        return

    # 运行测试
    await test_llm_adapter_directly()
    # await test_chat_simple()
    # await test_chat_with_tool()
    # await test_multi_turn_tool_call()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
