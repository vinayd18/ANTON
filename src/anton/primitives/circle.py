# -*- coding: utf-8 -*-
"""Circle → Shapely converter."""

from __future__ import annotations

import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def circle_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely circle polygon from *obj*.

    Uses ``Point(cx, cy).buffer(radius, resolution=128)`` to produce a
    polygon approximation with 128 segments per quarter.
    """
    r = obj.radius or 0.0
    return geom.Point(obj.center_x, obj.center_y).buffer(r, quad_segs=128)

