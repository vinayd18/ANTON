# -*- coding: utf-8 -*-
"""Comprehensive compatibility assessment engine for machine learning models in ANTON.

Compares candidate ML models against ANTON's canonical antenna geometry schema,
evaluating geometric representation, physical parameterization, material properties,
frequency bands, tensor dimensions, and electromagnetic output representations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from anton.ml.registry.model_metadata import (
    CompatibilityStatus,
    ModelCategory,
    ModelMetadata,
    TargetCapability,
)
from anton.models.geometry_schema import GeometryProject


# ANTON canonical supported geometries
ANTON_CANONICAL_GEOMETRIES = [
    "rectangular_patch",
    "circular_patch",
    "triangular_patch",
    "hexagonal_patch",
    "u_slot_patch",
    "inset_feed_patch",
    "annular_patch",
    "custom_polygon_patch",
]


@dataclass
class DimensionCompatibility:
    """Evaluation of a single compatibility dimension."""

    dimension_name: str
    is_compatible: bool
    score: float  # 0.0 to 10.0
    details: str
    remediation_required: Optional[str] = None


@dataclass
class CompatibilityEvaluationResult:
    """Comprehensive compatibility assessment result for an ML candidate."""

    model_id: str
    status: CompatibilityStatus
    overall_score: float  # 0.0 to 100.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    dimensions: List[DimensionCompatibility] = field(default_factory=list)
    supported_anton_geometries: List[str] = field(default_factory=list)
    unsupported_anton_geometries: List[str] = field(default_factory=list)
    required_preprocessing: List[str] = field(default_factory=list)
    adaptation_recommendations: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    summary_text: str = ""

    @property
    def overall_status(self) -> CompatibilityStatus:
        return self.status

    @property
    def adaptation_requirements(self) -> List[str]:
        return self.required_preprocessing + self.adaptation_recommendations

    def summary(self) -> str:
        lines = [
            f"Compatibility Assessment for '{self.model_id}': {self.status.value} (Score: {self.overall_score:.1f}/100)",
            f"  Supported Geometries ({len(self.supported_anton_geometries)}/{len(ANTON_CANONICAL_GEOMETRIES)}): {', '.join(self.supported_anton_geometries) if self.supported_anton_geometries else 'None directly'}",
        ]
        if self.unsupported_anton_geometries:
            lines.append(f"  Unsupported Geometries: {', '.join(self.unsupported_anton_geometries)}")
        if self.required_preprocessing:
            lines.append("  Required Preprocessing Steps:")
            for p in self.required_preprocessing:
                lines.append(f"    - {p}")
        if self.blockers:
            lines.append("  Critical Blockers:")
            for b in self.blockers:
                lines.append(f"    - [!] {b}")
        return "\n".join(lines)


class ModelCompatibilityAssessor:
    """Automated assessor evaluating models against ANTON's canonical geometry architecture."""

    @classmethod
    def evaluate(cls, model: ModelMetadata, reference_project: Optional[GeometryProject] = None) -> CompatibilityEvaluationResult:
        """Evaluates a model across 10 engineering compatibility dimensions."""
        dims: List[DimensionCompatibility] = []
        blockers: List[str] = []
        preprocessing: List[str] = []
        recommendations: List[str] = []

        # 1. Geometry Representation Compatibility
        # Check whether model inputs map to ANTON's canonical planar objects
        geom_format = model.input_specification.format
        supp_geom = [g.lower() for g in model.supported_geometries]
        matched_geoms = [g for g in ANTON_CANONICAL_GEOMETRIES if any(g in sg or sg in g for sg in supp_geom)]
        unmatched_geoms = [g for g in ANTON_CANONICAL_GEOMETRIES if g not in matched_geoms]

        if "pixel" in geom_format or "grid" in geom_format:
            # Pixelated grid models can approximate arbitrary planar patches via rasterization
            score_geom = 7.5
            details_geom = "Model uses binary pixel grid representation; requires 2D rasterization of canonical planar patches."
            preprocessing.append("2D rasterizer: project continuous polygons onto discrete binary pixel matrix.")
            matched_geoms = list(ANTON_CANONICAL_GEOMETRIES)  # Can rasterize any 2D planar polygon
            unmatched_geoms = []
        elif matched_geoms:
            ratio = len(matched_geoms) / len(ANTON_CANONICAL_GEOMETRIES)
            score_geom = min(10.0, 5.0 + ratio * 5.0)
            details_geom = f"Model explicitly supports {len(matched_geoms)} ANTON geometry type(s): {matched_geoms}."
            if unmatched_geoms:
                recommendations.append(f"Model does NOT support: {unmatched_geoms}. Do not assume rectangular models generalize.")
        else:
            score_geom = 2.0
            details_geom = f"No explicit overlap with ANTON's 8 canonical geometry types. Stated: {model.supported_geometries}."
            blockers.append("Geometry representation mismatch: Model does not support ANTON canonical planar geometries.")

        dims.append(DimensionCompatibility("Geometry Representation", score_geom >= 5.0, score_geom, details_geom))

        # 2. Parameter Compatibility
        input_params = [p.lower() for p in model.input_specification.parameters]
        if input_params:
            known_params = {"length", "width", "w", "l", "h", "height", "h_sub", "er", "eps_r", "feed_x", "feed_y", "fy", "slot", "w_slot", "l_slot"}
            overlap = [p for p in input_params if any(k in p for k in known_params)]
            score_param = (len(overlap) / len(input_params)) * 10.0 if input_params else 5.0
            details_param = f"Parameter overlap: {len(overlap)} of {len(input_params)} recognized ({overlap})."
            preprocessing.append(f"Parametric extraction: extract {[p for p in input_params]} from canonical ANTON layers and objects.")
        elif "pixel" in geom_format:
            score_param = 8.0
            details_param = "Non-parametric pixel representation: parameters derived from rasterization."
        else:
            score_param = 3.0
            details_param = "Undefined or non-standard input parameter specification."

        dims.append(DimensionCompatibility("Parameter Extraction", score_param >= 5.0, score_param, details_param))

        # 3. Material Compatibility
        mats = [m.lower() for m in model.supported_materials]
        if any(m in mats for m in ["fr4", "rogers", "alumina", "variable", "any", "dielectric"]):
            score_mat = 9.0
            details_mat = f"Supports dielectric substrate materials: {model.supported_materials}."
        elif mats:
            score_mat = 6.0
            details_mat = f"Restricted to specific material(s): {model.supported_materials}. Normalization required."
            preprocessing.append("Material property mapping: verify target substrate permittivity matches training domain.")
        else:
            score_mat = 4.0
            details_mat = "Material properties fixed or unparameterized in model architecture."
            recommendations.append("Substrate permittivity may be hardcoded into weights; test sensitivity to epsilon_r.")

        dims.append(DimensionCompatibility("Material Compatibility", score_mat >= 5.0, score_mat, details_mat))

        # 4. Frequency Range Compatibility
        fr = model.frequency_range
        if fr.f_min_ghz is not None and fr.f_max_ghz is not None:
            span = fr.f_max_ghz - fr.f_min_ghz
            score_freq = 9.0 if span >= 1.0 else 7.0
            details_freq = f"Specified frequency range: {fr.f_min_ghz:.2f} - {fr.f_max_ghz:.2f} GHz (Span: {span:.2f} GHz, Points: {fr.discrete_points or 'Continuous'})."
        else:
            score_freq = 4.0
            details_freq = "Frequency operational range unspecified or narrow single-frequency resonance only."

        dims.append(DimensionCompatibility("Frequency Range", score_freq >= 5.0, score_freq, details_freq))

        # 5. Input Tensor Compatibility
        in_spec = model.input_specification
        if in_spec.shape:
            score_in = 8.5
            details_in = f"Well-defined input tensor: shape={in_spec.shape}, dtype={in_spec.data_type}, norm={in_spec.normalization}."
            preprocessing.append(f"Input tensor assembly: construct shape {in_spec.shape} with {in_spec.normalization} scaling.")
        else:
            score_in = 3.0
            details_in = "Input tensor shape unspecified."
            blockers.append("Missing input tensor shape and normalization specification.")

        dims.append(DimensionCompatibility("Input Tensor Format", score_in >= 5.0, score_in, details_in))

        # 6. Output Tensor Compatibility
        out_spec = model.output_specification
        if out_spec.shape and out_spec.quantities:
            score_out = 9.0
            details_out = f"Well-defined output tensor: shape={out_spec.shape}, quantities={out_spec.quantities}."
        else:
            score_out = 3.5
            details_out = "Output tensor shape or physical quantities unspecified."
            blockers.append("Missing output tensor shape or target quantities specification.")

        dims.append(DimensionCompatibility("Output Tensor Format", score_out >= 5.0, score_out, details_out))

        # 7. S11 Representation Compatibility
        has_s11 = any(q.lower() in ["s11", "s_11", "return_loss", "s11_db", "s11_curve"] for q in out_spec.quantities)
        has_s11_cap = TargetCapability.S11_PREDICTION in model.target_capabilities
        if has_s11 or has_s11_cap:
            score_s11 = 9.5
            details_s11 = "Directly outputs frequency-dependent S11 return loss curve (in dB or complex reflection)."
        elif any(c in model.target_capabilities for c in [TargetCapability.INVERSE_DESIGN, TargetCapability.RESONANT_FREQUENCY_PREDICTION]):
            score_s11 = 7.0
            details_s11 = "Takes desired S11 or resonant frequency as input target for inverse geometric synthesis."
        else:
            score_s11 = 2.0
            details_s11 = "Model does not predict or ingest S11 scattering parameters."

        dims.append(DimensionCompatibility("S11 Representation", score_s11 >= 5.0, score_s11, details_s11))

        # 8. Radiation Data Compatibility (Gain, Efficiency, Pattern)
        rad_quantities = [q for q in out_spec.quantities if any(k in q.lower() for k in ["gain", "directivity", "efficiency", "pattern", "farfield"])]
        if rad_quantities:
            score_rad = 9.0
            details_rad = f"Model explicitly supports radiation metrics: {rad_quantities}."
        else:
            score_rad = 4.0
            details_rad = "Model does NOT predict far-field radiation patterns, gain, or efficiency (S11/geometry only)."
            recommendations.append("Do not claim radiation pattern or gain prediction; model targets impedance/S11 only.")

        dims.append(DimensionCompatibility("Radiation Metrics", score_rad >= 5.0, score_rad, details_rad))

        # 9. Framework & Execution Compatibility
        fw = model.framework.lower()
        if any(k in fw for k in ["pytorch", "torch", "sklearn", "scikit-learn"]):
            score_fw = 9.5
            details_fw = f"Direct Python framework compatibility ({model.framework})."
        elif any(k in fw for k in ["tensorflow", "keras"]):
            score_fw = 7.5
            details_fw = f"TensorFlow/Keras model ({model.framework}); requires TensorFlow runtime or ONNX export."
            recommendations.append("Recommend exporting Keras .h5 / SavedModel to ONNX for runtime execution.")
        elif "jax" in fw:
            score_fw = 6.0
            details_fw = "JAX-based model; requires specialized JAX environment."
        else:
            score_fw = 3.0
            details_fw = f"Framework '{model.framework}' requires specialized runtime environment."

        dims.append(DimensionCompatibility("Framework Compatibility", score_fw >= 5.0, score_fw, details_fw))

        # 10. Checkpoint Availability & Reproducibility
        if model.checkpoint_available and model.model_category == ModelCategory.CATEGORY_A:
            score_ckpt = 10.0
            details_ckpt = f"Verified checkpoint weights available ({len(model.checkpoints)} artifact(s))."
        elif model.model_category == ModelCategory.CATEGORY_B:
            score_ckpt = 5.0
            details_ckpt = "Training code available, but no pre-trained checkpoint weights committed. Requires manual training."
            recommendations.append("Model requires complete training on verified dataset before inference is possible.")
        elif model.model_category == ModelCategory.CATEGORY_C:
            score_ckpt = 3.0
            details_ckpt = "Dataset only. No model architecture or pretrained weights provided."
        else:
            score_ckpt = 2.0
            details_ckpt = "Research implementation without reproducible checkpoint files."

        dims.append(DimensionCompatibility("Checkpoint Availability", score_ckpt >= 5.0, score_ckpt, details_ckpt))

        # Calculate Overall Score (Weighted average across 10 dimensions)
        total_score = sum(d.score for d in dims)  # 0 to 100
        dim_scores = {d.dimension_name: round(d.score, 1) for d in dims}

        # Classify Compatibility Status
        if model.model_category == ModelCategory.CATEGORY_C:
            status = CompatibilityStatus.NOT_COMPATIBLE
        elif total_score >= 80.0 and model.checkpoint_available:
            status = CompatibilityStatus.DIRECTLY_COMPATIBLE
        elif total_score >= 60.0:
            status = CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING
        elif total_score >= 40.0:
            status = CompatibilityStatus.REQUIRES_ARCHITECTURE_MODIFICATION
        elif model.model_category == ModelCategory.CATEGORY_D or total_score < 30.0:
            status = CompatibilityStatus.INSUFFICIENT_INFORMATION
        else:
            status = CompatibilityStatus.NOT_COMPATIBLE

        summary_text = (
            f"Evaluated '{model.model_id}': Overall Score {total_score:.1f}/100. "
            f"Classified as {status.value}. "
            f"Pretrained weights: {'VERIFIED' if model.checkpoint_available else 'UNAVAILABLE'}."
        )

        return CompatibilityEvaluationResult(
            model_id=model.model_id,
            status=status,
            overall_score=round(total_score, 1),
            dimension_scores=dim_scores,
            dimensions=dims,
            supported_anton_geometries=matched_geoms,
            unsupported_anton_geometries=unmatched_geoms,
            required_preprocessing=preprocessing,
            adaptation_recommendations=recommendations,
            blockers=blockers,
            summary_text=summary_text,
        )


# Canonical aliases
CompatibilityAuditResult = CompatibilityEvaluationResult
ModelCompatibilityEvaluator = ModelCompatibilityAssessor
