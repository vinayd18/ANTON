# -*- coding: utf-8 -*-
"""Geometric operations module for ANTON."""

from anton.operations.boolean import (
    boolean_difference,
    boolean_intersection,
    boolean_union,
)
from anton.operations.offsets import offset_object
from anton.operations.transformations import (
    duplicate_object,
    extract_boundary,
    mirror_object,
    rotate_object,
    scale_object,
    translate_object,
)

__all__ = [
    "boolean_union",
    "boolean_difference",
    "boolean_intersection",
    "translate_object",
    "rotate_object",
    "scale_object",
    "mirror_object",
    "duplicate_object",
    "extract_boundary",
    "offset_object",
]
