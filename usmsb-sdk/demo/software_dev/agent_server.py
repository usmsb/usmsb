"""
Agent HTTP 服务器启动脚本

每个 Agent 在独立进程中运行
用法: python agent_server.py <agent_class> <port> <platform_url> <agent_id>
"""
import asyncio
import sys
import os

# 添加项目路径
demo_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(demo_dir)
usmsb_root = os.path.dirname(project_root)
sys.path.insert(0, usmsb_root)
sys.path.insert(0, os.path.join(usmsb_root, 'src'))

from usmsb_sdk.agent_sdk import AgentConfig, CapabilityDefinition, ProtocolType, ProtocolConfig
from demo.shared import DemoAgent
from demo.software_dev.agents import (
    ProductOwnerAgent,
    ArchitectAgent,
    DeveloperAgent,
    ReviewerAgent,
    DevOpsAgent,
)


# Agent 类映射
AGENT_CLASSES = {
    "ProductOwner": ProductOwnerAgent,
    "Architect": ArchitectAgent,
    "Developer": DeveloperAgent,
    "Reviewer": ReviewerAgent,
    "DevOps": DevOpsAgent,
}

# Agent 元数据
AGENT_METADATA = {
    "ProductOwner": {
        "role": "产品经理",
        "capabilities": ["requirement_analysis", "prioritization", "acceptance_testing"],
    },
    "Architect": {
        "role": "架构师",
        "capabilities": ["architecture_design", "tech_selection", "api_design"],
    },
    "Developer": {
        "role": "开发者",
        "capabilities": ["coding", "testing", "debugging"],
    },
    "Reviewer": {
        "role": "代码审查",
        "capabilities": ["code_review", "security_audit"],
    },
    "DevOps": {
        "role": "运维",
        "capabilities": ["ci_cd", "deployment", "monitoring"],
    },
}


async def start_agent_server(agent_name: str, port: int, platform_url: str, agent_id: str = None):
    """启动 Agent HTTP 服务器"""
    metadata = AGENT_METADATA[agent_name]
    agent_class = AGENT_CLASSES[agent_name]

    # 配置能力
    capabilities = [
        CapabilityDefinition(
            name=c,
            description=c.replace("_", " ").title(),
            category="development",
            level="advanced"
        )
        for c in metadata["capabilities"]
    ]

    # 配置协议 - 启用HTTP用于注册（设置endpoint）
    protocols = {
        ProtocolType.HTTP: ProtocolConfig(
            protocol_type=ProtocolType.HTTP,
            enabled=True,  # 启用以便注册时设置endpoint
            port=port,
            host="localhost",
        ),
    }

    # 创建配置
    config_kwargs = {
        "name": agent_name,
        "description": f"{metadata['role']} AI Agent",
        "capabilities": capabilities,
        "protocols": protocols,
        "auto_register": True,
        "skip_http_auto_start": True,  # 跳过自动启动，由start_with_http手动启动
        "heartbeat_interval": 30,
        "ttl": 90,
    }
    if agent_id:
        config_kwargs["agent_id"] = agent_id

    config = AgentConfig(**config_kwargs)

    # 创建 Agent 实例
    agent = agent_class(config, visualizer=None)

    print(f"🚀 {agent_name} 启动中...")

    # 启动agent（包括注册）
    await agent.start()

    print(f"✅ {agent_name} 已注册，Agent ID: {agent.agent_id}")
    print(f"   HTTP 端口: {port}")

    # 启动 HTTP 服务器
    print(f"🌐 {agent_name} 启动 HTTP 服务器...")
    await agent.start_with_http(
        host="0.0.0.0",
        port=port,
        platform_url=platform_url,
    )
    print(f"✅ {agent_name} HTTP 服务器已启动: http://localhost:{port}")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    # 停止
    print(f"🛑 {agent_name} 停止中...")
    await agent.stop_http()
    await agent.stop()
    print(f"✅ {agent_name} 已停止")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("用法: python agent_server.py <agent_name> <port> <platform_url> [agent_id]")
        sys.exit(1)

    agent_name = sys.argv[1]
    port = int(sys.argv[2])
    platform_url = sys.argv[3]
    agent_id = sys.argv[4] if len(sys.argv) > 4 else None

    print(f"=" * 50)
    print(f"  Agent 服务器: {agent_name}")
    print(f"  端口: {port}")
    print(f"  平台: {platform_url}")
    if agent_id:
        print(f"  Agent ID: {agent_id}")
    print(f"=" * 50)

    asyncio.run(start_agent_server(agent_name, port, platform_url, agent_id))
