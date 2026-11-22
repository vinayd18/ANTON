"""
Automated Tests for Dataset Validation and Quality Control (Stage 3.3).
"""

import pytest

from anton.datasets.schema import (
    AntennaIdentity,
    DatasetRecord,
    ElectromagneticOutputsRecord,
    MaterialPropertiesRecord,
    ProvenanceRecord,
    QualityStatus,
    SimulationMetadataRecord,
    SourceType,
)
from anton.datasets.validation import (
    StructuralValidator,
    ElectromagneticValidator,
    DuplicateDetector,
    QualityClassifier,
    ValidationReportGenerator,
)


def create_test_record(s11_db=None, s11_mag=None, s11_re=None, s11_im=None, is_converged=True, eff=0.85):
    freqs = [1.0, 2.0, 3.0]
    n = len(freqs)
    outputs = ElectromagneticOutputsRecord(
        frequencies_ghz=freqs,
        s11_db=s11_db or [-5.0, -15.0, -4.0],
        s11_magnitude=s11_mag or [0.56, 0.178, 0.63],
        s11_real=s11_re,
        s11_imag=s11_im,
        vswr=[3.5, 1.43, 4.4],
        radiation_efficiency=[eff] * n if eff is not None else None,
    )
    identity = AntennaIdentity(
        design_id="design_val_01",
        geometry_id="geo_val_01",
        geometry_hash="c" * 64,
        geometry_family="RECTANGULAR_PATCH",
        dataset_record_id="rec_val_01",
        data_source=SourceType.HFSS_SIMULATION,
    )
    materials = MaterialPropertiesRecord(
        name="Rogers_5880",
        permittivity_r=2.2,
        substrate_thickness_mm=0.787,
    )
    sim_meta = SimulationMetadataRecord(
        solver_name="HFSS",
        is_converged=is_converged,
    )
    provenance = ProvenanceRecord(
        source_type=SourceType.HFSS_SIMULATION,
        source_filename="test.s1p",
    )
    geometry = {
        "name": "test_patch",
        "family": "RECTANGULAR_PATCH",
        "patch": {"width": 40.0, "length": 35.0, "metal_thickness": 0.035},
        "substrate": {"width": 80.0, "length": 70.0, "thickness": 0.787},
        "feed": {"position": [0.0, -10.0]},
    }
    return DatasetRecord(
        antenna_identity=identity,
        geometry=geometry,
        materials=materials,
        simulation_metadata=sim_meta,
        outputs=outputs,
        provenance=provenance,
    )


def test_structural_validation_pass():
    rec = create_test_record()
    validator = StructuralValidator()
    issues = validator.validate(rec)
    assert len(issues) == 0


def test_passivity_violation_detection():
    # Passivity violation: |S11| = 1.20 (> 1.05)
    rec = create_test_record(s11_mag=[0.5, 1.20, 0.6])
    em_val = ElectromagneticValidator(passivity_tolerance=0.05)
    issues = em_val.validate(rec)

    assert any(iss.code == "NON_PASSIVE_S11" and iss.severity == "ERROR" for iss in issues)


def test_slight_passivity_warning():
    # Minor numerical artifact: |S11| = 1.02 (<= 1.05)
    rec = create_test_record(s11_mag=[0.5, 1.02, 0.6])
    em_val = ElectromagneticValidator(passivity_tolerance=0.05)
    issues = em_val.validate(rec)

    assert any(iss.code == "SLIGHT_PASSIVITY_VIOLATION" and iss.severity == "WARNING" for iss in issues)


def test_efficiency_bounds_validation():
    # Negative efficiency
    rec_neg = create_test_record(eff=-0.1)
    em_val = ElectromagneticValidator()
    issues_neg = em_val.validate(rec_neg)
    assert any("EFFICIENCY" in iss.code for iss in issues_neg)

    # Super-unitary efficiency
    rec_super = create_test_record(eff=1.5)
    issues_super = em_val.validate(rec_super)
    assert any("EFFICIENCY" in iss.code and iss.severity == "ERROR" for iss in issues_super)


def test_duplicate_detection_exact_and_near():
    rec1 = create_test_record()
    rec2 = create_test_record()
    # Modify rec2 ID but keep geometry identical
    rec2.antenna_identity.dataset_record_id = "rec_val_02"

    detector = DuplicateDetector(relative_param_tolerance=0.02)
    audit = detector.analyze_dataset_duplicates([rec1, rec2])

    assert audit["total_records_analyzed"] == 2
    assert audit["unique_geometries_count"] == 1
    assert len(audit["exact_duplicate_geometry_groups"]) == 1


def test_quality_classification_levels():
    classifier = QualityClassifier()

    # 1. Perfectly valid -> VERIFIED
    rec_valid = create_test_record()
    status, issues, passed = classifier.evaluate_record(rec_valid)
    assert status == QualityStatus.VERIFIED
    assert len(passed) >= 3

    # 2. Minor warning (unconverged) -> ACCEPTED_WITH_WARNINGS
    rec_warn = create_test_record(is_converged=False)
    status_w, issues_w, _ = classifier.evaluate_record(rec_warn)
    assert status_w == QualityStatus.ACCEPTED_WITH_WARNINGS

    # 3. Non-passive S11 -> REJECTED
    rec_bad = create_test_record(s11_mag=[0.5, 1.35, 0.5])
    status_r, issues_r, _ = classifier.evaluate_record(rec_bad)
    assert status_r == QualityStatus.REJECTED


def test_validation_report_generator():
    rec = create_test_record()
    rep_gen = ValidationReportGenerator()
    report = rep_gen.generate_record_report(rec)

    assert report["record_id"] == "rec_val_01"
    assert report["quality_status"] == QualityStatus.VERIFIED.value
    assert "STRUCTURAL_INTEGRITY" in report["passed_checks"]

    md = rep_gen.format_markdown_report(report)
    assert "Validation Report" in md
    assert "VERIFIED" in md

