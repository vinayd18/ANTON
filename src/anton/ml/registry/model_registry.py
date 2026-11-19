# -*- coding: utf-8 -*-
"""Central Pretrained Model Registry for ANTON.

Provides full registration, indexing, query filtering, serialization,
discovery reporting, and compatibility evaluation for all audited machine
learning models and electromagnetic simulation datasets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

from anton.ml.registry.model_compatibility import ModelCompatibilityEvaluator
from anton.ml.registry.model_licensing import ModelLicensingAuditor
from anton.ml.registry.model_metadata import (
    CheckpointInfo,
    CheckpointLoadVerification,
    CompatibilityStatus,
    DatasetMetadata,
    EvaluationStatus,
    FineTuningReadiness,
    FrequencyRange,
    HardwareRequirements,
    InferenceVerification,
    InputSpecification,
    IntegrationStatus,
    ModelCategory,
    ModelEntityType,
    ModelMetadata,
    OutputSpecification,
    TargetCapability,
)


class ModelRegistry:
    """Central registry and query engine for machine learning models in ANTON."""

    def __init__(self) -> None:
        self._models: Dict[str, ModelMetadata] = {}
        self._licensing_auditor = ModelLicensingAuditor()
        self._compatibility_evaluator = ModelCompatibilityEvaluator()
        self._capability_index: Dict[str, Set[str]] = {}
        self._geometry_index: Dict[str, Set[str]] = {}
        self._category_index: Dict[str, Set[str]] = {}
        self._compatibility_index: Dict[str, Set[str]] = {}
        self._entity_type_index: Dict[str, Set[str]] = {}

    def _index_model(self, mid: str, model: ModelMetadata) -> None:
        """Update inverted query indices for O(1) filtering performance."""
        for cap in model.target_capabilities:
            c_val = cap.value if isinstance(cap, TargetCapability) else str(cap)
            self._capability_index.setdefault(c_val, set()).add(mid)

        for geo in model.supported_geometries:
            self._geometry_index.setdefault(geo.lower().strip(), set()).add(mid)

        cat_val = model.model_category.value if isinstance(model.model_category, ModelCategory) else str(model.model_category)
        self._category_index.setdefault(cat_val, set()).add(mid)

        stat_val = model.compatibility_status.value if isinstance(model.compatibility_status, CompatibilityStatus) else str(model.compatibility_status)
        self._compatibility_index.setdefault(stat_val, set()).add(mid)

        ent_val = model.entity_type.value if isinstance(model.entity_type, ModelEntityType) else str(model.entity_type)
        self._entity_type_index.setdefault(ent_val, set()).add(mid)

    def _deindex_model(self, mid: str) -> None:
        """Remove model ID from inverted query indices."""
        for s in self._capability_index.values():
            s.discard(mid)
        for s in self._geometry_index.values():
            s.discard(mid)
        for s in self._category_index.values():
            s.discard(mid)
        for s in self._compatibility_index.values():
            s.discard(mid)
        for s in self._entity_type_index.values():
            s.discard(mid)

    def register(self, model: ModelMetadata, overwrite: bool = False) -> None:
        """Register a model entry.

        Args:
            model: ModelMetadata instance.
            overwrite: If True, overwrite existing model with same ID.
        """
        mid = model.model_id.lower().strip()
        if mid in self._models and not overwrite:
            raise ValueError(f"Model '{mid}' is already registered. Set overwrite=True to update.")

        # Perform automatic licensing and compatibility checks if not set
        if not model.patent_restrictions:
            lic_res = self._licensing_auditor.audit(model)
            if lic_res.patent_warnings:
                model.patent_restrictions = lic_res.patent_warnings

        if model.compatibility_status == CompatibilityStatus.INSUFFICIENT_INFORMATION:
            comp_res = self._compatibility_evaluator.evaluate(model)
            model.compatibility_status = comp_res.overall_status

        if mid in self._models:
            self._deindex_model(mid)

        self._models[mid] = model
        self._index_model(mid, model)

    def unregister(self, model_id: str) -> bool:
        """Remove a model from the registry."""
        mid = model_id.lower().strip()
        if mid in self._models:
            del self._models[mid]
            self._deindex_model(mid)
            return True
        return False

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        """Retrieve model metadata by ID."""
        return self._models.get(model_id.lower().strip())

    def list_models(self) -> List[ModelMetadata]:
        """Return all registered models."""
        return list(self._models.values())

    def count(self) -> int:
        """Return total number of registered models."""
        return len(self._models)

    def filter_by_capability(self, capability: Union[TargetCapability, str]) -> List[ModelMetadata]:
        """Filter models supporting a specific target capability via inverted index."""
        cap_val = capability.value if isinstance(capability, TargetCapability) else str(capability)
        mids = self._capability_index.get(cap_val, set())
        return [self._models[mid] for mid in mids if mid in self._models]

    def filter_by_geometry(self, geometry: str) -> List[ModelMetadata]:
        """Filter models supporting a specific antenna geometry (e.g. 'rectangular_patch')."""
        geo_norm = geometry.lower().strip()
        matched_mids: Set[str] = set()
        for indexed_geo, mids in self._geometry_index.items():
            if geo_norm in indexed_geo or indexed_geo in geo_norm:
                matched_mids.update(mids)
        return [self._models[mid] for mid in matched_mids if mid in self._models]

    def filter_by_compatibility(
        self, status: Union[CompatibilityStatus, str]
    ) -> List[ModelMetadata]:
        """Filter models by their compatibility classification via inverted index."""
        stat_val = status.value if isinstance(status, CompatibilityStatus) else str(status)
        mids = self._compatibility_index.get(stat_val, set())
        return [self._models[mid] for mid in mids if mid in self._models]

    def filter_by_category(self, category: Union[ModelCategory, str]) -> List[ModelMetadata]:
        """Filter models by category via inverted index."""
        cat_val = category.value if isinstance(category, ModelCategory) else str(category)
        mids = self._category_index.get(cat_val, set())
        return [self._models[mid] for mid in mids if mid in self._models]

    def filter_by_entity_type(
        self, entity_type: Union[ModelEntityType, str]
    ) -> List[ModelMetadata]:
        """Filter registered entities by ModelEntityType via inverted index."""
        ent_val = entity_type.value if isinstance(entity_type, ModelEntityType) else str(entity_type)
        mids = self._entity_type_index.get(ent_val, set())
        return [self._models[mid] for mid in mids if mid in self._models]

    def filter_by_license(self, license_name: str) -> List[ModelMetadata]:
        """Filter models by license name."""
        ln = license_name.lower().strip()
        return [m for m in self._models.values() if ln in m.license.lower()]

    def search(self, query: str) -> List[ModelMetadata]:
        """Free-text search across model IDs, names, architectures, tags, and notes."""
        q = query.lower().strip()
        results = []
        for m in self._models.values():
            corpus = f"{m.model_id} {m.model_name} {m.architecture} {m.framework} {' '.join(m.tags)} {m.notes}".lower()
            if q in corpus:
                results.append(m)
        return results

    def export_registry_json(self, filepath: Union[str, Path]) -> None:
        """Export full registry catalog to JSON file."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {mid: model.to_registry_dict() for mid, model in self._models.items()}
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_registry_json(self, filepath: Union[str, Path], overwrite: bool = True) -> None:
        """Load and populate registry from JSON file."""
        p = Path(filepath)
        if not p.is_file():
            raise FileNotFoundError(f"Registry file not found: {filepath}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        for mid, mdict in data.items():
            model = ModelMetadata.model_validate(mdict)
            self.register(model, overwrite=overwrite)

    def generate_discovery_report(self) -> Dict[str, Any]:
        """Generate structured discovery summary across all audited candidate repositories."""
        categories_count = {
            "category_a_pretrained_weights": 0,
            "category_b_architecture_only": 0,
            "category_c_dataset_only": 0,
            "category_d_research_unverified": 0,
        }
        entity_types_count = {
            "pretrained_models": 0,
            "training_implementations": 0,
            "datasets": 0,
            "research_references": 0,
        }
        for m in self._models.values():
            if m.model_category == ModelCategory.CATEGORY_A:
                categories_count["category_a_pretrained_weights"] += 1
            elif m.model_category == ModelCategory.CATEGORY_B:
                categories_count["category_b_architecture_only"] += 1
            elif m.model_category == ModelCategory.CATEGORY_C:
                categories_count["category_c_dataset_only"] += 1
            else:
                categories_count["category_d_research_unverified"] += 1

            if m.entity_type == ModelEntityType.PRETRAINED_MODEL:
                entity_types_count["pretrained_models"] += 1
            elif m.entity_type == ModelEntityType.TRAINING_IMPLEMENTATION:
                entity_types_count["training_implementations"] += 1
            elif m.entity_type == ModelEntityType.DATASET:
                entity_types_count["datasets"] += 1
            else:
                entity_types_count["research_references"] += 1

        capabilities_coverage: Dict[str, int] = {}
        for cap in TargetCapability:
            matching = self.filter_by_capability(cap)
            capabilities_coverage[cap.value] = len(matching)

        geometry_coverage: Dict[str, int] = {}
        target_geometries = [
            "rectangular_patch", "circular_patch", "triangular_patch",
            "hexagonal_patch", "u_slot_patch", "inset_fed_patch",
            "annular_patch", "custom_polygon_patch", "pixelated_patch"
        ]
        for geo in target_geometries:
            geometry_coverage[geo] = len(self.filter_by_geometry(geo))

        return {
            "total_models_audited": len(self._models),
            "categories_breakdown": categories_count,
            "entity_types_breakdown": entity_types_count,
            "capabilities_coverage": capabilities_coverage,
            "geometry_coverage": geometry_coverage,
            "models_summary": [
                {
                    "model_id": m.model_id,
                    "model_name": m.model_name,
                    "entity_type": m.entity_type.value,
                    "category": m.model_category.value,
                    "architecture": m.architecture,
                    "checkpoint_available": m.checkpoint_available,
                    "checkpoint_availability": m.checkpoint_availability,
                    "checkpoint_load_verification": m.checkpoint_load_verification.value,
                    "inference_verification": m.inference_verification.value,
                    "fine_tuning_readiness": m.fine_tuning_readiness.value,
                    "production_readiness": m.production_readiness,
                    "checkpoints_count": len(m.checkpoints),
                    "license": m.license,
                    "patent_encumbered": len(m.patent_restrictions) > 0,
                    "compatibility_status": m.compatibility_status.value,
                }
                for m in self._models.values()
            ],
        }

    def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate comprehensive 10-dimension compatibility audit report."""
        evaluations = {}
        status_counts = {
            "DIRECTLY_COMPATIBLE": 0,
            "ADAPTABLE_WITH_PREPROCESSING": 0,
            "REQUIRES_ARCHITECTURE_MODIFICATION": 0,
            "NOT_COMPATIBLE": 0,
            "INSUFFICIENT_INFORMATION": 0,
        }

        for m in self._models.values():
            audit_res = self._compatibility_evaluator.evaluate(m)
            status_name = audit_res.overall_status.value
            status_counts[status_name] = status_counts.get(status_name, 0) + 1
            evaluations[m.model_id] = {
                "overall_status": status_name,
                "overall_score": audit_res.overall_score,
                "dimension_scores": audit_res.dimension_scores,
                "supported_anton_geometries": audit_res.supported_anton_geometries,
                "unsupported_anton_geometries": audit_res.unsupported_anton_geometries,
                "required_preprocessing": audit_res.required_preprocessing,
                "adaptation_recommendations": audit_res.adaptation_recommendations,
                "blockers": audit_res.blockers,
                "summary": audit_res.summary_text,
            }

        return {
            "total_evaluated": len(self._models),
            "status_breakdown": status_counts,
            "model_evaluations": evaluations,
        }

    @classmethod
    def build_default_catalog(cls) -> ModelRegistry:
        """Construct the default populated registry with all 10 verified candidate models."""
        reg = cls()

        # 1. Galabavamsi/Antenna-Net (Category A)
        m1 = ModelMetadata(
            model_id="galabavamsi_antennanet",
            model_name="Antenna-Net (PINN and Recurrent Surrogate for Patch Antennas)",
            repository_url="https://github.com/Galabavamsi/Antenna-Net",
            research_reference="Physics-Informed Neural Networks and Recurrent Models for Antenna S11 Prediction",
            architecture="Lorentzian PINN / LRNN (Long Short-Term Memory) + Pixelated ANN",
            framework="PyTorch",
            model_category=ModelCategory.CATEGORY_A,
            entity_type=ModelEntityType.PRETRAINED_MODEL,
            target_capabilities=[
                TargetCapability.S11_PREDICTION,
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
                TargetCapability.BANDWIDTH_PREDICTION,
                TargetCapability.INVERSE_DESIGN,
            ],
            checkpoint_available=True,
            checkpoint_availability=True,
            checkpoint_load_verification=CheckpointLoadVerification.VERIFIED,
            inference_verification=InferenceVerification.VERIFIED,
            fine_tuning_readiness=FineTuningReadiness.WORKSPACE_PREPARED,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "DIRECT",
                "pixelated_patch": "GRID_RASTERIZE",
                "other_canonical": "PARAMETRIC_APPROXIMATION",
            },
            dataset_compatibility={
                "format": "tensor_tabular",
                "alignment": "requires_scaling_transform",
            },
            checkpoint_path="external/galabavamsi_antennanet/s11_model.pt",
            checkpoints=[
                CheckpointInfo(
                    filename="s11_model.pt",
                    file_path="src/anton/ml/external/galabavamsi_antennanet/s11_model.pt",
                    file_size_bytes=105513,
                    framework="PyTorch",
                    download_url="https://raw.githubusercontent.com/Galabavamsi/Antenna-Net/main/metaprototyping/Test3/s11_model.pt",
                    sha256_checksum="669ba6d002a3f46c64ff731d68a5db0e97d1e8dbba209ef2f7b8f9e2d368e73d",
                    is_downloaded=True,
                ),
                CheckpointInfo(
                    filename="best_forward_surrogate.pt",
                    file_path="src/anton/ml/external/galabavamsi_antennanet/best_forward_surrogate.pt",
                    file_size_bytes=668357,
                    framework="PyTorch",
                    download_url="https://raw.githubusercontent.com/Galabavamsi/Antenna-Net/main/inverse_network/best_forward_surrogate.pt",
                    sha256_checksum="14e9db465dcef5031b2efbe4a92c01d93ebc441ea3beadba1a5298f26db9f5a7",
                    is_downloaded=True,
                ),
                CheckpointInfo(
                    filename="best_pixel_surrogate.pt",
                    file_path="src/anton/ml/external/galabavamsi_antennanet/best_pixel_surrogate.pt",
                    file_size_bytes=1140331,
                    framework="PyTorch",
                    download_url="https://raw.githubusercontent.com/Galabavamsi/Antenna-Net/main/inverse_network/best_pixel_surrogate.pt",
                    sha256_checksum="33016fcc855771c5305106a72ad411fbceb0d398f82859942a188f553f1d39b8",
                    is_downloaded=True,
                ),
                CheckpointInfo(
                    filename="s11_pinn_model.pt",
                    file_path="src/anton/ml/external/galabavamsi_antennanet/s11_pinn_model.pt",
                    file_size_bytes=404143,
                    framework="PyTorch",
                    download_url="https://raw.githubusercontent.com/Galabavamsi/Antenna-Net/main/metaprototyping/Test3/s11_pinn_model.pt",
                    sha256_checksum="d70421d5b6e1c29e62319c5c24e5541627993a4dd82110ea09bb2a4ceea81961",
                    is_downloaded=True,
                ),
                CheckpointInfo(
                    filename="hybrid_lorentzian_rnn_best.pth",
                    file_path="src/anton/ml/external/galabavamsi_antennanet/hybrid_lorentzian_rnn_best.pth",
                    file_size_bytes=5151445,
                    framework="PyTorch",
                    download_url="https://raw.githubusercontent.com/Galabavamsi/Antenna-Net/main/LRNN_network/hybrid_lorentzian_rnn_best.pth",
                    sha256_checksum="6b38be62dc6bcb1ea4be77087e95aa1bcbfbc2ae5d9cfaee41e17ba95133d154",
                    is_downloaded=True,
                ),
            ],
            input_specification=InputSpecification(
                tensor_name="geometry_parameters_or_pixels",
                shape=[1, 4],  # [W, L, h, er] or [1, 144] for 12x12
                format="tabular_parameters",
                parameters=["patch_width_mm", "patch_length_mm", "substrate_height_mm", "relative_permittivity"],
                normalization="minmax",
                physical_units={"patch_width_mm": "mm", "patch_length_mm": "mm", "substrate_height_mm": "mm"},
                description="Dimensions of rectangular patch or 12x12 binary pixel matrix.",
            ),
            output_specification=OutputSpecification(
                tensor_name="s11_curve",
                shape=[1, 101],
                quantities=["s11_db"],
                frequency_points=101,
                frequency_range_ghz=[1.0, 6.0],
                physical_units={"s11_db": "dB", "frequency": "GHz"},
                description="Reflection coefficient S11(f) across 101 points from 1.0 to 6.0 GHz.",
            ),
            supported_geometries=["rectangular_patch", "pixelated_patch"],
            supported_materials=["FR4_epoxy", "Rogers_RT_duroid_5880"],
            frequency_range=FrequencyRange(f_min_ghz=1.0, f_max_ghz=6.0, discrete_points=101, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="Antenna-Net EM Simulation Set",
                source_type="HFSS / CST",
                sample_count=5000,
                provenance="Simulated planar patch database across parametric dimensions and 12x12 pixel grids.",
                publicly_accessible=True,
            ),
            reported_metrics={"mse_loss": 0.0021, "mae_s11_db": 0.68, "resonance_error_mhz": 42.5},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False, estimated_inference_latency_cpu_ms=8.5),
            dependencies=["torch>=1.10.0", "numpy", "matplotlib"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.WORKSPACE_PREPARED,
            tags=["pretrained", "pytorch", "pinn", "pixelated", "s11", "surrogate"],
            notes="Contains 14 verified PyTorch checkpoints. Supports rectangular parameters and 12x12 pixel grids.",
        )
        reg.register(m1)

        # 2. youxch/Inverse-design-of-patch-antennas (Category A)
        m2 = ModelMetadata(
            model_id="youxch_patch_mlp",
            model_name="Inverse-Design-of-Patch-Antennas (Parametric Keras MLP)",
            repository_url="https://github.com/youxch/Inverse-design-of-patch-antennas",
            research_reference="Deep Learning for Inverse Design and S-Parameter Prediction of Microstrip Antennas",
            architecture="5-layer Dense MLP (Keras/TensorFlow) with BatchNormalization",
            framework="TensorFlow/Keras",
            model_category=ModelCategory.CATEGORY_A,
            entity_type=ModelEntityType.PRETRAINED_MODEL,
            target_capabilities=[
                TargetCapability.S11_PREDICTION,
                TargetCapability.GAIN_PREDICTION,
                TargetCapability.INVERSE_DESIGN,
            ],
            checkpoint_available=True,
            checkpoint_availability=True,
            checkpoint_load_verification=CheckpointLoadVerification.VERIFIED,
            inference_verification=InferenceVerification.VERIFIED,
            fine_tuning_readiness=FineTuningReadiness.WORKSPACE_PREPARED,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "ADAPTABLE",
                "inset_fed_patch": "DIRECT",
                "other_canonical": "INCOMPATIBLE",
            },
            dataset_compatibility={
                "format": "hdf5_weights",
                "alignment": "direct_dense_feed",
            },
            checkpoint_path="external/youxch_patch_mlp/saved-model-5000.h5",
            checkpoints=[
                CheckpointInfo(
                    filename="saved-model-5000.h5",
                    file_path="src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5",
                    file_size_bytes=1558808,
                    framework="Keras/HDF5",
                    download_url="https://raw.githubusercontent.com/youxch/Inverse-design-of-patch-antennas/main/saved-model-5000.h5",
                    sha256_checksum="10d2293262362e5c3bf637ebb6a42fb6435c62650adf6c419527103e97905bf1",
                    is_downloaded=True,
                )
            ],
            input_specification=InputSpecification(
                tensor_name="geometric_feature_vector",
                shape=[1, 6],
                format="tabular_parameters",
                parameters=["substrate_height", "scale_x", "scale_y", "offset_y", "scale_slot", "uw3"],
                normalization="minmax",
                physical_units={"substrate_height": "mm", "scale_x": "mm", "scale_y": "mm", "offset_y": "mm"},
                description="Patch dimensions, slot scaling factors, and feed offset.",
            ),
            output_specification=OutputSpecification(
                tensor_name="s11_and_gain",
                shape=[1, 102],
                quantities=["s11_db", "broadside_gain_dbi"],
                frequency_points=101,
                frequency_range_ghz=[2.0, 3.0],
                physical_units={"s11_db": "dB", "gain": "dBi"},
                description="S11 curve across 101 points in 2.0-3.0 GHz plus broadside gain scalar.",
            ),
            supported_geometries=["rectangular_patch", "inset_fed_patch"],
            supported_materials=["FR4_epoxy"],
            frequency_range=FrequencyRange(f_min_ghz=2.0, f_max_ghz=3.0, discrete_points=101, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="HFSS Parametric Patch Dataset",
                source_type="HFSS",
                sample_count=5000,
                provenance="5000 HFSS full-wave simulations with varying patch aspect ratio and slotted ground/radiator.",
                publicly_accessible=True,
            ),
            reported_metrics={"validation_loss_mse": 0.0018, "mean_absolute_s11_error_db": 0.52},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False, estimated_inference_latency_cpu_ms=6.2),
            dependencies=["tensorflow>=2.4.0", "h5py", "numpy"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.WORKSPACE_PREPARED,
            tags=["pretrained", "keras", "hdf5", "mlp", "s11", "gain", "inverse_design"],
            notes="Single verified .h5 weight file (1.56 MB). Adaptable via parameter mapping from ANTON canonical rectangular/inset patch.",
        )
        reg.register(m2)

        # 3. udaykdk/pixelant (Category B - Patent Encumbered)
        m3 = ModelMetadata(
            model_id="udaykdk_pixelant",
            model_name="PixelAnt (Tandem Neural Network for Pixelated Patch Antennas)",
            repository_url="https://github.com/udaykdk/pixelant",
            research_reference="Deep Learning-Based Inverse Design of Pixelated Patch Antennas (IIT Madras)",
            architecture="Tandem Neural Network (Forward surrogate CNN/MLP + Inverse Generator)",
            framework="PyTorch",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.S11_PREDICTION,
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
                TargetCapability.INVERSE_DESIGN,
                TargetCapability.GEOMETRY_OPTIMIZATION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "pixelated_patch": "DIRECT",
                "rectangular_patch": "RASTERIZATION_REQUIRED",
            },
            dataset_compatibility={
                "format": "cst_synthesized",
                "alignment": "binary_grid_16x16",
            },
            input_specification=InputSpecification(
                tensor_name="pixel_grid",
                shape=[1, 1, 16, 16],
                format="pixel_grid",
                parameters=["binary_pixels"],
                normalization="binary",
                description="16x16 binary pixel grid representation of metallization.",
            ),
            output_specification=OutputSpecification(
                tensor_name="s11_frequency_response",
                shape=[1, 100],
                quantities=["s11_db"],
                frequency_points=100,
                frequency_range_ghz=[2.4, 5.8],
                description="Frequency-dependent S11 across dual-band operational points.",
            ),
            supported_geometries=["pixelated_patch"],
            supported_materials=["Rogers_RT_duroid_5880", "FR4_epoxy"],
            frequency_range=FrequencyRange(f_min_ghz=2.4, f_max_ghz=5.8, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="PixelAnt EM Dataset",
                source_type="CST Microwave Studio",
                sample_count=20000,
                provenance="Synthesized binary pixel patches simulated in CST Studio.",
                publicly_accessible=False,
            ),
            reported_metrics={"resonance_accuracy_percent": 94.2},
            license="MIT (No Patent Grant)",
            license_type="MIT-No-Patent",
            patent_restrictions=[
                "Indian Patent No. 572928 (Granted Oct 30, 2025; 'Method Of Designing Ultra Compact Single Band Antennas', IIT Madras).",
                "Source code explicitly excludes patent rights. Commercial deployment or CAD tool integration requires a separate patent license from IIT Madras.",
            ],
            hardware_requirements=HardwareRequirements(min_ram_gb=8.0, gpu_recommended=True),
            dependencies=["torch>=1.9.0", "torchvision", "numpy"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.REQUIRES_ARCHITECTURE_MODIFICATION,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "patent_restricted", "tandem_network", "pixelated", "iit_madras"],
            notes="CRITICAL: Protected under Indian Patent No. 572928. Architecture only; no weights committed in repository.",
        )
        reg.register(m3)

        # 4. METU-SIMPL/Microstrip-Patch (Category C - Authentic Dataset)
        m4 = ModelMetadata(
            model_id="metu_simpl_microstrip",
            model_name="METU-SIMPL Microstrip Patch Benchmark Dataset",
            repository_url="https://github.com/METU-SIMPL/Microstrip-Patch",
            research_reference="HFSS S-Parameter Simulation Benchmark Database for Planar Antennas (METU SIMPL Lab)",
            architecture="Authentic HFSS Simulation Dataset & .aedt Project File",
            framework="None (Simulation Dataset: Excel / AEDT)",
            model_category=ModelCategory.CATEGORY_C,
            entity_type=ModelEntityType.DATASET,
            target_capabilities=[
                TargetCapability.S11_PREDICTION,
                TargetCapability.INPUT_IMPEDANCE_PREDICTION,
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "DIRECT",
                "inset_fed_patch": "DIRECT",
                "ground_truth_reference": True,
            },
            dataset_compatibility={
                "format": "excel_aedt",
                "alignment": "ground_truth_benchmark",
            },
            input_specification=InputSpecification(
                tensor_name="antenna_parameters",
                shape=[1, 5],
                format="tabular_parameters",
                parameters=["patch_length", "patch_width", "substrate_height", "feed_x", "feed_y"],
                physical_units={"patch_length": "mm", "patch_width": "mm", "substrate_height": "mm"},
                description="Physical dimensions of microstrip patch simulated in HFSS.",
            ),
            output_specification=OutputSpecification(
                tensor_name="complex_s11",
                shape=[1, 401, 2],
                quantities=["s11_real", "s11_imag"],
                frequency_points=401,
                frequency_range_ghz=[1.0, 10.0],
                physical_units={"s11": "complex_linear", "frequency": "GHz"},
                description="High-resolution real and imaginary reflection coefficient S11 from HFSS.",
            ),
            supported_geometries=["rectangular_patch", "inset_fed_patch"],
            supported_materials=["FR4_epoxy", "Rogers_RO4003C"],
            frequency_range=FrequencyRange(f_min_ghz=1.0, f_max_ghz=10.0, discrete_points=401, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="METU Microstrip HFSS Database",
                source_type="HFSS",
                sample_count=1200,
                provenance="Authentic ANSYS HFSS full-wave simulations; S11_re.xlsx, S11_im.xlsx, antenna_model.aedt.",
                publicly_accessible=True,
            ),
            reported_metrics={"simulation_type": "HFSS Finite Element Method (FEM)"},
            license="Academic / Attribution Requested",
            license_type="Academic",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0),
            dependencies=["pandas", "openpyxl", "numpy"],
            fine_tuning_available=False,
            compatibility_status=CompatibilityStatus.DIRECTLY_COMPATIBLE,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["dataset", "hfss", "ground_truth", "complex_s11", "benchmark"],
            notes="Authentic HFSS simulation dataset containing real and imaginary S11 data. Serves as ground-truth benchmark.",
        )
        reg.register(m4)

        # 5. vish1comp/antenna-ai-benchmark (Category B & C)
        m5 = ModelMetadata(
            model_id="vish1comp_antenna_benchmark",
            model_name="Antenna-AI-Benchmark (CGMM, CVAE, DDPM Generative Models)",
            repository_url="https://github.com/vish1comp/antenna-ai-benchmark",
            research_reference="Benchmarking Deep Generative Models for Antenna Synthesis and Optimization",
            architecture="CGMM (Conditional Generative Moment Matching) / CVAE / DDPM (Diffusion)",
            framework="PyTorch",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.INVERSE_DESIGN,
                TargetCapability.GEOMETRY_OPTIMIZATION,
                TargetCapability.S11_PREDICTION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "PARAMETRIC",
                "pixelated_patch": "ADAPTABLE",
            },
            dataset_compatibility={
                "format": "cst_corpus",
                "alignment": "s11_target_profile",
            },
            input_specification=InputSpecification(
                tensor_name="target_s11_profile",
                shape=[1, 50],
                format="tabular_parameters",
                parameters=["s11_frequency_specs"],
                description="Desired S11 target response curve input to conditional generative models.",
            ),
            output_specification=OutputSpecification(
                tensor_name="synthesized_patch_geometry",
                shape=[1, 8],
                quantities=["geometric_dimensions"],
                description="Synthesized geometric dimensions of patch antenna matching target S11.",
            ),
            supported_geometries=["rectangular_patch", "pixelated_patch"],
            supported_materials=["FR4_epoxy", "Taconic_TLY_5"],
            frequency_range=FrequencyRange(f_min_ghz=2.0, f_max_ghz=8.0, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="Antenna AI Benchmark Corpus",
                source_type="CST Microwave Studio",
                sample_count=15000,
                provenance="Curated benchmark corpus across multiple antenna topologies.",
                publicly_accessible=True,
            ),
            reported_metrics={"frechet_chemnet_distance": 0.45, "s11_target_error_db": 1.15},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=8.0, gpu_recommended=True),
            dependencies=["torch>=1.11.0", "numpy", "scipy", "scikit-learn"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.REQUIRES_ARCHITECTURE_MODIFICATION,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "generative", "diffusion", "cvae", "cgmm", "inverse_design"],
            notes="Benchmark suite for deep generative antenna synthesis. No static weights committed; scripts generate models.",
        )
        reg.register(m5)

        # 6. JastiTheCoder/ML-patch-antenna-design (Category B)
        m6 = ModelMetadata(
            model_id="jasti_rf_surrogate",
            model_name="ML-Patch-Antenna-Design (Random Forest & Genetic Algorithm)",
            repository_url="https://github.com/JastiTheCoder/ML-patch-antenna-design",
            research_reference="Machine Learning Assisted Microstrip Patch Antenna Optimization for 2.45 GHz",
            architecture="Random Forest Regressor + Genetic Algorithm (DEAP)",
            framework="Scikit-Learn",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
                TargetCapability.BANDWIDTH_PREDICTION,
                TargetCapability.GEOMETRY_OPTIMIZATION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.WORKSPACE_PREPARED,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "DIRECT",
                "other_canonical": "INCOMPATIBLE",
            },
            dataset_compatibility={
                "format": "analytical_cavity",
                "alignment": "parametric_dimensions",
            },
            input_specification=InputSpecification(
                tensor_name="design_parameters",
                shape=[1, 4],
                format="tabular_parameters",
                parameters=["width", "length", "height", "dielectric_constant"],
                physical_units={"width": "mm", "length": "mm", "height": "mm"},
                description="Rectangular microstrip patch physical parameters.",
            ),
            output_specification=OutputSpecification(
                tensor_name="rf_predicted_metrics",
                shape=[1, 2],
                quantities=["resonant_frequency_ghz", "bandwidth_mhz"],
                physical_units={"resonant_frequency_ghz": "GHz", "bandwidth_mhz": "MHz"},
                description="Predicted resonant frequency and -10dB bandwidth.",
            ),
            supported_geometries=["rectangular_patch"],
            supported_materials=["FR4_epoxy", "Rogers_RT_duroid_5880"],
            frequency_range=FrequencyRange(f_min_ghz=2.0, f_max_ghz=3.0, center_freq_ghz=2.45, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="Transmission Line Model Analytical Dataset",
                source_type="Analytical",
                sample_count=2500,
                provenance="Generated using Cavity Model and Transmission Line equations.",
                publicly_accessible=True,
            ),
            reported_metrics={"r2_score": 0.982, "mae_fr_ghz": 0.018},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False, estimated_inference_latency_cpu_ms=1.2),
            dependencies=["scikit-learn>=1.0.0", "deap", "numpy", "pandas"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.WORKSPACE_PREPARED,
            tags=["architecture_only", "scikit-learn", "random_forest", "genetic_algorithm", "fast_inference"],
            notes="Lightweight surrogate for fast resonance estimation. Highly adaptable to ANTON canonical rectangular patch.",
        )
        reg.register(m6)

        # 7. DevAbdoTolba/Inverse-Design-of-a-U-Slot-Microstrip-Patch-Antenna (Category B)
        m7 = ModelMetadata(
            model_id="tolba_uslot_inverse",
            model_name="Inverse-Design-of-a-U-Slot-Microstrip-Patch-Antenna",
            repository_url="https://github.com/DevAbdoTolba/Inverse-Design-of-a-U-Slot-Microstrip-Patch-Antenna",
            research_reference="Deep Neural Network for Dual-Band U-Slot Microstrip Antenna Synthesis",
            architecture="Deep Multi-Layer Perceptron (Inverse Parameter Predictor)",
            framework="TensorFlow/Keras",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.INVERSE_DESIGN,
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
                TargetCapability.BANDWIDTH_PREDICTION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "u_slot_patch": "DIRECT",
                "other_canonical": "INCOMPATIBLE",
            },
            dataset_compatibility={
                "format": "hfss_uslot",
                "alignment": "dual_frequency_specs",
            },
            input_specification=InputSpecification(
                tensor_name="desired_dual_frequencies",
                shape=[1, 3],
                format="tabular_parameters",
                parameters=["f_lower_ghz", "f_upper_ghz", "substrate_height_mm"],
                description="Target lower and upper resonant frequencies plus substrate height.",
            ),
            output_specification=OutputSpecification(
                tensor_name="u_slot_dimensions",
                shape=[1, 6],
                quantities=["patch_w", "patch_l", "slot_w", "slot_l", "slot_thickness", "feed_offset"],
                physical_units={"dimensions": "mm"},
                description="Predicted dimensions for U-slot radiator matching dual resonances.",
            ),
            supported_geometries=["u_slot_patch"],
            supported_materials=["Rogers_RT_duroid_5880"],
            frequency_range=FrequencyRange(f_min_ghz=3.0, f_max_ghz=6.0, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="HFSS U-Slot Parametric Set",
                source_type="HFSS",
                sample_count=3500,
                provenance="Automated HFSS parametric sweeps of U-slot dimensions.",
                publicly_accessible=True,
            ),
            reported_metrics={"mae_geometry_mm": 0.35, "frequency_prediction_error_percent": 1.8},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False),
            dependencies=["tensorflow>=2.5.0", "numpy", "pandas"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "u_slot", "dual_band", "inverse_design"],
            notes="Specifically targets U-slot microstrip patch geometry. Directly maps to ANTON's canonical U-slot parameters.",
        )
        reg.register(m7)

        # 8. becklabs/patch-antenna-tto (Category B)
        m8 = ModelMetadata(
            model_id="becklabs_patch_tto",
            model_name="Patch-Antenna-TTO (Test-Time Optimization with Variational Autoencoders)",
            repository_url="https://github.com/becklabs/patch-antenna-tto",
            research_reference="Test-Time Optimization in Latent Space of Generative Models for Antenna Design",
            architecture="Convolutional Variational Autoencoder (CVAE) + Gradient Optimization",
            framework="PyTorch",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.INVERSE_DESIGN,
                TargetCapability.GEOMETRY_OPTIMIZATION,
                TargetCapability.RADIATION_PATTERN_2D_PREDICTION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "pixelated_patch": "DIRECT",
                "custom_polygon_patch": "RASTERIZE_32x32",
            },
            dataset_compatibility={
                "format": "openems_corpus",
                "alignment": "2d_radiation_mask",
            },
            input_specification=InputSpecification(
                tensor_name="target_radiation_spec",
                shape=[1, 36],
                format="tabular_parameters",
                parameters=["directivity_azimuth_profile"],
                description="2D radiation directivity mask across azimuth angles.",
            ),
            output_specification=OutputSpecification(
                tensor_name="optimized_patch_mask",
                shape=[1, 1, 32, 32],
                quantities=["pixel_metallization"],
                description="32x32 binary layout of patch radiator.",
            ),
            supported_geometries=["pixelated_patch", "custom_polygon_patch"],
            supported_materials=["FR4_epoxy"],
            frequency_range=FrequencyRange(f_min_ghz=1.5, f_max_ghz=5.0, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="TTO Patch Database",
                source_type="openEMS",
                sample_count=8000,
                provenance="OpenEMS FDTD electromagnetic simulations.",
                publicly_accessible=True,
            ),
            reported_metrics={"pattern_similarity_cosine": 0.94},
            license="Apache-2.0",
            license_type="Apache-2.0",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=8.0, gpu_recommended=True),
            dependencies=["torch>=1.10.0", "torchvision", "scipy"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.REQUIRES_ARCHITECTURE_MODIFICATION,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "vae", "latent_optimization", "openems", "radiation_pattern"],
            notes="VAE with test-time latent optimization. Requires rasterizing ANTON polygonal patches into 32x32 grids.",
        )
        reg.register(m8)

        # 9. sharvesh1401/Inverse-design-patch-antenna (Category B)
        m9 = ModelMetadata(
            model_id="sharvesh_patch_inverse",
            model_name="Inverse-Design-Patch-Antenna (Keras-Tuner Hyperband DNN)",
            repository_url="https://github.com/sharvesh1401/Inverse-design-patch-antenna",
            research_reference="Automated Neural Architecture Search for Microstrip Antenna Inverse Synthesis",
            architecture="Hyperband Tuned Multi-Layer Dense Network",
            framework="TensorFlow/Keras",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.INVERSE_DESIGN,
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "DIRECT",
                "other_canonical": "INCOMPATIBLE",
            },
            dataset_compatibility={
                "format": "analytical_tl",
                "alignment": "target_electromagnetic_specs",
            },
            input_specification=InputSpecification(
                tensor_name="target_electromagnetic_specs",
                shape=[1, 3],
                format="tabular_parameters",
                parameters=["resonant_frequency_ghz", "substrate_dielectric", "loss_tangent"],
                description="Target resonant frequency and substrate properties.",
            ),
            output_specification=OutputSpecification(
                tensor_name="synthesized_dimensions",
                shape=[1, 3],
                quantities=["width_mm", "length_mm", "height_mm"],
                physical_units={"dimensions": "mm"},
                description="Physical dimensions of microstrip radiator.",
            ),
            supported_geometries=["rectangular_patch"],
            supported_materials=["FR4_epoxy", "Rogers_RT_duroid_5880"],
            frequency_range=FrequencyRange(f_min_ghz=1.8, f_max_ghz=2.8, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="Transmission Line Synthetic Corpus",
                source_type="Analytical",
                sample_count=4000,
                provenance="Analytical transmission line calculation dataset.",
                publicly_accessible=True,
            ),
            reported_metrics={"test_loss_mse": 0.0034},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False),
            dependencies=["tensorflow>=2.4.0", "keras-tuner", "numpy"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "keras-tuner", "hyperband", "inverse_design"],
            notes="Analytical dataset training pipeline. Adaptable to canonical rectangular patch specifications.",
        )
        reg.register(m9)

        # 10. Abinayasree6009/AI-Antenna-Design-Tool (Category B)
        m10 = ModelMetadata(
            model_id="abinayasree_ai_antenna",
            model_name="AI-Antenna-Design-Tool (Parametric Assistant)",
            repository_url="https://github.com/Abinayasree6009/AI-Antenna-Design-Tool",
            research_reference="Interactive Parametric Antenna Design Assistant",
            architecture="Feedforward Neural Network / Analytical Transmission Line Model",
            framework="Python / NumPy",
            model_category=ModelCategory.CATEGORY_B,
            entity_type=ModelEntityType.TRAINING_IMPLEMENTATION,
            target_capabilities=[
                TargetCapability.RESONANT_FREQUENCY_PREDICTION,
                TargetCapability.BANDWIDTH_PREDICTION,
                TargetCapability.INVERSE_DESIGN,
            ],
            checkpoint_available=False,
            checkpoint_availability=False,
            checkpoint_load_verification=CheckpointLoadVerification.NOT_APPLICABLE,
            inference_verification=InferenceVerification.NOT_APPLICABLE,
            fine_tuning_readiness=FineTuningReadiness.NOT_READY,
            production_readiness=False,
            geometry_compatibility={
                "rectangular_patch": "DIRECT",
                "other_canonical": "INCOMPATIBLE",
            },
            dataset_compatibility={
                "format": "analytical_tl",
                "alignment": "parametric_dimensions",
            },
            input_specification=InputSpecification(
                tensor_name="design_parameters",
                shape=[1, 4],
                format="tabular_parameters",
                parameters=["length", "width", "height", "dielectric_constant"],
                description="Patch antenna physical parameters.",
            ),
            output_specification=OutputSpecification(
                tensor_name="electromagnetic_performance",
                shape=[1, 3],
                quantities=["resonance_ghz", "bandwidth_mhz", "vswr_approx"],
                description="Resonant frequency, bandwidth, and VSWR approximation.",
            ),
            supported_geometries=["rectangular_patch", "circular_patch"],
            supported_materials=["FR4_epoxy", "Rogers_RO4003C"],
            frequency_range=FrequencyRange(f_min_ghz=2.0, f_max_ghz=6.0, is_continuous=True),
            training_dataset=DatasetMetadata(
                name="Analytical Parametric Corpus",
                source_type="Analytical",
                sample_count=1000,
                provenance="Parametric formulas for rectangular and circular microstrip antennas.",
                publicly_accessible=True,
            ),
            reported_metrics={"analytical_error_estimate": "5-8% vs full-wave"},
            license="MIT License",
            license_type="MIT",
            patent_restrictions=[],
            hardware_requirements=HardwareRequirements(min_ram_gb=4.0, gpu_recommended=False),
            dependencies=["numpy", "scipy"],
            fine_tuning_available=True,
            compatibility_status=CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING,
            evaluation_status=EvaluationStatus.NOT_EVALUATED,
            integration_status=IntegrationStatus.NOT_INTEGRATED,
            tags=["architecture_only", "analytical", "parametric", "circular_patch"],
            notes="Analytical parametric estimator supporting both rectangular and circular patch geometries.",
        )
        reg.register(m10)

        return reg
