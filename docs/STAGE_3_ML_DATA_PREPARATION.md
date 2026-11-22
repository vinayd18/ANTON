# ANTON — Stage 3 ML-Ready Dataset Preparation Specification

---

### 1. Overview

Surrogate neural networks in antenna design map geometric and material parameters to frequency responses (forward modeling), or synthesize physical dimensions from target S-parameters (inverse design). The preparation pipeline in [src/anton/datasets/ml/](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/datasets/ml/) prepares research-grade, leakage-free tensor arrays ready for manual model training.

---

### 2. Geometry-Leakage-Free Splitting

#### 2.1 The Data Contamination Hazard
In computational electromagnetics datasets, researchers frequently perform parameter sweeps around a nominal antenna design, or re-simulate the same geometry under varying mesh discretizations. If records are shuffled and split uniformly at random:

$$P(\text{Design}_i \in \text{Train} \land \text{Design}_i \in \text{Test}) > 0$$

The neural network memorizes the geometric signature, yielding falsely optimistic evaluation metrics (e.g. $R^2 > 0.99$, MSE $< 10^{-4}$) that fail completely when presented with an unseen antenna design.

#### 2.2 ANTON Partitioning Protocol
`DatasetSplitter` eliminates leakage by grouping records strictly on deterministic `geometry_hash`:
1. Every record $r$ is mapped to a geometry cluster $C_k = \{ r \mid \text{hash}(r.\text{geometry}) == H_k \}$.
2. If `group_near_duplicates=True`, disjoint set union merges clusters whose parameter distance satisfies $D(C_a, C_b) \le 0.01$.
3. Entire clusters are assigned atomically to `train`, `val`, or `test`.
4. Mathematical verification confirms:
   $$\text{Hashes}_{\text{train}} \cap \text{Hashes}_{\text{test}} = \emptyset, \quad \text{Hashes}_{\text{val}} \cap \text{Hashes}_{\text{test}} = \emptyset$$

---

### 3. Frequency Grid Resampling via PCHIP

Different EM solver sweeps frequently employ disparate frequency intervals ($1.0$ to $6.0\,\text{GHz}$, $2.0$ to $8.0\,\text{GHz}$) or non-uniform adaptive frequency distributions:
- **Resampling Method**: Piecewise Cubic Hermite Interpolating Polynomials (`PchipInterpolator`). Unlike standard cubic splines, PCHIP guarantees shape preservation and monotonicity, preventing artificial oscillations and overshooting near sharp resonant dips.
- **Strict Extrapolation Prohibition**:
  $$\text{TargetGrid} \subseteq [\min(f_{\text{source}}), \max(f_{\text{source}})]$$
  If the source simulation band does not fully cover the target grid, `FrequencyGridAligner` raises a `ValueError` rather than extrapolating speculative electromagnetic behavior.

---

### 4. Feature Extraction & 2D Rasterization

`FeatureExtractor` converts canonical Stage 1 models into continuous vectors or 2D image representations:
1. **Continuous 10-Parameter Vector**:
   $$X = [W_{\text{patch}}, L_{\text{patch}}, W_{\text{sub}}, L_{\text{sub}}, h, \varepsilon_r, \tan\delta, x_f, y_f, t_{\text{metal}}]$$
2. **2D Planar Conductivity Masks**:
   Rasterizes top-layer conductors into binary or continuous grids ($16\times 16$, $32\times 32$, $64\times 64$) spanning the substrate bounds $[-W_{\text{sub}}/2, W_{\text{sub}}/2] \times [-L_{\text{sub}}/2, L_{\text{sub}}/2]$:
   - Conductor: $1.0$
   - Dielectric: $0.0$
   - Accurately captures inset feed notches, central holes (annular rings), and arbitrary polygon cutouts.

---

### 5. Train-Only Feature Scaling

To prevent test-set distribution leakage into feature normalization:
- `MinMaxScaler` and `StandardScaler` compute their transformation statistics ($\min, \max, \mu, \sigma$) **strictly on the training split**:
  $$\mu = \frac{1}{N_{\text{train}}} \sum_{i \in \text{Train}} x_i, \quad \sigma = \sqrt{\frac{1}{N_{\text{train}}} \sum_{i \in \text{Train}} (x_i - \mu)^2}$$
- Validation and test splits are transformed using the frozen training statistics.
- Scaling parameters are serialized to JSON alongside model artifacts to ensure identical preprocessing during inference.

---

### 6. Model-Specific Adapters

| Adapter | Target Checkpoints | Input Tensor | Target Output Tensor | Compatibility Enforcements |
|---|---|---|---|---|
| `AntennaNetAdapter` | `s11_model.pt`, `best_forward_surrogate.pt` | $[W, L, h, \varepsilon_r]$ ($4\text{-dim}$) | $S_{11,\text{dB}}$ resampled to $101$ pts over $[1.0, 6.0]\,\text{GHz}$ | Rejects non-rectangular geometries. Rejects sweeps narrower than $[1.0, 6.0]\,\text{GHz}$. |
| `YouxchAdapter` | `saved-model-5000.h5` | 22-dimensional geometric/ratio vector | $[S_{11,\text{dB}}(101), \text{Gain}(101)]$ ($202\text{-dim}$) | Rejects non-patch geometries. Requires coverage of $[2.0, 8.0]\,\text{GHz}$. |
| `GenericAdapter` | Custom models & Jasti RNN | Parametric vector + optional 2D raster mask | Configurable resampled $S_{11}$ or Complex S11 | User-configurable frequency grids and parameter mappings. |
