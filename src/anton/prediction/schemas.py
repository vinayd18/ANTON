# -*- coding: utf-8 -*-
"""Canonical Pydantic-v2 schema for ANTON electromagnetic predictions.

Defines typed request, response, status, quantity, and uncertainty models.
Ensures zero ambiguity in prediction results and enforces explicit null/absence
for unavailable or uncomputed electromagnetic quantities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PredictionStatus(str, Enum):
    """Execution status for electromagnetic prediction requests."""

    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_INCOMPATIBLE = "MODEL_INCOMPATIBLE"
    INPUT_INVALID = "INPUT_INVALID"
    MODEL_NOT_VALIDATED = "MODEL_NOT_VALIDATED"
    INFERENCE_FAILED = "INFERENCE_FAILED"


class ElectromagneticQuantity(str, Enum):
    """Electromagnetic quantities supported by the ANTON prediction subsystem."""

    S11_COMPLEX = "S11_COMPLEX"
    S11_DB = "S11_DB"
    S11_MAGNITUDE = "S11_MAGNITUDE"
    S11_PHASE = "S11_PHASE"
    VSWR = "VSWR"
    INPUT_IMPEDANCE = "INPUT_IMPEDANCE"
    RESONANT_FREQUENCY = "RESONANT_FREQUENCY"
    IMPEDANCE_BANDWIDTH = "IMPEDANCE_BANDWIDTH"
    GAIN = "GAIN"
    REALIZED_GAIN = "REALIZED_GAIN"
    DIRECTIVITY = "DIRECTIVITY"
    RADIATION_EFFICIENCY = "RADIATION_EFFICIENCY"
    TOTAL_EFFICIENCY = "TOTAL_EFFICIENCY"
    RADIATION_PATTERN_2D = "RADIATION_PATTERN_2D"
    RADIATION_PATTERN_3D = "RADIATION_PATTERN_3D"


class UncertaintyMethod(str, Enum):
    """Method used for estimating prediction uncertainty."""

    NONE = "NONE"
    ENSEMBLE_VARIANCE = "ENSEMBLE_VARIANCE"
    MONTE_CARLO_DROPOUT = "MONTE_CARLO_DROPOUT"
    QUANTILE_REGRESSION = "QUANTILE_REGRESSION"
    CONFORMAL_PREDICTION = "CONFORMAL_PREDICTION"


# ---------------------------------------------------------------------------
# Uncertainty Schema
# ---------------------------------------------------------------------------

class QuantityUncertainty(BaseModel):
    """Confidence intervals or uncertainty estimates for a predicted quantity."""

    quantity: ElectromagneticQuantity
    method: UncertaintyMethod = UncertaintyMethod.NONE
    confidence_level: float = 0.95
    lower_bound: Optional[List[float]] = None
    upper_bound: Optional[List[float]] = None
    standard_deviation: Optional[List[float]] = None
    notes: Optional[str] = None


class PredictionUncertainty(BaseModel):
    """Overall uncertainty information for a prediction response."""

    uncertainty_status: str = "NOT_AVAILABLE"  # "AVAILABLE", "NOT_AVAILABLE", "NOT_SUPPORTED"
    quantities: Dict[str, QuantityUncertainty] = Field(default_factory=dict)
    global_confidence_score: Optional[float] = None
    method_details: Optional[str] = None


# ---------------------------------------------------------------------------
# Request Configuration
# ---------------------------------------------------------------------------

class FrequencyConfig(BaseModel):
    """Frequency configuration for prediction."""

    f_min_hz: float = Field(..., gt=0.0, description="Minimum frequency in Hz")
    f_max_hz: float = Field(..., gt=0.0, description="Maximum frequency in Hz")
    num_points: int = Field(default=201, ge=2, le=5000, description="Number of frequency sample points")
    sweep_type: str = Field(default="linear", description="Sweep type: 'linear' or 'log'")

    @model_validator(mode="after")
    def check_bounds(self) -> FrequencyConfig:
        if self.f_max_hz <= self.f_min_hz:
            raise ValueError(f"f_max_hz ({self.f_max_hz}) must be strictly greater than f_min_hz ({self.f_min_hz})")
        return self


class PredictionConfig(BaseModel):
    """Optional settings for prediction computation."""

    raster_size: int = Field(default=64, description="Raster grid size (e.g. 32, 64, 128) if 2D mask is used")
    include_uncertainty: bool = Field(default=False, description="Whether to compute uncertainty if supported")
    conformal_alpha: float = Field(default=0.05, ge=0.01, le=0.5, description="Significance level for conformal prediction")
    custom_parameters: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary adapter-specific configuration")


# ---------------------------------------------------------------------------
# Prediction Request
# ---------------------------------------------------------------------------

class PredictionRequest(BaseModel):
    """Universal canonical prediction request for the ANTON EM prediction engine."""

    request_id: str = Field(default_factory=lambda: str(uuid4()), description="Unique request identifier")
    design_id: Optional[str] = Field(default=None, description="Identifier of the antenna design")
    geometry: Dict[str, Any] = Field(..., description="Canonical geometry definition (dictionary or serialized GeometryProject)")
    geometry_hash: Optional[str] = Field(default=None, description="SHA-256 hash of canonical geometry for cache/provenance")
    requested_quantities: List[ElectromagneticQuantity] = Field(
        default_factory=lambda: [
            ElectromagneticQuantity.S11_DB,
            ElectromagneticQuantity.VSWR,
            ElectromagneticQuantity.RESONANT_FREQUENCY,
        ],
        description="List of electromagnetic quantities requested"
    )
    frequency: Optional[FrequencyConfig] = Field(
        default=None,
        description="Frequency range and point count configuration"
    )
    port_id: Optional[str] = Field(default=None, description="Target port ID for multi-port designs")
    z0_ohm: float = Field(default=50.0, gt=0.0, description="Reference characteristic impedance in Ohms")
    model_id: Optional[str] = Field(default=None, description="Target model ID. If None, orchestrator selects best compatible model")
    model_version: Optional[str] = Field(default=None, description="Target model version")
    config: PredictionConfig = Field(default_factory=PredictionConfig, description="Prediction configuration parameters")
    units: Dict[str, str] = Field(
        default_factory=lambda: {"length": "mm", "frequency": "GHz"},
        description="Specified units for input parameters"
    )

    @field_validator("requested_quantities")
    @classmethod
    def validate_requested_quantities(cls, v: List[ElectromagneticQuantity]) -> List[ElectromagneticQuantity]:
        if not v:
            raise ValueError("requested_quantities must contain at least one ElectromagneticQuantity")
        return list(dict.fromkeys(v))  # deduplicate preserving order


# ---------------------------------------------------------------------------
# Numerical Results Schema
# ---------------------------------------------------------------------------

class S11ComplexPoint(BaseModel):
    """Complex S11 parameter at a single frequency."""
    frequency_hz: float
    real: float
    imag: float
    magnitude: float
    db: float
    phase_rad: Optional[float] = None
    phase_deg: Optional[float] = None


class ResonanceInfo(BaseModel):
    """Detected resonance peak."""
    resonant_frequency_hz: float
    s11_db: float
    bandwidth_10db_hz: Optional[float] = None
    fractional_bandwidth_percent: Optional[float] = None
    q_factor: Optional[float] = None


class ImpedanceBandwidth(BaseModel):
    """Impedance bandwidth interval matching a threshold (e.g. -10 dB or VSWR <= 2.0)."""
    threshold_db: float = -10.0
    f_lower_hz: float
    f_upper_hz: float
    bandwidth_hz: float
    fractional_bandwidth_percent: float
    center_frequency_hz: float


class PatternCut2D(BaseModel):
    """2D Radiation pattern cut (E-plane or H-plane)."""
    cut_plane: str  # "phi=0" (E-plane), "phi=90" (H-plane), "theta=90", etc.
    angles_deg: List[float]
    gain_dbi: List[float]
    directivity_dbi: Optional[List[float]] = None
    cross_polarization_dbi: Optional[List[float]] = None


class ElectromagneticResults(BaseModel):
    """Electromagnetic quantities predicted by an adapter/model.

    Quantities not computed or not available are explicitly None.
    """

    s11_complex: Optional[List[S11ComplexPoint]] = None
    s11_db: Optional[List[float]] = None
    s11_magnitude: Optional[List[float]] = None
    s11_phase_rad: Optional[List[float]] = None
    s11_phase_deg: Optional[List[float]] = None
    vswr: Optional[List[float]] = None
    input_impedance_real_ohm: Optional[List[float]] = None
    input_impedance_imag_ohm: Optional[List[float]] = None
    resonant_frequencies: Optional[List[ResonanceInfo]] = None
    primary_resonant_frequency_hz: Optional[float] = None
    impedance_bandwidths: Optional[List[ImpedanceBandwidth]] = None
    gain_dbi: Optional[List[float]] = None
    peak_gain_dbi: Optional[float] = None
    realized_gain_dbi: Optional[List[float]] = None
    directivity_dbi: Optional[List[float]] = None
    radiation_efficiency: Optional[List[float]] = None
    total_efficiency: Optional[List[float]] = None
    radiation_pattern_2d: Optional[List[PatternCut2D]] = None
    radiation_pattern_3d: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Prediction Response
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Universal canonical prediction response from the ANTON EM prediction engine."""

    request_id: str
    status: PredictionStatus
    status_message: str
    geometry_hash: Optional[str] = None
    model_id: Optional[str] = None
    model_version: Optional[str] = None
    model_provenance: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    frequency_grid_hz: Optional[List[float]] = None
    results: ElectromagneticResults = Field(default_factory=ElectromagneticResults)
    available_outputs: List[ElectromagneticQuantity] = Field(default_factory=list)
    missing_outputs: List[ElectromagneticQuantity] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    compatibility_assessment: Optional[Dict[str, Any]] = None
    validation_status: Optional[str] = None
    uncertainty: PredictionUncertainty = Field(default_factory=PredictionUncertainty)
    execution_time_ms: float = 0.0

    @classmethod
    def create_unavailable(
        cls,
        request_id: str,
        reason: str,
        status: PredictionStatus = PredictionStatus.MODEL_UNAVAILABLE,
        geometry_hash: Optional[str] = None,
        model_id: Optional[str] = None,
        requested_quantities: Optional[List[ElectromagneticQuantity]] = None,
        compatibility_assessment: Optional[Dict[str, Any]] = None,
        validation_status: Optional[str] = "NOT_VALIDATED",
    ) -> PredictionResponse:
        """Factory for generating a structured unavailable/incompatible response."""
        req_q = requested_quantities or []
        return cls(
            request_id=request_id,
            status=status,
            status_message=reason,
            geometry_hash=geometry_hash,
            model_id=model_id,
            results=ElectromagneticResults(),
            available_outputs=[],
            missing_outputs=req_q,
            warnings=[reason],
            compatibility_assessment=compatibility_assessment,
            validation_status=validation_status,
            uncertainty=PredictionUncertainty(
                uncertainty_status="NOT_AVAILABLE",
                method_details="Prediction unavailable; no uncertainty computed."
            ),
            execution_time_ms=0.0,
        )
