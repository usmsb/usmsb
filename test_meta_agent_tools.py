#!/usr/bin/env python3
"""
MetaAgent 预置工具测试脚本

测试所有注册的预置工具调用
"""

import asyncio
import sys
import os

# 添加 SDK 路径
sys.path.insert(0, '/Users/gujun/vibecode/usmsb/src')

import logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_tool_registry():
    """测试工具注册表"""
    from usmsb_sdk.meta_agent.tools.registry import ToolRegistry
    
    registry = ToolRegistry()
    
    # 导入并注册所有工具
    from usmsb_sdk.meta_agent.tools import register_tools
    await register_tools(registry)
    
    # 列出所有工具
    tools = registry.list_tools()
    print(f"\n{'='*60}")
    print(f"📦 MetaAgent 预置工具注册表")
    print(f"{'='*60}")
    print(f"共注册 {len(tools)} 个工具\n")
    
    for i, tool in enumerate(tools, 1):
        print(f"{i:2d}. {tool['name']:<25} - {tool['description'][:50]}...")
    
    return registry


async def test_platform_tools(registry):
    """测试平台工具"""
    print(f"\n{'='*60}")
    print(f"�_platform 平台管理工具测试")
    print(f"{'='*60}")
    
    platform_tools = [
        "start_node", "stop_node", "get_node_status", 
        "get_config", "update_config", "bind_wallet", "register_agent"
    ]
    
    for tool_name in platform_tools:
        try:
            result = await registry.execute(tool_name)
            print(f"✅ {tool_name}: {result}")
        except Exception as e:
            print(f"❌ {tool_name}: {e}")


async def test_system_tools(registry):
    """测试系统工具"""
    print(f"\n{'='*60}")
    print(f"⚙️ 系统工具测试")
    print(f"{'='*60}")
    
    # 测试 list_directory
    try:
        result = await registry.execute(
            "list_directory", 
            path="/Users/gujun/vibecode/usmsb",
            show_hidden=False
        )
        print(f"✅ list_directory: 成功列出目录")
        if "entries" in result:
            entries = result["entries"][:5]
            for e in entries:
                print(f"   - {e.get('name', 'unknown')}")
    except Exception as e:
        print(f"❌ list_directory: {e}")
    
    # 测试 get_file_info
    try:
        result = await registry.execute(
            "get_file_info",
            path="/Users/gujun/vibecode/usmsb/README.md"
        )
        print(f"✅ get_file_info: {result.get('size', 'unknown')} bytes")
    except Exception as e:
        print(f"❌ get_file_info: {e}")


async def test_web_tools(registry):
    """测试 Web 工具"""
    print(f"\n{'='*60}")
    print(f"🌐 Web 工具测试")
    print(f"{'='*60}")
    
    # 测试 fetch_url
    try:
        result = await registry.execute(
            "fetch_url",
            url="https://httpbin.org/get",
            method="GET"
        )
        if result.get("status") == "success":
            print(f"✅ fetch_url: status_code={result.get('status_code')}")
        else:
            print(f"⚠️ fetch_url: {result.get('message')}")
    except Exception as e:
        print(f"❌ fetch_url: {e}")


async def test_execution_tools(registry):
    """测试执行工具"""
    print(f"\n{'='*60}")
    print(f"🚀 执行工具测试")
    print(f"{'='*60}")
    
    # 测试不需要 session 的 execute_command
    try:
        result = await registry.execute(
            "execute_command",
            command="echo 'Hello from MetaAgent tools!'",
            timeout=5
        )
        print(f"✅ execute_command: {result.get('stdout', '').strip()}")
    except Exception as e:
        print(f"❌ execute_command: {e}")


async def test_tool_schemas(registry):
    """测试工具 Schema 生成"""
    print(f"\n{'='*60}")
    print(f"📄 工具 Schema 测试 (Function Calling)")
    print(f"{'='*60}")
    
    # 获取所有工具的 schema
    schemas = registry.get_tools_schema(provider="anthropic")
    
    print(f"\n共有 {len(schemas)} 个工具的 schema:\n")
    
    # 展示前 5 个工具的 schema
    for i, schema in enumerate(schemas[:5], 1):
        func = schema.get("function", {})
        print(f"{i}. {func.get('name')}")
        print(f"   description: {func.get('description', '')[:60]}...")
        params = func.get("parameters", {})
        props = params.get("properties", {})
        print(f"   parameters: {list(props.keys())}")
        print()


async def test_blockchain_tools(registry):
    """测试区块链工具"""
    print(f"\n{'='*60}")
    print(f"⛓️ 区块链工具测试")
    print(f"{'='*60}")
    
    blockchain_tools = [
        "get_wallet_balance",
        "get_transaction_history", 
        "send_transaction",
        "deploy_contract"
    ]
    
    for tool_name in blockchain_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"✅ {tool_name} (requires_session={tool.requires_session})")
        else:
            print(f"⚠️ {tool_name} - 未找到")


async def test_database_tools(registry):
    """测试数据库工具"""
    print(f"\n{'='*60}")
    print(f"🗄️ 数据库工具测试")
    print(f"{'='*60}")
    
    db_tools = [
        "db_query",
        "db_insert",
        "db_update",
        "db_delete"
    ]
    
    for tool_name in db_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"✅ {tool_name} (requires_session={tool.requires_session})")
        else:
            print(f"⚠️ {tool_name} - 未找到")


async def test_permission_tools(registry):
    """测试权限工具"""
    print(f"\n{'='*60}")
    print(f"🔐 权限工具测试")
    print(f"{'='*60}")
    
    perm_tools = [
        "check_permission",
        "grant_permission",
        "revoke_permission"
    ]
    
    for tool_name in perm_tools:
        tool = registry.get_tool(tool_name)
        if tool:
            print(f"✅ {tool_name} (requires_session={tool.requires_session})")
        else:
            print(f"⚠️ {tool_name} - 未找到")


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 MetaAgent 预置工具测试")
    print("="*60)
    
    # 测试工具注册表
    registry = await test_tool_registry()
    
    # 测试各类工具
    await test_platform_tools(registry)
    await test_system_tools(registry)
    await test_web_tools(registry)
    await test_execution_tools(registry)
    await test_tool_schemas(registry)
    await test_blockchain_tools(registry)
    await test_database_tools(registry)
    
    print(f"\n{'='*60}")
    print("✅ 测试完成")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
