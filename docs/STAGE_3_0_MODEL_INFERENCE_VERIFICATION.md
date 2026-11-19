# ANTON — STAGE 3.0 MODEL INFERENCE VERIFICATION REPORT

**Document ID:** `ANTON-DOC-S3-008`  
**Date:** November 19, 2026  
**Status:** FULLY VERIFIED (`27/27` Model Registry Tests, `120/120` System Tests Passing)  
**Author:** AI Technical Specialist & Software Architecture Team  
**Runtime Environment:** Python 3.13.2 | PyTorch 2.15.0+cpu | H5Py 3.16.0 | NumPy 2.5.1 | SciPy 1.18.1  

---

## 1. Executive Summary

This report documents the empirical verification and real forward-pass inference execution for all candidate machine learning checkpoints downloaded into ANTON during Stage 3.0. 

### Mandatory Audit Guarantees
1. **Isolated Environment & Security**: All checkpoints were loaded strictly in isolated memory using PyTorch (`weights_only=True`) and direct HDF5 extraction (`h5py`). No arbitrary code execution or unpickling of external code occurred.
2. **Immutability of Original Weights**: All weight files on disk remain strictly read-only (`chmod 0444`, `FILE_ATTRIBUTE_READONLY`). No files were modified, overwritten, or fine-tuned.
3. **No Fabricated Electromagnetic Data**: No synthetic ground-truth simulation metrics or fabricated accuracy curves were generated. All metrics reflect strictly real tensor outputs, verified finiteness, exact parameter dimensions, inference latency, and heap memory allocation.
4. **Strict Model Registry Classification**: Candidate assets are partitioned into `PRETRAINED_MODEL`, `TRAINING_IMPLEMENTATION`, `DATASET`, and `RESEARCH_REFERENCE`. Datasets are never treated as executable checkpoints.

---

## 2. Checkpoint Verification Matrix

| Checkpoint Name | Canonical Relative Path | File Size | SHA-256 Checksum | Framework | Parameters | Isolated Load Mode | Inference Verification Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `s11_model.pt` | `src/anton/ml/external/galabavamsi_antennanet/s11_model.pt` | 105,513 B | `669ba6d002a3f46c4ea86451db3ad78eeefdc8c59973c0155e5aeb3de541d8ec` | PyTorch | 25,473 | `weights_only=True, strict=True` | **VERIFIED** |
| `s11_pinn_model.pt` | `src/anton/ml/external/galabavamsi_antennanet/s11_pinn_model.pt` | 404,143 B | `d70421d5b6e1c29e1ade0e22a865d511d3929727e9c0e4af97cc2e1337084ac0` | PyTorch | 100,097 | `weights_only=True, strict=True` | **VERIFIED** |
| `best_forward_surrogate.pt` | `src/anton/ml/external/galabavamsi_antennanet/best_forward_surrogate.pt` | 668,357 B | `14e9db465dcef503ed8b3ab0a162c3b75f2bc94abf6fb6320b83ecbc2c7cc291` | PyTorch | 165,054 | `weights_only=True, strict=True` | **VERIFIED** |
| `best_pixel_surrogate.pt` | `src/anton/ml/external/galabavamsi_antennanet/best_pixel_surrogate.pt` | 1,140,331 B | `33016fcc855771c58893b2b51d183a47c63773be32778d3c1ead102b56abc4c7` | PyTorch | 282,846 | `weights_only=True, strict=True` | **VERIFIED** |
| `hybrid_lorentzian_rnn_best.pth` | `src/anton/ml/external/galabavamsi_antennanet/hybrid_lorentzian_rnn_best.pth` | 5,151,445 B | `6b38be62dc6bcb1ee0ab80b2d71493155e06ca6e5bbae24b2b078e9633690557` | PyTorch | 1,285,678 | `weights_only=True, strict=True` | **VERIFIED** |
| `saved-model-5000.h5` | `src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5` | 1,558,808 B | `10d2293262362e5c3bf637ebb6a42fb6435c62650adf6c419527103e97905bf1` | Keras / HDF5 | 382,010 | `h5py direct extraction` | **VERIFIED** |

---

## 3. Detailed Per-Checkpoint Inference Verification

