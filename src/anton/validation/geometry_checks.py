# -*- coding: utf-8 -*-
"""Individual geometric and antenna-structural validation checks for ANTON."""

from __future__ import annotations

from typing import Dict, List, Optional

import shapely.geometry as geom

from anton.feeds.feed_geometry import FeedDef, FeedManager
from anton.models.geometry_schema import (
    GeometryObject,
    LayerDef,
    MaterialRef,
)
from anton.primitives.base import to_shapely
from anton.validation.validation_report import ValidationIssue, ValidationSeverity


def check_invalid_dimensions(objects: Dict[str, GeometryObject]) -> List[ValidationIssue]:
    """Check for negative or non-physical dimensions in geometry primitives."""
    issues = []
    for obj_id, obj in objects.items():
        if obj.object_type in {"rectangle", "square"}:
            if obj.width is not None and obj.width <= 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_NONPOSITIVE_WIDTH",
                        description=f"Object '{obj.name or obj_id}' has non-positive width: {obj.width} m.",
                        object_id=obj_id,
                        suggestion="Specify a strictly positive width (> 0.0).",
                    )
                )
            if obj.height is not None and obj.height <= 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_NONPOSITIVE_HEIGHT",
                        description=f"Object '{obj.name or obj_id}' has non-positive height: {obj.height} m.",
                        object_id=obj_id,
                        suggestion="Specify a strictly positive height (> 0.0).",
                    )
                )
        elif obj.object_type in {"circle", "arc"}:
            if obj.radius is not None and obj.radius <= 0:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_NONPOSITIVE_RADIUS",
                        description=f"Object '{obj.name or obj_id}' has non-positive radius: {obj.radius} m.",
                        object_id=obj_id,
                        suggestion="Specify a strictly positive radius (> 0.0).",
                    )
                )
        elif obj.object_type == "ellipse":
            if (obj.semi_major is not None and obj.semi_major <= 0) or (
                obj.semi_minor is not None and obj.semi_minor <= 0
            ):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_NONPOSITIVE_SEMI_AXES",
                        description=f"Object '{obj.name or obj_id}' has non-positive semi-axes.",
                        object_id=obj_id,
                        suggestion="Both semi_major and semi_minor must be strictly positive.",
                    )
                )
    return issues


def check_zero_area(objects: Dict[str, GeometryObject]) -> List[ValidationIssue]:
    """Check for degenerate 2D primitives that yield zero or negligible area."""
    issues = []
    for obj_id, obj in objects.items():
        if obj.object_type in {"line", "arc"}:
            continue  # 1D line primitives legitimately have zero 2D area
        try:
            shape = to_shapely(obj)
            if shape.is_empty or shape.area < 1e-18:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_ZERO_AREA",
                        description=f"Object '{obj.name or obj_id}' has zero or degenerate 2D area ({shape.area} m²).",
                        object_id=obj_id,
                        suggestion="Verify object coordinates and dimensions.",
                    )
                )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="ERR_SHAPE_CONVERSION",
                    description=f"Failed to evaluate geometry for '{obj.name or obj_id}': {str(e)}",
                    object_id=obj_id,
                    suggestion="Ensure vertices and primitive properties are valid.",
                )
            )
    return issues


def check_self_intersection(objects: Dict[str, GeometryObject]) -> List[ValidationIssue]:
    """Check for self-intersecting or topologically invalid 2D contours."""
    issues = []
    for obj_id, obj in objects.items():
        try:
            shape = to_shapely(obj)
            if not shape.is_valid:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="ERR_SELF_INTERSECTING_GEOMETRY",
                        description=f"Object '{obj.name or obj_id}' is topologically invalid or self-intersecting.",
                        object_id=obj_id,
                        suggestion="Reorder vertices or eliminate self-intersections in contour.",
                    )
                )
        except Exception as e:
            # Already flagged or non-convertible
            pass
    return issues


