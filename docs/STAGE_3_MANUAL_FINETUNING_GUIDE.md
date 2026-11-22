# ANTON — Stage 3 Manual Fine-Tuning Guide

---

### 1. Mandatory Architectural Rule

> [!CAUTION]
> **Zero Automated Retraining**: ANTON does not automatically fine-tune, retrain, or overwrite pretrained checkpoints during backend execution, automated tests, or data imports. Original downloaded weights remain strictly read-only. All model fine-tuning must be executed manually by the computational engineer within dedicated workspace environments.

---

### 2. Fine-Tuning Workspaces Overview

Dedicated, isolated workspaces are provided in [src/anton/ml/workspaces/](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/ml/workspaces/):

| Workspace | Target Model & Architecture | Key Tooling Files |
|---|---|---|
| `antennanet_workspace/` | Deep Forward & Inverse Surrogates (`s11_model.pt`, `best_forward_surrogate.pt`) | [dataset_loader.py](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/ml/workspaces/antennanet_workspace/dataset_loader.py), `finetune_config.yaml`, `load_checkpoint_example.py` |
| `youxch_workspace/` | 22-parameter MLP Multi-Target (`saved-model-5000.h5`) | [dataset_loader.py](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/ml/workspaces/youxch_workspace/dataset_loader.py), `finetune_config.yaml` |
| `jasti_workspace/` | Hybrid Lorentzian Recurrent Neural Network | [dataset_loader.py](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/ml/workspaces/jasti_workspace/dataset_loader.py), `finetune_config.yaml` |

---

### 3. Step-by-Step Manual Fine-Tuning Workflow

#### Step 1: Ingest and Validate Electromagnetic Data
Export authentic simulation sweeps (Touchstone `.s1p` or CSV) from ANSYS HFSS or CST Studio Suite. Ingest and validate via the web UI at `http://localhost:8000/ui/datasets` or via the Python API:
```python
from anton.datasets.importers import DatasetImporter
from anton.datasets.storage import DatasetStorageManager

importer = DatasetImporter()
outputs, meta = importer.import_file("my_hfss_sweep.s1p")
```
Confirm that records achieve `VERIFIED` status in the validation report.

#### Step 2: Load Leakage-Free DataLoaders
Within the target workspace, invoke the provided `dataset_loader.py`:
```python
from anton.ml.workspaces.antennanet_workspace.dataset_loader import load_antennanet_dataloaders

train_loader, val_loader, test_loader, scaler, manifest = load_antennanet_dataloaders(
    batch_size=32,
    train_ratio=0.70,
    val_ratio=0.15,
    test_ratio=0.15,
    random_seed=42,
    only_verified=True,
)
print(f"Leakage check: {manifest['leakage_verification']}")
```

#### Step 3: Load Original Pretrained Weights Safely
Load the original checkpoint with read-only protection:
```python
import torch
from anton.ml.registry import ModelLoader

loader = ModelLoader()
original_ckpt = "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt"

# Create an isolated working copy for fine-tuning
working_path = loader.create_safe_working_copy(original_ckpt, target_dir="models/finetuned/work")
```

#### Step 4: Configure Training Parameters
Adjust `finetune_config.yaml` with research-grade hyperparameters:
- **Optimizer**: AdamW with weight decay $10^{-4}$.
- **Learning Rate**: Reduced learning rate (e.g. $10^{-4}$ to $5\times 10^{-5}$) to prevent catastrophic forgetting.
- **Layer Freezing**: Freeze lower representation layers; fine-tune only the final projection layers.
- **Loss Function**: Weighted Mean Squared Error (MSE) emphasizing the resonant dip ($S_{11} \le -10\,\text{dB}$).

#### Step 5: Execute Training Loop
Run the fine-tuning loop manually in Jupyter or via Python script. Track validation loss to prevent overfitting. Save the fine-tuned weights under a unique identifier:
```python
torch.save(model.state_dict(), "models/finetuned/antennanet_finetuned_v1.pt")
```

#### Step 6: Independent Evaluation on Unseen Test Antennas
Before deploying any fine-tuned model, evaluate its performance on the hold-out test set (`test_loader`):
- Compute overall Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE) on $S_{11,\text{dB}}$.
- Compute Resonant Frequency Error:
  $$\Delta f_{\text{res}} = |f_{\text{res,pred}} - f_{\text{res,true}}|$$
- Compute $-10\,\text{dB}$ Bandwidth Error:
  $$\Delta \text{BW} = |\text{BW}_{\text{pred}} - \text{BW}_{\text{true}}|$$

#### Step 7: Checkpoint Registration Rules
When registering the fine-tuned checkpoint into ANTON's Model Registry:
- Pydantic validator `validate_production_readiness` strictly prevents setting `production_readiness=True` unless full-wave verification is proven with reported metrics on authentic EM data.
- Specify `entity_type: PRETRAINED_MODEL` and document the training dataset provenance and commit hash.
