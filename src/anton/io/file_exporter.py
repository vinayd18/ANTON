# -*- coding: utf-8 -*-
"""Unified multi-format file exporter for ANTON.

Coordinates export of canonical antenna geometry to JSON, SVG, PNG, STEP, and STL formats.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Union

from anton.cad.cad_exporter import CADExporter
from anton.cad.solid_generator import SolidGenerator
from anton.io.json_exporter import export_project_json
from anton.models.geometry_schema import GeometryProject
from anton.visualization.geometry_renderer import GeometryRenderer

logger = logging.getLogger(__name__)


class FileExporter:
    """Unified file export interface for 2D, 3D, and data representations."""

    @staticmethod
    def export_json(project: GeometryProject, path: Union[str, Path]) -> Path:
        """Export canonical JSON geometry representation."""
        return export_project_json(project, path)

    @staticmethod
    def export_svg(
        project: GeometryProject,
        path: Union[str, Path],
        **kwargs,
    ) -> Path:
        """Export 2D vector geometry to SVG."""
        renderer = GeometryRenderer(project)
        return renderer.save_svg(path, **kwargs)

    @staticmethod
    def export_png(
        project: GeometryProject,
        path: Union[str, Path],
        dpi: int = 300,
        **kwargs,
    ) -> Path:
        """Export 2D rendered layout to PNG."""
        renderer = GeometryRenderer(project)
        return renderer.save_png(path, dpi=dpi, **kwargs)

    @staticmethod
    def export_step(project: GeometryProject, path: Union[str, Path]) -> Path:
        """Export 3D CAD assembly to STEP."""
        generator = SolidGenerator(project)
        assembly = generator.generate_assembly()
        return CADExporter.export_step(assembly, path)

    @staticmethod
    def export_stl(project: GeometryProject, path: Union[str, Path]) -> Path:
        """Export 3D CAD assembly to STL."""
        generator = SolidGenerator(project)
        assembly = generator.generate_assembly()
        return CADExporter.export_stl(assembly, path)

    @classmethod
    def export_all(
        cls,
        project: GeometryProject,
        output_dir: Union[str, Path],
        base_name: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Export project across all supported formats (.json, .svg, .png, .step, .stl).

        Returns a dictionary mapping format name to written file Path.
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        prefix = base_name or project.project_name.lower().replace(" ", "_")

        results = {}
        # 1. JSON
        json_path = out_dir / f"{prefix}.json"
        results["json"] = cls.export_json(project, json_path)

        # 2. SVG
        svg_path = out_dir / f"{prefix}.svg"
        results["svg"] = cls.export_svg(project, svg_path)

        # 3. PNG
        png_path = out_dir / f"{prefix}.png"
        results["png"] = cls.export_png(project, png_path)

        # 4. STEP
        try:
            step_path = out_dir / f"{prefix}.step"
            results["step"] = cls.export_step(project, step_path)
        except Exception as e:
            logger.warning("STEP export skipped: %s", e)

        # 5. STL
        try:
            stl_path = out_dir / f"{prefix}.stl"
            results["stl"] = cls.export_stl(project, stl_path)
        except Exception as e:
            logger.warning("STL export skipped: %s", e)

        return results

