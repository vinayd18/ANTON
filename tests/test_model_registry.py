# -*- coding: utf-8 -*-
"""Comprehensive automated test suite for ANTON Stage 3.0 Model Registry Subsystem."""

import json
import os
import stat
from pathlib import Path
import numpy as np
import pytest

from anton.ml.registry import (
    AntennaBenchmarkEvaluator,
    BenchmarkEvaluationReport,
    CheckpointInfo,
    CheckpointInspectionResult,
    CheckpointLoadVerification,
    CompatibilityStatus,
    DatasetMetadata,
    EvaluationSlice,
    EvaluationStatus,
    FineTuningReadiness,
    FrequencyRange,
    HardwareRequirements,
    InferenceVerification,
    InputSpecification,
    IntegrationStatus,
    LicenseAssessmentResult,
    ModelCategory,
    ModelCompatibilityEvaluator,
    ModelEntityType,
    ModelLicensingAuditor,
    ModelLoader,
    ModelMetadata,
    ModelRegistry,
    OutputSpecification,
    TargetCapability,
)


class TestModelMetadataValidation:
    """Tests Pydantic validation, types, and constraints for ModelMetadata."""

    def test_valid_model_metadata_creation(self):
        m = ModelMetadata(
            model_id="test_patch_model",
            model_name="Test Antenna Model",
            repository_url="https://github.com/example/test-patch",
            architecture="ResNet-18",
            framework="PyTorch",
            model_category=ModelCategory.CATEGORY_B,
            target_capabilities=[TargetCapability.S11_PREDICTION, TargetCapability.RESONANT_FREQUENCY_PREDICTION],
            supported_geometries=["rectangular_patch"],
            supported_materials=["FR4_epoxy"],
        )
        assert m.model_id == "test_patch_model"
        assert len(m.target_capabilities) == 2
        assert m.supported_geometries == ["rectangular_patch"]
        assert m.compatibility_status == CompatibilityStatus.INSUFFICIENT_INFORMATION

    def test_empty_model_id_raises_value_error(self):
        with pytest.raises(ValueError):
            ModelMetadata(
                model_id="   ",
                model_name="Invalid Model",
                repository_url="https://github.com/example/invalid",
                architecture="MLP",
                framework="TensorFlow",
            )

    def test_serialization_to_registry_dict(self):
        m = ModelMetadata(
            model_id="serialize_test",
            model_name="Serialize Test",
            repository_url="https://github.com/example/test",
            architecture="CNN",
            framework="PyTorch",
        )
        data = m.to_registry_dict()
        assert isinstance(data, dict)
        assert data["model_id"] == "serialize_test"


class TestModelRegistryCatalogAndFiltering:
    """Tests catalog building, registration, and query filters."""

    @pytest.fixture
    def registry(self):
        return ModelRegistry.build_default_catalog()

    def test_default_catalog_count(self, registry):
        # Must contain all 10 surveyed candidates
        assert registry.count() == 10

    def test_filter_by_category(self, registry):
        cat_a = registry.filter_by_category(ModelCategory.CATEGORY_A)
        cat_b = registry.filter_by_category(ModelCategory.CATEGORY_B)
        cat_c = registry.filter_by_category(ModelCategory.CATEGORY_C)

        assert len(cat_a) == 2
        assert set(m.model_id for m in cat_a) == {"galabavamsi_antennanet", "youxch_patch_mlp"}
        assert len(cat_b) == 7
        assert len(cat_c) == 1
        assert cat_c[0].model_id == "metu_simpl_microstrip"

    def test_filter_by_capability(self, registry):
        s11_models = registry.filter_by_capability(TargetCapability.S11_PREDICTION)
        assert len(s11_models) >= 4
        fr_models = registry.filter_by_capability(TargetCapability.RESONANT_FREQUENCY_PREDICTION)
        assert len(fr_models) >= 5

    def test_filter_by_geometry(self, registry):
        rect_models = registry.filter_by_geometry("rectangular_patch")
        assert len(rect_models) >= 6

        # Geometry gaps: triangular, hexagonal, annular patches should have zero out-of-the-box pretrained models
        tri_models = registry.filter_by_geometry("triangular_patch")
        assert len(tri_models) == 0
        hex_models = registry.filter_by_geometry("hexagonal_patch")
        assert len(hex_models) == 0
        annular_models = registry.filter_by_geometry("annular_patch")
        assert len(annular_models) == 0

    def test_free_text_search(self, registry):
        results = registry.search("PINN")
        assert len(results) >= 1
        assert any("antennanet" in m.model_id for m in results)

        results_rf = registry.search("Random Forest")
        assert len(results_rf) >= 1
        assert any("jasti" in m.model_id for m in results_rf)


