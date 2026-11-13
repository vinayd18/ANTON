# -*- coding: utf-8 -*-
"""Script to generate, validate, and export the 8 canonical example antennas for ANTON Stage 1."""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anton.core.geometry_engine import AntonEngine
from anton.core.units import Units
from anton.feeds.feed_geometry import FeedManager, FeedType
from anton.io.file_exporter import FileExporter
from anton.models.geometry_schema import VertexDef
from anton.operations.boolean import boolean_difference
from anton.validation.validator import GeometryValidator


def build_rectangular_patch() -> AntonEngine:
    """1. Rectangular patch antenna with microstrip line feed on FR4 substrate."""
    e = AntonEngine(project_name="Rectangular Patch Antenna")

    # Parameters
    w_p = e.add_parameter("W_p", Units.mm_to_m(38.0), description="Patch width")
    l_p = e.add_parameter("L_p", Units.mm_to_m(29.0), description="Patch length")
    w_sub = e.add_parameter("W_sub", Units.mm_to_m(60.0), description="Substrate width")
    l_sub = e.add_parameter("L_sub", Units.mm_to_m(60.0), description="Substrate length")
    h_sub = e.add_parameter("h_sub", Units.mm_to_m(1.6), description="Substrate thickness")
    w_f = e.add_parameter("W_f", Units.mm_to_m(3.1), description="Feed line width")
    l_f = e.add_parameter("L_f", Units.mm_to_m(15.5), description="Feed line length")

    # Materials
    m_fr4 = e.add_material(
        name="FR4",
        category="dielectric",
        properties={"relative_permittivity": 4.4, "loss_tangent": 0.02},
        source="Standard FR4 laminate",
    )
    m_cu = e.add_material(
        name="Copper",
        category="conductor",
        properties={"conductivity": 5.8e7},
        source="Annealed copper",
    )

    # Layers
    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_diel = e.add_layer("Substrate", "substrate", m_fr4, z_position=0.0, thickness=Units.mm_to_m(1.6))
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=Units.mm_to_m(1.6), thickness=35e-6)
    l_feed = e.add_layer("Feed", "feed", m_cu, z_position=Units.mm_to_m(1.6), thickness=35e-6)

    # Geometry Objects
    # Ground plane
    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="GroundPlane")
    # Substrate
    e.add_rectangle(l_diel, m_fr4, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="SubstrateBlock")
    # Radiating patch
    p_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(38.0), height=Units.mm_to_m(29.0), center_y=Units.mm_to_m(3.0), name="Radiator")
    # Feed line touching lower edge of patch (y_edge = 3.0 - 14.5 = -11.5 mm)
    # Feed runs from y = -27.0 to -11.5 mm (length = 15.5 mm, center_y = -19.25 mm)
    f_id = e.add_rectangle(l_feed, m_cu, width=Units.mm_to_m(3.1), height=Units.mm_to_m(15.5), center_y=Units.mm_to_m(-19.25), name="FeedLine")

    e.add_connection(f_id, p_id, "direct_edge_feed")
    return e


def build_circular_patch() -> AntonEngine:
    """2. Circular patch antenna on Rogers RO4003C substrate."""
    e = AntonEngine(project_name="Circular Patch Antenna")

    r_p = e.add_parameter("R_p", Units.mm_to_m(16.0), description="Circular patch radius")
    h_sub = e.add_parameter("h_sub", Units.mm_to_m(1.524), description="Substrate height")

    m_ro4003 = e.add_material(
        name="Rogers RO4003C",
        category="dielectric",
        properties={"relative_permittivity": 3.55, "loss_tangent": 0.0027},
    )
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_ro4003, z_position=0.0, thickness=Units.mm_to_m(1.524))
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=Units.mm_to_m(1.524), thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(65.0), height=Units.mm_to_m(65.0), name="Ground")
    e.add_rectangle(l_sub, m_ro4003, width=Units.mm_to_m(65.0), height=Units.mm_to_m(65.0), name="Substrate")
    p_id = e.add_circle(l_patch, m_cu, radius=Units.mm_to_m(16.0), name="CircularDisk")

    # Feed line reaching bottom rim of circle (y = -16.0 mm)
    f_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(3.4), height=Units.mm_to_m(16.5), center_y=Units.mm_to_m(-24.25), name="EdgeFeed")
    e.add_connection(f_id, p_id, "microstrip_edge")
    return e


