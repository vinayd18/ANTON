# ANTON — Universal Microstrip Patch Antenna Geometry Engine

ANTON is a Python library for defining, composing, and exporting 2.5-D
microstrip patch antenna geometries.  It provides a fully-typed, Pydantic-v2
schema for every primitive (rectangles, circles, ellipses, polygons, arcs,
custom contours, boolean results) together with layer, material, and feed
definitions, all managed through a single `AntonEngine` entry-point.

## Features

* Parametric geometry objects with dependency tracking
* Layer-based stack-up (patch, substrate, ground, feed, conductor, custom)
* Material database (dielectric / conductor) with arbitrary properties
* Full JSON serialisation / deserialisation of projects
* CAD-ready coordinate system (metres, Cartesian)
* UUID-based object identity throughout

## Installation

```bash
# editable install (recommended during development)
pip install -e .
```

## Quick Start

```python
from anton import AntonEngine

engine = AntonEngine("my_antenna")

# Add a material
cu = engine.add_material(name="Copper", category="conductor",
                         properties={"conductivity": 5.8e7})

# Add a layer
patch = engine.add_layer(name="Patch", layer_type="patch",
                         material_id=cu, z_position=0.0,
                         thickness=35e-6)

# Add a rectangular patch
rect = engine.add_rectangle(name="Patch Element",
                            layer_id=patch, material_id=cu,
                            width=0.050, height=0.040)

# Export
engine.export_json("my_antenna.json")
```

## Running Tests

```bash
pytest
```

## License

MIT
