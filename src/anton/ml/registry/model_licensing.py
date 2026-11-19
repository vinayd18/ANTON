# -*- coding: utf-8 -*-
"""Licensing and patent assessment engine for machine learning models in ANTON.

Conducts rigorous compliance audits for open-source licenses, patent grants,
commercial usability restrictions, and derivative-work obligations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from anton.ml.registry.model_metadata import ModelMetadata


@dataclass
class LicenseAssessmentResult:
    """Comprehensive legal and compliance audit result for a candidate model."""

    model_id: str
    license_name: str
    commercial_allowed: bool
    modification_allowed: bool
    distribution_allowed: bool
    patent_grant_included: bool
    patent_warnings: List[str] = field(default_factory=list)
    attribution_required: bool = True
    copyleft_enforced: bool = False
    usage_restrictions: List[str] = field(default_factory=list)
    compliance_guidelines: List[str] = field(default_factory=list)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    def summary(self) -> str:
        lines = [
            f"License Audit for '{self.model_id}': {self.license_name} [Risk: {self.risk_level}]",
            f"  Commercial Use Allowed: {'YES' if self.commercial_allowed else 'NO'}",
            f"  Patent Grant Included: {'YES' if self.patent_grant_included else 'NO'}",
            f"  Attribution Required: {'YES' if self.attribution_required else 'NO'}",
        ]
        if self.patent_warnings:
            lines.append("  Patent Warnings:")
            for pw in self.patent_warnings:
                lines.append(f"    - [!] {pw}")
        if self.usage_restrictions:
            lines.append("  Usage Restrictions:")
            for ur in self.usage_restrictions:
                lines.append(f"    - {ur}")
        return "\n".join(lines)


class ModelLicensingAuditor:
    """Audits models and repositories against open-source licenses and patent disclosures."""

    KNOWN_PATENTS: Dict[str, Dict[str, str]] = {
        "udaykdk/pixelant": {
            "patent_number": "Indian Patent No. 572928",
            "title": "Method Of Designing Ultra Compact Single Band Antennas",
            "inventors": "Uday Khankhoje and Aggraj Gupta (IIT Madras)",
            "filing_date": "2024-01-22",
            "grant_date": "2025-10-30",
            "restriction": "Source code is MIT (No Patent Grant). Commercial deployment or integration into commercial design software requires a separate patent license from IIT Madras.",
        }
    }

    @classmethod
    def audit(cls, model: ModelMetadata) -> LicenseAssessmentResult:
        """Alias for audit_model."""
        return cls.audit_model(model)

    @classmethod
    def audit_model(cls, model: ModelMetadata) -> LicenseAssessmentResult:
        """Conducts a comprehensive compliance and patent audit for a given model entry."""
        lic = (model.license or "Unspecified").strip()
        lic_lower = lic.lower()
        repo = model.repository_url.lower()

        commercial_allowed = True
        modification_allowed = True
        distribution_allowed = True
        patent_grant_included = True
        attribution_required = True
        copyleft_enforced = False
        patent_warnings: List[str] = []
        usage_restrictions: List[str] = []
        compliance_guidelines: List[str] = []
        risk_level = "LOW"

        # Check for known registered patents
        for repo_key, pat_info in cls.KNOWN_PATENTS.items():
            if repo_key in repo or repo_key in model.model_id:
                patent_grant_included = False
                p_desc = f"{pat_info['patent_number']}: '{pat_info['title']}' ({pat_info['inventors']}). {pat_info['restriction']}"
                patent_warnings.append(p_desc)
                usage_restrictions.append(f"Patent Restricted: {pat_info['patent_number']}")
                risk_level = "CRITICAL"

        # Add declared model patent restrictions if present
        if model.patent_restrictions:
            for pr in model.patent_restrictions:
                if pr not in patent_warnings:
                    patent_warnings.append(pr)
            patent_grant_included = False
            risk_level = "CRITICAL" if risk_level != "CRITICAL" else risk_level

        # Analyze license text and standard types
        if "no patent grant" in lic_lower or "no-patent" in lic_lower:
            patent_grant_included = False
            patent_warnings.append("License contains explicit 'No Patent Grant' clause. Commercial use may infringe ungranted patents.")
            risk_level = "HIGH" if risk_level != "CRITICAL" else "CRITICAL"

        if "mit" in lic_lower and "no patent" not in lic_lower:
            compliance_guidelines.append("Include original copyright notice and permission notice in all copies or substantial portions.")
        elif "apache" in lic_lower:
            patent_grant_included = True
            compliance_guidelines.append("Include original copyright notice, copy of Apache 2.0 license, and state changes made.")
        elif "gpl" in lic_lower:
            copyleft_enforced = True
            usage_restrictions.append("Strong copyleft: Any derivative work or combined distribution must be licensed under GPL-3.0.")
            risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level
            compliance_guidelines.append("Do not link proprietary or closed-source ANTON modules statically against GPL code.")
        elif "academic" in lic_lower or "non-commercial" in lic_lower or "research" in lic_lower:
            commercial_allowed = False
            usage_restrictions.append("Strictly non-commercial / academic use only. Commercial utilization prohibited.")
            risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level
        elif "unspecified" in lic_lower or "none" in lic_lower:
            commercial_allowed = False
            distribution_allowed = False
            usage_restrictions.append("No license declared by repository author. All rights reserved under standard copyright.")
            risk_level = "HIGH" if risk_level != "CRITICAL" else risk_level
            compliance_guidelines.append("Contact author to request explicit open-source license grant before redistributing weights.")

        # Check weights vs code license disparity
        if model.checkpoint_available and model.model_category == model.model_category.CATEGORY_A:
            compliance_guidelines.append("Verify whether model weights inherit source license or carry independent terms of use.")

        return LicenseAssessmentResult(
            model_id=model.model_id,
            license_name=lic,
            commercial_allowed=commercial_allowed,
            modification_allowed=modification_allowed,
            distribution_allowed=distribution_allowed,
            patent_grant_included=patent_grant_included,
            patent_warnings=patent_warnings,
            attribution_required=attribution_required,
            copyleft_enforced=copyleft_enforced,
            usage_restrictions=usage_restrictions,
            compliance_guidelines=compliance_guidelines,
            risk_level=risk_level,
        )
