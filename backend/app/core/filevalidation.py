from __future__ import annotations

import os
import re

from app.core.config import get_settings

settings = get_settings()

MAGIC_BYTE_MAP: dict[str, list[str]] = {
    "mp4": ["ftyp", "0000002066747970"],
    "webm": ["1a45dfa3"],
    "mov": ["ftypqt", "ftyp"],
    "mp3": ["494433", "fff3", "fffb"],
    "wav": ["52494646"],
    "ogg": ["4f676753"],
    "jpg": ["ffd8ff"],
    "jpeg": ["ffd8ff"],
    "png": ["89504e47"],
    "webp": ["52494646"],
    "srt": None,
    "vtt": ["576542565454"],
    "json": ["7b", "5b"],
    "txt": None,
    "zip": ["504b0304"],
    "ttf": ["00010000"],
    "otf": ["4f54544f"],
}

EXTENSION_ALIAS = {
    "jpeg": "jpg",
    "mpeg": "mp4",
    "m4v": "mp4",
    "aac": "mp3",
}


def sanitize_filename(name: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name[:200]


def validate_file_upload(filename: str, data: bytes, *, public: bool = False) -> dict:
    """Validate real MIME magic bytes, size, extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ext = EXTENSION_ALIAS.get(ext, ext)
    if ext not in settings.allowed_extensions_list:
        raise ValueError(f"Extension .{ext} not allowed")

    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"File exceeds {settings.max_upload_mb} MB limit")

    if not data:
        raise ValueError("Empty file")

    magic = MAGIC_BYTE_MAP.get(ext)
    if magic is not None and not public:
        head = data[:16].hex()
        if not any(m.lower() in head or head.startswith(m.lower()) for m in magic):
            raise ValueError(f"Magic bytes do not match .{ext}")

    if public:
        if not _is_image_or_text(data, ext):
            raise ValueError("Public uploads must be images or subtitle files")

    return {"extension": ext, "size": len(data), "checksum": _checksum(data)}


def _is_image_or_text(data: bytes, ext: str) -> bool:
    if ext in ("jpg", "jpeg", "png", "webp"):
        return True
    if ext in ("srt", "vtt", "txt", "json"):
        try:
            data.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    return False


def _checksum(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()
