# ANTON — STAGE 2 COMPLETE NOTEBOOK ARCHITECTURE & ENGINEERING AUDIT REPORT

**Date:** November 13, 2026  
**Status:** AUDIT COMPLETED — PENDING USER AUTHORIZATION FOR REPAIRS  
**Repository:** ANTON Universal Antenna Geometry Engine  
**Author:** Antigravity Senior Scientific Software Architect & RF/Microwave Engineer  
**Deliverable Document:** `STAGE_2_COMPLETE_NOTEBOOK_ARCHITECTURE_AUDIT.md`  

---

## EXECUTIVE SUMMARY

A rigorous, full-system engineering audit of all eight ANTON-generated ANSYS HFSS reproduction notebooks and their shared notebook-generation architecture was conducted.

The investigation confirms that the defects identified earlier in `annular_patch_hfss.ipynb` were **not isolated anomalies**, but rather symptoms of **deep systemic architectural defects** embedded in the shared generation pipeline:
1. **Pervasive PyAEDT API Hallucination (Cross-Notebook Critical):** Modeler and boundary generators invoke non-existent PyAEDT methods—specifically `app.modeler.extrude_sheet()`, `app.materials.check_if_exists()`, and `app.assign_radiation_boundary_to_objects()`. These methods do not exist in the official PyAEDT API and cause immediate runtime crashes (`AttributeError`) upon execution in live AEDT environments across all eight notebooks.
2. **Lumped Port Keyword Argument Mismatches (Cross-Notebook Critical):** `feed_port_generator.py` passes `integration_line` to `create_lumped_port_to_sheet()` (which expects `axisdir`) and passes `assignment` to `lumped_port()` (which expects `signal`), triggering fatal `TypeError` exceptions.
3. **Physical & Topological Feed Defects (Antenna-Specific Critical):**
   - **`rectangular_patch`:** The feed line terminates at $y = -27.0\,\text{mm}$, leaving a $3.0\,\text{mm}$ gap to the substrate edge ($y = -30.0\,\text{mm}$). The lumped port sheet is placed at $y = -27.0\,\text{mm}$, floating inside the dielectric substrate rather than on the outer background boundary.
   - **`inset_feed_patch`:** Severe double-defect:
     - The feed line terminates at $y = -30.0\,\text{mm}$, leaving a $5.0\,\text{mm}$ gap to the substrate edge ($y = -35.0\,\text{mm}$). The port is placed floating inside the substrate volume.
     - The feed conductor and radiating patch occupy the exact same physical space between $y = -10.0\,\text{mm}$ and $y = -2.0\,\text{mm}$ ($3.0 \times 8.0\,\text{mm}$ overlap), creating intersecting 3D copper solids that violate ACIS modeling and EM physics.
4. **Driven Terminal vs. Modal Solution Mismatch (Cross-Notebook High):** Cell 4 initializes HFSS with `solution_type="Terminal"`, but Cell 20 attempts to query modal report trace `'S(1,1)'`. In Driven Terminal designs, S-parameters are indexed by terminal names (e.g., `St(1,1)` or `S(Port1:1, Port1:1)`). The post-processor cannot extract `'S(1,1)'` from a terminal setup.
5. **Absence of Far-Field Setup (Cross-Notebook High):** Cell 22 attempts to query `dB(GainTotal)` with context `"3D"`, but neither Cell 14 nor Cell 16 creates an Infinite Sphere radiation setup (`insert_infinite_sphere`), guaranteeing a post-processing failure.
6. **False Sense of Security from Prior Testing (Process Critical):** All 76 automated tests passed because they performed only AST syntax parsing (`ast.parse`) and string keyword checks. None of the tests validated runtime signatures against PyAEDT or executed against mocked AEDT objects.

**Current Stage 2 Status:** FAILED ENGINEERING AUDIT.  
No source code has been modified in this turn. This document details all findings, root causes, severity rankings, and the proposed remediation plan for user authorization.

---

## PART A — AUDIT OF ALL EIGHT NOTEBOOKS

An exhaustive cell-by-cell inspection was performed on all eight generated Jupyter Notebooks in `examples/notebooks/`.

```
├── examples/notebooks/rectangular_patch_hfss.ipynb
├── examples/notebooks/circular_patch_hfss.ipynb
├── examples/notebooks/triangular_patch_hfss.ipynb
├── examples/notebooks/hexagonal_patch_hfss.ipynb
├── examples/notebooks/u_slot_patch_hfss.ipynb
├── examples/notebooks/inset_feed_patch_hfss.ipynb
├── examples/notebooks/annular_patch_hfss.ipynb
└── examples/notebooks/custom_polygon_patch_hfss.ipynb
```

Each notebook contains 27 cells (14 Markdown documentation cells and 13 executable Python code cells).

### 1. `rectangular_patch_hfss.ipynb`
- **Cell 4 (Connection):** Configures `solution_type="Terminal"`. Incompatible with Cell 20 querying `S(1,1)`.
- **Cell 6 (Materials):** Calls `app.materials.check_if_exists('FR4_epoxy')`. Method does not exist in PyAEDT.
- **Cell 8 (Stackup):** Correctly creates `GroundPlane` ($60 \times 60 \times 0.035\,\text{mm}$) at $z=-0.035\,\text{mm}$ and `SubstrateBlock` ($60 \times 60 \times 1.6\,\text{mm}$) at $z=0$.
- **Cell 10 (Patch & Feed):**
  - Creates `Radiator` ($38 \times 29 \times 0.035\,\text{mm}$) from $y = -11.5\,\text{mm}$ to $y = +17.5\,\text{mm}$.
  - Creates `FeedLine` ($3.1 \times 15.5 \times 0.035\,\text{mm}$) from $y = -27.0\,\text{mm}$ to $y = -11.5\,\text{mm}$.
  - **CRITICAL DEFECT:** Feed line terminates at $y = -27.0\,\text{mm}$. Substrate bottom edge is at $y = -30.0\,\text{mm}$. A $3.0\,\text{mm}$ gap exists between feed line and substrate edge.
