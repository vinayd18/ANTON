# -*- coding: utf-8 -*-
"""Unit tests for parametric dependencies, transitive propagation, and cycle detection."""

import pytest

from anton.core.geometry_engine import AntonEngine
from anton.models.geometry_schema import ParameterDef


def test_transitive_parameter_dependency():
    """Verify that updating parent parameter A updates child B and grandchild C."""
    e = AntonEngine("Param Project")
    # A = 10, B depends on A (B = 20), C depends on B (C = 40)
    e.add_parameter("param_a", 10.0)
    e.add_parameter("param_b", 20.0, dependencies=["param_a"])
    e.add_parameter("param_c", 40.0, dependencies=["param_b"])

    # Double param_a from 10 to 20 -> ratio = 2.0
    e.update_parameter("param_a", 20.0)

    assert e.project.parameters["param_a"].value == 20.0
    assert e.project.parameters["param_b"].value == 40.0
    assert e.project.parameters["param_c"].value == 80.0


def test_circular_parameter_dependency_rejected():
    """Verify that circular dependencies (A -> B -> A) raise a ValueError."""
    e = AntonEngine("Cycle Project")
    e.add_parameter("param_a", 10.0, dependencies=["param_b"])
    e.add_parameter("param_b", 20.0, dependencies=["param_a"])

    with pytest.raises(ValueError, match="Circular dependency detected"):
        e.update_parameter("param_a", 15.0)


def test_parameter_sync_with_object_dimensions():
    """Verify that updating a parameter automatically updates linked object dimensions."""
    e = AntonEngine("Sync Project")
    m = e.add_material("Copper", "conductor")
    l = e.add_layer("Patch", "patch", m, z_position=0.0016, thickness=35e-6)

    # Define parametric patch width
    e.add_parameter("W_p", 0.04)
    p_id = e.add_rectangle(l, m, width=0.04, height=0.03, name="Patch")

    # Link object parameter dictionary
    patch_obj = e.project.objects[p_id]
    patch_obj.parameters["width"] = ParameterDef(name="W_p", value=0.04)

    # Update parent parameter W_p from 0.04 to 0.06
    e.update_parameter("W_p", 0.06)

    assert patch_obj.parameters["width"].value == 0.06
    assert patch_obj.width == 0.06