def build_triangular_patch() -> AntonEngine:
    """3. Equilateral triangular patch antenna on Rogers RO4350B."""
    e = AntonEngine(project_name="Triangular Patch Antenna")

    side = Units.mm_to_m(35.0)
    h_tri = side * math.sqrt(3) / 2.0
    h_sub = Units.mm_to_m(0.762)

    m_ro4350 = e.add_material("Rogers RO4350B", "dielectric", {"relative_permittivity": 3.66, "loss_tangent": 0.0037})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_ro4350, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Ground")
    e.add_rectangle(l_sub, m_ro4350, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Substrate")

    # Equilateral triangle vertices centered at (0, 0)
    v1 = VertexDef(x=-side / 2.0, y=-h_tri / 3.0)
    v2 = VertexDef(x=side / 2.0, y=-h_tri / 3.0)
    v3 = VertexDef(x=0.0, y=2.0 * h_tri / 3.0)
    e.add_triangle(l_patch, m_cu, vertices=[v1, v2, v3], name="TriangularRadiator")
    return e


def build_hexagonal_patch() -> AntonEngine:
    """4. Regular hexagonal patch antenna on RT/Duroid 5880."""
    e = AntonEngine(project_name="Hexagonal Patch Antenna")

    r = Units.mm_to_m(18.0)
    h_sub = Units.mm_to_m(1.575)

    m_duroid = e.add_material("Rogers RT/Duroid 5880", "dielectric", {"relative_permittivity": 2.2, "loss_tangent": 0.0009})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_duroid, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(70.0), height=Units.mm_to_m(70.0), name="Ground")
    e.add_rectangle(l_sub, m_duroid, width=Units.mm_to_m(70.0), height=Units.mm_to_m(70.0), name="Substrate")

    # Hexagon 6 vertices
    hex_verts = []
    for i in range(6):
        angle = math.radians(60.0 * i)
        hex_verts.append(VertexDef(x=r * math.cos(angle), y=r * math.sin(angle)))

    e.add_polygon(l_patch, m_cu, vertices=hex_verts, name="HexagonalRadiator")
    return e


def build_u_slot_patch() -> AntonEngine:
    """5. Wideband U-slot rectangular patch antenna."""
    e = AntonEngine(project_name="U-Slot Rectangular Patch Antenna")

    h_sub = Units.mm_to_m(1.524)
    m_ro4003 = e.add_material("Rogers RO4003C", "dielectric", {"relative_permittivity": 3.55, "loss_tangent": 0.0027})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_ro4003, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(70.0), height=Units.mm_to_m(65.0), name="Ground")
    e.add_rectangle(l_sub, m_ro4003, width=Units.mm_to_m(70.0), height=Units.mm_to_m(65.0), name="Substrate")

    # Base patch
    base_patch_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(36.0), height=Units.mm_to_m(28.0), name="BasePatch")
    base_obj = e.project.objects[base_patch_id]

    # Create U-slot cutters: base horizontal slot + left & right vertical arms
    slot_w = Units.mm_to_m(1.5)
    # Bottom slot
    cut_b_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(16.0), height=slot_w, center_y=Units.mm_to_m(-4.0), name="USlotBase")
    # Left arm
    cut_l_id = e.add_rectangle(l_patch, m_cu, width=slot_w, height=Units.mm_to_m(12.0), center_x=Units.mm_to_m(-7.25), center_y=Units.mm_to_m(2.0), name="USlotLeftArm")
    # Right arm
    cut_r_id = e.add_rectangle(l_patch, m_cu, width=slot_w, height=Units.mm_to_m(12.0), center_x=Units.mm_to_m(7.25), center_y=Units.mm_to_m(2.0), name="USlotRightArm")

    cutters = [e.project.objects[cut_b_id], e.project.objects[cut_l_id], e.project.objects[cut_r_id]]
    slotted_patch = boolean_difference(base_obj, cutters, name="USlottedRadiator", layer_id=l_patch, material_id=m_cu)

    # Clean up temporary cutter objects and replace base patch with slotted patch
    e.remove_object(cut_b_id)
    e.remove_object(cut_l_id)
    e.remove_object(cut_r_id)
    e.remove_object(base_patch_id)

    e.add_object(slotted_patch)
    return e


