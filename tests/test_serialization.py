# -*- coding: utf-8 -*-
"""Unit tests for JSON, SVG, and PNG import/export serialization."""

from pathlib import Path
import pytest

from anton.core.geometry_engine import AntonEngine
from anton.io.file_exporter import FileExporter
from anton.io.json_exporter import export_project_json
from anton.io.json_importer import import_project_json


def test_json_roundtrip_preserves_geometry(tmp_path):
    e = AntonEngine("Serialization Roundtrip")
    m_cu = e.add_material("Copper", "conductor")
    m_fr4 = e.add_material("FR4", "dielectric")

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=0.0016, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=0.05, height=0.05, name="GND")
    p_id = e.add_rectangle(l_patch, m_cu, width=0.035, height=0.025, center_x=0.002, center_y=-0.001, name="Patch")

    json_path = tmp_path / "project.json"
    export_project_json(e.project, json_path)
    assert json_path.exists()

    imported = import_project_json(json_path)
    assert imported.project_name == "Serialization Roundtrip"
    assert len(imported.objects) == 2
    assert p_id in imported.objects
    assert imported.objects[p_id].width == 0.035
    assert imported.objects[p_id].height == 0.025
    assert imported.objects[p_id].center_x == 0.002
    assert imported.objects[p_id].center_y == -0.001


def test_invalid_json_raises(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ this is not valid json }", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed JSON syntax"):
        import_project_json(bad_file)


def test_svg_export(tmp_path):
    e = AntonEngine("SVG Test")
    m = e.add_material("Copper", "conductor")
    l = e.add_layer("Patch", "patch", m, z_position=0.0, thickness=35e-6)
    e.add_rectangle(l, m, width=0.04, height=0.03)

    svg_path = tmp_path / "plot.svg"
    FileExporter.export_svg(e.project, svg_path)
    assert svg_path.exists()
    assert svg_path.stat().st_size > 100
    content = svg_path.read_text(encoding="utf-8")
    assert "<svg" in content


def test_png_export(tmp_path):
    e = AntonEngine("PNG Test")
    m = e.add_material("Copper", "conductor")
    l = e.add_layer("Patch", "patch", m, z_position=0.0, thickness=35e-6)
    e.add_rectangle(l, m, width=0.04, height=0.03)

    png_path = tmp_path / "plot.png"
    FileExporter.export_png(e.project, png_path, dpi=100)
    assert png_path.exists()
    assert png_path.stat().st_size > 1000

