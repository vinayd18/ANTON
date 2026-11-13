# -*- coding: utf-8 -*-
"""Line → Shapely converter."""

from __future__ import annotations

import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def line_to_shapely(obj: GeometryObject) -> geom.LineString:
    """Build a Shapely :class:`LineString` from *obj.vertices*.

    Requires at least 2 vertices.
    """
    if not obj.vertices or len(obj.vertices) < 2:
        raise ValueError(f"Object '{obj.id}' needs ≥ 2 vertices for a line")
    pts = [(v.x, v.y) for v in obj.vertices]
    return geom.LineString(pts)

