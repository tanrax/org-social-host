"""
Utility functions for Org Social Host.
"""

import hashlib
import hmac
import secrets
import time
from urllib.parse import urlencode

from django.conf import settings


def generate_vfile_token(nickname: str) -> dict:
    """
    Generate a secure vfile token for a user.

    Args:
        nickname: User's nickname

    Returns:
        dict with 'token', 'timestamp', and 'signature'
    """
    # Generate cryptographically random token (256 bits = 64 hex chars)
    token = secrets.token_hex(32)

    # Current timestamp
    timestamp = int(time.time())

    # Generate signature: HMAC-SHA256 of token:timestamp:nickname
    message = f"{token}:{timestamp}:{nickname}"
    signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return {
        "token": token,
        "timestamp": timestamp,
        "signature": signature,
    }


def verify_vfile_token(token: str, timestamp: int, signature: str, nickname: str) -> bool:
    """
    Verify a vfile token is valid and belongs to the given nickname.

    Args:
        token: Random token from vfile
        timestamp: Timestamp from vfile
        signature: Signature from vfile
        nickname: Nickname to verify against

    Returns:
        True if token is valid, False otherwise
    """
    # Regenerate signature
    message = f"{token}:{timestamp}:{nickname}"
    expected_signature = hmac.new(
        settings.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Compare signatures (constant time to prevent timing attacks)
    return hmac.compare_digest(signature, expected_signature)


def build_vfile_url(token: str, timestamp: int, signature: str) -> str:
    """
    Build a complete vfile URL from components.

    Args:
        token: Random token
        timestamp: Unix timestamp
        signature: HMAC signature

    Returns:
        Complete vfile URL
    """
    base_url = f"http://{settings.SITE_DOMAIN}/vfile"
    params = {
        "token": token,
        "ts": str(timestamp),
        "sig": signature,
    }
    return f"{base_url}?{urlencode(params)}"


def parse_vfile_url(vfile_url: str) -> dict:
    """
    Parse a vfile URL into its components.

    Args:
        vfile_url: Complete vfile URL

    Returns:
        dict with 'token', 'timestamp', 'signature' or None if invalid
    """
    from urllib.parse import parse_qs, urlparse

    try:
        parsed = urlparse(vfile_url)
        params = parse_qs(parsed.query)

        return {
            "token": params.get("token", [None])[0],
            "timestamp": int(params.get("ts", [0])[0]),
            "signature": params.get("sig", [None])[0],
        }
    except (ValueError, IndexError, KeyError):
        return None


def validate_nickname(nickname: str) -> tuple[bool, str]:
    """
    Validate a nickname meets requirements.

    Args:
        nickname: Nickname to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not nickname:
        return False, "Nickname is required"

    if len(nickname) < 3:
        return False, "Nickname must be at least 3 characters"

    if len(nickname) > 50:
        return False, "Nickname must be at most 50 characters"

    # Only alphanumeric, hyphens, and underscores
    if not all(c.isalnum() or c in "-_" for c in nickname):
        return False, "Nickname can only contain letters, numbers, hyphens, and underscores"

    return True, ""
