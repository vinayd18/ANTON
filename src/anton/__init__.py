# -*- coding: utf-8 -*-
"""ANTON — Universal microstrip patch antenna geometry engine (Stage 1)."""

from anton.core.geometry_engine import AntonEngine
from anton.core.units import Units
from anton.models.geometry_schema import (
    AntennaConfig,
    GeometryObject,
    GeometryProject,
    LayerDef,
    MaterialRef,
    ParameterDef,
    VertexDef,
)
from anton.materials.material_database import MaterialDatabase
from anton.validation.validator import GeometryValidator
from anton.validation.validation_report import ValidationReport, ValidationIssue
from anton.visualization.geometry_renderer import GeometryRenderer
from anton.cad.solid_generator import SolidGenerator
from anton.cad.cad_exporter import CADExporter
from anton.io.file_exporter import FileExporter

__version__ = "0.1.0"

__all__ = [
    "AntonEngine",
    "Units",
    "GeometryProject",
    "GeometryObject",
    "LayerDef",
    "MaterialRef",
    "ParameterDef",
    "VertexDef",
    "AntennaConfig",
    "MaterialDatabase",
    "GeometryValidator",
    "ValidationReport",
    "ValidationIssue",
    "GeometryRenderer",
    "SolidGenerator",
    "CADExporter",
    "FileExporter",
]