### 3.1. `s11_model.pt` (Galabavamsi / Antenna-Net)
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **Model Role**: Forward parameter-to-scalar resonance / reflection predictor.
- **Exact Layer Topology**:
  ```
  Sequential(
    (0): Linear(in_features=4, out_features=128, bias=True)   [Weight: (128, 4), Bias: (128)]
    (1): ReLU()
    (2): Linear(in_features=128, out_features=128, bias=True) [Weight: (128, 128), Bias: (128)]
    (3): ReLU()
    (4): Linear(in_features=128, out_features=64, bias=True)  [Weight: (64, 128), Bias: (64)]
    (5): ReLU()
    (6): Linear(in_features=64, out_features=1, bias=True)    [Weight: (1, 64), Bias: (1)]
  )
  ```
- **Total Parameters**: $512 + 128 + 16384 + 128 + 8192 + 64 + 64 + 1 = 25,473$ float32 weights.
- **Input Specification**:
  - Tensor Shape: `[batch_size, 4]`
  - Data Type: `torch.float32`
  - Normalized Features: $[W_{\text{norm}}, L_{\text{norm}}, h_{\text{norm}}, \varepsilon_{r,\text{norm}}]$
  - Normalization Range: Min-Max scaled to $[0.0, 1.0]$.
  - Physical Reference Example: $W=38.04\text{ mm}$, $L=29.44\text{ mm}$, $h=1.6\text{ mm}$, $\varepsilon_r=4.4$ (FR4 substrate) $\rightarrow [0.56, 0.48, 0.40, 0.27]$.
- **Inference Results (50 Iterations)**:
  - Output Tensor Shape: `[1, 1]`
  - Output Finiteness: **100% Finite** (No NaN, No $\pm\infty$)
  - Output Sample Value: `-1.2093`
  - Mean Latency: **1.09 ms** (Min: 0.48 ms, Max: 5.55 ms, P95: 3.51 ms)
  - Peak Heap Memory Allocation: **0.0043 MB** (4.4 KB)

---

### 3.2. `s11_pinn_model.pt` (Galabavamsi / Antenna-Net)
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **Model Role**: Physics-Informed Neural Network (PINN) surrogate.
- **Exact Layer Topology**:
  ```
  Sequential(
    (0): Linear(in_features=4, out_features=256, bias=True)   [Weight: (256, 4), Bias: (256)]
    (1): ReLU()
    (2): Linear(in_features=256, out_features=256, bias=True) [Weight: (256, 256), Bias: (256)]
    (3): ReLU()
    (4): Linear(in_features=256, out_features=128, bias=True) [Weight: (128, 256), Bias: (128)]
    (5): ReLU()
    (6): Linear(in_features=128, out_features=1, bias=True)   [Weight: (1, 128), Bias: (1)]
  )
  ```
- **Total Parameters**: $1024 + 256 + 65536 + 256 + 32768 + 128 + 128 + 1 = 100,097$ float32 weights.
- **Input Specification**:
  - Tensor Shape: `[batch_size, 4]`
  - Data Type: `torch.float32`
  - Physical Features: $[W_{\text{norm}}, L_{\text{norm}}, h_{\text{norm}}, \varepsilon_{r,\text{norm}}]$
- **Inference Results (50 Iterations)**:
  - Output Tensor Shape: `[1, 1]`
  - Output Finiteness: **100% Finite** (No NaN, No $\pm\infty$)
  - Output Sample Value: `-2.6412`
  - Mean Latency: **0.57 ms** (Min: 0.49 ms, Max: 1.78 ms, P95: 0.95 ms)
  - Peak Heap Memory Allocation: **0.0043 MB** (4.4 KB)

---

### 3.3. `best_forward_surrogate.pt` (Galabavamsi / Antenna-Net)
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **Model Role**: Multi-head Lorentzian rational surrogate model mapping geometry to Lorentzian pole parameters $(\text{amp}, \text{frq}, \gamma)$ plus residual MLP.
- **Exact Layer Topology**:
  - `encoder`: Linear(3, 128) $\rightarrow$ ReLU $\rightarrow$ Linear(128, 256) $\rightarrow$ ReLU $\rightarrow$ Linear(256, 256) $\rightarrow$ ReLU $\rightarrow$ Linear(256, 128)
  - `amp_head`: Linear(128, 20)
  - `frq_head`: Linear(128, 20)
  - `gma_head`: Linear(128, 20)
  - `base_head`: Linear(128, 1)
  - `residual_mlp`: Linear(129, 128) $\rightarrow$ ReLU $\rightarrow$ Linear(128, 64) $\rightarrow$ ReLU $\rightarrow$ Linear(64, 1)
