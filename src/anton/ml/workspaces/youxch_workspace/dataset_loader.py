"""
Youxch Patch MLP Dataset Loader for Manual Fine-Tuning.

Loads leakage-free train/val/test splits for the 22-parameter Youxch model.
"""

from __future__ import annotations

import os
from typing import Tuple
import numpy as np

from anton.datasets.storage import DatasetStorageManager
from anton.datasets.ml import DatasetSplitter, YouxchAdapter, StandardScaler
from anton.datasets.schema import QualityStatus


def load_youxch_data(
    db_path: str = "data/datasets/metadata.db",
    h5_path: str = "data/datasets/arrays.h5",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler, dict]:
    """
    Returns (X_train, Y_train, X_val, Y_val, X_test, Y_test, scaler, manifest).
    """
    storage = DatasetStorageManager(db_path=db_path, h5_path=h5_path)
    records_meta = storage.db.list_records(limit=10000)

    records = []
    for meta in records_meta:
        raw_rec = storage.get_record(meta["record_id"])
        if raw_rec:
            from anton.datasets.schema import DatasetRecord
            records.append(DatasetRecord.model_validate(raw_rec))

    if not records:
        empty_x = np.empty((0, 22), dtype=np.float32)
        empty_y = np.empty((0, 202), dtype=np.float32)
        return empty_x, empty_y, empty_x, empty_y, empty_x, empty_y, StandardScaler(), {"record_count": 0}

    splitter = DatasetSplitter(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=random_seed,
    )
    train_recs, val_recs, test_recs, manifest = splitter.split_records(records)

    adapter = YouxchAdapter()

    def process_split(recs):
        xs, ys = [], []
        for r in recs:
            is_comp, _ = adapter.is_record_compatible(r)
            if is_comp:
                x, y = adapter.prepare_sample(r)
                xs.append(x)
                ys.append(y)
        if not xs:
            return np.empty((0, 22), dtype=np.float32), np.empty((0, 202), dtype=np.float32)
        return np.stack(xs, axis=0), np.stack(ys, axis=0)

    X_train, Y_train = process_split(train_recs)
    X_val, Y_val = process_split(val_recs)
    X_test, Y_test = process_split(test_recs)

    scaler = StandardScaler()
    if len(X_train) > 0:
        scaler.fit(X_train)
        X_train = scaler.transform(X_train)
        if len(X_val) > 0:
            X_val = scaler.transform(X_val)
        if len(X_test) > 0:
            X_test = scaler.transform(X_test)

    return X_train, Y_train, X_val, Y_val, X_test, Y_test, scaler, manifest

