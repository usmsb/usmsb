"""
Global Scheduler Entry Point
"""

import uvicorn
import argparse


def main():
    parser = argparse.ArgumentParser(description="USMSB Distributed Inference - Global Scheduler")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    print(f"[Global Scheduler] Starting on {args.host}:{args.port}")

    uvicorn.run(
        "global_scheduler.api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
