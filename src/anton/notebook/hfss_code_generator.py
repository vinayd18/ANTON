# -*- coding: utf-8 -*-
"""Geometry-to-HFSS code generator for PyAEDT notebooks."""

from __future__ import annotations

import math
from typing import List, Optional
from anton.models.geometry_schema import GeometryObject, GeometryProject


class HFSSCodeGenerator:
    """Translates canonical ANTON geometry objects into executable PyAEDT modeler code."""

    def __init__(self, project: GeometryProject) -> None:
        self.project = project

    def generate_patch_and_feed_geometry_code(self) -> str:
        """Generate Python code block for constructing patch radiators, slots, and feed conductors."""
        lines: List[str] = [
            "# ===========================================================================",
            "# 4. RADIATING PATCH, FEED, AND CSG SLOTS/CUTOUTS RECONSTRUCTION",
            "# ===========================================================================",
            "print('Constructing radiating patch elements and feed geometry in HFSS...')",
            "",
            "if app is not None:",
        ]

        # Process patch and feed layers
        for layer in self.project.layers.values():
            if layer.layer_type in {"patch", "feed", "conductor", "custom"}:
                lines.append(f"    # --- Layer: '{layer.name}' ({layer.layer_type}) at z={layer.z_position * 1e3:.4f} mm ---")

                for obj_id in layer.object_ids:
                    obj = self.project.objects.get(obj_id)
                    if not obj:
                        continue

                    obj_name = obj.name or f"{layer.name}_{obj.id[:6]}"
                    mat_id_str = f"material_name_map.get('{obj.material_id}', 'copper')"
                    z0 = layer.z_position
                    t = layer.thickness if layer.thickness > 0 else 35e-6

                    if obj.object_type in {"rectangle", "square"} and obj.width and obj.height:
                        x0 = obj.center_x - obj.width / 2.0
                        y0 = obj.center_y - obj.height / 2.0

                        if obj.rotation_deg and obj.rotation_deg != 0.0:
                            # Construct as 4 rotated vertices
                            hw, hh = obj.width / 2.0, obj.height / 2.0
                            rad = math.radians(obj.rotation_deg)
                            cos_a, sin_a = math.cos(rad), math.sin(rad)
                            corners = [(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)]
                            rot_pts = []
                            for cx_loc, cy_loc in corners:
                                rx = cx_loc * cos_a - cy_loc * sin_a + obj.center_x
                                ry = cx_loc * sin_a + cy_loc * cos_a + obj.center_y
                                rot_pts.append([rx, ry, z0])

                            lines.append(f"    # Rotated rectangle: {obj_name} ({obj.rotation_deg} deg)")
                            lines.append(f"    pts_{obj_name} = {rot_pts}")
                            lines.append(
                                f"    solid_{obj_name} = app.modeler.create_polyline("
                                f"points=pts_{obj_name}, close_surface=True, cover_surface=True, "
                                f"name='{obj_name}', matname={mat_id_str}"
                                f")"
                            )
                            lines.append(f"    app.modeler.extrude_sheet(solid_{obj_name}.name, {t})")
                        else:
                            lines.append(f"    # Rectangular conductor: {obj_name}")
                            lines.append(
                                f"    solid_{obj_name} = app.modeler.create_box("
                                f"origin=[{x0}, {y0}, {z0}], "
                                f"sizes=[{obj.width}, {obj.height}, {t}], "
                                f"name='{obj_name}', "
                                f"matname={mat_id_str}"
                                f")"
                            )
                        lines.append(f"    hfss_objects['{obj.id}'] = solid_{obj_name}.name")
                        lines.append(f"    app.modeler.set_color(solid_{obj_name}.name, [245, 158, 11])")
                        lines.append(f"    print(f\"  Created rectangular patch: '{{solid_{obj_name}.name}}'\")")

                    elif obj.object_type == "circle" and obj.radius:
                        lines.append(f"    # Circular disk solid: {obj_name}")
                        lines.append(
                            f"    solid_{obj_name} = app.modeler.create_cylinder("
                            f"cs_axis='Z', "
                            f"position=[{obj.center_x}, {obj.center_y}, {z0}], "
                            f"radius={obj.radius}, "
                            f"height={t}, "
                            f"name='{obj_name}', "
                            f"matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"    hfss_objects['{obj.id}'] = solid_{obj_name}.name")
                        lines.append(f"    app.modeler.set_color(solid_{obj_name}.name, [245, 158, 11])")
                        lines.append(f"    print(f\"  Created circular patch: '{{solid_{obj_name}.name}}'\")")

                    elif obj.object_type == "ellipse" and (obj.semi_major or getattr(obj, "radius", None)):
                        a = obj.semi_major or obj.radius or 0.02
                        b = obj.semi_minor or (a * 0.7)
                        ratio = b / a if a > 0 else 1.0
                        lines.append(f"    # Elliptical patch solid: {obj_name}")
                        lines.append("    try:")
                        lines.append(
                            f"        solid_{obj_name} = app.modeler.create_ellipse("
                            f"csPlane='XY', position=[{obj.center_x}, {obj.center_y}, {z0}], "
                            f"major_radius={a}, ratio={ratio}, name='{obj_name}')"
                        )
                        lines.append(f"        app.modeler.extrude_sheet(solid_{obj_name}.name, {t})")
                        lines.append("    except Exception:")
                        lines.append("        import math as _m")
                        lines.append(f"        _el_pts = [[{obj.center_x} + {a} * _m.cos(_t), {obj.center_y} + {b} * _m.sin(_t), {z0}] for _t in [_k * 2 * _m.pi / 64 for _k in range(64)]]")
                        lines.append(f"        solid_{obj_name} = app.modeler.create_polyline(points=_el_pts, close_surface=True, cover_surface=True, name='{obj_name}', matname={mat_id_str})")
                        lines.append(f"        app.modeler.extrude_sheet(solid_{obj_name}.name, {t})")
                        lines.append(f"    hfss_objects['{obj.id}'] = solid_{obj_name}.name")
                        lines.append(f"    app.modeler.set_color(solid_{obj_name}.name, [245, 158, 11])")
                        lines.append(f"    print(f\"  Created elliptical patch: '{{solid_{obj_name}.name}}'\")")

                    elif obj.object_type == "triangle":
                        pts_literal = [[v.x, v.y, z0] for v in obj.vertices]
                        lines.append(f"    # Triangular patch solid: {obj_name}")
                        lines.append(f"    pts_{obj_name} = {pts_literal}")
                        lines.append(
                            f"    solid_{obj_name} = app.modeler.create_polyline("
                            f"points=pts_{obj_name}, close_surface=True, cover_surface=True, "
                            f"name='{obj_name}', matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"    app.modeler.extrude_sheet(solid_{obj_name}.name, {t})")
                        lines.append(f"    hfss_objects['{obj.id}'] = solid_{obj_name}.name")
                        lines.append(f"    app.modeler.set_color(solid_{obj_name}.name, [245, 158, 11])")
                        lines.append(f"    print(f\"  Created triangular patch: '{{solid_{obj_name}.name}}'\")")

                    elif obj.vertices:
                        # Arbitrary polygon, CSG boolean result, or contour
                        pts_literal = [[v.x, v.y, z0] for v in obj.vertices]
                        lines.append(f"    # Polygonal / CSG solid: {obj_name}")
                        lines.append(f"    pts_{obj_name} = {pts_literal}")
                        lines.append(
                            f"    solid_{obj_name} = app.modeler.create_polyline("
                            f"points=pts_{obj_name}, close_surface=True, cover_surface=True, "
                            f"name='{obj_name}', matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"    app.modeler.extrude_sheet(solid_{obj_name}.name, {t})")

                        # If there are interior cutouts (holes)
                        if obj.inner_vertices:
                            hole_pts = [[v.x, v.y, z0 - t * 0.1] for v in obj.inner_vertices]
                            lines.append(f"    # Cutout hole: {obj_name}_hole")
                            lines.append(f"    hole_pts_{obj_name} = {hole_pts}")
                            lines.append(
                                f"    hole_{obj_name} = app.modeler.create_polyline("
                                f"points=hole_pts_{obj_name}, close_surface=True, cover_surface=True, "
                                f"name='{obj_name}_cutter', matname={mat_id_str}"
                                f")"
                            )
                            lines.append(f"    app.modeler.extrude_sheet(hole_{obj_name}.name, {t * 1.5})")
                            lines.append(
                                f"    app.modeler.subtract("
                                f"blank_list=[solid_{obj_name}.name], "
                                f"tool_list=[hole_{obj_name}.name], "
                                f"keep_originals=False"
                                f")"
                            )
                            lines.append(f"    print(f\"  Subtracted interior hole from '{{solid_{obj_name}.name}}'\")")

                        lines.append(f"    hfss_objects['{obj.id}'] = solid_{obj_name}.name")
                        lines.append(f"    app.modeler.set_color(solid_{obj_name}.name, [245, 158, 11])")
                        lines.append(f"    print(f\"  Created polygon patch: '{{solid_{obj_name}.name}}'\")")

                lines.append("")

        lines.append("    print('Radiating patch and feed geometry constructed successfully.')")
        lines.append("else:")
        lines.append("    print('Notice: app is None (offline mode). Modeler patch generation skipped.')")
        return "\n".join(lines)
