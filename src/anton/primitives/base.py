# -*- coding: utf-8 -*-
"""Primitive → Shapely converters.

Each submodule in ``anton.primitives`` exposes a single converter function.
This module provides a unified dispatcher, :func:`to_shapely`, that routes
a :class:`~anton.models.geometry_schema.GeometryObject` to the correct
converter based on its ``object_type`` field.
"""

from __future__ import annotations

from typing import Callable

import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject
from anton.primitives.rectangle import rectangle_to_shapely
from anton.primitives.circle import circle_to_shapely
from anton.primitives.ellipse import ellipse_to_shapely
from anton.primitives.triangle import triangle_to_shapely
from anton.primitives.polygon import polygon_to_shapely
from anton.primitives.line import line_to_shapely
from anton.primitives.arc import arc_to_shapely
from anton.primitives.custom_contour import custom_contour_to_shapely

__all__ = ["to_shapely"]

_CONVERTERS: dict[str, Callable[[GeometryObject], geom.base.BaseGeometry]] = {
    "rectangle": rectangle_to_shapely,
    "circle": circle_to_shapely,
    "ellipse": ellipse_to_shapely,
    "triangle": triangle_to_shapely,
    "polygon": polygon_to_shapely,
    "line": line_to_shapely,
    "arc": arc_to_shapely,
    "custom_contour": custom_contour_to_shapely,
    "boolean_result": polygon_to_shapely,  # stored as vertex list
}


def to_shapely(obj: GeometryObject) -> geom.base.BaseGeometry:
    """Convert a :class:`GeometryObject` to a Shapely geometry.

    Parameters
    ----------
    obj:
        The geometry object to convert.

    Returns
    -------
    shapely.geometry.base.BaseGeometry
        The Shapely representation.

    Raises
    ------
    NotImplementedError
        If the object_type has no registered converter.
    """
    converter = _CONVERTERS.get(obj.object_type)
    if converter is None:
        raise NotImplementedError(
            f"No Shapely converter registered for object_type '{obj.object_type}'"
        )
    return converter(obj)

