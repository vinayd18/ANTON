# -*- coding: utf-8 -*-
"""Comprehensive automated test suite for ANTON Stage 2 notebook generation and HFSS reproduction."""

import ast
import json
from pathlib import Path

import nbformat
import pytest

from anton.models.geometry_schema import (
    AntennaConfig,
    GeometryObject,
    GeometryProject,
    LayerDef,
    MaterialRef,
    ProjectMeta,
)
from anton.notebook import (
    BoundarySetupGenerator,
    FeedPortGenerator,
    HFSSCodeGenerator,
    MaterialCodeGenerator,
    NotebookGenerator,
    NotebookValidator,
    ResultExtractionGenerator,
    SolutionSetupGenerator,
    StackupCodeGenerator,
)


@pytest.fixture
def sample_project() -> GeometryProject:
    """Create a canonical test geometry project with substrate, ground, and patch."""
    return GeometryProject(
        project_name="TestPatch2400",
        geometry_id="test-geom-001",
        antenna=AntennaConfig(name="Test Rectangular Patch", configuration="rectangular"),
        metadata=ProjectMeta(description="Automated test antenna for Stage 2"),
        materials={
            "copper_mat": MaterialRef(id="copper_mat", name="Copper", category="conductor", properties={"conductivity": 5.8e7}),
            "rogers_mat": MaterialRef(id="rogers_mat", name="Rogers RT5880", category="dielectric", properties={"relative_permittivity": 2.2, "loss_tangent": 0.0009}),
        },
        layers={
            "gnd_layer": LayerDef(id="gnd_layer", name="Ground", layer_type="ground", z_position=-0.000035, thickness=0.000035, material_id="copper_mat", object_ids=["gnd_obj"]),
            "sub_layer": LayerDef(id="sub_layer", name="Substrate", layer_type="substrate", z_position=0.0, thickness=0.001575, material_id="rogers_mat", object_ids=["sub_obj"]),
            "patch_layer": LayerDef(id="patch_layer", name="Radiator", layer_type="patch", z_position=0.001575, thickness=0.000035, material_id="copper_mat", object_ids=["patch_obj", "feed_obj"]),
        },
        objects={
            "gnd_obj": GeometryObject(id="gnd_obj", name="GroundPlane", layer_id="gnd_layer", object_type="rectangle", center_x=0.0, center_y=0.0, width=0.08, height=0.08, material_id="copper_mat"),
            "sub_obj": GeometryObject(id="sub_obj", name="SubstrateBlock", layer_id="sub_layer", object_type="rectangle", center_x=0.0, center_y=0.0, width=0.08, height=0.08, material_id="rogers_mat"),
            "patch_obj": GeometryObject(id="patch_obj", name="RadiatorPatch", layer_id="patch_layer", object_type="rectangle", center_x=0.0, center_y=0.005, width=0.04, height=0.03, material_id="copper_mat"),
            "feed_obj": GeometryObject(id="feed_obj", name="FeedLine", layer_id="patch_layer", object_type="rectangle", center_x=0.0, center_y=-0.02, width=0.0048, height=0.02, material_id="copper_mat"),
        },
    )


class TestNotebookGeneration:
    """Tests for NotebookGenerator and its assembled structure."""

    def test_notebook_structure_and_metadata(self, sample_project: GeometryProject) -> None:
        generator = NotebookGenerator(
            project=sample_project,
            center_frequency_ghz=2.45,
            start_frequency_ghz=2.0,
            stop_frequency_ghz=3.0,
            num_frequency_points=101,
        )
        nb = generator.generate_notebook()

        assert isinstance(nb, nbformat.NotebookNode)
        assert nb.nbformat == 4
        assert "anton_metadata" in nb.metadata
        assert nb.metadata["anton_metadata"]["project_name"] == "TestPatch2400"
        assert nb.metadata["anton_metadata"]["center_frequency_ghz"] == 2.45

        # Check cells
        assert len(nb.cells) >= 20
        code_cells = [c for c in nb.cells if c.cell_type == "code"]
        md_cells = [c for c in nb.cells if c.cell_type == "markdown"]
        assert len(code_cells) >= 12
        assert len(md_cells) >= 12

    def test_ast_syntax_and_schema_validation(self, sample_project: GeometryProject, tmp_path: Path) -> None:
        generator = NotebookGenerator(sample_project, center_frequency_ghz=2.4)
        nb_path = tmp_path / "test_patch_hfss.ipynb"
        generator.save(nb_path)

        assert nb_path.exists()
        validator = NotebookValidator()
        result = validator.validate_file(nb_path, project=sample_project)

        assert result.is_valid is True
        assert result.syntax_valid is True
        assert len(result.errors) == 0
        assert result.code_cell_count >= 12

    def test_workflow_sections_coverage(self, sample_project: GeometryProject) -> None:
        generator = NotebookGenerator(sample_project, center_frequency_ghz=2.4)
        nb = generator.generate_notebook()
        validator = NotebookValidator()
        result = validator.validate_notebook(nb, project=sample_project)

        assert result.is_valid is True
        for sec, found in result.sections_found.items():
            assert found is True, f"Required section '{sec}' was not found in generated notebook"

    def test_custom_solution_parameters(self, sample_project: GeometryProject) -> None:
        generator = NotebookGenerator(
            project=sample_project,
            center_frequency_ghz=5.8,
            start_frequency_ghz=4.5,
            stop_frequency_ghz=7.0,
            num_frequency_points=251,
            max_passes=20,
            max_delta_s=0.015,
        )
        nb = generator.generate_notebook()
        all_code = "\n".join(c.source for c in nb.cells if c.cell_type == "code")

        assert "5.8GHz" in all_code or "5.8" in all_code
        assert "4.5" in all_code
        assert "7.0" in all_code
        assert "251" in all_code
        assert "20" in all_code
        assert "0.015" in all_code

    def test_derived_metrics_and_formulas(self, sample_project: GeometryProject) -> None:
        generator = NotebookGenerator(sample_project)
        nb = generator.generate_notebook()
        all_code = "\n".join(c.source for c in nb.cells if c.cell_type == "code")

        # Check mathematically consistent metric derivations
        assert "gamma_mag" in all_code
        assert "vswr" in all_code
        assert "z_in" in all_code
        assert "Z0 = 50.0" in all_code
        # Check export formats
        assert "s_parameters.csv" in all_code
        assert "simulation_summary.json" in all_code
        assert "antenna_s11.s1p" in all_code
        assert "# GHz S RI R 50.0" in all_code


