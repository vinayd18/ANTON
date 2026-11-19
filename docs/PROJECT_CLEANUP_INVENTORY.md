# ANTON — Project Structure & Cleanup Inventory
## Comprehensive Audit of Codebase Assets, Artifacts, and Cache Files

**Audit Date**: November 19, 2026  
**Status**: COMPLETE  
**Auditor**: Antigravity Technical Lead & Software Architecture Team  

---

## 1. Inventory Classification Schema

Every file and directory in the ANTON project repository has been audited and classified into one of three strict policy categories:

1. **`MUST_PRESERVE`**: Essential for system integrity, Stage 1 canonical geometry, Stage 2 notebook reproduction, Stage 3.0 ML Model Registry, testing, research reproducibility, or user documentation. Must never be deleted.
2. **`REQUIRES_REVIEW`**: Transient scripts or non-canonical experimental helpers created during inspection or development. Requires user review or formal archiving before removal.
3. **`SAFE_TO_DELETE`**: Purely disposable bytecode caches, temporary compiler output, or test runner state that can be regenerated on demand without data loss.

---

## 2. Comprehensive Inventory by Component

### Category A: Core Geometry Engine & Stage 1 Architecture (`MUST_PRESERVE`)
| File / Directory Path | Classification | Size / Description | Rationale |
|---|---|---|---|
| `src/anton/models/geometry_schema.py` | `MUST_PRESERVE` | 13.9 KB | Canonical Pydantic geometry schema; single source of truth. |
| `src/anton/core/geometry_engine.py` | `MUST_PRESERVE` | 12.8 KB | Core geometry builder, extrusion, and boolean engine. |
| `src/anton/core/geometry_registry.py` | `MUST_PRESERVE` | 3.5 KB | Canonical geometry registry and lookup index. |
| `src/anton/core/units.py` | `MUST_PRESERVE` | 3.8 KB | SI unit converter and dimensional validator. |
| `src/anton/primitives/*.py` (10 files) | `MUST_PRESERVE` | ~11.5 KB | Analytic 2D primitives (circle, rectangle, polygon, arc, etc.). |
| `src/anton/operations/*.py` (4 files) | `MUST_PRESERVE` | ~13.2 KB | Affine transformations and 2D Shapely boolean operations. |
| `src/anton/cad/cadquery_engine.py` | `MUST_PRESERVE` | 8.8 KB | 3D CAD B-Rep solid extrusion and assembly generator. |
| `src/anton/cad/exporters.py` | `MUST_PRESERVE` | 5.2 KB | STEP and STL file exporter. |
| `src/anton/materials/database.py` | `MUST_PRESERVE` | 7.9 KB | Material reference database. |
| `src/anton/validation/*.py` (4 files) | `MUST_PRESERVE` | ~17.6 KB | Geometric rule validator and non-overlapping stackup checks. |
| `src/anton/visualization/*.py` | `MUST_PRESERVE` | 10.8 KB | Matplotlib 2D layout and SVG renderer. |
| `data/materials/materials.json` | `MUST_PRESERVE` | 2.6 KB | Default materials database (FR4, Rogers, Copper, Alumina). |
| `examples/*.json, *.step, *.stl, *.svg, *.png` | `MUST_PRESERVE` | ~6.5 MB | 8 verified canonical antenna designs and multi-format exports. |

---

