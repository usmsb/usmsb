#!/usr/bin/env python3
"""
MetaAgent 预置工具测试 - 带钱包绑定

测试需要 UserSession 的工具调用
"""

import asyncio
import sys
import os
from uuid import uuid4

sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_with_wallet_binding():
    """使用钱包绑定测试工具"""
    from usmsb_sdk.meta_agent.tools.registry import ToolRegistry
    from usmsb_sdk.meta_agent.session.user_session import UserSession, SessionConfig
    from usmsb_sdk.meta_agent.session.session_manager import SessionManager
    
    # 生成随机钱包地址（测试用）
    test_wallet = f"0x{uuid4().hex[:40]}"
    test_node_id = "test-node-001"
    
    # 直接创建 UserSession
    session_config = SessionConfig()
    print(f"\n{'='*60}")
    print(f"🔗 绑定测试钱包地址: {test_wallet}")
    print(f"{'='*60}")
    
    # 创建 registry
    registry = ToolRegistry()
    
    # 注册所有工具
    from usmsb_sdk.meta_agent.tools import register_tools
    await register_tools(registry)
    
    # 直接创建 UserSession
    user_session = UserSession(
        wallet_address=test_wallet,
        node_id=test_node_id,
        config=session_config,
        data_dir="/tmp/test_sessions"
    )
    
    # 初始化 session
    await user_session.init()
    
    print(f"\n✅ UserSession 创建成功")
    print(f"   wallet: {user_session.wallet_address}")
    print(f"   workspace: {user_session.workspace}")
    
    # 测试需要 session 的工具
    print(f"\n{'='*60}")
    print(f"🧪 测试需要 UserSession 的工具")
    print(f"{'='*60}")
    
    # 1. list_directory
    print(f"\n1️⃣ list_directory")
    try:
        result = await registry.execute(
            "list_directory",
            session=user_session,
            path=user_session.workspace,
            show_hidden=False
        )
        print(f"   ✅ 成功")
        if "entries" in result:
            entries = result["entries"][:5]
            print(f"   📁 前5个条目:")
            for e in entries:
                print(f"      - {e.get('name', 'unknown')}")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 2. get_file_info
    print(f"\n2️⃣ get_file_info")
    try:
        # 使用绝对路径或工作空间相对路径
        readme_path = "/Users/gujun/vibecode/usmsb/README.md"
        
        result = await registry.execute(
            "get_file_info",
            session=user_session,
            path=readme_path
        )
        print(f"   ✅ 成功: {result.get('name')} - {result.get('size', 0)} bytes")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 3. search_files
    print(f"\n3️⃣ search_files")
    try:
        result = await registry.execute(
            "search_files",
            session=user_session,
            path="/Users/gujun/vibecode/usmsb/src",
            pattern="*.py",
            max_results=5
        )
        print(f"   ✅ 成功找到 {len(result.get('results', []))} 个文件")
        for r in result.get('results', [])[:3]:
            print(f"      - {r}")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 4. execute_command (不需要 session，但通过 session 执行)
    print(f"\n4️⃣ execute_command (with session)")
    try:
        result = await registry.execute(
            "execute_command",
            session=user_session,
            command="pwd",
            timeout=5
        )
        print(f"   ✅ {result.get('stdout', '').strip()}")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 5. read_file
    print(f"\n5️⃣ read_file")
    try:
        result = await registry.execute(
            "read_file",
            session=user_session,
            path="/Users/gujun/vibecode/usmsb/README.md",
            limit=200
        )
        content = result.get('content', '')[:100]
        print(f"   ✅ 读取成功: {content}...")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 6. write_file
    print(f"\n6️⃣ write_file")
    try:
        # 使用相对路径（相对于用户工作空间）
        test_file = "test_from_metaagent.txt"
        result = await registry.execute(
            "write_file",
            session=user_session,
            path=test_file,
            content="Hello from MetaAgent tool test! Written at " + str(asyncio.get_event_loop().time()),
            mode="w"
        )
        print(f"   ✅ 写入成功: {result.get('path', test_file)}")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 7. browser工具检查
    print(f"\n7️⃣ browser_open (检查工具是否可用)")
    tool = registry.get_tool("browser_open")
    if tool:
        print(f"   ✅ browser_open 已注册 (requires_session={tool.requires_session})")
        # 注意：实际打开浏览器需要桌面环境
    else:
        print(f"   ❌ browser_open 未找到")
    
    # 8. jupyter工具检查
    print(f"\n8️⃣ jupyter_status")
    tool = registry.get_tool("jupyter_status")
    if tool:
        print(f"   ✅ jupyter_status 已注册 (requires_session={tool.requires_session})")
        try:
            result = await registry.execute(
                "jupyter_status",
                session=user_session
            )
            print(f"   📊 状态: {result}")
        except Exception as e:
            print(f"   ⚠️ 执行: {e}")
    else:
        print(f"   ❌ jupyter_status 未找到")
    
    print(f"\n{'='*60}")
    print(f"✅ 钱包绑定工具测试完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(test_with_wallet_binding())
