# Youxch Patch MLP Architecture Specification

## Overview
- **Model ID**: `youxch_patch_mlp`
- **Source Repository**: `https://github.com/youxch/Inverse-design-of-patch-antennas`
- **License**: MIT License
- **Framework**: TensorFlow / Keras (>=2.4.0)
- **Primary Capabilities**: Frequency-dependent $S_{11}$ curve prediction, Broadside gain ($G$) prediction, Inverse patch geometry synthesis.

---

## 1. Network Topology

### Forward Surrogate MLP (`saved-model-5000.h5`)
- **Input Dimensions**: 6 geometric features $[h, \text{Scale}_X, \text{Scale}_Y, \text{Offset}_y, \text{Scale}_{\text{Slot}}, Uw_3]$
- **Layer 1**: Dense(6, 256) -> BatchNormalization -> ReLU -> Dropout(0.15)
- **Layer 2**: Dense(256, 512) -> BatchNormalization -> ReLU -> Dropout(0.15)
- **Layer 3**: Dense(512, 1024) -> BatchNormalization -> ReLU -> Dropout(0.15)
- **Layer 4**: Dense(1024, 512) -> BatchNormalization -> ReLU
- **Layer 5**: Dense(512, 256) -> BatchNormalization -> ReLU
- **Output Layer**: Dense(256, 102) -> Linear
  - Features 0..100: $S_{11}$ in dB across 101 frequency points from 2.0 GHz to 3.0 GHz ($\Delta f = 10\text{ MHz}$).
  - Feature 101: Broadside realized antenna gain in dBi.

---

## 2. Transfer Learning & Fine-Tuning Strategy

1. **Pretrained Weights**:
   - Checkpoint: `saved-model-5000.h5` (1,558,808 bytes).
   - Trained on 5,000 full-wave ANSYS HFSS simulations of rectangular and slotted patch antennas on FR4.
2. **Fine-Tuning on Custom Substrates**:
   - Freeze the first three dense blocks (`Dense(6, 256)`, `Dense(256, 512)`, `Dense(512, 1024)`).
   - Fine-tune Layers 4, 5, and Output layer on specialized substrate datasets (e.g., Rogers RT/duroid 5880 with $\varepsilon_r=2.2$ or RO4003C with $\varepsilon_r=3.55$).

