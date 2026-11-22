"""
Comprehensive Data Validation Engine for Electromagnetic Records.

Implements:
- Structural validation (metadata, array sizes, monotonic frequencies, NaN/Inf checks)
- Electromagnetic physical sanity checks (passivity, VSWR, complex consistency, efficiency, gain)
- Solver convergence status checks
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from anton.datasets.schema import (
    DatasetRecord,
    ElectromagneticOutputsRecord,
    QualityStatus,
    SourceType,
)


class ValidationIssue:
    """Represents a single validation check failure or warning."""

    def __init__(self, code: str, message: str, severity: str = "ERROR"):
        self.code = code
        self.message = message
        self.severity = severity.upper()  # ERROR, WARNING, INFO

    def to_dict(self) -> Dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}

    def __repr__(self) -> str:
        return f"[{self.severity}] {self.code}: {self.message}"


class StructuralValidator:
    """
    Validates data structures, array consistency, non-emptiness, and numerical integrity.
    """

    def validate(self, record: DatasetRecord) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1. Identity & Geometry linkage
        if not record.antenna_identity.design_id:
            issues.append(ValidationIssue("EMPTY_DESIGN_ID", "Antenna design ID cannot be empty."))
        if not record.antenna_identity.geometry_id:
            issues.append(ValidationIssue("EMPTY_GEOMETRY_ID", "Geometry ID reference cannot be empty."))
        if not record.geometry:
            issues.append(ValidationIssue("EMPTY_GEOMETRY", "Canonical geometry dictionary is empty."))

        # 2. Material sanity
        mat = record.materials
        if mat.permittivity_r <= 0.0 or math.isnan(mat.permittivity_r):
            issues.append(ValidationIssue("INVALID_PERMITTIVITY", f"Relative permittivity must be positive, got {mat.permittivity_r}"))
        if mat.substrate_thickness_mm <= 0.0 or math.isnan(mat.substrate_thickness_mm):
            issues.append(ValidationIssue("INVALID_SUBSTRATE_HEIGHT", f"Substrate thickness must be positive, got {mat.substrate_thickness_mm}"))
        if mat.loss_tangent < 0.0:
            issues.append(ValidationIssue("NEGATIVE_LOSS_TANGENT", f"Loss tangent cannot be negative, got {mat.loss_tangent}"))

        # 3. Frequency array validation
        outputs = record.outputs
        freqs = outputs.frequencies_ghz

        if not freqs or len(freqs) == 0:
            issues.append(ValidationIssue("EMPTY_FREQUENCIES", "Frequency grid cannot be empty."))
            return issues

        n_pts = len(freqs)

        # Check for NaN or Inf in frequencies
        if any(math.isnan(f) or math.isinf(f) for f in freqs):
            issues.append(ValidationIssue("NAN_OR_INF_FREQUENCY", "Frequency grid contains NaN or Infinite values."))

        # Check for negative frequencies
        if any(f <= 0.0 for f in freqs):
            issues.append(ValidationIssue("NON_POSITIVE_FREQUENCY", "All frequency points must be strictly positive (> 0 GHz)."))

        # Check strictly monotonic increasing
        for i in range(1, n_pts):
            if freqs[i] <= freqs[i - 1]:
                issues.append(
                    ValidationIssue(
                        "DISORDERED_FREQUENCIES",
                        f"Frequency grid is not strictly increasing at index {i}: {freqs[i]} <= {freqs[i-1]}"
                    )
                )
                break

        # Check array lengths consistency
        for arr_name, arr in [
            ("s11_real", outputs.s11_real),
            ("s11_imag", outputs.s11_imag),
            ("s11_magnitude", outputs.s11_magnitude),
            ("s11_phase_rad", outputs.s11_phase_rad),
            ("s11_db", outputs.s11_db),
            ("vswr", outputs.vswr),
            ("zin_real", outputs.zin_real),
            ("zin_imag", outputs.zin_imag),
        ]:
            if arr is not None:
                if len(arr) != n_pts:
                    issues.append(
                        ValidationIssue(
                            "ARRAY_LENGTH_MISMATCH",
                            f"{arr_name} length ({len(arr)}) does not match frequencies length ({n_pts})."
                        )
                    )
                # Check for NaNs
                if any(math.isnan(v) for v in arr):
                    issues.append(ValidationIssue("NAN_IN_RESPONSE", f"{arr_name} contains NaN values."))
                # Check for Infs (except vswr can have high finite clamp)
                if arr_name != "vswr" and any(math.isinf(v) for v in arr):
                    issues.append(ValidationIssue("INF_IN_RESPONSE", f"{arr_name} contains Infinite values."))

        return issues


class ElectromagneticValidator:
    """
    Validates physical plausibility of electromagnetic simulation or measurement data.
    """

    def __init__(self, passivity_tolerance: float = 0.05):
        self.passivity_tolerance = passivity_tolerance  # Allows up to 1.05 before strict error

    def validate(self, record: DatasetRecord) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        outputs = record.outputs

        # 1. Passivity check on |S11|
        # For passive one-port antenna, |S11| <= 1.0 (0 dB).
        if outputs.s11_magnitude is not None:
            max_mag = max(outputs.s11_magnitude)
            if max_mag > 1.0 + self.passivity_tolerance:
                issues.append(
                    ValidationIssue(
                        "NON_PASSIVE_S11",
                        f"Non-passive reflection coefficient: peak |S11| = {max_mag:.4f} > 1.0 + tol ({1.0 + self.passivity_tolerance})",
                        severity="ERROR"
                    )
                )
            elif max_mag > 1.0001:
                issues.append(
                    ValidationIssue(
                        "SLIGHT_PASSIVITY_VIOLATION",
                        f"Peak |S11| slightly exceeds unity: {max_mag:.4f} <= 1.05. Possible numerical de-embedding artifact.",
                        severity="WARNING"
                    )
                )

        if outputs.s11_db is not None:
            max_db = max(outputs.s11_db)
            if max_db > 20.0 * math.log10(1.0 + self.passivity_tolerance):
                issues.append(
                    ValidationIssue(
                        "POSITIVE_S11_DB",
                        f"Positive S11 in dB: peak S11 = {max_db:.2f} dB exceeds passivity limit.",
                        severity="ERROR"
                    )
                )

        # 2. Complex S11 consistency check
        if outputs.has_complex_s11 and outputs.s11_real and outputs.s11_imag and outputs.s11_magnitude:
            # Verify magnitude matches hypot(re, im)
            diffs = [
                abs(math.hypot(re, im) - mag)
                for re, im, mag in zip(outputs.s11_real, outputs.s11_imag, outputs.s11_magnitude)
            ]
            if max(diffs) > 1e-3:
                issues.append(
                    ValidationIssue(
                        "COMPLEX_MAGNITUDE_INCONSISTENCY",
                        f"Inconsistent complex S11: max deviation between sqrt(re^2+im^2) and s11_mag is {max(diffs):.4e}",
                        severity="ERROR"
                    )
                )

        # 3. Input impedance consistency
        if outputs.zin_real is not None:
            min_rin = min(outputs.zin_real)
            if min_rin < -0.1:
                issues.append(
                    ValidationIssue(
                        "NEGATIVE_INPUT_RESISTANCE",
                        f"Negative real input resistance Rin = {min_rin:.2f} Ohm. Passive antennas must have Rin >= 0.",
                        severity="ERROR"
                    )
                )

        # 4. VSWR check
        if outputs.vswr is not None:
            min_vswr = min(outputs.vswr)
            if min_vswr < 0.999:
                issues.append(
                    ValidationIssue(
                        "INVALID_VSWR",
                        f"VSWR cannot be less than 1.0, got minimum {min_vswr:.4f}",
                        severity="ERROR"
                    )
                )

        # 5. Efficiency ranges
        if outputs.radiation_efficiency is not None:
            for eff in outputs.radiation_efficiency:
                if eff < 0.0 or eff > 1.05:
                    issues.append(
                        ValidationIssue(
                            "INVALID_RADIATION_EFFICIENCY",
                            f"Radiation efficiency must be within [0.0, 1.0], got {eff}",
                            severity="ERROR" if eff > 1.10 else "WARNING"
                        )
                    )
                    break

        if outputs.total_efficiency is not None:
            for eff in outputs.total_efficiency:
                if eff < 0.0 or eff > 1.05:
                    issues.append(
                        ValidationIssue(
                            "INVALID_TOTAL_EFFICIENCY",
                            f"Total efficiency must be within [0.0, 1.0], got {eff}",
                            severity="ERROR" if eff > 1.10 else "WARNING"
                        )
                    )
                    break

        # 6. Gain sanity checks
        if outputs.gain_dbi is not None:
            max_gain = max(outputs.gain_dbi)
            min_gain = min(outputs.gain_dbi)
            if max_gain > 30.0:
                issues.append(
                    ValidationIssue(
                        "UNUSUALLY_HIGH_GAIN",
                        f"Peak gain of {max_gain:.2f} dBi is unusually high for a single-element patch antenna.",
                        severity="WARNING"
                    )
                )
            if min_gain < -100.0:
                issues.append(
                    ValidationIssue(
                        "EXTREME_NEGATIVE_GAIN",
                        f"Minimum gain of {min_gain:.2f} dBi may indicate non-radiating or unmeshed state.",
                        severity="WARNING"
                    )
                )

        # 7. Solver convergence status
        sim_meta = record.simulation_metadata
        if sim_meta.is_converged is False:
            issues.append(
                ValidationIssue(
                    "UNCONVERGED_SIMULATION",
                    "Electromagnetic solver reported simulation did not reach convergence criterion.",
                    severity="WARNING"
                )
            )

        return issues
