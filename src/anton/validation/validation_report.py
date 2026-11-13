# -*- coding: utf-8 -*-
"""Validation report models for ANTON."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity classification for geometry validation findings."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """Specific geometry or structural validation issue."""

    severity: ValidationSeverity
    code: str
    description: str
    object_id: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationReport(BaseModel):
    """Aggregate report summarizing all validation checks on an antenna project."""

    issues: List[ValidationIssue] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Returns True if there are zero fatal ERROR-level issues."""
        return not any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    @property
    def error_count(self) -> int:
        """Number of errors in the report."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Number of warnings in the report."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Number of informational notices in the report."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.INFO)

    def summary(self) -> str:
        """Human-readable summary of the validation outcome."""
        status = "PASSED" if self.is_valid else "FAILED"
        return (
            f"Validation {status}: {self.error_count} error(s), "
            f"{self.warning_count} warning(s), {self.info_count} notice(s)."
        )

