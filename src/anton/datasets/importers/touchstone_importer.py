"""
Touchstone S-Parameter Importer (.s1p, .s2p).

Supports standard Touchstone 1.0 and 1.1 formats exported from HFSS, CST, Keysight ADS,
Rohde & Schwarz or Copper Mountain VNAs. Handles all frequency units, data formats (RI, MA, DB),
and reference resistances.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Dict, List, Optional, Tuple

from anton.datasets.normalization import (
    convert_frequency_to_ghz,
    db_to_ri,
    ma_to_ri,
    linear_to_db,
    s11_to_vswr,
    complex_s11_to_zin,
    detect_resonances_and_bandwidth,
)
from anton.datasets.schema import ElectromagneticOutputsRecord, FrequencyUnit, ComplexFormat


class TouchstoneImporter:
    """
    Parser for Touchstone 1-port (.s1p) and 2-port (.s2p) files.
    """

    def __init__(self, default_z0: float = 50.0):
        self.default_z0 = default_z0

    def parse_file(self, file_path: str) -> Tuple[ElectromagneticOutputsRecord, Dict[str, any]]:
        """
        Parses a Touchstone file from disk.
        Returns (ElectromagneticOutputsRecord, metadata_dict).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Touchstone file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        file_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        filename = os.path.basename(file_path)

        outputs, meta = self.parse_string(content, filename=filename)
        meta["file_sha256"] = file_sha256
        meta["file_path"] = file_path
        return outputs, meta

    def parse_string(
        self,
        content: str,
        filename: str = "data.s1p"
    ) -> Tuple[ElectromagneticOutputsRecord, Dict[str, any]]:
        """
        Parses Touchstone string content.
        """
        lines = content.splitlines()

        # Touchstone option line defaults
        freq_unit = "ghz"
        data_format = "ma"  # Default in standard is MA
        parameter = "s"
        z0 = self.default_z0

        comments: List[str] = []
        data_rows: List[List[float]] = []

        is_two_port = filename.lower().endswith(".s2p")

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check for comments
            if line_str.startswith("!"):
                comments.append(line_str[1:].strip())
                continue

            # Check for option line
            if line_str.startswith("#"):
                tokens = line_str[1:].strip().split()
                # e.g. # GHz S MA R 50 or # MHz S DB R 50
                idx = 0
                while idx < len(tokens):
                    tok = tokens[idx].upper()
                    if tok in ("HZ", "KHZ", "MHZ", "GHZ", "THZ"):
                        freq_unit = tok.lower()
                    elif tok in ("S", "Y", "Z", "H", "G"):
                        parameter = tok.lower()
                    elif tok in ("DB", "MA", "RI"):
                        data_format = tok.upper()
                    elif tok == "R":
                        if idx + 1 < len(tokens):
                            try:
                                z0 = float(tokens[idx + 1])
                                idx += 1
                            except ValueError:
                                pass
                    idx += 1
                continue

            # Strip inline comments
            if "!" in line_str:
                line_str = line_str.split("!")[0].strip()

            # Parse numbers
            tokens = line_str.split()
            if not tokens:
                continue

            try:
                nums = [float(t) for t in tokens]
                data_rows.append(nums)
            except ValueError:
                # Malformed line or header text
                continue

        if not data_rows:
            raise ValueError(f"No valid numerical data rows found in Touchstone file '{filename}'.")

        # In Touchstone 2-port files, sometimes 9 numbers are spread across multiple lines
        # or 9 numbers appear on a single line: freq S11_1 S11_2 S21_1 S21_2 S12_1 S12_2 S22_1 S22_2
        freqs_ghz: List[float] = []
        s11_re_list: List[float] = []
        s11_im_list: List[float] = []
        s11_mag_list: List[float] = []
        s11_phase_rad_list: List[float] = []
        s11_db_list: List[float] = []
        vswr_list: List[float] = []
        zin_re_list: List[float] = []
        zin_im_list: List[float] = []

        # Process rows
        for row in data_rows:
            if len(row) < 3:
                continue
            raw_freq = row[0]
            val1 = row[1]
            val2 = row[2]

            freq_ghz = convert_frequency_to_ghz(raw_freq, freq_unit)

            if data_format == "RI":
                re = val1
                im = val2
                mag = math.hypot(re, im)
                phase_rad = math.atan2(im, re)
                db_val = linear_to_db(mag)
            elif data_format == "MA":
                mag = val1
                ang_deg = val2
                phase_rad = math.radians(ang_deg)
                re, im = ma_to_ri(mag, ang_deg)
                db_val = linear_to_db(mag)
            elif data_format == "DB":
                db_val = val1
                ang_deg = val2
                mag = 10.0 ** (db_val / 20.0)
                phase_rad = math.radians(ang_deg)
                re, im = db_to_ri(db_val, ang_deg)
            else:
                raise ValueError(f"Unknown Touchstone format: {data_format}")

            vswr = s11_to_vswr(mag)
            zin_re, zin_im = complex_s11_to_zin(re, im, z0=z0)

            freqs_ghz.append(round(freq_ghz, 6))
            s11_re_list.append(round(re, 6))
            s11_im_list.append(round(im, 6))
            s11_mag_list.append(round(mag, 6))
            s11_phase_rad_list.append(round(phase_rad, 6))
            s11_db_list.append(round(db_val, 4))
            vswr_list.append(round(vswr, 4))
            zin_re_list.append(round(zin_re, 4))
            zin_im_list.append(round(zin_im, 4))

        # Check frequency sorting
        if not all(freqs_ghz[i] < freqs_ghz[i + 1] for i in range(len(freqs_ghz) - 1)):
            # Sort by frequency
            combined = sorted(
                zip(
                    freqs_ghz,
                    s11_re_list,
                    s11_im_list,
                    s11_mag_list,
                    s11_phase_rad_list,
                    s11_db_list,
                    vswr_list,
                    zin_re_list,
                    zin_im_list,
                ),
                key=lambda x: x[0],
            )
            (
                freqs_ghz,
                s11_re_list,
                s11_im_list,
                s11_mag_list,
                s11_phase_rad_list,
                s11_db_list,
                vswr_list,
                zin_re_list,
                zin_im_list,
            ) = map(list, zip(*combined))

        # Detect resonances & bandwidth
        res_freqs, bw_mhz, fbw = detect_resonances_and_bandwidth(freqs_ghz, s11_db_list)

        outputs = ElectromagneticOutputsRecord(
            frequencies_ghz=freqs_ghz,
            s11_real=s11_re_list,
            s11_imag=s11_im_list,
            s11_magnitude=s11_mag_list,
            s11_phase_rad=s11_phase_rad_list,
            s11_db=s11_db_list,
            vswr=vswr_list,
            zin_real=zin_re_list,
            zin_imag=zin_im_list,
            resonant_frequencies_ghz=res_freqs if res_freqs else None,
            impedance_bandwidth_mhz=bw_mhz,
            bandwidth_percentage=fbw,
            has_complex_s11=True,
        )

        metadata = {
            "format": "Touchstone",
            "extension": ".s2p" if is_two_port else ".s1p",
            "frequency_unit": freq_unit,
            "data_format": data_format,
            "parameter": parameter,
            "z0_ohm": z0,
            "comments": comments,
            "num_points": len(freqs_ghz),
            "freq_min_ghz": min(freqs_ghz),
            "freq_max_ghz": max(freqs_ghz),
        }

        return outputs, metadata

