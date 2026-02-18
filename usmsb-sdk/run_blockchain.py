"""Run the Custom Blockchain Node."""
import asyncio
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from usmsb_sdk.platform.blockchain.custom_chain_adapter import CustomChainAdapter, CustomChainNetwork


async def main():
    """Run the blockchain node."""
    print("=" * 50)
    print("  USMSB Custom Blockchain Node Starting...")
    print("=" * 50)

    chain = CustomChainAdapter(CustomChainNetwork.LOCAL)

    # Initialize the chain
    success = await chain.initialize({})

    if success:
        chain_info = await chain.get_chain_info()
        print(f"Network: {chain_info['network']}")
        print(f"Node ID: {chain_info['node_id']}")
        print(f"Block Height: {chain_info['block_height']}")
        print("=" * 50)

        # Start block production
        await chain.start_block_production()

        print("  Blockchain Node is running!")
        print("  Producing blocks every 2 seconds...")
        print("  Press Ctrl+C to stop")
        print("=" * 50)

        # Create a wallet for testing
        wallet = await chain.create_wallet()
        print(f"\nDemo Wallet Created:")
        print(f"  Address: {wallet['address']}")
        print(f"  Balance: {wallet['balance']} USMSB")

        # Keep running
        try:
            while True:
                await asyncio.sleep(10)
                info = await chain.get_chain_info()
                print(f"Block: {info['block_height']} | Pending TXs: {info['pending_transactions']}")
        except KeyboardInterrupt:
            print("\nShutting down...")
            await chain.stop_block_production()
            await chain.shutdown()
    else:
        print("Failed to start blockchain node")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
