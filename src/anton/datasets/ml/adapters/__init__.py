"""
Model-Specific Dataset Adapters.
"""

from anton.datasets.ml.adapters.antennanet_adapter import AntennaNetAdapter
from anton.datasets.ml.adapters.youxch_adapter import YouxchAdapter
from anton.datasets.ml.adapters.generic_adapter import GenericAdapter

__all__ = [
    "AntennaNetAdapter",
    "YouxchAdapter",
    "GenericAdapter",
]