def check_missing_layer_refs(
    objects: Dict[str, GeometryObject], layers: Dict[str, LayerDef]
) -> List[ValidationIssue]:
    """Verify that every object references an existing layer in the project."""
    issues = []
    for obj_id, obj in objects.items():
        if obj.layer_id not in layers:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="ERR_MISSING_LAYER_REF",
                    description=f"Object '{obj.name or obj_id}' references non-existent layer ID '{obj.layer_id}'.",
                    object_id=obj_id,
                    suggestion="Assign object to a registered layer ID.",
                )
            )
    return issues


def check_missing_material_refs(
    objects: Dict[str, GeometryObject], materials: Dict[str, MaterialRef]
) -> List[ValidationIssue]:
    """Verify that every object references an existing material."""
    issues = []
    for obj_id, obj in objects.items():
        if obj.material_id not in materials:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="ERR_MISSING_MATERIAL_REF",
                    description=f"Object '{obj.name or obj_id}' references non-existent material ID '{obj.material_id}'.",
                    object_id=obj_id,
                    suggestion="Assign object to a registered material.",
                )
            )
    return issues


def check_feed_connectivity(
    feeds: List[FeedDef], objects: Dict[str, GeometryObject]
) -> List[ValidationIssue]:
    """Verify that feeds physically connect to their designated target radiating patch."""
    issues = []
    feed_mgr = FeedManager()
    for feed in feeds:
        if not feed.target_object_id:
            continue
        connected = feed_mgr.check_connectivity(feed, objects)
        if not connected:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="WARN_FEED_DISCONNECTED",
                    description=(
                        f"Feed '{feed.name}' (object '{feed.geometry_object_id}') does not "
                        f"physically touch target object '{feed.target_object_id}'."
                    ),
                    object_id=feed.geometry_object_id,
                    suggestion="Adjust feed line length or position to touch the patch boundary.",
                )
            )
    return issues


def check_overlapping_conductors(
    objects: Dict[str, GeometryObject], layers: Dict[str, LayerDef]
) -> List[ValidationIssue]:
    """Detect overlapping conductive elements on the same physical layer.

    Issued as a WARNING rather than an ERROR, because parasitic patches or intentional
    coupled elements may touch or overlap.
    """
    issues = []
    layer_to_objs: Dict[str, List[GeometryObject]] = {}
    for obj in objects.values():
        layer = layers.get(obj.layer_id)
        if layer and layer.layer_type in {"patch", "feed", "conductor"}:
            layer_to_objs.setdefault(obj.layer_id, []).append(obj)

    for layer_id, obj_list in layer_to_objs.items():
        n = len(obj_list)
        for i in range(n):
            for j in range(i + 1, n):
                o1, o2 = obj_list[i], obj_list[j]
                try:
                    s1 = to_shapely(o1)
                    s2 = to_shapely(o2)
                    if s1.intersects(s2) and not s1.touches(s2):
                        overlap_area = s1.intersection(s2).area
                        if overlap_area > 1e-12:
                            issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    code="WARN_OVERLAPPING_CONDUCTORS",
                                    description=(
                                        f"Conductive objects '{o1.name or o1.id}' and '{o2.name or o2.id}' "
                                        f"overlap on layer '{layers[layer_id].name}' (overlap area: {overlap_area:.4e} m²)."
                                    ),
                                    object_id=o1.id,
                                    suggestion="Check if union is intended or if objects should be spaced.",
                                )
                            )
                except Exception:
                    pass
    return issues


def check_required_layers(layers: Dict[str, LayerDef]) -> List[ValidationIssue]:
    """Check whether a full physical antenna stack is present when requested."""
    issues = []
    layer_types = {layer.layer_type for layer in layers.values()}
    for req in ["patch", "substrate", "ground"]:
        if req not in layer_types:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="WARN_INCOMPLETE_STACK",
                    description=f"Antenna stack is missing standard '{req}' layer.",
                    suggestion=f"Add a layer of type '{req}' for full microstrip stack simulation.",
                )
            )
    return issues
