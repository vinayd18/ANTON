"""
Generator for ANTON Scientific Data Analysis Jupyter Notebooks.
"""

import json
import os


def create_notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.13"},
            "orig_nbformat": 4
        },
        "nbformat": 4,
        "nbformat_minor": 5
    }


def md_cell(source):
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code_cell(source):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": source.splitlines(keepends=True)}


def main():
    os.makedirs("notebooks/analysis", exist_ok=True)

    # 1. 01_dataset_inspection.ipynb
    nb1 = create_notebook([
        md_cell("# ANTON — Notebook 01: Electromagnetic Dataset Inspection\n\nQueries and inspects the canonical ANTON electromagnetic dataset store (SQLite metadata + HDF5 numerical arrays)."),
        code_cell("""import os
import pandas as pd
import numpy as np
from anton.datasets.storage import DatasetStorageManager
from anton.datasets.schema import QualityStatus

storage = DatasetStorageManager()
stats = storage.db.get_statistics()
print("=== ANTON Dataset Subsystem Statistics ===")
for k, v in stats.items():
    print(f"{k}: {v}")
"""),
        code_cell("""records = storage.db.list_records(limit=100)
if not records:
    print("[EMPTY STATE] No simulation or measurement records are currently present in the production dataset.")
    print("To populate, import Touchstone or CSV files via the ANTON web dashboard or Python API.")
else:
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} records:")
    print(df[['record_id', 'design_id', 'geometry_family', 'min_freq_ghz', 'max_freq_ghz', 'quality_status']])
""")
    ])

    with open("notebooks/analysis/01_dataset_inspection.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb1, f, indent=2)

    # 2. 02_s11_impedance_vswr_analysis.ipynb
    nb2 = create_notebook([
        md_cell("# ANTON — Notebook 02: S11, VSWR, and Input Impedance Analysis\n\nVisualizes frequency responses, detects resonant frequencies, computes -10 dB bandwidth, and analyzes complex input impedance Zin."),
        code_cell("""import numpy as np
import matplotlib.pyplot as plt
from anton.datasets.storage import DatasetStorageManager
from anton.datasets.normalization import detect_resonances_and_bandwidth

storage = DatasetStorageManager()
records = storage.db.list_records(limit=1)

if not records:
    print("[EMPTY STATE] No simulation records available for visualization.")
else:
    rec_id = records[0]['record_id']
    arrays = storage.arrays.load_record_arrays(rec_id)
    freqs = arrays['frequencies_ghz']
    s11_db = arrays.get('s11_db')
    vswr = arrays.get('vswr')

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    if s11_db is not None:
        ax1.plot(freqs, s11_db, 'b-', lw=2, label='S11 (dB)')
        ax1.axhline(-10, color='r', linestyle='--', label='-10 dB Threshold')
        ax1.set_xlabel('Frequency (GHz)')
        ax1.set_ylabel('S11 (dB)')
        ax1.set_title(f'Return Loss — {rec_id}')
        ax1.grid(True)
        ax1.legend()

    if vswr is not None:
        ax2.plot(freqs, vswr, 'g-', lw=2, label='VSWR')
        ax2.axhline(2.0, color='r', linestyle='--', label='VSWR = 2.0')
        ax2.set_xlabel('Frequency (GHz)')
        ax2.set_ylabel('VSWR')
        ax2.set_title('Voltage Standing Wave Ratio')
        ax2.set_ylim(1.0, 10.0)
        ax2.grid(True)
        ax2.legend()

    plt.tight_layout()
    plt.show()
"""),
        code_cell("""# Complex Input Impedance Analysis (Rin + j Xin)
if records:
    rec_id = records[0]['record_id']
    arrays = storage.arrays.load_record_arrays(rec_id)
    zin_re = arrays.get('zin_real')
    zin_im = arrays.get('zin_imag')

    if zin_re is not None and zin_im is not None:
        plt.figure(figsize=(8, 5))
        plt.plot(arrays['frequencies_ghz'], zin_re, 'r-', lw=2, label='R_in (Resistance, Ohm)')
        plt.plot(arrays['frequencies_ghz'], zin_im, 'b--', lw=2, label='X_in (Reactance, Ohm)')
        plt.axhline(50, color='k', linestyle=':', label='Z0 = 50 Ohm')
        plt.axhline(0, color='gray', linestyle=':')
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Impedance (Ohm)')
        plt.title('Complex Input Impedance')
        plt.grid(True)
        plt.legend()
        plt.show()
    else:
        print("[INFO] Record contains magnitude-only S11. Zin is not calculated to prevent fabricated phase.")
""")
    ])

    with open("notebooks/analysis/02_s11_impedance_vswr_analysis.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb2, f, indent=2)

    # 3. 03_gain_radiation_patterns.ipynb
    nb3 = create_notebook([
        md_cell("# ANTON — Notebook 03: Gain, Efficiency, and Radiation Patterns\n\nAnalyzes antenna realized gain curves, radiation efficiency, and 2D polar far-field patterns."),
        code_cell("""import numpy as np
import matplotlib.pyplot as plt
from anton.datasets.storage import DatasetStorageManager

storage = DatasetStorageManager()
records = storage.db.list_records(limit=10)

has_gain_rec = None
for r in records:
    if r['has_gain'] or r['has_patterns']:
        has_gain_rec = r
        break

if not has_gain_rec:
    print("[EMPTY STATE] No records with exported gain or radiation patterns found.")
else:
    rec_id = has_gain_rec['record_id']
    arrays = storage.arrays.load_record_arrays(rec_id)
    if 'gain_dbi' in arrays:
        plt.figure(figsize=(8, 4))
        plt.plot(arrays['frequencies_ghz'], arrays['gain_dbi'], 'purple', lw=2, label='Realized Gain (dBi)')
        plt.xlabel('Frequency (GHz)')
        plt.ylabel('Gain (dBi)')
        plt.title(f'Gain vs Frequency — {rec_id}')
        plt.grid(True)
        plt.legend()
        plt.show()
""")
    ])

    with open("notebooks/analysis/03_gain_radiation_patterns.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb3, f, indent=2)

    # 4. 04_dataset_quality_and_sources.ipynb
    nb4 = create_notebook([
        md_cell("# ANTON — Notebook 04: Dataset Quality, Sources, and Training Readiness\n\nAssesses quality grading breakdown, solver source provenance, and duplicate design clustering."),
        code_cell("""import pandas as pd
import matplotlib.pyplot as plt
from anton.datasets.storage import DatasetStorageManager

storage = DatasetStorageManager()
stats = storage.db.get_statistics()

print("Quality Status Counts:")
for q, cnt in stats['quality_status_distribution'].items():
    print(f"  {q}: {cnt}")

print("\nData Source Counts:")
for s, cnt in stats['source_type_distribution'].items():
    print(f"  {s}: {cnt}")
"""),
        code_cell("""# Duplicate and near-duplicate audit
from anton.datasets.validation.duplicate_detector import DuplicateDetector
from anton.datasets.schema import DatasetRecord

records_meta = storage.db.list_records(limit=500)
records = []
for m in records_meta:
    raw = storage.get_record(m['record_id'])
    if raw:
        records.append(DatasetRecord.model_validate(raw))

if records:
    detector = DuplicateDetector(relative_param_tolerance=0.01)
    dup_report = detector.analyze_dataset_duplicates(records)
    print("=== Duplicate Geometry Audit ===")
    print(f"Total Records: {dup_report['total_records_analyzed']}")
    print(f"Unique Geometries: {dup_report['unique_geometries_count']}")
    print(f"Near Duplicate Pairs: {len(dup_report['near_duplicate_pairs'])}")
else:
    print("[EMPTY STATE] No records available to audit duplicates.")
""")
    ])

    with open("notebooks/analysis/04_dataset_quality_and_sources.ipynb", "w", encoding="utf-8") as f:
        json.dump(nb4, f, indent=2)

    print("Successfully generated all 4 scientific analysis notebooks in notebooks/analysis/.")


if __name__ == "__main__":
    main()
