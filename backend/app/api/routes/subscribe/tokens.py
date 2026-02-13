"""
PATH: backend/app/api/routes/subscribe/tokens.py
PURPOSE: Secure token generation/verification for unsubscribe links
"""

import os
import hashlib
import base64

# Secret for generating unsubscribe tokens
UNSUBSCRIBE_SECRET = os.getenv("SECRET_KEY", "fse-research-secret-2025")


def generate_unsubscribe_token(email: str) -> str:
    """Generate a secure token for unsubscribe links."""
    data = f"{email.lower()}:{UNSUBSCRIBE_SECRET}"
    hash_bytes = hashlib.sha256(data.encode()).digest()
    return base64.urlsafe_b64encode(hash_bytes[:16]).decode().rstrip("=")


def verify_unsubscribe_token(email: str, token: str) -> bool:
    """Verify that an unsubscribe token is valid for the given email."""
    expected_token = generate_unsubscribe_token(email)
    return token == expected_token


def get_unsubscribe_url(email: str) -> str:
    """Generate the full unsubscribe URL for an email."""
    token = generate_unsubscribe_token(email)
    encoded_email = base64.urlsafe_b64encode(email.lower().encode()).decode().rstrip("=")
    return f"https://research.finsoeasy.com/unsubscribe?e={encoded_email}&t={token}"
