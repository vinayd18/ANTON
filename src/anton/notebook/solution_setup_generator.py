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
            "if app is None:",
            "    raise RuntimeError('Critical: app is None. No active HFSS session to configure solution setup.')",
            "",
            "setup_name = 'Setup1'",
            "sweep_name = 'Sweep1'",
            "",
            "# Create HFSS solution setup with adaptive meshing",
            "setup = None",
            "try:",
            "    setup = app.create_setup(name=setup_name, setup_type='HFSSDrivenModal')",
            "except Exception as e_modal:",
            "    try:",
            "        setup = app.create_setup(name=setup_name, setup_type='HFSS')",
            "    except Exception as e_hfss:",
            "        try:",
            "            setup = app.create_setup(name=setup_name)",
            "        except Exception as e_gen:",
            "            raise RuntimeError(",
            "                f\"Failed to create HFSS solution setup '{setup_name}'! \"",
            "                f\"HFSSDrivenModal error: {e_modal}; HFSS error: {e_hfss}; Generic error: {e_gen}\"",
            "            ) from e_gen",
            "",
            "if setup is None:",
            "    raise RuntimeError(f\"Failed to create HFSS solution setup '{setup_name}'.\")",
            "",
            f"setup.props['Frequency'] = '{self.center_freq_ghz}GHz'",
            f"setup.props['MaximumPasses'] = {self.max_passes}",
            f"setup.props['MaxDeltaS'] = {self.max_delta_s}",
            f"print(f\"  Configured '{{setup.name}}': Center={self.center_freq_ghz} GHz, MaxPasses={self.max_passes}, MaxDeltaS={self.max_delta_s}\")",
            "",
            "# Configure broadband frequency sweep",
            f"print('Configuring {self.sweep_type} frequency sweep from {self.start_freq_ghz} to {self.stop_freq_ghz} GHz ({self.num_points} points)...')",
            "sweep = None",
            "try:",
            "    sweep = setup.create_frequency_sweep(",
            "        name=sweep_name,",
            "        unit='GHz',",
            f"        start_frequency={self.start_freq_ghz},",
            f"        stop_frequency={self.stop_freq_ghz},",
            f"        num_of_freq_points={self.num_points},",
            f"        sweep_type='{self.sweep_type}',",
            "    )",
            "except Exception as e1:",
            "    try:",
            "        sweep = setup.create_frequency_sweep(",
            "            name=sweep_name,",
            "            unit='GHz',",
            f"            start_frequency='{self.start_freq_ghz}GHz',",
            f"            stop_frequency='{self.stop_freq_ghz}GHz',",
            f"            num_of_freq_points={self.num_points},",
            f"            sweep_type='{self.sweep_type}',",
            "        )",
            "    except Exception as e2:",
            "        raise RuntimeError(",
            "            f\"Failed to configure frequency sweep '{sweep_name}'! \"",
            "            f\"Primary method error: {e1}; Fallback method error: {e2}\"",
            "        ) from e2",
            "",
            "if sweep is None:",
            "    raise RuntimeError(f\"Failed to create frequency sweep '{sweep_name}'.\")",
            "",
            "print(f\"  Configured frequency sweep: '{sweep.name}'\")",
            "",
        ]

        # Identify canonical patch/radiator object names from project
        radiator_names = [
            obj.name for obj in self.project.objects.values()
            if obj.name and (
                (self.project.layers.get(obj.layer_id) and self.project.layers[obj.layer_id].layer_type in ("patch", "feed"))
                or any(k in obj.name.lower() for k in ("patch", "radiator", "disk", "ring", "feed"))
            )
        ]

        lines.extend([
            "# Optional: Adaptive mesh refinement on patch conductors",
            "print('Assigning initial mesh refinement on conductive radiator faces...')",
            "try:",
            f"    target_radiators = {radiator_names}",
            "    modeler_names = getattr(app.modeler, 'object_names', [o.name for o in app.modeler.object_list])",
            "    patch_conductors = [name for name in target_radiators if name in modeler_names]",
            "    if not patch_conductors:",
            "        patch_conductors = [obj.name for obj in app.modeler.object_list if any(k in obj.name.lower() for k in ('patch', 'radiator', 'disk', 'ring', 'feed'))]",
            "    if patch_conductors:",
            "        app.mesh.assign_length_mesh(patch_conductors, isinside=False, maxlength=0.005, name='Mesh_PatchEdge')",
            "        print(f\"  Assigned length mesh refinement to: {patch_conductors}\")",
            "except Exception as e:",
            "    print(f'  Mesh refinement note (optional): {e}')",
            "",
            "print('HFSS simulation setup and frequency sweep fully configured.')",
        ])
        return "\n".join(lines)
