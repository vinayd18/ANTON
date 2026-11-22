"""
Automated Tests for Canonical Electromagnetic Dataset Schemas (Stage 3.1).
"""

import pytest
from pydantic import ValidationError

from anton.datasets.schema import (
    AntennaIdentity,
    DatasetRecord,
    ElectromagneticOutputsRecord,
    FarFieldPattern2D,
    MaterialPropertiesRecord,
    ProvenanceRecord,
    QualityStatus,
    SimulationMetadataRecord,
    SourceType,
)


def sample_geometry():
    return {
        "name": "patch_test_01",
        "family": "RECTANGULAR_PATCH",
        "patch": {"shape": "RECTANGULAR", "width": 30.0, "length": 25.0, "metal_thickness": 0.035},
        "substrate": {"width": 60.0, "length": 50.0, "thickness": 1.6, "material": "FR4_epoxy"},
        "ground_plane": {"type": "SOLID", "width": 60.0, "length": 50.0, "metal_thickness": 0.035},
        "feed": {"type": "MICROSTRIP_LINE", "width": 3.0, "position": [0.0, -12.5]},
    }


def test_valid_dataset_record_creation():
    identity = AntennaIdentity(
        design_id="design_001",
        geometry_id="geo_001",
        geometry_hash="a" * 64,
        geometry_family="RECTANGULAR_PATCH",
        dataset_record_id="rec_001",
        data_source=SourceType.HFSS_SIMULATION,
        source_reference="test_hfss.s1p",
    )
    assert identity.is_simulation is True
    assert identity.is_analytical is False

    materials = MaterialPropertiesRecord(
        name="FR4_epoxy",
        permittivity_r=4.4,
        substrate_thickness_mm=1.6,
        loss_tangent=0.02,
    )

    sim_metadata = SimulationMetadataRecord(
        solver_name="HFSS",
        z0_ohm=50.0,
        is_converged=True,
    )

    outputs = ElectromagneticOutputsRecord(
        frequencies_ghz=[1.0, 2.0, 3.0],
        s11_db=[-5.0, -15.0, -3.0],
        s11_magnitude=[0.562, 0.178, 0.708],
        vswr=[3.57, 1.43, 5.85],
    )
    assert outputs.has_complex_s11 is False
    assert "complex_s11" in outputs.missing_outputs

    provenance = ProvenanceRecord(
        source_type=SourceType.HFSS_SIMULATION,
        source_filename="test.s1p",
    )

    record = DatasetRecord(
        antenna_identity=identity,
        geometry=sample_geometry(),
        materials=materials,
        simulation_metadata=sim_metadata,
        outputs=outputs,
        provenance=provenance,
        quality_status=QualityStatus.VERIFIED,
    )

    geo_hash = record.compute_geometry_hash()
    assert len(geo_hash) == 64
    assert record.antenna_identity.design_id == "design_001"


def test_analytical_provenance_flag_enforcement():
    identity = AntennaIdentity(
        design_id="design_analytical_01",
        geometry_id="geo_001",
        geometry_hash="b" * 64,
        geometry_family="RECTANGULAR_PATCH",
        dataset_record_id="rec_analytical_001",
        data_source=SourceType.ANALYTICAL_APPROXIMATION,
        is_simulation=True,  # Attempting to falsely claim simulation
    )
    # Validator must enforce is_analytical=True and is_simulation=False
    assert identity.is_analytical is True
    assert identity.is_simulation is False


def test_invalid_material_properties_rejection():
    # Negative permittivity must raise ValidationError
    with pytest.raises(ValidationError):
        MaterialPropertiesRecord(
            name="invalid_mat",
            permittivity_r=-2.0,
            substrate_thickness_mm=1.6,
        )

    # Zero or negative thickness must raise ValidationError
    with pytest.raises(ValidationError):
        MaterialPropertiesRecord(
            name="invalid_mat",
            permittivity_r=4.4,
            substrate_thickness_mm=0.0,
        )


def test_disordered_frequency_array_rejection():
    # Frequencies must be strictly monotonically increasing
    with pytest.raises(ValidationError):
        ElectromagneticOutputsRecord(
            frequencies_ghz=[2.0, 1.5, 3.0],  # Disordered
            s11_db=[-10.0, -15.0, -5.0],
        )

    # Duplicate frequencies must be rejected
    with pytest.raises(ValidationError):
        ElectromagneticOutputsRecord(
            frequencies_ghz=[1.0, 2.0, 2.0, 3.0],  # Duplicate 2.0
            s11_db=[-5.0, -10.0, -10.0, -5.0],
        )


def test_mismatched_output_array_lengths_rejection():
    with pytest.raises(ValidationError):
        ElectromagneticOutputsRecord(
            frequencies_ghz=[1.0, 2.0, 3.0],
            s11_db=[-10.0, -15.0],  # Length 2 != Length 3
        )


def test_far_field_pattern_2d_validation():
    pat = FarFieldPattern2D(
        plane="E_PLANE",
        frequency_ghz=2.45,
        angles_deg=[-90.0, 0.0, 90.0],
        gain_total_dbi=[-5.0, 6.2, -5.0],
    )
    assert pat.plane == "E_PLANE"

    # Mismatched lengths must fail
    with pytest.raises(ValidationError):
        FarFieldPattern2D(
            plane="E_PLANE",
            frequency_ghz=2.45,
            angles_deg=[-90.0, 0.0, 90.0],
            gain_total_dbi=[-5.0, 6.2],  # Length 2 != Length 3
        )
