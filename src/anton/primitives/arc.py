# -*- coding: utf-8 -*-
"""Arc → Shapely converter."""

from __future__ import annotations

import math
import shapely.geometry as geom
import shapely.affinity as affinity

from anton.models.geometry_schema import GeometryObject


def arc_to_shapely(obj: GeometryObject) -> geom.LineString:
    """Build a Shapely LineString representing a circular arc from *obj*.

    Uses *radius*, *center_x*, *center_y*.
    Angles can be specified in obj.parameters (start_angle_deg, end_angle_deg)
    or metadata, defaulting to 0 to 180 degrees.
    """
    radius = obj.radius or 0.0
    if radius <= 0:
        raise ValueError(f"Arc object '{obj.id}' has non-positive radius: {radius}")

    start_deg = 0.0
    end_deg = 180.0
    if "start_angle_deg" in obj.parameters:
        start_deg = obj.parameters["start_angle_deg"].value
    elif "start_angle_deg" in obj.metadata:
        start_deg = float(obj.metadata["start_angle_deg"])

    if "end_angle_deg" in obj.parameters:
        end_deg = obj.parameters["end_angle_deg"].value
    elif "end_angle_deg" in obj.metadata:
        end_deg = float(obj.metadata["end_angle_deg"])

    # Discretize arc
    steps = 64
    d_theta = (end_deg - start_deg) / steps
    points = []
    for i in range(steps + 1):
        theta = math.radians(start_deg + i * d_theta)
        x = obj.center_x + radius * math.cos(theta)
        y = obj.center_y + radius * math.sin(theta)
        points.append((x, y))

    line = geom.LineString(points)
    if obj.rotation_deg:
        line = affinity.rotate(
            line, obj.rotation_deg, origin=(obj.center_x, obj.center_y), use_radians=False
        )
    return line

