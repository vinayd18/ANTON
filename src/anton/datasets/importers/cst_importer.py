"""
CST Studio Suite Export Importer.

Parses exported data from CST Studio Suite (including CST 2024-2026):
- 1D S-Parameter frequency responses (ASCII text / CSV with # header lines)
- Real/Imaginary or Magnitude(dB)/Phase exports
- Radiation and Total Efficiency exports
- Farfield pattern tables
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import re as regex
from typing import Any, Dict, List, Optional, Tuple

from anton.datasets.normalization import (
    convert_frequency_to_ghz,
    db_to_linear,
    db_to_ri,
    linear_to_db,
    s11_to_vswr,
    complex_s11_to_zin,
    detect_resonances_and_bandwidth,
)
from anton.datasets.schema import (
    ElectromagneticOutputsRecord,
    FarFieldPattern2D,
)


class CstImporter:
    """
    Parser for CST Studio Suite ASCII and CSV exports.
    """

    def __init__(self, default_z0: float = 50.0):
        self.default_z0 = default_z0

    def parse_s_parameter_file(
        self,
        file_path: str
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, Any]]:
        """Parses a CST S-parameter export file from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CST export file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        file_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        filename = os.path.basename(file_path)

        outputs, meta = self.parse_s_parameter_string(content, filename=filename)
        meta["file_sha256"] = file_sha256
        meta["file_path"] = file_path
        return outputs, meta

    def parse_s_parameter_string(
        self,
        content: str,
        filename: str = "cst_s11.txt"
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, Any]]:
        """Parses CST S-parameter export string."""
        lines = content.splitlines()

        header_line = None
        data_rows: List[List[float]] = []

        for line in lines:
            line_s = line.strip()
            if not line_s:
                continue

            # In CST, headers often start with '#' or '//'
            if line_s.startswith("#") or line_s.startswith("//"):
                raw_hdr = line_s.lstrip("#/").strip()
                if "freq" in raw_hdr.lower() or "s1" in raw_hdr.lower():
                    header_line = raw_hdr
                continue

            # Attempt parsing numbers separated by spaces, tabs, or commas
            tokens = regex.split(r"[\s,]+", line_s)
            try:
                nums = [float(t) for t in tokens if t]
                if nums:
                    data_rows.append(nums)
            except ValueError:
                # Text header without comment symbol
                if "freq" in line_s.lower():
                    header_line = line_s
                continue

        if not data_rows:
            raise ValueError(f"No numerical data found in CST export file '{filename}'.")

        # Determine frequency unit and columns
        freq_unit = "ghz"
        col_names = []
        if header_line:
            col_names = [c.strip() for c in regex.split(r"[\t,]+| {2,}", header_line) if c.strip()]
            hdr_l = header_line.lower()
            if "/ mhz" in hdr_l or "[mhz]" in hdr_l:
                freq_unit = "mhz"
            elif "/ khz" in hdr_l or "[khz]" in hdr_l:
                freq_unit = "khz"
            elif "/ hz" in hdr_l or "[hz]" in hdr_l:
                freq_unit = "hz"
            elif "/ ghz" in hdr_l or "[ghz]" in hdr_l:
                freq_unit = "ghz"

        # Check column types
        has_complex = False
        format_type = "UNKNOWN"

        num_cols = len(data_rows[0])
        if num_cols == 2:
            format_type = "DB_ONLY"
        elif num_cols == 3:
            if any("re" in c.lower() for c in col_names) and any("im" in c.lower() for c in col_names):
                format_type = "RI"
                has_complex = True
            elif any("deg" in c.lower() for c in col_names) or any("phase" in c.lower() for c in col_names):
                format_type = "DB_DEG" if any("db" in c.lower() for c in col_names) else "MA_DEG"
                has_complex = True
            else:
                format_type = "RI"
                has_complex = True

        freqs_ghz = []
        s11_re_list = []
        s11_im_list = []
        s11_mag_list = []
        s11_phase_rad_list = []
        s11_db_list = []
        vswr_list = []
        zin_re_list = []
        zin_im_list = []

        for row in data_rows:
            if len(row) < 2:
                continue
            f_ghz = convert_frequency_to_ghz(row[0], freq_unit)

            if format_type == "DB_ONLY":
                db_val = row[1]
                mag = db_to_linear(db_val)
                vswr = s11_to_vswr(mag)
                s11_db_list.append(round(db_val, 4))
                s11_mag_list.append(round(mag, 6))
                vswr_list.append(round(vswr, 4))

            elif format_type == "RI":
                re_val = row[1]
                im_val = row[2]
                mag = math.hypot(re_val, im_val)
                phase_rad = math.atan2(im_val, re_val)
                db_val = linear_to_db(mag)
                vswr = s11_to_vswr(mag)
                z_re, z_im = complex_s11_to_zin(re_val, im_val, z0=self.default_z0)

                s11_re_list.append(round(re_val, 6))
                s11_im_list.append(round(im_val, 6))
                s11_mag_list.append(round(mag, 6))
                s11_phase_rad_list.append(round(phase_rad, 6))
                s11_db_list.append(round(db_val, 4))
                vswr_list.append(round(vswr, 4))
                zin_re_list.append(round(z_re, 4))
                zin_im_list.append(round(z_im, 4))

            elif format_type in ("DB_DEG", "MA_DEG"):
                if format_type == "DB_DEG":
                    db_val = row[1]
                    ang_deg = row[2]
                    mag = db_to_linear(db_val)
                    phase_rad = math.radians(ang_deg)
                    re_val, im_val = db_to_ri(db_val, ang_deg)
                else:
                    mag = row[1]
                    ang_deg = row[2]
                    phase_rad = math.radians(ang_deg)
                    re_val = mag * math.cos(phase_rad)
                    im_val = mag * math.sin(phase_rad)
                    db_val = linear_to_db(mag)

                vswr = s11_to_vswr(mag)
                z_re, z_im = complex_s11_to_zin(re_val, im_val, z0=self.default_z0)

                s11_re_list.append(round(re_val, 6))
                s11_im_list.append(round(im_val, 6))
                s11_mag_list.append(round(mag, 6))
                s11_phase_rad_list.append(round(phase_rad, 6))
                s11_db_list.append(round(db_val, 4))
                vswr_list.append(round(vswr, 4))
                zin_re_list.append(round(z_re, 4))
                zin_im_list.append(round(z_im, 4))

            freqs_ghz.append(round(f_ghz, 6))

        # Detect resonances & bandwidth
        res_freqs, bw_mhz, fbw = detect_resonances_and_bandwidth(freqs_ghz, s11_db_list)

        outputs = ElectromagneticOutputsRecord(
            frequencies_ghz=freqs_ghz,
            s11_real=s11_re_list if has_complex else None,
            s11_imag=s11_im_list if has_complex else None,
            s11_magnitude=s11_mag_list if s11_mag_list else None,
            s11_phase_rad=s11_phase_rad_list if has_complex else None,
            s11_db=s11_db_list if s11_db_list else None,
            vswr=vswr_list if vswr_list else None,
            zin_real=zin_re_list if has_complex else None,
            zin_imag=zin_im_list if has_complex else None,
            resonant_frequencies_ghz=res_freqs if res_freqs else None,
            impedance_bandwidth_mhz=bw_mhz,
            bandwidth_percentage=fbw,
            has_complex_s11=has_complex,
        )

        metadata = {
            "format": "CST_ASCII",
            "solver": "CST Studio Suite",
            "frequency_unit": freq_unit,
            "has_complex_s11": has_complex,
            "num_points": len(freqs_ghz),
            "freq_min_ghz": min(freqs_ghz),
            "freq_max_ghz": max(freqs_ghz),
        }

        return outputs, metadata
