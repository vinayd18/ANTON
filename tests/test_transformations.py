# -*- coding: utf-8 -*-
"""Unit tests for geometric transformation functions."""

import pytest

from anton.models.geometry_schema import GeometryObject
from anton.operations.offsets import offset_object
from anton.operations.transformations import (
    duplicate_object,
    extract_boundary,
    mirror_object,
    rotate_object,
    scale_object,
    translate_object,
)
from anton.primitives.base import to_shapely


def test_translate_object():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.04,
        height=0.03,
        center_x=0.0,
        center_y=0.0,
    )
    shifted = translate_object(obj, dx=0.015, dy=-0.02)
    assert shifted.id != obj.id
    assert pytest.approx(shifted.center_x, rel=1e-5) == 0.015
    assert pytest.approx(shifted.center_y, rel=1e-5) == -0.02


def test_rotate_object():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.04,
        height=0.02,
    )
    rot = rotate_object(obj, angle_deg=90.0)
    shape = to_shapely(rot)
    # Area must be preserved
    assert pytest.approx(shape.area, rel=1e-5) == 0.04 * 0.02


def test_scale_object():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.02,
        height=0.03,
    )
    scaled = scale_object(obj, factor_x=2.0, factor_y=3.0)
    shape = to_shapely(scaled)
    expected_area = (0.02 * 2.0) * (0.03 * 3.0)
    assert pytest.approx(shape.area, rel=1e-5) == expected_area


def test_mirror_object():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.02,
        height=0.01,
        center_x=0.03,
        center_y=0.0,
    )
    # Mirror across x-axis at offset x=0 -> new centroid at x=-0.03
    mirrored = mirror_object(obj, axis="x", offset=0.0)
    shape = to_shapely(mirrored)
    assert pytest.approx(shape.centroid.x, rel=1e-5) == -0.03
    assert pytest.approx(shape.area, rel=1e-5) == 0.02 * 0.01


def test_duplicate_object():
    obj = GeometryObject(
        object_type="circle",
        layer_id="L1",
        material_id="M1",
        radius=0.015,
        name="OriginalCircle",
    )
    dup = duplicate_object(obj)
    assert dup.id != obj.id
    assert dup.radius == obj.radius
    assert "OriginalCircle" in dup.name


def test_extract_boundary():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.04,
        height=0.02,
    )
    boundary = extract_boundary(obj)
    assert boundary.object_type == "line"
    assert len(boundary.vertices) >= 4


def test_offset_object():
    obj = GeometryObject(
        object_type="circle",
        layer_id="L1",
        material_id="M1",
        radius=0.01,
    )
    # Inflate by 2mm
    inflated = offset_object(obj, distance=0.002)
    shape = to_shapely(inflated)
    # New radius should be 12mm
    expected_area = 3.14159 * (0.012 ** 2)
    assert pytest.approx(shape.area, rel=1e-2) == expected_area
