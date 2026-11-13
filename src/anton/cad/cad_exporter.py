# -*- coding: utf-8 -*-
"""CAD file exporter (STEP and STL) for ANTON."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

try:
    import cadquery as cq
    from cadquery import exporters
    CADQUERY_AVAILABLE = True
except ImportError:
    cq = None
    exporters = None
    CADQUERY_AVAILABLE = False

logger = logging.getLogger(__name__)


class CADExporter:
    """Exports 3D CAD solids and assemblies to industry-standard STEP and STL formats."""

    @staticmethod
    def export_step(
        solid_or_assembly: Union[cq.Workplane, cq.Assembly],
        path: Union[str, Path],
    ) -> Path:
        """Export solid or assembly to a STEP file (.step / .stp).

        Parameters
        ----------
        solid_or_assembly:
            CadQuery Workplane solid or cq.Assembly.
        path:
            Target file path.

        Returns
        -------
        Path:
            The written file path.
        """
        if not CADQUERY_AVAILABLE:
            raise ImportError("CadQuery is required to export STEP files.")

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(solid_or_assembly, cq.Assembly):
            solid_or_assembly.save(str(out_path), exportType="STEP")
        elif isinstance(solid_or_assembly, cq.Workplane):
            exporters.export(solid_or_assembly, str(out_path), exportType="STEP")
        else:
            raise TypeError(
                f"Expected cq.Workplane or cq.Assembly, got {type(solid_or_assembly)}"
            )

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise IOError(f"STEP export failed: output file '{out_path}' is empty or missing.")

        logger.info("Successfully exported STEP file: %s (%d bytes)", out_path, out_path.stat().st_size)
        return out_path

    @staticmethod
    def export_stl(
        solid_or_assembly: Union[cq.Workplane, cq.Assembly],
        path: Union[str, Path],
        tolerance: float = 1e-4,
        angular_tolerance: float = 0.1,
    ) -> Path:
        """Export solid or assembly to an STL mesh file (.stl).

        Parameters
        ----------
        solid_or_assembly:
            CadQuery Workplane solid or cq.Assembly.
        path:
            Target file path.
        tolerance:
            Linear deflection tolerance in metres.
        angular_tolerance:
            Angular deflection tolerance in radians.

        Returns
        -------
        Path:
            The written file path.
        """
        if not CADQUERY_AVAILABLE:
            raise ImportError("CadQuery is required to export STL files.")

        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(solid_or_assembly, cq.Assembly):
            solid_or_assembly.save(
                str(out_path),
                exportType="STL",
                tolerance=tolerance,
                angularTolerance=angular_tolerance,
            )
        elif isinstance(solid_or_assembly, cq.Workplane):
            exporters.export(
                solid_or_assembly,
                str(out_path),
                exportType="STL",
                tolerance=tolerance,
                angularTolerance=angular_tolerance,
            )
        else:
            raise TypeError(
                f"Expected cq.Workplane or cq.Assembly, got {type(solid_or_assembly)}"
            )

        if not out_path.exists() or out_path.stat().st_size == 0:
            raise IOError(f"STL export failed: output file '{out_path}' is empty or missing.")

        logger.info("Successfully exported STL file: %s (%d bytes)", out_path, out_path.stat().st_size)
        return out_path