class TestModelLicensingAndPatents:
    """Tests open-source compliance and patent detection."""

    def test_detect_indian_patent_572928_on_pixelant(self):
        m = ModelMetadata(
            model_id="udaykdk_pixelant",
            model_name="PixelAnt",
            repository_url="https://github.com/udaykdk/pixelant",
            architecture="Tandem NN",
            framework="PyTorch",
            license="MIT (No Patent Grant)",
        )
        audit = ModelLicensingAuditor.audit(m)
        assert audit.risk_level == "CRITICAL"
        assert audit.patent_grant_included is False
        assert any("572928" in w for w in audit.patent_warnings)
        assert any("IIT Madras" in w for w in audit.patent_warnings)

    def test_clean_mit_license(self):
        m = ModelMetadata(
            model_id="clean_model",
            model_name="Clean Model",
            repository_url="https://github.com/clean/clean-model",
            architecture="MLP",
            framework="PyTorch",
            license="MIT License",
        )
        audit = ModelLicensingAuditor.audit(m)
        assert audit.commercial_allowed is True
        assert audit.patent_grant_included is True
        assert audit.risk_level == "LOW"
        assert len(audit.patent_warnings) == 0


class TestModelCompatibilityEvaluator:
    """Tests 10-dimension compatibility evaluation."""

    def test_adaptable_with_preprocessing_antennanet(self):
        reg = ModelRegistry.build_default_catalog()
        model = reg.get_model("galabavamsi_antennanet")
        evaluator = ModelCompatibilityEvaluator()
        res = evaluator.evaluate(model)
        assert res.overall_score >= 60.0
        assert res.status in [CompatibilityStatus.DIRECTLY_COMPATIBLE, CompatibilityStatus.ADAPTABLE_WITH_PREPROCESSING]
        assert len(res.supported_anton_geometries) >= 1
        assert len(res.required_preprocessing) > 0

    def test_dataset_classification(self):
        reg = ModelRegistry.build_default_catalog()
        model = reg.get_model("metu_simpl_microstrip")
        evaluator = ModelCompatibilityEvaluator()
        res = evaluator.evaluate(model)
        assert res.status == CompatibilityStatus.NOT_COMPATIBLE  # Category C dataset without weights


class TestModelLoaderSecurityAndImmutability:
    """Tests checksum verification, safe headers, and read-only protections."""

    def test_compute_sha256(self, tmp_path):
        test_file = tmp_path / "test_weight.bin"
        test_file.write_bytes(b"ANTON_ELECTROMAGNETIC_TENSOR_WEIGHTS_TEST")
        sha = ModelLoader.compute_sha256(test_file)
        assert len(sha) == 64
        import hashlib
        expected = hashlib.sha256(b"ANTON_ELECTROMAGNETIC_TENSOR_WEIGHTS_TEST").hexdigest().lower()
        assert sha == expected

    def test_immutability_enforcement(self, tmp_path):
        f = tmp_path / "immutable.bin"
        f.write_bytes(b"PRETRAINED_WEIGHTS")
        ModelLoader.set_immutable(f)

        # Verify write permission is removed
        mode = f.stat().st_mode
        assert not (mode & stat.S_IWUSR)

        # Restore permissions for cleanup
        os.chmod(f, mode | stat.S_IWUSR)

    def test_create_safe_working_copy(self, tmp_path):
        src_file = tmp_path / "original_ckpt.bin"
        src_file.write_bytes(b"ORIGINAL_VERIFIED_CHECKPOINT")
        ModelLoader.set_immutable(src_file)

        dst_dir = tmp_path / "work_env"
        copied = ModelLoader.create_safe_working_copy(src_file, dst_dir)
        assert copied.is_file()
        assert copied.read_bytes() == b"ORIGINAL_VERIFIED_CHECKPOINT"

        # Copied file must be writable for manual fine-tuning
        assert bool(copied.stat().st_mode & stat.S_IWUSR)
        # Original file must remain read-only
        assert not bool(src_file.stat().st_mode & stat.S_IWUSR)

        # Cleanup
        os.chmod(src_file, stat.S_IWRITE)
        os.chmod(copied, stat.S_IWRITE)


