# -*- coding: utf-8 -*-
"""Geometry validation engine orchestrator for ANTON."""

from __future__ import annotations

from typing import List, Optional

from anton.feeds.feed_geometry import FeedDef
from anton.models.geometry_schema import GeometryProject
from anton.validation.geometry_checks import (
    check_feed_connectivity,
    check_invalid_dimensions,
    check_layer_stack_vertical_overlap,
    check_missing_layer_refs,
    check_missing_material_refs,
    check_overlapping_conductors,
    check_required_layers,
    check_self_intersection,
    check_zero_area,
)
from anton.validation.validation_report import ValidationReport


class GeometryValidator:
    """Validates an antenna geometry project against geometrical and physical structural rules."""

    def __init__(self) -> None:
        pass

    def validate(
        self,
        project: GeometryProject,
        feeds: Optional[List[FeedDef]] = None,
        require_full_stack: bool = False,
    ) -> ValidationReport:
        """Execute all validation checks on a GeometryProject.

        Parameters
        ----------
        project:
            The canonical GeometryProject to validate.
        feeds:
            Optional list of FeedDef structures to check connectivity against.
        require_full_stack:
            If True, verifies presence of patch, substrate, and ground layers.

        Returns
        -------
        ValidationReport:
            Report detailing all detected errors and warnings.
        """
        report = ValidationReport()

        # Dimension checks
        report.issues.extend(check_invalid_dimensions(project.objects))

        # Degenerate area checks
        report.issues.extend(check_zero_area(project.objects))

        # Topology and self-intersection checks
        report.issues.extend(check_self_intersection(project.objects))

        # Layer and material reference checks
        report.issues.extend(check_missing_layer_refs(project.objects, project.layers))
        report.issues.extend(check_missing_material_refs(project.objects, project.materials))

        # Overlapping conductors
        report.issues.extend(check_overlapping_conductors(project.objects, project.layers))

        # Vertical layer stack overlap
        report.issues.extend(check_layer_stack_vertical_overlap(project.layers))

        # Feed connectivity
        if feeds:
            report.issues.extend(check_feed_connectivity(feeds, project.objects))

        # Structural stack checks
        if require_full_stack:
            report.issues.extend(check_required_layers(project.layers))

        return report

