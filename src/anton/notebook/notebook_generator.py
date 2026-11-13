# -*- coding: utf-8 -*-
"""Notebook generation engine for exporting canonical ANTON designs to executable PyAEDT / HFSS Jupyter Notebooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from anton.models.geometry_schema import GeometryProject
from anton.notebook.boundary_setup_generator import BoundarySetupGenerator
from anton.notebook.feed_port_generator import FeedPortGenerator
from anton.notebook.hfss_code_generator import HFSSCodeGenerator
from anton.notebook.material_code_generator import MaterialCodeGenerator
from anton.notebook.result_extraction_generator import ResultExtractionGenerator
from anton.notebook.solution_setup_generator import SolutionSetupGenerator
from anton.notebook.stackup_code_generator import StackupCodeGenerator


class NotebookGenerator:
    """Assembles and generates standalone, executable Jupyter Notebooks reproducing ANTON antenna designs in ANSYS HFSS via PyAEDT."""

    def __init__(
        self,
        project: GeometryProject,
        center_frequency_ghz: float = 2.4,
        start_frequency_ghz: float = 1.8,
        stop_frequency_ghz: float = 3.0,
        num_frequency_points: int = 201,
        max_passes: int = 15,
        max_delta_s: float = 0.02,
        aedt_version: Optional[str] = None,
        non_graphical: bool = False,
        new_desktop_session: bool = False,
    ) -> None:
        self.project = project
        self.center_freq_ghz = center_frequency_ghz
        self.start_freq_ghz = start_frequency_ghz
        self.stop_freq_ghz = stop_frequency_ghz
        self.num_points = num_frequency_points
        self.max_passes = max_passes
        self.max_delta_s = max_delta_s
        self.aedt_version = aedt_version
        self.non_graphical = non_graphical
        self.new_desktop_session = new_desktop_session

        # Store project identifiers safely
        self.project_name = getattr(self.project, "project_name", "AntennaDesign")
        self.geometry_id = getattr(self.project, "geometry_id", "geom_001")
        self.description = (
            getattr(self.project.metadata, "description", None)
            or getattr(self.project.antenna, "description", None)
            or "Universal microstrip antenna geometry exported from ANTON"
        )

        # Instantiate sub-generators
        self.mat_gen = MaterialCodeGenerator(self.project)
        self.stackup_gen = StackupCodeGenerator(self.project)
        self.hfss_gen = HFSSCodeGenerator(self.project)
        self.feed_gen = FeedPortGenerator(self.project, getattr(self.project, "feeds", None))
        self.boundary_gen = BoundarySetupGenerator(self.project, self.center_freq_ghz)
        self.solution_gen = SolutionSetupGenerator(
            self.project,
            center_frequency_ghz=self.center_freq_ghz,
            start_frequency_ghz=self.start_freq_ghz,
            stop_frequency_ghz=self.stop_freq_ghz,
            num_frequency_points=self.num_points,
            max_passes=self.max_passes,
            max_delta_s=self.max_delta_s,
        )
        self.result_gen = ResultExtractionGenerator(self.project_name)

    def generate_notebook(self) -> nbformat.NotebookNode:
        """Assemble the complete Jupyter Notebook node with markdown documentation and executable Python cells."""
        nb = new_notebook()
        nb.metadata = {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.10.0",
            },
            "anton_metadata": {
                "project_name": self.project_name,
                "geometry_id": self.geometry_id,
                "version": getattr(self.project.metadata, "schema_version", "1.0.0"),
                "center_frequency_ghz": self.center_freq_ghz,
                "generator": "ANTON Stage 2 Notebook Generation Engine",
            },
        }

        cells: List[Any] = []

        # =====================================================================
        # Section 0: Title and Documentation
        # =====================================================================
        title_md = f"""# ANTON Antenna Reproduction: {self.project_name}
**Automated PyAEDT / ANSYS HFSS Model Generation**

---

### Project Overview
- **Project Name:** `{self.project_name}`
- **Project ID:** `{self.geometry_id}`
- **Description:** {self.description}
- **Internal Units:** SI Metres ($m$)
- **Operating Center Frequency:** `{self.center_freq_ghz} GHz`
- **Simulation Frequency Sweep:** `{self.start_freq_ghz} - {self.stop_freq_ghz} GHz` ({self.num_points} points)
- **Number of Physical Layers:** {len(self.project.layers)}
- **Number of Geometry Objects:** {len(self.project.objects)}

---

