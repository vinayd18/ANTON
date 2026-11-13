# -*- coding: utf-8 -*-
"""Geometric transformations for ANTON.

Provides translation, rotation, scaling, mirroring, duplication, and boundary extraction
for planar geometry objects.
"""

from __future__ import annotations

import copy
from typing import Optional, Tuple
from uuid import uuid4

import shapely.affinity as affinity
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject, VertexDef
from anton.operations.boolean import _shape_to_geometry_object
from anton.primitives.base import to_shapely


def translate_object(
    obj: GeometryObject,
    dx: float,
    dy: float,
    name: Optional[str] = None,
) -> GeometryObject:
    """Translate an object by (dx, dy) in metres.

    For basic primitives (circle, rectangle), updates center coordinates directly.
    For polygons or composite shapes, shifts vertices or geometry.
    Returns a new GeometryObject with a fresh UUID.
    """
    new_obj = copy.deepcopy(obj)
    new_obj.id = str(uuid4())
    if name:
        new_obj.name = name
    else:
        new_obj.name = f"{obj.name or 'obj'}_translated"

    new_obj.center_x += dx
    new_obj.center_y += dy

    if new_obj.vertices:
        new_obj.vertices = [
            VertexDef(x=v.x + dx, y=v.y + dy) for v in new_obj.vertices
        ]

    if new_obj.inner_vertices:
        new_obj.inner_vertices = [
            VertexDef(x=v.x + dx, y=v.y + dy) for v in new_obj.inner_vertices
        ]

    if new_obj.inner_holes:
        new_obj.inner_holes = [
            [VertexDef(x=v.x + dx, y=v.y + dy) for v in hole]
            for hole in new_obj.inner_holes
        ]

    return new_obj


def rotate_object(
    obj: GeometryObject,
    angle_deg: float,
    origin: Tuple[float, float] = (0.0, 0.0),
    name: Optional[str] = None,
) -> GeometryObject:
    """Rotate an object around an origin point by angle_deg (degrees).

    Returns a new GeometryObject representing the rotated geometry.
    """
    shape = to_shapely(obj)
    rot_shape = affinity.rotate(shape, angle_deg, origin=origin, use_radians=False)

    return _shape_to_geometry_object(
        rot_shape,
        name=name or f"{obj.name or 'obj'}_rot{int(angle_deg)}",
        layer_id=obj.layer_id,
        material_id=obj.material_id,
        operation_type="rotation",
    )


def scale_object(
    obj: GeometryObject,
    factor_x: float,
    factor_y: Optional[float] = None,
    origin: Tuple[float, float] = (0.0, 0.0),
    name: Optional[str] = None,
) -> GeometryObject:
    """Scale an object along X and Y axes relative to origin point."""
    fy = factor_y if factor_y is not None else factor_x
    shape = to_shapely(obj)
    scaled_shape = affinity.scale(shape, xfact=factor_x, yfact=fy, origin=origin)

    return _shape_to_geometry_object(
        scaled_shape,
        name=name or f"{obj.name or 'obj'}_scaled",
        layer_id=obj.layer_id,
        material_id=obj.material_id,
        operation_type="scale",
    )


def mirror_object(
    obj: GeometryObject,
    axis: str = "x",
    offset: float = 0.0,
    name: Optional[str] = None,
) -> GeometryObject:
    """Mirror an object across axis 'x' or 'y' at specified coordinate offset."""
    if axis not in {"x", "y"}:
        raise ValueError("Mirror axis must be 'x' or 'y'.")

    shape = to_shapely(obj)
    if axis == "x":
        # Mirror across x = offset: x -> 2*offset - x
        mirrored = affinity.scale(shape, xfact=-1, yfact=1, origin=(offset, 0))
    else:
        # Mirror across y = offset: y -> 2*offset - y
        mirrored = affinity.scale(shape, xfact=1, yfact=-1, origin=(0, offset))

    return _shape_to_geometry_object(
        mirrored,
        name=name or f"{obj.name or 'obj'}_mirror_{axis}",
        layer_id=obj.layer_id,
        material_id=obj.material_id,
        operation_type="mirror",
    )


def duplicate_object(
    obj: GeometryObject,
    new_name: Optional[str] = None,
) -> GeometryObject:
    """Create a deep copy of an object with a brand new UUID."""
    dup = copy.deepcopy(obj)
    dup.id = str(uuid4())
    if new_name:
        dup.name = new_name
    elif dup.name:
        dup.name = f"{dup.name}_copy"
    return dup


def extract_boundary(
    obj: GeometryObject,
    name: Optional[str] = None,
) -> GeometryObject:
    """Extract the outer boundary line of a 2D planar object."""
    shape = to_shapely(obj)
    if hasattr(shape, "exterior"):
        coords = list(shape.exterior.coords)
    elif hasattr(shape, "coords"):
        coords = list(shape.coords)
    else:
        raise ValueError(f"Cannot extract boundary from geometry of type {shape.geom_type}")

    vertices = [VertexDef(x=float(x), y=float(y)) for x, y in coords]
    return GeometryObject(
        id=str(uuid4()),
        name=name or f"{obj.name or 'obj'}_boundary",
        object_type="line",
        layer_id=obj.layer_id,
        material_id=obj.material_id,
        vertices=vertices,
    )

