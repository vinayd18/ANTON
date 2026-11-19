# Antenna-Net Architecture Specification

## Overview
- **Model ID**: `galabavamsi_antennanet`
- **Source Repository**: `https://github.com/Galabavamsi/Antenna-Net`
- **License**: MIT License
- **Framework**: PyTorch (>=1.10.0)
- **Primary Capabilities**: Frequency-dependent $S_{11}$ curve prediction, Resonant frequency ($f_r$) estimation, Bandwidth prediction, Lorentzian PINN forward surrogate.

---

## 1. Network Topologies

### A. Forward Parameter-to-$S_{11}$ MLP (`s11_model.pt`)
- **Input Dimension**: 4 features $[W, L, h, \varepsilon_r]$
- **Hidden Layer 1**: Linear(4, 128) -> BatchNorm1d -> LeakyReLU(negative_slope=0.1) -> Dropout(0.1)
- **Hidden Layer 2**: Linear(128, 256) -> BatchNorm1d -> LeakyReLU(negative_slope=0.1) -> Dropout(0.1)
- **Hidden Layer 3**: Linear(256, 512) -> BatchNorm1d -> LeakyReLU(negative_slope=0.1)
- **Hidden Layer 4**: Linear(512, 256) -> BatchNorm1d -> LeakyReLU(negative_slope=0.1)
- **Output Layer**: Linear(256, 101) -> Linear activation (representing $S_{11}$ in dB across 101 discrete frequency points from 1.0 GHz to 6.0 GHz with $\Delta f = 50\text{ MHz}$)

### B. Lorentzian Physics-Informed Neural Network (`s11_pinn_model.pt`)
- **Physics Inductive Bias**: Models reflection coefficient near resonance as a Lorentzian resonance line-shape:
  $$S_{11}(f) \approx S_{11,0} + \frac{A \cdot (\Gamma/2)^2}{(f - f_r)^2 + (\Gamma/2)^2}$$
- **Input Dimension**: $[W, L, h, \varepsilon_r]$ concatenated with frequency query $f \in [1.0, 6.0]\text{ GHz}$.
- **Loss Function**: Hybrid loss combining MSE with Lorentzian boundary constraint and negative reflection penalty ($S_{11} \le 0\text{ dB}$).

### C. Recurrent Frequency Sweep Surrogate (`hybrid_lorentzian_rnn_best.pth`)
- **Architecture**: Bi-directional LSTM layer (hidden_size=128, num_layers=2) followed by Fully Connected projection.
- **Sequential Input**: Step-wise frequency progression tracking dielectric dispersion.

---

## 2. Transfer Learning & Fine-Tuning Strategy

1. **Feature Extractor Freezing**:
   - Freeze Layers 1 and 2 (`Linear(4, 128)` and `Linear(128, 256)`).
   - Allow Layers 3, 4, and Output head to be fine-tuned on new substrate materials (e.g. Rogers RO4003C, Alumina).
2. **Loss Formulation for Fine-Tuning**:
   $$\mathcal{L} = \alpha \mathcal{L}_{\text{MSE}}(S_{11}^{\text{pred}}, S_{11}^{\text{true}}) + \beta |\Delta f_r| + \gamma \max(0, S_{11}^{\text{pred}} - 0.0)$$
   where $\alpha = 1.0$, $\beta = 0.2$, $\gamma = 10.0$ (penalty for non-physical positive $S_{11}$ in dB).

