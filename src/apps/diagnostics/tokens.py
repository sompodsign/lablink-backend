"""Signed, expiring tokens for public report access.

Tokens are HMAC-signed using Django's SECRET_KEY via ``django.core.signing``.
They embed the report's ``access_token`` UUID and carry a timestamp so they
can be rejected after ``REPORT_LINK_EXPIRY_DAYS`` days (default 30).

Usage
-----
Generate::

    signed = make_report_token(report)  # returns a URL-safe string

Verify::

    uuid_str = verify_report_token(signed)  # raises BadSignature / SignatureExpired
"""

from __future__ import annotations

from django.core import signing

_SALT = "report-public-access"
_MAX_AGE_DAYS = 3  # configurable — override via REPORT_LINK_EXPIRY_DAYS in settings


def make_report_token(report) -> str:
    """Return a signed, expiring URL token for *report*.

    The token encodes the report's ``access_token`` UUID and is valid for
    ``_MAX_AGE_DAYS`` days.
    """
    return signing.dumps(str(report.access_token), salt=_SALT)


def verify_report_token(token: str) -> str:
    """Decode and verify *token*.

    Returns the raw ``access_token`` UUID string on success.

    Raises
    ------
    django.core.signing.SignatureExpired
        If the token is older than ``_MAX_AGE_DAYS`` days.
    django.core.signing.BadSignature
        If the token has been tampered with or is malformed.
    """
    return signing.loads(token, salt=_SALT, max_age=_MAX_AGE_DAYS * 86_400)


def is_signed_token(value: str) -> bool:
    """Return True if *value* looks like a signing token (contains ``:``)."""
    return ":" in value
