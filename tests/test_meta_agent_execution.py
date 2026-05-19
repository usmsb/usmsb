"""
Test MetaAgent Execution Mode - 验证代码开发执行规则是否生效

测试场景：用户要求"帮我创建一个Flask REST API"
预期：MetaAgent 应该调用 write_file + run_command 工具，而非只返回代码文本
"""

import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from usmsb_sdk.meta_agent import MetaAgent, MetaAgentConfig
from usmsb_sdk.meta_agent.config import LLMConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_flask_api_creation():
    """测试：创建一个Flask REST API - 验证是否真正执行而非返回文本"""
    print("\n" + "="*60)
    print("Test: Flask REST API Creation (Execution Mode)")
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
        # 注册测试钱包（绕过权限检查）
        test_wallet = "test_wallet_execution_001"
        from usmsb_sdk.meta_agent.permission.manager import UserRole
        try:
            await agent.permission_manager.register_user(
                wallet_address=test_wallet,
                role=UserRole.DEVELOPER,
            )
            logger.info(f"Registered test wallet: {test_wallet}")
        except Exception as e:
            logger.warning(f"Wallet registration failed (may already exist): {e}")

        # 检查可用工具
        tools = agent.get_available_tools()
        tool_names = [t['name'] for t in tools]
        print(f"\n可用工具数量: {len(tools)}")
        print(f"关键工具: {[n for n in tool_names if n in ['write_file', 'run_command', 'execute_command', 'create_directory', 'read_file', 'list_directory']]}")

        # 发送创建Flask API的任务
        print("\n发送任务：帮我创建一个Flask REST API，包含用户注册和登录功能")
        response = await agent.chat(
            message="帮我创建一个Flask REST API，包含用户注册和登录功能。只创建核心代码，不要解释太多。",
            wallet_address=test_wallet
        )

        print(f"\n响应长度: {len(response)} 字符")
        print(f"\n响应内容:\n{response[:2000]}")

        # 判断是否真正执行了工具（通过检查文件是否被创建）
        # MetaAgent data_dir 默认为 ./data，所以 workspace 在:
        # /Users/gujun/vibecode/usmsb/data/{wallet}/workspace/
        import os as _os
        import glob as _glob
        base_data_dir = _os.path.join(_os.getcwd(), "data")
        user_workspace = f"{base_data_dir}/{test_wallet}/workspace"
        
        # 搜索所有 .py 文件（LLM 可能用不同目录名）
        py_files = []
        if _os.path.exists(user_workspace):
            for root, dirs, files in _os.walk(user_workspace):
                dirs[:] = [d for d in dirs if d not in ('temp', 'output', 'uploads', 'workspace')]
                for f in files:
                    if f.endswith('.py'):
                        full_path = _os.path.join(root, f)
                        py_files.append(full_path)
                        rel_path = _os.path.relpath(full_path, user_workspace)
                        size = _os.path.getsize(full_path)
                        print(f"\n📄 {rel_path} ({size} 字节)")

        print(f"\n--- 分析 ---")
        print(f"检查路径: {user_workspace}")
        print(f"Python 文件数量: {len(py_files)}")
        print(f"工具调用成功: {len(py_files) > 0}")

        if len(py_files) >= 2:
            print(f"\n✅ 通过: 工具执行成功！创建了 {len(py_files)} 个 Python 文件")
            print(f"文件列表: {[_os.path.relpath(f, user_workspace) for f in py_files]}")
        elif len(py_files) == 1:
            print(f"\n✅ 部分通过: 创建了 {len(py_files)} 个 Python 文件")
        else:
            has_code_blocks = "```" in response
            print(f"\n❌ 未通过: 文件未创建 (响应包含代码块: {has_code_blocks})")
            print(f"响应内容: {response[:500]}")

    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.stop()


async def test_simple_project_creation():
    """测试：创建一个简单项目 - 验证是否调用 write_file"""
    print("\n" + "="*60)
    print("Test: Simple Python Project Creation")
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
        print("\n发送任务：创建一个计算器Python程序，包含加减乘除功能")
        response = await agent.chat(
            message="创建一个计算器Python程序，包含加减乘除功能，写到 calc.py 文件中",
            wallet_address="test_wallet_execution_002"
        )

        print(f"\n响应长度: {len(response)} 字符")
        print(f"\n响应内容（前1000字符）:\n{response[:1000]}")

        has_code_blocks = "```" in response
        print(f"\n包含代码文本块: {has_code_blocks}")
        if has_code_blocks:
            print("❌ 返回了代码文本块而非实际创建文件")

    except Exception as e:
        print(f"\n测试出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.stop()


async def main():
    print("\n" + "="*60)
    print("MetaAgent 执行模式测试")
    print("="*60)

    if not os.getenv("MINIMAX_API_KEY"):
        print("\nERROR: MINIMAX_API_KEY not set!")
        return

    await test_flask_api_creation()
    # await test_simple_project_creation()

    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
