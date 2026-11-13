# -*- coding: utf-8 -*-
"""Unit tests for CadQuery 3D solid generation and CAD export."""

from pathlib import Path
import pytest

from anton.cad.cad_exporter import CADExporter
from anton.cad.solid_generator import SolidGenerator
from anton.core.geometry_engine import AntonEngine


def test_cad_solid_and_assembly_generation(tmp_path):
    pytest.importorskip("cadquery")

    e = AntonEngine("CAD Test Project")
    m_cu = e.add_material("Copper", "conductor")
    m_fr4 = e.add_material("FR4", "dielectric")

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=-35e-6, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_fr4, z_position=0.0, thickness=0.0016)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=0.0016, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=0.06, height=0.06, name="Ground")
    e.add_rectangle(l_sub, m_fr4, width=0.06, height=0.06, name="Substrate")
    p_id = e.add_rectangle(l_patch, m_cu, width=0.038, height=0.029, name="Patch")

    generator = SolidGenerator(e.project)
    patch_obj = e.project.objects[p_id]

    # Test single solid generation
    patch_solid = generator.generate_solid(patch_obj)
    assert patch_solid is not None

    # Test complete assembly generation
    assembly = generator.generate_assembly()
    assert assembly is not None

    # Test STEP export
    step_file = tmp_path / "antenna.step"
    CADExporter.export_step(assembly, step_file)
    assert step_file.exists()
    assert step_file.stat().st_size > 500

    # Test STL export
    stl_file = tmp_path / "antenna.stl"
    CADExporter.export_stl(assembly, stl_file)
    assert stl_file.exists()
    assert stl_file.stat().st_size > 500


def test_circle_cad_solid_generation():
    pytest.importorskip("cadquery")

    e = AntonEngine("Circle CAD")
    m_cu = e.add_material("Copper", "conductor")
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=0.0, thickness=35e-6)
    c_id = e.add_circle(l_patch, m_cu, radius=0.015, name="Disk")

    generator = SolidGenerator(e.project)
    disk_solid = generator.generate_solid(e.project.objects[c_id])
    assert disk_solid is not None

