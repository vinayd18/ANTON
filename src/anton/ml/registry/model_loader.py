# -*- coding: utf-8 -*-
"""Secure checkpoint loader and weight inspection engine for ANTON.

Guarantees:
1. Integrity verification via SHA-256 checksums.
2. Safe inspection of weights and architectures without arbitrary code execution.
3. Immutability safeguards preventing accidental overwriting or in-place modification
   of pretrained checkpoints.
4. Framework-agnostic header and format verification (PyTorch, HDF5, Safetensors, ONNX, Joblib).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from anton.ml.registry.model_metadata import CheckpointInfo


@dataclass
class CheckpointInspectionResult:
    """Safe inspection metadata for a model checkpoint."""

    file_path: str
    filename: str
    file_size_bytes: int
    sha256_hash: str
    format: str  # pytorch_zip, pytorch_legacy, hdf5, safetensors, onnx, joblib_pickle, unknown
    is_valid: bool
    is_read_only: bool
    detected_framework: str
    tensor_shapes: Dict[str, List[int]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    security_warnings: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


class CheckpointSecurityError(Exception):
    """Raised when a checkpoint fails security or integrity verification."""
    pass


class ReadOnlyWeightViolationError(Exception):
    """Raised when an operation attempts to overwrite or mutate immutable weights."""
    pass


class ModelLoader:
    """Secure model checkpoint loader and inspector for ANTON Model Registry."""

    # Known magic bytes
    HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
    ZIP_MAGIC = b"PK\x03\x04"
    GZIP_MAGIC = b"\x1f\x8b"
    PICKLE_PROTO_BYTES = [b"\x80\x02", b"\x80\x03", b"\x80\x04", b"\x80\x05"]

    # In-memory inspection cache keyed by (resolved_path, size_bytes, mtime)
    _inspection_cache: Dict[Tuple[str, int, float], CheckpointInspectionResult] = {}

    @classmethod
    def compute_sha256(cls, filepath: Union[str, Path], chunk_size: int = 131072) -> str:
        """Compute the SHA-256 hash of a file using an optimized 128KB chunk size."""
        p = Path(filepath)
        if not p.is_file():
            raise FileNotFoundError(f"Checkpoint file not found: {filepath}")

        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest().lower()

    @classmethod
    def detect_format(cls, filepath: Union[str, Path]) -> Tuple[str, str]:
        """Detect checkpoint format and framework by inspecting magic bytes and extension.

        Returns:
            Tuple[format, framework]
        """
        p = Path(filepath)
        if not p.is_file():
            return "not_found", "unknown"

        with open(p, "rb") as f:
            header = f.read(16)

        ext = p.suffix.lower()

        # Check HDF5
        if header.startswith(cls.HDF5_MAGIC) or ext in [".h5", ".hdf5"]:
            if header.startswith(cls.HDF5_MAGIC):
                return "hdf5", "Keras/TensorFlow"
            return "hdf5_unverified_header", "Keras/TensorFlow"

        # Check Zip (PyTorch v1.6+ or Safetensors / SavedModel)
        if header.startswith(cls.ZIP_MAGIC):
            # Check if it's a PyTorch zip archive
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    namelist = zf.namelist()
                    if any("archive/data.pkl" in name or "data.pkl" in name for name in namelist):
                        return "pytorch_zip", "PyTorch"
                    if any("saved_model.pb" in name for name in namelist):
                        return "tf_saved_model_zip", "TensorFlow"
            except Exception:
                pass
            return "zip_archive", "PyTorch"

        # Check Safetensors
        if ext == ".safetensors" and len(header) >= 8:
            try:
                header_len = struct.unpack("<Q", header[:8])[0]
                if 0 < header_len < 100 * 1024 * 1024:
                    return "safetensors", "Safetensors (HuggingFace)"
            except Exception:
                pass

        # Check PyTorch legacy pickle
        if any(header.startswith(pb) for pb in cls.PICKLE_PROTO_BYTES) or ext in [".pt", ".pth"]:
            return "pytorch_legacy", "PyTorch"

        # Check Joblib / Gzip Pickle
        if header.startswith(cls.GZIP_MAGIC) or ext in [".joblib", ".pkl", ".pickle"]:
            return "joblib_pickle", "Scikit-Learn/Joblib"

        # Check ONNX
        if ext == ".onnx":
            return "onnx", "ONNX"

        return "unknown", "unknown"

    @classmethod
    def inspect_checkpoint(cls, filepath: Union[str, Path], use_cache: bool = True) -> CheckpointInspectionResult:
        """Safely inspect a checkpoint file without executing untrusted code."""
        p = Path(filepath)
        if not p.is_file():
            return CheckpointInspectionResult(
                file_path=str(p),
                filename=p.name,
                file_size_bytes=0,
                sha256_hash="",
                format="not_found",
                is_valid=False,
                is_read_only=False,
                detected_framework="unknown",
                error_message=f"File not found: {p}",
            )

        stat_info = p.stat()
        cache_key = (str(p.resolve()), stat_info.st_size, stat_info.st_mtime)
        if use_cache and cache_key in cls._inspection_cache:
            return cls._inspection_cache[cache_key]

        file_size = stat_info.st_size
        sha256_hash = cls.compute_sha256(p)
        fmt, framework = cls.detect_format(p)
        warnings: List[str] = []
        tensor_shapes: Dict[str, List[int]] = {}
        metadata: Dict[str, Any] = {}
        is_valid = True

        # Check read-only permission status
        is_read_only = not (p.stat().st_mode & stat.S_IWUSR)

        # Inspect based on format
        if fmt == "pytorch_zip":
            try:
                with zipfile.ZipFile(p, "r") as zf:
                    entries = zf.infolist()
                    metadata["zip_entries_count"] = len(entries)
                    metadata["zip_filenames"] = [e.filename for e in entries[:25]]
                    # Extract tensor keys from entry names if present
                    for e in entries:
                        if "/data/" in e.filename or e.filename.endswith(".storage"):
                            tensor_shapes[e.filename] = [e.file_size]
            except Exception as e:
                warnings.append(f"Zip extraction warning: {e}")

        elif fmt == "hdf5":
            try:
                import h5py
                with h5py.File(p, "r") as h5_file:
                    def visitor(name, obj):
                        if isinstance(obj, h5py.Dataset):
                            tensor_shapes[name] = list(obj.shape)
                    h5_file.visititems(visitor)
                    metadata["h5_attrs"] = {k: str(v) for k, v in list(h5_file.attrs.items())[:10]}
            except ImportError:
                metadata["inspection_note"] = "h5py not installed; verified via valid HDF5 magic bytes"
            except Exception as e:
                warnings.append(f"HDF5 structure inspection warning: {e}")

        elif fmt == "safetensors":
            try:
                with open(p, "rb") as f:
                    header_len = struct.unpack("<Q", f.read(8))[0]
                    header_json = json.loads(f.read(header_len).decode("utf-8"))
                    for k, v in header_json.items():
                        if isinstance(v, dict) and "shape" in v:
                            tensor_shapes[k] = v["shape"]
                    metadata["safetensors_header"] = {k: v for k, v in header_json.items() if k == "__metadata__"}
            except Exception as e:
                warnings.append(f"Safetensors header reading warning: {e}")

        elif fmt == "pytorch_legacy":
            warnings.append(
                "Legacy PyTorch pickle format detected. Automatic unpickling skipped to prevent arbitrary code execution."
            )
            metadata["inspection_note"] = "PyTorch legacy pickle verified via header; use weights_only=True during manual execution"

        result = CheckpointInspectionResult(
            file_path=str(p.resolve()),
            filename=p.name,
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            format=fmt,
            is_valid=is_valid,
            is_read_only=is_read_only,
            detected_framework=framework,
            tensor_shapes=tensor_shapes,
            metadata=metadata,
            security_warnings=warnings,
        )
        if use_cache:
            cls._inspection_cache[cache_key] = result
        return result

    @classmethod
    def set_immutable(cls, filepath: Union[str, Path]) -> None:
        """Lock file permissions to read-only to prevent accidental modification or overwriting."""
        p = Path(filepath)
        if not p.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")
        # Remove write permissions for user, group, and others
        current_mode = p.stat().st_mode
        read_only_mode = current_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        os.chmod(p, read_only_mode)

    @classmethod
    def create_safe_working_copy(
        cls,
        source_path: Union[str, Path],
        target_dir: Union[str, Path],
        target_name: Optional[str] = None,
    ) -> Path:
        """Create a writable isolated copy of a checkpoint in a working directory.

        Guarantees that the original checkpoint remains completely untouched and immutable.
        """
        src = Path(source_path)
        if not src.is_file():
            raise FileNotFoundError(f"Source checkpoint not found: {source_path}")

        dst_dir = Path(target_dir)
        dst_dir.mkdir(parents=True, exist_ok=True)

        name = target_name or src.name
        dst = dst_dir / name

        shutil.copy2(src, dst)

        # Ensure the copied working file is writable for the user's manual fine-tuning workspace
        os.chmod(dst, dst.stat().st_mode | stat.S_IWUSR)
        return dst

    @classmethod
    def verify_checkpoint_info(
        cls,
        checkpoint_info: CheckpointInfo,
        strict_sha256: bool = True,
    ) -> Tuple[bool, List[str]]:
        """Verify a registered CheckpointInfo against physical file on disk."""
        errors: List[str] = []
        if not checkpoint_info.file_path:
            return False, ["Checkpoint file_path is not defined."]

        p = Path(checkpoint_info.file_path)
        if not p.is_file():
            return False, [f"Checkpoint file does not exist at path: {checkpoint_info.file_path}"]

        # Check size if specified
        if checkpoint_info.file_size_bytes > 0:
            actual_size = p.stat().st_size
            if actual_size != checkpoint_info.file_size_bytes:
                errors.append(
                    f"File size mismatch: expected {checkpoint_info.file_size_bytes} bytes, got {actual_size} bytes."
                )

        # Check SHA-256 if specified
        if checkpoint_info.sha256_checksum:
            actual_hash = cls.compute_sha256(p)
            expected_hash = checkpoint_info.sha256_checksum.lower().strip()
            if actual_hash != expected_hash:
                errors.append(
                    f"SHA-256 mismatch: expected {expected_hash}, calculated {actual_hash}."
                )
        elif strict_sha256:
            errors.append("No SHA-256 checksum recorded for verification.")

        return len(errors) == 0, errors

