"""Quick test for single agent HTTP server"""
import asyncio
import sys
import os

# Path setup
demo_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(demo_dir)
usmsb_root = os.path.dirname(project_root)
sys.path.insert(0, usmsb_root)
sys.path.insert(0, os.path.join(usmsb_root, 'src'))

from usmsb_sdk.agent_sdk import AgentConfig, BaseAgent
from typing import List


class TestAgent(BaseAgent):
    """Simple test agent"""
    def __init__(self):
        config = AgentConfig(
            name="TestAgent",
            description="Test Agent",
            capabilities=[],
            skills=[],
        )
        super().__init__(config)

    async def process_task(self, task):
        return {"result": "Task processed"}


async def main():
    print("Creating agent...")
    agent = TestAgent()

    print("Initializing agent...")
    await agent.initialize()

    print(f"Agent ID: {agent.agent_id}")

    print("Starting HTTP server on port 9090...")
    try:
        await agent.start_with_http(
            host="0.0.0.0",
            port=9090,
            platform_url="http://localhost:8000",
        )
        print("✅ Agent started successfully!")

        # Wait a bit
        await asyncio.sleep(3)

        # Check health
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9090/health") as resp:
                data = await resp.json()
                print(f"Health check: {data}")

    except Exception as e:
        print(f"❌ Failed to start: {e}")

    print("\nStopping agent...")
    await agent.stop_http()
    await agent.stop()
    print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
