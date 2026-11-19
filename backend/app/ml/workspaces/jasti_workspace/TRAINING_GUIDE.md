# Jasti RF Surrogate Training & Optimization Guide

Step-by-step instructions for training the Random Forest surrogate and running Genetic Algorithm optimization for 2.45 GHz patch antennas.

---

## Prerequisites
- Python 3.8+
- `scikit-learn >= 1.0.0`
- `deap`, `numpy`, `pandas`

---

## Step 1: Prepare Training Data
Collect authentic simulation or transmission-line analytical samples as described in `DATASET_PREPARATION.md`.

---

## Step 2: Fit Random Forest
Run `load_checkpoint_example.py` or execute the training pipeline in `finetune_config.yaml`.
Save the fitted estimator to `workspaces/jasti_workspace/rf_model.joblib`.

---

## Step 3: Run Genetic Algorithm Synthesis
Use the DEAP genetic algorithm to optimize patch width $W$ and length $L$ for a desired target frequency (e.g. 2.45 GHz) on a selected substrate.
Export the synthesized geometry directly to ANTON's canonical `rectangular_patch` schema.
