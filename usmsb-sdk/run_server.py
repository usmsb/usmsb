"""Run the USMSB SDK API server."""

import sys
import os

# Clear any existing MINIMAX_API_KEY to ensure .env is used
if "MINIMAX_API_KEY" in os.environ:
    del os.environ["MINIMAX_API_KEY"]

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv(override=True)

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/server_debug.log'),
        logging.StreamHandler()
    ]
)

import uvicorn
from usmsb_sdk.api.rest.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="debug",
        timeout_keep_alive=180,
    )
