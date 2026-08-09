"""Evidence storage with optional AES-256 encryption."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from app.core.config import get_settings

logger = logging.getLogger("app.services.evidence")

_CIPHER_KEY = None


def _get_key() -> bytes:
    global _CIPHER_KEY
    if _CIPHER_KEY is None:
        settings = get_settings()
        digest = __import__("hashlib").sha256(settings.secret_key).digest()
        _CIPHER_KEY = digest
    return _CIPHER_KEY


def _encrypt(data: bytes) -> bytes:
    from cryptography.hazmat.primitives import padding

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(_get_key()), modes.CBC(iv))
    encryptor = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    return iv + encryptor.update(padded) + encryptor.finalize()


def save_evidence(
    camera_id: int,
    violation_id: str,
    frame_bytes: bytes,
    mime_type: str = "image/jpeg",
    kind: str = "frame",
) -> dict[str, object]:
    """Persist an evidence frame (optionally encrypted) and return metadata."""
    settings = get_settings()
    evidence_dir = settings.EVIDENCE_DIR
    os.makedirs(evidence_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"violation_{violation_id}_{ts}.{_ext_for(mime_type)}"
    path = os.path.join(evidence_dir, filename)

    encrypted = False
    payload = frame_bytes
    if settings.ENCRYPT_EVIDENCE:
        payload = _encrypt(payload)
        encrypted = True

    with open(path, "wb") as handle:
        handle.write(payload)

    return {
        "path": path,
        "filename": filename,
        "mime_type": mime_type,
        "encrypted": encrypted,
        "kind": kind,
        "camera_id": camera_id,
        "violation_id": violation_id,
    }


def _ext_for(mime_type: str) -> str:
    return "jpg" if "jpeg" in mime_type or mime_type == "image/jpg" else mime_type.split("/")[-1]
