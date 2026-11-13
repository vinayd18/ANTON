# ANTON Geometry Validation Rules & Policy

---

## 1. Validation Philosophy

A microstrip antenna CAD model must be both **geometrically sound** and **physically plausible** for full-wave electromagnetic simulation. However, antenna engineering often employs unorthodox structures (such as parasitic ungrounded patches, isolated reactive elements, and intentional conductive coupling). 

Therefore, the **ANTON Validation Engine** enforces a strict two-tier classification:

1. **Fatal Errors (`ERROR`)**: Violations of mathematical, geometric, or referential validity that make 2D rendering or 3D meshing impossible. A project with even one `ERROR` is marked `is_valid = False` and cannot proceed to CAD export or simulation.
2. **Structural Warnings (`WARNING`)**: Geometrical states that are valid 2D shapes but often indicate antenna design oversights (e.g., disconnected feeds, unspaced overlapping conductors, or incomplete substrate stacks). These inform the engineer without blocking execution.

The engine **never silently modifies or alters invalid geometry**.

---

## 2. Validation Check Reference

| Code | Severity | Description | Trigger Condition | Recommended Corrective Action |
|---|---|---|---|---|
| `ERR_NONPOSITIVE_WIDTH` | **ERROR** | Object width is $\le 0$ | $w \le 0$ on rectangle/square | Set $w > 0$ in metres |
| `ERR_NONPOSITIVE_HEIGHT` | **ERROR** | Object height is $\le 0$ | $h \le 0$ on rectangle/square | Set $h > 0$ in metres |
| `ERR_NONPOSITIVE_RADIUS` | **ERROR** | Circle or arc radius is $\le 0$ | $r \le 0$ on circle/arc | Set $r > 0$ in metres |
| `ERR_NONPOSITIVE_SEMI_AXES` | **ERROR** | Ellipse semi-axis is $\le 0$ | $a \le 0$ or $b \le 0$ | Set both semi-axes $> 0$ |
| `ERR_ZERO_AREA` | **ERROR** | 2D primitive evaluates to zero area | Polygonal area $< 10^{-18}\,\text{m}^2$ | Check coordinate points and scale |
| `ERR_SHAPE_CONVERSION` | **ERROR** | Cannot construct valid 2D shape | Malformed vertices or unclosed contour | Provide $\ge 3$ distinct vertices |
| `ERR_SELF_INTERSECTING_GEOMETRY` | **ERROR** | Polygon boundary crosses itself | Self-intersecting loop detected by GEOS | Reorder vertices to form simple polygon |
| `ERR_MISSING_LAYER_REF` | **ERROR** | Object references non-existent layer ID | `obj.layer_id not in project.layers` | Assign to valid registered layer |
| `ERR_MISSING_MATERIAL_REF` | **ERROR** | Object references non-existent material ID | `obj.material_id not in project.materials` | Assign to valid material in database |
| `WARN_FEED_DISCONNECTED` | **WARNING** | Feed does not touch radiator | Feed polygon does not intersect or touch patch polygon within $1\,\mu\text{m}$ | Adjust feed line length or inset depth |
| `WARN_OVERLAPPING_CONDUCTORS` | **WARNING** | Two conductive patches overlap | Unintentional copper overlap $> 10^{-12}\,\text{m}^2$ on same layer | Merge with `boolean_union` or introduce spacing |
| `WARN_INCOMPLETE_STACK` | **WARNING** | Missing ground, substrate, or patch layer | Requested full-stack check without standard 3-layer sandwich | Add missing layer before full EM simulation |

---

## 3. Running Validation

```python
from anton.validation import GeometryValidator

validator = GeometryValidator()

# Run all checks, optionally checking feeds and verifying full stack
report = validator.validate(project, feeds=feeds_list, require_full_stack=True)

if not report.is_valid:
    print(f"Validation FAILED with {report.error_count} errors.")
    for issue in report.issues:
        if issue.severity == "error":
            print(f"  [{issue.code}] {issue.description} -> Suggestion: {issue.suggestion}")
else:
    print(f"Validation PASSED ({report.warning_count} warnings). Ready for CAD / EM simulation.")
```

