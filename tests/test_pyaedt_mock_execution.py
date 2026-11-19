# -*- coding: utf-8 -*-
"""Mock-based execution and API signature verification test suite for ANTON HFSS notebooks.

Executes generated notebook code cells against a mock PyAEDT environment to verify:
1. Exact API method names, parameter keywords, and signatures.
2. Zero calls to non-existent PyAEDT methods (e.g. extrude_sheet, check_if_exists).
3. Correct integration line vectors and port sheet orientations.
4. Correct Modal solution and setup types.
5. Infinite sphere far-field creation.
6. Authentic result extraction and derived metrics calculation.
7. Multi-hole preservation and Boolean regression.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pytest

from anton.models.geometry_schema import (
    AntennaConfig,
    GeometryObject,
    GeometryProject,
    LayerDef,
    MaterialRef,
    VertexDef,
)
from anton.notebook import NotebookGenerator
from anton.operations.boolean import boolean_difference, boolean_union
from anton.primitives.base import to_shapely


# ---------------------------------------------------------------------------
# High-Fidelity Mock PyAEDT Hierarchy
# ---------------------------------------------------------------------------

class MockObject3d:
    def __init__(self, name: str, matname: Optional[str] = None):
        self.name = name
        self.matname = matname
        self.faces = [f"{name}_face_{i}" for i in range(6)]


class MockMaterial:
    def __init__(self, name: str):
        self.name = name
        self.permittivity = 1.0
        self.dielectric_loss_tangent = 0.0
        self.conductivity = 0.0
        self.updated = False

    def update(self) -> None:
        self.updated = True


class MockMaterials:
    def __init__(self):
        self._mats: Dict[str, MockMaterial] = {
            "copper": MockMaterial("copper"),
            "FR4_epoxy": MockMaterial("FR4_epoxy"),
            "vacuum": MockMaterial("vacuum"),
            "air": MockMaterial("air"),
            "aluminum": MockMaterial("aluminum"),
        }

    def checkifmaterialexists(self, name: str) -> bool:
        return name in self._mats

    def add_material(self, name: str) -> MockMaterial:
        mat = MockMaterial(name)
        self._mats[name] = mat
        return mat

    def __getitem__(self, name: str) -> MockMaterial:
        return self._mats[name]

    def __contains__(self, name: str) -> bool:
        return name in self._mats


class MockSweep:
    def __init__(self, name: str, start: float, stop: float, points: int):
        self.name = name
        self.start = start
        self.stop = stop
        self.points = points


class MockSetup:
    def __init__(self, name: str, setup_type: str = "HFSSDrivenModal"):
        self.name = name
        self.setup_type = setup_type
        self.props: Dict[str, Any] = {}
        self.sweeps: Dict[str, MockSweep] = {}

    def create_frequency_sweep(
        self,
        name: str,
        unit: str = "GHz",
        start_frequency: float = 1.8,
        stop_frequency: float = 3.0,
        num_of_freq_points: int = 201,
        sweep_type: str = "Interpolating",
    ) -> MockSweep:
        sw = MockSweep(name, start_frequency, stop_frequency, num_of_freq_points)
        self.sweeps[name] = sw
        return sw


class MockModeler:
    def __init__(self):
        self.model_units = "meter"
        self.objects: Dict[str, MockObject3d] = {}
        self.swept_objects: List[dict] = []
        self.subtracted_objects: List[dict] = []
        self.rectangles: List[dict] = []

    @property
    def object_list(self) -> List[MockObject3d]:
        return list(self.objects.values())

    @property
    def object_names(self) -> List[str]:
        return list(self.objects.keys())

    def create_box(self, origin: list, sizes: list, name: str, matname: str = "vacuum") -> MockObject3d:
        obj = MockObject3d(name, matname)
        self.objects[name] = obj
        return obj

    def create_cylinder(self, cs_axis: str, position: list, radius: float, height: float, name: str, matname: str = "vacuum") -> MockObject3d:
        obj = MockObject3d(name, matname)
        self.objects[name] = obj
        return obj

    def create_polyline(self, points: list, close_surface: bool = True, cover_surface: bool = True, name: str = "Poly", matname: str = "vacuum") -> MockObject3d:
        obj = MockObject3d(name, matname)
        self.objects[name] = obj
        return obj

    def create_rectangle(self, orientation: str = "XZ", origin: list = None, sizes: list = None, name: str = "Rect", **kwargs) -> MockObject3d:
        obj = MockObject3d(name)
        self.objects[name] = obj
        self.rectangles.append({"name": name, "orientation": orientation, "origin": origin, "sizes": sizes})
        return obj

    def create_ellipse(self, cs_plane: str = "XY", center: list = None, major_radius: float = 0.01, ratio: float = 1.0, name: str = "Ellipse", **kwargs) -> MockObject3d:
        obj = MockObject3d(name)
        self.objects[name] = obj
        return obj

    def sweep_along_vector(self, assignment: Any, vector: list) -> bool:
        assert len(vector) == 3, f"sweep_along_vector expects a 3-element vector, got {vector}"
        name = assignment if isinstance(assignment, str) else getattr(assignment, "name", str(assignment))
        self.swept_objects.append({"name": name, "vector": vector})
        return True

    def subtract(self, blank_list: list, tool_list: list, keep_originals: bool = False) -> bool:
        self.subtracted_objects.append({"blank": blank_list, "tools": tool_list, "keep": keep_originals})
        return True

    def set_color(self, name: str, color: list) -> None:
        pass

    def set_transparency(self, name: str, val: float) -> None:
        pass


class MockMesh:
    def __init__(self):
        self.length_meshes: List[dict] = []

    def assign_length_mesh(self, names: list, isinside: bool = False, maxlength: float = 0.005, name: str = "Mesh") -> None:
        self.length_meshes.append({"names": names, "maxlength": maxlength, "mesh_name": name})


class MockReportData:
    def __init__(self, freqs: np.ndarray, s11_db: np.ndarray, s11_complex: np.ndarray):
        self.sweeps = {"Freq": freqs}
        self._s11_db = s11_db
        self._s11_complex = s11_complex

    def data_db(self) -> list:
        return list(self._s11_db)

    def data_complex(self) -> list:
        return list(self._s11_complex)


class MockPost:
    def __init__(self):
        self.queried_expressions: List[str] = []

    def get_report_data(self, expression: str, setup_sweep_name: str = "Setup1 : Sweep1", context: Optional[str] = None) -> Optional[MockReportData]:
        self.queried_expressions.append(expression)
        if expression == "S(1,1)":
            freqs = np.linspace(2.0e9, 3.0e9, 101)
            # Resonant dip around 2.45 GHz
            s11_db = -3.0 - 22.0 / (1.0 + ((freqs - 2.45e9) / 20e6) ** 2)
            gamma_mag = 10.0 ** (s11_db / 20.0)
            phase = np.linspace(np.pi, -np.pi, len(freqs))
            s11_complex = gamma_mag * np.exp(1j * phase)
            return MockReportData(freqs, s11_db, s11_complex)
        elif expression == "dB(GainTotal)":
            return MockReportData(np.array([2.45e9]), np.array([7.2]), np.array([7.2 + 0j]))
        return None


class MockHfssApp:
    def __init__(self, projectname=None, designname="AntennaDesign", solution_type="Modal", **kwargs):
        self.project_name = projectname or "MockProject"
        self.design_name = designname
        self.solution_type = solution_type
        self.modeler = MockModeler()
        self.materials = MockMaterials()
        self.mesh = MockMesh()
        self.post = MockPost()
        self.setups: Dict[str, MockSetup] = {}
        self.ports: List[dict] = []
        self.radiation_boundaries: List[str] = []
        self.infinite_spheres: List[dict] = []

    def create_setup(self, name: str, setup_type: str = "HFSSDrivenModal") -> MockSetup:
        setup = MockSetup(name, setup_type)
        self.setups[name] = setup
        return setup

    def create_lumped_port_to_sheet(
        self,
        sheet_name: str,
        axisdir: list,
        portname: str = "1",
        impedance: float = 50.0,
        renormalize: bool = True,
        reference_object_list: list = None,
    ) -> bool:
        assert isinstance(axisdir, list) and len(axisdir) == 2, f"axisdir must be [start, stop], got {axisdir}"
        assert axisdir[0] != axisdir[1], "Integration line start and stop cannot be identical"
        self.ports.append({
            "type": "lumped_port_to_sheet",
            "sheet": sheet_name,
            "axisdir": axisdir,
            "portname": portname,
            "impedance": impedance,
            "reference": reference_object_list,
        })
        return True

    def lumped_port(self, signal: str, reference: str, integration_line: list, impedance: float = 50.0, **kwargs) -> bool:
        self.ports.append({
            "type": "lumped_port",
            "signal": signal,
            "reference": reference,
            "integration_line": integration_line,
        })
        return True

    def assign_radiation_boundary_to_objects(self, assignment: Any) -> bool:
        name = assignment if isinstance(assignment, str) else assignment[0]
        self.radiation_boundaries.append(name)
        return True

    def assign_radiation_boundary(self, assignment: Any) -> bool:
        name = assignment if isinstance(assignment, str) else assignment[0]
        self.radiation_boundaries.append(name)
        return True

    def insert_infinite_sphere(
        self,
        theta_start: float = 0,
        theta_stop: float = 180,
        theta_step: float = 2,
        phi_start: float = -180,
        phi_stop: float = 180,
        phi_step: float = 2,
        name: str = "3D",
    ) -> bool:
        self.infinite_spheres.append({
            "name": name,
            "theta": [theta_start, theta_stop, theta_step],
            "phi": [phi_start, phi_stop, phi_step],
        })
        return True

    def save_project(self) -> None:
        pass

    def release_desktop(self, close_projects: bool = False, close_desktop: bool = False) -> None:
        pass


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestPyAEDTMockExecution:
    """Executes the notebook generator output against MockHfssApp."""

    @pytest.mark.parametrize("example_name", [
        "rectangular_patch",
        "circular_patch",
        "triangular_patch",
        "hexagonal_patch",
        "u_slot_patch",
        "inset_feed_patch",
        "annular_patch",
        "custom_polygon_patch",
    ])
    def test_mock_execution_of_generated_code(self, example_name: str) -> None:
        json_path = Path("examples") / f"{example_name}.json"
        assert json_path.exists(), f"Canonical JSON {json_path} must exist"

        with open(json_path, "r", encoding="utf-8") as f:
            proj_dict = json.load(f)

        project = GeometryProject(**proj_dict)
        generator = NotebookGenerator(project=project, center_frequency_ghz=2.45)
        nb = generator.generate_notebook()

        # Build mock execution environment
        mock_app = MockHfssApp(designname=project.project_name)
        exec_globals = {
            "app": mock_app,
            "np": np,
            "math": __import__("math"),
            "json": json,
            "Path": Path,
            "plt": type("MockPlt", (), {"subplots": lambda *a, **kw: (None, [type("MockAx", (), {"plot": lambda *a, **k: None, "axhline": lambda *a, **k: None, "set_xlabel": lambda *a, **k: None, "set_ylabel": lambda *a, **k: None, "set_title": lambda *a, **k: None, "grid": lambda *a, **k: None, "legend": lambda *a, **k: None, "set_ylim": lambda *a, **k: None}) for _ in range(3)]), "show": lambda: None, "tight_layout": lambda: None})(),
        }

        # Execute all notebook code cells except cell 0 (environment check with pip imports)
        for idx, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            source = cell.source
            # Skip environment check cell that imports live pyaedt
            if "import pyaedt" in source and "pip install pyaedt" in source:
                continue
            # Skip cell 4 if it re-instantiates Hfss live connection
            if "app = Hfss(" in source:
                # Modeler units must be set
                mock_app.modeler.model_units = "meter"
                continue
            # Skip manual solve cell
            if "app.analyze_setup" in source:
                continue

            try:
                exec(source, exec_globals)
            except Exception as e:
                pytest.fail(f"Execution failed in notebook for '{example_name}', cell #{idx + 1}:\n{e}\n\nCode:\n{source}")

        # Assertions on mock environment state after full execution:
        # 1. Modeler created solids
        assert len(mock_app.modeler.objects) >= 3, f"Expected at least 3 solids in modeler for {example_name}"

        # 2. Materials synchronized via checkifmaterialexists
        assert len(exec_globals.get("material_name_map", {})) >= 1

        # 3. Lumped port created with valid integration line
        assert len(mock_app.ports) == 1, f"Expected exactly 1 lumped port for {example_name}"
        port_info = mock_app.ports[0]
        assert port_info["type"] == "lumped_port_to_sheet"
        assert len(port_info["axisdir"]) == 2
        # Start and stop points have different Z coordinates
        z_start = port_info["axisdir"][0][2]
        z_stop = port_info["axisdir"][1][2]
        assert z_stop > z_start, f"Integration line must point from ground (+Z) to patch: {port_info['axisdir']}"

        # 4. Radiation boundary assigned
        assert len(mock_app.radiation_boundaries) >= 1
        assert "Airbox" in mock_app.radiation_boundaries[0]

        # 5. Far-field Infinite Sphere configured
        assert len(mock_app.infinite_spheres) == 1
        assert mock_app.infinite_spheres[0]["name"] == "3D"

        # 6. Solution setup created with DrivenModal
        assert "Setup1" in mock_app.setups
        assert mock_app.setups["Setup1"].setup_type == "HFSSDrivenModal"

        # 7. S-parameters extracted authentically without placeholders
        assert exec_globals.get("results_status") == "RESULTS_EXTRACTED"
        assert exec_globals.get("simulation_status") == "SIMULATION_COMPLETED"
        freqs_ghz = exec_globals.get("freqs_ghz")
        assert len(freqs_ghz) > 0
        s11_db = exec_globals.get("s11_db")
        assert len(s11_db) > 0
        vswr = exec_globals.get("vswr")
        assert len(vswr) > 0
        assert np.all(vswr >= 1.0), "VSWR must be >= 1.0"


class TestMultiHoleBooleanPreservation:
    """Verifies that arbitrary multiple holes are preserved through Boolean difference and CAD extrusion."""

    def test_multi_hole_preservation(self) -> None:
        # Create a base patch with TWO distinct rectangular cutouts
        base_obj = GeometryObject(
            id="base_patch",
            name="BasePatch",
            object_type="rectangle",
            layer_id="patch_layer",
            material_id="cu",
            center_x=0.0,
            center_y=0.0,
            width=0.04,
            height=0.04,
        )
        hole1 = GeometryObject(
            id="hole_left",
            name="HoleLeft",
            object_type="rectangle",
            layer_id="patch_layer",
            material_id="cu",
            center_x=-0.01,
            center_y=0.0,
            width=0.005,
            height=0.01,
        )
        hole2 = GeometryObject(
            id="hole_right",
            name="HoleRight",
            object_type="rectangle",
            layer_id="patch_layer",
            material_id="cu",
            center_x=0.01,
            center_y=0.0,
            width=0.005,
            height=0.01,
        )

        res = boolean_difference(base_obj, [hole1, hole2], name="DualSlotPatch", layer_id="patch_layer", material_id="cu")

        # 1. GeometryObject schema checks
        assert len(res.inner_holes) == 2, f"Expected 2 inner holes, got {len(res.inner_holes)}"
        assert len(res.inner_vertices) > 0, "inner_vertices should contain primary hole"

        # 2. Shapely polygon conversion check
        poly = to_shapely(res)
        assert len(poly.interiors) == 2, f"Expected 2 interior rings in Shapely polygon, got {len(poly.interiors)}"

        # 3. Area check: Base (0.0016 m2) - 2 * (0.00005 m2) = 0.0015 m2
        expected_area = 0.04 * 0.04 - 2 * (0.005 * 0.01)
        assert pytest.approx(poly.area, rel=1e-4) == expected_area


class TestFeedLineBoundaryTermination:
    """Verifies that all 8 canonical antennas have feed lines reaching the substrate boundary."""

    @pytest.mark.parametrize("example_name", [
        "rectangular_patch",
        "circular_patch",
        "triangular_patch",
        "hexagonal_patch",
        "u_slot_patch",
        "inset_feed_patch",
        "annular_patch",
        "custom_polygon_patch",
    ])
    def test_feed_touches_substrate_edge(self, example_name: str) -> None:
        json_path = Path("examples") / f"{example_name}.json"
        with open(json_path, "r", encoding="utf-8") as f:
            proj_dict = json.load(f)

        project = GeometryProject(**proj_dict)
        # Find substrate bounds
        sub_obj = next(o for o in project.objects.values() if "sub" in (o.name or "").lower())
        sub_shape = to_shapely(sub_obj)
        sub_minx, sub_miny, sub_maxx, sub_maxy = sub_shape.bounds

        # Find feed line
        feed_obj = next(o for o in project.objects.values() if "feed" in (o.name or "").lower())
        feed_shape = to_shapely(feed_obj)
        feed_minx, feed_miny, feed_maxx, feed_maxy = feed_shape.bounds

        # Feed line must touch at least one of the 4 outer edges of substrate
        touches_bottom = abs(feed_miny - sub_miny) < 1e-5
        touches_top = abs(feed_maxy - sub_maxy) < 1e-5
        touches_left = abs(feed_minx - sub_minx) < 1e-5
        touches_right = abs(feed_maxx - sub_maxx) < 1e-5

        assert touches_bottom or touches_top or touches_left or touches_right, (
            f"Antenna '{example_name}': Feed line bounds [{feed_minx}, {feed_miny}, {feed_maxx}, {feed_maxy}] "
            f"do not reach substrate bounds [{sub_minx}, {sub_miny}, {sub_maxx}, {sub_maxy}]!"
        )

