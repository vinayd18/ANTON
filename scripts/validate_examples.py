# -*- coding: utf-8 -*-
"""Validation script to audit and report on all generated example antennas in ANTON."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from anton.io.json_importer import import_project_json
from anton.validation.validator import GeometryValidator


def main() -> None:
    examples_dir = PROJECT_ROOT / "examples"
    if not examples_dir.exists():
        print(f"Examples directory '{examples_dir}' does not exist. Run scripts/create_examples.py first.")
        sys.exit(1)

    json_files = sorted(examples_dir.glob("*.json"))
    if not json_files:
        print(f"No JSON examples found in '{examples_dir}'. Run scripts/create_examples.py first.")
        sys.exit(1)

    validator = GeometryValidator()

    print("=" * 75)
    print("ANTON STAGE 1 — EXAMPLE ANTENNA VALIDATION AUDIT")
    print("=" * 75)

    all_passed = True

    for jf in json_files:
        print(f"\nAuditing: {jf.name}")
        try:
            # Test JSON import and schema validation
            project = import_project_json(jf)
            print(f"  Project: '{project.project_name}' (ID: {project.geometry_id[:8]}...)")
            print(f"  Objects: {len(project.objects)} | Layers: {len(project.layers)} | Materials: {len(project.materials)}")

            # Test geometry validation
            report = validator.validate(project, require_full_stack=True)
            print(f"  Status : {report.summary()}")

            if not report.is_valid:
                all_passed = False
                for issue in report.issues:
                    print(f"    - [ERROR] {issue.code}: {issue.description}")
            else:
                for issue in report.issues:
                    print(f"    - [{issue.severity.upper()}] {issue.code}: {issue.description}")

        except Exception as e:
            all_passed = False
            print(f"  [CRITICAL ERROR] Failed to import/validate '{jf.name}': {e}")

    print("\n" + "=" * 75)
    if all_passed:
        print("AUDIT RESULT: ALL EXAMPLES PASSED GEOMETRIC AND SCHEMA VALIDATION!")
    else:
        print("AUDIT RESULT: ONE OR MORE EXAMPLES FAILED VALIDATION.")
        sys.exit(1)
    print("=" * 75)


if __name__ == "__main__":
    main()
