import time

REQUEST_LOG = {}
MAX_REQUESTS_PER_MINUTE = 10

def check_role_permission(user_role: str, required_role: str) -> bool:
    """Ensures user possesses proper permissions for requested operation."""
    hierarchy = {"admin": 3, "manager": 2, "customer": 1}
    user_level = hierarchy.get(user_role, 0)
    required_level = hierarchy.get(required_role, 0)
    return user_level >= required_level

def is_rate_limited(user_id: str) -> bool:
    """Prevents brute-force or API flooding attacks."""
    current_time = time.time()
    window_start = current_time - 60

    if user_id not in REQUEST_LOG:
        REQUEST_LOG[user_id] = []

    REQUEST_LOG[user_id] = [t for t in REQUEST_LOG[user_id] if t > window_start]

    if len(REQUEST_LOG[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return True

    REQUEST_LOG[user_id].append(current_time)
    return False