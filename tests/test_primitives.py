# -*- coding: utf-8 -*-
"""Unit tests for geometry primitives and their Shapely conversions."""

import math
import pytest
import shapely.geometry as geom

from anton.core.units import Units
from anton.models.geometry_schema import GeometryObject, VertexDef
from anton.primitives.base import to_shapely


def test_rectangle_to_shapely():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.04,
        height=0.03,
        center_x=0.01,
        center_y=-0.02,
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.Polygon)
    assert pytest.approx(shape.area, rel=1e-5) == 0.04 * 0.03
    assert pytest.approx(shape.centroid.x, rel=1e-5) == 0.01
    assert pytest.approx(shape.centroid.y, rel=1e-5) == -0.02


def test_rotated_rectangle_preserves_area():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.05,
        height=0.02,
        rotation_deg=45.0,
    )
    shape = to_shapely(obj)
    assert pytest.approx(shape.area, rel=1e-5) == 0.05 * 0.02


def test_square_to_shapely():
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="L1",
        material_id="M1",
        width=0.025,
        height=0.025,
    )
    shape = to_shapely(obj)
    assert pytest.approx(shape.area, rel=1e-5) == 0.025 ** 2


def test_circle_to_shapely():
    radius = 0.015
    obj = GeometryObject(
        object_type="circle",
        layer_id="L1",
        material_id="M1",
        radius=radius,
        center_x=0.005,
        center_y=0.005,
    )
    shape = to_shapely(obj)
    expected_area = math.pi * (radius ** 2)
    assert pytest.approx(shape.area, rel=1e-3) == expected_area


def test_ellipse_to_shapely():
    a, b = 0.02, 0.01
    obj = GeometryObject(
        object_type="ellipse",
        layer_id="L1",
        material_id="M1",
        semi_major=a,
        semi_minor=b,
    )
    shape = to_shapely(obj)
    expected_area = math.pi * a * b
    assert pytest.approx(shape.area, rel=1e-3) == expected_area


def test_triangle_to_shapely():
    pts = [
        VertexDef(x=0.0, y=0.0),
        VertexDef(x=0.03, y=0.0),
        VertexDef(x=0.015, y=0.02),
    ]
    obj = GeometryObject(
        object_type="triangle",
        layer_id="L1",
        material_id="M1",
        vertices=pts,
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.Polygon)
    expected_area = 0.5 * 0.03 * 0.02
    assert pytest.approx(shape.area, rel=1e-5) == expected_area


def test_polygon_to_shapely():
    pts = [
        VertexDef(x=0.0, y=0.0),
        VertexDef(x=0.04, y=0.0),
        VertexDef(x=0.04, y=0.03),
        VertexDef(x=0.02, y=0.05),
        VertexDef(x=0.0, y=0.03),
    ]
    obj = GeometryObject(
        object_type="polygon",
        layer_id="L1",
        material_id="M1",
        vertices=pts,
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.Polygon)
    assert shape.is_valid


def test_line_to_shapely():
    pts = [VertexDef(x=0.0, y=0.0), VertexDef(x=0.05, y=0.0)]
    obj = GeometryObject(
        object_type="line",
        layer_id="L1",
        material_id="M1",
        vertices=pts,
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.LineString)
    assert pytest.approx(shape.length, rel=1e-5) == 0.05


def test_arc_to_shapely():
    obj = GeometryObject(
        object_type="arc",
        layer_id="L1",
        material_id="M1",
        radius=0.02,
        metadata={"start_angle_deg": 0.0, "end_angle_deg": 180.0},
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.LineString)
    expected_length = math.pi * 0.02
    assert pytest.approx(shape.length, rel=1e-2) == expected_length


def test_custom_contour_with_hole():
    outer = [
        VertexDef(x=-0.02, y=-0.02),
        VertexDef(x=0.02, y=-0.02),
        VertexDef(x=0.02, y=0.02),
        VertexDef(x=-0.02, y=0.02),
    ]
    hole = [
        VertexDef(x=-0.005, y=-0.005),
        VertexDef(x=0.005, y=-0.005),
        VertexDef(x=0.005, y=0.005),
        VertexDef(x=-0.005, y=0.005),
    ]
    obj = GeometryObject(
        object_type="custom_contour",
        layer_id="L1",
        material_id="M1",
        vertices=outer,
        inner_vertices=hole,
    )
    shape = to_shapely(obj)
    assert isinstance(shape, geom.Polygon)
    assert len(shape.interiors) == 1
    expected_area = (0.04 ** 2) - (0.01 ** 2)
    assert pytest.approx(shape.area, rel=1e-5) == expected_area
