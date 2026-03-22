"""
E2E Backend Fixture - Manages the FastAPI test server lifecycle.
"""
import pytest
import time
import subprocess
import requests
import os
import signal


@pytest.fixture(scope="module")
def backend_server():
    """
    Start the FastAPI backend on a free port, wait for it to be ready,
    then yield the base URL. Cleanup stops the server after tests.
    """
    # Find a free port
    import socket
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()

    base_url = f"http://127.0.0.1:{port}"

    # Start uvicorn
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

    proc = subprocess.Popen(
        [
            'python', '-m', 'uvicorn',
            'usmsb_sdk.api.rest.main:app',
            '--host', '127.0.0.1',
            '--port', str(port),
            '--log-level', 'warning',
        ],
        cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Wait for server to be ready (max 15s)
    for _ in range(30):
        try:
            r = requests.get(f"{base_url}/api/health", timeout=1)
            if r.status_code < 500:
                break
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("Backend failed to start within 15s")

    yield base_url

    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
