# ANTON — STAGE 3.0 MODEL REGISTRY CORRECTIONS REPORT

**Document ID:** `ANTON-DOC-S3-009`  
**Date:** November 19, 2026  
**Status:** COMPLETED & INTEGRATED  
**Author:** AI Technical Specialist & Software Architecture Team  
**System Impact:** `src/anton/ml/registry/`, `backend/app/ml/`, `tests/test_model_registry.py`  

---

## 1. Context and Problem Statement

During the initial Stage 3.0 implementation, an architectural ambiguity was identified where distinct types of assets were conflated:
1. **Datasets were grouped with models**: For example, `metu_simpl_microstrip` is an authentic ANSYS HFSS simulation database (containing `.xlsx` curves and `.aedt` projects), yet it was registered alongside executable neural network weights.
2. **Coupled readiness indicators**: Production readiness and fine-tuning readiness were loosely coupled to checkpoint availability rather than being independent, verifiable architectural attributes.
3. **Repository code & binary duplication**: Both `src/anton/ml/` and `backend/app/ml/` maintained duplicate copies of multi-megabyte binary weights (`.pt`, `.pth`, `.h5`) and redundant registry schemas, creating risks of divergence.

---

## 2. Key Corrections Implemented

### 2.1. Explicit Entity Type Separation (`ModelEntityType`)
Registered entries in the ANTON Model Registry are now categorized using the strict `ModelEntityType` enumeration:
- **`PRETRAINED_MODEL`**: Candidates possessing downloadable, verified static neural network weights capable of forward-pass execution (e.g. `galabavamsi_antennanet`, `youxch_patch_mlp`).
- **`TRAINING_IMPLEMENTATION`**: Research repositories providing Python/PyTorch/TensorFlow network definitions and training scripts, but without committed pre-trained weights (e.g. `udaykdk_pixelant`, `vish1comp_antenna_benchmark`, `jasti_rf_surrogate`).
- **`DATASET`**: Pure electromagnetic simulation corpora or measurement databases intended as ground-truth benchmarks or training sets, not executable models (e.g. `metu_simpl_microstrip`).
- **`RESEARCH_REFERENCE`**: Academic publications, patents, or theoretical formulations without directly executable code.

### 2.2. Independent Architectural Fields in `ModelMetadata`
The canonical Pydantic model (`src/anton/ml/registry/model_metadata.py`) now defines independent, decoupled fields:

```python
class ModelMetadata(BaseModel):
    # Entity Classification
    entity_type: ModelEntityType = ModelEntityType.RESEARCH_REFERENCE
    
    # Decoupled Checkpoint Indicators
    checkpoint_available: bool = False
    checkpoint_availability: bool = False
    checkpoint_load_verification: CheckpointLoadVerification = CheckpointLoadVerification.NOT_APPLICABLE
    inference_verification: InferenceVerification = InferenceVerification.NOT_APPLICABLE
    
    # Decoupled Lifecycle and Readiness Indicators
    fine_tuning_readiness: FineTuningReadiness = FineTuningReadiness.NOT_READY
    production_readiness: bool = False
    
    # Structured Compatibility Dimensions
    geometry_compatibility: Dict[str, Any] = Field(default_factory=dict)
    dataset_compatibility: Dict[str, Any] = Field(default_factory=dict)
```

### 2.3. Strict Validation Rule for `production_readiness`
To prevent premature or unjustified claims of production deployment:
```python
@field_validator("production_readiness")
@classmethod
def validate_production_readiness(cls, v: bool, info) -> bool:
    if v:
        raise ValueError(
            "production_readiness cannot be set to True in Stage 3.0: models have "
            "not been independently evaluated against authentic full-wave simulation data."
        )
    return False
```
Any attempt to register or instantiate a model with `production_readiness=True` without verified full-wave ground-truth validation raises an immediate `ValueError`.

### 2.4. Elimination of Duplicate Code and Binary Checkpoints
1. **Authoritative Location**: `src/anton/ml/` is established as the single canonical source of truth for all ML registry schemas, evaluators, loaders, reports, and weight files.
2. **Binary De-duplication**: 8.8 MB of duplicate binary files (`s11_model.pt`, `best_forward_surrogate.pt`, `best_pixel_surrogate.pt`, `s11_pinn_model.pt`, `hybrid_lorentzian_rnn_best.pth`, `saved-model-5000.h5`) were permanently removed from `backend/app/ml/external/`.
3. **Thin Module Adapters**:
   - `backend/app/ml/registry/__init__.py`: Imports directly from `anton.ml.registry`.
   - `backend/app/ml/external/__init__.py`: Provides path resolution pointing to `src/anton/ml/external/`.

---

## 3. Corrected Catalog Breakdown (All 10 Entries)

| Model ID | Model Name | Entity Type | Category | Checkpoint Avail. | Checkpoint Load Status | Inference Status | Fine-Tuning Readiness | Prod. Ready |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `galabavamsi_antennanet` | Antenna-Net | `PRETRAINED_MODEL` | Category A | `True` | **`VERIFIED`** | **`VERIFIED`** | `WORKSPACE_PREPARED` | `False` |
| `youxch_patch_mlp` | Inverse-Design-Patch | `PRETRAINED_MODEL` | Category A | `True` | **`VERIFIED`** | **`VERIFIED`** | `WORKSPACE_PREPARED` | `False` |
| `udaykdk_pixelant` | PixelAnt (IIT Madras) | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `metu_simpl_microstrip` | METU-SIMPL Dataset | **`DATASET`** | Category C | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `vish1comp_antenna_benchmark` | Antenna-AI-Benchmark | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `jasti_rf_surrogate` | ML-Patch-Antenna (DEAP) | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `WORKSPACE_PREPARED` | `False` |
| `tolba_uslot_inverse` | U-Slot Patch Inverse | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `becklabs_patch_tto` | Patch-Antenna-TTO | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `sharvesh_patch_inverse` | Inverse-Design-Patch-Keras | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |
| `abinayasree_ai_antenna` | AI-Antenna-Design-Tool | `TRAINING_IMPLEMENTATION` | Category B | `False` | `NOT_APPLICABLE` | `NOT_APPLICABLE` | `NOT_READY` | `False` |

---

## 4. Query Index Optimization for Entity Types

In `src/anton/ml/registry/model_registry.py`, an inverted query index `_entity_type_index: Dict[str, Set[str]]` was added alongside `_capability_index`, `_geometry_index`, and `_category_index`.

This guarantees:
- $O(1)$ query time when filtering models by entity type via `registry.filter_by_entity_type(ModelEntityType.PRETRAINED_MODEL)`.
- Instant separation of benchmarks and training code from actual executable weights.

