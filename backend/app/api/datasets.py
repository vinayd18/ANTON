"""
FastAPI Dataset Management Router.

Endpoints for:
- Listing and querying electromagnetic dataset collections and records
- Ingesting Touchstone (.s1p, .s2p) and CSV simulation reports via JSON payloads
- Inspecting record metadata, canonical geometry, and frequency responses
- Validation execution and quality report retrieval
- Leakage-free ML dataset splitting and preparation
- Multi-format exports (JSON, CSV, HDF5, NPZ)
"""

from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

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
from anton.datasets.importers import DatasetImporter
from anton.datasets.validation import QualityClassifier, ValidationReportGenerator
from anton.datasets.storage import DatasetStorageManager, DatasetExporter, is_safe_path
from anton.datasets.ml import DatasetSplitter

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

_STORAGE: Optional[DatasetStorageManager] = None
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB limit


def get_storage() -> DatasetStorageManager:
    global _STORAGE
    if _STORAGE is None:
        _STORAGE = DatasetStorageManager()
    return _STORAGE


class ImportDatasetRequest(BaseModel):
    file_content: str = Field(description="Raw file content (text) or base64 encoded bytes")
    is_base64: bool = Field(default=False)
    filename: str = Field(default="data.s1p")
    geometry_family: str = Field(default="RECTANGULAR_PATCH")
    patch_width_mm: float = Field(default=30.0, gt=0.0)
    patch_length_mm: float = Field(default=30.0, gt=0.0)
    substrate_thickness_mm: float = Field(default=1.6, gt=0.0)
    permittivity_r: float = Field(default=4.4, gt=0.0)
    loss_tangent: float = Field(default=0.02, ge=0.0)
    material_name: str = Field(default="FR4_epoxy")
    solver_name: str = Field(default="HFSS")
    source_type: str = Field(default="HFSS_SIMULATION")
    z0_ohm: float = Field(default=50.0, gt=0.0)


class PrepareDatasetRequest(BaseModel):
    train_ratio: float = Field(default=0.70, ge=0.1, le=0.9)
    val_ratio: float = Field(default=0.15, ge=0.05, le=0.45)
    test_ratio: float = Field(default=0.15, ge=0.05, le=0.45)
    random_seed: int = Field(default=42)
    geometry_family: Optional[str] = None
    target_f_min: Optional[float] = None
    target_f_max: Optional[float] = None
    num_points: int = Field(default=101)


class ExportDatasetRequest(BaseModel):
    record_ids: Optional[List[str]] = None
    format: str = Field(default="json", pattern="^(json|csv|hdf5|numpy)$")
    geometry_family: Optional[str] = None


@router.get("", summary="List Dataset Collections")
def list_datasets() -> Dict[str, Any]:
    storage = get_storage()
    stats = storage.db.get_statistics()
    return {
        "status": "success",
        "dataset_statistics": stats,
    }


@router.get("/statistics", summary="Dataset Summary Statistics")
def get_statistics() -> Dict[str, Any]:
    storage = get_storage()
    return storage.db.get_statistics()


