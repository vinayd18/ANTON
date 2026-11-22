"""
Automated Tests for ML-Ready Dataset Preparation (Stage 3.6).
"""

import numpy as np
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
from anton.datasets.ml import (
    DatasetSplitter,
    FrequencyGridAligner,
    FeatureExtractor,
    MinMaxScaler,
    StandardScaler,
    AntennaNetAdapter,
    YouxchAdapter,
    GenericAdapter,
)


def make_record(rec_id: str, design_id: str, geo_hash: str, family="RECTANGULAR_PATCH"):
    freqs = list(np.linspace(1.0, 6.0, 101))
    s11 = list(-5.0 - 15.0 * np.exp(-((np.array(freqs) - 2.45) / 0.2) ** 2))
    outputs = ElectromagneticOutputsRecord(
        frequencies_ghz=freqs,
        s11_db=s11,
        s11_magnitude=[float(10 ** (v / 20.0)) for v in s11],
        vswr=[float((1 + 10 ** (v / 20.0)) / max(1e-4, 1 - 10 ** (v / 20.0))) for v in s11],
    )
    identity = AntennaIdentity(
        design_id=design_id,
        geometry_id=f"geo_{design_id}",
        geometry_hash=geo_hash,
        geometry_family=family,
        dataset_record_id=rec_id,
        data_source=SourceType.HFSS_SIMULATION,
    )
    materials = MaterialPropertiesRecord(
        name="FR4_epoxy",
        permittivity_r=4.4,
        substrate_thickness_mm=1.6,
    )
    sim_meta = SimulationMetadataRecord(solver_name="HFSS", is_converged=True)
    provenance = ProvenanceRecord(source_type=SourceType.HFSS_SIMULATION)
    geometry = {
        "name": f"antenna_{rec_id}",
        "family": family,
        "patch": {"shape": family, "width": 32.0, "length": 28.0, "metal_thickness": 0.035},
        "substrate": {"width": 60.0, "length": 60.0, "thickness": 1.6},
        "feed": {"position": [0.0, -14.0]},
    }
    return DatasetRecord(
        antenna_identity=identity,
        geometry=geometry,
        materials=materials,
        simulation_metadata=sim_meta,
        outputs=outputs,
        provenance=provenance,
        quality_status=QualityStatus.VERIFIED,
    )


def test_leakage_free_dataset_splitting():
    # Create 10 records across 4 distinct designs (with repeated variations)
    records = [
        make_record("r1", "d1", "hash_1"),
        make_record("r2", "d1", "hash_1"),  # Repeated design d1
        make_record("r3", "d2", "hash_2"),
        make_record("r4", "d2", "hash_2"),  # Repeated design d2
        make_record("r5", "d3", "hash_3"),
        make_record("r6", "d3", "hash_3"),
        make_record("r7", "d4", "hash_4"),
        make_record("r8", "d4", "hash_4"),
        make_record("r9", "d4", "hash_4"),
        make_record("r10", "d4", "hash_4"),
    ]

    splitter = DatasetSplitter(train_ratio=0.5, val_ratio=0.25, test_ratio=0.25, random_seed=42)
    train, val, test, manifest = splitter.split_records(records)

    assert len(train) + len(val) + len(test) == 10
    assert manifest["leakage_verification"] == "ZERO_LEAKAGE_CONFIRMED"

    # Verify zero design overlap
    train_designs = {r.antenna_identity.design_id for r in train}
    val_designs = {r.antenna_identity.design_id for r in val}
    test_designs = {r.antenna_identity.design_id for r in test}

    assert len(train_designs.intersection(val_designs)) == 0
    assert len(train_designs.intersection(test_designs)) == 0
    assert len(val_designs.intersection(test_designs)) == 0


def test_frequency_grid_pchip_resampling():
    aligner = FrequencyGridAligner(target_f_min=1.0, target_f_max=5.0, num_points=101)

    # 1. Compatible sweep
    src_f = [0.8, 1.5, 2.5, 3.5, 5.2]
    src_v = [-2.0, -10.0, -25.0, -8.0, -1.0]
    assert aligner.is_compatible(src_f) is True

    resampled = aligner.resample_curve(src_f, src_v)
    assert len(resampled) == 101
    assert isinstance(resampled, np.ndarray)

    # 2. Incompatible sweep (narrower than target grid) -> MUST REJECT
    narrow_f = [2.0, 3.0, 4.0]
    narrow_v = [-5.0, -15.0, -5.0]
    assert aligner.is_compatible(narrow_f) is False
    with pytest.raises(ValueError):
        aligner.resample_curve(narrow_f, narrow_v)


def test_train_only_scalers():
    # Synthetic feature data
    X_train = np.array([[10.0, 1.0], [30.0, 3.0], [20.0, 2.0]], dtype=np.float32)
    X_test = np.array([[15.0, 1.5], [40.0, 4.0]], dtype=np.float32)

    # MinMaxScaler
    minmax = MinMaxScaler()
    minmax.fit(X_train)
    X_train_scaled = minmax.transform(X_train)
    assert np.min(X_train_scaled) >= 0.0
    assert np.max(X_train_scaled) <= 1.0

    X_test_scaled = minmax.transform(X_test)
    # Test point 40.0 was larger than train max 30.0 -> must be > 1.0
    assert X_test_scaled[1, 0] > 1.0

    # Serialization
    d = minmax.to_dict()
    restored = MinMaxScaler.from_dict(d)
    assert np.allclose(restored.transform(X_train), X_train_scaled)

    # StandardScaler
    std_scaler = StandardScaler()
    std_scaler.fit(X_train)
    X_std = std_scaler.transform(X_train)
    assert abs(np.mean(X_std)) < 1e-6


def test_feature_extractor_parameters_and_raster():
    rec = make_record("r_feat", "d_feat", "h_feat", family="RECTANGULAR_PATCH")

    # Continuous vector
    vec = FeatureExtractor.extract_continuous_vector(rec)
    assert len(vec) == 10
    assert vec[0] == 32.0  # width
    assert vec[1] == 28.0  # length
    assert vec[4] == 1.6   # height
    assert vec[5] == 4.4   # eps_r

    # 2D Rasterization
    mask = FeatureExtractor.rasterize_patch_2d(rec, grid_size=16)
    assert mask.shape == (16, 16)
    # Center must be conductor
    assert mask[8, 8] == 1.0
    # Outer corners must be dielectric
    assert mask[0, 0] == 0.0


def test_antennanet_adapter():
    adapter = AntennaNetAdapter()

    # Compatible rectangular patch
    rec_rect = make_record("r_an", "d_an", "h_an", family="RECTANGULAR_PATCH")
    is_comp, reason = adapter.is_record_compatible(rec_rect)
    assert is_comp is True
    assert reason == "COMPATIBLE"

    x, y = adapter.prepare_sample(rec_rect)
    assert x.shape == (4,)
    assert y.shape == (101,)

    # Incompatible circular patch -> MUST REJECT
    rec_circ = make_record("r_circ", "d_circ", "h_circ", family="CIRCULAR_PATCH")
    is_comp_c, reason_c = adapter.is_record_compatible(rec_circ)
    assert is_comp_c is False
    assert "strictly supports RECTANGULAR_PATCH" in reason_c

    with pytest.raises(ValueError):
        adapter.prepare_sample(rec_circ)

