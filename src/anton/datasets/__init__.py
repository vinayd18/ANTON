"""
ANTON Canonical Electromagnetic Dataset Subsystem.

Provides scientifically rigorous dataset schemas, ingestion pipelines,
electromagnetic validation, dual-tier storage, and ML dataset preparation.
"""

from anton.datasets.schema import (
    SourceType,
    QualityStatus,
    FrequencyUnit,
    LengthUnit,
    AngleUnit,
    ComplexFormat,
    AntennaIdentity,
    MaterialPropertiesRecord,
    SimulationMetadataRecord,
    FarFieldPattern2D,
    FarFieldPattern3D,
    ElectromagneticOutputsRecord,
    ProvenanceRecord,
    DatasetRecord,
)

__all__ = [
    "SourceType",
    "QualityStatus",
    "FrequencyUnit",
    "LengthUnit",
    "AngleUnit",
    "ComplexFormat",
    "AntennaIdentity",
    "MaterialPropertiesRecord",
    "SimulationMetadataRecord",
    "FarFieldPattern2D",
    "FarFieldPattern3D",
    "ElectromagneticOutputsRecord",
    "ProvenanceRecord",
    "DatasetRecord",
]

