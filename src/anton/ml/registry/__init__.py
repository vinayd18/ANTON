# -*- coding: utf-8 -*-
"""ANTON Machine Learning Model Registry Subsystem.

Exports registry engine, metadata schemas, compatibility evaluators,
licensing auditors, benchmark evaluators, and secure loaders.
"""

from anton.ml.registry.model_compatibility import (
    CompatibilityAuditResult,
    ModelCompatibilityEvaluator,
)
from anton.ml.registry.model_evaluator import (
    AntennaBenchmarkEvaluator,
    BenchmarkEvaluationReport,
    EvaluationSlice,
    MetricResult,
)
from anton.ml.registry.model_licensing import (
    LicenseAssessmentResult,
    ModelLicensingAuditor,
)
from anton.ml.registry.model_loader import (
    CheckpointInspectionResult,
    CheckpointSecurityError,
    ModelLoader,
    ReadOnlyWeightViolationError,
)
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
from anton.ml.registry.model_registry import ModelRegistry

__all__ = [
    "ModelRegistry",
    "ModelMetadata",
    "ModelCategory",
    "ModelEntityType",
    "TargetCapability",
    "CompatibilityStatus",
    "EvaluationStatus",
    "IntegrationStatus",
    "CheckpointLoadVerification",
    "InferenceVerification",
    "FineTuningReadiness",
    "InputSpecification",
    "OutputSpecification",
    "FrequencyRange",
    "DatasetMetadata",
    "HardwareRequirements",
    "CheckpointInfo",
    "ModelLicensingAuditor",
    "LicenseAssessmentResult",
    "ModelCompatibilityEvaluator",
    "CompatibilityAuditResult",
    "AntennaBenchmarkEvaluator",
    "BenchmarkEvaluationReport",
    "EvaluationSlice",
    "MetricResult",
    "ModelLoader",
    "CheckpointInspectionResult",
    "CheckpointSecurityError",
    "ReadOnlyWeightViolationError",
]

