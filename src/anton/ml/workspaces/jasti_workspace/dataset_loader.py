"""
Jasti RF Surrogate Dataset Loader for Manual Fine-Tuning.

Loads leakage-free train/val/test splits for the Hybrid Lorentzian RNN model.
"""

from __future__ import annotations

import os
from typing import Tuple
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from anton.datasets.storage import DatasetStorageManager
from anton.datasets.ml import DatasetSplitter, GenericAdapter, MinMaxScaler


def load_jasti_dataloaders(
    db_path: str = "data/datasets/metadata.db",
    h5_path: str = "data/datasets/arrays.h5",
    batch_size: int = 16,
    random_seed: int = 42,
) -> Tuple[DataLoader, DataLoader, DataLoader, MinMaxScaler, dict]:
    """
    Returns PyTorch DataLoaders for Jasti Hybrid Lorentzian RNN fine-tuning.
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
        empty_loader = DataLoader(TensorDataset(torch.zeros((0, 10)), torch.zeros((0, 101))), batch_size=batch_size)
        return empty_loader, empty_loader, empty_loader, MinMaxScaler(), {"record_count": 0}

    splitter = DatasetSplitter(random_seed=random_seed)
    train_recs, val_recs, test_recs, manifest = splitter.split_records(records)

    adapter = GenericAdapter(target_f_min=1.0, target_f_max=10.0, num_points=101)

    def extract_xy(recs):
        xs, ys = [], []
        for r in recs:
            s = adapter.prepare_sample(r)
            if "s11_db" in s:
                xs.append(s["features_params"])
                ys.append(s["s11_db"])
        if not xs:
            return np.empty((0, 10), dtype=np.float32), np.empty((0, 101), dtype=np.float32)
        return np.stack(xs, axis=0), np.stack(ys, axis=0)

    X_train, Y_train = extract_xy(train_recs)
    X_val, Y_val = extract_xy(val_recs)
    X_test, Y_test = extract_xy(test_recs)

    scaler = MinMaxScaler()
    if len(X_train) > 0:
        scaler.fit(X_train)
        X_train = scaler.transform(X_train)
        if len(X_val) > 0:
            X_val = scaler.transform(X_val)
        if len(X_test) > 0:
            X_test = scaler.transform(X_test)

    train_loader = DataLoader(TensorDataset(torch.from_numpy(X_train), torch.from_numpy(Y_train)), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.from_numpy(X_val), torch.from_numpy(Y_val)), batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(TensorDataset(torch.from_numpy(X_test), torch.from_numpy(Y_test)), batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, scaler, manifest

