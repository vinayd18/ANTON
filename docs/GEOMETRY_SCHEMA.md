# ANTON Geometry Schema Specification
## Canonical Representation & Pydantic Data Model (v1.0.0)

---

## 1. Overview

The canonical geometry schema of **ANTON** is the single source of truth for all planar antenna models. It encapsulates every physical and topological attribute of the design, ensuring that 2D rendering, 3D CAD modeling, electromagnetic simulation (e.g. PyAEDT / HFSS), and future AI/ML surrogate modeling consume identical, strictly-typed data.

The schema is implemented in Python using **Pydantic v2** (`anton.models.geometry_schema`).

---

## 2. Global Design Rules

1. **Strict SI Units**: All spatial coordinates, lengths, radii, and thicknesses are expressed in **metres (`m`)**. The schema validator explicitly rejects any other unit for dimensions.
2. **Deterministic Identifiers**: Every entity (project, layer, material, object, connection) carries a unique UUID string (`uuid4`).
3. **Cartesian Coordinate System**: The $XY$-plane represents the planar layout of conductors and substrates. The $+Z$-axis points upward along the substrate stack.
4. **Immutability & Integrity**: Objects are never silently modified. All mutations produce new verified objects or update tracked references.

---

## 3. Schema Data Structure Hierarchy

```
GeometryProject
├── project_name: str
├── geometry_id: str (UUID)
├── units: "m" (enforced)
├── coordinate_system: "Cartesian"
├── antenna: AntennaConfig
│   ├── name: str
│   ├── configuration: str ("custom", "patch", "array", ...)
│   └── description: Optional[str]
├── parameters: Dict[str, ParameterDef]
│   └── [param_name]:
│       ├── name: str
│       ├── value: float
│       ├── unit: str
│       ├── min_value, max_value: Optional[float]
│       └── dependencies: List[str]
├── materials: Dict[str, MaterialRef]
│   └── [mat_id]:
│       ├── id: str (UUID)
│       ├── name: str
│       ├── category: "dielectric" | "conductor"
│       ├── properties: Dict[str, float | str]
│       │   ├── relative_permittivity: float
│       │   ├── loss_tangent: float
│       │   └── conductivity: float
│       ├── source: Optional[str]
│       └── valid_range: Optional[str]
├── layers: Dict[str, LayerDef]
│   └── [layer_id]:
│       ├── id: str (UUID)
│       ├── name: str
│       ├── layer_type: "patch" | "substrate" | "ground" | "feed" | "conductor" | "custom"
│       ├── z_position: float (metres)
│       ├── thickness: float (metres)
│       ├── material_id: str (UUID ref)
│       └── object_ids: List[str] (UUID refs)
├── objects: Dict[str, GeometryObject]
│   └── [obj_id]:
│       ├── id: str (UUID)
│       ├── name: Optional[str]
│       ├── object_type: str ("rectangle"|"circle"|"ellipse"|"triangle"|"polygon"|"line"|"arc"|"custom_contour"|"boolean_result")
│       ├── layer_id: str (UUID ref)
│       ├── material_id: str (UUID ref)
│       ├── center_x: float
│       ├── center_y: float
│       ├── rotation_deg: float
│       ├── width, height: Optional[float]
│       ├── radius, semi_major, semi_minor: Optional[float]
│       ├── vertices: List[VertexDef]
│       ├── inner_vertices: List[VertexDef] (cutouts / slots)
│       ├── parameters: Dict[str, ParameterDef]
│       └── metadata: Dict[str, Union[str, float]]
├── connections: List[ConnectionDef]
│   └── [connection]:
│       ├── id: str (UUID)
│       ├── source_object_id: str (UUID ref)
│       ├── target_object_id: str (UUID ref)
│       ├── connection_type: str ("direct_edge_feed", "inset_feed_connection", ...)
│       └── metadata: Dict[str, Union[str, float]]
└── metadata: ProjectMeta
    ├── schema_version: "1.0.0"
    ├── created_at: ISO 8601 UTC timestamp
    ├── modified_at: Optional[ISO 8601 UTC timestamp]
    ├── author: Optional[str]
    └── description: Optional[str]
```

---

## 4. Annotated Example JSON

Below is a representative excerpt from `examples/rectangular_patch.json`:

```json
{
  "project_name": "Rectangular Patch Antenna",
  "geometry_id": "149ca6e4-6cb0-4f05-8859-994df7a1cf05",
  "units": "m",
  "coordinate_system": "Cartesian",
  "antenna": {
    "name": "Custom Antenna",
    "configuration": "custom",
    "description": null
  },
  "parameters": {
    "W_p": {
      "name": "W_p",
      "value": 0.038,
      "unit": "m",
      "description": "Patch width",
      "min_value": null,
      "max_value": null,
      "dependencies": []
    },
    "L_p": {
      "name": "L_p",
      "value": 0.029,
      "unit": "m",
      "description": "Patch length",
      "min_value": null,
      "max_value": null,
      "dependencies": []
    }
  },
  "materials": {
    "5d7d3c01-70e0-47b7-9ee1-f926ce405c1d": {
      "id": "5d7d3c01-70e0-47b7-9ee1-f926ce405c1d",
      "name": "FR4",
      "category": "dielectric",
      "properties": {
        "relative_permittivity": 4.4,
        "loss_tangent": 0.02
      },
      "source": "Standard FR4 laminate",
      "valid_range": null
    }
  },
  "layers": {
    "1f4d9ca2-4806-444a-9ef8-e160e1d1f043": {
      "id": "1f4d9ca2-4806-444a-9ef8-e160e1d1f043",
      "name": "Patch",
      "layer_type": "patch",
      "z_position": 0.0016,
      "thickness": 0.000035,
      "material_id": "8939c32e-57ae-488f-a78b-d72b226e6d1b",
      "object_ids": [
        "bc7ba977-80fe-4dc3-9b93-875c7423ee25"
      ]
    }
  },
  "objects": {
    "bc7ba977-80fe-4dc3-9b93-875c7423ee25": {
      "id": "bc7ba977-80fe-4dc3-9b93-875c7423ee25",
      "name": "Radiator",
      "object_type": "rectangle",
      "layer_id": "1f4d9ca2-4806-444a-9ef8-e160e1d1f043",
      "material_id": "8939c32e-57ae-488f-a78b-d72b226e6d1b",
      "center_x": 0.0,
      "center_y": 0.003,
      "rotation_deg": 0.0,
      "width": 0.038,
      "height": 0.029,
      "radius": null,
      "semi_major": null,
      "semi_minor": null,
      "vertices": [],
      "inner_vertices": [],
      "parameters": {},
      "metadata": {}
    }
  },
  "connections": [
    {
      "id": "67f6bbcf-3c5e-4c81-8bfa-1200e6255745",
      "source_object_id": "b1ca2903-518f-4aa7-92be-3f191295fcfa",
      "target_object_id": "bc7ba977-80fe-4dc3-9b93-875c7423ee25",
      "connection_type": "direct_edge_feed",
      "metadata": {}
    }
  ],
  "metadata": {
    "schema_version": "1.0.0",
    "created_at": "2026-11-13T08:03:00.000000Z",
    "modified_at": null,
    "author": null,
    "description": null
  }
}
```

---

## 5. Schema Versioning Policy

- Schema versions follow strict SemVer: `MAJOR.MINOR.PATCH`.
- `schema_version = "1.0.0"` is the initial release.
- Any future field additions with default values will increment `MINOR` (backwards-compatible).
- Any breaking rename or structure restructuring will increment `MAJOR`, accompanied by an automated migration hook in `anton.io.json_importer`.

