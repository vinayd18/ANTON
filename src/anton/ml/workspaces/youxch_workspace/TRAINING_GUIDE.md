# Youxch Patch MLP Manual Fine-Tuning Walkthrough

Step-by-step instructions for fine-tuning the Keras MLP model on target frequency sweeps or new patch variants.

---

## Prerequisites
- Python 3.8+
- `tensorflow >= 2.4.0`
- `h5py`, `numpy`, `matplotlib`
- Verified checkpoint at `src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5`

---

## Step 1: Verify Checkpoint Immutability
Check that the original `.h5` file is read-only:
```bash
python -c "from anton.ml.registry import ModelLoader; res = ModelLoader.inspect_checkpoint('src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5'); print('Format:', res.format); print('Read-Only:', res.is_read_only)"
```

---

## Step 2: Load Model in Working Directory
Use `ModelLoader.create_safe_working_copy()` to copy the checkpoint to `workspaces/youxch_workspace/work/` so original weights cannot be modified.

---

## Step 3: Train and Evaluate
Execute fine-tuning on your training dataset using the hyperparameters defined in `finetune_config.yaml`.
Evaluate the final model against test simulation data using `evaluation_template.ipynb`.

