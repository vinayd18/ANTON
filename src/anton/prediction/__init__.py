"""ANTON Prediction Subsystem.

Model-agnostic electromagnetic prediction engine, feature processing,
adapter framework, model compatibility auditing, and postprocessing.
"""

from anton.prediction.schemas import (
    ElectromagneticQuantity,
    PredictionConfig,
    PredictionRequest,
    PredictionResponse,
    PredictionStatus,
)

__all__ = [
    "ElectromagneticQuantity",
    "PredictionConfig",
    "PredictionRequest",
    "PredictionResponse",
    "PredictionStatus",
]
