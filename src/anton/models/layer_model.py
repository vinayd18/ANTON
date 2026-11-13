"""Layer model — LayerType enum and re-exported LayerDef."""

from enum import Enum

from anton.models.geometry_schema import LayerDef

__all__ = ["LayerType", "LayerDef"]


class LayerType(str, Enum):
    """Supported layer types in the antenna stack-up."""

    PATCH = "patch"
    SUBSTRATE = "substrate"
    GROUND = "ground"
    FEED = "feed"
    CONDUCTOR = "conductor"
    CUSTOM = "custom"