@router.get("/records", summary="List and Filter Records")
def list_records(
    geometry_family: Optional[str] = Query(None, description="Filter by geometry family"),
    source_type: Optional[str] = Query(None, description="Filter by source type"),
    quality_status: Optional[str] = Query(None, description="Filter by quality status"),
    min_freq: Optional[float] = Query(None, description="Minimum frequency GHz"),
    max_freq: Optional[float] = Query(None, description="Maximum frequency GHz"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    storage = get_storage()
    records = storage.db.list_records(
        geometry_family=geometry_family,
        source_type=source_type,
        quality_status=quality_status,
        min_freq=min_freq,
        max_freq=max_freq,
        limit=limit,
        offset=offset,
    )
    return {
        "total": len(records),
        "limit": limit,
        "offset": offset,
        "records": records,
    }


@router.get("/records/{record_id}", summary="Get Full Record Metadata")
def get_record(record_id: str) -> Dict[str, Any]:
    storage = get_storage()
    raw = storage.get_record(record_id)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record '{record_id}' not found.",
        )
    return raw


@router.get("/records/{record_id}/quality", summary="Get Record Validation Quality Report")
def get_record_quality(record_id: str) -> Dict[str, Any]:
    storage = get_storage()
    report = storage.db.get_quality_report(record_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quality report for record '{record_id}'.",
        )
    return report


@router.get("/records/{record_id}/responses", summary="Get Numerical Frequency Responses")
def get_record_responses(record_id: str) -> Dict[str, Any]:
    storage = get_storage()
    if not storage.arrays.has_record_arrays(record_id):
        rec = storage.get_record(record_id)
        if not rec:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
        outputs = rec.get("outputs", {})
        return {
            "record_id": record_id,
            "frequencies_ghz": outputs.get("frequencies_ghz", []),
            "s11_db": outputs.get("s11_db"),
            "vswr": outputs.get("vswr"),
            "s11_real": outputs.get("s11_real"),
            "s11_imag": outputs.get("s11_imag"),
            "gain_dbi": outputs.get("gain_dbi"),
        }

    arrays = storage.arrays.load_record_arrays(record_id)
    serialized = {k: v.tolist() for k, v in arrays.items()}
    serialized["record_id"] = record_id
    return serialized


@router.post("/import", summary="Import Simulation / Measurement File")
def import_dataset_file(req: ImportDatasetRequest) -> Dict[str, Any]:
    if req.is_base64:
        try:
            raw_bytes = base64.b64decode(req.file_content)
            content_str = raw_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to decode base64: {e}")
    else:
        content_str = req.file_content

    if len(content_str.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // (1024*1024)} MB",
        )

    filename = req.filename or "upload.s1p"
    safe_suffix = os.path.splitext(filename)[1].lower() or ".s1p"

    with tempfile.NamedTemporaryFile(delete=False, suffix=safe_suffix, mode="w", encoding="utf-8") as tmp:
        tmp.write(content_str)
        tmp_path = tmp.name

    try:
        importer = DatasetImporter(default_z0=req.z0_ohm)
        outputs, parse_meta = importer.import_file(tmp_path)

        sub_w = round(req.patch_width_mm * 2.0, 3)
        sub_l = round(req.patch_length_mm * 2.0, 3)
        geometry_dict = {
            "name": f"imported_{req.geometry_family.lower()}_{filename}",
            "family": req.geometry_family,
            "patch": {
                "shape": req.geometry_family,
                "width": req.patch_width_mm,
                "length": req.patch_length_mm,
                "metal_thickness": 0.035,
            },
            "substrate": {
                "width": sub_w,
                "length": sub_l,
                "thickness": req.substrate_thickness_mm,
                "material": req.material_name,
            },
            "ground_plane": {
                "type": "SOLID",
                "width": sub_w,
                "length": sub_l,
                "metal_thickness": 0.035,
            },
            "feed": {
                "type": "MICROSTRIP_LINE",
                "width": 3.0,
                "position": [0.0, -req.patch_length_mm / 2.0],
            },
        }

        geo_str = json.dumps(geometry_dict, sort_keys=True)
        geo_hash = hashlib.sha256(geo_str.encode("utf-8")).hexdigest()
        file_sha256 = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

        rec_id = f"rec_{file_sha256[:10]}_{int(datetime.datetime.now().timestamp())}"

        src_type = SourceType(req.source_type) if req.source_type in SourceType.__members__ else SourceType.HFSS_SIMULATION

        identity = AntennaIdentity(
            design_id=f"design_{geo_hash[:10]}",
            geometry_id=f"geo_{geo_hash[:10]}",
            geometry_hash=geo_hash,
            geometry_family=req.geometry_family,
            dataset_record_id=rec_id,
            data_source=src_type,
            source_reference=filename,
        )

        materials = MaterialPropertiesRecord(
            name=req.material_name,
            permittivity_r=req.permittivity_r,
            permeability_r=1.0,
            loss_tangent=req.loss_tangent,
            substrate_thickness_mm=req.substrate_thickness_mm,
        )

        sim_metadata = SimulationMetadataRecord(
            solver_name=req.solver_name,
            z0_ohm=req.z0_ohm,
            is_converged=True,
            convergence_status="Imported simulation file",
        )

        provenance = ProvenanceRecord(
            source_type=src_type,
            source_filename=filename,
            source_file_sha256=file_sha256,
            processing_history=[{"step": "file_upload_import", "status": "completed"}],
        )

        record = DatasetRecord(
            antenna_identity=identity,
            geometry=geometry_dict,
            materials=materials,
            simulation_metadata=sim_metadata,
            outputs=outputs,
            provenance=provenance,
            quality_status=QualityStatus.UNVERIFIED,
            tags=["uploaded", req.geometry_family.lower()],
        )

        report_gen = ValidationReportGenerator()
        report = report_gen.generate_record_report(record)

        storage = get_storage()
        storage.save_record(record)

        return {
            "status": "success",
            "record_id": rec_id,
            "quality_status": record.quality_status.value,
            "frequency_points": len(outputs.frequencies_ghz),
            "freq_min_ghz": min(outputs.frequencies_ghz),
            "freq_max_ghz": max(outputs.frequencies_ghz),
            "has_complex_s11": outputs.has_complex_s11,
            "validation_report": report,
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/validate", summary="Run Validation on Records")
def validate_records(record_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    storage = get_storage()
    if not record_ids:
        recs_meta = storage.db.list_records(limit=1000)
        record_ids = [r["record_id"] for r in recs_meta]

    results = []
    report_gen = ValidationReportGenerator()

    for rid in record_ids:
        raw = storage.get_record(rid)
        if raw:
            rec = DatasetRecord.model_validate(raw)
            rep = report_gen.generate_record_report(rec)
            storage.db.save_quality_report(rid, rep)
            results.append({"record_id": rid, "quality_status": rep["quality_status"], "passed": len(rep["passed_checks"])})

    return {
        "status": "success",
        "validated_count": len(results),
        "results": results,
    }


@router.post("/prepare", summary="Prepare Leakage-Free ML Dataset Split")
def prepare_ml_dataset(req: PrepareDatasetRequest) -> Dict[str, Any]:
    storage = get_storage()
    records_meta = storage.db.list_records(
        geometry_family=req.geometry_family,
        limit=5000,
    )

    records = []
    for m in records_meta:
        raw = storage.get_record(m["record_id"])
        if raw:
            records.append(DatasetRecord.model_validate(raw))

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No matching records found to prepare dataset.",
        )

    splitter = DatasetSplitter(
        train_ratio=req.train_ratio,
        val_ratio=req.val_ratio,
        test_ratio=req.test_ratio,
        random_seed=req.random_seed,
    )
    train_recs, val_recs, test_recs, manifest = splitter.split_records(records)

    ds_id = f"ds_prep_{int(datetime.datetime.now().timestamp())}"
    storage.db.create_dataset_collection(
        dataset_id=ds_id,
        name=f"ML Dataset ({req.geometry_family or 'All'})",
        description=f"Generated split with seed {req.random_seed}",
    )
    for r in train_recs:
        storage.db.assign_to_split(ds_id, r.antenna_identity.dataset_record_id, "train")
    for r in val_recs:
        storage.db.assign_to_split(ds_id, r.antenna_identity.dataset_record_id, "val")
    for r in test_recs:
        storage.db.assign_to_split(ds_id, r.antenna_identity.dataset_record_id, "test")

    return {
        "status": "success",
        "dataset_id": ds_id,
        "manifest": manifest,
    }


@router.post("/export", summary="Export Records to File")
def export_dataset(req: ExportDatasetRequest) -> Dict[str, Any]:
    storage = get_storage()
    recs_meta = storage.db.list_records(
        geometry_family=req.geometry_family,
        limit=1000,
    )
    if req.record_ids:
        target_ids = set(req.record_ids)
        recs_meta = [r for r in recs_meta if r["record_id"] in target_ids]

    records = []
    for m in recs_meta:
        raw = storage.get_record(m["record_id"])
        if raw:
            records.append(DatasetRecord.model_validate(raw))

    if not records:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No records to export.")

    export_dir = os.path.abspath("data/datasets/exports")
    os.makedirs(export_dir, exist_ok=True)
    export_id = f"export_{int(datetime.datetime.now().timestamp())}"

    if req.format == "json":
        out_file = os.path.join(export_dir, f"{export_id}.json")
        DatasetExporter.export_json(records, out_file)
    elif req.format == "csv":
        out_file = os.path.join(export_dir, f"{export_id}.csv")
        DatasetExporter.export_csv(records[0], out_file)
    elif req.format == "numpy":
        out_file = os.path.join(export_dir, f"{export_id}.npz")
        DatasetExporter.export_numpy(records, out_file)
    elif req.format == "hdf5":
        out_file = os.path.join(export_dir, f"{export_id}.h5")
        DatasetExporter.export_hdf5(records, out_file)
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format.")

    return {
        "status": "success",
        "export_id": export_id,
        "format": req.format,
        "record_count": len(records),
        "download_url": f"/api/datasets/exports/{export_id}?format={req.format}",
    }


@router.get("/exports/{export_id}", summary="Download Exported Bundle")
def download_export(export_id: str, format: str = "json"):
    export_dir = os.path.abspath("data/datasets/exports")
    ext_map = {"json": ".json", "csv": ".csv", "numpy": ".npz", "hdf5": ".h5"}
    ext = ext_map.get(format.lower(), ".json")
    file_path = os.path.join(export_dir, f"{export_id}{ext}")

    if not is_safe_path(export_dir, file_path) or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export bundle not found.")

    return FileResponse(
        path=file_path,
        filename=os.path.basename(file_path),
        media_type="application/octet-stream",
    )
