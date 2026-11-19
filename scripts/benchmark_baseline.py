# -*- coding: utf-8 -*-
"""Comprehensive performance benchmarking script for ANTON."""

import json
import os
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable, Dict, List

# Ensure src is in sys.path
sys.path.insert(0, str(Path("src").resolve()))

from anton.models.geometry_schema import GeometryProject
from anton.validation.validator import GeometryValidator
from anton.ml.registry import (
    ModelRegistry,
    ModelCompatibilityEvaluator,
    ModelLoader,
    TargetCapability,
    ModelCategory,
)

EXAMPLES_DIR = Path("examples")

def measure_operation(name: str, op_func: Callable[[], Any], iterations: int = 100) -> Dict[str, Any]:
    """Measure execution time and peak memory consumption of an operation."""
    # Warm-up
    for _ in range(5):
        op_func()

    tracemalloc.start()
    start_time = time.perf_counter()

    for _ in range(iterations):
        op_func()

    end_time = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    total_time_ms = (end_time - start_time) * 1000.0
    avg_time_ms = total_time_ms / iterations
    peak_mem_kb = peak / 1024.0

    return {
        "operation": name,
        "iterations": iterations,
        "total_time_ms": round(total_time_ms, 3),
        "avg_time_ms": round(avg_time_ms, 4),
        "peak_memory_kb": round(peak_mem_kb, 2),
    }

def benchmark_suite(out_json_path: str = "data/benchmark_results.json"):
    results = {}

    # 1. Canonical Geometry Loading
    json_files = list(EXAMPLES_DIR.glob("*.json"))
    def load_canonical_geometries():
        projects = []
        for jf in json_files:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects.append(GeometryProject.model_validate(data))
        return projects

    print("Benchmarking Canonical Geometry Loading...")
    results["geometry_loading"] = measure_operation("Canonical Geometry Loading (8 designs)", load_canonical_geometries, iterations=50)

    # 2. Canonical Geometry Serialization
    projects = load_canonical_geometries()
    def serialize_geometries():
        serialized = []
        for p in projects:
            serialized.append(p.model_dump_json())
        return serialized

    print("Benchmarking Geometry Serialization...")
    results["geometry_serialization"] = measure_operation("Geometry Serialization (8 designs)", serialize_geometries, iterations=50)

    # 3. Geometry Validation
    validator = GeometryValidator()
    def validate_geometries():
        val_results = []
        for p in projects:
            val_results.append(validator.validate(p))
        return val_results

    print("Benchmarking Geometry Validation...")
    results["geometry_validation"] = measure_operation("Geometry Validation (8 designs)", validate_geometries, iterations=50)

    # 4. Model Registry Loading
    def load_registry():
        return ModelRegistry.build_default_catalog()

    print("Benchmarking Model Registry Loading...")
    results["model_registry_loading"] = measure_operation("Model Registry Default Catalog Loading", load_registry, iterations=50)

    # 5. Model Metadata Queries
    reg = load_registry()
    def query_registry():
        q1 = reg.filter_by_capability(TargetCapability.S11_PREDICTION)
        q2 = reg.filter_by_geometry("rectangular_patch")
        q3 = reg.filter_by_category(ModelCategory.CATEGORY_A)
        q4 = reg.search("PINN")
        return q1, q2, q3, q4

    print("Benchmarking Model Metadata Queries...")
    results["model_metadata_queries"] = measure_operation("Model Metadata Queries (Filter & Search)", query_registry, iterations=100)

    # 6. Checkpoint Discovery & Verification
    ckpts = [
        "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt",
        "src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5",
    ]
    def discover_checkpoints():
        inspections = []
        for c in ckpts:
            if os.path.exists(c):
                inspections.append(ModelLoader.inspect_checkpoint(c))
        return inspections

    print("Benchmarking Checkpoint Discovery...")
    results["checkpoint_discovery"] = measure_operation("Checkpoint Discovery & Safe Header Inspection", discover_checkpoints, iterations=50)

    # 7. Dataset Metadata Loading
    def load_dataset_metadata():
        model = reg.get_model("metu_simpl_microstrip")
        return model.training_dataset.model_dump()

    print("Benchmarking Dataset Metadata Loading...")
    results["dataset_metadata_loading"] = measure_operation("Dataset Metadata Loading", load_dataset_metadata, iterations=100)

    # 8. Compatibility Assessment
    evaluator = ModelCompatibilityEvaluator()
    models = reg.list_models()
    def run_compatibility_eval():
        evals = []
        for m in models:
            evals.append(evaluator.evaluate(m))
        return evals

    print("Benchmarking Compatibility Assessment...")
    results["compatibility_assessment"] = measure_operation("Compatibility Assessment (10 models across 10 dimensions)", run_compatibility_eval, iterations=50)

    # Save to disk
    out_p = Path(out_json_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nBenchmark complete. Saved to {out_json_path}")
    for k, v in results.items():
        print(f"  [{v['operation']}]: Avg {v['avg_time_ms']} ms | Peak Mem: {v['peak_memory_kb']} KB")

    return results

if __name__ == "__main__":
    benchmark_suite()
