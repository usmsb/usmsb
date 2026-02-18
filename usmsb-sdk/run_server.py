"""Run the USMSB SDK API server."""
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import uvicorn
from usmsb_sdk.api.rest.main import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
