"""Unit tests for TOTP MFA service functions.

These tests exercise the pure-logic functions in
``app.components.totp_mfa.service`` without requiring a database
or FastAPI request context.

To run after activation:
    pytest tests/unit/test_totp_mfa.py -v
"""

from __future__ import annotations

import pytest

# After activation, the module lives at app.components.totp_mfa.service.
# During template development, we import from the template source.
try:
    from app.components.totp_mfa.service import (  # type: ignore[import-untyped]
        generate_backup_codes,
        generate_totp_secret,
        get_totp_uri,
        hash_backup_code,
        verify_backup_code,
        verify_totp,
    )
except ImportError:
    import sys
    from pathlib import Path

    template_src = (
        Path(__file__).resolve().parent.parent.parent
        / "boilerplate"
        / "templates"
        / "totp_mfa"
        / "app"
    )
    sys.path.insert(0, str(template_src.parent.parent))
    from app.components.totp_mfa.service import (  # type: ignore[import-untyped]  # noqa: E402
        generate_backup_codes,
        generate_totp_secret,
        get_totp_uri,
        hash_backup_code,
        verify_backup_code,
        verify_totp,
    )


class TestTOTPSecretGeneration:
    """Tests for generate_totp_secret()."""

    def test_generates_base32_string(self) -> None:
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) >= 16  # pyotp.random_base32() is typically 32 chars

    def test_generates_unique_secrets(self) -> None:
        secrets = {generate_totp_secret() for _ in range(10)}
        assert len(secrets) == 10  # all unique

    def test_secret_is_valid_base32(self) -> None:
        """Generated secret should only contain base32 chars (A-Z, 2-7)."""
        import re

        secret = generate_totp_secret()
        assert re.fullmatch(r"[A-Z2-7]+", secret), f"Invalid base32: {secret}"


class TestTOTPProvisioningURI:
    """Tests for get_totp_uri()."""

    def test_uri_format(self) -> None:
        uri = get_totp_uri("JBSWY3DPEHPK3PXP", "test@example.com", issuer="TestApp")
        assert uri.startswith("otpauth://totp/")
        assert "TestApp:" in uri  # email may be URL-encoded: test%40example.com
        assert "secret=JBSWY3DPEHPK3PXP" in uri
        assert "issuer=TestApp" in uri

    def test_uri_uses_custom_issuer(self) -> None:
        uri = get_totp_uri("ABCDEFGH234567", "user@corp.com", issuer="MyApp")
        assert "issuer=MyApp" in uri
        assert "MyApp:" in uri  # email may be URL-encoded: user%40corp.com


