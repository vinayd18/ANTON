"""
Duplicate and Near-Duplicate Detection Engine.

Provides:
- Exact geometry hashing (SHA-256 of canonical geometry dictionary)
- Parameter-based geometric similarity analysis
- Duplicate source-file detection (SHA-256 of raw data)
- Distinguishes geometrically identical designs simulated under different conditions (solvers, materials, mesh)
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Set, Tuple

from anton.datasets.schema import DatasetRecord


class DuplicateDetector:
    """
    Detects exact duplicate geometries, identical simulations, and near-duplicate parameter vectors.
    """

    def __init__(self, relative_param_tolerance: float = 0.01):
        self.relative_param_tolerance = relative_param_tolerance

    @staticmethod
    def compute_geometry_hash(geometry_dict: Dict[str, Any]) -> str:
        """
        Computes a deterministic SHA-256 hash from a canonical geometry dict.
        """
        canonical_json = json.dumps(geometry_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_file_hash(content_bytes: bytes) -> str:
        """
        Computes SHA-256 hash of raw file content.
        """
        return hashlib.sha256(content_bytes).hexdigest()

    def extract_key_geometric_parameters(self, record: DatasetRecord) -> Dict[str, float]:
        """
        Extracts continuous geometric dimensions for distance/similarity calculation.
        """
        params: Dict[str, float] = {}
        geo = record.geometry
        patch = geo.get("patch", {})
        substrate = geo.get("substrate", {})
        feed = geo.get("feed", {})

        # Lengths / widths
        if "width" in patch:
            params["patch_width"] = float(patch["width"])
        if "length" in patch:
            params["patch_length"] = float(patch["length"])
        if "radius" in patch:
            params["patch_radius"] = float(patch["radius"])
        if "thickness" in substrate:
            params["substrate_height"] = float(substrate["thickness"])
        if "thickness" in patch:
            params["metal_thickness"] = float(patch["thickness"])

        # Feed positions
        feed_pos = feed.get("position")
        if isinstance(feed_pos, (list, tuple)) and len(feed_pos) >= 2:
            params["feed_x"] = float(feed_pos[0])
            params["feed_y"] = float(feed_pos[1])

        # Material permittivity
        params["eps_r"] = float(record.materials.permittivity_r)

        return params

    def compute_parameter_distance(
        self,
        params_a: Dict[str, float],
        params_b: Dict[str, float]
    ) -> float:
        """
        Calculates normalized Euclidean distance between two antenna parameter sets.
        Returns a normalized score (0.0 = identical).
        """
        common_keys = set(params_a.keys()).intersection(set(params_b.keys()))
        if not common_keys:
            return float("inf")

        sq_sum = 0.0
        for k in common_keys:
            va = params_a[k]
            vb = params_b[k]
            avg = (abs(va) + abs(vb)) / 2.0
            if avg > 1e-6:
                diff_norm = (va - vb) / avg
            else:
                diff_norm = va - vb
            sq_sum += diff_norm ** 2

        return math.sqrt(sq_sum / len(common_keys))

    def analyze_dataset_duplicates(
        self,
        records: List[DatasetRecord]
    ) -> Dict[str, Any]:
        """
        Scans a collection of records for exact and near duplicates.
        Does not delete records; catalogs relationships clearly.
        """
        exact_geometry_groups: Dict[str, List[str]] = {}
        source_file_groups: Dict[str, List[str]] = {}
        near_duplicate_pairs: List[Dict[str, Any]] = []

        param_cache: Dict[str, Dict[str, float]] = {}

        for rec in records:
            rec_id = rec.antenna_identity.dataset_record_id
            geo_hash = self.compute_geometry_hash(rec.geometry)
            exact_geometry_groups.setdefault(geo_hash, []).append(rec_id)

            if rec.provenance.source_file_sha256:
                source_file_groups.setdefault(rec.provenance.source_file_sha256, []).append(rec_id)

            param_cache[rec_id] = self.extract_key_geometric_parameters(rec)

        # Check near-duplicates across distinct geometry hashes
        rec_ids = list(param_cache.keys())
        for i in range(len(rec_ids)):
            id_a = rec_ids[i]
            params_a = param_cache[id_a]
            for j in range(i + 1, len(rec_ids)):
                id_b = rec_ids[j]
                # If exact duplicate already grouped, skip pair
                dist = self.compute_parameter_distance(params_a, param_cache[id_b])
                if 0.0 < dist <= self.relative_param_tolerance:
                    near_duplicate_pairs.append({
                        "record_a": id_a,
                        "record_b": id_b,
                        "normalized_distance": round(dist, 6),
                        "similarity_percentage": round((1.0 - dist) * 100.0, 2),
                    })

        # Filter out unique hashes from exact groups
        duplicate_geometries = {k: v for k, v in exact_geometry_groups.items() if len(v) > 1}
        duplicate_source_files = {k: v for k, v in source_file_groups.items() if len(v) > 1}

        return {
            "total_records_analyzed": len(records),
            "unique_geometries_count": len(exact_geometry_groups),
            "exact_duplicate_geometry_groups": duplicate_geometries,
            "duplicate_source_file_groups": duplicate_source_files,
            "near_duplicate_pairs": near_duplicate_pairs,
        }
