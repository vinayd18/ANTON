# -*- coding: utf-8 -*-
"""Notebook generation and validation package for ANTON Stage 2.

Enables automated generation of standalone, executable Jupyter Notebooks (.ipynb)
for reproducing ANTON antenna designs in ANSYS HFSS via PyAEDT, operating
independently of live simulation environments.
"""

from anton.notebook.boundary_setup_generator import BoundarySetupGenerator
from anton.notebook.feed_port_generator import FeedPortGenerator
from anton.notebook.hfss_code_generator import HFSSCodeGenerator
from anton.notebook.material_code_generator import MaterialCodeGenerator
from anton.notebook.notebook_generator import NotebookGenerator
from anton.notebook.notebook_validator import NotebookValidationResult, NotebookValidator
from anton.notebook.result_extraction_generator import ResultExtractionGenerator
from anton.notebook.solution_setup_generator import SolutionSetupGenerator
from anton.notebook.stackup_code_generator import StackupCodeGenerator

__all__ = [
    "NotebookGenerator",
    "NotebookValidator",
    "NotebookValidationResult",
    "MaterialCodeGenerator",
    "StackupCodeGenerator",
    "HFSSCodeGenerator",
    "FeedPortGenerator",
    "BoundarySetupGenerator",
    "SolutionSetupGenerator",
    "ResultExtractionGenerator",
]

