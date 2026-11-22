"""
ANTON Backend FastAPI Application.

Main entrypoint providing:
- Electromagnetic Dataset Engineering API (/api/datasets/...)
- Pretrained Model Registry API (/api/ml/...)
- Web Dashboard UIs (/ui/datasets, /ui/models)
- Health check endpoints
"""

from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.api.datasets import router as datasets_router
from backend.app.api.ml import router as ml_router

app = FastAPI(
    title="ANTON Electromagnetic AI Platform",
    description="Research-grade microstrip patch antenna design, electromagnetic dataset engineering, and surrogate ML platform.",
    version="0.1.0",
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(datasets_router)
app.include_router(ml_router)


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "service": "ANTON Backend",
        "version": "0.1.0",
        "dataset_engine": "active",
        "model_registry": "active",
    }


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/ui/datasets")


@app.get("/ui/datasets", response_class=HTMLResponse, tags=["ui"])
def dataset_ui():
    ui_path = os.path.abspath("backend/app/ml/ui/dataset_management_ui.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ANTON Dataset Management UI</h1><p>UI template loading...</p>"


@app.get("/ui/models", response_class=HTMLResponse, tags=["ui"])
def models_ui():
    ui_path = os.path.abspath("backend/app/ml/ui/model_registry_ui.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>ANTON Model Registry UI</h1>"

