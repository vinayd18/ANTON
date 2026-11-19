# Antenna-Net Tensor & Normalization Specification

## 1. Input Tensor Specification

| Tensor Index | Parameter Name | Physical Meaning | Physical Unit | Training Range (Min, Max) | Normalization Formula |
|---|---|---|---|---|---|
| `x[:, 0]` | `patch_width` | Radiator physical width ($W$) | mm | $[10.0, 80.0]$ | $x_{\text{norm}} = \frac{W - 10.0}{70.0}$ |
| `x[:, 1]` | `patch_length` | Radiator resonant length ($L$) | mm | $[10.0, 80.0]$ | $x_{\text{norm}} = \frac{L - 10.0}{70.0}$ |
| `x[:, 2]` | `substrate_height` | Dielectric layer thickness ($h$) | mm | $[0.5, 3.2]$ | $x_{\text{norm}} = \frac{h - 0.5}{2.7}$ |
| `x[:, 3]` | `permittivity` | Relative permittivity ($\varepsilon_r$) | unitless | $[1.0, 10.2]$ | $x_{\text{norm}} = \frac{\varepsilon_r - 1.0}{9.2}$ |

- **Data Type**: `torch.float32`
- **Batch Shape**: `[Batch_Size, 4]`

---

## 2. Output Tensor Specification

- **Tensor Name**: `s11_db_curve`
- **Shape**: `[Batch_Size, 101]`
- **Data Type**: `torch.float32`
- **Frequency Grid**: Uniform 101 points from 1.0 GHz to 6.0 GHz:
  $$f_k = 1.0 + k \times \frac{6.0 - 1.0}{100} = 1.0 + 0.05 \cdot k \quad (\text{GHz}), \quad k \in [0, 100]$$
- **Physical Unit**: Decibels ($\text{dB}$)
- **Valid Range**: $S_{11} \in [-50.0, 0.0]\text{ dB}$

---

## 3. Pixelated Model Input Specification (12x12 Grid)

- **Tensor Name**: `pixel_grid`
- **Shape**: `[Batch_Size, 1, 12, 12]` or flattened `[Batch_Size, 144]`
- **Value Space**: Binary $\{0.0, 1.0\}$ where $1.0$ indicates copper metallization and $0.0$ indicates dielectric etching.

