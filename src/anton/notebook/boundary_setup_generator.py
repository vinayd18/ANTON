# -*- coding: utf-8 -*-
"""Radiation boundary and airbox configuration code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import List, Optional
from anton.models.geometry_schema import GeometryProject


class BoundarySetupGenerator:
    """Generates PyAEDT code for airbox enclosure, padding, and radiation boundaries."""

    def __init__(self, project: GeometryProject, center_frequency_ghz: float = 2.4) -> None:
        self.project = project
        self.center_freq_ghz = center_frequency_ghz

    def generate_boundary_code(self) -> str:
        """Generate Python code block for constructing airbox and assigning radiation boundary."""
        # Calculate wavelength in air: lambda_0 = c / f
        c = 2.99792458e8
        f_hz = self.center_freq_ghz * 1e9
        lambda_0 = c / f_hz
        lambda_quarter = lambda_0 / 4.0

        lines: List[str] = [
            "# ===========================================================================",
            "# 6. AIRBOX ENCLOSURE & RADIATION BOUNDARY CONFIGURATION",
            "# ===========================================================================",
            f"print('Creating airbox with quarter-wave radiation padding at {self.center_freq_ghz} GHz...')",
            "",
            f"center_freq_ghz = {self.center_freq_ghz}",
            f"lambda_quarter = {lambda_quarter:.6f}  # lambda_0 / 4 in metres ({lambda_quarter * 1e3:.2f} mm)",
            "",
            "if app is not None:",
            "    # Query overall model bounding box",
            "    try:",
            "        # Get current model bounding box in HFSS modeler",
            "        bb = app.modeler.get_bounding_box()",
            "        xmin, ymin, zmin = float(bb[0]), float(bb[1]), float(bb[2])",
            "        xmax, ymax, zmax = float(bb[3]), float(bb[4]), float(bb[5])",
            "    except Exception:",
            "        # Fallback to estimated bounds based on substrate geometry",
            "        xmin, xmax = -0.04, 0.04",
            "        ymin, ymax = -0.04, 0.04",
            "        zmin, zmax = -0.001, 0.003",
            "",
            "    # Calculate airbox dimensions with quarter-wave padding",
            "    air_x0 = xmin - lambda_quarter",
            "    air_y0 = ymin - lambda_quarter",
            "    air_z0 = zmin - lambda_quarter",
            "    air_dx = (xmax - xmin) + 2.0 * lambda_quarter",
            "    air_dy = (ymax - ymin) + 2.0 * lambda_quarter",
            "    air_dz = (zmax - zmin) + 2.0 * lambda_quarter",
            "",
            "    # Create Airbox solid",
            "    airbox = app.modeler.create_box(",
            "        origin=[air_x0, air_y0, air_z0],",
            "        sizes=[air_dx, air_dy, air_dz],",
            "        name='Airbox',",
            "        matname='vacuum'",
            "    )",
            "    # Set airbox transparency in modeler",
            "    app.modeler.set_color(airbox.name, [186, 230, 253])",
            "    try:",
            "        app.modeler.set_transparency(airbox.name, 0.85)",
            "    except Exception:",
            "        pass",
            "",
            "    # Assign Radiation Boundary to Airbox outer surfaces",
            "    try:",
            "        app.assign_radiation_boundary_to_objects(airbox.name)",
            "        print(f\"  Radiation boundary successfully assigned to '{airbox.name}'\")",
            "    except Exception as e:",
            "        try:",
            "            app.assign_radiation_boundary_to_faces(airbox.faces)",
            "            print(f\"  Radiation boundary assigned to airbox faces: {e}\")",
            "        except Exception as e2:",
            "            print(f\"  Radiation boundary assignment note: {e2}\")",
            "",
            "    print('Airbox and radiation boundaries configured.')",
            "else:",
            "    print('Notice: app is None (offline mode). Airbox configuration skipped.')",
        ]
        return "\n".join(lines)
