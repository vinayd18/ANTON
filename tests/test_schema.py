# -*- coding: utf-8 -*-
"""Unit tests for canonical Pydantic geometry schema and project model."""

import pytest
from pydantic import ValidationError

from anton.core.geometry_engine import AntonEngine
from anton.models.geometry_schema import (
    AntennaConfig,
    GeometryObject,
    GeometryProject,
    LayerDef,
    MaterialRef,
    ParameterDef,
)


def test_geometry_project_creation():
    project = GeometryProject(project_name="Microstrip Patch")
    assert project.project_name == "Microstrip Patch"
    assert project.units == "m"
    assert project.coordinate_system == "Cartesian"
    assert len(project.geometry_id) > 0


def test_invalid_units_rejected():
    with pytest.raises(ValidationError):
        GeometryProject(project_name="Invalid Units", units="mm")


def test_parameter_def_validation():
    p = ParameterDef(name="W_p", value=0.038, unit="m", description="Patch Width")
    assert p.value == 0.038
    assert p.unit == "m"


def test_material_ref_creation():
    mat = MaterialRef(
        name="Copper",
        category="conductor",
        properties={"conductivity": 5.8e7},
    )
    assert mat.category == "conductor"
    assert mat.properties["conductivity"] == 5.8e7


def test_layer_def_creation():
    layer = LayerDef(
        name="Substrate",
        layer_type="substrate",
        z_position=0.0,
        thickness=0.0016,
        material_id="mat_123",
    )
    assert layer.thickness == 0.0016
    assert layer.layer_type == "substrate"


def test_geometry_object_unknown_type_rejected():
    with pytest.raises(ValidationError):
        GeometryObject(
            object_type="unknown_extrusion_type",
            layer_id="L1",
            material_id="M1",
        )


def test_project_roundtrip_dict():
    e = AntonEngine("Roundtrip Project")
    mid = e.add_material("Copper", "conductor")
    lid = e.add_layer("PatchLayer", "patch", mid, z_position=0.0016, thickness=35e-6)
    oid = e.add_rectangle(lid, mid, width=0.04, height=0.03, name="Patch")

    data = e.to_dict()
    assert isinstance(data, dict)

    reconstructed = AntonEngine.from_dict(data)
    assert reconstructed.project.project_name == "Roundtrip Project"
    assert lid in reconstructed.project.layers
    assert oid in reconstructed.project.objects
    assert reconstructed.project.objects[oid].width == 0.04
