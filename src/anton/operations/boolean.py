# -*- coding: utf-8 -*-
"""Boolean geometry operations for ANTON.

Performs Union, Difference, and Intersection operations on planar geometry objects.
Converts GeometryObject models to Shapely geometry, executes the topological operation,
and constructs a new canonical GeometryObject representing the result.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from uuid import uuid4

import shapely.geometry as geom
import shapely.ops as ops

from anton.models.geometry_schema import GeometryObject, VertexDef
from anton.primitives.base import to_shapely

logger = logging.getLogger(__name__)


def _shape_to_geometry_object(
    shape: geom.base.BaseGeometry,
    name: Optional[str],
    layer_id: str,
    material_id: str,
    operation_type: str = "boolean_result",
) -> GeometryObject:
    """Helper to convert a Shapely Polygon or MultiPolygon back into a GeometryObject."""
    if shape.is_empty:
        raise ValueError("Resulting boolean geometry is empty.")

    if isinstance(shape, geom.MultiPolygon):
        logger.warning(
            "Boolean operation produced a MultiPolygon. Selecting the component with the largest area."
        )
        shape = max(shape.geoms, key=lambda g: g.area)

    if not isinstance(shape, geom.Polygon):
        raise ValueError(
            f"Expected a 2D polygonal result from boolean operation, got {shape.geom_type}."
        )

    # Extract exterior coordinates (exclude duplicate closing point)
    ext_coords = list(shape.exterior.coords)
    if len(ext_coords) > 1 and ext_coords[0] == ext_coords[-1]:
        ext_coords = ext_coords[:-1]
    vertices = [VertexDef(x=float(x), y=float(y)) for x, y in ext_coords]

    # Extract inner holes if present
    inner_vertices: List[VertexDef] = []
    if len(shape.interiors) > 0:
        # If there are multiple holes, we can chain or extract the primary hole
        hole_coords = list(shape.interiors[0].coords)
        if len(hole_coords) > 1 and hole_coords[0] == hole_coords[-1]:
            hole_coords = hole_coords[:-1]
        inner_vertices = [VertexDef(x=float(x), y=float(y)) for x, y in hole_coords]

    centroid = shape.centroid

    return GeometryObject(
        id=str(uuid4()),
        name=name or f"{operation_type}_{uuid4().hex[:6]}",
        object_type="boolean_result",
        layer_id=layer_id,
        material_id=material_id,
        center_x=float(centroid.x),
        center_y=float(centroid.y),
        vertices=vertices,
        inner_vertices=inner_vertices,
        metadata={"operation": operation_type, "area": float(shape.area)},
    )


def boolean_union(
    objects: List[GeometryObject],
    name: Optional[str] = None,
    layer_id: Optional[str] = None,
    material_id: Optional[str] = None,
) -> GeometryObject:
    """Compute the geometric union of two or more geometry objects.

    Parameters
    ----------
    objects:
        List of objects to merge.
    name:
        Optional name for the resulting object.
    layer_id:
        Target layer ID (defaults to first object's layer if omitted).
    material_id:
        Target material ID (defaults to first object's material if omitted).
    """
    if not objects:
        raise ValueError("Cannot perform union on an empty object list.")

    target_layer = layer_id or objects[0].layer_id
    target_material = material_id or objects[0].material_id

    shapes = [to_shapely(obj) for obj in objects]
    result_shape = ops.unary_union(shapes)

    return _shape_to_geometry_object(
        result_shape,
        name=name or "Union_Result",
        layer_id=target_layer,
        material_id=target_material,
        operation_type="union",
    )


def boolean_difference(
    base: GeometryObject,
    cutters: List[GeometryObject],
    name: Optional[str] = None,
    layer_id: Optional[str] = None,
    material_id: Optional[str] = None,
) -> GeometryObject:
    """Subtract one or more cutter objects from the base object.

    Useful for creating slots, notches, cutouts, inset feeds, annular rings, etc.

    Parameters
    ----------
    base:
        The primary object to cut into.
    cutters:
        Objects representing cutouts or slots to subtract.
    name:
        Optional name for resulting object.
    layer_id:
        Target layer ID (defaults to base.layer_id).
    material_id:
        Target material ID (defaults to base.material_id).
    """
    if not cutters:
        return base

    target_layer = layer_id or base.layer_id
    target_material = material_id or base.material_id

    base_shape = to_shapely(base)
    cutter_shapes = [to_shapely(c) for c in cutters]
    cutter_union = ops.unary_union(cutter_shapes)

    result_shape = base_shape.difference(cutter_union)

    if result_shape.is_empty:
        raise ValueError("Difference operation resulted in an empty geometry (cutters completely eclipsed base).")

    return _shape_to_geometry_object(
        result_shape,
        name=name or f"{base.name or 'base'}_cut",
        layer_id=target_layer,
        material_id=target_material,
        operation_type="difference",
    )


def boolean_intersection(
    objects: List[GeometryObject],
    name: Optional[str] = None,
    layer_id: Optional[str] = None,
    material_id: Optional[str] = None,
) -> GeometryObject:
    """Compute the geometric intersection of two or more geometry objects.

    Parameters
    ----------
    objects:
        Objects to intersect.
    name:
        Optional name for resulting object.
    layer_id:
        Target layer ID (defaults to first object's layer).
    material_id:
        Target material ID (defaults to first object's material).
    """
    if not objects:
        raise ValueError("Cannot perform intersection on an empty object list.")

    target_layer = layer_id or objects[0].layer_id
    target_material = material_id or objects[0].material_id

    result_shape = to_shapely(objects[0])
    for obj in objects[1:]:
        result_shape = result_shape.intersection(to_shapely(obj))
        if result_shape.is_empty:
            raise ValueError("Intersection resulted in empty geometry.")

    return _shape_to_geometry_object(
        result_shape,
        name=name or "Intersection_Result",
        layer_id=target_layer,
        material_id=target_material,
        operation_type="intersection",
    )
