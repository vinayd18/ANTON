"""
ML-Ready Dataset Preparation Subpackage.

Provides:
- Geometry-leakage-free splitting (DatasetSplitter)
- PCHIP frequency grid alignment (FrequencyGridAligner)
- Continuous parameter extraction and 2D rasterization (FeatureExtractor)
- Train-only feature and target scalers (MinMaxScaler, StandardScaler)
- Model-specific adapters (AntennaNetAdapter, YouxchAdapter, GenericAdapter)
"""

from anton.datasets.ml.splitter import DatasetSplitter
from anton.datasets.ml.frequency_grid import FrequencyGridAligner
from anton.datasets.ml.feature_extractor import FeatureExtractor
from anton.datasets.ml.scalers import MinMaxScaler, StandardScaler
from anton.datasets.ml.adapters import AntennaNetAdapter, YouxchAdapter, GenericAdapter

__all__ = [
    "DatasetSplitter",
    "FrequencyGridAligner",
    "FeatureExtractor",
    "MinMaxScaler",
    "StandardScaler",
    "AntennaNetAdapter",
    "YouxchAdapter",
    "GenericAdapter",
]
