# -*- coding: utf-8 -*-
"""Pytest fixtures for ANTON Stage 1 test suite."""

import sys
from pathlib import Path
import pytest

# Ensure src is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anton.core.geometry_engine import AntonEngine
from anton.core.units import Units
from anton.models.geometry_schema import GeometryObject, VertexDef


@pytest.fixture
def empty_engine():
    """Provides a fresh, empty AntonEngine instance."""
    return AntonEngine(project_name="Test Antenna")


@pytest.fixture
def engine_with_stack(empty_engine):
    """Provides an AntonEngine pre-populated with standard Copper and FR4 layers."""
    e = empty_engine
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})
    m_fr4 = e.add_material("FR4", "dielectric", {"relative_permittivity": 4.4, "loss_tangent": 0.02})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=-35e-6, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_fr4, z_position=0.0, thickness=Units.mm_to_m(1.6))
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=Units.mm_to_m(1.6), thickness=35e-6)

    return {
        "engine": e,
        "copper_id": m_cu,
        "fr4_id": m_fr4,
        "ground_id": l_gnd,
        "substrate_id": l_sub,
        "patch_id": l_patch,
    }


@pytest.fixture
def sample_rectangle(engine_with_stack):
    """Provides a standard 40mm x 30mm rectangle object."""
    info = engine_with_stack
    e = info["engine"]
    obj_id = e.add_rectangle(
        layer_id=info["patch_id"],
        material_id=info["copper_id"],
        width=Units.mm_to_m(40.0),
        height=Units.mm_to_m(30.0),
        name="TestRect",
    )
    return e.project.objects[obj_id]


@pytest.fixture
def sample_circle(engine_with_stack):
    """Provides a standard 15mm radius circle object."""
    info = engine_with_stack
    e = info["engine"]
    obj_id = e.add_circle(
        layer_id=info["patch_id"],
        material_id=info["copper_id"],
        radius=Units.mm_to_m(15.0),
        name="TestCircle",
    )
    return e.project.objects[obj_id]

