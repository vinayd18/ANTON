"""
Generic Multi-Target Parametric Dataset Adapter.

Provides configurable feature extraction and frequency grid resampling
for custom and arbitrary antenna machine learning models.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np

from anton.datasets.schema import DatasetRecord
from anton.datasets.ml.frequency_grid import FrequencyGridAligner
from anton.datasets.ml.feature_extractor import FeatureExtractor


class GenericAdapter:
    """
    Highly configurable adapter supporting user-defined frequency bands,
    custom parameter sets, and 2D conductivity rasterization.
    """

    def __init__(
        self,
        target_f_min: float,
        target_f_max: float,
        num_points: int = 101,
        include_raster_mask: bool = False,
        raster_size: int = 32,
    ):
        self.aligner = FrequencyGridAligner(
            target_f_min=target_f_min,
            target_f_max=target_f_max,
            num_points=num_points,
        )
        self.include_raster_mask = include_raster_mask
        self.raster_size = raster_size

    def prepare_sample(
        self,
        record: DatasetRecord
    ) -> Dict[str, np.ndarray]:
        """
        Extracts a dictionary of tensors for the given record:
        - 'features_params': continuous parameter vector
        - 'features_raster': 2D binary/conductivity mask (if enabled)
        - 's11_db': resampled S11
        - 'complex_s11': resampled (re, im) if available
        """
        outputs = record.outputs
        params = FeatureExtractor.extract_continuous_vector(record)

        result: Dict[str, np.ndarray] = {
            "features_params": params,
        }

        if self.include_raster_mask:
            mask = FeatureExtractor.rasterize_patch_2d(record, grid_size=self.raster_size)
            result["features_raster"] = mask

        # Resample responses
        if outputs.s11_db is not None and self.aligner.is_compatible(outputs.frequencies_ghz):
            result["s11_db"] = self.aligner.resample_curve(outputs.frequencies_ghz, outputs.s11_db)

        if outputs.has_complex_s11 and outputs.s11_real and outputs.s11_imag and self.aligner.is_compatible(outputs.frequencies_ghz):
            re_res, im_res = self.aligner.resample_complex_s11(
                outputs.frequencies_ghz, outputs.s11_real, outputs.s11_imag
            )
            result["s11_real"] = re_res
            result["s11_imag"] = im_res

        if outputs.gain_dbi is not None and self.aligner.is_compatible(outputs.frequencies_ghz):
            result["gain_dbi"] = self.aligner.resample_curve(outputs.frequencies_ghz, outputs.gain_dbi)

        return result

