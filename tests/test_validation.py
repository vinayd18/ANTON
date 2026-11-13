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


def test_layer_stack_vertical_overlap_detected(empty_engine):
    """Regression test: overlapping ground and substrate vertically should trigger a warning."""
    e = empty_engine
    m_cu = e.add_material("Copper", "conductor")
    m_fr4 = e.add_material("FR4", "dielectric")

    # Both ground and substrate starting at z=0 with thickness > 0 -> vertical overlap!
    e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    e.add_layer("Substrate", "substrate", m_fr4, z_position=0.0, thickness=0.0016)

    v = GeometryValidator()
    report = v.validate(e.project)
    assert any(i.code == "WARN_LAYER_VERTICAL_OVERLAP" for i in report.issues)


def test_valid_non_overlapping_stack(engine_with_stack):
    """Regression test: ground at z=-35um, substrate at z=0, patch at z=h has zero stackup overlap."""
    info = engine_with_stack
    e = info["engine"]
    v = GeometryValidator()
    report = v.validate(e.project)
    assert not any(i.code == "WARN_LAYER_VERTICAL_OVERLAP" for i in report.issues)


def test_edge_feed_connected(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    # Patch centered at y=0, height=0.03 (extends from y=-0.015 to y=+0.015)
    p_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.04, height=0.03, center_y=0.0)
    # Feed line from y=-0.025 to y=-0.015 (length=0.01, center_y=-0.02) touches edge at y=-0.015
    f_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.003, height=0.01, center_y=-0.02)

    feed = FeedDef(
        name="EdgeFeed",
        feed_type=FeedType.EDGE,
        geometry_object_id=f_id,
        target_object_id=p_id,
    )
    v = GeometryValidator()
    report = v.validate(e.project, feeds=[feed])
    assert not any(i.code == "WARN_FEED_DISCONNECTED" for i in report.issues)


def test_probe_feed_connectivity(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    p_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.04, height=0.03, center_y=0.0)
    # Probe pin inside patch at (0.005, 0.005)
    probe_feed = FeedDef(
        name="CoaxialProbe",
        feed_type=FeedType.PROBE,
        geometry_object_id=p_id,
        target_object_id=p_id,
        connection_point_x=0.005,
        connection_point_y=0.005,
    )
    v = GeometryValidator()
    report = v.validate(e.project, feeds=[probe_feed])
    assert not any(i.code == "WARN_FEED_DISCONNECTED" for i in report.issues)


def test_multiple_feeds_connectivity(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    p_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.04, height=0.04, center_y=0.0)
    # Feed 1 at bottom edge (y = -0.02)
    f1_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.003, height=0.01, center_y=-0.025)
    # Feed 2 at left edge (x = -0.02)
    f2_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.01, height=0.003, center_x=-0.025)

    feed1 = FeedDef(name="Port1", feed_type=FeedType.MICROSTRIP, geometry_object_id=f1_id, target_object_id=p_id)
    feed2 = FeedDef(name="Port2", feed_type=FeedType.MICROSTRIP, geometry_object_id=f2_id, target_object_id=p_id)

    v = GeometryValidator()
    report = v.validate(e.project, feeds=[feed1, feed2])
    assert not any(i.code == "WARN_FEED_DISCONNECTED" for i in report.issues)


def test_disconnected_parasitic_element_valid(engine_with_stack):
    info = engine_with_stack
    e = info["engine"]
    # Driven patch
    p_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.03, height=0.02, center_x=-0.02)
    # Intentionally disconnected parasitic patch element 10mm away
    parasitic_id = e.add_rectangle(info["patch_id"], info["copper_id"], width=0.03, height=0.02, center_x=0.02)

    v = GeometryValidator()
    report = v.validate(e.project)
    assert report.is_valid
    assert report.error_count == 0


