# Jasti RF Surrogate Feature & Metric Specification

## 1. Input Features

| Index | Feature | Meaning | Unit | Min | Max |
|---|---|---|---|---|---|
| 0 | `width` | Patch width ($W$) | mm | 15.0 | 60.0 |
| 1 | `length` | Patch resonant length ($L$) | mm | 15.0 | 60.0 |
| 2 | `height` | Substrate height ($h$) | mm | 0.5 | 3.2 |
| 3 | `dielectric_constant` | Relative permittivity ($\varepsilon_r$) | unitless | 2.0 | 10.0 |

- **Format**: 2D tabular array `[n_samples, 4]`
- **Scaling**: StandardScaler or raw physical features (tree models are invariant to monotonic feature scaling).

---

## 2. Output Targets

| Target Index | Target Name | Description | Unit |
|---|---|---|---|
| 0 | `resonant_frequency` | Predicted fundamental resonant frequency ($f_r$) | GHz |
| 1 | `bandwidth` | -10dB impedance bandwidth | MHz |

- **Format**: `[n_samples, 2]`
