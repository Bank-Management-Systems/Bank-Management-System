import os
import jwt
import hashlib
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("DB_SECRET_KEY", "default_secure_bank_key_2026")
TOKEN_EXPIRATION_HOURS = 2

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256 for secure DB storage."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies user login password against stored hash."""
    return hash_password(plain_password) == hashed_password

def generate_session_token(user_id: str, role: str) -> str:
    """Generates a signed JWT session token."""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")