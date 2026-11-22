"""
Automated Tests for Dataset Storage and Management Subsystem (Stage 3.4).
"""

import os
import tempfile
import pytest
import numpy as np

from anton.datasets.schema import (
    AntennaIdentity,
    DatasetRecord,
    ElectromagneticOutputsRecord,
    MaterialPropertiesRecord,
    ProvenanceRecord,
    QualityStatus,
    SimulationMetadataRecord,
    SourceType,
)
from anton.datasets.storage import (
    MetadataDatabase,
    ArrayStore,
    DatasetStorageManager,
    DatasetExporter,
    atomic_write,
    compute_sha256,
    is_safe_path,
)


def sample_record(record_id="rec_store_01"):
    freqs = [1.0, 2.0, 3.0, 4.0]
    outputs = ElectromagneticOutputsRecord(
        frequencies_ghz=freqs,
        s11_db=[-5.0, -18.0, -8.0, -4.0],
        s11_magnitude=[0.56, 0.125, 0.398, 0.63],
        s11_real=[0.5, 0.1, -0.3, 0.6],
        s11_imag=[0.25, 0.075, 0.26, -0.19],
        vswr=[3.5, 1.28, 2.32, 4.4],
        zin_real=[45.0, 52.0, 38.0, 60.0],
        zin_imag=[10.0, 2.0, -15.0, 5.0],
        gain_dbi=[2.0, 6.5, 4.0, 1.5],
    )
    identity = AntennaIdentity(
        design_id="design_s_01",
        geometry_id="geo_s_01",
        geometry_hash="d" * 64,
        geometry_family="RECTANGULAR_PATCH",
        dataset_record_id=record_id,
        data_source=SourceType.HFSS_SIMULATION,
    )
    materials = MaterialPropertiesRecord(
        name="FR4_epoxy",
        permittivity_r=4.4,
        substrate_thickness_mm=1.6,
    )
    sim_meta = SimulationMetadataRecord(
        solver_name="HFSS",
        is_converged=True,
    )
    provenance = ProvenanceRecord(
        source_type=SourceType.HFSS_SIMULATION,
        source_filename="sweep.s1p",
    )
    return DatasetRecord(
        antenna_identity=identity,
        geometry={"name": "test", "family": "RECTANGULAR_PATCH", "patch": {"width": 30.0, "length": 25.0}},
        materials=materials,
        simulation_metadata=sim_meta,
        outputs=outputs,
        provenance=provenance,
        quality_status=QualityStatus.VERIFIED,
    )


def test_atomic_write_and_path_safety():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        test_file = os.path.join(tmpdir, "test_atomic.txt")
        sha = atomic_write(test_file, "hello world from anton")
        assert os.path.exists(test_file)
        assert len(sha) == 64

        # Safe path checks
        assert is_safe_path(tmpdir, test_file) is True
        evil_path = os.path.join(tmpdir, "../../windows/system32")
        assert is_safe_path(tmpdir, evil_path) is False


def test_metadata_database_crud():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = os.path.join(tmpdir, "test_meta.db")
        db = MetadataDatabase(db_path=db_path)

        rec = sample_record()
        rec_id = db.save_record(rec)
        assert rec_id == "rec_store_01"

        # Retrieve
        fetched = db.get_record(rec_id)
        assert fetched is not None
        assert fetched["antenna_identity"]["dataset_record_id"] == "rec_store_01"

        # List
        records = db.list_records(geometry_family="RECTANGULAR_PATCH")
        assert len(records) == 1
        assert records[0]["has_complex_s11"] is True

        # Statistics
        stats = db.get_statistics()
        assert stats["total_records"] == 1
        assert stats["unique_geometries"] == 1


def test_hdf5_array_store():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        h5_path = os.path.join(tmpdir, "test_arrays.h5")
        store = ArrayStore(h5_path=h5_path)

        rec = sample_record("rec_h5_01")
        store.save_record_arrays("rec_h5_01", rec.outputs)

        assert store.has_record_arrays("rec_h5_01") is True

        # Load
        arrays = store.load_record_arrays("rec_h5_01")
        assert "frequencies_ghz" in arrays
        assert "s11_db" in arrays
        assert "zin_real" in arrays
        assert len(arrays["frequencies_ghz"]) == 4
        assert abs(arrays["frequencies_ghz"][1] - 2.0) < 1e-4

        # Delete
        assert store.delete_record_arrays("rec_h5_01") is True
        assert store.has_record_arrays("rec_h5_01") is False


def test_dataset_storage_manager():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        mgr = DatasetStorageManager(
            db_path=os.path.join(tmpdir, "meta.db"),
            h5_path=os.path.join(tmpdir, "arrays.h5"),
        )
        rec = sample_record("rec_mgr_01")
        rec_id = mgr.save_record(rec)

        assert mgr.get_record(rec_id) is not None
        arrays = mgr.load_arrays(rec_id)
        assert "s11_db" in arrays


def test_dataset_exporter():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        rec = sample_record("rec_exp_01")

        # JSON Export
        json_file = os.path.join(tmpdir, "export.json")
        DatasetExporter.export_json([rec], json_file)
        assert os.path.exists(json_file)

        # CSV Export
        csv_file = os.path.join(tmpdir, "export.csv")
        DatasetExporter.export_csv(rec, csv_file)
        assert os.path.exists(csv_file)

        # NumPy Export
        npz_file = os.path.join(tmpdir, "export.npz")
        DatasetExporter.export_numpy([rec], npz_file)
        assert os.path.exists(npz_file)
        with np.load(npz_file) as data:
            assert any("frequencies_ghz" in k for k in data.files)

        # HDF5 Export
        h5_file = os.path.join(tmpdir, "export.h5")
        DatasetExporter.export_hdf5([rec], h5_file)
        assert os.path.exists(h5_file)
