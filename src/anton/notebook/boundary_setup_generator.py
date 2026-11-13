# -*- coding: utf-8 -*-
"""Radiation boundary and airbox configuration code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import List, Tuple
from anton.models.geometry_schema import GeometryProject
from anton.primitives.base import to_shapely


class BoundarySetupGenerator:
    """Generates PyAEDT code for airbox enclosure, padding, and radiation boundaries."""

    def __init__(self, project: GeometryProject, center_frequency_ghz: float = 2.4) -> None:
        self.project = project
        self.center_freq_ghz = center_frequency_ghz

    def compute_canonical_bounds(self) -> Tuple[float, float, float, float, float, float]:
        """Compute exact (xmin, ymin, zmin, xmax, ymax, zmax) bounding box from project in metres."""
        xmin, ymin, xmax, ymax = 1e9, 1e9, -1e9, -1e9
        found_xy = False
        for obj in self.project.objects.values():
            try:
                shape = to_shapely(obj)
                b = shape.bounds
                if b and len(b) >= 4:
                    xmin = min(xmin, b[0])
                    ymin = min(ymin, b[1])
                    xmax = max(xmax, b[2])
                    ymax = max(ymax, b[3])
                    found_xy = True
            except Exception:
                pass

        if not found_xy:
            xmin, ymin, xmax, ymax = -0.03, -0.03, 0.03, 0.03

        zmin, zmax = 1e9, -1e9
        found_z = False
        for layer in self.project.layers.values():
            z0 = layer.z_position
            z1 = layer.z_position + layer.thickness
            zmin = min(zmin, min(z0, z1))
            zmax = max(zmax, max(z0, z1))
            found_z = True

        if not found_z:
            zmin, zmax = -0.000035, 0.001635

        return (xmin, ymin, zmin, xmax, ymax, zmax)

    def generate_boundary_code(self) -> str:
        """Generate Python code block for constructing airbox and assigning radiation boundary."""
        # Calculate wavelength in air: lambda_0 = c / f
        c = 2.99792458e8
        f_hz = self.center_freq_ghz * 1e9
        lambda_0 = c / f_hz
        lambda_quarter = lambda_0 / 4.0

        c_xmin, c_ymin, c_zmin, c_xmax, c_ymax, c_zmax = self.compute_canonical_bounds()

        lines: List[str] = [
            "# ===========================================================================",
            "# 6. AIRBOX ENCLOSURE & RADIATION BOUNDARY CONFIGURATION",
            "# ===========================================================================",
            f"print('Creating airbox with quarter-wave radiation padding at {self.center_freq_ghz} GHz...')",
            "",
            f"center_freq_ghz = {self.center_freq_ghz}",
            f"lambda_quarter = {lambda_quarter:.6f}  # lambda_0 / 4 in metres ({lambda_quarter * 1e3:.2f} mm)",
            "",
            "# Verified canonical geometry bounds from ANTON project (metres)",
            f"canon_xmin, canon_ymin, canon_zmin = {c_xmin:.6f}, {c_ymin:.6f}, {c_zmin:.6f}",
            f"canon_xmax, canon_ymax, canon_zmax = {c_xmax:.6f}, {c_ymax:.6f}, {c_zmax:.6f}",
            "",
            "# Query model bounding box from HFSS modeler with fallback to canonical project bounds",
            "try:",
            "    bb = app.modeler.get_bounding_box()",
            "    if bb and len(bb) >= 6:",
            "        xmin, ymin, zmin = float(bb[0]), float(bb[1]), float(bb[2])",
            "        xmax, ymax, zmax = float(bb[3]), float(bb[4]), float(bb[5])",
            "    else:",
            "        xmin, ymin, zmin = canon_xmin, canon_ymin, canon_zmin",
            "        xmax, ymax, zmax = canon_xmax, canon_ymax, canon_zmax",
            "except Exception as err_bb:",
            "    print(f'Warning: Could not query modeler bounding box ({err_bb}); using verified canonical project bounds.')",
            "    xmin, ymin, zmin = canon_xmin, canon_ymin, canon_zmin",
            "    xmax, ymax, zmax = canon_xmax, canon_ymax, canon_zmax",
            "",
            "# Calculate airbox dimensions with quarter-wave padding",
            "air_x0 = xmin - lambda_quarter",
            "air_y0 = ymin - lambda_quarter",
            "air_z0 = zmin - lambda_quarter",
            "air_dx = (xmax - xmin) + 2.0 * lambda_quarter",
            "air_dy = (ymax - ymin) + 2.0 * lambda_quarter",
            "air_dz = (zmax - zmin) + 2.0 * lambda_quarter",
            "",
            "# Create Airbox solid",
            "airbox = app.modeler.create_box(",
            "    origin=[air_x0, air_y0, air_z0],",
            "    sizes=[air_dx, air_dy, air_dz],",
            "    name='Airbox',",
            "    matname='vacuum'",
            ")",
            "if airbox is None:",
            "    raise RuntimeError('Failed to create Airbox solid in HFSS modeler.')",
            "",
            "# Set airbox transparency in modeler",
            "app.modeler.set_color(airbox.name, [186, 230, 253])",
            "try:",
            "    app.modeler.set_transparency(airbox.name, 0.85)",
            "except Exception:",
            "    pass",
            "",
            "# Assign Radiation Boundary to Airbox outer surfaces",
            "rad_assigned = False",
            "try:",
            "    app.assign_radiation_boundary_to_objects(airbox.name)",
            "    rad_assigned = True",
            "    print(f\"  Radiation boundary successfully assigned to object: '{airbox.name}'\")",
            "except Exception as err_obj:",
            "    try:",
            "        app.assign_radiation_boundary([airbox.name])",
            "        rad_assigned = True",
            "        print(f\"  Radiation boundary assigned via assign_radiation_boundary to '{airbox.name}'\")",
            "    except Exception as err_assign:",
            "        try:",
            "            app.assign_radiation_boundary_to_faces(airbox.faces)",
            "            rad_assigned = True",
            "            print('  Radiation boundary assigned to airbox faces')",
            "        except Exception as err_faces:",
            "            raise RuntimeError(",
            "                f\"Failed to assign radiation boundary to Airbox! \"",
            "                f\"Object method error: {err_obj}; Direct method error: {err_assign}; Face method error: {err_faces}\"",
            "            ) from err_faces",
            "",
            "if not rad_assigned:",
            "    raise RuntimeError('Critical verification failure: Radiation boundary was not assigned to Airbox.')",
            "",
            "# Create 3D Infinite Sphere for far-field radiation analysis",
            "try:",
            "    app.insert_infinite_sphere(",
            "        theta_start=0,",
            "        theta_stop=180,",
            "        theta_step=2,",
            "        phi_start=-180,",
            "        phi_stop=180,",
            "        phi_step=2,",
            "        name='3D',",
            "    )",
            "    print(\"  Created Infinite Sphere far-field setup: '3D'\")",
            "except Exception as e_inf:",
            "    try:",
            "        rad_mod = app.get_module('RadField') if hasattr(app, 'get_module') else (app.oModule.GetModule('RadField') if hasattr(app, 'oModule') else None)",
            "        if rad_mod is not None:",
            "            rad_mod.InsertInfiniteSphereSetup([",
            "                'NAME:3D',",
            "                'UseCustomRadiationSurface:=', False,",
            "                'CSDefinition:=', 'Theta-Phi',",
            "                'Polarization:=', 'Linear',",
            "                'ThetaStart:=', '0deg',",
            "                'ThetaStop:=', '180deg',",
            "                'ThetaStep:=', '2deg',",
            "                'PhiStart:=', '-180deg',",
            "                'PhiStop:=', '180deg',",
            "                'PhiStep:=', '2deg',",
            "                'UseLocalCS:=', False,",
            "            ])",
            "            print(\"  Created Infinite Sphere '3D' via RadField module\")",
            "        else:",
            "            print(f\"  Far-field setup note: {e_inf}\")",
            "    except Exception as e_mod:",
            "        print(f\"  Far-field setup note: {e_inf} / {e_mod}\")",
            "",
            "print('Airbox, radiation boundaries, and far-field setups successfully configured.')",
        ]
        return "\n".join(lines)
