#!/bin/bash
set -e

echo "=========================================="
echo "  USMSB - AI Civilization New World Platform"
echo "  Full Node Startup"
echo "=========================================="

# Create necessary directories
mkdir -p /app/data /app/logs

# Set environment defaults
export NODE_ID=${NODE_ID:-"node_$(hostname)"}
export NODE_ADDRESS=${NODE_ADDRESS:-$(hostname -I | awk '{print $1}')}
export NODE_PORT=${NODE_PORT:-8080}

echo "Node ID: ${NODE_ID}"
echo "Node Address: ${NODE_ADDRESS}"
echo "Node Port: ${NODE_PORT}"

# Start Redis connection check
echo "Checking Redis connection..."
until nc -z redis 6379 2>/dev/null; do
    echo "Waiting for Redis..."
    sleep 1
done
echo "Redis is available!"

# Start nginx (frontend)
echo "Starting nginx..."
nginx

# Start the USMSB platform
echo "Starting USMSB Platform..."
cd /app

# Run database migrations if needed
python -c "from usmsb_sdk.data_management.models import init_db; init_db()" 2>/dev/null || true

# Start the REST API server
echo "Starting REST API on port 8000..."
python -m uvicorn usmsb_sdk.api.rest.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level ${LOG_LEVEL:-info} &

API_PID=$!

# Wait for API to be ready
sleep 3

# Start the P2P node
echo "Starting P2P Node on port 8080..."
python -c "
import asyncio
from usmsb_sdk.node.decentralized_node import DecentralizedPlatform

async def main():
    config = {
        'node_id': '${NODE_ID}',
        'address': '${NODE_ADDRESS}',
        'port': ${NODE_PORT},
        'bootstrap_peers': '${BOOTSTRAP_PEERS}'.split(',') if '${BOOTSTRAP_PEERS}' else [],
        'capabilities': ['llm', 'agent_hosting', 'compute', 'blockchain'],
    }
    platform = DecentralizedPlatform(config)
    await platform.start()

    # Keep running
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
" &

P2P_PID=$!

# Start the custom blockchain (if enabled)
if [ "${ENABLE_BLOCKCHAIN:-true}" = "true" ]; then
    echo "Starting Custom Blockchain on port 9000..."
    python -c "
import asyncio
from usmsb_sdk.platform.blockchain.custom_chain_adapter import CustomChainAdapter, CustomChainNetwork

async def main():
    chain = CustomChainAdapter(CustomChainNetwork.LOCAL)
    await chain.initialize({})
    await chain.start_block_production()

    # Keep running
    while True:
        await asyncio.sleep(3600)

asyncio.run(main())
" &

    CHAIN_PID=$!
fi

echo ""
echo "=========================================="
echo "  USMSB Platform is running!"
echo "=========================================="
echo "  Frontend:    http://localhost/"
echo "  API:         http://localhost:8000/"
echo "  API Docs:    http://localhost:8000/docs"
echo "  P2P Node:    http://localhost:8080/"
echo "  Blockchain:  http://localhost:9000/"
echo "=========================================="

# Handle shutdown gracefully
shutdown() {
    echo "Shutting down..."
    kill $API_PID 2>/dev/null || true
    kill $P2P_PID 2>/dev/null || true
    kill $CHAIN_PID 2>/dev/null || true
    nginx -s stop 2>/dev/null || true
    exit 0
}

trap shutdown SIGTERM SIGINT

# Wait for processes
wait
