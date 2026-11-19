# Youxch Patch MLP Dataset Preparation Guide

## 1. Preparing Simulation Data for Fine-Tuning

Export electromagnetic simulations from ANSYS HFSS or CST Studio into a NumPy array or CSV file with the following column structure:

```csv
sample_id,h_mm,scale_x,scale_y,offset_y_mm,scale_slot,uw_3_mm,s11_2.000,s11_2.010,...,s11_3.000,gain_dbi
patch_0001,1.6,1.05,0.98,2.5,0.0,0.0,-3.4,-4.1,...,-2.8,6.85
patch_0002,1.6,1.00,1.00,0.0,0.2,1.5,-2.1,-2.9,...,-1.8,7.12
```

---

## 2. Parameter Mapping from ANTON Canonical Schemas

To map an ANTON canonical `rectangular_patch` or `inset_fed_patch` into the 6 features:

```python
from anton.models.geometry_schema import GeometryProject

def anton_to_youxch_features(project: GeometryProject, ref_w_mm=38.04, ref_l_mm=29.44) -> list:
    sub = next(l for l in project.layers if l.layer_type == "dielectric")
    h_mm = sub.thickness * 1000.0
    
    patch = next(o for o in project.objects if o.layer_id == "patch_layer")
    w_mm = patch.parameters["width"] * 1000.0
    l_mm = patch.parameters["length"] * 1000.0
    
    scale_x = w_mm / ref_w_mm
    scale_y = l_mm / ref_l_mm
    
    feed = project.metadata.get("feed", {})
    offset_y = feed.get("y_mm", 0.0)
    
    scale_slot = 0.0  # solid patch
    uw_3 = 0.0
    
    return [h_mm, scale_x, scale_y, offset_y, scale_slot, uw_3]
```

