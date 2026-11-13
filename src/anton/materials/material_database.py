# -*- coding: utf-8 -*-
"""Material database foundation for ANTON.

Provides database loading, lookup, editing, and registration of representative
dielectric and conductor materials for RF/microwave antenna engineering.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import uuid4

from anton.models.geometry_schema import MaterialRef


class MaterialDatabase:
    """Repository of RF substrate materials and conductor metallizations."""

    def __init__(self, json_path: Optional[Union[str, Path]] = None) -> None:
        self._materials: Dict[str, MaterialRef] = {}
        self._name_index: Dict[str, str] = {}

        if json_path is not None:
            self.load(json_path)
        else:
            # Look for default bundled materials.json
            bundled = Path(__file__).resolve().parent.parent.parent.parent / "data" / "materials" / "materials.json"
            if bundled.exists():
                self.load(bundled)

    def load(self, path: Union[str, Path]) -> None:
        """Load materials from a JSON array file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Material database file '{path}' not found.")

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._materials.clear()
        self._name_index.clear()

        for item in data:
            mat_id = item.get("id") or str(uuid4())
            mat = MaterialRef(
                id=mat_id,
                name=item["name"],
                category=item["category"],
                properties=item.get("properties", {}),
                source=item.get("source"),
                valid_range=item.get("valid_range"),
            )
            self._materials[mat.id] = mat
            self._name_index[mat.name.lower()] = mat.id

    def save(self, path: Union[str, Path]) -> None:
        """Save current materials to a JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        data = [mat.model_dump() for mat in self._materials.values()]
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add(self, material: MaterialRef) -> str:
        """Add a new MaterialRef instance to the database."""
        self._materials[material.id] = material
        self._name_index[material.name.lower()] = material.id
        return material.id

    def create_dielectric(
        self,
        name: str,
        relative_permittivity: float,
        loss_tangent: float = 0.0,
        source: Optional[str] = None,
        valid_range: Optional[str] = None,
    ) -> MaterialRef:
        """Create and register a custom dielectric material."""
        mat = MaterialRef(
            name=name,
            category="dielectric",
            properties={
                "relative_permittivity": relative_permittivity,
                "loss_tangent": loss_tangent,
            },
            source=source,
            valid_range=valid_range,
        )
        self.add(mat)
        return mat

    def create_conductor(
        self,
        name: str,
        conductivity: float,
        source: Optional[str] = None,
        valid_range: Optional[str] = None,
    ) -> MaterialRef:
        """Create and register a custom conductor material."""
        mat = MaterialRef(
            name=name,
            category="conductor",
            properties={"conductivity": conductivity},
            source=source,
            valid_range=valid_range,
        )
        self.add(mat)
        return mat

    def get(self, name_or_id: str) -> Optional[MaterialRef]:
        """Retrieve a material by ID or case-insensitive name."""
        if name_or_id in self._materials:
            return self._materials[name_or_id]

        matched_id = self._name_index.get(name_or_id.lower())
        if matched_id:
            return self._materials[matched_id]

        return None

    def list_all(self) -> List[MaterialRef]:
        """List all registered materials."""
        return list(self._materials.values())

