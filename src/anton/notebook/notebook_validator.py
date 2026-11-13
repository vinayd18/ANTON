# -*- coding: utf-8 -*-
"""Notebook validator for checking syntax, schema, structure, and geometric consistency of generated PyAEDT notebooks."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import nbformat
from nbformat import NotebookNode

from anton.models.geometry_schema import GeometryProject


@dataclass
class NotebookValidationResult:
    """Structured result of notebook validation."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    cell_count: int = 0
    code_cell_count: int = 0
    markdown_cell_count: int = 0
    syntax_valid: bool = True
    sections_found: Dict[str, bool] = field(default_factory=dict)
    geometric_consistency: Dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        """Return a formatted human-readable summary of validation."""
        status = "PASSED" if self.is_valid else "FAILED"
        lines = [
            f"Notebook Validation Summary: {status}",
            f"  Total Cells: {self.cell_count} (Code: {self.code_cell_count}, Markdown: {self.markdown_cell_count})",
            f"  Python AST Syntax: {'VALID' if self.syntax_valid else 'SYNTAX ERRORS DETECTED'}",
        ]
        if self.sections_found:
            lines.append("  Detected Workflow Sections:")
            for sec, found in self.sections_found.items():
                mark = "[X]" if found else "[ ]"
                lines.append(f"    {mark} {sec}")
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"    - {err}")
        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    - {w}")
        return "\n".join(lines)


class NotebookValidator:
    """Validates generated Jupyter Notebooks for schema compliance, Python syntax, and design consistency."""

    REQUIRED_SECTIONS = [
        ("Environment & PyAEDT Setup", ["pyaedt", "Hfss"]),
        ("Material Definitions", ["materials", "add_material"]),
        ("Stackup & Substrate Modeling", ["substrate", "ground", "create_box"]),
        ("Patch Antenna Radiator Modeling", ["patch", "create_rectangle", "create_circle", "create_poly"]),
        ("Feed & Port Configuration", ["port", "create_lumped_port", "create_wave_port"]),
        ("Airbox & Radiation Boundary", ["airbox", "radiation", "create_open_region", "assign_radiation_boundary"]),
        ("Solution Setup & Frequency Sweep", ["setup", "sweep", "create_setup", "insert_frequency_sweep"]),
        ("Manual Simulation Trigger", ["analyze_setup"]),
        ("Result Extraction & Antenna Metrics", ["get_report_data", "vswr", "s11"]),
        ("Multi-Format Export (CSV, JSON, S1P)", ["csv", "json", ".s1p", "Touchstone"]),
    ]

    def validate_file(
        self,
        file_path: Union[str, Path],
        project: Optional[GeometryProject] = None,
    ) -> NotebookValidationResult:
        """Validate a notebook file on disk."""
        path = Path(file_path)
        if not path.exists():
            return NotebookValidationResult(
                is_valid=False,
                errors=[f"Notebook file not found: {path}"],
            )
        try:
            with open(path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as e:
            return NotebookValidationResult(
                is_valid=False,
                errors=[f"Failed to read/parse notebook file as valid JSON/nbformat: {e}"],
            )
        return self.validate_notebook(nb, project)

    def validate_notebook(
        self,
        notebook: NotebookNode,
        project: Optional[GeometryProject] = None,
    ) -> NotebookValidationResult:
        """Validate a NotebookNode object."""
        errors: List[str] = []
        warnings: List[str] = []
        sections_found: Dict[str, bool] = {}
        geometric_consistency: Dict[str, Any] = {}
        syntax_valid = True

        # 1. Validate against Jupyter Notebook v4 JSON schema
        try:
            nbformat.validate(notebook)
        except Exception as e:
            errors.append(f"nbformat JSON schema validation error: {e}")

        cells = notebook.get("cells", [])
        cell_count = len(cells)
        code_cells = [c for c in cells if c.get("cell_type") == "code"]
        md_cells = [c for c in cells if c.get("cell_type") == "markdown"]
        code_cell_count = len(code_cells)
        md_cell_count = len(md_cells)

        if cell_count == 0:
            errors.append("Notebook contains no cells.")

        # 2. Check Python syntax of all code cells
        for idx, cell in enumerate(code_cells):
            source = cell.get("source", "")
            if not source.strip():
                continue
            try:
                ast.parse(source)
            except SyntaxError as e:
                syntax_valid = False
                errors.append(
                    f"SyntaxError in code cell #{idx + 1} at line {e.lineno}: {e.msg} (text: {e.text!r})"
                )

        # 3. Check for required workflow sections across the entire notebook
        all_text = "\n".join(cell.get("source", "") for cell in cells).lower()
        for sec_name, keywords in self.REQUIRED_SECTIONS:
            found = any(kw.lower() in all_text for kw in keywords)
            sections_found[sec_name] = found
            if not found:
                warnings.append(f"Section or keywords for '{sec_name}' not detected in notebook.")

        # 4. Geometric & Project consistency checks (if project is provided)
        if project is not None:
            proj_name = getattr(project, "project_name", "").lower()
            if proj_name and proj_name not in all_text:
                warnings.append(f"Project name '{getattr(project, 'project_name', '')}' not referenced in notebook.")

            # Check layer presence
            found_layers = 0
            layers = getattr(project, "layers", {})
            for layer in layers.values():
                layer_id = getattr(layer, "id", "").lower()
                layer_name = getattr(layer, "name", "").lower()
                if (layer_id and layer_id in all_text) or (layer_name and layer_name in all_text):
                    found_layers += 1
            geometric_consistency["layers_in_project"] = len(layers)
            geometric_consistency["layers_found_in_notebook"] = found_layers

            # Check object count
            objs_found = 0
            objects = getattr(project, "objects", {})
            for obj in objects.values():
                obj_name = getattr(obj, "name", "").lower()
                if obj_name and obj_name in all_text:
                    objs_found += 1
            geometric_consistency["objects_in_project"] = len(objects)
            geometric_consistency["objects_found_in_notebook"] = objs_found

            # Check feeds
            feeds_found = 0
            feeds_list = getattr(project, "feeds", None) or getattr(project, "connections", [])
            for feed in feeds_list:
                feed_name = getattr(feed, "name", "").lower()
                if (feed_name and feed_name in all_text) or "port" in all_text:
                    feeds_found += 1
            geometric_consistency["feeds_in_project"] = len(feeds_list)
            geometric_consistency["feeds_found_in_notebook"] = feeds_found

        is_valid = (len(errors) == 0) and syntax_valid

        return NotebookValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cell_count=cell_count,
            code_cell_count=code_cell_count,
            markdown_cell_count=md_cell_count,
            syntax_valid=syntax_valid,
            sections_found=sections_found,
            geometric_consistency=geometric_consistency,
        )
