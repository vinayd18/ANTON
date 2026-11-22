"""
Storage and Data Management Subpackage.
"""

from anton.datasets.storage.database import MetadataDatabase
from anton.datasets.storage.array_store import ArrayStore
from anton.datasets.storage.atomic_io import atomic_write, compute_sha256, is_safe_path
from anton.datasets.storage.exporter import DatasetExporter


class DatasetStorageManager:
    """
    Unified coordinator managing both the relational SQLite metadata store
    and the HDF5 numerical array repository.
    """

    def __init__(
        self,
        db_path: str = "data/datasets/metadata.db",
        h5_path: str = "data/datasets/arrays.h5",
    ):
        self.db = MetadataDatabase(db_path=db_path)
        self.arrays = ArrayStore(h5_path=h5_path)
        self.exporter = DatasetExporter()

    def save_record(self, record) -> str:
        """
        Atomically commits metadata to SQLite and numerical arrays to HDF5.
        """
        rec_id = self.db.save_record(record)
        self.arrays.save_record_arrays(rec_id, record.outputs)
        return rec_id

    def get_record(self, record_id: str):
        """Retrieves record metadata."""
        return self.db.get_record(record_id)

    def load_arrays(self, record_id: str):
        """Loads numerical arrays for record."""
        return self.arrays.load_record_arrays(record_id)


__all__ = [
    "MetadataDatabase",
    "ArrayStore",
    "DatasetStorageManager",
    "DatasetExporter",
    "atomic_write",
    "compute_sha256",
    "is_safe_path",
]
