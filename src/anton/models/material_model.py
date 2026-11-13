"""Material model — MaterialCategory enum and re-exported MaterialRef."""

from enum import Enum

from anton.models.geometry_schema import MaterialRef

__all__ = ["MaterialCategory", "MaterialRef"]


class MaterialCategory(str, Enum):
    """Supported material categories."""

    DIELECTRIC = "dielectric"
    CONDUCTOR = "conductor"
