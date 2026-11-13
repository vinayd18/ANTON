# -*- coding: utf-8 -*-
"""2D geometry visualization engine for ANTON using Matplotlib."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Union

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
import matplotlib.pyplot as plt
import numpy as np
import shapely.geometry as geom

from anton.models.geometry_schema import GeometryProject
from anton.primitives.base import to_shapely

logger = logging.getLogger(__name__)

# Standard color palette by layer type
LAYER_COLOR_MAP: Dict[str, Dict[str, Union[str, float]]] = {
    "ground": {"facecolor": "#94A3B8", "edgecolor": "#475569", "alpha": 0.45},
    "substrate": {"facecolor": "#BAE6FD", "edgecolor": "#0284C7", "alpha": 0.35},
    "patch": {"facecolor": "#F59E0B", "edgecolor": "#B45309", "alpha": 0.85},
    "feed": {"facecolor": "#10B981", "edgecolor": "#047857", "alpha": 0.90},
    "conductor": {"facecolor": "#EAB308", "edgecolor": "#A16207", "alpha": 0.80},
    "custom": {"facecolor": "#A855F7", "edgecolor": "#7E22CE", "alpha": 0.70},
}


class GeometryRenderer:
    """Renders 2D planar microstrip antenna layouts from canonical GeometryProject models."""

    def __init__(self, project: GeometryProject) -> None:
        self.project = project

    def _shapely_to_mpl_patch(
        self,
        shape: geom.base.BaseGeometry,
        facecolor: str,
        edgecolor: str,
        alpha: float,
        label: Optional[str] = None,
    ) -> List[matplotlib.artist.Artist]:
        """Convert a Shapely geometry into Matplotlib patch artists."""
        artists = []

        if isinstance(shape, geom.Polygon):
            # Create compound path with holes
            vertices = []
            codes = []

            # Exterior ring
            ext_coords = list(shape.exterior.coords)
            if ext_coords:
                vertices.append(ext_coords[0])
                codes.append(MplPath.MOVETO)
                for pt in ext_coords[1:-1]:
                    vertices.append(pt)
                    codes.append(MplPath.LINETO)
                vertices.append(ext_coords[-1])
                codes.append(MplPath.CLOSEPOLY)

            # Interior rings (holes)
            for interior in shape.interiors:
                int_coords = list(interior.coords)
                if int_coords:
                    vertices.append(int_coords[0])
                    codes.append(MplPath.MOVETO)
                    for pt in int_coords[1:-1]:
                        vertices.append(pt)
                        codes.append(MplPath.LINETO)
                    vertices.append(int_coords[-1])
                    codes.append(MplPath.CLOSEPOLY)

            if vertices:
                path = MplPath(vertices, codes)
                patch = mpatches.PathPatch(
                    path,
                    facecolor=facecolor,
                    edgecolor=edgecolor,
                    linewidth=1.2,
                    alpha=alpha,
                    label=label,
                )
                artists.append(patch)

        elif isinstance(shape, geom.MultiPolygon):
            for i, poly in enumerate(shape.geoms):
                artists.extend(
                    self._shapely_to_mpl_patch(
                        poly, facecolor, edgecolor, alpha, label if i == 0 else None
                    )
                )

        elif isinstance(shape, (geom.LineString, geom.MultiLineString)):
            if isinstance(shape, geom.LineString):
                lines = [shape]
            else:
                lines = list(shape.geoms)
            for i, line in enumerate(lines):
                coords = np.array(line.coords)
                artist = plt.Line2D(
                    coords[:, 0],
                    coords[:, 1],
                    color=edgecolor,
                    linewidth=1.8,
                    alpha=alpha,
                    label=label if i == 0 else None,
                )
                artists.append(artist)

        return artists

    def render(
        self,
        show_layers: Optional[List[str]] = None,
        hide_layers: Optional[List[str]] = None,
        show_ids: bool = False,
        show_dimensions: bool = False,
        title: Optional[str] = None,
        figsize: tuple = (10, 8),
    ) -> matplotlib.figure.Figure:
        """Render the 2D layout to a Matplotlib Figure.

        Parameters
        ----------
        show_layers:
            Whitelist of layer IDs or layer names to render.
        hide_layers:
            Blacklist of layer IDs or names to suppress.
        show_ids:
            Whether to annotate object IDs at their centroids.
        show_dimensions:
            Whether to annotate bounding box dimensions.
        title:
            Plot title.
        figsize:
            Figure dimensions in inches.
        """
        fig, ax = plt.subplots(figsize=figsize)

        # Determine layer visibility
        allowed_layer_ids: Set[str] = set(self.project.layers.keys())
        if show_layers is not None:
            show_set = {s.lower() for s in show_layers}
            allowed_layer_ids = {
                lid
                for lid, layer in self.project.layers.items()
                if lid.lower() in show_set or layer.name.lower() in show_set
            }
        if hide_layers is not None:
            hide_set = {h.lower() for h in hide_layers}
            allowed_layer_ids = {
                lid
                for lid in allowed_layer_ids
                if lid.lower() not in hide_set
                and self.project.layers[lid].name.lower() not in hide_set
            }

        # Sort layers by z_position ascending so bottom layers (ground, substrate) draw first
        sorted_layers = sorted(
            [layer for layer in self.project.layers.values() if layer.id in allowed_layer_ids],
            key=lambda l: l.z_position,
        )

        legend_handles = {}

        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")

        for layer in sorted_layers:
            layer_style = LAYER_COLOR_MAP.get(
                layer.layer_type.lower(),
                LAYER_COLOR_MAP["custom"],
            )

            for obj_id in layer.object_ids:
                obj = self.project.objects.get(obj_id)
                if not obj:
                    continue

                try:
                    shape = to_shapely(obj)
                    if shape.is_empty:
                        continue

                    # Update bounds
                    bounds = shape.bounds  # (minx, miny, maxx, maxy)
                    min_x = min(min_x, bounds[0])
                    min_y = min(min_y, bounds[1])
                    max_x = max(max_x, bounds[2])
                    max_y = max(max_y, bounds[3])

                    artists = self._shapely_to_mpl_patch(
                        shape,
                        facecolor=str(layer_style["facecolor"]),
                        edgecolor=str(layer_style["edgecolor"]),
                        alpha=float(layer_style["alpha"]),
                        label=layer.name,
                    )

                    for artist in artists:
                        if isinstance(artist, mpatches.PathPatch):
                            ax.add_patch(artist)
                        elif isinstance(artist, plt.Line2D):
                            ax.add_line(artist)

                    if layer.name not in legend_handles:
                        legend_handles[layer.name] = mpatches.Patch(
                            facecolor=str(layer_style["facecolor"]),
                            edgecolor=str(layer_style["edgecolor"]),
                            alpha=float(layer_style["alpha"]),
                            label=f"{layer.name} ({layer.layer_type})",
                        )

                    # Optional annotations
                    if show_ids:
                        centroid = shape.centroid
                        ax.text(
                            centroid.x,
                            centroid.y,
                            obj.name or obj.id[:6],
                            fontsize=8,
                            ha="center",
                            va="center",
                            color="#1E293B",
                            weight="bold",
                        )

                    if show_dimensions and hasattr(obj, "width") and obj.width:
                        bounds = shape.bounds
                        ax.annotate(
                            f"{obj.width * 1000:.1f} mm",
                            xy=((bounds[0] + bounds[2]) / 2, bounds[1]),
                            xytext=(0, -12),
                            textcoords="offset points",
                            ha="center",
                            fontsize=7,
                            color="#334155",
                        )

                except Exception as e:
                    logger.warning("Failed to render object '%s': %s", obj.id, e)

        # Configure axis presentation
        ax.set_aspect("equal", adjustable="datalim")
        ax.grid(True, linestyle="--", alpha=0.5, color="#CBD5E1")
        ax.set_xlabel("X (metres)", fontsize=10)
        ax.set_ylabel("Y (metres)", fontsize=10)

        # Dynamic margins
        if min_x != float("inf"):
            dx = max_x - min_x or 0.01
            dy = max_y - min_y or 0.01
            ax.set_xlim(min_x - dx * 0.1, max_x + dx * 0.1)
            ax.set_ylim(min_y - dy * 0.1, max_y + dy * 0.1)

        display_title = title or f"{self.project.project_name} — 2D Geometry Layout"
        ax.set_title(display_title, fontsize=12, pad=12)

        if legend_handles:
            ax.legend(handles=list(legend_handles.values()), loc="upper right", framealpha=0.9)

        fig.tight_layout()
        return fig

    def save_svg(self, path: Union[str, Path], **kwargs) -> Path:
        """Render and save 2D vector geometry to SVG format."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig = self.render(**kwargs)
        fig.savefig(out_path, format="svg", bbox_inches="tight")
        plt.close(fig)
        return out_path

    def save_png(self, path: Union[str, Path], dpi: int = 300, **kwargs) -> Path:
        """Render and save raster geometry to high-resolution PNG."""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig = self.render(**kwargs)
        fig.savefig(out_path, format="png", dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        return out_path

