# ANTON: ANSYS HFSS & PyAEDT Compatibility Guide
**Stage 2 Environment & Verification Manual**

---

## 1. Scope & Purpose

This guide outlines the system requirements, PyAEDT integration best practices, and troubleshooting steps for running ANTON-generated `.ipynb` notebooks against ANSYS Electronics Desktop (HFSS).

---

## 2. Software Requirements & Version Matrix

### 2.1 ANSYS Electronics Desktop (AEDT)
ANTON-generated notebooks support the following AEDT versions:
- **AEDT 2025 R1 (2025.1)**: Fully supported.
- **AEDT 2024 R2 (2024.2)**: Fully supported.
- **AEDT 2024 R1 (2024.1)**: Fully supported (Recommended).
- **AEDT 2023 R2 (2023.2)**: Fully supported.
- **AEDT 2023 R1 (2023.1)**: Supported.
- **AEDT 2022 R2 (2022.2)**: Supported (requires PyAEDT $\ge 0.6.0$).

### 2.2 Python Environment
- **Python**: $\ge 3.8$ (Python 3.10 to 3.12 recommended; 3.13 supported).
- **Required Packages**:
  ```bash
  pip install pyaedt numpy matplotlib nbformat
  ```

---

## 3. Connecting to HFSS: Online vs. Offline Execution Modes

ANTON notebooks are designed to be resilient in two operational modes:

### Mode A: Live Verification with HFSS Desktop (Recommended)
1. Launch ANSYS Electronics Desktop on your workstation.
2. Open Jupyter Lab or VS Code Notebook:
   ```bash
   jupyter lab
   ```
3. Open any generated notebook (e.g., `examples/notebooks/rectangular_patch_hfss.ipynb`).
4. Execute Cell 1 and Cell 2.
   - PyAEDT automatically attaches to the running `ansysedt.exe` process via the COM interface (Windows) or gRPC (Linux).
   - The HFSS modeler window will immediately reflect the 3D geometry, stackup, airbox, ports, and boundary conditions as each cell executes.

### Mode B: Offline / Dry-Run Mode (No AEDT Installed or Closed)
If `pyaedt` is not installed or ANSYS Electronics Desktop is not open:
- Cell 2 catches the connection exception gracefully and sets `app = None`.
- Subsequent cells recognize offline mode and skip modeler API calls while remaining syntactically valid.
- The post-processing cells fall back to synthetic demonstration datasets to verify the plotting, metric derivation, and Touchstone export pipeline without errors.

---

## 4. Key HFSS Modeling Conventions

### 4.1 Modeler Units
ANTON enforces **SI Metres ($m$)** as the canonical unit system across all modules.
In Cell 2 of every notebook:
```python
app.modeler.model_units = "meter"
```
All dimensions, coordinate offsets, and box sizes passed to PyAEDT are given in metres (e.g., $0.0016\,m$ for $1.6\,\text{mm}$ substrate).

### 4.2 Solution Type: Terminal vs. Modal
Microstrip patch antennas with lumped ports bridging a ground plane and a microstrip conductor trace are simulated using **Terminal** solution mode by default:
```python
app = Hfss(..., solution_type="Terminal")
```
If you prefer S-parameters derived from modal wave excitation, change `solution_type="Terminal"` to `solution_type="Modal"` in Cell 2.

### 4.3 Quarter-Wave Radiation Airbox
To prevent artificial reflections from the computational domain boundary, ANTON sizes the airbox to extend by at least **$\lambda_0 / 4$** away from the antenna bounding box in all directions:
$$\lambda_0 = \frac{c_0}{f_{\text{center}}}$$
An absorbing radiation boundary condition is assigned to the exterior faces of the airbox.

---

## 5. Troubleshooting & FAQ

### Issue 1: "PyAEDT cannot connect to AEDT desktop session"
- **Cause**: AEDT is not running, or multiple conflicting AEDT versions are registered.
- **Solution**:
  1. Open ANSYS Electronics Desktop manually from the Windows Start menu.
  2. In Cell 2, specify the exact version string, e.g.:
     ```python
     specified_version = "2024.1"
     ```
  3. Ensure AEDT is not blocked by Windows Firewall or administrative permission mismatch.

### Issue 2: "Port integration line error" or "Sheet is not on boundary"
- **Cause**: The lumped port sheet must touch both the conductive patch and the reference ground plane.
- **Solution**: ANTON automatically aligns the port sheet in the $XZ$ plane from $z = z_{\text{sub\_bottom}}$ to $z = z_{\text{sub\_top}}$. If custom feed adjustments were made in ANTON, verify the feed edge in HFSS Modeler and adjust the integration line vertices if needed.

### Issue 3: "License checkout failed for HFSS"
- **Cause**: All available ANSYS HFSS solver licenses are in use or license server is unreachable.
- **Solution**: The notebook does not automatically trigger the solver. You can inspect the geometry and save the project file (`.aedt`). Run the analysis manually (`app.analyze_setup('Setup1')`) only when license capacity is available.

