"""
Dataset Importers Subpackage.

Provides unified interface for importing electromagnetic simulation and measurement files:
- Touchstone (.s1p, .s2p)
- HFSS CSV frequency sweeps, gain, and patterns
- CST Studio ASCII / CSV exports
- Published dataset adapters (METU, Antenna-AI-Benchmark)
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

from anton.datasets.importers.touchstone_importer import TouchstoneImporter
from anton.datasets.importers.hfss_csv_importer import HfssCsvImporter
from anton.datasets.importers.cst_importer import CstImporter
from anton.datasets.importers.published_dataset_adapters import (
    MetuDatasetAdapter,
    AntennaAiBenchmarkAdapter,
)
from anton.datasets.schema import ElectromagneticOutputsRecord


class DatasetImporter:
    """
    Unified high-level importer with format auto-detection.
    """

    def __init__(self, default_z0: float = 50.0):
        self.default_z0 = default_z0
        self.touchstone = TouchstoneImporter(default_z0=default_z0)
        self.hfss = HfssCsvImporter(default_z0=default_z0)
        self.cst = CstImporter(default_z0=default_z0)

    def import_file(
        self,
        file_path: str,
        format_hint: Optional[str] = None
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, Any]]:
        """
        Auto-detects file format and parses into ElectromagneticOutputsRecord and metadata.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        hint = (format_hint or "").lower()

        if hint in ("touchstone", "s1p", "s2p") or ext in (".s1p", ".s2p"):
            return self.touchstone.parse_file(file_path)

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            first_lines = [f.readline() for _ in range(15)]
        header_text = "".join(first_lines).lower()

        # Check for Touchstone option line
        if any(line.strip().startswith("#") and any(u in line.lower() for u in ("ghz", "mhz", "khz", "hz")) for line in first_lines):
            # Could be CST ASCII or Touchstone
            if any("s1,1" in line.lower() for line in first_lines):
                return self.cst.parse_s_parameter_file(file_path)
            return self.touchstone.parse_file(file_path)

        # Check for HFSS CSV
        if ext == ".csv" or hint == "hfss_csv" or "db(s(1,1))" in header_text or "re(s(1,1))" in header_text:
            return self.hfss.parse_s_parameter_file(file_path)

        # Check for CST
        if hint == "cst" or "cst" in header_text or "s1,1" in header_text:
            return self.cst.parse_s_parameter_file(file_path)

        # Fallback: attempt HFSS CSV then Touchstone
        try:
            return self.hfss.parse_s_parameter_file(file_path)
        except Exception:
            return self.touchstone.parse_file(file_path)


__all__ = [
    "DatasetImporter",
    "TouchstoneImporter",
    "HfssCsvImporter",
    "CstImporter",
    "MetuDatasetAdapter",
    "AntennaAiBenchmarkAdapter",
]

