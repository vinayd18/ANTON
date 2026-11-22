# ANTON — Stage 3 Import Formats and Data Ingestion Specification

---

### 1. Overview

ANTON incorporates dedicated, high-throughput parsing pipelines in [src/anton/datasets/importers/](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/datasets/importers/) for industry-standard electromagnetic simulation and measurement files. Live software automation of ANSYS HFSS or CST Studio Suite is intentionally decoupled; users export standard result files or load research datasets, which ANTON validates and normalizes.

---

### 2. Supported Ingestion Formats

#### 2.1 Touchstone Files (`.s1p`, `.s2p`)
Complies with EIA/IBIS Touchstone 1.0 and 1.1 specifications:
- **Option Line**: Begins with `#` specifying frequency unit, parameter type, numerical format, and reference impedance:
  ```
  # <frequency_unit> S <format> R <z0>
  ```
  - **Frequency Units**: `Hz`, `kHz`, `MHz`, `GHz`. Normalized to `GHz`.
  - **Data Formats**:
    - `RI`: Real part, Imaginary part.
    - `MA`: Linear magnitude, Phase angle in degrees.
    - `DB`: Logarithmic magnitude in dB ($20\log_{10}|S|$), Phase angle in degrees.
  - **Reference Impedance**: `R <z0>`, default $50.0\,\Omega$.
- **Comment Lines**: Lines prefixed with `!` are stripped and preserved in metadata.
- **Port Types**:
  - `.s1p`: Single-port reflection coefficient ($S_{11}$).
  - `.s2p`: Two-port scattering matrix. $S_{11}$ is extracted from columns 2 and 3.

#### 2.2 ANSYS HFSS CSV Reports
HFSS exports tabular CSV reports with variable column headers depending on HFSS version (2020 R2 through 2026):
- **Frequency Column**: Identified by case-insensitive matching of `Freq`. Units bracketed in header (e.g. `Freq [GHz]`, `Freq [MHz]`) are parsed and converted to GHz.
- **S-Parameter Representations**:
  - Real / Imaginary: `"re(S(1,1)) []"`, `"im(S(1,1)) []"`.
  - dB / Phase: `"dB(S(1,1)) []"`, `"ang_deg(S(1,1)) []"`.
  - Magnitude Only: `"dB(S(1,1)) []"`.
- **Gain Tables**: `"Freq [GHz]"`, `"dB(GainTotal) []"`, `"dB(RealizedGainTotal) []"`.
- **2D Radiation Patterns**: `"Theta [deg]"` or `"Phi [deg]"`, `"dB(GainTotal) []"`.

> [!WARNING]
> If an HFSS CSV export provides only `"dB(S(1,1)) []"` without phase angle, ANTON preserves it strictly as magnitude-only. It **never** fabricates a phase angle or synthesizes imaginary components.

#### 2.3 CST Studio Suite ASCII & CSV Exports
CST Studio Suite exports 1D frequency responses as tab- or space-delimited text or CSV:
- **Header Line**: Prefixed with `#` or `//`:
  ```
  # Frequency / GHz    S1,1/dB
  ```
  or
  ```
  # Frequency / GHz    S1,1/re    S1,1/im
  ```
- **Numerical Formatting**: Handles exponential scientific notation (e.g. `1.000000e+00`).
- **Power & Efficiency Tables**: Parses Radiation Efficiency and Total Efficiency.

#### 2.4 Published Scientific Datasets
1. **METU-SIMPL Microstrip Patch Benchmark Dataset**:
   - High-resolution ANSYS HFSS FEM simulations over $1.0\,\text{GHz}$ to $10.0\,\text{GHz}$ ($401$ frequency points).
   - Ingests $S_{11,\text{re}}$ and $S_{11,\text{im}}$ matrices alongside physical parameter sweeps ($W, L, h, x_f, y_f, \varepsilon_r$).
   - Automatically maps into canonical Stage 1 geometry dictionary.
2. **Antenna-AI-Benchmark Dataset**:
   - CST Microwave Studio transient solver corpus for generative antenna design.
   - Maps multi-frequency target profiles and synthesized geometry vectors.

---

### 3. Unit Normalization Standards

All physical quantities entering the dataset subsystem are converted into canonical SI/electromagnetic standard units:

| Physical Dimension | Canonical Unit | Supported Ingestion Units & Conversion Factors |
|---|---|---|
| **Frequency** | $\text{GHz}$ | $\text{Hz} \times 10^{-9}$, $\text{kHz} \times 10^{-6}$, $\text{MHz} \times 10^{-3}$, $\text{GHz} \times 1.0$ |
| **Geometry Length** | $\text{mm}$ | $\text{m} \times 1000.0$, $\text{cm} \times 10.0$, $\text{mm} \times 1.0$, $\text{in} \times 25.4$, $\text{mil} \times 0.0254$ |
| **Angle** | $\text{degrees}$ | $\text{radians} \times (180.0 / \pi)$, $\text{deg} \times 1.0$ |
| **S-Parameter Mag** | Linear & $\text{dB}$ | $|S_{11}| = 10^{S_{11,\text{dB}} / 20}$, $S_{11,\text{dB}} = 20 \log_{10}|S_{11}|$ |
| **Impedance** | $\Omega$ | $Z_{\text{in}} = Z_0 \frac{1 + S_{11}}{1 - S_{11}}$ (Complex $S_{11}$ required) |
| **Gain** | $\text{dBi}$ | $\text{Realized gain referenced to isotropic radiator}$ |

---

### 4. Resonance and Bandwidth Extraction

For all imported frequency curves, ANTON executes quadratic-interpolated local minimum detection on $S_{11,\text{dB}}$:
1. Resonant dips are identified where $S_{11,\text{dB}} \le -10.0\,\text{dB}$ and $S_{11}(f_i) < S_{11}(f_{i\pm 1})$.
2. Sub-grid frequency refinement is computed via 3-point parabolic fitting:
   $$f_{\text{res}} = f_0 - \frac{d_1}{d_2} \Delta f$$
3. The contiguous $-10\,\text{dB}$ impedance bandwidth interval $[f_{\text{low}}, f_{\text{high}}]$ is determined using linear edge interpolation.
4. Fractional bandwidth is computed as:
   $$\text{FBW} = \frac{f_{\text{high}} - f_{\text{low}}}{f_{\text{res}}} \times 100\%$$