- **Cell 12 (Port):**
  - Places port sheet at `port_y = -0.027` ($y = -27.0\,\text{mm}$), floating $3.0\,\text{mm}$ inside the substrate interior.
  - Passes invalid argument `integration_line` to `create_lumped_port_to_sheet` (PyAEDT expects `axisdir`).
- **Cell 14 (Airbox & Boundary):**
  - Calls `app.assign_radiation_boundary_to_objects()`. Method does not exist in PyAEDT.
- **Cell 16 (Setup & Mesh):**
  - Setup type mismatch: `HFSSDrivenAuto` with Driven Terminal.
  - Mesh refinement finds `Radiator` (`'radiator' in name.lower()`), sets `maxlength=0.005`.
- **Cell 20 (Result Extraction):** Queries `'S(1,1)'`. Will return None or error under Driven Terminal.
- **Cell 22 (Visualization):** Queries `dB(GainTotal)` with context `"3D"`. Fails because no Infinite Sphere was created.

### 2. `circular_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch with `S(1,1)`.
- **Cell 6 (Materials):** Calls `check_if_exists()`. Method does not exist.
- **Cell 8 (Stackup):** Creates `Ground` ($65 \times 65 \times 0.035\,\text{mm}$) and `Substrate` ($65 \times 65 \times 1.524\,\text{mm}$, Rogers RO4003C).
- **Cell 10 (Patch & Feed):**
  - Creates `CircularDisk` using `create_cylinder(radius=0.016, height=3.5e-05)`.
  - Creates `EdgeFeed` ($3.4 \times 16.5 \times 0.035\,\text{mm}$) from $y = -32.5\,\text{mm}$ to $y = -16.0\,\text{mm}$.
  - Connectivity is physically correct (touches circle at $y=-16\,\text{mm}$ and reaches substrate edge at $y=-32.5\,\text{mm}$).
- **Cell 12 (Port):**
  - Port sheet correctly at $y = -32.5\,\text{mm}$.
  - Fatal argument mismatches: `assignment` in `lumped_port` and `integration_line` in `create_lumped_port_to_sheet`.
- **Cell 14 (Airbox):** Invalid boundary method calls `assign_radiation_boundary_to_objects`.
- **Cell 16 (Setup & Mesh):**
  - **DEFECT:** Mesh refinement filter: `[obj.name for obj in app.modeler.object_list if 'patch' in obj.name.lower() or 'radiator' in obj.name.lower()]`.
  - The object is named `CircularDisk` (contains neither `'patch'` nor `'radiator'`). Filter returns `[]`. Mesh refinement is silently skipped!
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 3. `triangular_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $60 \times 60\,\text{mm}$ substrate ($h=0.762\,\text{mm}$, Rogers RO4350B).
- **Cell 10 (Patch & Feed):**
  - Creates `TriangularRadiator` via `create_polyline(close_surface=True, cover_surface=True)`.
  - **FATAL RUNTIME CRASH:** Line calling `app.modeler.extrude_sheet(solid_TriangularRadiator.name, 3.5e-05)`. `extrude_sheet()` does not exist in PyAEDT.
  - `TriangleFeedLine` created from $y = -30.0\,\text{mm}$ to $y = -10.104\,\text{mm}$ (touches flat triangle base).
- **Cell 12 (Port):** Port sheet at $y = -30.0\,\text{mm}$. Fatal port API argument mismatches.
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Finds `TriangularRadiator`. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 4. `hexagonal_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $70 \times 70\,\text{mm}$ substrate ($h=1.575\,\text{mm}$, RT/Duroid 5880).
- **Cell 10 (Patch & Feed):**
  - Creates `HexagonalRadiator` via `create_polyline()`.
  - **FATAL RUNTIME CRASH:** Calls non-existent `app.modeler.extrude_sheet()`.
  - `HexagonFeedLine` created from $y = -35.0\,\text{mm}$ to $y = -15.588\,\text{mm}$ (touches flat bottom hexagon edge).
