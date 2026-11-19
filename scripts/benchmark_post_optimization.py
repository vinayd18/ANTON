# -*- coding: utf-8 -*-
"""Post-optimization performance benchmarking and comparison script for ANTON."""

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

def main():
    post_results = {}
    json_files = list(EXAMPLES_DIR.glob("*.json"))

    # 1. Canonical Geometry Loading (now using optimized model_validate_json directly)
    def load_canonical_geometries():
        projects = []
        for jf in json_files:
            projects.append(GeometryProject.from_json(jf))
        return projects

    print("Post-Optimization: Canonical Geometry Loading...")
    post_results["geometry_loading"] = measure_operation("Canonical Geometry Loading (8 designs)", load_canonical_geometries, iterations=50)

    # 2. Canonical Geometry Serialization
    projects = load_canonical_geometries()
    def serialize_geometries():
        serialized = []
        for p in projects:
            serialized.append(p.model_dump_json())
        return serialized

    print("Post-Optimization: Geometry Serialization...")
    post_results["geometry_serialization"] = measure_operation("Geometry Serialization (8 designs)", serialize_geometries, iterations=50)

    # 3. Geometry Validation
    validator = GeometryValidator()
    def validate_geometries():
        val_results = []
        for p in projects:
            val_results.append(validator.validate(p))
        return val_results

    print("Post-Optimization: Geometry Validation...")
    post_results["geometry_validation"] = measure_operation("Geometry Validation (8 designs)", validate_geometries, iterations=50)

    # 4. Model Registry Loading
    def load_registry():
        return ModelRegistry.build_default_catalog()

    print("Post-Optimization: Model Registry Loading...")
    post_results["model_registry_loading"] = measure_operation("Model Registry Default Catalog Loading", load_registry, iterations=50)

    # 5. Model Metadata Queries (now with inverted indexing)
    reg = load_registry()
    def query_registry():
        q1 = reg.filter_by_capability(TargetCapability.S11_PREDICTION)
        q2 = reg.filter_by_geometry("rectangular_patch")
        q3 = reg.filter_by_category(ModelCategory.CATEGORY_A)
        q4 = reg.search("PINN")
        return q1, q2, q3, q4

    print("Post-Optimization: Model Metadata Queries...")
    post_results["model_metadata_queries"] = measure_operation("Model Metadata Queries (Filter & Search)", query_registry, iterations=100)

    # 6. Checkpoint Discovery (now using cached inspections)
    ckpts = [
        "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt",
        "src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5",
    ]
    def discover_checkpoints():
        inspections = []
        for c in ckpts:
            if os.path.exists(c):
                inspections.append(ModelLoader.inspect_checkpoint(c, use_cache=True))
        return inspections

    print("Post-Optimization: Checkpoint Discovery...")
    post_results["checkpoint_discovery"] = measure_operation("Checkpoint Discovery & Safe Header Inspection", discover_checkpoints, iterations=50)

    # 7. Dataset Metadata Loading
    def load_dataset_metadata():
        model = reg.get_model("metu_simpl_microstrip")
        return model.training_dataset.model_dump()

    print("Post-Optimization: Dataset Metadata Loading...")
    post_results["dataset_metadata_loading"] = measure_operation("Dataset Metadata Loading", load_dataset_metadata, iterations=100)

    # 8. Compatibility Assessment
    evaluator = ModelCompatibilityEvaluator()
    models = reg.list_models()
    def run_compatibility_eval():
        evals = []
        for m in models:
            evals.append(evaluator.evaluate(m))
        return evals

    print("Post-Optimization: Compatibility Assessment...")
    post_results["compatibility_assessment"] = measure_operation("Compatibility Assessment (10 models across 10 dimensions)", run_compatibility_eval, iterations=50)

    # Load baseline
    with open("data/benchmark_results.json", "r", encoding="utf-8") as f:
        baseline_results = json.load(f)

    comparison = {}
    print("\n" + "="*80)
    print(f"{'Operation':<45} | {'Baseline (ms)':<14} | {'Optimized (ms)':<14} | {'Speedup':<8}")
    print("="*80)

    for op_key, post_item in post_results.items():
        base_item = baseline_results.get(op_key, {})
        base_ms = base_item.get("avg_time_ms", 0.0)
        post_ms = post_item["avg_time_ms"]
        speedup = f"{base_ms / post_ms:.2f}x" if post_ms > 0 else "N/A"
        pct_diff = ((base_ms - post_ms) / base_ms) * 100.0 if base_ms > 0 else 0.0
        
        comparison[op_key] = {
            "operation": post_item["operation"],
            "baseline_avg_time_ms": base_ms,
            "optimized_avg_time_ms": post_ms,
            "baseline_peak_mem_kb": base_item.get("peak_memory_kb", 0.0),
            "optimized_peak_mem_kb": post_item["peak_memory_kb"],
            "speedup_factor": round(base_ms / post_ms, 2) if post_ms > 0 else 1.0,
            "time_reduction_percent": round(pct_diff, 1),
        }
        print(f"{post_item['operation']:<45} | {base_ms:<14.4f} | {post_ms:<14.4f} | {speedup:<8}")

    print("="*80)

    with open("data/benchmark_comparison.json", "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2)

    print("Benchmark comparison written to data/benchmark_comparison.json")

if __name__ == "__main__":
    main()

