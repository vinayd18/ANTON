# -*- coding: utf-8 -*-
"""Ellipse → Shapely converter."""

from __future__ import annotations

import math

import shapely.affinity as affinity
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject


def ellipse_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a Shapely ellipse polygon from *obj*.

    Creates a unit circle, scales by *semi_major* (x) and *semi_minor* (y),
    then rotates and translates to *center_x*, *center_y*.
    """
    a = obj.semi_major or 0.0
    b = obj.semi_minor or 0.0
    # Start with a unit circle at origin
    circle = geom.Point(0, 0).buffer(1.0, quad_segs=128)
    # Scale to ellipse dimensions
    ellipse = affinity.scale(circle, xfact=a, yfact=b, origin=(0, 0))
    # Rotate
    if obj.rotation_deg:
        ellipse = affinity.rotate(ellipse, obj.rotation_deg, origin=(0, 0), use_radians=False)
    # Translate to center
    ellipse = affinity.translate(ellipse, xoff=obj.center_x, yoff=obj.center_y)
    return ellipse

