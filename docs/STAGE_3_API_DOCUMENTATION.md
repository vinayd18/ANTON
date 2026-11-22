# ANTON — Stage 3 Backend API Documentation

---

### 1. Overview

The ANTON backend exposes a REST API built with FastAPI, providing programmatic access to electromagnetic dataset management, physical validation, leakage-free ML preparation, and model registry queries.

- **Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **Web Dashboard**: `http://localhost:8000/ui/datasets`

---

### 2. Dataset Management Endpoints (`/api/datasets`)

#### `GET /api/datasets`
Returns high-level dataset collections and aggregate statistics.
- **Response**: `200 OK`
```json
{
  "status": "success",
  "dataset_statistics": {
    "total_records": 12,
    "unique_geometries": 8,
    "geometry_family_distribution": {"RECTANGULAR_PATCH": 8, "CIRCULAR_PATCH": 4}
  }
}
```

#### `GET /api/datasets/statistics`
Returns detailed KPI metrics across records, designs, sources, and quality levels.
- **Response**: `200 OK`

#### `GET /api/datasets/records`
Lists records with pagination and multi-column filtering.
- **Query Parameters**:
  - `geometry_family` (string, optional)
  - `source_type` (string, optional)
  - `quality_status` (string, optional)
  - `min_freq` (float, optional)
  - `max_freq` (float, optional)
  - `limit` (int, default: 50, max: 500)
  - `offset` (int, default: 0)
- **Response**: `200 OK` with `{ "total": int, "limit": int, "offset": int, "records": [...] }`

#### `GET /api/datasets/records/{record_id}`
Retrieves full canonical metadata and geometry definition for a single record.
- **Response**: `200 OK` or `404 Not Found`

#### `GET /api/datasets/records/{record_id}/quality`
Retrieves the automated validation report, detailing passed checks, warnings, and failed criteria.
- **Response**: `200 OK` or `404 Not Found`

#### `GET /api/datasets/records/{record_id}/responses`
Retrieves numerical frequency response series ($S_{11}$, VSWR, $Z_{\text{in}}$, Gain).
- **Response**: `200 OK` with numerical lists.

#### `POST /api/datasets/import`
Ingests an electromagnetic simulation file (Touchstone `.s1p`/`.s2p` or CSV table) via JSON payload.
- **Request Body (`application/json`)**:
```json
{
  "file_content": "# GHz S DB R 50\n1.0 -5.0 0.0\n2.0 -20.0 0.0\n3.0 -4.0 0.0",
  "is_base64": false,
  "filename": "patch_hfss.s1p",
  "geometry_family": "RECTANGULAR_PATCH",
  "patch_width_mm": 30.0,
  "patch_length_mm": 25.0,
  "substrate_thickness_mm": 1.6,
  "permittivity_r": 4.4,
  "solver_name": "HFSS",
  "source_type": "HFSS_SIMULATION",
  "z0_ohm": 50.0
}
```
- **Response**: `200 OK` with `{ "status": "success", "record_id": str, "quality_status": str, "validation_report": {...} }`
- **Error Codes**: `400 Bad Request`, `413 Payload Too Large` ($>50\,\text{MB}$).

#### `POST /api/datasets/validate`
Executes validation on specified or all records and updates quality ratings in the database.
- **Request Body**: `{"record_ids": ["rec_001", "rec_002"]}` (or omit for all).
- **Response**: `200 OK` with validation summary.

#### `POST /api/datasets/prepare`
Partitions dataset records into Train, Validation, and Test splits with zero geometry leakage.
- **Request Body**:
```json
{
  "train_ratio": 0.70,
  "val_ratio": 0.15,
  "test_ratio": 0.15,
  "random_seed": 42,
  "geometry_family": "RECTANGULAR_PATCH"
}
```
- **Response**: `200 OK` with split manifest and `dataset_id`.

#### `POST /api/datasets/export`
Packages records into a downloadable export bundle.
- **Request Body**:
```json
{
  "format": "json", // "json", "csv", "numpy", or "hdf5"
  "geometry_family": "RECTANGULAR_PATCH"
}
```
- **Response**: `200 OK` with `download_url`.

#### `GET /api/datasets/exports/{export_id}`
Downloads the generated export bundle. Enforces safe path validation to block directory traversal.
- **Response**: `200 OK` (binary stream) or `404 Not Found`.

---

### 3. Model Registry Endpoints (`/api/ml`)

#### `GET /api/ml/models`
Returns all 10 registered models and surrogate networks in ANTON's Model Registry.
- **Response**: `200 OK` with list of model definitions.

#### `GET /api/ml/models/{model_id}`
Retrieves detailed metadata for a specific model.
- **Response**: `200 OK` or `404 Not Found`.

#### `GET /api/ml/models/{model_id}/compatibility`
Retrieves geometry and input tensor compatibility constraints for a specific model.
- **Response**: `200 OK` with compatibility assessment dictionary.