def build_inset_feed_patch() -> AntonEngine:
    """6. Inset-fed rectangular patch antenna with 50-ohm matching notches."""
    e = AntonEngine(project_name="Inset-Fed Patch Antenna")

    h_sub = Units.mm_to_m(1.6)
    m_fr4 = e.add_material("FR4", "dielectric", {"relative_permittivity": 4.4, "loss_tangent": 0.02})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_fr4, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(70.0), height=Units.mm_to_m(70.0), name="Ground")
    e.add_rectangle(l_sub, m_fr4, width=Units.mm_to_m(70.0), height=Units.mm_to_m(70.0), name="Substrate")

    # Patch: W=38mm, L=30mm, centered at y = 5mm (bottom edge at y = -10mm)
    base_patch_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(38.0), height=Units.mm_to_m(30.0), center_y=Units.mm_to_m(5.0), name="MainPatch")
    base_patch = e.project.objects[base_patch_id]

    # Inset notches: inset depth y_0 = 8 mm, notch width g = 1.0 mm, feed width w_f = 3.0 mm
    # Left notch at x = -2.0 mm, right notch at x = +2.0 mm, depth 8mm (y from -10 to -2 mm)
    notch_w = Units.mm_to_m(1.0)
    notch_d = Units.mm_to_m(8.0)
    y_notch_c = Units.mm_to_m(-6.0)

    n_l_id = e.add_rectangle(l_patch, m_cu, width=notch_w, height=notch_d, center_x=Units.mm_to_m(-2.0), center_y=y_notch_c, name="NotchLeft")
    n_r_id = e.add_rectangle(l_patch, m_cu, width=notch_w, height=notch_d, center_x=Units.mm_to_m(2.0), center_y=y_notch_c, name="NotchRight")

    cutters = [e.project.objects[n_l_id], e.project.objects[n_r_id]]
    notched_patch = boolean_difference(base_patch, cutters, name="NotchedRadiator", layer_id=l_patch, material_id=m_cu)

    e.remove_object(n_l_id)
    e.remove_object(n_r_id)
    e.remove_object(base_patch_id)
    p_id = e.add_object(notched_patch)

    # Inset feed line: runs from y = -30mm to y = -2mm (length = 28mm, center_y = -16mm)
    f_id = e.add_rectangle(l_patch, m_cu, width=Units.mm_to_m(3.0), height=Units.mm_to_m(28.0), center_y=Units.mm_to_m(-16.0), name="InsetFeedLine")
    e.add_connection(f_id, p_id, "inset_feed_connection")
    return e