### Category B: Stage 2 Notebook Generation Architecture (`MUST_PRESERVE`)
| File / Directory Path | Classification | Size / Description | Rationale |
|---|---|---|---|
| `src/anton/notebook/notebook_generator.py` | `MUST_PRESERVE` | 14.5 KB | Main Jupyter notebook orchestrator. |
| `src/anton/notebook/hfss_code_generator.py` | `MUST_PRESERVE` | 7.8 KB | Shared PyAEDT Python code generator. |
| `src/anton/notebook/stackup_code_generator.py` | `MUST_PRESERVE` | 5.8 KB | Non-overlapping layer stackup code emitter. |
| `src/anton/notebook/boundary_setup_generator.py`| `MUST_PRESERVE`| 8.3 KB | Radiation boundary and airbox emission logic. |
| `src/anton/notebook/feed_port_generator.py` | `MUST_PRESERVE` | 12.3 KB | Edge lumped port and coaxial probe port emitter. |
| `src/anton/notebook/solution_setup_generator.py`| `MUST_PRESERVE` | 7.3 KB | Solution setup and frequency sweep emitter. |
| `src/anton/notebook/result_extraction_generator.py`| `MUST_PRESERVE`| 12.4 KB| S11, VSWR, and Far-Field extraction code emitter. |
| `src/anton/notebook/notebook_validator.py` | `MUST_PRESERVE` | 9.2 KB | AST syntax checker and schema consistency auditor. |
| `notebooks/*_hfss.ipynb` (8 notebooks) | `MUST_PRESERVE` | ~320 KB | Standalone executable Jupyter notebooks for all 8 examples. |

---

### Category C: Stage 3.0 ML Model Registry & Storage (`MUST_PRESERVE`)
| File / Directory Path | Classification | Size / Description | Rationale |
|---|---|---|---|
| `src/anton/ml/registry/model_metadata.py` | `MUST_PRESERVE` | 7.4 KB | Strict Pydantic model schemas and tensor specs. |
| `src/anton/ml/registry/model_licensing.py` | `MUST_PRESERVE` | 7.1 KB | Open-source licensing auditor & Indian Patent 572928 detector. |
| `src/anton/ml/registry/model_compatibility.py` | `MUST_PRESERVE` | 14.8 KB | 10-dimension compatibility scoring engine. |
| `src/anton/ml/registry/model_evaluator.py` | `MUST_PRESERVE` | 11.1 KB | Ground-truth benchmark evaluator (MAE, RMSE, $R^2$, $\Delta f_r$). |
| `src/anton/ml/registry/model_loader.py` | `MUST_PRESERVE` | 8.8 KB | Secure checkpoint loader, SHA-256 verifier, immutability guard. |
| `src/anton/ml/registry/model_registry.py` | `MUST_PRESERVE` | 27.5 KB | Central registry, query engine, and default catalog. |
| `src/anton/ml/models/model_download_manifest.json`| `MUST_PRESERVE` | 4.1 KB | Cryptographic manifest of verified checkpoints. |
| `src/anton/ml/external/galabavamsi_antennanet/*` | `MUST_PRESERVE` | ~7.5 MB | 5 verified read-only PyTorch pretrained checkpoints. |
| `src/anton/ml/external/youxch_patch_mlp/*` | `MUST_PRESERVE` | 1.56 MB | 1 verified read-only Keras HDF5 pretrained checkpoint. |
| `src/anton/ml/workspaces/antennanet_workspace/*` | `MUST_PRESERVE` | ~16 KB | Manual fine-tuning workspace (7 complete files). |
| `src/anton/ml/workspaces/youxch_workspace/*` | `MUST_PRESERVE` | ~10 KB | Manual fine-tuning workspace (7 complete files). |
| `src/anton/ml/workspaces/jasti_workspace/*` | `MUST_PRESERVE` | ~7.5 KB | Manual fine-tuning workspace (7 complete files). |
| `src/anton/ml/ui/model_registry_ui.html` | `MUST_PRESERVE` | 18.9 KB | Interactive Model Registry UI dashboard. |
| `src/anton/ml/reports/*.json` (4 files) | `MUST_PRESERVE` | ~63 KB | Discovery, compatibility, catalog, and verification reports. |
| `backend/app/ml/*` | `MUST_PRESERVE` | ~9.2 MB | Synchronized bridge to backend runtime environment. |
| `data/deep_dive_raw.json` | `MUST_PRESERVE` | 29.3 KB | Raw GitHub API inspection trees for candidate repositories. |
| `data/benchmark_results.json` | `MUST_PRESERVE` | 1.8 KB | Baseline performance measurements. |

---

