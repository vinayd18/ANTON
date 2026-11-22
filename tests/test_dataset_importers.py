"""
Automated Tests for Dataset Importers and Format Normalizers (Stage 3.2).
"""

import math
import os
import tempfile
import pytest

from anton.datasets.importers import (
    DatasetImporter,
    TouchstoneImporter,
    HfssCsvImporter,
    CstImporter,
    MetuDatasetAdapter,
    AntennaAiBenchmarkAdapter,
)
from anton.datasets.normalization import (
    convert_frequency_to_ghz,
    s11_to_vswr,
    complex_s11_to_zin,
    detect_resonances_and_bandwidth,
)


def test_unit_normalization():
    assert convert_frequency_to_ghz(1e9, "Hz") == 1.0
    assert convert_frequency_to_ghz(1000.0, "MHz") == 1.0
    assert convert_frequency_to_ghz(1000000.0, "kHz") == 1.0
    assert convert_frequency_to_ghz(2.45, "GHz") == 2.45

    with pytest.raises(ValueError):
        convert_frequency_to_ghz(1.0, "parsecs")


def test_s11_to_vswr_and_zin():
    # |S11| = 0 (perfect match) -> VSWR = 1.0, Zin = 50 + j0
    vswr_match = s11_to_vswr(0.0)
    assert abs(vswr_match - 1.0) < 1e-4

    rin, xin = complex_s11_to_zin(0.0, 0.0, z0=50.0)
    assert abs(rin - 50.0) < 1e-4
    assert abs(xin - 0.0) < 1e-4

    # |S11| = 0.333333 -> VSWR = 2.0
    vswr_2 = s11_to_vswr(1.0 / 3.0)
    assert abs(vswr_2 - 2.0) < 1e-3

    # Clamping for |S11| = 1.0 (open or short)
    vswr_open = s11_to_vswr(1.0)
    assert vswr_open >= 100.0


def test_detect_resonances_and_bandwidth():
    freqs = [1.0, 1.5, 2.0, 2.4, 2.45, 2.5, 3.0, 3.5]
    # S11 with deep resonance at 2.45 GHz
    s11_db = [-2.0, -4.0, -8.0, -18.0, -28.0, -16.0, -6.0, -3.0]

    res_freqs, bw_mhz, fbw = detect_resonances_and_bandwidth(freqs, s11_db, threshold_db=-10.0)
    assert len(res_freqs) >= 1
    assert abs(res_freqs[0] - 2.45) < 0.05
    assert bw_mhz is not None and bw_mhz > 0.0
    assert fbw is not None and fbw > 0.0


def test_touchstone_ri_parsing():
    content = """! Touchstone 1-port test in Real/Imaginary
# GHz S RI R 50
1.0   -0.10   0.05
2.0   -0.02   0.01
3.0    0.50  -0.30
"""
    importer = TouchstoneImporter()
    outputs, meta = importer.parse_string(content, filename="test_ri.s1p")

    assert meta["data_format"] == "RI"
    assert meta["z0_ohm"] == 50.0
    assert outputs.frequencies_ghz == [1.0, 2.0, 3.0]
    assert outputs.has_complex_s11 is True
    assert len(outputs.s11_real) == 3
    assert len(outputs.s11_imag) == 3
    assert len(outputs.zin_real) == 3


def test_touchstone_db_parsing_and_no_phase_fabrication():
    content = """! Touchstone DB format
# MHz S DB R 50
1000   -10.0   45.0
2000   -20.0  -30.0
3000    -5.0   90.0
"""
    importer = TouchstoneImporter()
    outputs, meta = importer.parse_string(content, filename="test_db.s1p")

    assert meta["frequency_unit"] == "mhz"
    assert outputs.frequencies_ghz == [1.0, 2.0, 3.0]
    assert outputs.has_complex_s11 is True
    assert outputs.s11_db == [-10.0, -20.0, -5.0]


