"""Parameter model — re-exported ParameterDef with dependency helper."""

from __future__ import annotations

from typing import Dict

from anton.models.geometry_schema import ParameterDef

__all__ = ["ParameterDef", "resolve_dependencies"]


def resolve_dependencies(
    parameters: Dict[str, ParameterDef],
    name: str,
    visited: set[str] | None = None,
) -> list[str]:
    """Return a topologically-ordered list of parameter names that *name* depends on.

    Parameters
    ----------
    parameters:
        Mapping of parameter name → ParameterDef.
    name:
        The parameter whose dependency chain to resolve.
    visited:
        Internal set used for cycle detection.

    Returns
    -------
    list[str]
        Dependency names in resolution order (leaves first).

    Raises
    ------
    ValueError
        If a circular dependency is detected.
    """
    if visited is None:
        visited = set()
    if name in visited:
        raise ValueError(f"Circular dependency detected involving '{name}'")
    visited.add(name)

    param = parameters.get(name)
    if param is None:
        return []

    order: list[str] = []
    for dep in param.dependencies:
        order.extend(resolve_dependencies(parameters, dep, visited.copy()))
    order.append(name)
    return order
