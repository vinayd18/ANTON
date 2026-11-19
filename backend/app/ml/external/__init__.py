# -*- coding: utf-8 -*-
"""Adapter module providing paths to authoritative external checkpoints in src/anton/ml/external."""

from pathlib import Path

EXTERNAL_MODELS_DIR = Path(__file__).resolve().parents[4] / "src" / "anton" / "ml" / "external"

def get_checkpoint_path(relative_path: str) -> Path:
    """Resolve checkpoint path against authoritative storage in src/anton/ml/external."""
    p = EXTERNAL_MODELS_DIR / relative_path
    if not p.exists():
        raise FileNotFoundError(f"Checkpoint not found at canonical location: {p}")
    return p
