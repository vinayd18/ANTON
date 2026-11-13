# -*- coding: utf-8 -*-
"""Rectangle → Shapely converter."""

from __future__ import annotations

import math

import shapely.affinity as affinity
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def rectangle_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely :class:`Polygon` from a rectangle *obj*.

    Uses *width*, *height*, *center_x*, *center_y*, and *rotation_deg*.
    """
    w = obj.width or 0.0
    h = obj.height or 0.0
    hw, hh = w / 2.0, h / 2.0
    cx, cy = obj.center_x, obj.center_y
    corners = [
        (cx - hw, cy - hh),
        (cx + hw, cy - hh),
        (cx + hw, cy + hh),
        (cx - hw, cy + hh),
    ]
    poly = geom.Polygon(corners)
    if obj.rotation_deg:
        poly = affinity.rotate(poly, obj.rotation_deg, origin=(cx, cy), use_radians=False)
    return poly

