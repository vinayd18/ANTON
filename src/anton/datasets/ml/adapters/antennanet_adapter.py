"""
AntennaNet Dataset Adapter.

Prepares compatible feature vectors and target frequency responses
for the AntennaNet deep learning models (e.g. s11_model.pt, best_forward_surrogate.pt).

Specifications:
- Input Features: [patch_width_mm, patch_length_mm, substrate_height_mm, permittivity_r] (4-dim)
- Target: S11 in dB resampled to 101 points over [1.0, 6.0] GHz.
- Supported Geometry: RECTANGULAR_PATCH only.
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np

from anton.datasets.schema import DatasetRecord
from anton.datasets.ml.frequency_grid import FrequencyGridAligner


class AntennaNetAdapter:
    """
    Translates canonical DatasetRecords into tensors compatible with AntennaNet checkpoints.
    """

    TARGET_F_MIN = 1.0
    TARGET_F_MAX = 6.0
    NUM_POINTS = 101

    def __init__(self):
        self.aligner = FrequencyGridAligner(
            target_f_min=self.TARGET_F_MIN,
            target_f_max=self.TARGET_F_MAX,
            num_points=self.NUM_POINTS
        )

    def is_record_compatible(self, record: DatasetRecord) -> Tuple[bool, str]:
        """
        Verifies if record meets AntennaNet architecture constraints.
        """
        family = record.antenna_identity.geometry_family.upper()
        if family != "RECTANGULAR_PATCH":
            return False, f"Incompatible geometry family: '{family}'. AntennaNet strictly supports RECTANGULAR_PATCH."

        geo = record.geometry
        patch = geo.get("patch", {})
        if "width" not in patch or "length" not in patch:
            return False, "Patch geometry missing 'width' or 'length' parameters."

        outputs = record.outputs
        if outputs.s11_db is None:
            return False, "Record missing S11 in dB."

        if not self.aligner.is_compatible(outputs.frequencies_ghz):
            src_min = min(outputs.frequencies_ghz)
            src_max = max(outputs.frequencies_ghz)
            return False, (
                f"Frequency range [{src_min:.2f}, {src_max:.2f}] GHz does not cover "
                f"AntennaNet target grid [1.0, 6.0] GHz."
            )

        return True, "COMPATIBLE"

    def prepare_sample(self, record: DatasetRecord) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extracts (x_tensor, y_tensor) for a single record.
        x_tensor: [4] -> [W, L, h, eps_r]
        y_tensor: [101] -> S11_dB resampled
        """
        is_comp, reason = self.is_record_compatible(record)
        if not is_comp:
            raise ValueError(f"Record {record.antenna_identity.dataset_record_id} is incompatible: {reason}")

        patch = record.geometry.get("patch", {})
        w = float(patch["width"])
        length = float(patch["length"])
        h = float(record.materials.substrate_thickness_mm)
        eps_r = float(record.materials.permittivity_r)

        x = np.array([w, length, h, eps_r], dtype=np.float32)

        # Resample S11 to 101 points
        y = self.aligner.resample_curve(record.outputs.frequencies_ghz, record.outputs.s11_db)

        return x, y

    def prepare_batch(
        self,
        records: List[DatasetRecord]
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Processes a list of records. Skips incompatible ones with recorded reasons.
        Returns (X, Y, valid_record_ids).
        """
        x_list = []
        y_list = []
        valid_ids = []

        for r in records:
            is_comp, _ = self.is_record_compatible(r)
            if is_comp:
                x, y = self.prepare_sample(r)
                x_list.append(x)
                y_list.append(y)
                valid_ids.append(r.antenna_identity.dataset_record_id)

        if not x_list:
            return np.empty((0, 4), dtype=np.float32), np.empty((0, self.NUM_POINTS), dtype=np.float32), []

        return np.stack(x_list, axis=0), np.stack(y_list, axis=0), valid_ids

