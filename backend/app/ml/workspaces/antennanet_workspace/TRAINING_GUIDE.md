# Antenna-Net Manual Fine-Tuning Walkthrough

This guide provides end-to-end instructions for manually fine-tuning the Antenna-Net pretrained model on your own HFSS or measured S-parameter data.

---

## Prerequisites
- Python 3.9+
- `torch >= 1.10.0`
- `numpy`, `scipy`, `matplotlib`
- Verified checkpoint at `src/anton/ml/external/galabavamsi_antennanet/s11_model.pt`

---

## Step 1: Verify Checkpoint Immutability
Before training, verify that the original checkpoint has read-only permissions and that its SHA-256 matches:
```bash
python -c "from anton.ml.registry import ModelLoader; res = ModelLoader.inspect_checkpoint('src/anton/ml/external/galabavamsi_antennanet/s11_model.pt'); print('Is Read-Only:', res.is_read_only); print('SHA256:', res.sha256_hash)"
```

---

## Step 2: Prepare Training Data
Follow `DATASET_PREPARATION.md` to format your simulation results into a CSV or NumPy file with normalized features $[W, L, h, \varepsilon_r]$ and target $S_{11}(f)$ curves.

---

## Step 3: Run Fine-Tuning Script
Execute your fine-tuning script. Note that fine-tuning writes new model checkpoints to `workspaces/antennanet_workspace/checkpoints/` and **never** overwrites `external/galabavamsi_antennanet/`.

```python
# Sample fine-tuning loop skeleton
optimizer = torch.optim.AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=0.0005, weight_decay=1e-4)
criterion = torch.nn.MSELoss()

for epoch in range(num_epochs):
    model.train()
    for batch_x, batch_y in train_loader:
        optimizer.zero_grad()
        pred = model(batch_x)
        loss = criterion(pred, batch_y)
        loss.backward()
        optimizer.step()
```

---

## Step 4: Evaluate with `evaluation_template.ipynb`
Open `evaluation_template.ipynb` in your Jupyter environment and run the cells to calculate MAE, RMSE, resonance frequency deviation ($|\Delta f_r|$), and bandwidth error against your validation dataset.
