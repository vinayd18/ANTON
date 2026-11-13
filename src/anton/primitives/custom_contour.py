# -*- coding: utf-8 -*-
"""Custom contour → Shapely converter."""

from __future__ import annotations

import shapely.geometry as geom
import shapely.affinity as affinity

from anton.models.geometry_schema import GeometryObject


def custom_contour_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely Polygon from custom closed contour defined in *obj*.

    Uses *vertices* as the outer boundary and *inner_vertices* as an optional
    interior cut-out (hole).
    """
    if not obj.vertices or len(obj.vertices) < 3:
        raise ValueError(
            f"Custom contour '{obj.id}' requires at least 3 vertices, got {len(obj.vertices) if obj.vertices else 0}"
        )

    exterior = [(v.x, v.y) for v in obj.vertices]
    holes = []
    if obj.inner_vertices and len(obj.inner_vertices) >= 3:
        holes.append([(v.x, v.y) for v in obj.inner_vertices])

    poly = geom.Polygon(exterior, holes)
    if not poly.is_valid:
        # Attempt minimal buffer fix or raise clear error
        poly = poly.buffer(0)
        if not poly.is_valid or poly.is_empty:
            raise ValueError(f"Custom contour '{obj.id}' produced an invalid polygon geometry.")

    if obj.rotation_deg:
        cx = obj.center_x if obj.center_x != 0.0 else poly.centroid.x
        cy = obj.center_y if obj.center_y != 0.0 else poly.centroid.y
        poly = affinity.rotate(poly, obj.rotation_deg, origin=(cx, cy), use_radians=False)

    return poly
