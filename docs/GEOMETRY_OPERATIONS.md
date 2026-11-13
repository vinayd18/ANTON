# ANTON Geometry Operations & Constructive Solid Geometry Guide

---

## 1. Overview

**ANTON** provides a complete suite of planar 2D computational geometry and constructive solid geometry (CSG) operations implemented in `anton.operations`. All operations:
1. Accept canonical `GeometryObject` instances.
2. Evaluate topological operations using high-precision GEOS/Shapely computational kernels.
3. Construct and return brand-new `GeometryObject` instances with fresh unique UUIDs.
4. Guarantee that the original input objects remain unmodified (pure functional semantics).

---

## 2. Boolean Operations (`anton.operations.boolean`)

### 2.1. `boolean_union`
Merges two or more planar objects into a single contiguous polygon or compound shape.

```python
from anton.operations import boolean_union

# Combine two radiating sections or multi-element patches
combined_patch = boolean_union(
    [patch_element_1, patch_element_2],
    name="MergedRadiator",
    layer_id=target_layer_id,
    material_id=target_material_id,
)
```

### 2.2. `boolean_difference`
Subtracts one or more "cutter" objects from a base object. This is the primary mechanism for:
- Cutting rectangular, cross, or circular slots.
- Creating dual-band U-slots and E-slots.
- Creating inset-feed notches.
- Fabricating annular circular or polygonal rings.
- Engineering defected ground structures (DGS).

```python
from anton.operations import boolean_difference

# Cut a circular slot into a rectangular microstrip patch
base_patch = engine.get_object(patch_id)
circular_slot = engine.get_object(slot_id)

slotted_patch = boolean_difference(
    base=base_patch,
    cutters=[circular_slot],
    name="SlottedPatchRadiator",
)
```

### 2.3. `boolean_intersection`
Computes the shared common area between multiple overlapping objects.

```python
from anton.operations import boolean_intersection

shared_overlap = boolean_intersection([patch_a, patch_b])
```

---

## 3. Geometric Transformations (`anton.operations.transformations`)

### 3.1. Translation
Shifts an object along the $X$ and $Y$ axes by $(dx, dy)$ in metres.

```python
from anton.operations import translate_object

shifted_feed = translate_object(feed_line, dx=0.005, dy=-0.012)
```

### 3.2. Rotation
Rotates an object by $\theta$ degrees around a specified origin point $(x_0, y_0)$.

```python
from anton.operations import rotate_object

rotated_patch = rotate_object(patch, angle_deg=45.0, origin=(0.0, 0.0))
```

### 3.3. Scaling
Scales an object independently along $X$ and $Y$ dimensions:

```python
from anton.operations import scale_object

enlarged_patch = scale_object(patch, factor_x=1.2, factor_y=1.2)
```

### 3.4. Mirroring
Reflects an object across a vertical ($x = \text{offset}$) or horizontal ($y = \text{offset}$) axis. Essential for creating symmetric antenna arrays and balanced corporate feed networks:

```python
from anton.operations import mirror_object

mirrored_arm = mirror_object(left_arm, axis="x", offset=0.0)
```

### 3.5. Boundary Extraction
Extracts the 1D perimeter contour from any closed 2D polygon as a `line` object:

```python
from anton.operations import extract_boundary

perimeter = extract_boundary(patch, name="PatchEdgePerimeter")
```

---

## 4. Offsets & Buffering (`anton.operations.offsets`)

### `offset_object`
Expands (inflates) or contracts (deflates) a geometry by a signed distance in metres:
- **Positive distance ($d > 0$)**: Dilates the shape outward. Useful for ground clearance rings and parasitic coupling gaps.
- **Negative distance ($d < 0$)**: Erodes the shape inward. Useful for edge-inset margins.

```python
from anton.operations import offset_object

clearance_ring = offset_object(radiator, distance=0.002)  # 2 mm outer clearance
```

