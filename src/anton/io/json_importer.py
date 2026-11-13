# -*- coding: utf-8 -*-
"""JSON importer for ANTON canonical geometry models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

from pydantic import ValidationError

from anton.models.geometry_schema import GeometryProject


def import_project_json(path: Union[str, Path]) -> GeometryProject:
    """Read and validate a GeometryProject from a JSON file.

    Parameters
    ----------
    path:
        Path to the JSON file.

    Returns
    -------
    GeometryProject:
        The validated canonical geometry project.

    Raises
    ------
    FileNotFoundError:
        If the file does not exist.
    ValueError:
        If JSON is malformed or schema validation fails.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Geometry JSON file '{path}' does not exist.")

    try:
        raw_text = p.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON syntax in '{path}': {e}") from e

    try:
        project = GeometryProject.model_validate(data)
        return project
    except ValidationError as e:
        raise ValueError(f"Schema validation failed for '{path}':\n{e}") from e

