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


def test_circle_minus_rectangle_slot():
    import math
    circle = GeometryObject(object_type="circle", layer_id="L1", material_id="M1", radius=0.02)
    slot = GeometryObject(object_type="rectangle", layer_id="L1", material_id="M1", width=0.01, height=0.004)

    diff = boolean_difference(circle, [slot])
    shape = to_shapely(diff)

    expected_area = math.pi * (0.02 ** 2) - (0.01 * 0.004)
    assert pytest.approx(shape.area, rel=1e-3) == expected_area
    assert len(shape.interiors) == 1


def test_annular_ring_circle_minus_circle():
    import math
    outer = GeometryObject(object_type="circle", layer_id="L1", material_id="M1", radius=0.018)
    inner = GeometryObject(object_type="circle", layer_id="L1", material_id="M1", radius=0.009)

    ring = boolean_difference(outer, [inner])
    shape = to_shapely(ring)

    expected_area = math.pi * ((0.018 ** 2) - (0.009 ** 2))
    assert pytest.approx(shape.area, rel=1e-3) == expected_area
    assert len(shape.interiors) == 1


def test_hole_preservation_in_cad_solid_volume():
    """Verify that holes/cutouts are preserved in 3D CAD extrusion with correct volume."""
    import math
    import cadquery as cq
    from anton.cad.solid_generator import SolidGenerator
    from anton.core.geometry_engine import AntonEngine

    e = AntonEngine("Hole CAD Test")
    m = e.add_material("Copper", "conductor")
    l = e.add_layer("Patch", "patch", m, z_position=0.0016, thickness=35e-6)

    # 40mm x 30mm patch with 10mm x 5mm cutout
    patch = GeometryObject(object_type="rectangle", layer_id=l, material_id=m, width=0.04, height=0.03)
    slot = GeometryObject(object_type="rectangle", layer_id=l, material_id=m, width=0.01, height=0.005)
    slotted_patch = boolean_difference(patch, [slot], layer_id=l, material_id=m)

    gen = SolidGenerator(e.project)
    solid = gen.generate_solid(slotted_patch, thickness=35e-6)

    cad_volume = solid.val().Volume()
    expected_area = (0.04 * 0.03) - (0.01 * 0.005)
    expected_volume = expected_area * 35e-6

    assert pytest.approx(cad_volume, rel=1e-4) == expected_volume


