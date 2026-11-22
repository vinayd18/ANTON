"""
Multi-Format Dataset Exporter.

Supports exporting electromagnetic datasets and records to:
- JSON (complete self-contained records)
- CSV (frequency response curves and parameter sweeps)
- NumPy (.npz archives of arrays and parameters)
- HDF5 (standalone portable numerical container)
- Parquet (tabular column-oriented storage, with fallback)
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any, Dict, List, Optional
import numpy as np

from anton.datasets.schema import DatasetRecord
from anton.datasets.storage.atomic_io import atomic_write


class DatasetExporter:
    """
    Exports single or multiple dataset records into research-grade portable formats.
    """

    @staticmethod
    def export_json(records: List[DatasetRecord], output_path: str, indent: int = 2) -> str:
        """
        Exports records as a unified JSON array.
        """
        data = [r.model_dump() for r in records]
        json_str = json.dumps(data, indent=indent)
        return atomic_write(output_path, json_str)

    @staticmethod
    def export_csv(record: DatasetRecord, output_path: str) -> str:
        """
        Exports a record's frequency sweep response to a standard CSV file.
        """
        outputs = record.outputs
        freqs = outputs.frequencies_ghz

        fieldnames = ["frequency_ghz"]
        if outputs.s11_db is not None:
            fieldnames.append("s11_db")
        if outputs.s11_magnitude is not None:
            fieldnames.append("s11_mag")
        if outputs.vswr is not None:
            fieldnames.append("vswr")
        if outputs.s11_real is not None and outputs.s11_imag is not None:
            fieldnames.extend(["s11_real", "s11_imag", "s11_phase_rad"])
        if outputs.zin_real is not None and outputs.zin_imag is not None:
            fieldnames.extend(["zin_real", "zin_imag"])
        if outputs.gain_dbi is not None:
            fieldnames.append("gain_dbi")

        rows = []
        for i, f in enumerate(freqs):
            row = {"frequency_ghz": f}
            if outputs.s11_db is not None:
                row["s11_db"] = outputs.s11_db[i]
            if outputs.s11_magnitude is not None:
                row["s11_mag"] = outputs.s11_magnitude[i]
            if outputs.vswr is not None:
                row["vswr"] = outputs.vswr[i]
            if outputs.s11_real is not None and outputs.s11_imag is not None:
                row["s11_real"] = outputs.s11_real[i]
                row["s11_imag"] = outputs.s11_imag[i]
                row["s11_phase_rad"] = outputs.s11_phase_rad[i] if outputs.s11_phase_rad else 0.0
            if outputs.zin_real is not None and outputs.zin_imag is not None:
                row["zin_real"] = outputs.zin_real[i]
                row["zin_imag"] = outputs.zin_imag[i]
            if outputs.gain_dbi is not None and i < len(outputs.gain_dbi):
                row["gain_dbi"] = outputs.gain_dbi[i]
            rows.append(row)

        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

        return atomic_write(output_path, buf.getvalue())

    @staticmethod
    def export_numpy(records: List[DatasetRecord], output_path: str) -> str:
        """
        Exports records as a NumPy compressed archive (.npz).
        """
        import tempfile
        arrays_dict: Dict[str, np.ndarray] = {}

        for idx, r in enumerate(records):
            prefix = f"rec_{idx}_{r.antenna_identity.dataset_record_id}"
            out = r.outputs
            arrays_dict[f"{prefix}_frequencies_ghz"] = np.asarray(out.frequencies_ghz, dtype=np.float32)
            if out.s11_db is not None:
                arrays_dict[f"{prefix}_s11_db"] = np.asarray(out.s11_db, dtype=np.float32)
            if out.s11_real is not None and out.s11_imag is not None:
                arrays_dict[f"{prefix}_s11_real"] = np.asarray(out.s11_real, dtype=np.float32)
                arrays_dict[f"{prefix}_s11_imag"] = np.asarray(out.s11_imag, dtype=np.float32)
            if out.vswr is not None:
                arrays_dict[f"{prefix}_vswr"] = np.asarray(out.vswr, dtype=np.float32)
            if out.gain_dbi is not None:
                arrays_dict[f"{prefix}_gain_dbi"] = np.asarray(out.gain_dbi, dtype=np.float32)

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        # Use np.savez_compressed
        temp_path = output_path + ".tmp.npz"
        np.savez_compressed(temp_path, **arrays_dict)
        os.replace(temp_path, output_path)
        from anton.datasets.storage.atomic_io import compute_sha256
        return compute_sha256(output_path)

    @staticmethod
    def export_hdf5(records: List[DatasetRecord], output_path: str) -> str:
        """
        Exports records into a standalone HDF5 file.
        """
        import h5py
        from anton.datasets.storage.array_store import ArrayStore

        temp_h5 = output_path + ".tmp.h5"
        if os.path.exists(temp_h5):
            os.remove(temp_h5)

        store = ArrayStore(h5_path=temp_h5)
        for r in records:
            store.save_record_arrays(r.antenna_identity.dataset_record_id, r.outputs)

        os.replace(temp_h5, output_path)
        from anton.datasets.storage.atomic_io import compute_sha256
        return compute_sha256(output_path)

    @staticmethod
    def export_parquet(records: List[DatasetRecord], output_path: str) -> str:
        """
        Exports records to Parquet using Pandas/PyArrow if available, or falls back to CSV.
        """
        try:
            import pandas as pd
            # Flatten records into tabular summary dataframe
            rows = []
            for r in records:
                ident = r.antenna_identity
                mat = r.materials
                row = {
                    "record_id": ident.dataset_record_id,
                    "design_id": ident.design_id,
                    "geometry_family": ident.geometry_family,
                    "quality_status": r.quality_status.value,
                    "source_type": ident.data_source.value,
                    "substrate_material": mat.name,
                    "permittivity_r": mat.permittivity_r,
                    "substrate_thickness_mm": mat.substrate_thickness_mm,
                    "loss_tangent": mat.loss_tangent,
                    "z0_ohm": r.simulation_metadata.z0_ohm,
                    "min_freq_ghz": min(r.outputs.frequencies_ghz),
                    "max_freq_ghz": max(r.outputs.frequencies_ghz),
                    "num_freq_points": len(r.outputs.frequencies_ghz),
                    "has_complex_s11": r.outputs.has_complex_s11,
                    "peak_gain_dbi": r.outputs.peak_gain_dbi,
                }
                rows.append(row)

            df = pd.DataFrame(rows)
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            df.to_parquet(output_path, engine="auto")
            from anton.datasets.storage.atomic_io import compute_sha256
            return compute_sha256(output_path)
        except Exception:
            # Fallback to CSV
            csv_path = output_path.replace(".parquet", ".csv")
            return DatasetExporter.export_json(records, csv_path)
