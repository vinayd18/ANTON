"""
Feature and Target Scalers for ML Dataset Preparation.

Implements Min-Max and Standard Scalers that fit strictly on training splits
and export their normalization parameters for reproducible deployment.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
import numpy as np


class MinMaxScaler:
    """
    Scales features linearly into [feature_range[0], feature_range[1]].
    Fit strictly on training data.
    """

    def __init__(self, feature_range: tuple = (0.0, 1.0)):
        self.feature_range = feature_range
        self.data_min_: Optional[np.ndarray] = None
        self.data_max_: Optional[np.ndarray] = None
        self.scale_: Optional[np.ndarray] = None
        self.min_: Optional[np.ndarray] = None
        self.is_fitted = False

    def fit(self, x: np.ndarray) -> MinMaxScaler:
        """Computes min and max for scaling across axis 0."""
        x = np.asarray(x, dtype=np.float64)
        self.data_min_ = np.min(x, axis=0)
        self.data_max_ = np.max(x, axis=0)
        data_range = self.data_max_ - self.data_min_
        data_range[data_range == 0.0] = 1.0  # Prevent division by zero

        scale = (self.feature_range[1] - self.feature_range[0]) / data_range
        self.scale_ = scale
        self.min_ = self.feature_range[0] - self.data_min_ * scale
        self.is_fitted = True
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Transforms input array using fitted parameters."""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fit before transforming data.")
        x = np.asarray(x, dtype=np.float64)
        return (x * self.scale_ + self.min_).astype(np.float32)

    def inverse_transform(self, x: np.ndarray) -> np.ndarray:
        """Inverts scaling back to original physical domain."""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fit before inverse transforming data.")
        x = np.asarray(x, dtype=np.float64)
        return ((x - self.min_) / self.scale_).astype(np.float32)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes fitted scaler parameters to JSON-compatible dictionary."""
        return {
            "type": "MinMaxScaler",
            "feature_range": list(self.feature_range),
            "data_min": self.data_min_.tolist() if self.data_min_ is not None else None,
            "data_max": self.data_max_.tolist() if self.data_max_ is not None else None,
            "scale": self.scale_.tolist() if self.scale_ is not None else None,
            "min": self.min_.tolist() if self.min_ is not None else None,
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> MinMaxScaler:
        """Reconstructs scaler from dictionary."""
        scaler = cls(feature_range=tuple(d["feature_range"]))
        scaler.data_min_ = np.array(d["data_min"])
        scaler.data_max_ = np.array(d["data_max"])
        scaler.scale_ = np.array(d["scale"])
        scaler.min_ = np.array(d["min"])
        scaler.is_fitted = d["is_fitted"]
        return scaler


class StandardScaler:
    """
    Standardizes features by removing the mean and scaling to unit variance.
    Fit strictly on training data.
    """

    def __init__(self, with_mean: bool = True, with_std: bool = True):
        self.with_mean = with_mean
        self.with_std = with_std
        self.mean_: Optional[np.ndarray] = None
        self.std_: Optional[np.ndarray] = None
        self.is_fitted = False

    def fit(self, x: np.ndarray) -> StandardScaler:
        """Computes mean and std across axis 0."""
        x = np.asarray(x, dtype=np.float64)
        if self.with_mean:
            self.mean_ = np.mean(x, axis=0)
        else:
            self.mean_ = np.zeros(x.shape[1], dtype=np.float64)

        if self.with_std:
            std = np.std(x, axis=0)
            std[std == 0.0] = 1.0  # Prevent division by zero
            self.std_ = std
        else:
            self.std_ = np.ones(x.shape[1], dtype=np.float64)

        self.is_fitted = True
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Transforms input array using fitted mean and std."""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fit before transforming data.")
        x = np.asarray(x, dtype=np.float64)
        return ((x - self.mean_) / self.std_).astype(np.float32)

    def inverse_transform(self, x: np.ndarray) -> np.ndarray:
        """Inverts standardization back to original domain."""
        if not self.is_fitted:
            raise RuntimeError("Scaler must be fit before inverse transforming data.")
        x = np.asarray(x, dtype=np.float64)
        return (x * self.std_ + self.mean_).astype(np.float32)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes fitted scaler parameters to dictionary."""
        return {
            "type": "StandardScaler",
            "with_mean": self.with_mean,
            "with_std": self.with_std,
            "mean": self.mean_.tolist() if self.mean_ is not None else None,
            "std": self.std_.tolist() if self.std_ is not None else None,
            "is_fitted": self.is_fitted,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> StandardScaler:
        """Reconstructs scaler from dictionary."""
        scaler = cls(with_mean=d["with_mean"], with_std=d["with_std"])
        scaler.mean_ = np.array(d["mean"])
        scaler.std_ = np.array(d["std"])
        scaler.is_fitted = d["is_fitted"]
        return scaler
