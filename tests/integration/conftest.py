import os
import subprocess
import time
import pytest
import requests
from config import BASE_URL

@pytest.fixture(scope="session", autouse=True)
def ensure_server_running():
    """Ensure the backend API server is running before executing any integration tests."""
    healthy = False
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=1)
        if r.status_code == 200:
            healthy = True
    except Exception:
        pass

    proc = None
    if not healthy:
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        server_bin = os.path.join(root_dir, "backend", "bank_server")
        env = os.environ.copy()
        proc = subprocess.Popen([server_bin], cwd=root_dir, env=env)
        with open("/tmp/server.pid", "w") as f:
            f.write(str(proc.pid))

        for _ in range(30):
            try:
                r = requests.get(f"{BASE_URL}/api/health", timeout=1)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if not healthy:
            raise RuntimeError(f"Could not connect to backend server at {BASE_URL}")

    yield

    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            pass
