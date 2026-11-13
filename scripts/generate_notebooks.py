# -*- coding: utf-8 -*-
"""Script to generate standalone PyAEDT/HFSS reproduction notebooks for all 8 example antennas."""

from __future__ import annotations

import json
from pathlib import Path

from anton.models.geometry_schema import GeometryProject
from anton.notebook.notebook_generator import NotebookGenerator
from anton.notebook.notebook_validator import NotebookValidator


def generate_all_example_notebooks() -> None:
    examples_dir = Path("examples")
    output_dir = examples_dir / "notebooks"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(examples_dir.glob("*.json"))
    validator = NotebookValidator()

    print(f"Generating HFSS reproduction notebooks for {len(json_files)} example antennas...")

    for jf in json_files:
        name = jf.stem
        nb_path = output_dir / f"{name}_hfss.ipynb"
        print(f"Loading '{jf}'...")
        with open(jf, "r", encoding="utf-8") as f:
            proj_dict = json.load(f)

        project = GeometryProject(**proj_dict)

        # Tune center frequencies appropriately if known, default 2.4 GHz
        center_freq = 2.4
        if "annular" in name:
            center_freq = 3.0
        elif "circular" in name:
            center_freq = 2.4
        elif "u_slot" in name:
            center_freq = 2.45

        generator = NotebookGenerator(
            project=project,
            center_frequency_ghz=center_freq,
            start_frequency_ghz=center_freq * 0.75,
            stop_frequency_ghz=center_freq * 1.25,
            num_frequency_points=201,
        )

        saved_path = generator.save(nb_path)
        print(f"Saved notebook: {saved_path}")

        # Validate generated notebook
        res = validator.validate_file(saved_path, project=project)
        print(f"Validation: {'PASSED' if res.is_valid else 'FAILED'} (Cells: {res.cell_count}, Code: {res.code_cell_count}, AST Syntax: {'OK' if res.syntax_valid else 'ERROR'})")
        if res.errors:
            for err in res.errors:
                print(f"  ERROR: {err}")
            raise RuntimeError(f"Generated notebook {saved_path} failed validation!")
        if res.warnings:
            for w in res.warnings:
                print(f"  WARNING: {w}")

    print("\nAll example notebooks successfully generated and validated!")


if __name__ == "__main__":
    generate_all_example_notebooks()

