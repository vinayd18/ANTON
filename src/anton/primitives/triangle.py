# -*- coding: utf-8 -*-
"""Triangle → Shapely converter."""

from __future__ import annotations

import math

import shapely.affinity as affinity
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def triangle_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely triangle polygon from *obj*.

    If *vertices* are provided (≥3), the first three are used.
    Otherwise an equilateral triangle is generated from *width*
    (side length), centred at (*center_x*, *center_y*).
    """
    if obj.vertices and len(obj.vertices) >= 3:
        pts = [(v.x, v.y) for v in obj.vertices[:3]]
    else:
        # Generate equilateral triangle
        side = obj.width or 0.0
        h = side * math.sqrt(3) / 2.0
        cx, cy = obj.center_x, obj.center_y
        pts = [
            (cx - side / 2.0, cy - h / 3.0),
            (cx + side / 2.0, cy - h / 3.0),
            (cx, cy + 2.0 * h / 3.0),
        ]
    poly = geom.Polygon(pts)
    if obj.rotation_deg:
        poly = affinity.rotate(poly, obj.rotation_deg, origin=(obj.center_x, obj.center_y), use_radians=False)
    return poly