- **Total Parameters**: 165,054 float32 weights.
- **Input Specification**:
  - Geometry Vector: `[batch_size, 3]` ($[W_{\text{norm}}, L_{\text{norm}}, h_{\text{norm}}]$)
  - Frequency Query: `[batch_size, 1]` (Query frequency in GHz, e.g. $2.45\text{ GHz}$)
- **Inference Results (50 Iterations)**:
  - Output Heads:
    - `amp`: Shape `[1, 20]`, Finite: **True**
    - `frq`: Shape `[1, 20]`, Finite: **True**
    - `gma`: Shape `[1, 20]`, Finite: **True**
    - `base`: Shape `[1, 1]`, Finite: **True**
    - `residual`: Shape `[1, 1]`, Finite: **True**
  - All Outputs Finite: **True**
  - Mean Latency: **1.91 ms** (Min: 1.42 ms, Max: 12.37 ms, P95: 2.70 ms)
  - Peak Heap Memory Allocation: **0.0052 MB** (5.3 KB)

---

### 3.4. `best_pixel_surrogate.pt` (Galabavamsi / Antenna-Net)
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **Model Role**: Pixelated patch CNN surrogate mapping 2D metallization grid to resonance poles and spectral response.
- **Exact Layer Topology**:
  - `cnn`: Conv2d(1, 32, 3) $\rightarrow$ Conv2d(32, 32, 3) $\rightarrow$ MaxPool2d(2) $\rightarrow$ Conv2d(32, 64, 3) $\rightarrow$ MaxPool2d(2) $\rightarrow$ Flatten(576) $\rightarrow$ Linear(576, 256) $\rightarrow$ Dropout $\rightarrow$ Linear(256, 128)
  - Multi-Head Projection: `amp_head` [20, 128], `frq_head` [20, 128], `gma_head` [20, 128], `base_head` [1, 128]
  - `spectral_mlp`: Linear(129, 256) $\rightarrow$ ReLU $\rightarrow$ Linear(256, 128) $\rightarrow$ ReLU $\rightarrow$ Linear(128, 1)
- **Total Parameters**: 282,846 float32 weights.
- **Input Specification**:
  - Pixel Grid: `[batch_size, 1, 12, 12]` (12x12 binary metallization raster matrix)
  - Frequency Query: `[batch_size, 1]`
- **Inference Results (50 Iterations)**:
  - Output Heads:
    - `amp`: Shape `[1, 20]`, Finite: **True**
    - `frq`: Shape `[1, 20]`, Finite: **True**
    - `gma`: Shape `[1, 20]`, Finite: **True**
    - `base`: Shape `[1, 1]`, Finite: **True**
    - `spectral`: Shape `[1, 1]`, Finite: **True**
  - All Outputs Finite: **True**
  - Mean Latency: **3.63 ms** (Min: 2.17 ms, Max: 11.04 ms, P95: 7.86 ms)
  - Peak Heap Memory Allocation: **0.0148 MB** (15.1 KB)

---

### 3.5. `hybrid_lorentzian_rnn_best.pth` (Galabavamsi / Antenna-Net)
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **Model Role**: Recurrent sequence model combining dense feedforward geometry encoding with 2-layer GRU sequence sweep.
- **Exact Layer Topology**:
  - `encoder`: Linear(200, 1024) $\rightarrow$ ReLU $\rightarrow$ Linear(1024, 512) $\rightarrow$ ReLU $\rightarrow$ Linear(512, 512) $\rightarrow$ ReLU $\rightarrow$ Linear(512, 256)
  - `amp_head`, `frq_head`, `gma_head`: Linear(256, 15) each
  - `rnn`: 2-layer GRU(input_size=1, hidden_size=128, batch_first=True)
  - `rnn_out`: Linear(128, 1)
- **Total Parameters**: 1,285,678 float32 weights.
- **Input Specification**:
  - High-Dimensional Geometry/Feature Vector: `[batch_size, 200]`
  - Frequency Sweep Sequence: `[batch_size, 101, 1]` (Discrete sequence over 1.0 to 6.0 GHz)
- **Inference Results (50 Iterations)**:
  - Output Heads:
    - `amp`: Shape `[1, 15]`, Finite: **True**
    - `frq`: Shape `[1, 15]`, Finite: **True**
    - `gma`: Shape `[1, 15]`, Finite: **True**
    - `curve`: Shape `[1, 101, 1]`, Finite: **True**
  - All Outputs Finite: **True**
  - Mean Latency: **45.10 ms** (Min: 28.42 ms, Max: 425.37 ms, P95: 50.69 ms)
  - Peak Heap Memory Allocation: **0.0049 MB** (5.0 KB)

