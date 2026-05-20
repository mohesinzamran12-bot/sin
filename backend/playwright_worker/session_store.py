"""Encrypted storage helpers for browser session cookies."""
import base64
import json
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet() -> Fernet:
    """Derive a Fernet key from the hex-encoded BROWSER_SESSION_ENCRYPTION_KEY."""
    raw = bytes.fromhex(settings.BROWSER_SESSION_ENCRYPTION_KEY)
    # Fernet requires exactly 32 bytes, URL-safe base64 encoded
    key = base64.urlsafe_b64encode(raw[:32])
    return Fernet(key)


def encrypt_cookies(cookies: list[dict]) -> bytes:
    """Serialize and encrypt a list of cookie dicts."""
    f = _get_fernet()
    plaintext = json.dumps(cookies).encode()
    return f.encrypt(plaintext)


def decrypt_cookies(encrypted: bytes) -> list[dict]:
    """Decrypt and deserialize cookie bytes back to a list of dicts."""
    f = _get_fernet()
    plaintext = f.decrypt(encrypted)
    return json.loads(plaintext.decode())
