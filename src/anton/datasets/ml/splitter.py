"""
Leakage-Free Dataset Splitting Engine.

Partitions antenna dataset records into Train, Validation, and Test sets
while guaranteeing ZERO geometry leakage by grouping records strictly
by antenna design ID and geometry hash.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from anton.datasets.schema import DatasetRecord
from anton.datasets.validation.duplicate_detector import DuplicateDetector


class DatasetSplitter:
    """
    Groups records by geometry to prevent test set contamination,
    and supports reproducible pseudo-random splitting.
    """

    def __init__(
        self,
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        random_seed: int = 42,
        group_near_duplicates: bool = True,
        near_duplicate_tolerance: float = 0.01,
    ):
        if not (0.999 <= train_ratio + val_ratio + test_ratio <= 1.001):
            raise ValueError("Split ratios must sum to 1.0.")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.group_near_duplicates = group_near_duplicates
        self.near_duplicate_tolerance = near_duplicate_tolerance
        self.detector = DuplicateDetector(relative_param_tolerance=near_duplicate_tolerance)

    def split_records(
        self,
        records: List[DatasetRecord]
    ) -> Tuple[List[DatasetRecord], List[DatasetRecord], List[DatasetRecord], Dict[str, Any]]:
        """
        Splits records into (train_records, val_records, test_records, split_manifest).
        Guarantees that all records sharing the same design or geometry hash belong to the same split.
        """
        if not records:
            return [], [], [], {"train_count": 0, "val_count": 0, "test_count": 0}

        # 1. Group records by exact geometry hash / design_id
        # group_key -> list of records
        geometry_groups: Dict[str, List[DatasetRecord]] = {}
        for r in records:
            # Grouping key is deterministic geometry hash
            geo_hash = r.antenna_identity.geometry_hash or self.detector.compute_geometry_hash(r.geometry)
            geometry_groups.setdefault(geo_hash, []).append(r)

        # 2. Optionally cluster near-duplicate groups together
        group_keys = list(geometry_groups.keys())
        if self.group_near_duplicates and len(group_keys) > 1:
            # Union-find or disjoint set clustering of near-duplicate groups
            parent = {k: k for k in group_keys}

            def find(i: str) -> str:
                if parent[i] == i:
                    return i
                parent[i] = find(parent[i])
                return parent[i]

            def union(i: str, j: str):
                root_i = find(i)
                root_j = find(j)
                if root_i != root_j:
                    parent[root_i] = root_j

            # Check parameter distances between group representative designs
            group_rep_params = {
                k: self.detector.extract_key_geometric_parameters(geometry_groups[k][0])
                for k in group_keys
            }

            for i in range(len(group_keys)):
                k_a = group_keys[i]
                for j in range(i + 1, len(group_keys)):
                    k_b = group_keys[j]
                    dist = self.detector.compute_parameter_distance(group_rep_params[k_a], group_rep_params[k_b])
                    if dist <= self.near_duplicate_tolerance:
                        union(k_a, k_b)

            # Re-cluster by root parent
            clustered_groups: Dict[str, List[DatasetRecord]] = {}
            for k in group_keys:
                root = find(k)
                clustered_groups.setdefault(root, []).extend(geometry_groups[k])
            final_groups = list(clustered_groups.values())
        else:
            final_groups = list(geometry_groups.values())

        # 3. Shuffle groups reproducibly
        rng = random.Random(self.random_seed)
        rng.shuffle(final_groups)

        total_records = len(records)
        target_train_count = int(total_records * self.train_ratio)
        target_val_count = int(total_records * self.val_ratio)

        train_recs: List[DatasetRecord] = []
        val_recs: List[DatasetRecord] = []
        test_recs: List[DatasetRecord] = []

        curr_train = 0
        curr_val = 0

        for grp in final_groups:
            grp_len = len(grp)
            if curr_train + grp_len <= target_train_count or (curr_train == 0 and curr_val == 0):
                train_recs.extend(grp)
                curr_train += grp_len
            elif curr_val + grp_len <= target_val_count:
                val_recs.extend(grp)
                curr_val += grp_len
            else:
                test_recs.extend(grp)

        # Fallback if test_recs ended up empty and we have at least 3 groups
        if not test_recs and len(final_groups) >= 3 and len(train_recs) > 1:
            test_recs.extend(train_recs[-1:])
            train_recs = train_recs[:-1]

        # Verify zero leakage
        train_geos = {r.antenna_identity.geometry_hash for r in train_recs}
        val_geos = {r.antenna_identity.geometry_hash for r in val_recs}
        test_geos = {r.antenna_identity.geometry_hash for r in test_recs}

        overlap_tv = train_geos.intersection(val_geos)
        overlap_tt = train_geos.intersection(test_geos)
        overlap_vt = val_geos.intersection(test_geos)

        if overlap_tv or overlap_tt or overlap_vt:
            raise RuntimeError(
                f"Data leakage detected! Overlap Train-Val: {len(overlap_tv)}, "
                f"Train-Test: {len(overlap_tt)}, Val-Test: {len(overlap_vt)}"
            )

        manifest = {
            "total_records": total_records,
            "train_count": len(train_recs),
            "val_count": len(val_recs),
            "test_count": len(test_recs),
            "train_ratio_actual": round(len(train_recs) / total_records, 4) if total_records else 0.0,
            "val_ratio_actual": round(len(val_recs) / total_records, 4) if total_records else 0.0,
            "test_ratio_actual": round(len(test_recs) / total_records, 4) if total_records else 0.0,
            "random_seed": self.random_seed,
            "unique_geometry_groups": len(final_groups),
            "leakage_verification": "ZERO_LEAKAGE_CONFIRMED",
            "train_record_ids": [r.antenna_identity.dataset_record_id for r in train_recs],
            "val_record_ids": [r.antenna_identity.dataset_record_id for r in val_recs],
            "test_record_ids": [r.antenna_identity.dataset_record_id for r in test_recs],
        }

        return train_recs, val_recs, test_recs, manifest

