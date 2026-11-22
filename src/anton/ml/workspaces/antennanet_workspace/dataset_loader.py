"""
AntennaNet Dataset Loader for Manual Fine-Tuning.

Connects to the canonical ANTON Dataset Subsystem to load leakage-free
Train, Validation, and Test splits into PyTorch DataLoaders.
"""

from __future__ import annotations

import os
from typing import Optional, Tuple
import numpy as np
import torch
from torch.utils.data import TensorDataset, DataLoader

from anton.datasets.storage import DatasetStorageManager
from anton.datasets.ml import DatasetSplitter, AntennaNetAdapter, MinMaxScaler
from anton.datasets.schema import QualityStatus


def load_antennanet_dataloaders(
    db_path: str = "data/datasets/metadata.db",
    h5_path: str = "data/datasets/arrays.h5",
    batch_size: int = 16,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_seed: int = 42,
    only_verified: bool = True,
) -> Tuple[DataLoader, DataLoader, DataLoader, MinMaxScaler, dict]:
    """
    Loads verified AntennaNet records from ANTON storage, splits them without leakage,
    scales features using training data only, and returns (train_loader, val_loader, test_loader, scaler, manifest).
    """
    storage = DatasetStorageManager(db_path=db_path, h5_path=h5_path)
    
    # Query records
    records_meta = storage.db.list_records(
        geometry_family="RECTANGULAR_PATCH",
        limit=10000,
    )
    
    records = []
    for meta in records_meta:
        if only_verified and meta["quality_status"] not in (QualityStatus.VERIFIED.value, QualityStatus.ACCEPTED_WITH_WARNINGS.value):
            continue
        raw_rec = storage.get_record(meta["record_id"])
        if raw_rec:
            from anton.datasets.schema import DatasetRecord
            records.append(DatasetRecord.model_validate(raw_rec))

    if not records:
        print("Warning: No compatible records found in dataset database. Using fallback empty loaders.")
        dummy_x = torch.zeros((0, 4), dtype=torch.float32)
        dummy_y = torch.zeros((0, 101), dtype=torch.float32)
        empty_loader = DataLoader(TensorDataset(dummy_x, dummy_y), batch_size=batch_size)
        return empty_loader, empty_loader, empty_loader, MinMaxScaler(), {"record_count": 0}

    # Split without leakage
    splitter = DatasetSplitter(
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_seed=random_seed,
    )
    train_recs, val_recs, test_recs, split_manifest = splitter.split_records(records)

    adapter = AntennaNetAdapter()
    X_train, Y_train, _ = adapter.prepare_batch(train_recs)
    X_val, Y_val, _ = adapter.prepare_batch(val_recs)
    X_test, Y_test, _ = adapter.prepare_batch(test_recs)

    # Fit scaler on training data ONLY
    scaler = MinMaxScaler(feature_range=(0.0, 1.0))
    if len(X_train) > 0:
        scaler.fit(X_train)
        X_train_norm = scaler.transform(X_train)
        X_val_norm = scaler.transform(X_val) if len(X_val) > 0 else X_val
        X_test_norm = scaler.transform(X_test) if len(X_test) > 0 else X_test
    else:
        X_train_norm = X_train
        X_val_norm = X_val
        X_test_norm = X_test

    # Convert to PyTorch DataLoaders
    train_dataset = TensorDataset(torch.from_numpy(X_train_norm), torch.from_numpy(Y_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val_norm), torch.from_numpy(Y_val))
    test_dataset = TensorDataset(torch.from_numpy(X_test_norm), torch.from_numpy(Y_test))

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

    return train_loader, val_loader, test_loader, scaler, split_manifest


if __name__ == "__main__":
    t_loader, v_loader, te_loader, sc, man = load_antennanet_dataloaders()
    print("AntennaNet Dataloader loaded:", man)

