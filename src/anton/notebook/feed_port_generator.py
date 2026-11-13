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

        # Find feed objects or feeds
        feed_layer = next((l for l in self.project.layers.values() if l.layer_type in {"feed", "patch"}), None)
        feed_objs = []
        if feed_layer:
            for oid in feed_layer.object_ids:
                o = self.project.objects.get(oid)
                if o and ("feed" in (o.name or "").lower() or o.layer_id == feed_layer.id):
                    feed_objs.append(o)

        if not self.feeds and feed_objs:
            # Default microstrip lumped port at lowest Y edge of feed object
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
            lines.append(
                "    port_sheet = app.modeler.create_rectangle("
                "csPlane='XZ', "
                "position=[port_x0, port_y, port_z0], "
                "dimension_list=[port_w, port_h], "
                "name='Port1_Sheet'"
                ")"
            )
            lines.append("")
            lines.append("    # Assign 50-Ohm Lumped Port with integration line pointing +Z from ground to patch")
            lines.append("    try:")
            lines.append("        # PyAEDT modern lumped_port API")
            lines.append(
                "        app.lumped_port("
                "assignment=port_sheet.name, "
                "reference=ref_ground, "
                "create_port_sheet=False, "
                "port_name='1'"
                ")"
            )
            lines.append("        print(\"  Assigned Lumped Port '1' to sheet '\" + port_sheet.name + \"'\")")
            lines.append("    except Exception as e:")
            lines.append("        print(f'  Lumped port assignment note: {e}')")
            lines.append("        print('  Port sheet created. You can verify integration line in HFSS graphical interface.')")

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