### Category D: Automated Test Suites & Test Fixtures (`MUST_PRESERVE`)
| File / Directory Path | Classification | Size / Description | Rationale |
|---|---|---|---|
| `tests/conftest.py` | `MUST_PRESERVE` | 2.1 KB | Shared pytest fixtures and test geometry builders. |
| `tests/test_schema.py` | `MUST_PRESERVE` | 2.3 KB | Stage 1 Pydantic schema validation tests. |
| `tests/test_primitives.py` | `MUST_PRESERVE` | 4.5 KB | Stage 1 analytic 2D primitives unit tests. |
| `tests/test_transformations.py` | `MUST_PRESERVE` | 3.1 KB | Stage 1 affine transformations tests. |
| `tests/test_boolean_operations.py` | `MUST_PRESERVE` | 4.9 KB | Stage 1 Shapely boolean operations & hole tests. |
| `tests/test_materials.py` | `MUST_PRESERVE` | 2.6 KB | Stage 1 material database tests. |
| `tests/test_cad_generation.py` | `MUST_PRESERVE` | 2.2 KB | Stage 1 CadQuery 3D solid extrusion tests. |
| `tests/test_serialization.py` | `MUST_PRESERVE` | 2.5 KB | Stage 1 JSON, SVG, PNG export tests. |
| `tests/test_validation.py` | `MUST_PRESERVE` | 7.3 KB | Stage 1 geometry and stackup validation tests. |
| `tests/test_notebook_generation.py` | `MUST_PRESERVE` | 13.1 KB | Stage 2 notebook structure & AST syntax tests. |
| `tests/test_pyaedt_mock_execution.py` | `MUST_PRESERVE` | 18.7 KB | Stage 2 PyAEDT API compatibility & mock execution tests. |
| `tests/test_model_registry.py` | `MUST_PRESERVE` | 10.7 KB | Stage 3.0 Model Registry unit & integration tests (18 tests). |

---

### Category E: Candidate Files for Review or Safe Cleanup
| File / Directory Path | Classification | Size | Rationale & Disposal Action |
|---|---|---|---|
| `src/**/__pycache__/*.pyc` (35+ files) | **`SAFE_TO_DELETE`** | ~350 KB | Compiled Python bytecode. Automatically re-created upon execution. |
| `tests/**/__pycache__/*.pyc` (13 files) | **`SAFE_TO_DELETE`** | ~300 KB | Compiled test bytecode. Automatically re-created upon pytest execution. |
| `.pytest_cache/*` | **`SAFE_TO_DELETE`** | ~10 KB | Pytest session cache (`v/cache/nodeids`, `lastfailed`). Re-created on test run. |
| `src/anton.egg-info/*` | **`SAFE_TO_DELETE`** | ~3 KB | Ephemeral packaging metadata from local `pip install -e .`. Fully regeneratable. |
| `scripts/test_registry_smoke.py` | **`REQUIRES_REVIEW`** | 1.7 KB | Temporary smoke test script used during initial development. Safe to archive or keep in `scripts/`. |
| `scripts/generate_antennanet_notebook.py` | **`REQUIRES_REVIEW`** | 2.4 KB | Workspace generator script. Outputs are already written. Safe to keep in `scripts/`. |
| `scripts/generate_youxch_notebook.py` | **`REQUIRES_REVIEW`** | 2.1 KB | Workspace generator script. Outputs are already written. Safe to keep in `scripts/`. |
| `scripts/generate_jasti_notebook.py` | **`REQUIRES_REVIEW`** | 1.8 KB | Workspace generator script. Outputs are already written. Safe to keep in `scripts/`. |

---

## 3. Summary of Cleanup Strategy

1. **Immediate Safe Deletion**:
   - Clean up Python `__pycache__` directories across `src/` and `tests/`.
   - Clear `.pytest_cache`.
   - Remove ephemeral `src/anton.egg-info`.
2. **Preservation**:
   - **All** geometry files, 3D CAD models, notebooks, material databases, model weights, workspaces, documentation, and test suites are strictly preserved.
3. **Review**:
   - The helper scripts in `scripts/` will be retained as documented utilities for audit repeatability.

