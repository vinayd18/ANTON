"""
Validation Report Generator.

Creates machine-readable JSON dicts and human-readable Markdown reports
for dataset records and validation audits.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List
from anton.datasets.schema import DatasetRecord, QualityStatus
from anton.datasets.validation.quality_classifier import QualityClassifier
from anton.datasets.validation.validator import ValidationIssue


class ValidationReportGenerator:
    """
    Generates detailed validation reports for single records or entire datasets.
    """

    def __init__(self, classifier: Optional[QualityClassifier] = None):
        self.classifier = classifier or QualityClassifier()

    def generate_record_report(self, record: DatasetRecord) -> Dict[str, Any]:
        """
        Runs validation and generates comprehensive machine-readable report dict.
        """
        status, issues, passed_checks = self.classifier.evaluate_record(record)

        # Categorize issues
        failed_checks = [iss.to_dict() for iss in issues if iss.severity == "ERROR"]
        warnings = [iss.to_dict() for iss in issues if iss.severity == "WARNING"]

        # Recommendations
        recommendations = []
        for iss in issues:
            if iss.code == "NON_PASSIVE_S11":
                recommendations.append("Check solver port de-embedding or excitation definition.")
            elif iss.code == "UNCONVERGED_SIMULATION":
                recommendations.append("Increase maximum adaptive passes in HFSS/CST mesh setup.")
            elif iss.code == "EMPTY_FREQUENCIES":
                recommendations.append("Re-export frequency sweep results from solver.")
            elif iss.code == "MISSING_S11_DATA":
                recommendations.append("Ensure S11 report was exported in CSV/Touchstone format.")

        report = {
            "record_id": record.antenna_identity.dataset_record_id,
            "design_id": record.antenna_identity.design_id,
            "geometry_family": record.antenna_identity.geometry_family,
            "quality_status": status.value,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "validation_rules_applied": [
                "STRUCTURAL_INTEGRITY",
                "FREQUENCY_MONOTONICITY",
                "PASSIVITY_LIMITS",
                "VSWR_LIMITS",
                "COMPLEX_S11_CONSISTENCY",
                "EFFICIENCY_BOUNDS",
                "CONVERGENCE_STATUS",
            ],
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "warnings": warnings,
            "missing_outputs": record.outputs.missing_outputs,
            "recommended_corrections": recommendations,
        }

        # Update record in place
        record.quality_status = status
        record.quality_report = report
        return report

    def format_markdown_report(self, report: Dict[str, Any]) -> str:
        """
        Formats report dict into readable Markdown.
        """
        status = report.get("quality_status", "UNKNOWN")
        icon = "✅" if status == "VERIFIED" else ("⚠️" if status == "ACCEPTED_WITH_WARNINGS" else "❌")

        md = [
            f"# Validation Report: `{report.get('record_id')}`",
            f"**Status**: {icon} `{status}`  ",
            f"**Design ID**: `{report.get('design_id')}` | **Family**: `{report.get('geometry_family')}`  ",
            f"**Timestamp**: {report.get('timestamp')}  \n",
            "## Passed Checks",
        ]

        passed = report.get("passed_checks", [])
        if passed:
            for p in passed:
                md.append(f"- [x] `{p}`")
        else:
            md.append("- *No checks passed completely.*")

        md.append("\n## Failed Checks")
        failed = report.get("failed_checks", [])
        if failed:
            for f in failed:
                md.append(f"- ❌ **{f['code']}**: {f['message']}")
        else:
            md.append("- *None (all core sanity tests passed).*")

        md.append("\n## Warnings")
        warnings = report.get("warnings", [])
        if warnings:
            for w in warnings:
                md.append(f"- ⚠️ **{w['code']}**: {w['message']}")
        else:
            md.append("- *No warnings.*")

        md.append("\n## Missing Quantities")
        missing = report.get("missing_outputs", [])
        if missing:
            for m in missing:
                md.append(f"- `[{m}]`")
        else:
            md.append("- *Full output package available.*")

        recs = report.get("recommended_corrections", [])
        if recs:
            md.append("\n## Recommended Corrections")
            for r in recs:
                md.append(f"1. {r}")

        return "\n".join(md)

