"""
Data-Quality Classifier for Electromagnetic Records.

Classifies dataset records into:
- VERIFIED: Converged full-wave simulation or authentic measurement, passed all physical/structural checks.
- ACCEPTED_WITH_WARNINGS: Minor non-fatal anomalies (e.g. slight high-frequency edge de-embedding violation, unconverged warning).
- INCOMPLETE: Missing critical outputs (e.g. empty S11 array, incomplete frequency sweep).
- REJECTED: Fatal physical or numerical violations (NaN/Inf, non-passive |S11| > 1.05, negative efficiency).
- UNVERIFIED: Initial uninspected state.
"""

from __future__ import annotations

from typing import List, Tuple
from anton.datasets.schema import DatasetRecord, QualityStatus
from anton.datasets.validation.validator import (
    StructuralValidator,
    ElectromagneticValidator,
    ValidationIssue,
)


class QualityClassifier:
    """
    Evaluates validation issues and assigns definitive QualityStatus.
    """

    def __init__(self, passivity_tolerance: float = 0.05):
        self.structural_validator = StructuralValidator()
        self.em_validator = ElectromagneticValidator(passivity_tolerance=passivity_tolerance)

    def evaluate_record(self, record: DatasetRecord) -> Tuple[QualityStatus, List[ValidationIssue], List[str]]:
        """
        Runs full validation suite and determines quality status.
        Returns (QualityStatus, list_of_issues, passed_checks).
        """
        issues: List[ValidationIssue] = []
        passed_checks: List[str] = []

        # Structural checks
        struct_issues = self.structural_validator.validate(record)
        issues.extend(struct_issues)
        if not struct_issues:
            passed_checks.append("STRUCTURAL_INTEGRITY")
            passed_checks.append("NON_EMPTY_ARRAYS")
            passed_checks.append("MONOTONIC_FREQUENCIES")

        # Incompleteness check
        outputs = record.outputs
        if outputs.s11_db is None and outputs.s11_magnitude is None and outputs.s11_real is None:
            issues.append(ValidationIssue("MISSING_S11_DATA", "Record contains no S11 data.", severity="ERROR"))

        # EM checks
        em_issues = self.em_validator.validate(record)
        issues.extend(em_issues)

        # Check specific passed EM checks
        if not any(iss.code in ("NON_PASSIVE_S11", "POSITIVE_S11_DB") for iss in em_issues):
            passed_checks.append("PASSIVITY_CHECK")
        if not any(iss.code == "INVALID_VSWR" for iss in em_issues):
            passed_checks.append("VSWR_PHYSICAL_LIMITS")
        if not any(iss.code == "COMPLEX_MAGNITUDE_INCONSISTENCY" for iss in em_issues) and outputs.has_complex_s11:
            passed_checks.append("COMPLEX_S11_CONSISTENCY")
        if not any("EFFICIENCY" in iss.code for iss in em_issues) and outputs.radiation_efficiency is not None:
            passed_checks.append("EFFICIENCY_BOUNDS")

        # Determine final status
        has_errors = any(iss.severity == "ERROR" for iss in issues)
        has_warnings = any(iss.severity == "WARNING" for iss in issues)

        if any(iss.code in ("EMPTY_FREQUENCIES", "MISSING_S11_DATA", "EMPTY_GEOMETRY") for iss in issues):
            status = QualityStatus.INCOMPLETE
        elif has_errors:
            status = QualityStatus.REJECTED
        elif has_warnings:
            status = QualityStatus.ACCEPTED_WITH_WARNINGS
        else:
            status = QualityStatus.VERIFIED

        return status, issues, passed_checks

