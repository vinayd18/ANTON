"""
FastAPI Model Registry and Pretrained ML Router.

Endpoints for:
- Querying registered pretrained models and surrogate networks
- Retrieving compatibility assessments and target capabilities
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/ml", tags=["ml"])

CATALOG_PATH = os.path.abspath("src/anton/ml/reports/model_registry_catalog.json")


def load_catalog() -> Dict[str, Any]:
    if not os.path.exists(CATALOG_PATH):
        return {}
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/models", summary="List Registered Models")
def list_models() -> Dict[str, Any]:
    cat = load_catalog()
    models = list(cat.values())
    return {
        "status": "success",
        "total_models": len(models),
        "models": models,
    }


@router.get("/models/{model_id}", summary="Get Model Details")
def get_model(model_id: str) -> Dict[str, Any]:
    cat = load_catalog()
    if model_id not in cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found in registry.",
        )
    return cat[model_id]


@router.get("/models/{model_id}/compatibility", summary="Get Model Compatibility Assessment")
def get_model_compatibility(model_id: str) -> Dict[str, Any]:
    cat = load_catalog()
    if model_id not in cat:
        raise HTTPException(status_code=404, detail="Model not found.")
    m = cat[model_id]
    return {
        "model_id": model_id,
        "model_name": m.get("model_name"),
        "compatibility_status": m.get("compatibility_status"),
        "geometry_compatibility": m.get("geometry_compatibility"),
        "target_capabilities": m.get("target_capabilities"),
        "fine_tuning_available": m.get("fine_tuning_available"),
        "production_readiness": m.get("production_readiness"),
    }

