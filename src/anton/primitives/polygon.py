# -*- coding: utf-8 -*-
"""Polygon → Shapely converter."""

from __future__ import annotations

import shapely.affinity as affinity
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def polygon_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely polygon from *obj.vertices*.

    If *inner_holes* (or *inner_vertices*) are present, they define interior holes.
    """
    if not obj.vertices:
        raise ValueError(f"Object '{obj.id}' has no vertices for polygon conversion")
    exterior = [(v.x, v.y) for v in obj.vertices]
    holes = []
    if obj.inner_holes:
        for hole in obj.inner_holes:
            if len(hole) >= 3:
                holes.append([(v.x, v.y) for v in hole])
    elif obj.inner_vertices:
        holes.append([(v.x, v.y) for v in obj.inner_vertices])
    poly = geom.Polygon(exterior, holes)
    if obj.rotation_deg:
        centroid = poly.centroid
        poly = affinity.rotate(poly, obj.rotation_deg, origin=(centroid.x, centroid.y), use_radians=False)
    return poly

