# Youxch Patch MLP Tensor & Normalization Specification

## 1. Input Tensor Specification

| Tensor Index | Parameter Name | Physical Description | Unit | Min Value | Max Value |
|---|---|---|---|---|---|
| `x[:, 0]` | `substrate_height` | Substrate dielectric thickness ($h$) | mm | 0.8 | 3.2 |
| `x[:, 1]` | `scale_x` | Patch X-dimension scaling relative to reference width | unitless | 0.7 | 1.4 |
| `x[:, 2]` | `scale_y` | Patch Y-dimension scaling relative to reference length | unitless | 0.7 | 1.4 |
| `x[:, 3]` | `offset_y` | Microstrip feed point Y-offset from center | mm | -15.0 | 15.0 |
| `x[:, 4]` | `scale_slot` | Slotted perturbation scale factor ($0.0 = \text{solid patch}$) | unitless | 0.0 | 1.0 |
| `x[:, 5]` | `uw_3` | High-order modal notch width parameter | mm | 0.0 | 5.0 |

- **Shape**: `[Batch_Size, 6]`
- **Data Type**: `float32`
- **Normalization**: Min-Max scaling to $[0.0, 1.0]$:
  $$x_{\text{norm}} = \frac{x - x_{\min}}{x_{\max} - x_{\min}}$$

---

## 2. Output Tensor Specification

- **Shape**: `[Batch_Size, 102]`
- **Elements `0..100`**: $S_{11}(\text{dB})$ evaluated on uniform 101 points in $[2.0, 3.0]\text{ GHz}$:
  $$f_k = 2.0 + k \times 0.01 \quad (\text{GHz}), \quad k \in [0, 100]$$
- **Element `101`**: Broadside antenna realized gain ($G$) in $\text{dBi}$.
- **Data Type**: `float32`
