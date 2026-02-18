"""Run the P2P Node."""
import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from usmsb_sdk.node.decentralized_node import DecentralizedPlatform


async def main():
    """Run the P2P node."""
    config = {
        "port": 9001,
        "capabilities": ["llm", "agent_hosting", "compute", "blockchain"],
        "bootstrap_peers": [],
    }

    platform = DecentralizedPlatform(config)

    print("=" * 50)
    print("  USMSB P2P Node Starting...")
    print("=" * 50)

    success = await platform.start()

    if success:
        node_info = await platform.node.get_node_info()
        print(f"Node ID: {node_info['node_id']}")
        print(f"Status: {node_info['status']}")
        print(f"Listening on: {node_info['identity']['address']}:{node_info['identity']['port']}")
        print("=" * 50)
        print("  P2P Node is running!")
        print("  Press Ctrl+C to stop")
        print("=" * 50)

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            print("\nShutting down...")
            await platform.stop()
    else:
        print("Failed to start P2P node")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
