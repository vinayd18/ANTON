# -*- coding: utf-8 -*-
"""Geometry offset (dilation/deflation) operations for ANTON."""

from __future__ import annotations

from typing import Optional

from anton.models.geometry_schema import GeometryObject
from anton.operations.boolean import _shape_to_geometry_object
from anton.primitives.base import to_shapely


def offset_object(
    obj: GeometryObject,
    distance: float,
    name: Optional[str] = None,
) -> GeometryObject:
    """Offset (inflate or deflate) a 2D geometry object by a signed distance in metres.

    Positive distance: dilation (expansion).
    Negative distance: erosion (shrinkage).
    """
    shape = to_shapely(obj)
    offset_shape = shape.buffer(distance)

    if offset_shape.is_empty:
        raise ValueError(
            f"Offsetting object '{obj.id}' by {distance} m resulted in an empty geometry."
        )

    return _shape_to_geometry_object(
        offset_shape,
        name=name or f"{obj.name or 'obj'}_offset",
        layer_id=obj.layer_id,
        material_id=obj.material_id,
        operation_type="offset",
    )
