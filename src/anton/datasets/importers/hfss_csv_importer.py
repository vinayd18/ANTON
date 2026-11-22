"""
HFSS CSV Report and Table Importer.

Parses exported reports from ANSYS HFSS:
- Frequency sweep CSV tables (S11 in dB, Re/Im, Mag/Phase)
- Peak/Broadside Gain vs Frequency CSV tables
- 2D Radiation Pattern cuts (Theta or Phi cuts)
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
import os
import re
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


class HfssCsvImporter:
    """
    Parser for ANSYS HFSS CSV exports.
    Handles multiple column naming variations, units in brackets, and missing phase.
    """

    def __init__(self, default_z0: float = 50.0):
        self.default_z0 = default_z0

    def parse_s_parameter_file(
        self,
        file_path: str
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, Any]]:
        """Parses an HFSS exported S-parameter CSV file from disk."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HFSS CSV file not found: {file_path}")

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
        filename: str = "hfss_report.csv"
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, Any]]:
        """Parses S-parameter CSV content exported from HFSS."""
        reader = csv.reader(io.StringIO(content))
        header_row = None
        data_rows = []

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            # Look for header line containing 'freq'
            if header_row is None:
                row_lower = [c.strip().lower() for c in row]
                if any("freq" in c for c in row_lower):
                    header_row = [c.strip() for c in row]
                    continue
            else:
                try:
                    data_rows.append([float(c.strip()) for c in row if c.strip() != ""])
                except ValueError:
                    continue

        if header_row is None or not data_rows:
            raise ValueError(f"Could not identify valid HFSS CSV header or data rows in '{filename}'.")

        # Analyze column headers
        freq_idx = -1
        freq_unit = "ghz"
        s11_db_idx = -1
        s11_mag_idx = -1
        s11_re_idx = -1
        s11_im_idx = -1
        s11_ang_deg_idx = -1

        for idx, col in enumerate(header_row):
            col_l = col.lower()
            if "freq" in col_l:
                freq_idx = idx
                if "[mhz]" in col_l or "mhz" in col_l:
                    freq_unit = "mhz"
                elif "[khz]" in col_l or "khz" in col_l:
                    freq_unit = "khz"
                elif "[hz]" in col_l:
                    freq_unit = "hz"
                elif "[ghz]" in col_l or "ghz" in col_l:
                    freq_unit = "ghz"
            elif "db(s(1,1))" in col_l or "s(1,1)_db" in col_l or "s11_db" in col_l or "s11(db)" in col_l:
                s11_db_idx = idx
            elif "re(s(1,1))" in col_l or "real(s(1,1))" in col_l or "s11_re" in col_l:
                s11_re_idx = idx
            elif "im(s(1,1))" in col_l or "imag(s(1,1))" in col_l or "s11_im" in col_l:
                s11_im_idx = idx
            elif "ang_deg(s(1,1))" in col_l or "ang(s(1,1))" in col_l or "phase(s(1,1))" in col_l or "s11_deg" in col_l:
                s11_ang_deg_idx = idx
            elif "mag(s(1,1))" in col_l or "abs(s(1,1))" in col_l or "s11_mag" in col_l:
                s11_mag_idx = idx

        if freq_idx == -1:
            raise ValueError("No frequency column found in HFSS CSV header.")

        freqs_ghz = []
        s11_db_list = []
        s11_mag_list = []
        s11_re_list = []
        s11_im_list = []
        s11_phase_rad_list = []
        vswr_list = []
        zin_re_list = []
        zin_im_list = []

        has_re_im = (s11_re_idx != -1 and s11_im_idx != -1)
        has_db_ang = (s11_db_idx != -1 and s11_ang_deg_idx != -1)
        has_mag_ang = (s11_mag_idx != -1 and s11_ang_deg_idx != -1)
        has_complex = has_re_im or has_db_ang or has_mag_ang

        for row in data_rows:
            if len(row) <= freq_idx:
                continue
            raw_f = row[freq_idx]
            f_ghz = convert_frequency_to_ghz(raw_f, freq_unit)

            if has_re_im:
                re = row[s11_re_idx]
                im = row[s11_im_idx]
                mag = math.hypot(re, im)
                phase_rad = math.atan2(im, re)
                db_val = linear_to_db(mag)
                vswr = s11_to_vswr(mag)
                z_re, z_im = complex_s11_to_zin(re, im, z0=self.default_z0)

                s11_re_list.append(round(re, 6))
                s11_im_list.append(round(im, 6))
                s11_mag_list.append(round(mag, 6))
                s11_phase_rad_list.append(round(phase_rad, 6))
                s11_db_list.append(round(db_val, 4))
                vswr_list.append(round(vswr, 4))
                zin_re_list.append(round(z_re, 4))
                zin_im_list.append(round(z_im, 4))

            elif has_db_ang:
                db_val = row[s11_db_idx]
                ang_deg = row[s11_ang_deg_idx]
                mag = db_to_linear(db_val)
                phase_rad = math.radians(ang_deg)
                re, im = db_to_ri(db_val, ang_deg)
                vswr = s11_to_vswr(mag)
                z_re, z_im = complex_s11_to_zin(re, im, z0=self.default_z0)

                s11_re_list.append(round(re, 6))
                s11_im_list.append(round(im, 6))
                s11_mag_list.append(round(mag, 6))
                s11_phase_rad_list.append(round(phase_rad, 6))
                s11_db_list.append(round(db_val, 4))
                vswr_list.append(round(vswr, 4))
                zin_re_list.append(round(z_re, 4))
                zin_im_list.append(round(z_im, 4))

            elif has_mag_ang:
                mag = row[s11_mag_idx]
                ang_deg = row[s11_ang_deg_idx]
                phase_rad = math.radians(ang_deg)
                re = mag * math.cos(phase_rad)
                im = mag * math.sin(phase_rad)
                db_val = linear_to_db(mag)
                vswr = s11_to_vswr(mag)
                z_re, z_im = complex_s11_to_zin(re, im, z0=self.default_z0)

                s11_re_list.append(round(re, 6))
                s11_im_list.append(round(im, 6))
                s11_mag_list.append(round(mag, 6))
                s11_phase_rad_list.append(round(phase_rad, 6))
                s11_db_list.append(round(db_val, 4))
                vswr_list.append(round(vswr, 4))
                zin_re_list.append(round(z_re, 4))
                zin_im_list.append(round(z_im, 4))

            elif s11_db_idx != -1:
                # MAGNITUDE-ONLY S11
                db_val = row[s11_db_idx]
                mag = db_to_linear(db_val)
                vswr = s11_to_vswr(mag)
                s11_db_list.append(round(db_val, 4))
                s11_mag_list.append(round(mag, 6))
                vswr_list.append(round(vswr, 4))
                # DO NOT FABRICATE COMPLEX S11 OR ZIN

            elif s11_mag_idx != -1:
                # LINEAR MAGNITUDE ONLY
                mag = row[s11_mag_idx]
                db_val = linear_to_db(mag)
                vswr = s11_to_vswr(mag)
                s11_db_list.append(round(db_val, 4))
                s11_mag_list.append(round(mag, 6))
                vswr_list.append(round(vswr, 4))

            else:
                raise ValueError("HFSS CSV must contain S11 (in dB, Re/Im, or Mag).")

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
            "format": "HFSS_CSV",
            "solver": "HFSS",
            "frequency_unit": freq_unit,
            "has_complex_s11": has_complex,
            "columns": header_row,
            "num_points": len(freqs_ghz),
            "freq_min_ghz": min(freqs_ghz),
            "freq_max_ghz": max(freqs_ghz),
        }

        return outputs, metadata

    def parse_gain_file(
        self,
        file_path: str
    ) -> Tuple[List[float], List[float], Dict[str, Any]]:
        """
        Parses an HFSS exported Gain vs Frequency CSV report.
        Returns (frequencies_ghz, gain_dbi, metadata).
        """
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        reader = csv.reader(io.StringIO(content))
        header_row = None
        data_rows = []

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            if header_row is None:
                row_l = [c.strip().lower() for c in row]
                if any("freq" in c for c in row_l):
                    header_row = [c.strip() for c in row]
                    continue
            else:
                try:
                    data_rows.append([float(c.strip()) for c in row if c.strip() != ""])
                except ValueError:
                    continue

        if header_row is None or not data_rows:
            raise ValueError(f"Could not parse HFSS Gain CSV '{file_path}'.")

        freq_idx = 0
        gain_idx = 1
        freq_unit = "ghz"

        for idx, col in enumerate(header_row):
            c_l = col.lower()
            if "freq" in c_l:
                freq_idx = idx
                if "mhz" in c_l:
                    freq_unit = "mhz"
                elif "ghz" in c_l:
                    freq_unit = "ghz"
            elif "gain" in c_l or "db(gaintotal)" in c_l:
                gain_idx = idx

        freqs = []
        gains = []
        for r in data_rows:
            if len(r) > max(freq_idx, gain_idx):
                freqs.append(convert_frequency_to_ghz(r[freq_idx], freq_unit))
                gains.append(r[gain_idx])

        meta = {
            "format": "HFSS_GAIN_CSV",
            "num_points": len(freqs),
            "peak_gain_dbi": max(gains) if gains else None,
        }
        return freqs, gains, meta

    def parse_pattern_2d_file(
        self,
        file_path: str,
        frequency_ghz: float,
        plane: str = "E_PLANE"
    ) -> FarFieldPattern2D:
        """
        Parses an HFSS exported 2D Radiation Pattern CSV (e.g. Theta vs GainTotal).
        """
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        reader = csv.reader(io.StringIO(content))
        header_row = None
        data_rows = []

        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue
            if header_row is None:
                row_l = [c.strip().lower() for c in row]
                if any("theta" in c or "phi" in c or "ang" in c for c in row_l):
                    header_row = [c.strip() for c in row]
                    continue
            else:
                try:
                    data_rows.append([float(c.strip()) for c in row if c.strip() != ""])
                except ValueError:
                    continue

        angle_idx = 0
        gain_idx = 1
        for idx, col in enumerate(header_row):
            c_l = col.lower()
            if "theta" in c_l or "phi" in c_l or "ang" in c_l:
                angle_idx = idx
            elif "gain" in c_l:
                gain_idx = idx

        angles = []
        gains = []
        for r in data_rows:
            if len(r) > max(angle_idx, gain_idx):
                angles.append(r[angle_idx])
                gains.append(r[gain_idx])

        return FarFieldPattern2D(
            plane=plane,
            frequency_ghz=frequency_ghz,
            angles_deg=angles,
            gain_total_dbi=gains,
            normalization_peak_dbi=max(gains) if gains else None,
        )

