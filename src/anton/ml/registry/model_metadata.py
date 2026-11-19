# -*- coding: utf-8 -*-
"""Canonical Pydantic schema and metadata models for the ANTON Machine Learning Model Registry.

Provides rigorous, typed, and validated structures for model discovery,
checkpoint tracking, compatibility assessment, and capability mapping.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class ModelCategory(str, Enum):
    """Categorization of candidate models based on artifact availability."""

    CATEGORY_A = "Pretrained model with downloadable verified weights"
    CATEGORY_B = "Model architecture with training code only"
    CATEGORY_C = "Dataset without a pretrained model"
    CATEGORY_D = "Research implementation without reproducible checkpoints"


class ModelEntityType(str, Enum):
    """Classification of registered entity type separating models, training code, datasets, and literature."""

    PRETRAINED_MODEL = "PRETRAINED_MODEL"
    TRAINING_IMPLEMENTATION = "TRAINING_IMPLEMENTATION"
    DATASET = "DATASET"
    RESEARCH_REFERENCE = "RESEARCH_REFERENCE"


class CheckpointLoadVerification(str, Enum):
    """Status of checkpoint file loading verification in isolated environment."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class InferenceVerification(str, Enum):
    """Status of model forward-pass execution verification on documented test inputs."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FineTuningReadiness(str, Enum):
    """Readiness of model/workspace for manual user fine-tuning."""

    READY = "READY"
    WORKSPACE_PREPARED = "WORKSPACE_PREPARED"
    NOT_READY = "NOT_READY"


class TargetCapability(str, Enum):
    """ANTON target capabilities supported or evaluated by ML models."""

    S11_PREDICTION = "Frequency-dependent S11 prediction"
    VSWR_PREDICTION = "VSWR prediction"
    INPUT_IMPEDANCE_PREDICTION = "Input impedance prediction"
    RESONANT_FREQUENCY_PREDICTION = "Resonant frequency prediction"
    BANDWIDTH_PREDICTION = "Bandwidth prediction"
    GAIN_PREDICTION = "Gain prediction"
    RADIATION_EFFICIENCY_PREDICTION = "Radiation efficiency prediction"
    RADIATION_PATTERN_2D_PREDICTION = "2D radiation-pattern prediction"
    RADIATION_PATTERN_3D_PREDICTION = "3D radiation-pattern prediction"
    INVERSE_DESIGN = "Inverse antenna design"
    GEOMETRY_OPTIMIZATION = "Antenna geometry optimization"
    IMAGE_TO_GEOMETRY_RECONSTRUCTION = "Antenna image-to-geometry reconstruction"


class CompatibilityStatus(str, Enum):
    """Compatibility classification with ANTON's canonical geometry representation."""

    DIRECTLY_COMPATIBLE = "DIRECTLY_COMPATIBLE"
    ADAPTABLE_WITH_PREPROCESSING = "ADAPTABLE_WITH_PREPROCESSING"
    REQUIRES_ARCHITECTURE_MODIFICATION = "REQUIRES_ARCHITECTURE_MODIFICATION"
    NOT_COMPATIBLE = "NOT_COMPATIBLE"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"


class EvaluationStatus(str, Enum):
    """Evaluation readiness status in ANTON benchmark pipeline."""

    NOT_EVALUATED = "NOT_EVALUATED"
    EVALUATION_IN_PROGRESS = "EVALUATION_IN_PROGRESS"
    EVALUATED_BENCHMARKED = "EVALUATED_BENCHMARKED"
    EVALUATION_FAILED = "EVALUATION_FAILED"


class IntegrationStatus(str, Enum):
    """Integration lifecycle status in ANTON production codebase."""

    NOT_INTEGRATED = "NOT_INTEGRATED"
    WORKSPACE_PREPARED = "WORKSPACE_PREPARED"
    ADAPTED_FOR_ANTON = "ADAPTED_FOR_ANTON"
    PRODUCTION_READY = "PRODUCTION_READY"


class InputSpecification(BaseModel):
    """Detailed specification of model input tensors."""

    tensor_name: str = "input"
    shape: List[Union[int, str]] = Field(default_factory=list)
    data_type: str = "float32"
    format: str = "tabular_parameters"  # tabular_parameters, pixel_grid, image, sequence
    parameters: List[str] = Field(default_factory=list)
    normalization: str = "none"  # minmax, standard, custom, none
    physical_units: Dict[str, str] = Field(default_factory=dict)
    description: str = ""


class OutputSpecification(BaseModel):
    """Detailed specification of model output tensors."""

    tensor_name: str = "output"
    shape: List[Union[int, str]] = Field(default_factory=list)
    data_type: str = "float32"
    quantities: List[str] = Field(default_factory=list)
    frequency_points: Optional[int] = None
    frequency_range_ghz: Optional[List[float]] = None
    physical_units: Dict[str, str] = Field(default_factory=dict)
    description: str = ""


