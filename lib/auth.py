"""Password hashing + user authentication helpers.

Uses only the Python standard library (hashlib PBKDF2) so there is no
compiled dependency (e.g. bcrypt) that could fail to build on Streamlit
Community Cloud's free tier.
"""
from __future__ import annotations

import hashlib
import os
import secrets


def hash_password(password: str) -> tuple[str, str]:
    """Return (salt_hex, hash_hex) for a new password."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex(), dk.hex()


def verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return secrets.compare_digest(dk, expected)


def generate_temp_password(length: int = 10) -> str:
    """A readable-ish random password for newly created accounts."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
