from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# pyotp and qrcode are required dependencies (see ACTIVATE.md)
# import them at module level in case the user has them, with graceful fallback
try:
    import pyotp
except ImportError:
    pyotp = None  # type: ignore[assignment]

try:
    import qrcode  # noqa: F401
except ImportError:
    qrcode = None  # type: ignore[assignment]


def generate_totp_secret() -> str:
    """Generate a new base32-encoded TOTP secret."""
    if pyotp is None:
        raise ImportError("pyotp is required for TOTP MFA. Install with: pip install pyotp")
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str, issuer: str = "Polyglot") -> str:
    """Build the otpauth:// provisioning URI for a QR code."""
    if pyotp is None:
        raise ImportError("pyotp is required for TOTP MFA. Install with: pip install pyotp")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret.

    Uses valid_window=1 to accept codes from adjacent time steps
    (typically ±30s), which tolerates modest clock drift.
    """
    if pyotp is None:
        raise ImportError("pyotp is required for TOTP MFA. Install with: pip install pyotp")
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_qr_data_uri(provisioning_uri: str) -> str:
    """Generate a QR code as a base64 data URI for inline <img> display."""
    if qrcode is None:
        raise ImportError(
            "qrcode[pil] is required for QR code generation. Install with: pip install qrcode[pil]"
        )
    import base64
    import io

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"


def generate_backup_codes(count: int = 8) -> list[str]:
    """Generate a list of single-use backup codes.

    Each code is 10 characters of hex (40 bits), formatted as 2 groups of 5
    for readability (e.g. 'a1b2c-d3e4f').
    """
    codes: list[str] = []
    for _ in range(count):
        raw = secrets.token_hex(5)  # 10 hex chars
        formatted = f"{raw[:5]}-{raw[5:]}"
        codes.append(formatted)
    return codes


def hash_backup_code(code: str) -> str:
    """SHA-256 hash of a backup code for secure storage.

    The code is lowercased and stripped before hashing to allow
    case-insensitive entry during login.
    """
    normalized = code.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify_backup_code(code: str, hashes: list[str]) -> bool:
    """Check a provided code against a list of hashed backup codes.

    Returns True if the code matches any hash in the list.
    Uses constant-time comparison to prevent timing attacks.
    """
    import hmac

    target_hash = hash_backup_code(code)
    for stored_hash in hashes:
        if hmac.compare_digest(target_hash, stored_hash):
            return True
    return False