def build_annular_patch() -> AntonEngine:
    """7. Annular circular ring patch antenna on Alumina substrate."""
    e = AntonEngine(project_name="Annular Ring Patch Antenna")

    h_sub = Units.mm_to_m(1.0)
    m_al = e.add_material("Alumina", "dielectric", {"relative_permittivity": 9.8, "loss_tangent": 0.0001})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_al, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Ground")
    e.add_rectangle(l_sub, m_al, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Substrate")

    # Outer circle: radius = 18 mm, Inner hole: radius = 9 mm
    outer_id = e.add_circle(l_patch, m_cu, radius=Units.mm_to_m(18.0), name="OuterDisk")
    inner_id = e.add_circle(l_patch, m_cu, radius=Units.mm_to_m(9.0), name="InnerHole")

    outer_obj = e.project.objects[outer_id]
    inner_obj = e.project.objects[inner_id]

    ring_obj = boolean_difference(outer_obj, [inner_obj], name="AnnularRingRadiator", layer_id=l_patch, material_id=m_cu)

    e.remove_object(inner_id)
    e.remove_object(outer_id)
    e.add_object(ring_obj)
    return e


def build_custom_polygon_patch() -> AntonEngine:
    """8. Custom stepped polygonal patch radiator with corner perturbations."""
    e = AntonEngine(project_name="Custom Polygonal Patch Antenna")

    h_sub = Units.mm_to_m(0.8)
    m_ro4350 = e.add_material("Rogers RO4350B", "dielectric", {"relative_permittivity": 3.66, "loss_tangent": 0.0037})
    m_cu = e.add_material("Copper", "conductor", {"conductivity": 5.8e7})

    l_gnd = e.add_layer("Ground", "ground", m_cu, z_position=0.0, thickness=35e-6)
    l_sub = e.add_layer("Substrate", "substrate", m_ro4350, z_position=0.0, thickness=h_sub)
    l_patch = e.add_layer("Patch", "patch", m_cu, z_position=h_sub, thickness=35e-6)

    e.add_rectangle(l_gnd, m_cu, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Ground")
    e.add_rectangle(l_sub, m_ro4350, width=Units.mm_to_m(60.0), height=Units.mm_to_m(60.0), name="Substrate")

    # 8-vertex stepped polygon
    pts = [
        (-15.0, -12.0),
        (15.0, -12.0),
        (15.0, 5.0),
        (10.0, 5.0),
        (10.0, 12.0),
        (-10.0, 12.0),
        (-10.0, 5.0),
        (-15.0, 5.0),
    ]
    vertices = [VertexDef(x=Units.mm_to_m(x), y=Units.mm_to_m(y)) for x, y in pts]
    e.add_polygon(l_patch, m_cu, vertices=vertices, name="SteppedPolygonRadiator")
    return e


EXAMPLES = [
    ("rectangular_patch", build_rectangular_patch),
    ("circular_patch", build_circular_patch),
    ("triangular_patch", build_triangular_patch),
    ("hexagonal_patch", build_hexagonal_patch),
    ("u_slot_patch", build_u_slot_patch),
    ("inset_feed_patch", build_inset_feed_patch),
    ("annular_patch", build_annular_patch),
    ("custom_polygon_patch", build_custom_polygon_patch),
]


def main() -> None:
    examples_dir = PROJECT_ROOT / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    validator = GeometryValidator()

    print("=" * 70)
    print("ANTON STAGE 1 — CANONICAL EXAMPLE ANTENNA GENERATION")
    print("=" * 70)

    for slug, builder in EXAMPLES:
        print(f"\n[Generating] {slug}...")
        engine = builder()

        # Validate geometry
        report = validator.validate(engine.project, require_full_stack=True)
        if not report.is_valid:
            print(f"  [ERROR] Validation failed: {report.summary()}")
            for issue in report.issues:
                print(f"    - {issue.code}: {issue.description}")
            sys.exit(1)
        else:
            print(f"  [Validated] {report.summary()}")

        # Export multi-format: JSON, SVG, PNG, STEP, STL
        exported = FileExporter.export_all(engine.project, output_dir=examples_dir, base_name=slug)
        for fmt, path in exported.items():
            size = path.stat().st_size
            print(f"  -> Exported {fmt.upper()}: {path.name} ({size:,} bytes)")

    print("\n" + "=" * 70)
    print("All 8 canonical antenna examples generated, validated, and exported successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
