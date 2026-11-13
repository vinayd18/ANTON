# -*- coding: utf-8 -*-
"""Unit tests for the material reference database."""

import pytest

from anton.materials.material_database import MaterialDatabase
from anton.models.geometry_schema import MaterialRef


def test_load_default_materials_database():
    db = MaterialDatabase()
    materials = db.list_all()
    assert len(materials) >= 8

    # Verify standard records
    names = {m.name.lower() for m in materials}
    assert "fr4" in names
    assert "copper" in names
    assert "rogers ro4003c" in names
    assert "rogers rt/duroid 5880" in names
    assert "alumina" in names


def test_get_material_by_name():
    db = MaterialDatabase()
    cu = db.get("Copper")
    assert cu is not None
    assert cu.category == "conductor"
    assert cu.properties["conductivity"] == 58000000.0


def test_get_nonexistent_returns_none():
    db = MaterialDatabase()
    assert db.get("NonExistentPlastic") is None


def test_create_custom_dielectric():
    db = MaterialDatabase()
    custom_mat = db.create_dielectric(
        name="CustomPTFE",
        relative_permittivity=2.1,
        loss_tangent=0.0005,
        source="Laboratory Measurement",
    )
    assert custom_mat.id in [m.id for m in db.list_all()]
    fetched = db.get("CustomPTFE")
    assert fetched is not None
    assert fetched.properties["relative_permittivity"] == 2.1


def test_create_custom_conductor():
    db = MaterialDatabase()
    gold = db.create_conductor(name="Gold", conductivity=4.1e7)
    assert gold.category == "conductor"
    assert gold.properties["conductivity"] == 4.1e7


def test_frequency_dependent_material_properties():
    """Verify that frequency-dependent data (tables, dispersion parameters) can be stored."""
    mat = MaterialRef(
        name="DispersiveDielectric",
        category="dielectric",
        properties={
            "relative_permittivity": 4.4,
            "loss_tangent": 0.02,
            "frequency_sweep": {
                "frequencies_hz": [1e9, 2e9, 5e9, 10e9],
                "permittivity_real": [4.42, 4.38, 4.31, 4.25],
                "loss_tangent": [0.018, 0.019, 0.022, 0.025],
            },
            "dispersion_model": "Djordjevic-Sarkar",
        },
        source="Broadband VNA measurement",
        valid_range="1 - 10 GHz",
    )
    db = MaterialDatabase()
    db.add(mat)

    retrieved = db.get("DispersiveDielectric")
    assert retrieved is not None
    assert "frequency_sweep" in retrieved.properties
    assert len(retrieved.properties["frequency_sweep"]["frequencies_hz"]) == 4
    assert retrieved.properties["dispersion_model"] == "Djordjevic-Sarkar"


