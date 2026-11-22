"""
Frequency Grid Resampling and Alignment.

Provides shape-preserving monotonic resampling of electromagnetic frequency sweeps
onto standardized grids (e.g. 101 or 201 points) using PCHIP interpolation.
Strictly forbids extrapolation beyond simulated frequency boundaries.
"""

from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
from scipy.interpolate import PchipInterpolator


class FrequencyGridAligner:
    """
    Resamples frequency responses to a target uniform grid without distorting narrow resonances.
    """

    def __init__(
        self,
        target_f_min: float,
        target_f_max: float,
        num_points: int = 101
    ):
        self.target_f_min = target_f_min
        self.target_f_max = target_f_max
        self.num_points = num_points
        self.target_grid = np.linspace(target_f_min, target_f_max, num_points, dtype=np.float64)

    def is_compatible(self, source_freqs: List[float], tol_ghz: float = 1e-4) -> bool:
        """
        Verifies that source frequency sweep completely covers the target grid
        without requiring extrapolation.
        """
        if not source_freqs:
            return False
        src_min = min(source_freqs)
        src_max = max(source_freqs)
        return (src_min <= self.target_f_min + tol_ghz) and (src_max >= self.target_f_max - tol_ghz)

    def resample_curve(
        self,
        source_freqs: List[float],
        source_values: List[float]
    ) -> np.ndarray:
        """
        Resamples a 1D response curve (e.g. S11_dB or Gain) onto target_grid.
        Uses PCHIP (Piecewise Cubic Hermite Interpolating Polynomial) to preserve monotonicity
        and prevent overshoot near sharp resonance dips.
        """
        if not self.is_compatible(source_freqs):
            raise ValueError(
                f"Source frequencies [{min(source_freqs):.3f}, {max(source_freqs):.3f}] GHz do not "
                f"fully cover target grid [{self.target_f_min:.3f}, {self.target_f_max:.3f}] GHz. "
                f"Extrapolation is strictly prohibited."
            )

        src_f = np.asarray(source_freqs, dtype=np.float64)
        src_v = np.asarray(source_values, dtype=np.float64)

        # Ensure sorted
        if not np.all(np.diff(src_f) > 0):
            sort_idx = np.argsort(src_f)
            src_f = src_f[sort_idx]
            src_v = src_v[sort_idx]

        interpolator = PchipInterpolator(src_f, src_v)
        resampled = interpolator(self.target_grid)
        return resampled.astype(np.float32)

    def resample_complex_s11(
        self,
        source_freqs: List[float],
        s11_re: List[float],
        s11_im: List[float]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Resamples real and imaginary components of S11 independently onto target grid.
        """
        resampled_re = self.resample_curve(source_freqs, s11_re)
        resampled_im = self.resample_curve(source_freqs, s11_im)
        return resampled_re, resampled_im
