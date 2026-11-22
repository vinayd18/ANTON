"""
Automated Tests for Dataset Backend API & Frontend Integration (Stage 3.8).
"""

import tempfile
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from anton.datasets.storage import DatasetStorageManager


@pytest.fixture(scope="module")
def client():
    # Use temporary DB and HDF5 for isolated API tests
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        import backend.app.api.datasets as ds_api
        ds_api._STORAGE = DatasetStorageManager(
            db_path=f"{tmpdir}/api_meta.db",
            h5_path=f"{tmpdir}/api_arrays.h5",
        )
        with TestClient(app) as c:
            yield c
        ds_api._STORAGE = None


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["dataset_engine"] == "active"


def test_statistics_initial(client):
    res = client.get("/api/datasets/statistics")
    assert res.status_code == 200
    data = res.json()
    assert "total_records" in data
    assert "unique_geometries" in data


def test_import_touchstone_via_api(client):
    touchstone_text = """! HFSS exported S11
# GHz S DB R 50
1.0   -4.5   0.0
2.0  -18.2   0.0
3.0   -6.1   0.0
"""
    payload = {
        "file_content": touchstone_text,
        "is_base64": False,
        "filename": "patch_hfss.s1p",
        "geometry_family": "RECTANGULAR_PATCH",
        "patch_width_mm": 30.0,
        "patch_length_mm": 25.0,
        "substrate_thickness_mm": 1.6,
        "permittivity_r": 4.4,
        "solver_name": "HFSS",
        "source_type": "HFSS_SIMULATION",
        "z0_ohm": 50.0,
    }

    res = client.post("/api/datasets/import", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "record_id" in data
    rec_id = data["record_id"]

    # Verify record in listing
    list_res = client.get("/api/datasets/records")
    assert list_res.status_code == 200
    records = list_res.json()["records"]
    assert any(r["record_id"] == rec_id for r in records)

    # Get single record
    get_res = client.get(f"/api/datasets/records/{rec_id}")
    assert get_res.status_code == 200
    assert get_res.json()["antenna_identity"]["geometry_family"] == "RECTANGULAR_PATCH"

    # Get quality report
    qual_res = client.get(f"/api/datasets/records/{rec_id}/quality")
    assert qual_res.status_code == 200
    assert "passed_checks" in qual_res.json()

    # Get responses
    resp_res = client.get(f"/api/datasets/records/{rec_id}/responses")
    assert resp_res.status_code == 200
    assert len(resp_res.json()["frequencies_ghz"]) == 3


def test_prepare_and_export_via_api(client):
    # Prepare ML split
    prep_res = client.post(
        "/api/datasets/prepare",
        json={"train_ratio": 0.7, "val_ratio": 0.15, "test_ratio": 0.15, "random_seed": 42},
    )
    assert prep_res.status_code == 200
    assert prep_res.json()["status"] == "success"

    # Export
    exp_res = client.post("/api/datasets/export", json={"format": "json"})
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert exp_data["status"] == "success"
    exp_id = exp_data["export_id"]

    # Download
    down_res = client.get(f"/api/datasets/exports/{exp_id}?format=json")
    assert down_res.status_code == 200


def test_path_traversal_rejection(client):
    evil_res = client.get("/api/datasets/exports/../../etc/passwd")
    assert evil_res.status_code in (404, 400)


def test_ui_endpoints(client):
    ds_ui = client.get("/ui/datasets")
    assert ds_ui.status_code == 200
    assert "ANTON Electromagnetic Datasets" in ds_ui.text

    mod_ui = client.get("/ui/models")
    assert mod_ui.status_code == 200