### Standalone Execution Instructions
> **ANTON Architectural Principle:**
> ANTON operates completely independently of ANSYS HFSS. This notebook is a **self-contained script** intended to be executed in your local Jupyter environment.
>
> 1. Ensure you have **ANSYS Electronics Desktop (AEDT)** installed on your machine (versions 2022.1 - 2025.1 supported).
> 2. Ensure your Python environment has `pyaedt`, `numpy`, and `matplotlib`:
>    ```bash
>    pip install pyaedt numpy matplotlib
>    ```
> 3. Execute the cells sequentially from top to bottom.
> 4. Inspect the recreated 3D CAD model directly inside the ANSYS HFSS graphical interface.
> 5. Review the manual solve cell, run the electromagnetic analysis, and extract S-parameters, VSWR, and radiation patterns.
"""
        cells.append(new_markdown_cell(title_md))

        # =====================================================================
        # Section 1: Environment & Dependency Check
        # =====================================================================
        env_md = """## 1. Environment & Dependency Check
Verifies Python dependencies, PyAEDT availability, and system compatibility."""
        cells.append(new_markdown_cell(env_md))

        env_code = """# Check required packages
import sys

print(f"Python interpreter: {sys.executable}")
print(f"Python version: {sys.version.split()[0]}")

try:
    import pyaedt
    print(f"PyAEDT version: {pyaedt.__version__}")
except ImportError:
    print("WARNING: 'pyaedt' is not installed in this environment.")
    print("Please install PyAEDT to connect to ANSYS HFSS: pip install pyaedt")

try:
    import numpy as np
    print(f"NumPy version: {np.__version__}")
except ImportError:
    print("WARNING: 'numpy' is not installed: pip install numpy")

try:
    import matplotlib
    print(f"Matplotlib version: {matplotlib.__version__}")
except ImportError:
    print("WARNING: 'matplotlib' is not installed: pip install matplotlib")
"""
        cells.append(new_code_cell(env_code))

        # =====================================================================
        # Section 2: HFSS Desktop Connection
        # =====================================================================
        conn_md = """## 2. Launch / Connect to ANSYS HFSS Desktop
Connects to an existing HFSS session or launches a new AEDT desktop session using PyAEDT."""
        cells.append(new_markdown_cell(conn_md))

        version_str = f"'{self.aedt_version}'" if self.aedt_version else "None"
        conn_code = f"""import os
from pathlib import Path

try:
    from pyaedt import Hfss
except ImportError:
    Hfss = None
    print("PyAEDT not imported; mock/offline mode enabled.")

design_name = "{self.project_name}"
specified_version = {version_str}
non_graphical = {self.non_graphical}
new_desktop_session = {self.new_desktop_session}

app = None
if Hfss is not None:
    try:
        print(f"Connecting to ANSYS HFSS for design '{{design_name}}'...")
        app = Hfss(
            projectname=None,
            designname=design_name,
            solution_type="Terminal",
            specified_version=specified_version,
            non_graphical=non_graphical,
            new_desktop_session=new_desktop_session,
        )
        # Enforce SI Metres in the HFSS Modeler
        app.modeler.model_units = "meter"
        print("Successfully connected to ANSYS HFSS Desktop.")
        print(f"Active Project: {{app.project_name}} | Active Design: {{app.design_name}}")
        print(f"HFSS Modeler units set to: {{app.modeler.model_units}}")
    except Exception as e:
        print(f"Could not connect to live HFSS instance: {{e}}")
        print("Ensure ANSYS Electronics Desktop is running or valid AEDT licenses are configured.")
else:
    print("Please install pyaedt to execute this cell against ANSYS HFSS.")
"""
        cells.append(new_code_cell(conn_code))

        # =====================================================================
        # Section 3: Material Definitions
        # =====================================================================
        mat_md = """## 3. Material Definitions & HFSS Library Synchronization
Synchronizes substrate dielectrics, ground/patch conductors, and loss tangents with the HFSS material database."""
        cells.append(new_markdown_cell(mat_md))
        cells.append(new_code_cell(self.mat_gen.generate_material_definitions_code()))

        # =====================================================================
        # Section 4: Physical Stackup (Substrate & Ground)
        # =====================================================================
        stackup_md = """## 4. Physical Stackup: Substrate & Ground Plane Modeling
Creates the 3D dielectric substrate block and ground plane in HFSS with exact Z-stackup coordinates."""
        cells.append(new_markdown_cell(stackup_md))
        cells.append(new_code_cell(self.stackup_gen.generate_stackup_code()))

        # =====================================================================
        # Section 5: Radiator Patch, Feed & Cutouts
        # =====================================================================
        patch_md = """## 5. Radiating Patch, Feed Line & CSG Cutouts Modeling
