"""Health check - always strict (the endpoint is implemented in the template)."""
from config import call


def test_health_returns_ok():
    r = call("GET", "/api/health")
    assert r.status_code == 200, f"API not healthy: HTTP {r.status_code}"
    body = r.json()
    assert body.get("status") == "ok"
