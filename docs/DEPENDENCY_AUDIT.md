# ANTON — Dependency Audit & Environment Architecture
## Modular Dependency Groups, Version Constraints, and Framework Isolation

**Report Date**: November 19, 2026  
**Status**: COMPLETE & VERIFIED  
**Auditor**: Antigravity Technical Lead & Software Architecture Team  

---

## 1. Executive Summary

In compliance with Section 7 of the Stage 3.0 requirements, a comprehensive dependency audit of the ANTON platform was conducted. The objective is to keep ANTON lightweight, modular, maintainable, and reproducible across diverse operating environments without forcing unnecessary heavyweight packages.

### Key Architectural Decision on ML Frameworks
Heavyweight deep-learning frameworks (such as PyTorch and TensorFlow/Keras) are **NOT included as mandatory base dependencies** in ANTON's primary `dependencies` list. 
- **Rationale**: Forcing `torch` (which downloads >2 GB of CUDA/C++ binaries) or `tensorflow` into the base geometry engine would break lightweight deployment in embedded, CAD-only, or CI environments.
- **Solution**: Heavyweight dependencies are organized into optional extras (`project.optional-dependencies`), while original pretrained weights are inspected safely via binary headers and loaded in isolated, dedicated user workspaces.

---

## 2. Dependency Organization & Modular Groups

The configuration in [pyproject.toml](file:///c:/Users/adewa/Pictures/Anton%202/pyproject.toml) organizes packages into clean, functional groups:

| Group Name | Packages & Version Constraints | Functional Purpose | Runtime Scope |
|---|---|---|---|
| **`core`** (Base) | `pydantic>=2.0`<br>`numpy>=1.24.0`<br>`shapely>=2.0.0`<br>`sympy>=1.12` | Canonical geometry schemas, 2D analytic primitives, SI unit management, and 2D Shapely boolean planar operations. | Minimal / Mandatory |
| **`cad`** | `cadquery>=2.1` | 3D solid B-Rep extrusion, OpenCASCADE kernel operations, and STEP/STL solid exports. | 3D CAD Modeling |
| **`visualization`** | `matplotlib>=3.7.0` | 2D antenna layout visualization, SVG generation, and PNG rasterization. | Rendering |
| **`notebook`** | `nbformat>=5.0` | Standalone executable Jupyter Notebook generation (.ipynb) for external ANSYS HFSS reproduction. | Notebook Emitter |
| **`data`** | `scipy>=1.10.0`<br>`pandas>=2.0.0`<br>`openpyxl>=3.1.0` | Parsing simulation datasets (e.g. METU-SIMPL Excel/CSV datasets) and scientific curve fitting. | Benchmark Datasets |
| **`ml`** | `scikit-learn>=1.0.0`<br>`h5py>=3.8.0` | Random Forest surrogate modeling (Jasti), HDF5 weight inspection (Youxch), and model evaluation metrics. | ML Registry / Benchmarks |
| **`dev`** | `pytest>=7.0.0`<br>`coverage>=7.0.0` | Automated testing, unit verification, and code coverage measurement. | Testing |
| **`all`** | `anton[core,cad,visualization,notebook,data,ml,dev]` | Complete umbrella installation combining all platform capabilities. | Full Platform |

---

## 3. Version Compatibility & Conflict Analysis

1. **Python Interpreter Support**:
   - Platform requires `python >= 3.10` and has been verified against `Python 3.13.2`.
2. **Pydantic v2 Migration**:
   - `pydantic >= 2.0` is strictly enforced. All models utilize Pydantic v2 syntax (`@field_validator`, `@model_validator`, `model_dump()`, `model_dump_json()`, `model_validate_json()`).
3. **Shapely 2.0 Compatibility**:
   - Uses modern vectorized Shapely 2.0 primitives without deprecated GEOS wrappers.
4. **Zero Conflicting Packages**:
   - No pinned exact versions (`==`) that would cause dependency resolution conflicts in upstream environments. All constraints utilize safe minimum bounds (`>=`).

---

## 4. Reproducible Environment Guidelines

To install ANTON according to your operational needs:

```bash
# Minimal CAD & Geometry Only (Ultra-lightweight)
pip install -e ".[core,cad]"

# Full Research Platform with Notebook Generation & ML Registry
pip install -e ".[all]"

# Running Automated Test Suite
pytest tests/ -v
```

