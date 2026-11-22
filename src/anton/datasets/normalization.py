"""
Scientific Normalization and Electromagnetic Processing Module.

Provides physical conversions for:
- Frequency units (Hz, kHz, MHz, GHz)
- Length units (m, cm, mm)
- Angle units (deg, rad)
- S-parameter magnitudes (linear, dB)
- Complex S-parameters (RI, MA, DB)
- Voltage Standing Wave Ratio (VSWR)
- Complex input impedance (Zin)
- Resonance and bandwidth extraction
"""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import numpy as np


def convert_frequency_to_ghz(freq: float, unit: str) -> float:
    """Converts a frequency value to gigahertz (GHz)."""
    unit_lower = unit.strip().lower()
    if unit_lower in ("hz", "hertz"):
        return freq / 1e9
    elif unit_lower in ("khz", "kilohertz"):
        return freq / 1e6
    elif unit_lower in ("mhz", "megahertz"):
        return freq / 1e3
    elif unit_lower in ("ghz", "gigahertz"):
        return freq
    elif unit_lower in ("thz", "terahertz"):
        return freq * 1e3
    else:
        raise ValueError(f"Unsupported frequency unit: '{unit}'. Must be Hz, kHz, MHz, or GHz.")


def convert_length_to_mm(length: float, unit: str) -> float:
    """Converts a geometric length value to millimeters (mm)."""
    unit_lower = unit.strip().lower()
    if unit_lower in ("mm", "millimeter", "millimeters"):
        return length
    elif unit_lower in ("cm", "centimeter", "centimeters"):
        return length * 10.0
    elif unit_lower in ("m", "meter", "meters"):
        return length * 1000.0
    elif unit_lower in ("um", "micrometer", "microns"):
        return length / 1000.0
    elif unit_lower in ("in", "inch", "inches"):
        return length * 25.4
    elif unit_lower in ("mil", "mils"):
        return length * 0.0254
    else:
        raise ValueError(f"Unsupported length unit: '{unit}'. Must be mm, cm, m, in, or mil.")


def convert_angle_to_deg(angle: float, unit: str) -> float:
    """Converts an angle to degrees."""
    unit_lower = unit.strip().lower()
    if unit_lower in ("deg", "degree", "degrees"):
        return angle
    elif unit_lower in ("rad", "radian", "radians"):
        return math.degrees(angle)
    else:
        raise ValueError(f"Unsupported angle unit: '{unit}'. Must be deg or rad.")


def linear_to_db(linear_mag: float, floor_db: float = -120.0) -> float:
    """
    Converts linear S-parameter magnitude to decibels: 20 * log10(|S|).
    Enforces a realistic numerical floor.
    """
    if linear_mag <= 0.0:
        return floor_db
    db = 20.0 * math.log10(linear_mag)
    return max(db, floor_db)


def db_to_linear(db_val: float) -> float:
    """Converts decibels to linear S-parameter magnitude: 10^(dB / 20)."""
    return 10.0 ** (db_val / 20.0)


def s11_to_vswr(mag: float, max_vswr: float = 100.0) -> float:
    """
    Computes Voltage Standing Wave Ratio (VSWR):
    VSWR = (1 + |S11|) / (1 - |S11|)
    For |S11| >= 1.0, clamps to max_vswr to avoid division by zero or negative VSWR.
    """
    if mag < 0.0:
        mag = abs(mag)
    if mag >= 0.999999:
        return max_vswr
    vswr = (1.0 + mag) / (1.0 - mag)
    return min(vswr, max_vswr)


def complex_s11_to_zin(
    s11_re: float,
    s11_im: float,
    z0: float = 50.0,
    singularity_threshold: float = 1e-7
) -> Tuple[float, float]:
    """
    Calculates complex input impedance Zin = Rin + j*Xin from complex reflection coefficient S11:
    Zin = Z0 * (1 + S11) / (1 - S11)
    
    Returns (Rin, Xin) in Ohms.
    Strictly requires both real and imaginary parts of S11.
    """
    s11 = complex(s11_re, s11_im)
    denom = 1.0 - s11
    if abs(denom) < singularity_threshold:
        # Near S11 = 1 + j0 (open circuit)
        return float(1e6), 0.0
    zin = z0 * (1.0 + s11) / denom
    return float(zin.real), float(zin.imag)


def ri_to_db_phase(re: float, im: float) -> Tuple[float, float]:
    """Converts Real/Imag components to (dB_magnitude, phase_deg)."""
    mag = math.hypot(re, im)
    db = linear_to_db(mag)
    phase_deg = math.degrees(math.atan2(im, re))
    return db, phase_deg


