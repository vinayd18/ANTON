"""AntonEngine — the main entry-point for the ANTON geometry engine.

Wraps a :class:`GeometryProject` and a :class:`GeometryRegistry`, providing
convenient helpers for adding materials, layers, parameters, and all supported
geometry primitives.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from anton.core.geometry_registry import GeometryRegistry
from anton.models.geometry_schema import (
    AntennaConfig,
    ConnectionDef,
    GeometryObject,
    GeometryProject,
    LayerDef,
    MaterialRef,
    ParameterDef,
    VertexDef,
)


class AntonEngine:
    """High-level façade for building antenna geometry projects.

    Parameters
    ----------
    project_name:
        Human-readable name for the project.
    """

    def __init__(self, project_name: str) -> None:
        self.project = GeometryProject(project_name=project_name)
        self.registry = GeometryRegistry()

    # -- materials ----------------------------------------------------------

    def add_material(
        self,
        name: str,
        category: str,
        properties: dict[str, float | str] | None = None,
        source: str | None = None,
        valid_range: str | None = None,
    ) -> str:
        """Add a material and return its id."""
        mat = MaterialRef(
            name=name,
            category=category,
            properties=properties or {},
            source=source,
            valid_range=valid_range,
        )
        self.project.materials[mat.id] = mat
        return mat.id

    def get_material(self, material_id: str) -> Optional[MaterialRef]:
        """Return a material by id, or ``None``."""
        return self.project.materials.get(material_id)

    def list_materials(self) -> list[MaterialRef]:
        """Return all materials."""
        return list(self.project.materials.values())

    # -- layers -------------------------------------------------------------

    def add_layer(
        self,
        name: str,
        layer_type: str,
        material_id: str,
        z_position: float = 0.0,
        thickness: float = 0.0,
    ) -> str:
        """Add a layer and return its id."""
        layer = LayerDef(
            name=name,
            layer_type=layer_type,
            material_id=material_id,
            z_position=z_position,
            thickness=thickness,
        )
        self.project.layers[layer.id] = layer
        return layer.id

    def get_layer(self, layer_id: str) -> Optional[LayerDef]:
        """Return a layer by id, or ``None``."""
        return self.project.layers.get(layer_id)

    def list_layers(self) -> list[LayerDef]:
        """Return all layers."""
        return list(self.project.layers.values())

    # -- parameters ---------------------------------------------------------

    def add_parameter(
        self,
        name: str,
        value: float,
        unit: str = "m",
        description: str | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        dependencies: list[str] | None = None,
    ) -> str:
        """Add a named parameter and return its name (used as key)."""
        param = ParameterDef(
            name=name,
            value=value,
            unit=unit,
            description=description,
            min_value=min_value,
            max_value=max_value,
            dependencies=dependencies or [],
        )
        self.project.parameters[name] = param
        return name

    def update_parameter(self, name: str, value: float) -> None:
        """Update a parameter's value and propagate changes to dependent parameters and objects.

        Propagates changes transitively to all dependent parameters in the DAG and
        synchronizes geometry dimensions for any linked GeometryObjects.

        Raises
        ------
        KeyError
            If the parameter *name* does not exist.
        ValueError
            If a circular dependency is detected in the parameter dependency graph.
        """
        from anton.models.parameter_model import resolve_dependencies

        if name not in self.project.parameters:
            raise KeyError(f"Parameter '{name}' not found")

        # Cycle validation
        for p_name in self.project.parameters:
            resolve_dependencies(self.project.parameters, p_name)

        param = self.project.parameters[name]
        old_value = param.value
        param.value = value

        if old_value == 0:
            return

        ratio = value / old_value

        # Transitive propagation through dependency graph
        updated = {name: ratio}
        queue = [name]

        while queue:
            curr = queue.pop(0)
            curr_ratio = updated[curr]
            for p in self.project.parameters.values():
                if curr in p.dependencies:
                    p.value *= curr_ratio
                    updated[p.name] = curr_ratio
                    queue.append(p.name)

        # Synchronize with object geometry
        for obj in self.project.objects.values():
            for attr, p_def in obj.parameters.items():
                if p_def.name in updated:
                    p_def.value = self.project.parameters[p_def.name].value
                    if hasattr(obj, attr):
                        setattr(obj, attr, p_def.value)

    # -- generic object registration ----------------------------------------

    def _register_object(self, obj: GeometryObject) -> str:
        """Add *obj* to both the registry and the project, and record in its layer."""
        self.registry.add(obj)
        self.project.objects[obj.id] = obj
        layer = self.project.layers.get(obj.layer_id)
        if layer is not None:
            layer.object_ids.append(obj.id)
        return obj.id

    def add_object(self, obj: GeometryObject) -> str:
        """Register an arbitrary :class:`GeometryObject` and return its id."""
        return self._register_object(obj)

    def remove_object(self, obj_id: str) -> None:
        """Remove an object from the project and its layer.

        Raises
        ------
        KeyError
            If *obj_id* is not found.
        """
        obj = self.project.objects.get(obj_id)
        if obj is None:
            raise KeyError(f"Object '{obj_id}' not found")
        layer = self.project.layers.get(obj.layer_id)
        if layer is not None and obj_id in layer.object_ids:
            layer.object_ids.remove(obj_id)
        del self.project.objects[obj_id]
        if obj_id in self.registry:
            self.registry.remove(obj_id)

    def list_objects(self) -> list[GeometryObject]:
        """Return all geometry objects."""
        return list(self.project.objects.values())

    # -- primitive helpers --------------------------------------------------

    def add_rectangle(
        self,
        layer_id: str,
        material_id: str,
        width: float,
        height: float,
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add a rectangle and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="rectangle",
            layer_id=layer_id,
            material_id=material_id,
            width=width,
            height=height,
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    def add_circle(
        self,
        layer_id: str,
        material_id: str,
        radius: float,
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
    ) -> str:
        """Add a circle and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="circle",
            layer_id=layer_id,
            material_id=material_id,
            radius=radius,
            center_x=center_x,
            center_y=center_y,
        )
        return self._register_object(obj)

    def add_ellipse(
        self,
        layer_id: str,
        material_id: str,
        semi_major: float,
        semi_minor: float,
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add an ellipse and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="ellipse",
            layer_id=layer_id,
            material_id=material_id,
            semi_major=semi_major,
            semi_minor=semi_minor,
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    def add_triangle(
        self,
        layer_id: str,
        material_id: str,
        vertices: list[VertexDef],
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add a triangle (3 vertices) and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="triangle",
            layer_id=layer_id,
            material_id=material_id,
            vertices=vertices,
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    def add_polygon(
        self,
        layer_id: str,
        material_id: str,
        vertices: list[VertexDef],
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add a polygon and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="polygon",
            layer_id=layer_id,
            material_id=material_id,
            vertices=vertices,
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    def add_line(
        self,
        layer_id: str,
        material_id: str,
        vertices: list[VertexDef],
        name: str | None = None,
    ) -> str:
        """Add a line (two or more vertices) and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="line",
            layer_id=layer_id,
            material_id=material_id,
            vertices=vertices,
        )
        return self._register_object(obj)

    def add_arc(
        self,
        layer_id: str,
        material_id: str,
        radius: float,
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add an arc and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="arc",
            layer_id=layer_id,
            material_id=material_id,
            radius=radius,
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    def add_custom_contour(
        self,
        layer_id: str,
        material_id: str,
        vertices: list[VertexDef],
        inner_vertices: list[VertexDef] | None = None,
        name: str | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rotation_deg: float = 0.0,
    ) -> str:
        """Add a custom contour and return its id."""
        obj = GeometryObject(
            name=name,
            object_type="custom_contour",
            layer_id=layer_id,
            material_id=material_id,
            vertices=vertices,
            inner_vertices=inner_vertices or [],
            center_x=center_x,
            center_y=center_y,
            rotation_deg=rotation_deg,
        )
        return self._register_object(obj)

    # -- connections --------------------------------------------------------

    def add_connection(
        self,
        source_object_id: str,
        target_object_id: str,
        connection_type: str,
        metadata: dict[str, str | float] | None = None,
    ) -> str:
        """Add a connection between two objects and return its id."""
        conn = ConnectionDef(
            source_object_id=source_object_id,
            target_object_id=target_object_id,
            connection_type=connection_type,
            metadata=metadata or {},
        )
        self.project.connections.append(conn)
        return conn.id

    # -- serialisation ------------------------------------------------------

    def export_json(self, path: Union[str, Path]) -> None:
        """Write the project to a JSON file."""
        self.project.to_json(path)

    def load_json(self, path: Union[str, Path]) -> None:
        """Load a project from a JSON file, replacing current state."""
        self.project = GeometryProject.from_json(path)
        self.registry.clear()
        for obj in self.project.objects.values():
            self.registry.add(obj)

    def to_dict(self) -> dict[str, Any]:
        """Return the project as a plain dict."""
        return self.project.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AntonEngine":
        """Reconstruct an engine from a plain dict."""
        project = GeometryProject.model_validate(data)
        engine = cls.__new__(cls)
        engine.project = project
        engine.registry = GeometryRegistry()
        for obj in project.objects.values():
            engine.registry.add(obj)
        return engine
