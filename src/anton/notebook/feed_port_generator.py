# -*- coding: utf-8 -*-
"""Feed and excitation port configuration code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

import math
from typing import List, Optional
from shapely.geometry import Point

from anton.feeds.feed_geometry import FeedDef, FeedType
from anton.models.geometry_schema import GeometryObject, GeometryProject
from anton.primitives.base import to_shapely


class FeedPortGenerator:
    """Generates PyAEDT code for configuring RF ports and excitations (Lumped, Wave, or Probe).

    Enforces electrical connectivity validation and verifies port placement before code generation.
    """

    def __init__(self, project: GeometryProject, feeds: Optional[List[FeedDef]] = None) -> None:
        self.project = project
        self.feeds = feeds or []

    def _resolve_feed_and_target(self) -> tuple[Optional[GeometryObject], Optional[GeometryObject]]:
        """Resolve the verified signal feed object and target radiator object."""
        # 1. Check canonical connections
        if getattr(self.project, "connections", None):
            for conn in self.project.connections:
                src_obj = self.project.objects.get(conn.source_object_id)
                tgt_obj = self.project.objects.get(conn.target_object_id)
                if src_obj and tgt_obj:
                    # Validate electrical connectivity using Shapely
                    src_shape = to_shapely(src_obj)
                    tgt_shape = to_shapely(tgt_obj)
                    if src_shape.intersects(tgt_shape) or src_shape.touches(tgt_shape) or src_shape.distance(tgt_shape) < 1e-5:
                        return src_obj, tgt_obj
                    else:
                        raise ValueError(
                            f"Electrical connectivity check FAILED: Declared feed '{src_obj.name}' "
                            f"does not physically touch target radiator '{tgt_obj.name}' "
                            f"(distance: {src_shape.distance(tgt_shape)*1e3:.4f} mm)."
                        )

        # 2. Check objects on layers of type 'feed' or named '*feed*'
        feed_objs = [
            o for o in self.project.objects.values()
            if "feed" in (o.name or "").lower() or (
                self.project.layers.get(o.layer_id) and self.project.layers[o.layer_id].layer_type == "feed"
            )
        ]
        patch_objs = [
            o for o in self.project.objects.values()
            if self.project.layers.get(o.layer_id) and self.project.layers[o.layer_id].layer_type in {"patch", "custom"}
            and o not in feed_objs
        ]

        for f_obj in feed_objs:
            f_shape = to_shapely(f_obj)
            for p_obj in patch_objs:
                p_shape = to_shapely(p_obj)
                if f_shape.intersects(p_shape) or f_shape.touches(p_shape) or f_shape.distance(p_shape) < 1e-5:
                    return f_obj, p_obj

        # If feed object exists but no patch contacts it
        if feed_objs:
            return feed_objs[0], None

        return None, None

    def generate_port_configuration_code(self) -> str:
        """Generate Python code block for constructing port sheets and assigning excitations.

        Raises ValueError if no valid feed structure is found or if port position is inside a cutout.
        """
        lines: List[str] = [
            "# ===========================================================================",
            "# 5. PORT & EXCITATION CONFIGURATION",
            "# ===========================================================================",
            "print('Configuring RF excitation ports in HFSS...')",
            "",
            "# Identify ground reference conductor in HFSS modeler",
            "ground_names = [obj.name for obj in app.modeler.object_list if 'ground' in obj.name.lower()]",
            "if not ground_names:",
            "    raise RuntimeError('CRITICAL: No ground plane conductor found in HFSS modeler for port reference.')",
            "ref_ground = ground_names[0]",
            "print(f\"  Reference ground conductor: '{ref_ground}'\")",
            "",
        ]

        # Determine substrate vertical bounds
        sub_layer = next((l for l in self.project.layers.values() if l.layer_type == "substrate"), None)
        h_sub = sub_layer.thickness if sub_layer else 0.0016
        z_sub_bottom = sub_layer.z_position if sub_layer else 0.0
        z_sub_top = z_sub_bottom + h_sub

        feed_obj, patch_obj = self._resolve_feed_and_target()

        if feed_obj is None and not self.feeds:
            raise ValueError(
                f"Cannot configure RF excitation port for project '{self.project.project_name}': "
                "No feed conductor with verified electrical contact to the radiator was found in the canonical model. "
                "Define a microstrip feed line or coaxial probe feed before generating HFSS excitation."
            )

        if feed_obj and patch_obj is None and not self.feeds:
            raise ValueError(
                f"Electrical connectivity check FAILED for project '{self.project.project_name}': "
                f"Feed conductor '{feed_obj.name}' does not physically contact any radiating patch element."
            )

        if feed_obj:
            # Determine port edge and orientation based on feed geometry and relative patch placement
            cx = feed_obj.center_x or 0.0
            cy = feed_obj.center_y or 0.0
            w_f = feed_obj.width or 0.003
            h_f = feed_obj.height or 0.015

            p_cx = patch_obj.center_x if patch_obj else 0.0
            p_cy = patch_obj.center_y if patch_obj else 0.0

            # Detect whether feed line runs vertically (along Y) or horizontally (along X)
            is_y_directed = h_f >= w_f

            if is_y_directed:
                # Vertical feed line: port sheet is in XZ plane
                port_plane = "XZ"
                if patch_obj:
                    patch_shape = to_shapely(patch_obj)
                    if p_cy >= cy:
                        # Feed contacts patch at top (+Y); port is at bottom outer edge (-Y)
                        port_y = cy - h_f / 2.0
                    else:
                        # Feed contacts patch at bottom (-Y); port is at top outer edge (+Y)
                        port_y = cy + h_f / 2.0

                    port_test_pt = Point(cx, port_y)
                    if patch_shape.contains(port_test_pt):
                        raise ValueError(
                            f"Port placement ERROR: Derived port coordinate ({cx*1e3:.2f}, {port_y*1e3:.2f}) mm "
                            f"lies inside the radiator body or cutout hole of '{patch_obj.name}'."
                        )
                else:
                    port_y = cy - h_f / 2.0

                port_origin = [cx - w_f / 2.0, port_y, z_sub_bottom]
                port_sizes = [w_f, h_sub]
                int_line_start = [cx, port_y, z_sub_bottom]
                int_line_stop = [cx, port_y, z_sub_top]
                loc_desc = f"x={cx * 1e3:.3f} mm, y={port_y * 1e3:.3f} mm"
            else:
                # Horizontal feed line: port sheet is in YZ plane
                port_plane = "YZ"
                if patch_obj:
                    patch_shape = to_shapely(patch_obj)
                    if p_cx >= cx:
                        # Feed contacts patch at right (+X); port is at left outer edge (-X)
                        port_x = cx - w_f / 2.0
                    else:
                        # Feed contacts patch at left (-X); port is at right outer edge (+X)
                        port_x = cx + w_f / 2.0

                    port_test_pt = Point(port_x, cy)
                    if patch_shape.contains(port_test_pt):
                        raise ValueError(
                            f"Port placement ERROR: Derived port coordinate ({port_x*1e3:.2f}, {cy*1e3:.2f}) mm "
                            f"lies inside the radiator body or cutout hole of '{patch_obj.name}'."
                        )
                else:
                    port_x = cx - w_f / 2.0

                port_origin = [port_x, cy - h_f / 2.0, z_sub_bottom]
                port_sizes = [h_f, h_sub]
                int_line_start = [port_x, cy, z_sub_bottom]
                int_line_stop = [port_x, cy, z_sub_top]
                loc_desc = f"x={port_x * 1e3:.3f} mm, y={cy * 1e3:.3f} mm"

            lines.append(f"# Verified feed conductor: '{feed_obj.name}' (signal trace)")
            lines.append(f"# Port location: {loc_desc}, plane={port_plane}, spanning z=[{z_sub_bottom * 1e3:.3f}, {z_sub_top * 1e3:.3f}] mm")
            if is_y_directed:
                lines.append(f"port_y = {port_y}")
            else:
                lines.append(f"port_x = {port_x}")
            lines.append(f"port_origin = {port_origin}")
            lines.append(f"port_sizes = {port_sizes}")
            lines.append("")
            lines.append(f"# Construct 2D excitation port sheet in {port_plane} plane bridging ground to signal trace")
            lines.append("try:")
            lines.append("    port_sheet = app.modeler.create_rectangle(")
            lines.append(f"        orientation='{port_plane}',")
            lines.append("        origin=port_origin,")
            lines.append("        sizes=port_sizes,")
            lines.append("        name='Port1_Sheet',")
            lines.append("    )")
            lines.append("except Exception:")
            lines.append("    port_sheet = app.modeler.create_rectangle(")
            lines.append(f"        csPlane='{port_plane}',")
            lines.append("        position=port_origin,")
            lines.append("        dimension_list=port_sizes,")
            lines.append("        name='Port1_Sheet',")
            lines.append("    )")
            lines.append("")
            lines.append("if port_sheet is None:")
            lines.append("    raise RuntimeError('CRITICAL: Failed to construct Port1_Sheet in HFSS modeler.')")
            lines.append("print(f\"  Created excitation sheet: '{port_sheet.name}'\")")
            lines.append("")
            lines.append("# Integration line: directed +Z from reference ground to signal trace")
            lines.append(f"int_line_start = {int_line_start}")
            lines.append(f"int_line_stop = {int_line_stop}")
            lines.append("")
            lines.append("# Assign 50-Ohm Lumped Port with integration line")
            lines.append("try:")
            lines.append("    app.create_lumped_port_to_sheet(")
            lines.append("        sheet_name=port_sheet.name,")
            lines.append("        axisdir=[int_line_start, int_line_stop],")
            lines.append("        portname='1',")
            lines.append("        impedance=50.0,")
            lines.append("        renormalize=True,")
            lines.append("        reference_object_list=[ref_ground],")
            lines.append("    )")
            lines.append("    print(f\"  Assigned Lumped Port '1' via create_lumped_port_to_sheet to '{port_sheet.name}'\")")
            lines.append("except Exception as e1:")
            lines.append("    try:")
            lines.append("        app.lumped_port(")
            lines.append("            signal=port_sheet.name,")
            lines.append("            reference=ref_ground,")
            lines.append("            integration_line=[int_line_start, int_line_stop],")
            lines.append("            impedance=50.0,")
            lines.append("            name='1',")
            lines.append("            renormalize=True,")
            lines.append("        )")
            lines.append("        print(f\"  Assigned Lumped Port '1' via lumped_port to '{port_sheet.name}'\")")
            lines.append("    except Exception as e2:")
            lines.append("        raise RuntimeError(f\"CRITICAL: Failed to assign Lumped Port '1' in HFSS: {e1} / {e2}\") from e2")

        elif self.feeds:
            for idx, feed in enumerate(self.feeds):
                p_name = f"Port_{idx + 1}"
                lines.append(f"# Feed: '{feed.name}' (Type: {feed.feed_type.value})")
                if feed.feed_type == FeedType.PROBE and feed.connection_point_x is not None:
                    px, py = feed.connection_point_x, feed.connection_point_y
                    lines.append(f"# Coaxial probe pin at ({px * 1e3:.2f}, {py * 1e3:.2f}) mm")
                    lines.append(
                        f"probe_pin = app.modeler.create_cylinder("
                        f"cs_axis='Z', position=[{px}, {py}, {z_sub_bottom}], "
                        f"radius=0.0006, height={h_sub}, name='{p_name}_Pin', matname='copper'"
                        f")"
                    )
                    lines.append("if probe_pin is None:")
                    lines.append(f"    raise RuntimeError(\"CRITICAL: Failed to create probe pin for '{p_name}'.\")")

        lines.append("")
        lines.append("print('Excitation port configuration successfully completed.')")
        return "\n".join(lines)
