"""
Canonical Antenna Feature Extractor and Geometry Rasterizer.

Extracts continuous physical dimensions, substrate properties, and feed parameters,
and rasterizes arbitrary 2D planar conductor patterns into 2D conductivity masks (e.g. 16x16, 32x32).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from anton.datasets.schema import DatasetRecord


class FeatureExtractor:
    """
    Translates canonical ANTON geometry records into numerical machine learning inputs.
    """

    @staticmethod
    def extract_continuous_vector(record: DatasetRecord) -> np.ndarray:
        """
        Extracts continuous geometric and material parameters:
        [patch_w, patch_l, sub_w, sub_l, sub_h, eps_r, tan_d, feed_x, feed_y, metal_t]
        """
        geo = record.geometry
        patch = geo.get("patch", {})
        sub = geo.get("substrate", {})
        feed = geo.get("feed", {})
        mat = record.materials

        patch_w = float(patch.get("width", patch.get("radius", 0.0) * 2.0))
        patch_l = float(patch.get("length", patch.get("radius", 0.0) * 2.0))
        sub_w = float(sub.get("width", patch_w * 2.0))
        sub_l = float(sub.get("length", patch_l * 2.0))
        sub_h = float(sub.get("thickness", mat.substrate_thickness_mm))
        eps_r = float(mat.permittivity_r)
        tan_d = float(mat.loss_tangent)
        metal_t = float(patch.get("metal_thickness", 0.035))

        feed_pos = feed.get("position", [0.0, 0.0])
        feed_x = float(feed_pos[0]) if len(feed_pos) > 0 else 0.0
        feed_y = float(feed_pos[1]) if len(feed_pos) > 1 else 0.0

        vec = np.array([
            patch_w, patch_l, sub_w, sub_l, sub_h,
            eps_r, tan_d, feed_x, feed_y, metal_t
        ], dtype=np.float32)

        return vec

    @staticmethod
    def rasterize_patch_2d(
        record: DatasetRecord,
        grid_size: int = 32,
        extent_ratio: float = 1.2
    ) -> np.ndarray:
        """
        Rasterizes the 2D top conductor layer into a binary/fractional conductivity grid (grid_size x grid_size).
        Grid spans [-extent_w/2, extent_w/2] x [-extent_l/2, extent_l/2].
        Conductor = 1.0, Dielectric = 0.0.
        """
        geo = record.geometry
        patch = geo.get("patch", {})
        shape = patch.get("shape", "RECTANGULAR").upper()

        mask = np.zeros((grid_size, grid_size), dtype=np.float32)

        # Coordinate axes
        sub = geo.get("substrate", {})
        sub_w = float(sub.get("width", 50.0))
        sub_l = float(sub.get("length", 50.0))

        # Viewport dimensions
        extent_x = sub_w * extent_ratio / 2.0
        extent_y = sub_l * extent_ratio / 2.0

        x_coords = np.linspace(-extent_x, extent_x, grid_size)
        y_coords = np.linspace(-extent_y, extent_y, grid_size)
        xx, yy = np.meshgrid(x_coords, y_coords)

        if shape in ("RECTANGULAR", "INSET_FED", "U_SLOT"):
            w = float(patch.get("width", 30.0))
            length = float(patch.get("length", 30.0))
            # Base rectangle
            cond = (np.abs(xx) <= w / 2.0) & (np.abs(yy) <= length / 2.0)

            # Inset notches
            if shape == "INSET_FED" and "notch_width" in patch:
                nw = float(patch.get("notch_width", 2.0))
                nl = float(patch.get("notch_length", 5.0))
                feed_w = float(patch.get("feed_line_width", 3.0))
                # Left and right notches
                notch_y = (yy <= -length / 2.0 + nl) & (yy >= -length / 2.0)
                notch_x = (np.abs(xx) >= feed_w / 2.0) & (np.abs(xx) <= feed_w / 2.0 + nw)
                cond = cond & ~(notch_y & notch_x)

            # U-slot cut
            if shape == "U_SLOT" and "slot_width" in patch:
                sw = float(patch.get("slot_width", 2.0))
                sl = float(patch.get("slot_length", 10.0))
                st = float(patch.get("slot_thickness", 1.0))
                # U-slot arms and base
                slot_base = (np.abs(xx) <= sw / 2.0) & (np.abs(yy) <= st / 2.0)
                slot_arms = (np.abs(np.abs(xx) - sw / 2.0) <= st / 2.0) & (yy >= 0) & (yy <= sl)
                cond = cond & ~(slot_base | slot_arms)

            mask[cond] = 1.0

        elif shape in ("CIRCULAR", "ANNULAR"):
            r_out = float(patch.get("radius", patch.get("outer_radius", 15.0)))
            r_in = float(patch.get("inner_radius", 0.0)) if shape == "ANNULAR" else 0.0
            r_sq = xx ** 2 + yy ** 2
            cond = (r_sq <= r_out ** 2) & (r_sq >= r_in ** 2)
            mask[cond] = 1.0

        elif shape == "TRIANGULAR":
            side = float(patch.get("side_length", 30.0))
            # Equilateral triangle centered at origin
            h = side * math.sqrt(3) / 2.0
            # Vertices: (0, 2h/3), (-side/2, -h/3), (side/2, -h/3)
            cond = (yy >= -h / 3.0) & (yy <= 2 * h / 3.0 - math.sqrt(3) * np.abs(xx))
            mask[cond] = 1.0

        elif shape == "HEXAGONAL":
            r = float(patch.get("radius", 15.0))
            # Regular hexagon
            cond = (np.abs(xx) <= r) & (np.abs(yy) <= r * math.sqrt(3) / 2.0) & (np.abs(xx) * math.sqrt(3) / 2.0 + np.abs(yy) * 0.5 <= r * math.sqrt(3) / 2.0)
            mask[cond] = 1.0

        else:
            # Default fallback rectangle from bounding box
            w = float(patch.get("width", 30.0))
            length = float(patch.get("length", 30.0))
            cond = (np.abs(xx) <= w / 2.0) & (np.abs(yy) <= length / 2.0)
            mask[cond] = 1.0

        return mask
