"""
Node Executor Entry Point
"""

import asyncio
import argparse

from .executor import NodeExecutor
from .gpu_monitor import GPUMonitor
from .model_manager import ModelManager
from .vllm_engine import VLLMEngine
from shared.llm_telemetry_contract import load_invocation_recorder_from_factory


async def main():
    parser = argparse.ArgumentParser(description="USMSB Node Executor")
    parser.add_argument("--node-id", required=True, help="Node ID")
    parser.add_argument("--scheduler-url", default="http://localhost:8000", help="Global Scheduler URL")
    parser.add_argument("--port", type=int, default=8080, help="Executor HTTP port")
    parser.add_argument("--gpu-count", type=int, help="GPU count (auto-detect if not set)")
    args = parser.parse_args()

    # Detect GPU
    gpu_monitor = GPUMonitor()
    gpu_info = gpu_monitor.get_gpu_info()

    node_id = args.node_id
    gpu_count = args.gpu_count or gpu_info["gpu_count"]
    gpu_type = gpu_info["gpu_type"]
    total_vram = gpu_info["total_vram_gb"]

    print(f"[NodeExecutor] Starting node: {node_id}")
    print(f"               GPUs: {gpu_count}x {gpu_type}")
    print(f"               Total VRAM: {total_vram}GB")

    # Initialize components
    invocation_recorder = load_invocation_recorder_from_factory()
    vllm_engine = VLLMEngine(invocation_recorder=invocation_recorder)
    model_manager = ModelManager(vllm_engine, total_vram, gpu_count)
    executor = NodeExecutor(
        node_id=node_id,
        scheduler_url=args.scheduler_url,
        port=args.port,
        gpu_count=gpu_count,
        gpu_type=gpu_type,
        total_vram_gb=total_vram,
        vllm_engine=vllm_engine,
        model_manager=model_manager,
        gpu_monitor=gpu_monitor
    )

    # Start
    await executor.start()


if __name__ == "__main__":
    asyncio.run(main())
