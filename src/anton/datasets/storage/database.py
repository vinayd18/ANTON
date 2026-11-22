"""
Metadata Storage Subsystem using SQLite.

Stores:
- Antenna metadata and identity
- Canonical geometry references and hashes
- Material properties and simulation metadata
- Data provenance and audit history
- Quality status and validation reports
- Dataset collections and train/val/test split memberships

Designed for local embedded execution with schema compatible with future PostgreSQL migration.
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from anton.datasets.schema import DatasetRecord, QualityStatus, SourceType
from anton.datasets.storage.atomic_io import is_safe_path


class MetadataDatabase:
    """
    SQLite-backed transactional metadata store for electromagnetic records and datasets.
    """

    def __init__(self, db_path: str = "data/datasets/metadata.db"):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.initialize_schema()

    @contextmanager
    def _connection(self):
        """Context manager that commits transactions and reliably closes the SQLite connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_schema(self) -> None:
        """Creates metadata tables and indices if not already present."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # 1. Dataset records table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_records (
                    record_id TEXT PRIMARY KEY,
                    design_id TEXT NOT NULL,
                    geometry_id TEXT NOT NULL,
                    geometry_hash TEXT NOT NULL,
                    geometry_family TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    quality_status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    z0_ohm REAL NOT NULL,
                    min_freq_ghz REAL NOT NULL,
                    max_freq_ghz REAL NOT NULL,
                    num_freq_points INTEGER NOT NULL,
                    has_complex_s11 INTEGER NOT NULL,
                    has_gain INTEGER NOT NULL,
                    has_patterns INTEGER NOT NULL,
                    tags_json TEXT NOT NULL,
                    materials_json TEXT NOT NULL,
                    simulation_metadata_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    geometry_json TEXT NOT NULL,
                    record_json TEXT NOT NULL
                );
                """
            )

            # Indices for rapid querying and filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_geometry_family ON dataset_records (geometry_family);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_quality_status ON dataset_records (quality_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_source_type ON dataset_records (source_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_geometry_hash ON dataset_records (geometry_hash);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_records_design_id ON dataset_records (design_id);")

            # 2. Quality reports table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS quality_reports (
                    record_id TEXT PRIMARY KEY,
                    quality_status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    passed_checks_json TEXT NOT NULL,
                    failed_checks_json TEXT NOT NULL,
                    warnings_json TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    FOREIGN KEY (record_id) REFERENCES dataset_records (record_id) ON DELETE CASCADE
                );
                """
            )

            # 3. Dataset collections table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    version TEXT NOT NULL,
                    record_count INTEGER DEFAULT 0
                );
                """
            )

            # 4. Dataset membership and split assignment
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset_members (
                    dataset_id TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    split TEXT NOT NULL DEFAULT 'unassigned',
                    PRIMARY KEY (dataset_id, record_id),
                    FOREIGN KEY (dataset_id) REFERENCES datasets (dataset_id) ON DELETE CASCADE,
                    FOREIGN KEY (record_id) REFERENCES dataset_records (record_id) ON DELETE CASCADE
                );
                """
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_members_split ON dataset_members (dataset_id, split);")

    def save_record(self, record: DatasetRecord) -> str:
        """
        Inserts or replaces a DatasetRecord in the metadata store.
        Returns the record_id.
        """
        rec_id = record.antenna_identity.dataset_record_id
        identity = record.antenna_identity
        outputs = record.outputs
        freqs = outputs.frequencies_ghz

        min_f = min(freqs) if freqs else 0.0
        max_f = max(freqs) if freqs else 0.0
        n_pts = len(freqs) if freqs else 0

        has_complex = 1 if outputs.has_complex_s11 else 0
        has_gain = 1 if outputs.gain_dbi is not None else 0
        has_patterns = 1 if (outputs.patterns_2d or outputs.patterns_3d) else 0

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO dataset_records (
                    record_id, design_id, geometry_id, geometry_hash, geometry_family,
                    source_type, quality_status, created_at, z0_ohm,
                    min_freq_ghz, max_freq_ghz, num_freq_points,
                    has_complex_s11, has_gain, has_patterns,
                    tags_json, materials_json, simulation_metadata_json,
                    provenance_json, geometry_json, record_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec_id,
                    identity.design_id,
                    identity.geometry_id,
                    identity.geometry_hash,
                    identity.geometry_family,
                    identity.data_source.value,
                    record.quality_status.value,
                    identity.created_at,
                    record.simulation_metadata.z0_ohm,
                    min_f,
                    max_f,
                    n_pts,
                    has_complex,
                    has_gain,
                    has_patterns,
                    json.dumps(record.tags),
                    record.materials.model_dump_json(),
                    record.simulation_metadata.model_dump_json(),
                    record.provenance.model_dump_json(),
                    json.dumps(record.geometry),
                    record.model_dump_json(),
                ),
            )

            # Save quality report if present
            if record.quality_report:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO quality_reports (
                        record_id, quality_status, timestamp, passed_checks_json,
                        failed_checks_json, warnings_json, report_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec_id,
                        record.quality_report.get("quality_status", "UNVERIFIED"),
                        record.quality_report.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                        json.dumps(record.quality_report.get("passed_checks", [])),
                        json.dumps(record.quality_report.get("failed_checks", [])),
                        json.dumps(record.quality_report.get("warnings", [])),
                        json.dumps(record.quality_report),
                    ),
                )

        return rec_id

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves raw record dictionary by record_id."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT record_json FROM dataset_records WHERE record_id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["record_json"])
        return None

    def list_records(
        self,
        geometry_family: Optional[str] = None,
        source_type: Optional[str] = None,
        quality_status: Optional[str] = None,
        min_freq: Optional[float] = None,
        max_freq: Optional[float] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Filters and lists dataset records with pagination.
        """
        query = ["SELECT record_id, design_id, geometry_id, geometry_hash, geometry_family, source_type, quality_status, created_at, z0_ohm, min_freq_ghz, max_freq_ghz, num_freq_points, has_complex_s11, has_gain, has_patterns, tags_json FROM dataset_records WHERE 1=1"]
        params: List[Any] = []

        if geometry_family:
            query.append("AND geometry_family = ?")
            params.append(geometry_family)
        if source_type:
            query.append("AND source_type = ?")
            params.append(source_type)
        if quality_status:
            query.append("AND quality_status = ?")
            params.append(quality_status)
        if min_freq is not None:
            query.append("AND max_freq_ghz >= ?")
            params.append(min_freq)
        if max_freq is not None:
            query.append("AND min_freq_ghz <= ?")
            params.append(max_freq)

        query.append("ORDER BY created_at DESC LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        results = []
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(" ".join(query), params)
            for row in cursor.fetchall():
                results.append({
                    "record_id": row["record_id"],
                    "design_id": row["design_id"],
                    "geometry_id": row["geometry_id"],
                    "geometry_hash": row["geometry_hash"],
                    "geometry_family": row["geometry_family"],
                    "source_type": row["source_type"],
                    "quality_status": row["quality_status"],
                    "created_at": row["created_at"],
                    "z0_ohm": row["z0_ohm"],
                    "min_freq_ghz": row["min_freq_ghz"],
                    "max_freq_ghz": row["max_freq_ghz"],
                    "num_freq_points": row["num_freq_points"],
                    "has_complex_s11": bool(row["has_complex_s11"]),
                    "has_gain": bool(row["has_gain"]),
                    "has_patterns": bool(row["has_patterns"]),
                    "tags": json.loads(row["tags_json"]),
                })

        return results

    def save_quality_report(
        self,
        record_id: str,
        report: Dict[str, Any],
        conn: Optional[sqlite3.Connection] = None
    ) -> None:
        """Saves a validation report for a record."""
        def _execute(target_conn):
            cursor = target_conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO quality_reports (
                    record_id, quality_status, timestamp, passed_checks_json,
                    failed_checks_json, warnings_json, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    report.get("quality_status", "UNVERIFIED"),
                    report.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                    json.dumps(report.get("passed_checks", [])),
                    json.dumps(report.get("failed_checks", [])),
                    json.dumps(report.get("warnings", [])),
                    json.dumps(report),
                ),
            )
            cursor.execute(
                "UPDATE dataset_records SET quality_status = ? WHERE record_id = ?",
                (report.get("quality_status", "UNVERIFIED"), record_id),
            )

        if conn is not None:
            _execute(conn)
        else:
            with self._connection() as c:
                _execute(c)

    def get_quality_report(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves validation report by record_id."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT report_json FROM quality_reports WHERE record_id = ?", (record_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["report_json"])
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Computes summary statistics across all dataset records.
        """
        with self._connection() as conn:
            cursor = conn.cursor()

            # Total counts
            cursor.execute("SELECT COUNT(*) AS total_records, COUNT(DISTINCT design_id) AS total_designs, COUNT(DISTINCT geometry_hash) AS unique_geometries FROM dataset_records;")
            base = cursor.fetchone()
            total_records = base["total_records"]
            total_designs = base["total_designs"]
            unique_geometries = base["unique_geometries"]

            # By geometry family
            cursor.execute("SELECT geometry_family, COUNT(*) AS cnt FROM dataset_records GROUP BY geometry_family;")
            families = {r["geometry_family"]: r["cnt"] for r in cursor.fetchall()}

            # By quality status
            cursor.execute("SELECT quality_status, COUNT(*) AS cnt FROM dataset_records GROUP BY quality_status;")
            qualities = {r["quality_status"]: r["cnt"] for r in cursor.fetchall()}

            # By source type
            cursor.execute("SELECT source_type, COUNT(*) AS cnt FROM dataset_records GROUP BY source_type;")
            sources = {r["source_type"]: r["cnt"] for r in cursor.fetchall()}

            # Output capabilities
            cursor.execute("SELECT SUM(has_complex_s11) AS complex_cnt, SUM(has_gain) AS gain_cnt, SUM(has_patterns) AS pat_cnt FROM dataset_records;")
            caps = cursor.fetchone()

            return {
                "total_records": total_records,
                "total_antenna_designs": total_designs,
                "unique_geometries": unique_geometries,
                "geometry_family_distribution": families,
                "quality_status_distribution": qualities,
                "source_type_distribution": sources,
                "available_outputs": {
                    "complex_s11_count": caps["complex_cnt"] or 0,
                    "gain_count": caps["gain_cnt"] or 0,
                    "radiation_patterns_count": caps["pat_cnt"] or 0,
                },
            }

    def create_dataset_collection(
        self,
        dataset_id: str,
        name: str,
        description: str = "",
        version: str = "1.0.0"
    ) -> None:
        """Registers a named dataset collection."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO datasets (
                    dataset_id, name, description, created_at, version, record_count
                ) VALUES (?, ?, ?, ?, ?, 0)
                """,
                (
                    dataset_id,
                    name,
                    description,
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    version,
                ),
            )

    def assign_to_split(self, dataset_id: str, record_id: str, split: str = "train") -> None:
        """Assigns a record to a split ('train', 'val', 'test') within a dataset collection."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO dataset_members (dataset_id, record_id, split)
                VALUES (?, ?, ?)
                """,
                (dataset_id, record_id, split),
            )
            cursor.execute(
                """
                UPDATE datasets SET record_count = (
                    SELECT COUNT(*) FROM dataset_members WHERE dataset_id = ?
                ) WHERE dataset_id = ?
                """,
                (dataset_id, dataset_id),
            )

    def get_dataset_members(
        self,
        dataset_id: str,
        split: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """Returns list of (record_id, split) for a dataset collection."""
        with self._connection() as conn:
            cursor = conn.cursor()
            if split:
                cursor.execute(
                    "SELECT record_id, split FROM dataset_members WHERE dataset_id = ? AND split = ?",
                    (dataset_id, split),
                )
            else:
                cursor.execute(
                    "SELECT record_id, split FROM dataset_members WHERE dataset_id = ?",
                    (dataset_id,),
                )
            return [(r["record_id"], r["split"]) for r in cursor.fetchall()]