- **Cell 12 (Port):** Port sheet at $y = -35.0\,\text{mm}$. Fatal port API argument mismatches.
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Finds `HexagonalRadiator`. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 5. `u_slot_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $70 \times 65\,\text{mm}$ substrate ($h=1.524\,\text{mm}$, Rogers RO4003C).
- **Cell 10 (Patch & Feed):**
  - Creates `USlottedRadiator` polyline sheet.
  - **FATAL RUNTIME CRASH #1:** Calls non-existent `app.modeler.extrude_sheet(solid_USlottedRadiator.name, 3.5e-05)`.
  - Creates `hole_USlottedRadiator` cutter polyline sheet.
  - **FATAL RUNTIME CRASH #2:** Calls non-existent `app.modeler.extrude_sheet(hole_USlottedRadiator.name, 5.25e-05)`.
  - Calls `app.modeler.subtract()`.
  - Creates `USlotFeedLine` ($3.4 \times 18.5 \times 0.035\,\text{mm}$) from $y = -32.5\,\text{mm}$ to $y = -14.0\,\text{mm}$.
- **Cell 12 (Port):** Port sheet at $y = -32.5\,\text{mm}$. Fatal port API argument mismatches.
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Finds `USlottedRadiator`. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 6. `inset_feed_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $70 \times 70\,\text{mm}$ substrate ($h=1.6\,\text{mm}$, FR4).
- **Cell 10 (Patch & Feed):**
  - Creates `NotchedRadiator` via polyline sheet.
  - **FATAL RUNTIME CRASH:** Calls non-existent `app.modeler.extrude_sheet()`.
  - **CRITICAL PHYSICAL/CAD DEFECT #1 (Double Conductor Overlap):**
    - `NotchedRadiator` contains copper in the central tongue between $x \in [-1.5, 1.5]\,\text{mm}$ and $y \in [-10.0, -2.0]\,\text{mm}$.
    - `InsetFeedLine` is defined as a separate box from $y = -30.0\,\text{mm}$ to $y = -2.0\,\text{mm}$ ($w = 3.0\,\text{mm}$).
    - In the region $y \in [-10.0, -2.0]\,\text{mm}$, BOTH `NotchedRadiator` and `InsetFeedLine` occupy the exact same 3D volume ($3.0 \times 8.0\,\text{mm}$ overlap area of $24\,\text{mm}^2$). HFSS will fail ACIS body intersection checks and produce double-boundary meshing errors.
  - **CRITICAL PHYSICAL/CAD DEFECT #2 (Feed Termination Gap):**
    - Substrate bottom edge is at $y = -35.0\,\text{mm}$.
    - `InsetFeedLine` starts at $y = -30.0\,\text{mm}$.
    - A $5.0\,\text{mm}$ gap exists between the feed line and the substrate edge!