class TestAntennaBenchmarkEvaluatorMetrics:
    """Tests standard error metrics for electromagnetic simulation."""

    def test_mae_rmse_r2(self):
        y_true = np.array([-12.5, -15.0, -22.0, -18.0, -8.0])
        y_pred = np.array([-12.0, -14.5, -20.0, -17.5, -8.5])

        mae = AntennaBenchmarkEvaluator.calculate_mae(y_true, y_pred)
        rmse = AntennaBenchmarkEvaluator.calculate_rmse(y_true, y_pred)
        r2 = AntennaBenchmarkEvaluator.calculate_r2(y_true, y_pred)

        assert pytest.approx(mae, 0.01) == 0.8
        assert pytest.approx(rmse, 0.01) == 1.0
        assert r2 > 0.95

    def test_resonant_frequency_metrics(self):
        freqs = np.linspace(2.0, 3.0, 101)  # 2.0 to 3.0 GHz, step 10 MHz
        # Create a dip at 2.45 GHz
        s11_true = -5.0 * np.ones(101)
        s11_true[45] = -25.0  # index 45 -> 2.45 GHz

        # Predicted dip at 2.46 GHz
        s11_pred = -5.0 * np.ones(101)
        s11_pred[46] = -22.0  # index 46 -> 2.46 GHz

        delta_fr_mhz, pct_err = AntennaBenchmarkEvaluator.calculate_resonant_frequency_error(freqs, s11_true, s11_pred)
        assert pytest.approx(delta_fr_mhz, 0.5) == 10.0  # 10 MHz error
        assert pct_err < 1.0


class TestFineTuningWorkspacesCompleteness:
    """Verifies that all 3 fine-tuning workspaces contain all required files."""

    WORKSPACES = [
        "src/anton/ml/workspaces/antennanet_workspace",
        "src/anton/ml/workspaces/youxch_workspace",
        "src/anton/ml/workspaces/jasti_workspace",
    ]

    REQUIRED_FILES = [
        "ARCHITECTURE.md",
        "TENSOR_SPEC.md",
        "DATASET_PREPARATION.md",
        "finetune_config.yaml",
        "load_checkpoint_example.py",
        "evaluation_template.ipynb",
        "TRAINING_GUIDE.md",
    ]

    def test_workspace_files_exist(self):
        for ws in self.WORKSPACES:
            ws_path = Path(ws)
            assert ws_path.is_dir(), f"Workspace directory missing: {ws}"
            for req in self.REQUIRED_FILES:
                f_path = ws_path / req
                assert f_path.is_file(), f"Missing required file '{req}' in {ws}"
                assert f_path.stat().st_size > 0, f"File '{req}' is empty in {ws}"