class TestSubGenerators:
    """Individual unit tests for modular code generator components."""

    def test_material_code_generator(self, sample_project: GeometryProject) -> None:
        gen = MaterialCodeGenerator(sample_project)
        code = gen.generate_material_definitions_code()
        assert "app.materials" in code
        assert "Rogers_RT5880" in code
        assert "Copper" in code
        ast.parse(code)  # Verify syntax

    def test_stackup_code_generator(self, sample_project: GeometryProject) -> None:
        gen = StackupCodeGenerator(sample_project)
        code = gen.generate_stackup_code()
        assert "app.modeler.create_box" in code
        assert "SubstrateBlock" in code
        assert "GroundPlane" in code
        ast.parse(code)

    def test_hfss_code_generator(self, sample_project: GeometryProject) -> None:
        gen = HFSSCodeGenerator(sample_project)
        code = gen.generate_patch_and_feed_geometry_code()
        assert "RadiatorPatch" in code
        assert "FeedLine" in code
        ast.parse(code)

    def test_feed_port_generator(self, sample_project: GeometryProject) -> None:
        gen = FeedPortGenerator(sample_project)
        code = gen.generate_port_configuration_code()
        assert "port" in code.lower()
        ast.parse(code)

    def test_boundary_setup_generator(self, sample_project: GeometryProject) -> None:
        gen = BoundarySetupGenerator(sample_project, center_frequency_ghz=2.4)
        code = gen.generate_boundary_code()
        assert "Airbox" in code
        assert "assign_radiation_boundary" in code
        ast.parse(code)

    def test_solution_setup_generator(self, sample_project: GeometryProject) -> None:
        gen = SolutionSetupGenerator(sample_project, center_frequency_ghz=2.4)
        code = gen.generate_solution_setup_code()
        assert "Setup1" in code
        assert "Sweep1" in code
        ast.parse(code)

    def test_result_extraction_generator(self) -> None:
        gen = ResultExtractionGenerator(design_name="TestAntenna")
        solve_code = gen.generate_manual_solve_code()
        extract_code = gen.generate_result_extraction_code()
        plot_code = gen.generate_visualization_code()
        export_code = gen.generate_data_export_code()

        ast.parse(solve_code)
        ast.parse(extract_code)
        ast.parse(plot_code)
        ast.parse(export_code)


class TestNotebookValidator:
    """Tests for NotebookValidator error detection."""

    def test_detects_corrupt_syntax(self) -> None:
        nb = nbformat.v4.new_notebook()
        nb.cells = [
            nbformat.v4.new_code_cell("x = 10\nprint('hello')"),
            nbformat.v4.new_code_cell("def broken_func(\n  # syntax error"),
        ]
        validator = NotebookValidator()
        res = validator.validate_notebook(nb)
        assert res.is_valid is False
        assert res.syntax_valid is False
        assert any("SyntaxError" in err for err in res.errors)

    def test_detects_missing_file(self) -> None:
        validator = NotebookValidator()
        res = validator.validate_file(Path("non_existent_notebook_file.ipynb"))
        assert res.is_valid is False
        assert any("not found" in err for err in res.errors)

    def test_all_example_notebooks_exist_and_valid(self) -> None:
        examples_dir = Path("examples/notebooks")
        if not examples_dir.exists():
            pytest.skip("examples/notebooks directory does not exist")

        notebooks = list(examples_dir.glob("*.ipynb"))
        assert len(notebooks) >= 8, f"Expected at least 8 generated example notebooks, found {len(notebooks)}"

        validator = NotebookValidator()
        for nb_path in notebooks:
            res = validator.validate_file(nb_path)
            assert res.is_valid is True, f"Notebook '{nb_path.name}' failed validation: {res.errors}"
            assert res.syntax_valid is True