- **Cell 12 (Port):**
  - Places port sheet at $y = -30.0\,\text{mm}$, floating $5.0\,\text{mm}$ inside the substrate dielectric volume.
  - Fatal port API argument mismatches.
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Finds `NotchedRadiator`. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 7. `annular_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $60 \times 60\,\text{mm}$ substrate ($h=1.0\,\text{mm}$, Alumina).
- **Cell 10 (Patch & Feed):**
  - Creates `AnnularRingRadiator` and `AnnularRingRadiator_cutter`.
  - **FATAL RUNTIME CRASH:** Calls non-existent `app.modeler.extrude_sheet()`.
  - Feed line correctly placed from $y = -30.0\,\text{mm}$ to $y = -18.0\,\text{mm}$ (outer rim).
- **Cell 12 (Port):**
  - Port sheet correctly at $y = -30.0\,\text{mm}$ with $+Z$ integration line (no longer inside the hole).
  - Fatal port API argument mismatches (`assignment` and `integration_line`).
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Setup frequency at $3.0\,\text{GHz}$. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

### 8. `custom_polygon_patch_hfss.ipynb`
- **Cell 4 (Connection):** `solution_type="Terminal"` mismatch.
- **Cell 6 (Materials):** `check_if_exists()` hallucination.
- **Cell 8 (Stackup):** Creates $60 \times 60\,\text{mm}$ substrate ($h=0.8\,\text{mm}$, Rogers RO4350B).
- **Cell 10 (Patch & Feed):**
  - Creates 8-vertex `SteppedPolygonRadiator`.
  - **FATAL RUNTIME CRASH:** Calls non-existent `app.modeler.extrude_sheet()`.
  - `PolygonFeedLine` created from $y = -30.0\,\text{mm}$ to $y = -12.0\,\text{mm}$ (touches stepped base).
- **Cell 12 (Port):** Port sheet at $y = -30.0\,\text{mm}$. Fatal port API argument mismatches.
- **Cell 14 (Airbox):** Non-existent boundary methods.
- **Cell 16 (Setup & Mesh):** Finds `SteppedPolygonRadiator`. Terminal setup mismatch.
- **Cell 20 & 22:** S(1,1) terminal mismatch and missing Infinite Sphere context `"3D"`.

---

## PART B — AUDIT OF SHARED GENERATOR MODULES

### 1. `src/anton/notebook/hfss_code_generator.py`
- **Defect 1: Non-existent method `extrude_sheet()`**
  - Lines 67, 109, 114, 129, 145, 158:
    `app.modeler.extrude_sheet(solid_{obj_name}.name, {t})`
  - In PyAEDT, extruding a 2D sheet into a 3D solid is done via:
    `app.modeler.sweep_along_vector(names=solid_{obj_name}.name, vector=[0, 0, {t}])`
    or `app.modeler.thicken_sheet(object_name=solid_{obj_name}.name, thickness={t})`.
  - Calling `extrude_sheet()` raises `AttributeError: 'Modeler3D' object has no attribute 'extrude_sheet'`.
- **Defect 2: Invalid `create_ellipse` arguments**
  - Line 105: Passes `csPlane='XY', position=[...], major_radius=..., ratio=...`.
  - PyAEDT expects `cs_axis='Z', center=[...]`.
- **Defect 3: Single-hole limitation in interior cutouts**
  - Lines 148–167: Only inspects `obj.inner_vertices`. Cannot handle multiple cutouts.
- **Defect 4: Missing Boolean Union between feed and patch**
  - In geometries like inset feed, conductive feed line and patch are created as separate intersecting solids rather than unified conductors.

### 2. `src/anton/notebook/material_code_generator.py`
- **Defect 1: Non-existent method `check_if_exists()`**
  - Lines 50, 55, 70:
    `app.materials.check_if_exists(...)`
  - In PyAEDT, the method is `app.materials.checkifmaterialexists(...)` (no underscores) or Python `mat_name in app.materials`.
  - Raises `AttributeError: 'Materials' object has no attribute 'check_if_exists'` in Cell 6 of all 8 notebooks.

### 3. `src/anton/notebook/boundary_setup_generator.py`
- **Defect 1: Non-existent method `assign_radiation_boundary_to_objects()`**
  - Line 99:
    `app.assign_radiation_boundary_to_objects(airbox.name)`
- **Defect 2: Non-existent fallback `assign_radiation_boundary_to_faces()`**
  - Line 104:
    `app.assign_radiation_boundary_to_faces(airbox.faces)`
  - In PyAEDT, the canonical method is `app.assign_radiation_boundary(assignment=airbox.name, name="Rad1")` or `app.create_open_region(frequency=...)`.
  - Both attempts fail, raising `RuntimeError` in Cell 14 of all 8 notebooks.
- **Defect 3: Missing Infinite Sphere Far-Field Setup**
  - Neither this generator nor `solution_setup_generator.py` creates an Infinite Sphere radiation setup (`app.insert_infinite_sphere(name="3D")`). Without it, 3D far-field radiation patterns cannot be computed.

### 4. `src/anton/notebook/feed_port_generator.py`
- **Defect 1: Invalid keyword arguments in `create_lumped_port_to_sheet`**
  - Line 186: Passes `integration_line=[int_line_start, int_line_stop]`.
  - PyAEDT `create_lumped_port_to_sheet()` expects `axisdir=[int_line_start, int_line_stop]`.
  - Raises `TypeError: create_lumped_port_to_sheet() got an unexpected keyword argument 'integration_line'`.
- **Defect 2: Invalid keyword arguments in `lumped_port`**
  - Line 174: Passes `assignment=port_sheet.name`.
  - PyAEDT `lumped_port()` expects `signal=port_sheet.name`.
  - Raises `TypeError: lumped_port() got an unexpected keyword argument 'assignment'`.
- **Defect 3: Hardcoded XZ orientation assumption**
  - Lines 150, 157: Always creates port sheets in the `XZ` plane (`orientation='XZ'`), assuming feeds always run along $Y$. Feeds running along $X$ require a `YZ` plane port sheet.
- **Defect 4: Integration line vector convention**
  - Line 168: Integration line runs Ground $\rightarrow$ Signal. In PyAEDT/HFSS, standard convention for lumped ports is Signal $\rightarrow$ Ground (`axisdir=[signal_pt, ground_pt]`).

### 5. `src/anton/notebook/solution_setup_generator.py`
- **Defect 1: Setup type mismatch with Driven Terminal**
  - Line 30: Creates `HFSSDrivenAuto` or `HFSS` setup while the parent application is in Driven Terminal mode.
- **Defect 2: Narrow mesh refinement search filter**
  - Line 70: Searches only for `'patch'` or `'radiator'` in object names. Fails to match objects named `CircularDisk`, `BasePatch`, `SteppedConductor`, etc.

### 6. `src/anton/notebook/result_extraction_generator.py`
- **Defect 1: S-parameter expression mismatch**
  - Line 56: Hardcodes `app.post.get_report_data('S(1,1)', ...)`. Under Driven Terminal mode, this expression does not exist in HFSS.
- **Defect 2: Missing Far-Field Setup handling**
  - Line 158: Queries `dB(GainTotal)` with context `"3D"`, which will throw an exception because no 3D far-field infinite sphere setup was ever created.

### 7. `src/anton/notebook/notebook_generator.py`
- **Defect 1: Hardcoded `solution_type="Terminal"`**
  - Line 190: Hardcodes `solution_type="Terminal"` in Cell 4, conflicting with modal S-parameter extraction in Cell 20.

### 8. `src/anton/notebook/notebook_validator.py`
- **Defect 1: Purely static AST validation**
  - Only checks Python syntax grammar via `ast.parse()` and coarse regex keywords.
  - Does not check whether API calls match PyAEDT method signatures or argument names.
  - Allows syntactically valid but runtime-broken code to pass validation.

### 9. `scripts/create_examples.py`
- **Defect 1: `build_rectangular_patch()` feed line gap**
  - Feed line defined from $y = -27.0\,\text{mm}$ to $y = -11.5\,\text{mm}$, while substrate edge is at $y = -30.0\,\text{mm}$ ($3.0\,\text{mm}$ gap).
- **Defect 2: `build_inset_feed_patch()` feed line gap**
  - Feed line defined from $y = -30.0\,\text{mm}$ to $y = -2.0\,\text{mm}$, while substrate edge is at $y = -35.0\,\text{mm}$ ($5.0\,\text{mm}$ gap).
- **Defect 3: `build_inset_feed_patch()` overlapping conductors**
  - Notched patch and inset feed line overlap over $3.0 \times 8.0\,\text{mm}$ between $y = -10.0\,\text{mm}$ and $y = -2.0\,\text{mm}$.
- **Defect 4: Single-hole limitation in `src/anton/operations/boolean.py`**
  - Line 56: `hole_coords = list(shape.interiors[0].coords)` silently discards all cutouts after the first one.

---

## PART C — 15-POINT ENGINEERING VERIFICATION MATRIX

| Verification Criterion | `rectangular` | `circular` | `triangular` | `hexagonal` | `u_slot` | `inset_feed` | `annular` | `custom_polygon` |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Canonical Geometry Fidelity** | PASS | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS |
| **2. Construction & Booleans** | PASS | PASS | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **3. Substrate & Ground Positioning** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **4. Material Assignment** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **5. Feed Connectivity & Gaps** | **FAIL** | PASS | PASS | PASS | PASS | **FAIL** | PASS | PASS |
| **6. Port Geometry & Integration Line** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **7. Reference Conductor Assignment** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **8. Airbox Dimensions & Padding** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **9. Radiation Boundary Assignment** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **10. Solution Setup & Frequency Sweep** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **11. Mesh Configuration** | PASS | **FAIL** | PASS | PASS | PASS | PASS | PASS | PASS |
| **12. S-Parameter Extraction** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **13. VSWR & Input Impedance Calculation** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| **14. Far-Field & Radiation Pattern** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **15. Project Save & Session Release** | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

### Analysis of the 15 Criteria:
1. **Canonical Geometry Fidelity:** Inset feed fails because `NotchedRadiator` does not actually cut out the feed tongue, resulting in overlapping bodies.
2. **Construction & Booleans:** 6 of 8 antennas fail because `app.modeler.extrude_sheet()` does not exist in PyAEDT.
3. **Substrate & Ground:** All 8 antennas have correct non-overlapping Z-coordinates ($z \in [-35\,\mu\text{m}, 0]$ for ground, $z \in [0, h]$ for substrate).
4. **Material Assignment:** All 8 fail because `app.materials.check_if_exists()` does not exist in PyAEDT.
5. **Feed Connectivity:** `rectangular_patch` has a $3\,\text{mm}$ gap to the edge; `inset_feed` has a $5\,\text{mm}$ gap and an overlapping conductor body.
6. **Port Geometry:** All 8 fail because `create_lumped_port_to_sheet()` receives invalid parameter `integration_line` instead of `axisdir`.
7. **Reference Conductor:** Modeler ground plane detection logic works correctly.
8. **Airbox Dimensions:** Canonical bounding box calculation and $\lambda_0/4$ padding are mathematically sound.
9. **Radiation Boundary:** All 8 fail because `assign_radiation_boundary_to_objects()` does not exist in PyAEDT.
10. **Solution Setup:** All 8 fail due to the `DrivenTerminal` vs `HFSSDrivenAuto` setup type mismatch.
11. **Mesh Configuration:** `circular_patch` fails because `CircularDisk` is excluded by the name filter.
12. **S-Parameter Extraction:** All 8 fail because `S(1,1)` does not exist in Driven Terminal designs.
13. **VSWR & Impedance Calculation:** Formulas ($Z_0 \frac{1+\Gamma}{1-\Gamma}$, $\frac{1+\|\Gamma\|}{1-\|\Gamma\|}$) are mathematically sound.
14. **Far-Field Extraction:** All 8 fail because no Infinite Sphere far-field setup is configured in HFSS.
15. **Save & Release:** Save project and release desktop calls are syntactically sound and non-blocking.

---

## PART D — SEVERITY-RANKED DEFECT CLASSIFICATION

### Defect 1: PyAEDT Hallucination — `app.modeler.extrude_sheet()`
- **Severity:** **CRITICAL**
- **Affected Notebooks:** `annular_patch`, `custom_polygon_patch`, `hexagonal_patch`, `triangular_patch`, `u_slot_patch`, `inset_feed_patch` (6 of 8 notebooks).
- **Cell:** Cell 10.
- **Shared Source Module:** `src/anton/notebook/hfss_code_generator.py` (lines 67, 109, 114, 129, 145, 158) and `stackup_code_generator.py` (line 93).
- **Exact Code:** `app.modeler.extrude_sheet(solid_{obj_name}.name, {t})`
- **Root Cause:** Method does not exist in PyAEDT.
- **Engineering Impact:** Immediate crash with `AttributeError` when constructing 3D solids.
- **Recommended Correction:** Replace with `app.modeler.sweep_along_vector(names=solid_{obj_name}.name, vector=[0, 0, {t}])` or `app.modeler.thicken_sheet(object_name=solid_{obj_name}.name, thickness={t})`.

---

### Defect 2: PyAEDT Hallucination — `app.materials.check_if_exists()`
- **Severity:** **CRITICAL**
- **Affected Notebooks:** ALL EIGHT NOTEBOOKS (8 of 8).
- **Cell:** Cell 6.
- **Shared Source Module:** `src/anton/notebook/material_code_generator.py` (lines 50, 55, 70).
- **Exact Code:** `if app.materials.check_if_exists(mat_name):`
- **Root Cause:** Method does not exist in PyAEDT. The real method is `checkifmaterialexists()` (no underscores) or Python `mat_name in app.materials`.
- **Engineering Impact:** Immediate crash with `AttributeError` during material configuration.
- **Recommended Correction:** Replace with `if mat_name in app.materials:` or `if app.materials.checkifmaterialexists(mat_name):`.

---

### Defect 3: PyAEDT Hallucination — `app.assign_radiation_boundary_to_objects()`
- **Severity:** **CRITICAL**
- **Affected Notebooks:** ALL EIGHT NOTEBOOKS (8 of 8).
- **Cell:** Cell 14.
- **Shared Source Module:** `src/anton/notebook/boundary_setup_generator.py` (lines 99, 104).
- **Exact Code:** `app.assign_radiation_boundary_to_objects(airbox.name)` and `app.assign_radiation_boundary_to_faces(airbox.faces)`
- **Root Cause:** Methods do not exist in PyAEDT. The canonical method is `app.assign_radiation_boundary(assignment=airbox.name, name="Rad1")`.
- **Engineering Impact:** Immediate crash with `AttributeError` and `RuntimeError` during airbox boundary assignment.
- **Recommended Correction:** Replace with `app.assign_radiation_boundary(assignment=airbox.name, name="Rad1")`.

---

### Defect 4: Lumped Port Parameter Name Mismatch — `axisdir` vs `integration_line`
- **Severity:** **CRITICAL**
- **Affected Notebooks:** ALL EIGHT NOTEBOOKS (8 of 8).
- **Cell:** Cell 12.
- **Shared Source Module:** `src/anton/notebook/feed_port_generator.py` (lines 174, 186).
- **Exact Code:**
  ```python
  app.lumped_port(assignment=port_sheet.name, ...)
  app.create_lumped_port_to_sheet(sheet_name=port_sheet.name, integration_line=[int_line_start, int_line_stop], ...)
  ```
- **Root Cause:** In PyAEDT, `create_lumped_port_to_sheet` expects `axisdir=[start, stop]`, not `integration_line`. In `lumped_port()`, `signal=` is expected, not `assignment=`.
- **Engineering Impact:** Immediate crash with `TypeError: got an unexpected keyword argument` in Cell 12.
- **Recommended Correction:** Use `axisdir=[int_line_start, int_line_stop]` in `create_lumped_port_to_sheet`, and use `signal=port_sheet.name` in `lumped_port()`.

---

### Defect 5: Inset-Fed Patch Overlapping Conductors
- **Severity:** **CRITICAL**
- **Affected Notebooks:** `inset_feed_patch_hfss.ipynb` (1 of 8).
- **Cell:** Cell 10.
- **Shared Source Module:** `scripts/create_examples.py:build_inset_feed_patch()`.
- **Exact Code:**
  ```python
  notched_patch = boolean_difference(base_patch, cutters)
  f_id = e.add_rectangle(l_patch, m_cu, width=3.0mm, height=28.0mm, center_y=-16.0mm, name="InsetFeedLine")
  ```
- **Root Cause:** `base_patch` already has copper in the central tongue between $y = -10.0\,\text{mm}$ and $y = -2.0\,\text{mm}$. Adding a separate `InsetFeedLine` from $y = -30.0\,\text{mm}$ to $y = -2.0\,\text{mm}$ creates a $3.0 \times 8.0\,\text{mm}$ overlapping copper solid.
- **Engineering Impact:** Modeler geometry intersection violation in HFSS.
- **Recommended Correction:** Either cut out the central tongue from the patch, or merge the feed line and patch via `boolean_union`.

---

### Defect 6: Feed Line Termination Gap to Substrate Boundary
- **Severity:** **CRITICAL**
- **Affected Notebooks:** `rectangular_patch_hfss.ipynb`, `inset_feed_patch_hfss.ipynb` (2 of 8).
- **Cell:** Cell 10 and Cell 12.
- **Shared Source Module:** `scripts/create_examples.py` (`build_rectangular_patch`, `build_inset_feed_patch`) and `feed_port_generator.py`.
- **Exact Code:**
  - `rectangular_patch`: Feed line runs $y = -27.0\,\text{mm}$ to $-11.5\,\text{mm}$; substrate edge is at $y = -30.0\,\text{mm}$ ($3\,\text{mm}$ gap).
  - `inset_feed_patch`: Feed line runs $y = -30.0\,\text{mm}$ to $-2.0\,\text{mm}$; substrate edge is at $y = -35.0\,\text{mm}$ ($5\,\text{mm}$ gap).
- **Root Cause:** Example creation script defined feed lines shorter than the substrate margin.
- **Engineering Impact:** Lumped port sheet is positioned inside the substrate dielectric volume rather than on the background boundary face.
- **Recommended Correction:** Extend feed lines to reach the substrate boundary ($y = -30.0\,\text{mm}$ for rectangular, $y = -35.0\,\text{mm}$ for inset feed) and align port sheet to the edge.

---

### Defect 7: Solution Type Mismatch — Driven Terminal vs. Modal `S(1,1)`
- **Severity:** **HIGH**
- **Affected Notebooks:** ALL EIGHT NOTEBOOKS (8 of 8).
- **Cell:** Cell 4, Cell 16, Cell 20.
- **Shared Source Module:** `notebook_generator.py` (Cell 4), `solution_setup_generator.py` (Cell 16), `result_extraction_generator.py` (Cell 20).
- **Exact Code:** Cell 4 sets `solution_type="Terminal"`; Cell 20 calls `app.post.get_report_data('S(1,1)', ...)`.
- **Root Cause:** Microstrip patch antennas in HFSS use Modal solutions (`solution_type="Modal"`). In Driven Terminal, `S(1,1)` does not exist.
- **Engineering Impact:** Results extraction returns `None` or fails because trace name `S(1,1)` is invalid in Terminal designs.
- **Recommended Correction:** Set `solution_type="Modal"` (or `"DrivenModal"`) in Cell 4, configure modal driven setup in Cell 16, and extract `S(1,1)` in Cell 20.

---

### Defect 8: Missing Far-Field Infinite Sphere Setup
- **Severity:** **HIGH**
- **Affected Notebooks:** ALL EIGHT NOTEBOOKS (8 of 8).
- **Cell:** Cell 14 / 16 and Cell 22.
- **Shared Source Module:** `boundary_setup_generator.py` / `solution_setup_generator.py` and `result_extraction_generator.py`.
- **Exact Code:** Cell 22 queries `app.post.get_report_data('dB(GainTotal)', ..., context='3D')`, but no Infinite Sphere was ever created.
- **Root Cause:** Far-field radiation setup was omitted from the notebook generator.
- **Engineering Impact:** 3D far-field extraction in Cell 22 always fails with missing context error.
- **Recommended Correction:** Add `app.insert_infinite_sphere(name="3D")` or `app.create_open_region(frequency=...)` in Cell 14 or Cell 16.

---

### Defect 9: Multi-Hole Discard in Boolean Operations
- **Severity:** **HIGH**
- **Affected Notebooks:** Potential defect in all complex slotted geometries.
- **Shared Source Module:** `src/anton/operations/boolean.py` (line 56) and `src/anton/models/geometry_schema.py`.
- **Exact Code:** `hole_coords = list(shape.interiors[0].coords)`
- **Root Cause:** Schema only has `inner_vertices: list[VertexDef]` (single list), and `boolean.py` takes only `interiors[0]`.
- **Engineering Impact:** Any antenna with more than one hole (e.g. dual U-slot, defected ground structure) has all holes after the first silently discarded!
- **Recommended Correction:** Extend schema to support `inner_rings: list[list[VertexDef]]` or loop over all interiors during boolean operations and CAD generation.

---

### Defect 10: Mesh Refinement Filter Excludes Non-Standard Object Names
- **Severity:** **MEDIUM**
- **Affected Notebooks:** `circular_patch_hfss.ipynb` (1 of 8).
- **Cell:** Cell 16.
- **Shared Source Module:** `src/anton/notebook/solution_setup_generator.py` (line 70).
- **Exact Code:** `patch_conductors = [obj.name for obj in app.modeler.object_list if 'patch' in obj.name.lower() or 'radiator' in obj.name.lower()]`
- **Root Cause:** Name filter does not match `CircularDisk`.
- **Engineering Impact:** Length mesh refinement is omitted for circular patch.
- **Recommended Correction:** Query patch layer objects directly by layer type rather than relying on substring matching on object names.

---

### Defect 11: Hardcoded XZ Port Plane Assumption
- **Severity:** **MEDIUM**
- **Affected Notebooks:** Architecture-level defect.
- **Cell:** Cell 12.
- **Shared Source Module:** `src/anton/notebook/feed_port_generator.py` (lines 150, 157).
- **Exact Code:** `orientation='XZ'`, `csPlane='XZ'`.
- **Root Cause:** Hardcoded assumption that feeds are along $Y$.
- **Engineering Impact:** Side-fed ($X$-directed) microstrip antennas generate incorrect port sheets.
- **Recommended Correction:** Determine feed line primary axis dynamically: if width > height, orient in `YZ`; if height > width, orient in `XZ`.

---

## PART E — VERIFICATION LEVEL ASSESSMENT

| Verification Level | Description | Status | Evidence / Notes |
|---|---|---|---|
| **1. Notebook Generation** | Generation of `.ipynb` files via `NotebookGenerator.save()` | **VERIFIED** | All 8 notebooks generate without Python exceptions. |
| **2. Schema Validation** | Jupyter Notebook v4 JSON schema validation | **VERIFIED** | `nbformat.validate()` passes on all 8 files. |
| **3. Python Syntax Validation** | AST parsing of all code cells | **VERIFIED** | `ast.parse()` passes on all code cells in all 8 notebooks. |
| **4. Generator Unit Tests** | Automated tests in `tests/test_notebook_generation.py` | **VERIFIED (LIMITED)** | 76/76 unit tests pass, but rely solely on AST syntax and keyword checks. |
| **5. Mock-Based API Tests** | Tests mocking PyAEDT classes and method signatures | **NOT VERIFIED** | No PyAEDT mock tests currently exist in the test suite. |
| **6. PyAEDT Runtime Execution** | Execution of generated notebook cells in Python with `pyaedt` imported | **NOT VERIFIED** | Runtime execution against live PyAEDT fails due to Defect 1, 2, 3, 4. |
| **7. Actual HFSS Geometry Creation** | Live creation of 3D solids in AEDT Modeler | **NOT VERIFIED** | Requires live AEDT license and desktop session. |
| **8. Port & Boundary Verification** | Verification of Lumped Port and Radiation Boundary in HFSS | **NOT VERIFIED** | Requires live AEDT session. |
| **9. Successful EM Simulation** | Solving Setup1:Sweep1 in HFSS solver engine | **NOT VERIFIED** | ANTON backend does not execute live HFSS simulations. |
| **10. Simulation-Result Extraction** | Extraction of authentic S-parameters from HFSS post-processor | **NOT VERIFIED** | Requires completed HFSS simulation. |

> [!IMPORTANT]
> Levels 5–10 are marked **NOT VERIFIED**. The passing status of Levels 1–4 does NOT establish PyAEDT API compatibility or electromagnetic correctness.

---

## PART F — RECOMMENDED REPAIR ORDER & SOURCE MODIFICATIONS

### Phase 1: Canonical Geometry & Example Script Repairs
1. **`scripts/create_examples.py`:**
   - Fix `build_rectangular_patch()`: Extend `FeedLine` to reach substrate edge at $y = -30.0\,\text{mm}$ ($L_f = 18.5\,\text{mm}, y_{\text{cy}} = -20.75\,\text{mm}$).
   - Fix `build_inset_feed_patch()`:
     - Extend `InsetFeedLine` to reach substrate edge at $y = -35.0\,\text{mm}$.
     - Correct notch boolean operation so the central feed tongue is NOT double-created in both the patch and the feed line.
   - Regenerate all 8 canonical JSON, SVG, PNG, STEP, and STL files via `python scripts/create_examples.py`.

### Phase 2: PyAEDT API & Modeler Code Generator Repairs
2. **`src/anton/notebook/material_code_generator.py`:**
   - Replace non-existent `app.materials.check_if_exists()` with `mat_name in app.materials` or `app.materials.checkifmaterialexists(mat_name)`.
3. **`src/anton/notebook/hfss_code_generator.py`:**
   - Replace non-existent `app.modeler.extrude_sheet()` with `app.modeler.sweep_along_vector(names=solid.name, vector=[0, 0, t])` or `app.modeler.thicken_sheet(object_name=solid.name, thickness=t)`.
   - Fix `create_ellipse` arguments to use `cs_axis='Z', center=[x, y, z]`.
4. **`src/anton/notebook/stackup_code_generator.py`:**
   - Replace `app.modeler.extrude_sheet()` with `app.modeler.sweep_along_vector()`.

### Phase 3: Port, Boundary & Setup Repairs
5. **`src/anton/notebook/feed_port_generator.py`:**
   - Fix parameter name in `create_lumped_port_to_sheet`: change `integration_line=` to `axisdir=`.
   - Fix parameter name in `lumped_port`: change `assignment=` to `signal=`.
   - Dynamically select port plane (`XZ` vs `YZ`) based on feed line aspect ratio.
   - Set integration line direction from Signal to Ground (`axisdir=[signal_pt, ground_pt]`).
6. **`src/anton/notebook/boundary_setup_generator.py`:**
   - Replace non-existent `assign_radiation_boundary_to_objects` / `assign_radiation_boundary_to_faces` with `app.assign_radiation_boundary(assignment=airbox.name, name="Rad1")`.
   - Add Infinite Sphere far-field radiation setup: `app.insert_infinite_sphere(name="3D")`.
7. **`src/anton/notebook/notebook_generator.py` & `solution_setup_generator.py`:**
   - Change `solution_type="Terminal"` to `solution_type="Modal"` (standard for microstrip patch antennas).
   - Configure Driven Modal setup in Cell 16 (`setup_type='HFSSDrivenModal'`).
   - Broaden mesh refinement object query to target all objects on patch/conductor layers.

### Phase 4: Result Extraction & Post-Processing
8. **`src/anton/notebook/result_extraction_generator.py`:**
   - Ensure report query uses modal expression `S(1,1)` under Modal solution type.
   - Far-field pattern extraction queries `app.post.get_report_data('dB(GainTotal)', setup_sweep_name='Setup1 : LastAdaptive', context='3D')` with confirmed Infinite Sphere setup.

### Phase 5: Regeneration, Mock Testing & Final Verification
9. Re-run `python scripts/generate_notebooks.py` to regenerate all eight notebooks.
10. Add mock-based PyAEDT API signature tests to `tests/test_notebook_generation.py` ensuring that every generated method call matches PyAEDT signatures.
11. Execute full test suite `python -m pytest tests/ -v`.

---

## FINAL STAGE 2 ACCEPTANCE CRITERIA

Before Stage 2 can be certified complete and Stage 3 authorized, the following criteria must be satisfied:

1. [ ] **Zero Non-Existent API Calls:** No notebook contains calls to `extrude_sheet`, `check_if_exists`, `assign_radiation_boundary_to_objects`, or `assign_radiation_boundary_to_faces`.
2. [ ] **Correct Parameter Signatures:** All port creation calls use `axisdir` and valid signal/reference arguments.
3. [ ] **Physical Feed Continuity:** Every microstrip feed line extends from the target radiator to the physical outer substrate boundary with zero gap.
4. [ ] **Non-Overlapping Conductors:** Inset-fed patch has zero volume overlap between feed line and patch body.
5. [ ] **Solution Type Consistency:** Application solution type (`Modal`), setup type (`HFSSDrivenModal`), and S-parameter query (`S(1,1)`) are fully synchronized.
6. [ ] **Far-Field Infinite Sphere:** Infinite sphere radiation setup is configured prior to far-field report extraction.
7. [ ] **Synthetic Data Prohibition:** Zero fabricated S11 curves, VSWR, Zin, or radiation patterns.
8. [ ] **Mock-Based Test Suite:** Automated tests verify PyAEDT method signatures and argument names, not merely AST syntax.
9. [ ] **Clean Test Execution:** 100% pass rate across the updated test suite.

---

*End of Stage 2 Complete Notebook Architecture & Engineering Audit Report.*  
*Awaiting user approval before modifying any source code files.*

