# -*- coding: utf-8 -*-
"""Unit tests for the geometry validation engine."""

import pytest

from anton.core.geometry_engine import AntonEngine
from anton.feeds.feed_geometry import FeedDef, FeedType
from anton.models.geometry_schema import GeometryObject
from anton.validation.validator import GeometryValidator


def test_valid_project_passes(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    e.add_rectangle(info["patch_id"], info["copper_id"], width=0.04, height=0.03)

    v = GeometryValidator()
    report = v.validate(e.project)
    assert report.is_valid
    assert report.error_count == 0


def test_negative_dimension_detected(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    e.add_rectangle(info["patch_id"], info["copper_id"], width=-0.04, height=0.03)

    v = GeometryValidator()
    report = v.validate(e.project)
    assert not report.is_valid
    assert any(i.code == "ERR_NONPOSITIVE_WIDTH" for i in report.issues)


def test_zero_radius_detected(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    e.add_circle(info["patch_id"], info["copper_id"], radius=0.0)

    v = GeometryValidator()
    report = v.validate(e.project)
    assert not report.is_valid
    assert any(i.code == "ERR_NONPOSITIVE_RADIUS" for i in report.issues)


def test_missing_layer_reference_detected(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    # Register an object pointing to a ghost layer
    obj = GeometryObject(
        object_type="rectangle",
        layer_id="non_existent_layer_id",
        material_id=info["copper_id"],
        width=0.04,
        height=0.03,
    )
    e.project.objects[obj.id] = obj

    v = GeometryValidator()
    report = v.validate(e.project)
    assert not report.is_valid
    assert any(i.code == "ERR_MISSING_LAYER_REF" for i in report.issues)


def test_missing_material_reference_detected(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    obj = GeometryObject(
        object_type="rectangle",
        layer_id=info["patch_id"],
        material_id="non_existent_material_id",
        width=0.04,
        height=0.03,
    )
    e.project.objects[obj.id] = obj

    v = GeometryValidator()
    report = v.validate(e.project)
    assert not report.is_valid
    assert any(i.code == "ERR_MISSING_MATERIAL_REF" for i in report.issues)


def test_feed_connectivity_warning(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]

    p_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.04, height=0.03, center_y=0.05)
    f_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.003, height=0.01, center_y=-0.05)

    feed = FeedDef(
        name="DisconnectedFeed",
        feed_type=FeedType.MICROSTRIP,
        geometry_object_id=f_id,
        target_object_id=p_id,
    )

    v = GeometryValidator()
    report = v.validate(e.project, feeds=[feed])
    assert report.is_valid  # Still valid (it's a warning, not fatal error)
    assert any(i.code == "WARN_FEED_DISCONNECTED" for i in report.issues)


def test_require_full_stack_warning(empty_engine):
    # Empty project missing ground, substrate, patch
    v = GeometryValidator()
    report = v.validate(empty_engine.project, require_full_stack=True)
    assert any(i.code == "WARN_INCOMPLETE_STACK" for i in report.issues)