class TestStage3RealInferenceAndIntegrity:
    """Verifies authentic model weights, isolated inference execution, and registry integrity."""

    def test_real_checkpoint_loading_torch(self):
        import torch
        ckpt_path = Path("src/anton/ml/external/galabavamsi_antennanet/s11_model.pt")
        assert ckpt_path.is_file()
        sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        assert isinstance(sd, dict)
        assert "net.0.weight" in sd
        assert tuple(sd["net.0.weight"].shape) == (128, 4)
        assert tuple(sd["net.6.weight"].shape) == (1, 64)

    def test_real_checkpoint_loading_h5(self):
        import h5py
        h5_path = Path("src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5")
        assert h5_path.is_file()
        with h5py.File(h5_path, "r") as f:
            assert "dense" in f
            assert "dense_7" in f
            w0 = f["dense"]["dense/kernel:0"][:]
            assert w0.shape == (6, 8)
            w7 = f["dense_7"]["dense_7/kernel:0"][:]
            assert w7.shape == (512, 402)

    def test_real_model_inference_finiteness(self):
        import torch
        import torch.nn as nn

        class S11Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(4, 128),
                    nn.ReLU(),
                    nn.Linear(128, 128),
                    nn.ReLU(),
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Linear(64, 1),
                )
            def forward(self, x):
                return self.net(x)

        ckpt_path = Path("src/anton/ml/external/galabavamsi_antennanet/s11_model.pt")
        model = S11Model()
        sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        model.load_state_dict(sd, strict=True)
        model.eval()

        inp = torch.tensor([[0.5, 0.4, 0.3, 0.2]], dtype=torch.float32)
        with torch.no_grad():
            out = model(inp)

        assert out.shape == (1, 1)
        assert torch.isfinite(out).all().item() is True

    def test_input_dimension_mismatch_rejection(self):
        import torch
        import torch.nn as nn

        class S11Model(nn.Module):
            def __init__(self):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(4, 128),
                    nn.ReLU(),
                    nn.Linear(128, 128),
                    nn.ReLU(),
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Linear(64, 1),
                )
            def forward(self, x):
                return self.net(x)

        ckpt_path = Path("src/anton/ml/external/galabavamsi_antennanet/s11_model.pt")
        model = S11Model()
        sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
        model.load_state_dict(sd, strict=True)
        model.eval()

        # Input with 5 features instead of 4 must raise RuntimeError
        bad_inp = torch.tensor([[0.5, 0.4, 0.3, 0.2, 0.1]], dtype=torch.float32)
        with pytest.raises(RuntimeError):
            with torch.no_grad():
                _ = model(bad_inp)

    def test_checkpoint_corruption_detection(self, tmp_path):
        import torch
        corrupt_file = tmp_path / "corrupted_model.pt"
        # Write corrupted header / invalid bytes
        corrupt_file.write_bytes(b"CORRUPTED_PK_HEADER_NOT_A_VALID_TORCH_FILE")
        with pytest.raises(Exception):
            torch.load(corrupt_file, map_location="cpu", weights_only=True)

    def test_unsupported_geometries_returns_empty(self):
        reg = ModelRegistry.build_default_catalog()
        assert len(reg.filter_by_geometry("triangular_patch")) == 0
        assert len(reg.filter_by_geometry("hexagonal_patch")) == 0
        assert len(reg.filter_by_geometry("annular_patch")) == 0

    def test_duplicate_registry_entry_rejection(self):
        reg = ModelRegistry.build_default_catalog()
        dup = reg.get_model("galabavamsi_antennanet")
        assert dup is not None
        with pytest.raises(ValueError, match="already registered"):
            reg.register(dup, overwrite=False)

    def test_strict_production_readiness_enforcement(self):
        with pytest.raises(ValueError, match="production_readiness cannot be set to True"):
            ModelMetadata(
                model_id="premature_prod_model",
                model_name="Premature Model",
                repository_url="https://github.com/example/prod",
                architecture="MLP",
                framework="PyTorch",
                production_readiness=True,
            )

    def test_registry_entity_separation(self):
        reg = ModelRegistry.build_default_catalog()
        metu = reg.get_model("metu_simpl_microstrip")
        assert metu is not None
        assert metu.entity_type == ModelEntityType.DATASET
        assert metu.checkpoint_availability is False
        assert metu.checkpoint_load_verification == CheckpointLoadVerification.NOT_APPLICABLE
        assert metu.inference_verification == InferenceVerification.NOT_APPLICABLE

        antennanet = reg.get_model("galabavamsi_antennanet")
        assert antennanet is not None
        assert antennanet.entity_type == ModelEntityType.PRETRAINED_MODEL
        assert antennanet.checkpoint_availability is True
        assert antennanet.checkpoint_load_verification == CheckpointLoadVerification.VERIFIED
        assert antennanet.inference_verification == InferenceVerification.VERIFIED
        assert antennanet.fine_tuning_readiness == FineTuningReadiness.WORKSPACE_PREPARED
        assert antennanet.production_readiness is False

        training_impls = reg.filter_by_entity_type(ModelEntityType.TRAINING_IMPLEMENTATION)
        assert len(training_impls) == 7
        assert all(m.production_readiness is False for m in training_impls)
        assert all(m.checkpoint_availability is False for m in training_impls)