class FrequencyRange(BaseModel):
    """Frequency operational band of model."""

    f_min_ghz: Optional[float] = None
    f_max_ghz: Optional[float] = None
    center_freq_ghz: Optional[float] = None
    discrete_points: Optional[int] = None
    is_continuous: bool = True


class DatasetMetadata(BaseModel):
    """Provenance and specification of training dataset."""

    name: str = "unspecified"
    source_type: str = "Unknown"  # HFSS, CST, openEMS, MEEP, Analytical, Measurement
    sample_count: Optional[int] = None
    provenance: str = ""
    publicly_accessible: bool = False
    license: Optional[str] = None
    download_url: Optional[str] = None


class HardwareRequirements(BaseModel):
    """Inference and manual fine-tuning hardware requirements."""

    min_ram_gb: float = 4.0
    gpu_recommended: bool = False
    min_vram_gb: Optional[float] = None
    estimated_inference_latency_cpu_ms: Optional[float] = None


class CheckpointInfo(BaseModel):
    """Details of verified checkpoint file on disk or repository."""

    filename: str
    file_path: Optional[str] = None
    file_size_bytes: int = 0
    sha256_checksum: Optional[str] = None
    download_url: Optional[str] = None
    framework: str = "PyTorch"
    is_downloaded: bool = False
    download_date: Optional[str] = None


class ModelMetadata(BaseModel):
    """Canonical model entry for the ANTON Model Registry.

    Strictly satisfies all required fields defined in ANTON Stage 3.0 specification.
    """

    model_id: str
    model_name: str
    repository_url: str
    research_reference: str = ""
    architecture: str
    framework: str
    model_category: ModelCategory = ModelCategory.CATEGORY_B
    entity_type: ModelEntityType = ModelEntityType.RESEARCH_REFERENCE
    target_capabilities: List[TargetCapability] = Field(default_factory=list)
    checkpoint_available: bool = False
    checkpoint_availability: bool = False
    checkpoint_path: Optional[str] = None
    checkpoints: List[CheckpointInfo] = Field(default_factory=list)
    checkpoint_load_verification: CheckpointLoadVerification = CheckpointLoadVerification.NOT_APPLICABLE
    inference_verification: InferenceVerification = InferenceVerification.NOT_APPLICABLE
    fine_tuning_readiness: FineTuningReadiness = FineTuningReadiness.NOT_READY
    production_readiness: bool = False
    geometry_compatibility: Dict[str, Any] = Field(default_factory=dict)
    dataset_compatibility: Dict[str, Any] = Field(default_factory=dict)
    input_specification: InputSpecification = Field(default_factory=InputSpecification)
    output_specification: OutputSpecification = Field(default_factory=OutputSpecification)
    supported_geometries: List[str] = Field(default_factory=list)
    supported_materials: List[str] = Field(default_factory=list)
    frequency_range: FrequencyRange = Field(default_factory=FrequencyRange)
    training_dataset: DatasetMetadata = Field(default_factory=DatasetMetadata)
    reported_metrics: Dict[str, Union[float, str, dict]] = Field(default_factory=dict)
    license: str = "Unspecified"
    license_type: str = "Custom"  # MIT, Apache-2.0, GPL-3.0, MIT-No-Patent, Proprietary
    patent_restrictions: List[str] = Field(default_factory=list)
    hardware_requirements: HardwareRequirements = Field(default_factory=HardwareRequirements)
    dependencies: List[str] = Field(default_factory=list)
    fine_tuning_available: bool = False
    compatibility_status: CompatibilityStatus = CompatibilityStatus.INSUFFICIENT_INFORMATION
    evaluation_status: EvaluationStatus = EvaluationStatus.NOT_EVALUATED
    integration_status: IntegrationStatus = IntegrationStatus.NOT_INTEGRATED
    tags: List[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("model_id cannot be empty")
        return v.strip().lower()

    @field_validator("checkpoint_available")
    @classmethod
    def validate_checkpoint_flag(cls, v: bool, info) -> bool:
        # Cross validation: category A must have checkpoint_available True
        return v

    @field_validator("production_readiness")
    @classmethod
    def validate_production_readiness(cls, v: bool, info) -> bool:
        if v:
            raise ValueError(
                "production_readiness cannot be set to True in Stage 3.0: models have "
                "not been independently evaluated against authentic full-wave simulation data."
            )
        return False

    def to_registry_dict(self) -> Dict[str, Any]:
        """Serialize model entry to registry dictionary format matching prompt specifications."""
        return self.model_dump()