Generates planar conductors, polygons, circles, rings, slots, and performs CSG subtractions in the HFSS modeler."""
        cells.append(new_markdown_cell(patch_md))
        cells.append(new_code_cell(self.hfss_gen.generate_patch_and_feed_geometry_code()))

        # =====================================================================
        # Section 6: Port & Excitation Configuration
        # =====================================================================
        port_md = """## 6. Feed & Excitation Port Configuration
Constructs port excitation sheets (Lumped Port, Wave Port, or Coaxial Probe) referencing the ground plane."""
        cells.append(new_markdown_cell(port_md))
        cells.append(new_code_cell(self.feed_gen.generate_port_configuration_code()))

        # =====================================================================
        # Section 7: Airbox & Radiation Boundary
        # =====================================================================
        airbox_md = f"""## 7. Airbox Enclosure & Radiation Boundary
Encloses the antenna structure in an airbox padded by $\\lambda_0 / 4$ at {self.center_freq_ghz} GHz with an ABC/PML radiation boundary."""
        cells.append(new_markdown_cell(airbox_md))
        cells.append(new_code_cell(self.boundary_gen.generate_boundary_code()))

        # =====================================================================
        # Section 8: Simulation Setup & Frequency Sweep
        # =====================================================================
        setup_md = f"""## 8. Solution Setup & Frequency Sweep
Configures adaptive mesh refinement setup at {self.center_freq_ghz} GHz and an interpolating frequency sweep ({self.start_freq_ghz} - {self.stop_freq_ghz} GHz)."""
        cells.append(new_markdown_cell(setup_md))
        cells.append(new_code_cell(self.solution_gen.generate_solution_setup_code()))

        # =====================================================================
        # Section 9: Manual Solve Execution
        # =====================================================================
        solve_md = """## 9. Manual Simulation Solve Execution
> **ANTON Manual Execution Gate:**
> Simulations are intentionally not executed automatically. Inspect your 3D design in ANSYS HFSS Desktop first.
> When ready, uncomment and execute the cell below."""
        cells.append(new_markdown_cell(solve_md))
        cells.append(new_code_cell(self.result_gen.generate_manual_solve_code()))

        # =====================================================================
        # Section 10: Result Extraction & Derived Metrics
        # =====================================================================
        extract_md = """## 10. Result Extraction, Impedance & Far-Field Metrics Derivation
Extracts $S_{11}$, derives $\\text{VSWR} = \\frac{1 + |\\Gamma|}{1 - |\\Gamma|}$, calculates complex input impedance $Z_{\\text{in}}$, and distinguishes Gain vs. Directivity vs. Realized Gain."""
        cells.append(new_markdown_cell(extract_md))
        cells.append(new_code_cell(self.result_gen.generate_result_extraction_code()))

        # =====================================================================
        # Section 11: Visualization Plots
        # =====================================================================
        vis_md = """## 11. Visualization: S-Parameters, VSWR, Impedance & Far-Field Radiation Patterns
Generates 2D Cartesian and polar plots for return loss, VSWR, complex input impedance, and elevation radiation cuts."""
        cells.append(new_markdown_cell(vis_md))
        cells.append(new_code_cell(self.result_gen.generate_visualization_code()))

        # =====================================================================
        # Section 12: Multi-Format Result Export
        # =====================================================================
        export_md = """## 12. Multi-Format Simulation Result Export
Exports simulation results and antenna performance summaries to:
1. `s_parameters.csv` (CSV format)
2. `simulation_summary.json` (Structured JSON summary)
3. `antenna_s11.s1p` (Standard Touchstone 1-Port format)"""
        cells.append(new_markdown_cell(export_md))
        cells.append(new_code_cell(self.result_gen.generate_data_export_code()))

        # =====================================================================
        # Section 13: Project Save & Desktop Release
        # =====================================================================
        save_md = """## 13. Project Save & Clean Session Release
Saves the ANSYS HFSS project file and cleanly releases the PyAEDT desktop session handle."""
        cells.append(new_markdown_cell(save_md))

        save_code = """# Save project and release desktop handle
if app is not None:
    try:
        app.save_project()
        print(f"HFSS Project '{app.project_name}' saved successfully.")
        # Release desktop handle without forcibly closing the user's GUI session
        app.release_desktop(close_projects=False, close_desktop=False)
        print("Released PyAEDT desktop handle cleanly.")
    except Exception as e:
        print(f"Project save note: {e}")
else:
    print("Offline mode: No active HFSS session to save.")
"""
        cells.append(new_code_cell(save_code))

        nb.cells = cells
        return nb

    def save(self, filepath: Union[str, Path]) -> Path:
        """Generate and save the notebook to the specified `.ipynb` path."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        nb = self.generate_notebook()
        with open(path, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)
        return path
