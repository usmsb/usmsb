#!/usr/bin/env python
"""
清理并重新注册 Demo Agents

运行方式:
    cd demo/software_dev
    python cleanup_and_reregister.py
"""

import asyncio
import sys
import os
import httpx
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = os.getenv("PLATFORM_URL", "http://127.0.0.1:8000")

# Demo Agent 名称和端口映射
DEMO_AGENT_PORTS = {
    "ProductOwner": 8081,
    "Architect": 8082,
    "Developer": 8083,
    "Reviewer": 8084,
    "DevOps": 8085,
}
DEMO_AGENT_NAMES = list(DEMO_AGENT_PORTS.keys())


async def get_all_agents(client: httpx.AsyncClient) -> list:
    """获取所有已注册的 agents"""
    try:
        response = await client.get(f"{BASE_URL}/agents")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"获取 agents 失败: {e}")
        return []


async def cleanup_demo_agents(client: httpx.AsyncClient) -> int:
    """清理 Demo agents"""
    print("\n" + "=" * 60)
    print("  🧹 清理 Demo Agents")
    print("=" * 60)

    agents = await get_all_agents(client)
    if not agents:
        print("  没有找到已注册的 agents")
        return 0

    print(f"  平台共有 {len(agents)} 个 agents")

    deleted_count = 0
    for agent in agents:
        agent_name = agent.get("name", "")
        agent_id = agent.get("agent_id", agent.get("id", ""))
        metadata = agent.get("metadata", {})

        # 检查是否是 demo agent
        is_demo = (
            agent_name in DEMO_AGENT_NAMES or
            metadata.get("demo") == "software_dev" or
            "software_dev" in str(metadata)
        )

        if is_demo and agent_id:
            try:
                response = await client.delete(f"{BASE_URL}/agents/{agent_id}")
                if response.status_code in [200, 204, 404]:
                    deleted_count += 1
                    print(f"  🗑️ 已删除: {agent_name} ({agent_id})")
                else:
                    print(f"  ⚠️ 删除失败 {agent_name}: {response.status_code}")
            except Exception as e:
                print(f"  ❌ 删除异常 {agent_name}: {e}")

    print(f"\n  ✅ 共删除 {deleted_count} 个 Demo Agents")
    return deleted_count


async def register_demo_agents(client: httpx.AsyncClient) -> int:
    """注册 Demo Agents"""
    print("\n" + "=" * 60)
    print("  📝 注册 Demo Agents")
    print("=" * 60)

    # Agent 配置
    agents_config = [
        {
            "name": "ProductOwner",
            "description": "产品经理 Agent - 负责需求分析和任务拆分",
            "capabilities": ["requirement_analysis", "prioritization", "acceptance_testing"],
            "skills": [
                {"name": "analyze_requirement", "description": "分析需求"},
                {"name": "accept_feature", "description": "验收功能"},
            ],
        },
        {
            "name": "Architect",
            "description": "架构师 Agent - 负责系统架构设计和技术选型",
            "capabilities": ["architecture_design", "tech_selection", "api_design"],
            "skills": [
                {"name": "design_architecture", "description": "设计架构"},
                {"name": "select_tech_stack", "description": "技术选型"},
            ],
        },
        {
            "name": "Developer",
            "description": "开发者 Agent - 负责代码实现和测试",
            "capabilities": ["coding", "testing", "debugging", "documentation"],
            "skills": [
                {"name": "implement_feature", "description": "实现功能"},
                {"name": "write_tests", "description": "编写测试"},
            ],
        },
        {
            "name": "Reviewer",
            "description": "代码审查 Agent - 负责代码质量和安全审查",
            "capabilities": ["code_review", "security_audit", "best_practices"],
            "skills": [
                {"name": "review_code", "description": "代码审查"},
                {"name": "check_security", "description": "安全检查"},
            ],
        },
        {
            "name": "DevOps",
            "description": "运维 Agent - 负责部署和监控",
            "capabilities": ["ci_cd", "deployment", "monitoring"],
            "skills": [
                {"name": "deploy", "description": "部署应用"},
                {"name": "check_health", "description": "健康检查"},
            ],
        },
    ]

    registered_count = 0
    for cfg in agents_config:
        port = DEMO_AGENT_PORTS.get(cfg["name"], 8080)
        registration_data = {
            "name": cfg["name"],
            "description": cfg["description"],
            "agent_type": "ai_agent",
            "capabilities": cfg["capabilities"],
            "skills": cfg["skills"],
            "endpoint": f"http://localhost:{port}",
            "chat_endpoint": f"http://localhost:{port}/chat",
            "protocol": "standard",
            "status": "online",
            "heartbeat_interval": 30,
            "ttl": 90,
            "metadata": {
                "role": cfg["name"],
                "demo": "software_dev",
                "version": "1.0.0",
                "port": port,
                "chat_supported": True,
                "heartbeat_enabled": True,
            }
        }

        try:
            response = await client.post(
                f"{BASE_URL}/agents",
                json=registration_data
            )

            if response.status_code in [200, 201]:
                data = response.json()
                agent_id = data.get("agent_id", "unknown")
                registered_count += 1
                print(f"  ✅ 注册成功: {cfg['name']} (ID: {agent_id})")
            else:
                error_detail = response.text[:100]
                print(f"  ❌ 注册失败 {cfg['name']}: {response.status_code} - {error_detail}")
        except Exception as e:
            print(f"  ❌ 注册异常 {cfg['name']}: {e}")

    print(f"\n  ✅ 共注册 {registered_count} 个 Demo Agents")
    return registered_count


async def verify_agents(client: httpx.AsyncClient):
    """验证注册的 agents"""
    print("\n" + "=" * 60)
    print("  🔍 验证注册的 Agents")
    print("=" * 60)

    agents = await get_all_agents(client)
    demo_agents = [a for a in agents if a.get("metadata", {}).get("demo") == "software_dev"]

    print(f"  平台共有 {len(agents)} 个 agents")
    print(f"  Demo Agents: {len(demo_agents)} 个")

    for agent in demo_agents:
        print(f"    - {agent.get('name')}: {agent.get('description', '')[:40]}...")


async def main():
    print("\n" + "🎯" * 30)
    print("\n  🔄 Demo Agents 清理与重新注册")
    print("\n" + "🎯" * 30)
    print(f"\n  平台地址: {BASE_URL}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 检查平台
        try:
            response = await client.get(f"{BASE_URL}/health")
            if response.status_code != 200:
                print(f"\n  ❌ 平台不健康: {response.status_code}")
                return
            print(f"  ✅ 平台运行正常")
        except Exception as e:
            print(f"\n  ❌ 无法连接平台: {e}")
            return

        # 清理
        deleted = await cleanup_demo_agents(client)

        # 重新注册
        registered = await register_demo_agents(client)

        # 验证
        await verify_agents(client)

    print("\n" + "=" * 60)
    if deleted > 0 and registered > 0:
        print(f"  ✅ 完成! 删除了 {deleted} 个, 注册了 {registered} 个")
    else:
        print(f"  ⚠️ 完成! 删除: {deleted}, 注册: {registered}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
