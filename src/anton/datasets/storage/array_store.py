"""
HDF5-Backed Numerical Array Store for Electromagnetic Data.

Stores large continuous arrays:
- Frequency grids
- Complex S-parameters (real, imaginary, magnitude, phase, dB)
- Voltage Standing Wave Ratio (VSWR)
- Complex input impedance (Zin real, imag)
- Realized gain and efficiency curves
- 2D and 3D radiation patterns

Features gzip chunked compression and thread-safe dataset access.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import h5py
import numpy as np

from anton.datasets.schema import ElectromagneticOutputsRecord


class ArrayStore:
    """
    Manages storage and retrieval of numerical arrays in an HDF5 repository.
    """

    def __init__(self, h5_path: str = "data/datasets/arrays.h5"):
        self.h5_path = os.path.abspath(h5_path)
        os.makedirs(os.path.dirname(self.h5_path), exist_ok=True)
        # Ensure file exists
        if not os.path.exists(self.h5_path):
            with h5py.File(self.h5_path, "w") as f:
                f.attrs["version"] = "1.0.0"
                f.attrs["creator"] = "ANTON Electromagnetic Subsystem"

    def save_record_arrays(
        self,
        record_id: str,
        outputs: ElectromagneticOutputsRecord,
        compression: str = "gzip"
    ) -> None:
        """
        Saves all numerical arrays for a record under group /records/{record_id}.
        """
        with h5py.File(self.h5_path, "a") as f:
            records_grp = f.require_group("records")
            if record_id in records_grp:
                del records_grp[record_id]

            rec_grp = records_grp.create_group(record_id)

            # Mandatory frequency grid
            rec_grp.create_dataset(
                "frequencies_ghz",
                data=np.asarray(outputs.frequencies_ghz, dtype=np.float32),
                compression=compression,
            )

            # Optional S-parameters
            if outputs.s11_real is not None:
                rec_grp.create_dataset("s11_real", data=np.asarray(outputs.s11_real, dtype=np.float32), compression=compression)
            if outputs.s11_imag is not None:
                rec_grp.create_dataset("s11_imag", data=np.asarray(outputs.s11_imag, dtype=np.float32), compression=compression)
            if outputs.s11_magnitude is not None:
                rec_grp.create_dataset("s11_magnitude", data=np.asarray(outputs.s11_magnitude, dtype=np.float32), compression=compression)
            if outputs.s11_phase_rad is not None:
                rec_grp.create_dataset("s11_phase_rad", data=np.asarray(outputs.s11_phase_rad, dtype=np.float32), compression=compression)
            if outputs.s11_db is not None:
                rec_grp.create_dataset("s11_db", data=np.asarray(outputs.s11_db, dtype=np.float32), compression=compression)
            if outputs.vswr is not None:
                rec_grp.create_dataset("vswr", data=np.asarray(outputs.vswr, dtype=np.float32), compression=compression)
            if outputs.zin_real is not None:
                rec_grp.create_dataset("zin_real", data=np.asarray(outputs.zin_real, dtype=np.float32), compression=compression)
            if outputs.zin_imag is not None:
                rec_grp.create_dataset("zin_imag", data=np.asarray(outputs.zin_imag, dtype=np.float32), compression=compression)

            # Gain & Efficiency
            if outputs.gain_dbi is not None:
                rec_grp.create_dataset("gain_dbi", data=np.asarray(outputs.gain_dbi, dtype=np.float32), compression=compression)
            if outputs.radiation_efficiency is not None:
                rec_grp.create_dataset("radiation_efficiency", data=np.asarray(outputs.radiation_efficiency, dtype=np.float32), compression=compression)
            if outputs.total_efficiency is not None:
                rec_grp.create_dataset("total_efficiency", data=np.asarray(outputs.total_efficiency, dtype=np.float32), compression=compression)

            # 2D Patterns
            if outputs.patterns_2d:
                pat2d_grp = rec_grp.create_group("patterns_2d")
                for idx, pat in enumerate(outputs.patterns_2d):
                    p_sub = pat2d_grp.create_group(f"cut_{idx}_{pat.plane}_{pat.frequency_ghz:.2f}GHz")
                    p_sub.attrs["plane"] = pat.plane
                    p_sub.attrs["frequency_ghz"] = pat.frequency_ghz
                    p_sub.create_dataset("angles_deg", data=np.asarray(pat.angles_deg, dtype=np.float32), compression=compression)
                    p_sub.create_dataset("gain_total_dbi", data=np.asarray(pat.gain_total_dbi, dtype=np.float32), compression=compression)

    def load_record_arrays(self, record_id: str) -> Dict[str, np.ndarray]:
        """
        Loads all numerical arrays for a record into a dictionary of NumPy arrays.
        """
        results: Dict[str, np.ndarray] = {}
        with h5py.File(self.h5_path, "r") as f:
            path = f"records/{record_id}"
            if path not in f:
                raise KeyError(f"Record '{record_id}' not found in HDF5 array store.")
            grp = f[path]
            for key, val in grp.items():
                if isinstance(val, h5py.Dataset):
                    results[key] = val[:]
        return results

    def has_record_arrays(self, record_id: str) -> bool:
        """Checks if arrays exist for record_id."""
        with h5py.File(self.h5_path, "r") as f:
            return f"records/{record_id}" in f

    def delete_record_arrays(self, record_id: str) -> bool:
        """Deletes arrays for record_id from the store."""
        with h5py.File(self.h5_path, "a") as f:
            path = f"records/{record_id}"
            if path in f:
                del f[path]
                return True
        return False
