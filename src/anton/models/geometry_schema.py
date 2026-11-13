"""Canonical Pydantic-v2 schema for the ANTON geometry engine.

Every geometric primitive, layer, material, parameter, and project is defined
here.  All lengths are in **metres**.  Every object carries a UUID.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Vertex
# ---------------------------------------------------------------------------

class VertexDef(BaseModel):
    """A 2-D vertex (x, y) in metres."""

    x: float
    y: float


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------

class ParameterDef(BaseModel):
    """A named design parameter with optional bounds and dependencies."""

    name: str
    value: float
    unit: str = "m"
    description: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    dependencies: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

class MaterialRef(BaseModel):
    """A reference to a material (dielectric or conductor)."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    category: Literal["dielectric", "conductor"]
    properties: dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = None
    valid_range: Optional[str] = None


# ---------------------------------------------------------------------------
# Layer
# ---------------------------------------------------------------------------

class LayerDef(BaseModel):
    """A physical layer in the antenna stack-up."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    layer_type: str
    z_position: float = 0.0
    thickness: float = 0.0
    material_id: str
    object_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Geometry Object
# ---------------------------------------------------------------------------

_VALID_OBJECT_TYPES = {
    "rectangle",
    "circle",
    "ellipse",
    "triangle",
    "polygon",
    "line",
    "arc",
    "custom_contour",
    "boolean_result",
}


class GeometryObject(BaseModel):
    """A single geometric primitive or composite in the project."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: Optional[str] = None
    object_type: str
    layer_id: str
    material_id: str
    center_x: float = 0.0
    center_y: float = 0.0
    rotation_deg: float = 0.0
    width: Optional[float] = None
    height: Optional[float] = None
    radius: Optional[float] = None
    semi_major: Optional[float] = None
    semi_minor: Optional[float] = None
    vertices: list[VertexDef] = Field(default_factory=list)
    inner_vertices: list[VertexDef] = Field(default_factory=list)
    inner_holes: list[list[VertexDef]] = Field(default_factory=list)
    parameters: dict[str, ParameterDef] = Field(default_factory=dict)
    metadata: dict[str, Union[str, float]] = Field(default_factory=dict)

    @field_validator("object_type")
    @classmethod
    def _validate_object_type(cls, v: str) -> str:
        if v not in _VALID_OBJECT_TYPES:
            raise ValueError(
                f"object_type must be one of {sorted(_VALID_OBJECT_TYPES)}, got '{v}'"
            )
        return v


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

class ConnectionDef(BaseModel):
    """A logical connection between two geometry objects."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    source_object_id: str
    target_object_id: str
    connection_type: str
    metadata: dict[str, Union[str, float]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Antenna configuration
# ---------------------------------------------------------------------------

class AntennaConfig(BaseModel):
    """High-level antenna configuration descriptor."""

    name: str
    configuration: str = "custom"
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------

class ProjectMeta(BaseModel):
    """Metadata envelope for a geometry project."""

    schema_version: str = "1.0.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at: Optional[datetime] = None
    author: Optional[str] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Geometry Project (top-level)
# ---------------------------------------------------------------------------

class GeometryProject(BaseModel):
    """Top-level container for an ANTON geometry project."""

    project_name: str
    geometry_id: str = Field(default_factory=lambda: str(uuid4()))
    units: str = "m"
    coordinate_system: str = "Cartesian"
    antenna: AntennaConfig = Field(
        default_factory=lambda: AntennaConfig(name="Custom Antenna")
    )
    parameters: dict[str, ParameterDef] = Field(default_factory=dict)
    materials: dict[str, MaterialRef] = Field(default_factory=dict)
    layers: dict[str, LayerDef] = Field(default_factory=dict)
    objects: dict[str, GeometryObject] = Field(default_factory=dict)
    connections: list[ConnectionDef] = Field(default_factory=list)
    metadata: ProjectMeta = Field(default_factory=ProjectMeta)

    @field_validator("units")
    @classmethod
    def _validate_units(cls, v: str) -> str:
        if v != "m":
            raise ValueError("Only 'm' (metres) is supported as the unit system")
        return v

    # -- serialisation helpers ----------------------------------------------

    def to_json(self, path: Union[str, Path]) -> None:
        """Serialise the project to a JSON file at *path*."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "GeometryProject":
        """Deserialise a project from a JSON file at *path*."""
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(data)
