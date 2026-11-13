# -*- coding: utf-8 -*-
"""Layer and physical substrate stackup reconstruction code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import List
from anton.models.geometry_schema import GeometryProject, LayerDef


class StackupCodeGenerator:
    """Generates PyAEDT code for constructing substrate, ground plane, and dielectric stackup."""

    def __init__(self, project: GeometryProject) -> None:
        self.project = project

    def generate_stackup_code(self) -> str:
        """Generate Python code block for constructing substrate and ground plane solids."""
        lines: List[str] = [
            "# ===========================================================================",
            "# 3. DIELECTRIC SUBSTRATE & GROUND PLANE CONSTRUCTION",
            "# ===========================================================================",
            "print('Constructing physical layer stackup in HFSS modeler...')",
            "",
            "# Collect created modeler objects for verification",
            "hfss_objects = {}",
            "",
        ]

        # Sort layers by z_position ascending
        sorted_layers = sorted(self.project.layers.values(), key=lambda l: l.z_position)

        for layer in sorted_layers:
            if layer.layer_type in {"substrate", "ground"}:
                lines.append(f"# Layer: '{layer.name}' (Type: {layer.layer_type}, z={layer.z_position * 1e3:.4f} mm, t={layer.thickness * 1e3:.4f} mm)")

                for obj_id in layer.object_ids:
                    obj = self.project.objects.get(obj_id)
                    if not obj:
                        continue

                    obj_name = obj.name or f"{layer.name}_{obj.id[:6]}"
                    mat_id_str = f"material_name_map.get('{obj.material_id}', 'vacuum')"

                    if obj.object_type in {"rectangle", "square"} and obj.width and obj.height:
                        # Box origin at lower-left-bottom: [cx - w/2, cy - h/2, z0]
                        x0 = obj.center_x - obj.width / 2.0
                        y0 = obj.center_y - obj.height / 2.0
                        z0 = layer.z_position
                        t = layer.thickness if layer.thickness > 0 else 35e-6

                        lines.append(f"# Create rectangular solid for {obj_name}")
                        lines.append(
                            f"box_{obj_name} = app.modeler.create_box("
                            f"origin=[{x0}, {y0}, {z0}], "
                            f"sizes=[{obj.width}, {obj.height}, {t}], "
                            f"name='{obj_name}', "
                            f"matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"hfss_objects['{obj.id}'] = box_{obj_name}.name")
                        lines.append(f"print(f\"  Created box solid: '{{box_{obj_name}.name}}' for layer '{layer.name}'\")")

                    elif obj.object_type == "circle" and obj.radius:
                        z0 = layer.z_position
                        t = layer.thickness if layer.thickness > 0 else 35e-6
                        lines.append(f"# Create circular cylinder solid for {obj_name}")
                        lines.append(
                            f"cyl_{obj_name} = app.modeler.create_cylinder("
                            f"cs_axis='Z', "
                            f"position=[{obj.center_x}, {obj.center_y}, {z0}], "
                            f"radius={obj.radius}, "
                            f"height={t}, "
                            f"name='{obj_name}', "
                            f"matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"hfss_objects['{obj.id}'] = cyl_{obj_name}.name")
                        lines.append(f"print(f\"  Created cylinder solid: '{{cyl_{obj_name}.name}}' for layer '{layer.name}'\")")

                    elif obj.vertices:
                        # Extruded polygon
                        z0 = layer.z_position
                        t = layer.thickness if layer.thickness > 0 else 35e-6
                        pts_literal = [[v.x, v.y, z0] for v in obj.vertices]
                        lines.append(f"# Create polygon sheet and extrude for {obj_name}")
                        lines.append(f"pts_{obj_name} = {pts_literal}")
                        lines.append(
                            f"poly_{obj_name} = app.modeler.create_polyline("
                            f"points=pts_{obj_name}, close_surface=True, cover_surface=True, "
                            f"name='{obj_name}', matname={mat_id_str}"
                            f")"
                        )
                        lines.append(f"app.modeler.extrude_sheet(poly_{obj_name}.name, {t})")
                        lines.append(f"hfss_objects['{obj.id}'] = poly_{obj_name}.name")
                        lines.append(f"print(f\"  Created extruded polygon: '{{poly_{obj_name}.name}}' for layer '{layer.name}'\")")

                lines.append("")

        lines.append("print('Dielectric substrate and ground structure created successfully.')")
        return "\n".join(lines)

