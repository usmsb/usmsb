"""
软件开发协作 Demo - 统一入口

使用真正的 Agent SDK，每个 Agent 在独立进程中运行：
- 自动注册到平台
- 自动心跳
- 自动取消注册
- 内置 HTTP 服务器
- agent_id 持久化
"""

import asyncio
import os
import sys
import json
import subprocess
import signal
import time
from pathlib import Path

# 添加项目路径
demo_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(demo_dir)
usmsb_root = os.path.dirname(project_root)
sys.path.insert(0, usmsb_root)
sys.path.insert(0, os.path.join(usmsb_root, 'src'))

from usmsb_sdk.agent_sdk import (
    AgentConfig,
    CapabilityDefinition,
    ProtocolType,
    ProtocolConfig,
)

# ============================================================================
# 配置
# ============================================================================

AGENT_IDS_FILE = Path(__file__).parent / "agent_ids.json"

# Agent 端口配置
AGENT_PORTS = {
    "ProductOwner": {"http": 9081, "p2p": 19081},
    "Architect": {"http": 9082, "p2p": 19082},
    "Developer": {"http": 9083, "p2p": 19083},
    "Reviewer": {"http": 9084, "p2p": 19084},
    "DevOps": {"http": 9085, "p2p": 19085},
}

# Agent 配置
AGENT_CONFIG = [
    {
        "name": "ProductOwner",
        "role": "产品经理",
        "capabilities": ["requirement_analysis", "prioritization", "acceptance_testing"],
    },
    {
        "name": "Architect",
        "role": "架构师",
        "capabilities": ["architecture_design", "tech_selection", "api_design"],
    },
    {
        "name": "Developer",
        "role": "开发者",
        "capabilities": ["coding", "testing", "debugging"],
    },
    {
        "name": "Reviewer",
        "role": "代码审查",
        "capabilities": ["code_review", "security_audit"],
    },
    {
        "name": "DevOps",
        "role": "运维",
        "capabilities": ["ci_cd", "deployment", "monitoring"],
    },
]


# ============================================================================
# 持久化逻辑
# ============================================================================

def load_agent_ids() -> dict:
    """加载持久化的 agent_id"""
    if AGENT_IDS_FILE.exists():
        try:
            with open(AGENT_IDS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_agent_ids(agent_ids: dict):
    """保存 agent_id 到文件"""
    with open(AGENT_IDS_FILE, 'w') as f:
        json.dump(agent_ids, f, indent=2)


# ============================================================================
# 主函数
# ============================================================================

async def main():
    print("\n" + "=" * 50)
    print("  软件开发协作 Demo")
    print("  Agent SDK - 多进程版本")
    print("=" * 50)

    # 加载持久化的 agent_ids
    agent_ids = load_agent_ids()
    print(f"\n📁 已加载 {len(agent_ids)} 个持久化的 Agent ID")

    # 为每个 Agent 生成或使用已保存的 ID
    agent_id_map = {}
    for cfg in AGENT_CONFIG:
        name = cfg["name"]
        saved_id = agent_ids.get(name)
        agent_id_map[name] = saved_id

    # 保存 agent_ids（确保文件存在）
    save_agent_ids(agent_id_map)
    print(f"💾 Agent ID 已保存到 {AGENT_IDS_FILE}")

    # 启动所有 Agent 进程
    print("\n🚀 启动 Agent 进程...")
    processes = {}

    script_path = os.path.abspath(__file__).replace("\\", "/")
    agent_server_script = script_path.replace("demo_runner.py", "agent_server.py")

    # 用于存储新注册的agent_id
    new_agent_ids = {}

    for cfg in AGENT_CONFIG:
        name = cfg["name"]
        ports = AGENT_PORTS[name]
        port = ports["http"]
        agent_id = agent_id_map.get(name)

        # 构建命令
        cmd = [
            sys.executable,
            agent_server_script,
            name,
            str(port),
            "http://localhost:8000",
        ]
        if agent_id:
            cmd.append(agent_id)

        print(f"  📦 启动 {name} (端口: {port})...")

        # 启动子进程
        try:
            # 使用 PIPE 来捕获输出
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            processes[name] = {"process": proc, "agent_id": None}

            # 如果没有指定agent_id，设置为None让它自动生成
            if not agent_id:
                new_agent_ids[name] = None

            print(f"      ✅ {name} 进程已启动 (PID: {proc.pid})")
        except Exception as e:
            print(f"      ❌ {name} 启动失败: {e}")

    # 等待所有 Agent 启动
    print("\n⏳ 等待 Agent 启动完成...")
    await asyncio.sleep(5)

    # 测试平台 API
    print("\n🧪 测试平台 API...")
    import aiohttp

    async with aiohttp.ClientSession() as session:
        # 1. 获取所有 Agent
        try:
            async with session.get("http://localhost:8000/agents") as resp:
                data = await resp.json()
                print(f"  ✅ GET /agents: {len(data)} 个 agent")
        except Exception as e:
            print(f"  ❌ GET /agents 失败: {e}")

        # 2. 发现在线 Agent
        try:
            async with session.get("http://localhost:8000/agents/discover?limit=10") as resp:
                data = await resp.json()
                print(f"  ✅ GET /agents/discover: {len(data)} 个在线 agent")
        except Exception as e:
            print(f"  ❌ GET /agents/discover 失败: {e}")

        # 3. 测试每个 Agent 的心跳
        for name, proc_info in processes.items():
            agent_id = agent_id_map.get(name) or new_agent_ids.get(name)
            if agent_id:
                try:
                    async with session.post(f"http://localhost:8000/agents/{agent_id}/heartbeat") as resp:
                        data = await resp.json()
                        status = data.get('status', 'N/A')
                        print(f"  ✅ POST /agents/{name}/heartbeat: {status}")
                except Exception as e:
                    print(f"  ❌ POST /agents/{name}/heartbeat 失败: {e}")

    print("\n" + "=" * 50)
    print("  所有 Agent 运行中...")
    print("=" * 50)
    print("\n按 Ctrl+C 停止所有 Agent\n")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass

    # 停止所有 Agent 进程
    print("\n🛑 停止所有 Agent 进程...")
    for name, proc_info in processes.items():
        proc = proc_info["process"]
        try:
            proc.terminate()
            proc.wait(timeout=5)
            print(f"  ✅ {name} 已停止")
        except subprocess.TimeoutExpired:
            proc.kill()
            print(f"  ⚠️ {name} 强制终止")
        except Exception as e:
            print(f"  ❌ {name} 停止失败: {e}")

    print("\n✅ Demo 完成!\n")


if __name__ == "__main__":
    asyncio.run(main())
