# ANTON — Stage 3 Canonical Dataset Schema Specification

---

### 1. Overview

The canonical dataset schema is defined in [src/anton/datasets/schema.py](file:///c:/Users/adewa/Pictures/Anton%202/src/anton/datasets/schema.py) using Pydantic v2. It provides type safety, runtime validation, physical sanity constraints, and seamless serialization.

---

### 2. Schema Components

#### 2.1 Antenna Identity (`AntennaIdentity`)
Uniquely identifies the antenna design, its canonical geometry reference, and high-level data origin.

| Field | Type | Description |
|---|---|---|
| `design_id` | `str` | Unique identifier for the antenna design (e.g. `design_001`). |
| `geometry_id` | `str` | Reference to Stage 1 canonical geometry entity. |
| `geometry_hash` | `str` | Deterministic SHA-256 hash of canonical geometry JSON. |
| `geometry_family` | `str` | Family (e.g. `RECTANGULAR_PATCH`, `CIRCULAR_PATCH`, `INSET_FED_PATCH`). |
| `dataset_record_id` | `str` | Globally unique record ID in the dataset store (e.g. `rec_a8f9021`). |
| `design_version` | `str` | Revision string, defaults to `"1.0.0"`. |
| `created_at` | `str` | Creation timestamp in ISO-8601 UTC. |
| `data_source` | `SourceType` | Origin: `HFSS_SIMULATION`, `CST_SIMULATION`, `EXPERIMENTAL_MEASUREMENT`, `PUBLISHED_DATASET`, `ANALYTICAL_APPROXIMATION`. |
| `source_reference` | `Optional[str]` | File path, DOI, or publication citation. |
| `is_simulation` | `bool` | True if derived from computational electromagnetic solver. |
| `is_measurement` | `bool` | True if measured with a vector network analyzer. |
| `is_analytical` | `bool` | True if derived from closed-form transmission-line or cavity model. |

> [!IMPORTANT]
> The Pydantic model validator automatically enforces that if `data_source == ANALYTICAL_APPROXIMATION`, `is_analytical` is set to `True` and `is_simulation` is set to `False`. Analytical formulas can never masquerade as full-wave simulation ground truth.

#### 2.2 Material Properties (`MaterialPropertiesRecord`)
Preserves nominal values and frequency-dependent dispersion tables.

| Field | Type | Constraint | Description |
|---|---|---|---|
| `name` | `str` | Non-empty | Commercial or standard substrate designation (e.g. `Rogers RT/duroid 5880`). |
| `permittivity_r` | `float` | `> 0.0` | Nominal relative dielectric constant ($\varepsilon_r$). |
| `permeability_r` | `float` | `> 0.0` | Nominal relative permeability ($\mu_r$), defaults to `1.0`. |
| `loss_tangent` | `float` | `>= 0.0` | Dielectric loss tangent ($\tan\delta$). |
| `conductivity` | `Optional[float]` | `>= 0.0` | Conductor bulk conductivity in $\text{S/m}$ (e.g. $5.8 \times 10^7\,\text{S/m}$ for copper). |
| `substrate_thickness_mm` | `float` | `> 0.0` | Dielectric substrate height $h$ in millimeters. |
| `is_frequency_dependent` | `bool` | - | True if material parameters vary across frequency sweep. |
| `frequency_table` | `Optional[Dict]` | - | Table mapping frequencies to $\varepsilon_r(f)$ and $\tan\delta(f)$. |
| `model_reference` | `Optional[str]` | - | Dispersion model (Debye, Drude, Djordjevic-Sarkar). |

#### 2.3 Simulation Metadata (`SimulationMetadataRecord`)
Captures full-wave solver execution settings, boundary conditions, and convergence metrics.

| Field | Type | Description |
|---|---|---|
| `solver_name` | `str` | Solver brand and product (e.g. `HFSS`, `CST Studio Suite`). |
| `solver_version` | `Optional[str]` | Software release (e.g. `2024 R2`, `2026`). |
| `simulation_method` | `Optional[str]` | Numerical method: `FEM`, `FIT`, `FDTD`, `MoM`, `BEM`. |
| `solution_type` | `Optional[str]` | Solution domain: `Modal`, `Terminal`, `Transient`, `Eigenmode`. |
| `z0_ohm` | `float` | Port reference characteristic impedance in Ohms (default $50.0\,\Omega$). |
| `adaptive_passes` | `Optional[int]` | Completed adaptive meshing passes. |
| `convergence_status` | `Optional[str]` | Convergence message from solver (e.g. `delta S < 0.02`). |
| `is_converged` | `Optional[bool]` | True if adaptive mesh satisfied convergence stopping criterion. |

#### 2.4 Electromagnetic Outputs (`ElectromagneticOutputsRecord`)
Holds discrete frequency sweep arrays and radiation metrics. Strictly catalogs missing outputs so absence is never confused with zero.

| Field | Type | Description |
|---|---|---|
| `frequencies_ghz` | `List[float]` | Strictly increasing frequency grid points in GHz. |
| `s11_real` | `Optional[List[float]]` | Real component of reflection coefficient $\text{Re}(S_{11})$. |
| `s11_imag` | `Optional[List[float]]` | Imaginary component of reflection coefficient $\text{Im}(S_{11})$. |
| `s11_magnitude` | `Optional[List[float]]` | Linear reflection coefficient magnitude $|S_{11}|$. |
| `s11_phase_rad` | `Optional[List[float]]` | Reflection coefficient phase in radians ($-\pi$ to $+\pi$). |
| `s11_db` | `Optional[List[float]]` | Return loss in decibels: $20 \log_{10}(\|S_{11}\|)$. |
| `vswr` | `Optional[List[float]]` | Voltage Standing Wave Ratio: $(1+\|S_{11}\|)/(1-\|S_{11}\|)$. |
| `zin_real` | `Optional[List[float]]` | Real input impedance (radiation + loss resistance) in Ohms. |
| `zin_imag` | `Optional[List[float]]` | Imaginary input impedance (input reactance) in Ohms. |
| `resonant_frequencies_ghz` | `Optional[List[float]]` | Detected resonance frequencies below $-10\,\text{dB}$. |
| `impedance_bandwidth_mhz` | `Optional[float]` | $-10\,\text{dB}$ impedance bandwidth in MHz. |
| `bandwidth_percentage` | `Optional[float]` | Fractional bandwidth percentage $\text{FBW} = (\Delta f / f_0) \times 100\%$. |
| `gain_dbi` | `Optional[List[float]]` | Realized gain vs frequency in dBi. |
| `radiation_efficiency` | `Optional[List[float]]` | Radiation efficiency ($0.0$ to $1.0$). |
| `has_complex_s11` | `bool` | True if both real and imaginary S11 components are present. |
| `missing_outputs` | `List[str]` | Explicit list of absent quantities (e.g. `['complex_s11', 'gain']`). |

---

### 3. Canonical Record Container (`DatasetRecord`)

A complete record binds identity, Stage 1 canonical geometry, materials, simulation metadata, outputs, and provenance:

```json
{
  "antenna_identity": {
    "design_id": "design_rect_245",
    "geometry_id": "geo_rect_245",
    "geometry_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "geometry_family": "RECTANGULAR_PATCH",
    "dataset_record_id": "rec_hfss_00192",
    "design_version": "1.0.0",
    "created_at": "2026-11-22T22:00:00Z",
    "data_source": "HFSS_SIMULATION",
    "is_simulation": true,
    "is_measurement": false,
    "is_analytical": false
  },
  "geometry": {
    "name": "rectangular_patch_245",
    "family": "RECTANGULAR_PATCH",
    "patch": {
      "shape": "RECTANGULAR",
      "width": 30.0,
      "length": 25.0,
      "metal_thickness": 0.035
    },
    "substrate": {
      "width": 60.0,
      "length": 50.0,
      "thickness": 1.6,
      "material": "FR4_epoxy"
    },
    "ground_plane": {
      "type": "SOLID",
      "width": 60.0,
      "length": 50.0,
      "metal_thickness": 0.035
    },
    "feed": {
      "type": "MICROSTRIP_LINE",
      "width": 3.0,
      "position": [0.0, -12.5]
    }
  },
  "materials": {
    "name": "FR4_epoxy",
    "permittivity_r": 4.4,
    "permeability_r": 1.0,
    "loss_tangent": 0.02,
    "substrate_thickness_mm": 1.6
  },
  "simulation_metadata": {
    "solver_name": "HFSS",
    "z0_ohm": 50.0,
    "is_converged": true
  },
  "outputs": {
    "frequencies_ghz": [2.0, 2.45, 3.0],
    "s11_db": [-4.5, -21.2, -3.8],
    "s11_magnitude": [0.596, 0.087, 0.646],
    "vswr": [3.95, 1.19, 4.65],
    "has_complex_s11": false,
    "missing_outputs": ["complex_s11", "input_impedance", "gain"]
  },
  "provenance": {
    "source_type": "HFSS_SIMULATION",
    "source_filename": "patch_sweep.csv",
    "imported_at": "2026-11-22T22:00:00Z",
    "anton_version": "0.1.0"
  },
  "quality_status": "VERIFIED"
}
```
