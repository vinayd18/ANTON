# -*- coding: utf-8 -*-
"""3D CAD solid generation engine for ANTON using CadQuery and OpenCASCADE."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import shapely.geometry as geom

from anton.models.geometry_schema import GeometryObject, GeometryProject
from anton.primitives.base import to_shapely

logger = logging.getLogger(__name__)

try:
    import cadquery as cq
    CADQUERY_AVAILABLE = True
except ImportError:
    cq = None
    CADQUERY_AVAILABLE = False


# Assembly color styling by layer type (RGB + Alpha)
LAYER_COLOR_CAD: Dict[str, cq.Color] = {}
if CADQUERY_AVAILABLE:
    LAYER_COLOR_CAD = {
        "ground": cq.Color(0.58, 0.64, 0.72, 1.0),      # Slate gray
        "substrate": cq.Color(0.73, 0.90, 0.99, 0.6),   # Translucent dielectric cyan
        "patch": cq.Color(0.96, 0.62, 0.04, 1.0),       # Copper / gold
        "feed": cq.Color(0.06, 0.72, 0.51, 1.0),        # Green conductor
        "conductor": cq.Color(0.92, 0.70, 0.03, 1.0),   # Golden yellow
        "custom": cq.Color(0.66, 0.33, 0.97, 1.0),      # Purple
    }


class SolidGenerator:
    """Generates 3D CAD solids and assemblies from canonical ANTON geometry projects."""

    def __init__(self, project: GeometryProject) -> None:
        if not CADQUERY_AVAILABLE:
            raise ImportError(
                "CadQuery is required for 3D CAD solid generation. "
                "Please install cadquery in your Python environment."
            )
        self.project = project

    def _polygon_to_workplane(
        self,
        polygon: geom.Polygon,
        thickness: float,
        z_position: float,
    ) -> cq.Workplane:
        """Extrude a 2D Shapely polygon (with any interior cut-outs) into a 3D solid."""
        if thickness <= 0:
            # Thin metallization representation default (e.g. 35 um standard 1 oz copper)
            thickness = 35e-6

        # Exterior contour
        ext_coords = [(float(x), float(y)) for x, y in polygon.exterior.coords[:-1]]
        if len(ext_coords) < 3:
            raise ValueError("Polygon exterior requires at least 3 vertices to extrude.")

        solid = (
            cq.Workplane("XY")
            .polyline(ext_coords)
            .close()
            .extrude(thickness)
        )

        # Subtract any interior cutouts / holes
        for interior in polygon.interiors:
            int_coords = [(float(x), float(y)) for x, y in interior.coords[:-1]]
            if len(int_coords) >= 3:
                hole_cutter = (
                    cq.Workplane("XY")
                    .polyline(int_coords)
                    .close()
                    .extrude(thickness * 1.5)  # Ensure full cut-through
                    .translate((0, 0, -thickness * 0.25))
                )
                solid = solid.cut(hole_cutter)

        # Apply Z-stack offset
        if z_position != 0.0:
            solid = solid.translate((0, 0, z_position))

        return solid

    def generate_solid(
        self,
        obj: GeometryObject,
        thickness: Optional[float] = None,
        z_position: Optional[float] = None,
    ) -> cq.Workplane:
        """Generate a 3D CadQuery solid for a single GeometryObject.

        Parameters
        ----------
        obj:
            GeometryObject to extrude.
        thickness:
            Extrusion thickness in metres. If None, inherits from parent layer.
        z_position:
            Z-plane offset in metres. If None, inherits from parent layer.
        """
        layer = self.project.layers.get(obj.layer_id)
        eff_thickness = thickness if thickness is not None else (layer.thickness if layer else 35e-6)
        eff_z = z_position if z_position is not None else (layer.z_position if layer else 0.0)

        shape = to_shapely(obj)

        if isinstance(shape, geom.Polygon):
            return self._polygon_to_workplane(shape, eff_thickness, eff_z)
        elif isinstance(shape, geom.MultiPolygon):
            # Compound extrusion of multi-polygon components
            solids = [
                self._polygon_to_workplane(poly, eff_thickness, eff_z)
                for poly in shape.geoms
            ]
            compound_solid = solids[0]
            for s in solids[1:]:
                compound_solid = compound_solid.union(s)
            return compound_solid
        elif isinstance(shape, (geom.LineString, geom.MultiLineString)):
            raise TypeError(
                f"Cannot directly extrude 1D line object '{obj.id}'. "
                "Feed or trace lines should be modeled as 2D strips."
            )
        else:
            raise NotImplementedError(
                f"CAD extrusion not supported for geometry type {shape.geom_type}"
            )

    def generate_assembly(self) -> cq.Assembly:
        """Construct a complete multi-layer 3D CAD assembly from the geometry project.

        Returns
        -------
        cq.Assembly:
            CadQuery Assembly with colored solids positioned in the vertical stack.
        """
        assembly = cq.Assembly(name=self.project.project_name)

        for layer in self.project.layers.values():
            color = LAYER_COLOR_CAD.get(
                layer.layer_type.lower(),
                LAYER_COLOR_CAD.get("custom"),
            )

            for obj_id in layer.object_ids:
                obj = self.project.objects.get(obj_id)
                if not obj:
                    continue
                if obj.object_type in {"line", "arc"}:
                    continue  # Skip unextruded 1D guides

                try:
                    solid = self.generate_solid(
                        obj,
                        thickness=layer.thickness,
                        z_position=layer.z_position,
                    )
                    elem_name = f"{layer.name}_{obj.name or obj.id[:6]}"
                    assembly.add(solid, name=elem_name, color=color)
                except Exception as e:
                    logger.error("Failed to generate solid for '%s': %s", obj.id, e)

        return assembly
