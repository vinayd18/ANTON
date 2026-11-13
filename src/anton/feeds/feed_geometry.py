# -*- coding: utf-8 -*-
"""Feed geometry representation and connectivity engine for ANTON.

Supports microstrip line feed, inset feed, edge feed, coaxial probe feed representation,
and custom feeds. Verifies geometric connectivity to radiating elements.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field

from anton.models.geometry_schema import GeometryObject, ParameterDef
from anton.primitives.base import to_shapely


class FeedType(str, Enum):
    """Supported RF feed geometry types."""

    MICROSTRIP = "microstrip"
    INSET = "inset"
    EDGE = "edge"
    PROBE = "probe"
    CUSTOM = "custom"


class FeedDef(BaseModel):
    """Representation of an antenna feed structure."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    feed_type: FeedType
    geometry_object_id: str
    target_object_id: Optional[str] = None
    connection_point_x: Optional[float] = None
    connection_point_y: Optional[float] = None
    parameters: Dict[str, ParameterDef] = Field(default_factory=dict)
    metadata: Dict[str, Union[str, float]] = Field(default_factory=dict)


class FeedManager:
    """Manages antenna feeds and evaluates geometric physical connectivity."""

    def __init__(self) -> None:
        self._feeds: Dict[str, FeedDef] = {}

    def create_feed(
        self,
        name: str,
        feed_type: Union[FeedType, str],
        geometry_object_id: str,
        target_object_id: Optional[str] = None,
        connection_point_x: Optional[float] = None,
        connection_point_y: Optional[float] = None,
        metadata: Optional[Dict[str, Union[str, float]]] = None,
    ) -> FeedDef:
        """Create and register a new antenna feed."""
        if isinstance(feed_type, str):
            feed_type = FeedType(feed_type.lower())

        feed = FeedDef(
            name=name,
            feed_type=feed_type,
            geometry_object_id=geometry_object_id,
            target_object_id=target_object_id,
            connection_point_x=connection_point_x,
            connection_point_y=connection_point_y,
            metadata=metadata or {},
        )
        self._feeds[feed.id] = feed
        return feed

    def get_feed(self, feed_id: str) -> Optional[FeedDef]:
        """Retrieve a feed by ID."""
        return self._feeds.get(feed_id)

    def list_feeds(self) -> List[FeedDef]:
        """List all feeds."""
        return list(self._feeds.values())

    def check_connectivity(
        self,
        feed: FeedDef,
        objects: Dict[str, GeometryObject],
        tolerance: float = 1e-6,
    ) -> bool:
        """Check if feed geometry touches or intersects the target radiating structure.

        Parameters
        ----------
        feed:
            The FeedDef instance to verify.
        objects:
            Mapping of object IDs to GeometryObject models.
        tolerance:
            Tolerance in metres for contact evaluation.

        Returns
        -------
        bool:
            True if feed physically contacts or overlaps the target object.
        """
        if not feed.target_object_id:
            # No target specified, cannot verify physical connection
            return True

        feed_obj = objects.get(feed.geometry_object_id)
        target_obj = objects.get(feed.target_object_id)

        if not feed_obj or not target_obj:
            return False

        feed_shape = to_shapely(feed_obj)
        target_shape = to_shapely(target_obj)

        # For probe feeds with explicit (x, y) connection point
        if feed.connection_point_x is not None and feed.connection_point_y is not None:
            import shapely.geometry as geom_types
            probe_pt = geom_types.Point(feed.connection_point_x, feed.connection_point_y)
            if target_shape.contains(probe_pt) or target_shape.distance(probe_pt) <= tolerance:
                return True

        # Check direct intersection or contact
        if feed_shape.intersects(target_shape) or feed_shape.touches(target_shape):
            return True

        # Check within physical tolerance buffer
        if tolerance > 0:
            buffered_feed = feed_shape.buffer(tolerance)
            if buffered_feed.intersects(target_shape):
                return True

        return False