class TestTOTPVerification:
    """Tests for verify_totp()."""

    def test_verifies_correct_code(self) -> None:

        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        code = totp.now()

        assert verify_totp(secret, code) is True

    def test_rejects_wrong_code(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False

    def test_accepts_adjacent_window(self) -> None:
        """verify_totp with valid_window=1 should accept ±1 time step."""
        import pyotp

        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        # Get current code
        now = int(__import__("time").time())
        current_code = totp.at(now)
        assert verify_totp(secret, current_code) is True

        # Previous window should also be accepted (valid_window=1)
        prev_code = totp.at(now - 30)
        assert verify_totp(secret, prev_code) is True

        # Next window should also be accepted
        next_code = totp.at(now + 30)
        assert verify_totp(secret, next_code) is True

        # Far past should be rejected
        old_code = totp.at(now - 120)
        assert verify_totp(secret, old_code) is False

    def test_empty_code_rejected(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "") is False


class TestBackupCodes:
    """Tests for generate_backup_codes()."""

    def test_generates_requested_count(self) -> None:
        codes = generate_backup_codes(8)
        assert len(codes) == 8

    def test_generates_default_count(self) -> None:
        codes = generate_backup_codes()
        assert len(codes) == 8

    def test_format_is_hyphenated_hex(self) -> None:
        import re

        codes = generate_backup_codes(20)
        for code in codes:
            assert re.fullmatch(r"[a-f0-9]{5}-[a-f0-9]{5}", code), f"Bad format: {code}"

    def test_all_unique(self) -> None:
        codes = generate_backup_codes(50)
        assert len(set(codes)) == 50

    def test_custom_count(self) -> None:
        codes = generate_backup_codes(12)
        assert len(codes) == 12
        assert len(set(codes)) == 12


class TestBackupCodeHashing:
    """Tests for hash_backup_code()."""

    def test_produces_sha256_hex(self) -> None:
        result = hash_backup_code("abc12-def34")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex digest
        # hex-only
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_codes_produce_different_hashes(self) -> None:
        h1 = hash_backup_code("abc12-def34")
        h2 = hash_backup_code("abc12-def35")
        assert h1 != h2

    def test_same_code_produces_same_hash(self) -> None:
        h1 = hash_backup_code("abc12-def34")
        h2 = hash_backup_code("abc12-def34")
        assert h1 == h2

    def test_case_insensitive(self) -> None:
        h1 = hash_backup_code("ABC12-DEF34")
        h2 = hash_backup_code("abc12-def34")
        assert h1 == h2

    def test_whitespace_insensitive(self) -> None:
        h1 = hash_backup_code("  abc12-def34  ")
        h2 = hash_backup_code("abc12-def34")
        assert h1 == h2


class TestBackupCodeVerification:
    """Tests for verify_backup_code()."""

    def test_finds_matching_code(self) -> None:
        codes = generate_backup_codes(8)
        hashes = [hash_backup_code(c) for c in codes]
        assert verify_backup_code(codes[3], hashes) is True

    def test_rejects_nonexistent_code(self) -> None:
        codes = generate_backup_codes(8)
        hashes = [hash_backup_code(c) for c in codes]
        assert verify_backup_code("fffff-fffff", hashes) is False

    def test_case_insensitive_match(self) -> None:
        codes = generate_backup_codes(8)
        hashes = [hash_backup_code(c) for c in codes]
        assert verify_backup_code(codes[0].upper(), hashes) is True

    def test_whitespace_insensitive_match(self) -> None:
        codes = generate_backup_codes(8)
        hashes = [hash_backup_code(c) for c in codes]
        assert verify_backup_code(f"  {codes[0]}  ", hashes) is True

    def test_empty_hashes_rejects_anything(self) -> None:
        assert verify_backup_code("abc12-def34", []) is False

    def test_code_already_used_fails(self) -> None:
        """Once a code is removed from hashes, it should not verify."""
        codes = generate_backup_codes(8)
        hashes = [hash_backup_code(c) for c in codes]

        # Use code at index 2
        used_code = codes[2]
        used_hash = hash_backup_code(used_code)

        assert verify_backup_code(used_code, hashes) is True

        # Remove it (simulate consumption)
        hashes.remove(used_hash)

        # Now it should fail
        assert verify_backup_code(used_code, hashes) is False


class TestSchemaValidation:
    """Tests for Pydantic schemas in app.components.totp_mfa.schemas."""

    def test_verify_request_valid(self) -> None:
        try:
            from app.components.totp_mfa.schemas import (
                MFAVerifyRequest,
            )
        except ImportError:
            pytest.skip("Schemas not importable (template not activated)")

        req = MFAVerifyRequest(
            secret="JBSWY3DPEHPK3PXP",
            code="123456",
            backup_codes=["abcd1-efgh2"],
        )
        assert req.secret == "JBSWY3DPEHPK3PXP"
        assert req.code == "123456"

    def test_verify_request_code_too_short(self) -> None:
        try:
            from app.components.totp_mfa.schemas import (
                MFAVerifyRequest,
            )
        except ImportError:
            pytest.skip("Schemas not importable (template not activated)")

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MFAVerifyRequest(
                secret="JBSWY3DPEHPK3PXP",
                code="123",  # too short
                backup_codes=["abcd1-efgh2"],
            )

    def test_challenge_request_valid(self) -> None:
        try:
            from app.components.totp_mfa.schemas import (
                MFAChallengeRequest,
            )
        except ImportError:
            pytest.skip("Schemas not importable (template not activated)")

        req = MFAChallengeRequest(code="123456")
        assert req.code == "123456"

        # Backup code also valid
        req2 = MFAChallengeRequest(code="abc12-def34")
        assert req2.code == "abc12-def34"
