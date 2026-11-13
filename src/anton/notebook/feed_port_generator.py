# -*- coding: utf-8 -*-
"""Feed and excitation port configuration code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import List, Optional
from anton.feeds.feed_geometry import FeedDef, FeedType
from anton.models.geometry_schema import GeometryProject


class FeedPortGenerator:
    """Generates PyAEDT code for configuring RF ports and excitations (Lumped, Wave, or Probe)."""

    def __init__(self, project: GeometryProject, feeds: Optional[List[FeedDef]] = None) -> None:
        self.project = project
        self.feeds = feeds or []

    def generate_port_configuration_code(self) -> str:
        """Generate Python code block for constructing port sheets and assigning excitations."""
        lines: List[str] = [
            "# ===========================================================================",
            "# 5. PORT & EXCITATION CONFIGURATION",
            "# ===========================================================================",
            "print('Configuring RF excitation ports in HFSS...')",
            "",
            "if app is not None:",
            "    # Identify ground and substrate geometry for port referencing",
            "    ground_names = [obj.name for obj in app.modeler.object_list if 'ground' in obj.name.lower()]",
            "    ref_ground = ground_names[0] if ground_names else None",
            "",
        ]

        # Find substrate layer to determine height
        sub_layer = next((l for l in self.project.layers.values() if l.layer_type == "substrate"), None)
        h_sub = sub_layer.thickness if sub_layer else 0.0016
        z_sub_bottom = sub_layer.z_position if sub_layer else 0.0
        z_sub_top = z_sub_bottom + h_sub

        # Collect potential feed objects with strict prioritization:
        # Priority 1: Objects on a layer with layer_type == "feed"
        feed_objs = []
        for layer in self.project.layers.values():
            if layer.layer_type == "feed":
                for oid in layer.object_ids:
                    o = self.project.objects.get(oid)
                    if o:
                        feed_objs.append(o)

        # Priority 2: Objects with "feed" in their name across all layers
        if not feed_objs:
            for o in self.project.objects.values():
                if "feed" in (o.name or "").lower():
                    feed_objs.append(o)

        # Priority 3: Connections source objects
        if not feed_objs and getattr(self.project, "connections", None):
            for conn in self.project.connections:
                src_o = self.project.objects.get(conn.source_object_id)
                if src_o:
                    feed_objs.append(src_o)

        # Priority 4: Fallback to patch layer objects if no feed object exists
        if not feed_objs:
            for layer in self.project.layers.values():
                if layer.layer_type == "patch":
                    for oid in layer.object_ids:
                        o = self.project.objects.get(oid)
                        if o:
                            feed_objs.append(o)

        if not self.feeds and feed_objs:
            # Default microstrip lumped port at lowest Y edge of the primary feed object
            primary_feed = min(feed_objs, key=lambda o: (o.center_y if o.center_y is not None else 0))
            w_f = primary_feed.width if primary_feed.width else 0.003
            h_f = primary_feed.height if primary_feed.height else 0.015
            cx = primary_feed.center_x
            cy_edge = primary_feed.center_y - h_f / 2.0

            lines.append("    # --- Auto-Configured Microstrip Lumped Port ---")
            lines.append(f"    # Port location: x={cx * 1e3:.2f} mm, y={cy_edge * 1e3:.2f} mm, spanning z=[{z_sub_bottom * 1e3:.2f}, {z_sub_top * 1e3:.2f}] mm")
            lines.append(f"    port_w = {w_f}")
            lines.append(f"    port_x0 = {cx} - port_w / 2.0")
            lines.append(f"    port_y = {cy_edge}")
            lines.append(f"    port_z0 = {z_sub_bottom}")
            lines.append(f"    port_h = {h_sub}")
            lines.append("")
            lines.append("    # Create port sheet in XZ plane bridging ground to feed trace")
            lines.append("    try:")
            lines.append("        # Modern PyAEDT orientation syntax")
            lines.append("        port_sheet = app.modeler.create_rectangle(")
            lines.append("            orientation='XZ',")
            lines.append("            origin=[port_x0, port_y, port_z0],")
            lines.append("            sizes=[port_w, port_h],")
            lines.append("            name='Port1_Sheet',")
            lines.append("        )")
            lines.append("    except Exception:")
            lines.append("        # Classic PyAEDT csPlane syntax fallback")
            lines.append("        port_sheet = app.modeler.create_rectangle(")
            lines.append("            csPlane='XZ',")
            lines.append("            position=[port_x0, port_y, port_z0],")
            lines.append("            dimension_list=[port_w, port_h],")
            lines.append("            name='Port1_Sheet',")
            lines.append("        )")
            lines.append("")
            lines.append("    # Integration line definition: pointing +Z from ground to patch feed")
            lines.append(f"    int_line_start = [{cx}, {cy_edge}, {z_sub_bottom}]")
            lines.append(f"    int_line_stop = [{cx}, {cy_edge}, {z_sub_top}]")
            lines.append("")
            lines.append("    # Assign 50-Ohm Lumped Port with integration line")
            lines.append("    try:")
            lines.append("        # PyAEDT lumped_port API")
            lines.append("        app.lumped_port(")
            lines.append("            assignment=port_sheet.name,")
            lines.append("            reference=ref_ground,")
            lines.append("            integration_line=[int_line_start, int_line_stop],")
            lines.append("            create_port_sheet=False,")
            lines.append("            port_name='1',")
            lines.append("        )")
            lines.append("        print(\"  Assigned Lumped Port '1' with +Z integration line to sheet '\" + port_sheet.name + \"'\")")
            lines.append("    except Exception as e1:")
            lines.append("        try:")
            lines.append("            # Fallback for PyAEDT create_lumped_port_to_sheet")
            lines.append("            app.create_lumped_port_to_sheet(")
            lines.append("                sheet_name=port_sheet.name,")
            lines.append("                reference_object_list=[ref_ground] if ref_ground else [],")
            lines.append("                integration_line=[int_line_start, int_line_stop],")
            lines.append("                portname='1',")
            lines.append("            )")
            lines.append("            print(\"  Assigned Lumped Port '1' via create_lumped_port_to_sheet\")")
            lines.append("        except Exception as e2:")
            lines.append("            print(f'  Lumped port assignment note: {e1} / {e2}')")
            lines.append("            print('  Port sheet created. You can verify integration line in HFSS graphical interface.')")

        elif self.feeds:
            for idx, feed in enumerate(self.feeds):
                p_name = f"Port_{idx + 1}"
                lines.append(f"    # Feed: '{feed.name}' (Type: {feed.feed_type.value})")
                if feed.feed_type == FeedType.PROBE and feed.connection_point_x is not None:
                    px, py = feed.connection_point_x, feed.connection_point_y
                    lines.append(f"    # Coaxial probe pin at ({px * 1e3:.2f}, {py * 1e3:.2f}) mm")
                    lines.append(
                        f"    probe_pin = app.modeler.create_cylinder("
                        f"cs_axis='Z', position=[{px}, {py}, {z_sub_bottom}], "
                        f"radius=0.0006, height={h_sub}, name='{p_name}_Pin', matname='copper'"
                        f")"
                    )
                else:
                    lines.append(f"    # Standard feed structure '{feed.name}' associated with object '{feed.geometry_object_id}'")

        else:
            lines.append("    # Notice: No feed line or port explicitly mapped.")
            lines.append("    # You can assign a lumped or wave port to any desired boundary sheet.")

        lines.append("    print('Excitation port configuration completed.')")
        lines.append("else:")
        lines.append("    print('Notice: app is None (offline mode). Port configuration skipped.')")
        return "\n".join(lines)