def ma_to_ri(mag: float, ang_deg: float) -> Tuple[float, float]:
    """Converts Linear Magnitude and Angle (deg) to (Real, Imag)."""
    ang_rad = math.radians(ang_deg)
    re = mag * math.cos(ang_rad)
    im = mag * math.sin(ang_rad)
    return re, im


def db_to_ri(db_val: float, ang_deg: float) -> Tuple[float, float]:
    """Converts Decibel Magnitude and Angle (deg) to (Real, Imag)."""
    mag = db_to_linear(db_val)
    ang_rad = math.radians(ang_deg)
    re = mag * math.cos(ang_rad)
    im = mag * math.sin(ang_rad)
    return re, im


def detect_resonances_and_bandwidth(
    frequencies_ghz: List[float],
    s11_db: List[float],
    threshold_db: float = -10.0
) -> Tuple[List[float], Optional[float], Optional[float]]:
    """
    Detects resonant frequencies (local minima of S11_dB below threshold_db)
    and computes the -10 dB impedance bandwidth of the primary resonance.

    Returns:
    - resonant_frequencies_ghz: List of resonant frequencies sorted by dip depth
    - bandwidth_mhz: -10 dB bandwidth in MHz (None if no resonance below threshold)
    - fractional_bandwidth_pct: Fractional bandwidth percentage (None if no resonance)
    """
    if len(frequencies_ghz) < 3 or len(s11_db) != len(frequencies_ghz):
        return [], None, None

    freqs = np.asarray(frequencies_ghz, dtype=float)
    s11 = np.asarray(s11_db, dtype=float)

    # Find local minima where s11 is below threshold
    res_freqs = []
    res_depths = []

    for i in range(1, len(s11) - 1):
        if s11[i] < s11[i - 1] and s11[i] < s11[i + 1] and s11[i] <= threshold_db:
            # Quadratic refinement for sub-grid minimum
            # y = a*(x - x0)^2 + b*(x - x0) + c
            x0 = freqs[i]
            dx = (freqs[i + 1] - freqs[i - 1]) / 2.0
            d1 = (s11[i + 1] - s11[i - 1]) / 2.0
            d2 = s11[i + 1] - 2.0 * s11[i] + s11[i - 1]
            if d2 > 0:
                delta_x = -d1 / d2 * (freqs[i + 1] - freqs[i])
                refined_freq = x0 + np.clip(delta_x, -(freqs[i] - freqs[i - 1]) * 0.5, (freqs[i + 1] - freqs[i]) * 0.5)
            else:
                refined_freq = x0
            res_freqs.append(float(refined_freq))
            res_depths.append(float(s11[i]))

    # If no interior local minimum below threshold, check global minimum
    if not res_freqs:
        min_idx = int(np.argmin(s11))
        if s11[min_idx] <= threshold_db:
            res_freqs.append(float(freqs[min_idx]))
            res_depths.append(float(s11[min_idx]))

    if not res_freqs:
        return [], None, None

    # Sort resonances by dip depth (strongest resonance first)
    sorted_pairs = sorted(zip(res_freqs, res_depths), key=lambda p: p[1])
    sorted_res_freqs = [p[0] for p in sorted_pairs]
    primary_res = sorted_res_freqs[0]

    # Find -10 dB bandwidth around the primary resonance
    # Find contiguous interval where s11 <= threshold_db enclosing primary_res
    below_thresh = s11 <= threshold_db
    res_idx = int(np.argmin(np.abs(freqs - primary_res)))

    if not below_thresh[res_idx]:
        return sorted_res_freqs, None, None

    # Walk left
    left_idx = res_idx
    while left_idx > 0 and below_thresh[left_idx - 1]:
        left_idx -= 1

    # Walk right
    right_idx = res_idx
    while right_idx < len(freqs) - 1 and below_thresh[right_idx + 1]:
        right_idx += 1

    # Linear interpolation at band edges
    if left_idx > 0:
        f1, f2 = freqs[left_idx - 1], freqs[left_idx]
        s1, s2 = s11[left_idx - 1], s11[left_idx]
        f_low = f1 + (threshold_db - s1) / (s2 - s1) * (f2 - f1) if s2 != s1 else f2
    else:
        f_low = freqs[0]

    if right_idx < len(freqs) - 1:
        f1, f2 = freqs[right_idx], freqs[right_idx + 1]
        s1, s2 = s11[right_idx], s11[right_idx + 1]
        f_high = f1 + (threshold_db - s1) / (s2 - s1) * (f2 - f1) if s2 != s1 else f1
    else:
        f_high = freqs[-1]

    bw_ghz = max(0.0, float(f_high - f_low))
    bw_mhz = bw_ghz * 1000.0
    fbw_pct = (bw_ghz / primary_res) * 100.0 if primary_res > 0 else 0.0

    return sorted_res_freqs, round(bw_mhz, 3), round(fbw_pct, 3)
