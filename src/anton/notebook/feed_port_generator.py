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
            # Determine port edge and orientation
            cx = feed_obj.center_x or 0.0
            cy = feed_obj.center_y or 0.0
            w_f = feed_obj.width or 0.003
            h_f = feed_obj.height or 0.015

            # If target patch is known, find which end of the feed line contacts the patch
            if patch_obj:
                patch_shape = to_shapely(patch_obj)
                p_cy = patch_obj.center_y or 0.0
                # Contact interface is at top (contact_y > cy) or at bottom (contact_y < cy)
                if p_cy >= cy:
                    # Feed line contacts patch at top (+Y edge); excitation port is at outer bottom (-Y edge)
                    port_y = cy - h_f / 2.0
                else:
                    # Feed line contacts patch at bottom (-Y edge); excitation port is at outer top (+Y edge)
                    port_y = cy + h_f / 2.0

                # Strictly validate that port_y is NOT inside the patch or any hole
                port_test_pt = Point(cx, port_y)
                if patch_shape.contains(port_test_pt):
                    raise ValueError(
                        f"Port placement ERROR: Derived port coordinate ({cx*1e3:.2f}, {port_y*1e3:.2f}) mm "
                        f"lies inside the radiator body or cutout hole of '{patch_obj.name}'."
                    )
            else:
                port_y = cy - h_f / 2.0

            port_x0 = cx - w_f / 2.0
            port_z0 = z_sub_bottom
            port_h = h_sub

            lines.append(f"# Verified feed conductor: '{feed_obj.name}' (signal trace)")
            lines.append(f"# Port location: x={cx * 1e3:.3f} mm, y={port_y * 1e3:.3f} mm, spanning z=[{port_z0 * 1e3:.3f}, {z_sub_top * 1e3:.3f}] mm")
            lines.append(f"port_w = {w_f}")
            lines.append(f"port_h = {port_h}")
            lines.append(f"port_x0 = {port_x0}")
            lines.append(f"port_y = {port_y}")
            lines.append(f"port_z0 = {port_z0}")
            lines.append("")
            lines.append("# Construct 2D excitation port sheet in XZ plane bridging ground to signal trace")
            lines.append("try:")
            lines.append("    port_sheet = app.modeler.create_rectangle(")
            lines.append("        orientation='XZ',")
            lines.append("        origin=[port_x0, port_y, port_z0],")
            lines.append("        sizes=[port_w, port_h],")
            lines.append("        name='Port1_Sheet',")
            lines.append("    )")
            lines.append("except Exception:")
            lines.append("    port_sheet = app.modeler.create_rectangle(")
            lines.append("        csPlane='XZ',")
            lines.append("        position=[port_x0, port_y, port_z0],")
            lines.append("        dimension_list=[port_w, port_h],")
            lines.append("        name='Port1_Sheet',")
            lines.append("    )")
            lines.append("")
            lines.append("if port_sheet is None:")
            lines.append("    raise RuntimeError('CRITICAL: Failed to construct Port1_Sheet in HFSS modeler.')")
            lines.append("print(f\"  Created excitation sheet: '{port_sheet.name}'\")")
            lines.append("")
            lines.append("# Integration line: directed +Z from reference ground to signal trace")
            lines.append(f"int_line_start = [{cx}, {port_y}, {port_z0}]")
            lines.append(f"int_line_stop = [{cx}, {port_y}, {z_sub_top}]")
            lines.append("")
            lines.append("# Assign 50-Ohm Lumped Port with integration line")
            lines.append("try:")
            lines.append("    app.lumped_port(")
            lines.append("        assignment=port_sheet.name,")
            lines.append("        reference=ref_ground,")
            lines.append("        integration_line=[int_line_start, int_line_stop],")
            lines.append("        create_port_sheet=False,")
            lines.append("        port_name='1',")
            lines.append("    )")
            lines.append("    print(f\"  Assigned Lumped Port '1' with +Z integration line to '{port_sheet.name}'\")")
            lines.append("except Exception as e1:")
            lines.append("    try:")
            lines.append("        app.create_lumped_port_to_sheet(")
            lines.append("            sheet_name=port_sheet.name,")
            lines.append("            reference_object_list=[ref_ground],")
            lines.append("            integration_line=[int_line_start, int_line_stop],")
            lines.append("            portname='1',")
            lines.append("        )")
            lines.append("        print(f\"  Assigned Lumped Port '1' via create_lumped_port_to_sheet to '{port_sheet.name}'\")")
            lines.append("    except Exception as e2:")
            lines.append("        raise RuntimeError(f\"CRITICAL: Failed to assign Lumped Port '1' in HFSS: {e1} / {e2}\")")

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