def test_touchstone_two_port_s2p():
    content = """# GHz S MA R 50
! Freq S11 S21 S12 S22
2.4   0.2 30.0  0.9 -10.0  0.9 -10.0  0.2 30.0
2.5   0.1 10.0  0.95 -5.0  0.95 -5.0  0.1 10.0
"""
    importer = TouchstoneImporter()
    outputs, meta = importer.parse_string(content, filename="filter.s2p")
    assert meta["extension"] == ".s2p"
    assert outputs.frequencies_ghz == [2.4, 2.5]
    assert outputs.has_complex_s11 is True


def test_hfss_csv_magnitude_only_preservation():
    csv_content = """"Freq [GHz]","dB(S(1,1)) []"
1.0,-4.52
1.5,-7.89
2.0,-18.42
2.5,-6.12
"""
    importer = HfssCsvImporter()
    outputs, meta = importer.parse_s_parameter_string(csv_content, filename="hfss_s11.csv")

    assert outputs.frequencies_ghz == [1.0, 1.5, 2.0, 2.5]
    assert outputs.s11_db == [-4.52, -7.89, -18.42, -6.12]
    # Critical requirement: Magnitude-only S11 must NOT fabricate complex phase or Zin
    assert outputs.has_complex_s11 is False
    assert outputs.s11_real is None
    assert outputs.s11_imag is None
    assert outputs.zin_real is None


def test_hfss_csv_complex_re_im():
    csv_content = """"Freq [GHz]","re(S(1,1)) []","im(S(1,1)) []"
2.0,0.12,-0.08
2.5,0.03,0.01
3.0,-0.20,0.15
"""
    importer = HfssCsvImporter()
    outputs, meta = importer.parse_s_parameter_string(csv_content, filename="hfss_complex.csv")

    assert outputs.frequencies_ghz == [2.0, 2.5, 3.0]
    assert outputs.has_complex_s11 is True
    assert outputs.s11_real == [0.12, 0.03, -0.20]
    assert outputs.zin_real is not None


def test_cst_ascii_import():
    cst_text = """# Frequency / GHz    S1,1/dB
1.000000000000000e+00   -3.500000000000000e+00
1.500000000000000e+00   -9.200000000000000e+00
2.000000000000000e+00   -19.80000000000000e+00
"""
    importer = CstImporter()
    outputs, meta = importer.parse_s_parameter_string(cst_text, filename="cst_sweep.txt")

    assert outputs.frequencies_ghz == [1.0, 1.5, 2.0]
    assert outputs.s11_db == [-3.5, -9.2, -19.8]
    assert meta["solver"] == "CST Studio Suite"


def test_metu_dataset_adapter():
    adapter = MetuDatasetAdapter()
    freqs = [1.0, 2.0, 3.0, 4.0]
    s11_re = [0.1, -0.05, 0.02, -0.2]
    s11_im = [0.05, 0.01, -0.03, 0.15]

    rec = adapter.create_canonical_record(
        record_idx=42,
        patch_width_mm=32.0,
        patch_length_mm=28.0,
        substrate_height_mm=1.524,
        feed_x_mm=0.0,
        feed_y_mm=-7.0,
        s11_re=s11_re,
        s11_im=s11_im,
        frequencies_ghz=freqs,
    )

    assert rec.antenna_identity.geometry_family == "RECTANGULAR_PATCH"
    assert rec.outputs.has_complex_s11 is True
    assert rec.outputs.frequencies_ghz == freqs
    assert rec.materials.permittivity_r == 3.55
    assert rec.antenna_identity.source_reference == "METU-SIMPL Microstrip Patch Benchmark Dataset (HFSS FEM)"
    assert "METU SIMPL" in rec.provenance.citation_or_reference


def test_antenna_ai_benchmark_adapter():
    adapter = AntennaAiBenchmarkAdapter()
    freqs = [2.0, 2.45, 3.0]
    s11_db = [-5.0, -22.0, -4.0]

    rec = adapter.create_canonical_record(
        record_idx=7,
        geometry_family="RECTANGULAR_PATCH",
        dimensions={"width": 35.0, "length": 30.0},
        frequencies_ghz=freqs,
        s11_db=s11_db,
    )

    assert rec.antenna_identity.geometry_family == "RECTANGULAR_PATCH"
    assert rec.outputs.s11_db == s11_db
    assert rec.outputs.has_complex_s11 is False
    assert rec.simulation_metadata.solver_name == "CST Studio Suite"
