# -*- coding: utf-8 -*-
"""Layer management engine for ANTON.

Handles creation, indexing, object assignment, and physical stack-up ordering
for multilayer planar antenna structures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from anton.models.geometry_schema import LayerDef

if TYPE_CHECKING:
    from anton.core.geometry_engine import AntonEngine


class LayerManager:
    """Manages physical and logical layers within an ANTON antenna project."""

    def __init__(self, engine: AntonEngine) -> None:
        self.engine = engine

    def create_layer(
        self,
        name: str,
        layer_type: str,
        material_id: str,
        z_position: float = 0.0,
        thickness: float = 0.0,
    ) -> str:
        """Create a new layer in the project and return its unique ID."""
        return self.engine.add_layer(
            name=name,
            layer_type=layer_type,
            material_id=material_id,
            z_position=z_position,
            thickness=thickness,
        )

    def get_layer(self, layer_id: str) -> Optional[LayerDef]:
        """Retrieve a layer by its ID."""
        return self.engine.get_layer(layer_id)

    def list_layers(self) -> List[LayerDef]:
        """List all layers in the project."""
        return self.engine.list_layers()

    def assign_object(self, layer_id: str, object_id: str) -> None:
        """Assign a geometry object to a specific layer."""
        layer = self.get_layer(layer_id)
        if layer is None:
            raise KeyError(f"Layer '{layer_id}' not found.")
        if object_id not in layer.object_ids:
            layer.object_ids.append(object_id)

    def remove_object(self, layer_id: str, object_id: str) -> None:
        """Remove a geometry object assignment from a layer."""
        layer = self.get_layer(layer_id)
        if layer is None:
            raise KeyError(f"Layer '{layer_id}' not found.")
        if object_id in layer.object_ids:
            layer.object_ids.remove(object_id)

    def get_layer_stack(self) -> List[LayerDef]:
        """Return all layers ordered vertically from bottom to top (by z_position)."""
        return sorted(self.list_layers(), key=lambda layer: layer.z_position)

    def get_objects_in_layer(self, layer_id: str) -> List[str]:
        """Return the list of object IDs associated with the specified layer."""
        layer = self.get_layer(layer_id)
        if layer is None:
            raise KeyError(f"Layer '{layer_id}' not found.")
        return list(layer.object_ids)
