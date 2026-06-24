from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime


def hash_token(token: str) -> str:
    """SHA-256 hash of a token string."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_session_token() -> str:
    """Cryptographically random session token."""
    return secrets.token_urlsafe(48)


def compute_signature(payload: str, key: str) -> str:
    """HMAC-SHA256 signature for webhook verification."""
    return hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_signature(payload: str, key: str, signature: str) -> bool:
    """Constant-time HMAC verification."""
    expected = compute_signature(payload, key)
    return hmac.compare_digest(expected, signature)


def generate_nonce() -> str:
    """CSP nonce."""
    return os.urandom(16).hex()


def utcnow() -> datetime:
    return datetime.now(UTC)


def utcfromtimestamp(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)
