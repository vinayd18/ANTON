# -*- coding: utf-8 -*-
"""Unit tests for Boolean geometry operations."""

import pytest

from anton.models.geometry_schema import GeometryObject
from anton.operations.boolean import (
    boolean_difference,
    boolean_intersection,
    boolean_union,
)
from anton.primitives.base import to_shapely


def test_boolean_union():
    # Two overlapping squares: [0, 0.02] x [0, 0.02] and [0.01, 0.03] x [0, 0.02]
    sq1 = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.02,
        height=0.02,
        center_x=0.01,
        center_y=0.01,
    )
    sq2 = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.02,
        height=0.02,
        center_x=0.02,
        center_y=0.01,
    )

    merged = boolean_union([sq1, sq2])
    shape = to_shapely(merged)

    # Union area should be 0.03 * 0.02 = 0.0006
    assert pytest.approx(shape.area, rel=1e-5) == 0.0006
    assert merged.object_type == "boolean_result"


def test_boolean_difference_creates_slot():
    # Base patch: 40mm x 30mm
    patch = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.04,
        height=0.03,
    )
    # Slot: 10mm x 5mm cut from center
    slot = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.01,
        height=0.005,
    )

    slotted = boolean_difference(patch, [slot])
    shape = to_shapely(slotted)

    expected_area = (0.04 * 0.03) - (0.01 * 0.005)
    assert pytest.approx(shape.area, rel=1e-5) == expected_area
    assert len(shape.interiors) == 1  # Contains a hole


def test_boolean_difference_complete_subtraction_raises():
    base = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.02,
        height=0.02,
    )
    cutter = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.05,
        height=0.05,
    )

    with pytest.raises(ValueError, match="empty geometry"):
        boolean_difference(base, [cutter])


def test_boolean_intersection():
    r1 = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.03,
        height=0.03,
        center_x=0.0,
        center_y=0.0,
    )
    r2 = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.03,
        height=0.03,
        center_x=0.015,
        center_y=0.0,
    )

    common = boolean_intersection([r1, r2])
    shape = to_shapely(common)

    # Overlap is 15mm x 30mm = 0.015 * 0.03 = 0.00045
    assert pytest.approx(shape.area, rel=1e-5) == 0.00045
