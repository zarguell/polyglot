from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class MFASetupResponse(BaseModel):
    """Returned by GET /mfa/setup — includes the QR provisioning URI
    and newly generated backup codes."""

    secret: str
    provisioning_uri: str
    qr_data_uri: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    """Submitted by POST /mfa/verify to confirm TOTP setup."""

    secret: str = Field(
        ...,
        min_length=16,
        description="The TOTP secret (from the setup response)",
    )
    code: Annotated[
        str,
        StringConstraints(
            min_length=6,
            max_length=8,
            strip_whitespace=True,
        ),
    ] = Field(
        ...,
        description="The 6-digit TOTP code from the authenticator app",
    )
    backup_codes: list[str] = Field(
        ...,
        description="The backup codes to store (from setup response)",
    )


class MFAChallengeRequest(BaseModel):
    """Submitted by POST /mfa/challenge to complete MFA login."""

    code: Annotated[
        str,
        StringConstraints(
            min_length=6,
            max_length=12,
            strip_whitespace=True,
        ),
    ] = Field(
        ...,
        description="A 6-digit TOTP code or a backup code",
    )


class MFADisableRequest(BaseModel):
    """Submitted by POST /mfa/disable to remove MFA."""

    password: str = Field(
        ...,
        min_length=1,
        description="Current password for re-authentication",
    )


class MFAStatusResponse(BaseModel):
    """Returned by GET /mfa/status."""

    enabled: bool
    verified_at: str | None = None
    backup_codes_remaining: int = 0