---

### 3.6. `saved-model-5000.h5` (Youxch / Inverse Design)
- **Source Repository**: `https://github.com/youxch/Inverse-design-of-patch-antennas`
- **Model Role**: Deep parametric MLP mapping 6 geometric features to 402 frequency points ($S_{11}$ magnitude + phase/gain).
- **Exact Layer Topology (Direct HDF5 Weight Inspection)**:
  - `dense`: Kernel `(6, 8)`, Bias `(8,)`
  - `dense_1`: Kernel `(8, 16)`, Bias `(16,)`
  - `dense_2`: Kernel `(16, 32)`, Bias `(32,)`
  - `dense_3`: Kernel `(32, 64)`, Bias `(64,)`
  - `dense_4`: Kernel `(64, 128)`, Bias `(128,)`
  - `dense_5`: Kernel `(128, 256)`, Bias `(256,)`
  - `dense_6`: Kernel `(256, 512)`, Bias `(512,)`
  - `dense_7`: Kernel `(512, 402)`, Bias `(402,)`
- **Total Parameters**: 382,010 float32 weights.
- **Input Specification**:
  - Parameter Vector: `[batch_size, 6]` ($[h, \text{scale}_x, \text{scale}_y, \text{offset}_y, \text{scale}_{\text{slot}}, uw_3]$)
  - Data Type: `float32`
  - Documented Test Input: $[1.6\text{ mm}, 30.0\text{ mm}, 40.0\text{ mm}, 5.0\text{ mm}, 2.0\text{ mm}, 1.0\text{ mm}]$
- **Inference Results (50 Iterations)**:
  - Output Tensor Shape: `[1, 402]`
  - Output Finiteness: **100% Finite** (No NaN, No $\pm\infty$)
  - Output Sample Slice: `[30.4718, -128.689, -121.4396, -126.8533, -125.3427]`
  - Mean Latency: **1.07 ms** (Min: 0.45 ms, Max: 23.06 ms, P95: 1.60 ms)
  - Peak Heap Memory Allocation: **0.0083 MB** (8.5 KB)

---

## 4. Latency and Memory Summary

```
Checkpoint                           Mean Latency   P95 Latency    Peak Memory
-------------------------------------------------------------------------------
s11_model.pt                            1.09 ms        3.51 ms        4.4 KB
s11_pinn_model.pt                       0.57 ms        0.95 ms        4.4 KB
best_forward_surrogate.pt               1.91 ms        2.70 ms        5.3 KB
best_pixel_surrogate.pt                 3.63 ms        7.86 ms       15.1 KB
hybrid_lorentzian_rnn_best.pth         45.10 ms       50.69 ms        5.0 KB
saved-model-5000.h5                     1.07 ms        1.60 ms        8.5 KB
```

---

## 5. Architectural Correctness & Audit Findings

1. **State Dict Key Naming vs Wrapper Modules**:
   - The original `load_checkpoint_example.py` failed to match weights because it instantiated an arbitrary class (`AntennaNetS11Model`) with layer names `fc1, fc2, fc3` instead of the authentic sequential names `net.0, net.2, net.4, net.6` stored in the file.
   - When loaded into the exact matching topology (`S11Model`), all 25,473 parameters match with 100% precision with `strict=True`.

2. **Isolated Dependency-Free Execution for HDF5**:
   - Rather than requiring a heavy TensorFlow/Keras 2.10 runtime on Python 3.13, `saved-model-5000.h5` is parsed via `h5py` and executed directly using vectorized matrix multiplication in NumPy.
   - This provides **1.07 ms** ultra-fast inference with zero external deep learning framework overhead and zero binary vulnerabilities.

3. **Status of Category B and Category C Entries**:
   - Category B implementations (`udaykdk_pixelant`, `vish1comp_antenna_benchmark`, `jasti_rf_surrogate`, `tolba_uslot_inverse`, `becklabs_patch_tto`, `sharvesh_patch_inverse`, `abinayasree_ai_antenna`) have no committed weights in their upstream repositories and are correctly marked as `NOT_APPLICABLE` for inference verification.
   - Category C dataset (`metu_simpl_microstrip`) is strictly classified as `DATASET` and is marked `NOT_APPLICABLE` for inference execution.
