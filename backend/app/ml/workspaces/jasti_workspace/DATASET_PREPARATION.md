# Jasti RF Surrogate Dataset Preparation

## 1. Tabular Dataset Generation

Prepare simulation results or analytical cavity model calculations in CSV format:

```csv
sample_id,width_mm,length_mm,height_mm,dielectric_constant,resonant_frequency_ghz,bandwidth_mhz
1,38.04,29.44,1.6,4.4,2.45,45.2
2,40.00,31.00,1.57,2.2,2.42,52.8
```

---

## 2. Extraction from ANTON Canonical Rectangular Patch

```python
from anton.models.geometry_schema import GeometryProject

def project_to_jasti_features(project: GeometryProject):
    sub = next(l for l in project.layers if l.layer_type == "dielectric")
    patch = next(o for o in project.objects if o.layer_id == "patch_layer")
    
    w = patch.parameters["width"] * 1000.0
    l = patch.parameters["length"] * 1000.0
    h = sub.thickness * 1000.0
    er = project.metadata.get("dielectric_constant", 4.4)
    
    return [w, l, h, er]
```
