# Antenna-Net Dataset Preparation Guide

## 1. Ground Truth Simulation Data Format

To fine-tune Antenna-Net on your own simulation data (e.g. from ANSYS HFSS or CST Studio), prepare a CSV or HDF5 file containing:

```csv
sample_id,patch_width_mm,patch_length_mm,substrate_height_mm,permittivity,s11_1.00GHz,s11_1.05GHz,...,s11_6.00GHz
sample_0001,38.04,29.44,1.6,4.4,-1.2,-1.5,...,-2.1
sample_0002,40.00,32.00,0.8,2.2,-0.8,-1.1,...,-1.9
```

### Constraints:
1. All 101 frequency points must strictly match the 1.0 GHz to 6.0 GHz grid (step = 50 MHz).
2. S-parameters must be in dB ($20 \log_{10} |S_{11}|$).
3. All samples must include authentic simulation provenance (HFSS version, mesh convergence criteria, solution setup). Never mix synthetic or unverified estimates into the fine-tuning dataset.

---

## 2. Converting ANTON Canonical Designs to Training Vectors

Use the provided helper script `load_checkpoint_example.py` or export parameters directly from ANTON's canonical `GeometryProject`:

```python
from anton.models.geometry_schema import GeometryProject

def extract_antennanet_features(project: GeometryProject) -> dict:
    # 1. Extract substrate layer
    sub_layer = next(l for l in project.layers if l.layer_type == "dielectric")
    substrate_h = sub_layer.thickness * 1000.0  # meters to mm
    
    # 2. Extract material permittivity
    er = project.metadata.get("dielectric_constant", 4.4)
    
    # 3. Extract patch dimensions
    patch_obj = next(o for o in project.objects if o.layer_id == "patch_layer")
    w = patch_obj.parameters["width"] * 1000.0
    l = patch_obj.parameters["length"] * 1000.0
    
    return {"W": w, "L": l, "h": substrate_h, "er": er}
```

