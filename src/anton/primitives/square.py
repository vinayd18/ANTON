# -*- coding: utf-8 -*-
"""Square → Shapely converter (alias for rectangle with width == height)."""

from __future__ import annotations

from anton.models.geometry_schema import GeometryObject
from anton.primitives.rectangle import rectangle_to_shapely

import shapely.geometry as geom


def square_to_shapely(obj: GeometryObject) -> geom.Polygon:
    """Build a square polygon. Uses *width* for both dimensions."""
    return rectangle_to_shapely(obj)

