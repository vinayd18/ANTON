"""In-memory registry of GeometryObject instances, keyed by UUID."""

from __future__ import annotations

from typing import Optional

from anton.models.geometry_schema import GeometryObject


class GeometryRegistry:
    """Fast in-memory store for :class:`GeometryObject` instances.

    Objects are keyed by their ``id`` (UUID string).
    """

    def __init__(self) -> None:
        self._objects: dict[str, GeometryObject] = {}

    # -- mutators -----------------------------------------------------------

    def add(self, obj: GeometryObject) -> str:
        """Register *obj* and return its id."""
        self._objects[obj.id] = obj
        return obj.id

    def remove(self, obj_id: str) -> None:
        """Remove the object with *obj_id*.

        Raises
        ------
        KeyError
            If *obj_id* is not present.
        """
        del self._objects[obj_id]

    def clear(self) -> None:
        """Remove all registered objects."""
        self._objects.clear()

    # -- accessors ----------------------------------------------------------

    def get(self, obj_id: str) -> Optional[GeometryObject]:
        """Return the object with *obj_id*, or ``None``."""
        return self._objects.get(obj_id)

    def all(self) -> list[GeometryObject]:
        """Return a list of all registered objects."""
        return list(self._objects.values())

    def __contains__(self, obj_id: str) -> bool:
        """Return ``True`` if *obj_id* is registered."""
        return obj_id in self._objects

    def __len__(self) -> int:
        return len(self._objects)
