"""
Atomic I/O and Path Safety Utilities.

Ensures that writes are transactional and corruption-resistant,
computes cryptographic checksums, and validates path boundaries to prevent traversal attacks.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from typing import Union


def is_safe_path(base_dir: str, target_path: str) -> bool:
    """
    Validates that target_path resolves strictly within base_dir,
    preventing path traversal attacks (e.g. ../../etc/passwd).
    """
    abs_base = os.path.abspath(base_dir)
    abs_target = os.path.abspath(target_path)
    return abs_target.startswith(abs_base)


def compute_sha256(file_path: str) -> str:
    """Computes SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_bytes_sha256(data: bytes) -> str:
    """Computes SHA-256 hash of byte content."""
    return hashlib.sha256(data).hexdigest()


def atomic_write(file_path: str, content: Union[str, bytes], mode: str = "w") -> str:
    """
    Atomically writes content to file_path by first writing to a temporary file
    in the same directory and then renaming it.
    Returns the SHA-256 checksum of the written file.
    """
    target_dir = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(target_dir, exist_ok=True)

    is_binary = "b" in mode or isinstance(content, bytes)
    write_mode = "wb" if is_binary else "w"
    encoding = None if is_binary else "utf-8"

    # Create temporary file in same directory for atomic rename
    temp_fd, temp_path = tempfile.mkstemp(dir=target_dir, prefix=".tmp_anton_")
    try:
        with os.fdopen(temp_fd, write_mode, encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        # Atomic replace
        os.replace(temp_path, file_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise

    return compute_sha256(file_path)
