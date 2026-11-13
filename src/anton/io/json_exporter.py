# -*- coding: utf-8 -*-
"""JSON exporter for ANTON canonical geometry models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from anton.models.geometry_schema import GeometryProject


def export_project_json(
    project: GeometryProject,
    path: Union[str, Path],
    indent: int = 2,
) -> Path:
    """Serialize and export a GeometryProject to a formatted JSON file.

    Parameters
    ----------
    project:
        The GeometryProject to serialize.
    path:
        Target file path.
    indent:
        JSON indentation formatting.

    Returns
    -------
    Path:
        Written file path.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(project.model_dump_json(indent=indent), encoding="utf-8")
    return out_path
