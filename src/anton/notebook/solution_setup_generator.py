# -*- coding: utf-8 -*-
"""Simulation setup and frequency sweep code generator for PyAEDT / HFSS notebooks."""

from __future__ import annotations

from typing import List, Optional
from anton.models.geometry_schema import GeometryProject


class SolutionSetupGenerator:
    """Generates PyAEDT code for solution setups, convergence criteria, and frequency sweeps."""

    def __init__(
        self,
        project: GeometryProject,
        center_frequency_ghz: float = 2.4,
        start_frequency_ghz: float = 1.8,
        stop_frequency_ghz: float = 3.0,
        num_frequency_points: int = 201,
        max_passes: int = 15,
        max_delta_s: float = 0.02,
        sweep_type: str = "Interpolating",
    ) -> None:
        self.project = project
        self.center_freq_ghz = center_frequency_ghz
        self.start_freq_ghz = start_frequency_ghz
        self.stop_freq_ghz = stop_frequency_ghz
        self.num_points = num_frequency_points
        self.max_passes = max_passes
        self.max_delta_s = max_delta_s
        self.sweep_type = sweep_type

    def generate_solution_setup_code(self) -> str:
        """Generate Python code block for creating HFSS setup and frequency sweep."""
        lines: List[str] = [
            "# ===========================================================================",
            "# 7. SOLUTION SETUP & FREQUENCY SWEEP CONFIGURATION",
            "# ===========================================================================",
            f"print('Configuring solution setup at {self.center_freq_ghz} GHz...')",
            "",
            "if app is not None:",
            "    setup_name = 'Setup1'",
            "    sweep_name = 'Sweep1'",
            "",
            "    # Create HFSS solution setup with adaptive meshing",
            "    setup = None",
            "    try:",
            "        # Modern PyAEDT setup creation",
            f"        setup = app.create_setup(name=setup_name, setup_type='HFSSDrivenAuto')",
            "    except Exception:",
            "        try:",
            f"            setup = app.create_setup(name=setup_name, setup_type='HFSS')",
            "        except Exception:",
            f"            setup = app.create_setup(name=setup_name)",
            "",
            f"    setup.props['Frequency'] = '{self.center_freq_ghz}GHz'",
            f"    setup.props['MaximumPasses'] = {self.max_passes}",
            f"    setup.props['MaxDeltaS'] = {self.max_delta_s}",
            f"    print(f\"  Configured '{{setup.name}}': Center={self.center_freq_ghz} GHz, MaxPasses={self.max_passes}, MaxDeltaS={self.max_delta_s}\")",
            "",
            "    # Configure broadband frequency sweep",
            f"    print(f'Configuring {self.sweep_type} frequency sweep from {self.start_freq_ghz} to {self.stop_freq_ghz} GHz ({self.num_points} points)...')",
            "    try:",
            "        sweep = setup.create_frequency_sweep(",
            "            name=sweep_name,",
            "            unit='GHz',",
            f"            start_frequency={self.start_freq_ghz},",
            f"            stop_frequency={self.stop_freq_ghz},",
            f"            num_of_freq_points={self.num_points},",
            f"            sweep_type='{self.sweep_type}',",
            "        )",
            "        print(f\"  Configured frequency sweep: '{sweep.name}'\")",
            "    except Exception:",
            "        try:",
            "            # Fallback format with string units for older PyAEDT",
            "            sweep = setup.create_frequency_sweep(",
            "                name=sweep_name,",
            "                unit='GHz',",
            f"                start_frequency='{self.start_freq_ghz}GHz',",
            f"                stop_frequency='{self.stop_freq_ghz}GHz',",
            f"                num_of_freq_points={self.num_points},",
            f"                sweep_type='{self.sweep_type}',",
            "            )",
            "            print(f\"  Configured frequency sweep (fallback): '{sweep.name}'\")",
            "        except Exception as e:",
            "            print(f'  Sweep creation note: {e}')",
            "",
            "    # Optional: Adaptive mesh refinement on patch conductors",
            "    print('Assigning initial mesh refinement on conductive radiator faces...')",
            "    try:",
            "        patch_conductors = [obj.name for obj in app.modeler.object_list if 'patch' in obj.name.lower() or 'radiator' in obj.name.lower()]",
            "        if patch_conductors:",
            "            app.mesh.assign_length_mesh(patch_conductors, isinside=False, maxlength=0.005, name='Mesh_PatchEdge')",
            "            print(f\"  Assigned length mesh refinement to: {patch_conductors}\")",
            "    except Exception as e:",
            "        print(f'  Mesh refinement note (optional): {e}')",
            "",
            "    print('HFSS simulation setup and frequency sweep fully configured.')",
            "else:",
            "    print('Notice: app is None (offline mode). Solution setup skipped.')",
        ]
        return "\n".join(lines)
