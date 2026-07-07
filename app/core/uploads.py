"""Local file storage for uploaded receipts.

The frontend sends receipts as base64 data URLs and expects the backend to
store them and return a ``receiptUrl``. This saves the file under the configured
upload directory and returns a public URL. It is a drop-in stand-in for a cloud
store (e.g. Cloudinary) — swap this module's body to push to a provider instead.
"""

import base64
import binascii
import os
import re
import uuid

from app.core.config import settings

_RECEIPTS_SUBDIR = "receipts"
_DATA_URL_RE = re.compile(r"^data:(?P<mime>[^;]+);base64,(?P<data>.+)$", re.DOTALL)

_EXTENSION_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "application/pdf": ".pdf",
}


def _safe_extension(file_name: str | None, mime: str | None) -> str:
    if file_name and "." in file_name:
        ext = os.path.splitext(file_name)[1].lower()
        if len(ext) <= 6:
            return ext
    return _EXTENSION_BY_MIME.get((mime or "").lower(), ".bin")


def save_receipt(data_url_or_b64: str, file_name: str | None = None) -> str:
    """Persist a base64 (optionally data-URL) receipt and return its public URL.

    Raises ValueError if the payload is not valid base64.
    """
    mime: str | None = None
    payload = data_url_or_b64.strip()

    match = _DATA_URL_RE.match(payload)
    if match:
        mime = match.group("mime")
        payload = match.group("data")

    try:
        content = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Receipt is not valid base64 data") from exc

    receipts_dir = os.path.join(settings.upload_dir, _RECEIPTS_SUBDIR)
    os.makedirs(receipts_dir, exist_ok=True)

    ext = _safe_extension(file_name, mime)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(receipts_dir, stored_name), "wb") as handle:
        handle.write(content)

    base = settings.public_base_url.rstrip("/")
    return f"{base}/{settings.upload_dir}/{_RECEIPTS_SUBDIR}/{stored_name}"
