# -*- coding: utf-8 -*-
"""Material assignment and creation code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import Dict, List
from anton.models.geometry_schema import GeometryProject, MaterialRef


class MaterialCodeGenerator:
    """Generates PyAEDT code to verify, create, and assign materials in HFSS."""

    # Common built-in HFSS material name mappings (case-insensitive lookup)
    STANDARD_HFSS_MATERIALS: Dict[str, str] = {
        "copper": "copper",
        "aluminium": "aluminum",
        "aluminum": "aluminum",
        "silver": "silver",
        "gold": "gold",
        "vacuum": "vacuum",
        "air": "air",
        "fr4": "FR4_epoxy",
        "fr4_epoxy": "FR4_epoxy",
        "teflon": "Teflon (tm)",
    }

    def __init__(self, project: GeometryProject) -> None:
        self.project = project

    def generate_material_definitions_code(self) -> str:
        """Generate Python code block for defining all materials used in the project."""
        lines: List[str] = [
            "# ===========================================================================",
            "# 2. MATERIAL DEFINITIONS & HFSS LIBRARY SYNCHRONIZATION",
            "# ===========================================================================",
            "print('Configuring materials in HFSS library...')",
            "material_name_map = {}  # Maps ANTON material ID to HFSS material name",
            "",
        ]

        for mat_id, mat in self.project.materials.items():
            clean_name = mat.name.replace(" ", "_").replace("/", "_").replace("-", "_")
            lower_name = mat.name.lower()

            lines.append(f"# Material: '{mat.name}' (Category: {mat.category})")

            # Check if this matches a built-in standard HFSS material
            if lower_name in self.STANDARD_HFSS_MATERIALS:
                hfss_builtin = self.STANDARD_HFSS_MATERIALS[lower_name]
                lines.append(f"if app is not None and app.materials.check_if_exists('{hfss_builtin}'):")
                lines.append(f"    material_name_map['{mat_id}'] = '{hfss_builtin}'")
                lines.append(f"    print(f\"Using built-in HFSS material: '{hfss_builtin}'\")")
                lines.append("else:")
                lines.append(f"    mat_name = '{clean_name}'")
                lines.append("    if app is not None and not app.materials.check_if_exists(mat_name):")
                lines.append("        new_mat = app.materials.add_material(mat_name)")
                if mat.category == "dielectric":
                    eps_r = mat.properties.get("relative_permittivity", 1.0)
                    tan_d = mat.properties.get("loss_tangent", 0.0)
                    lines.append(f"        new_mat.permittivity = {eps_r}")
                    lines.append(f"        new_mat.dielectric_loss_tangent = {tan_d}")
                    lines.append(f"        print(f\"Created custom dielectric material: '{{mat_name}}' (eps_r={eps_r}, tan_d={tan_d})\")")
                elif mat.category == "conductor":
                    cond = mat.properties.get("conductivity", 5.8e7)
                    lines.append(f"        new_mat.conductivity = {cond}")
                    lines.append(f"        print(f\"Created custom conductor material: '{{mat_name}}' (sigma={cond} S/m)\")")
                lines.append(f"    material_name_map['{mat_id}'] = mat_name")
            else:
                lines.append(f"mat_name = '{clean_name}'")
                lines.append("if app is not None and not app.materials.check_if_exists(mat_name):")
                lines.append("    new_mat = app.materials.add_material(mat_name)")
                if mat.category == "dielectric":
                    eps_r = mat.properties.get("relative_permittivity", 1.0)
                    tan_d = mat.properties.get("loss_tangent", 0.0)
                    lines.append(f"    new_mat.permittivity = {eps_r}")
                    lines.append(f"    new_mat.dielectric_loss_tangent = {tan_d}")
                    lines.append(f"    print(f\"Created custom dielectric material: '{{mat_name}}' (eps_r={eps_r}, tan_d={tan_d})\")")
                elif mat.category == "conductor":
                    cond = mat.properties.get("conductivity", 5.8e7)
                    lines.append(f"    new_mat.conductivity = {cond}")
                    lines.append(f"    print(f\"Created custom conductor material: '{{mat_name}}' (sigma={cond} S/m)\")")
                lines.append(f"material_name_map['{mat_id}'] = mat_name")

            # Support frequency-dependent table if present
            if "frequency_sweep" in mat.properties and isinstance(mat.properties["frequency_sweep"], dict):
                lines.append("    # Note: Frequency-dependent properties detected in ANTON metadata.")
                lines.append(f"    # Dataset: {mat.properties['frequency_sweep']}")

            lines.append("")

        lines.append("print(f'Successfully synchronized {len(material_name_map)} material(s) in HFSS.')")
        return "\n".join(lines)
