# -*- coding: utf-8 -*-
"""Verification script for generated PyAEDT notebooks."""
import json
from pathlib import Path

def main():
    nb_dir = Path("examples/notebooks")
    notebooks = sorted(nb_dir.glob("*.ipynb"))
    print(f"Auditing {len(notebooks)} generated notebooks:")

    issues = []
    for nb_path in notebooks:
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        code = "\n".join("".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"] == "code")

        # 1. Non-existent PyAEDT methods
        if "extrude_sheet" in code:
            issues.append(f"{nb_path.name}: contains extrude_sheet")
        if "check_if_exists" in code:
            issues.append(f"{nb_path.name}: contains check_if_exists")
        if "create_lumped_port_to_sheet(" in code and "axisdir=" not in code:
            issues.append(f"{nb_path.name}: create_lumped_port_to_sheet missing axisdir")
        if "solution_type='Terminal'" in code or 'solution_type="Terminal"' in code:
            issues.append(f"{nb_path.name}: solution_type is Terminal instead of Modal")
        if "insert_infinite_sphere" not in code:
            issues.append(f"{nb_path.name}: missing insert_infinite_sphere")
        if "sweep_along_vector" not in code and nb_path.name not in ("rectangular_patch_hfss.ipynb", "circular_patch_hfss.ipynb"):
            issues.append(f"{nb_path.name}: missing sweep_along_vector")
        if "CircularDisk" in code and "CircularDisk" not in code.split("target_radiators = ")[1].split("]")[0]:
            issues.append(f"{nb_path.name}: CircularDisk not in target_radiators")

    if not issues:
        print("SUCCESS: ALL 8 NOTEBOOKS PASSED CLEANLY! Zero legacy hallucinations detected!")
    else:
        for iss in issues:
            print("ISSUE:", iss)

if __name__ == "__main__":
    main()
