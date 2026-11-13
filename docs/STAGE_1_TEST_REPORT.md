# ANTON — Stage 1 Automated Test Report

---

## 1. Test Execution Summary

- **Framework**: `pytest 9.1.1`
- **Python Version**: `3.13.2 (64-bit on Windows 11)`
- **Total Tests Collected**: **46**
- **Total Tests Passed**: **46 (100%)**
- **Total Tests Failed**: **0 (0%)**
- **Total Tests Skipped**: **0**
- **Total Execution Time**: **2.69 seconds**

---

## 2. Test Suite Breakdown

### 2.1. `tests/test_primitives.py` (10 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_rectangle_to_shapely` | Verifies area and centroid placement for rectangular primitives | **PASSED** |
| `test_rotated_rectangle_preserves_area` | Verifies that arbitrary 45-degree rotation preserves mathematical area | **PASSED** |
| `test_square_to_shapely` | Verifies square geometry conversion | **PASSED** |
| `test_circle_to_shapely` | Verifies circle polygonization area matches $\pi r^2$ within 0.1% | **PASSED** |
| `test_ellipse_to_shapely` | Verifies affine-scaled ellipse area matches $\pi a b$ within 0.1% | **PASSED** |
| `test_triangle_to_shapely` | Verifies 3-vertex triangle area and topology | **PASSED** |
| `test_polygon_to_shapely` | Verifies multi-vertex convex/concave polygon conversion | **PASSED** |
| `test_line_to_shapely` | Verifies 1D LineString construction and metric length | **PASSED** |
| `test_arc_to_shapely` | Verifies discretized arc length matches analytical formula $\pi r$ | **PASSED** |
| `test_custom_contour_with_hole` | Verifies custom contour with interior cutout retains hole topology | **PASSED** |

### 2.2. `tests/test_boolean_operations.py` (4 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_boolean_union` | Merges two overlapping squares and verifies resulting area | **PASSED** |
| `test_boolean_difference_creates_slot` | Subtracts a slot from a patch and verifies hole generation | **PASSED** |
| `test_boolean_difference_complete_subtraction_raises` | Verifies that subtracting a larger cutter raises a descriptive `ValueError` | **PASSED** |
| `test_boolean_intersection` | Computes common overlap area between two overlapping rectangular patches | **PASSED** |

### 2.3. `tests/test_transformations.py` (7 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_translate_object` | Translates object by $(\Delta x, \Delta y)$ and checks centroid and new UUID | **PASSED** |
| `test_rotate_object` | Rotates object by 90 degrees and checks area preservation | **PASSED** |
| `test_scale_object` | Scales along $X$ and $Y$ by factors and asserts area scaling | **PASSED** |
| `test_mirror_object` | Reflects object across $X$-axis and verifies coordinate flip | **PASSED** |
| `test_duplicate_object` | Creates deep copy with fresh UUID and cloned geometry | **PASSED** |
| `test_extract_boundary` | Extracts 1D LineString perimeter boundary from 2D patch | **PASSED** |
| `test_offset_object` | Inflates circle by $2\,\text{mm}$ and asserts expanded radius/area | **PASSED** |

### 2.4. `tests/test_schema.py` (7 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_geometry_project_creation` | Creates default project and verifies default parameters and UUID | **PASSED** |
| `test_invalid_units_rejected` | Negative test: verifies that non-SI units (e.g. "mm") are rejected | **PASSED** |
| `test_parameter_def_validation` | Verifies parameter model validation and fields | **PASSED** |
| `test_material_ref_creation` | Verifies dielectric/conductor material models | **PASSED** |
| `test_layer_def_creation` | Verifies layer definition model and stack positioning | **PASSED** |
| `test_geometry_object_unknown_type_rejected` | Negative test: asserts invalid primitive type strings raise `ValidationError` | **PASSED** |
| `test_project_roundtrip_dict` | Verifies dictionary serialization and reconstruction | **PASSED** |

### 2.5. `tests/test_validation.py` (7 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_valid_project_passes` | Validates clean microstrip antenna with zero issues | **PASSED** |
| `test_negative_dimension_detected` | Flags non-positive dimensions with `ERR_NONPOSITIVE_WIDTH` | **PASSED** |
| `test_zero_radius_detected` | Flags zero circle radius with `ERR_NONPOSITIVE_RADIUS` | **PASSED** |
| `test_missing_layer_reference_detected` | Flags object pointing to non-existent layer with `ERR_MISSING_LAYER_REF` | **PASSED** |
| `test_missing_material_reference_detected` | Flags object pointing to missing material with `ERR_MISSING_MATERIAL_REF` | **PASSED** |
| `test_feed_connectivity_warning` | Warns when feed does not physically touch radiating patch | **PASSED** |
| `test_require_full_stack_warning` | Warns when standard microstrip 3-layer sandwich is incomplete | **PASSED** |

### 2.6. `tests/test_materials.py` (5 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_load_default_materials_database` | Loads bundled JSON database and asserts $\ge 8$ records | **PASSED** |
| `test_get_material_by_name` | Looks up "Copper" and verifies conductivity $5.8 \times 10^7\,\text{S/m}$ | **PASSED** |
| `test_get_nonexistent_returns_none` | Negative test: checks non-existent material lookup | **PASSED** |
| `test_create_custom_dielectric` | Creates and registers user-defined dielectric | **PASSED** |
| `test_create_custom_conductor` | Creates and registers user-defined conductor | **PASSED** |

### 2.7. `tests/test_cad_generation.py` (2 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_cad_solid_and_assembly_generation` | Generates 3D multi-layer CadQuery assembly and exports STEP and STL | **PASSED** |
| `test_circle_cad_solid_generation` | Generates 3D extruded solid for circular disk | **PASSED** |

### 2.8. `tests/test_serialization.py` (4 Tests)
| Test Case | Description | Result |
|---|---|---|
| `test_json_roundtrip_preserves_geometry` | Serializes project to disk, loads back, and asserts identical dimensions | **PASSED** |
| `test_invalid_json_raises` | Negative test: verifies that malformed JSON raises `ValueError` | **PASSED** |
| `test_svg_export` | Verifies non-empty SVG vector file generation | **PASSED** |
| `test_png_export` | Verifies non-empty high-resolution PNG rendering | **PASSED** |

---

## 3. Test Coverage & Quality Assessment

1. **Deterministic Execution**: All tests use fixed random seeds / deterministic inputs.
2. **Negative Testing**: Every subsystem includes explicit failure cases ensuring that invalid inputs, degenerate polygons, or illegal units are safely rejected.
3. **End-to-End Pipeline**: From parametric primitive creation $\to$ boolean operations $\to$ validation $\to$ 2D SVG/PNG $\to$ 3D OpenCASCADE STEP/STL export.

