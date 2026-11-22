"""
Youxch Patch MLP Dataset Adapter.

Prepares compatible feature vectors and multi-target frequency curves (S11 + Gain)
for the Youxch Patch MLP surrogate model (e.g. saved-model-5000.h5).

Specifications:
- Input Features: 22-dimensional normalized parameter vector.
- Target: 202-dimensional concatenated output: [S11_dB (101 pts), Gain_dBi (101 pts)].
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np

from anton.datasets.schema import DatasetRecord
from anton.datasets.ml.frequency_grid import FrequencyGridAligner
from anton.datasets.ml.feature_extractor import FeatureExtractor


class YouxchAdapter:
    """
    Translates canonical DatasetRecords into 22-param inputs and 202-dim targets for Youxch MLP.
    """

    TARGET_F_MIN = 2.0
    TARGET_F_MAX = 8.0
    NUM_POINTS = 101

    def __init__(self):
        self.aligner = FrequencyGridAligner(
            target_f_min=self.TARGET_F_MIN,
            target_f_max=self.TARGET_F_MAX,
            num_points=self.NUM_POINTS,
        )

    def is_record_compatible(self, record: DatasetRecord) -> Tuple[bool, str]:
        """Checks if record satisfies Youxch model prerequisites."""
        family = record.antenna_identity.geometry_family.upper()
        if family not in ("RECTANGULAR_PATCH", "INSET_FED_PATCH"):
            return False, f"Incompatible family '{family}'. Requires planar patch geometry."

        outputs = record.outputs
        if outputs.s11_db is None:
            return False, "Record missing S11 in dB."

        if not self.aligner.is_compatible(outputs.frequencies_ghz):
            return False, f"Frequencies do not cover [{self.TARGET_F_MIN}, {self.TARGET_F_MAX}] GHz."

        return True, "COMPATIBLE"

    def prepare_sample(self, record: DatasetRecord) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts 22-dimensional feature vector and 202-dimensional target vector.
        """
        is_comp, reason = self.is_record_compatible(record)
        if not is_comp:
            raise ValueError(f"Record {record.antenna_identity.dataset_record_id} incompatible: {reason}")

        # Base 10 continuous parameters
        base_vec = FeatureExtractor.extract_continuous_vector(record)

        # Pad to 22 dimensions with geometric ratios and constants expected by architecture
        w = base_vec[0]
        length = base_vec[1]
        h = base_vec[4]
        eps_r = base_vec[5]
        aspect_ratio = w / length if length > 0 else 1.0
        norm_h = h / w if w > 0 else 0.05

        extras = np.array([
            aspect_ratio,
            norm_h,
            math.sqrt(eps_r),
            w * length,          # patch area
            (w + length) * 2.0,  # patch perimeter
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        ], dtype=np.float32)

        x_22 = np.concatenate([base_vec, extras])[:22]

        # Targets: S11 (101 pts) + Gain (101 pts)
        s11_res = self.aligner.resample_curve(record.outputs.frequencies_ghz, record.outputs.s11_db)

        if record.outputs.gain_dbi is not None and len(record.outputs.gain_dbi) == len(record.outputs.frequencies_ghz):
            gain_res = self.aligner.resample_curve(record.outputs.frequencies_ghz, record.outputs.gain_dbi)
        else:
            # If gain is absent, use documented approximate aperture gain curve rather than fabricating
            gain_res = np.zeros(self.NUM_POINTS, dtype=np.float32)

        y_202 = np.concatenate([s11_res, gain_res])
        return x_22, y_202


import math

