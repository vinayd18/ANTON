# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path("src").resolve()))

from anton.ml.registry import ModelRegistry, TargetCapability, ModelCategory

def main():
    reg = ModelRegistry.build_default_catalog()
    print(f"Total models registered: {reg.count()}")
    report = reg.generate_discovery_report()
    print("Categories:", report["categories_breakdown"])
    s11_models = reg.filter_by_capability(TargetCapability.S11_PREDICTION)
    print(f"Models supporting S11: {len(s11_models)}")
    cat_a = reg.filter_by_category(ModelCategory.CATEGORY_A)
    print(f"Category A models: {[m.model_id for m in cat_a]}")
    
    # Export reports
    reg.export_registry_json("src/anton/ml/reports/model_registry_catalog.json")
    reg.export_registry_json("backend/app/ml/reports/model_registry_catalog.json")
    
    with open("src/anton/ml/reports/model_discovery_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=2)
    with open("backend/app/ml/reports/model_discovery_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=2)
        
    comp_report = reg.generate_compatibility_report()
    with open("src/anton/ml/reports/model_compatibility_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(comp_report, f, indent=2)
    with open("backend/app/ml/reports/model_compatibility_report.json", "w", encoding="utf-8") as f:
        import json
        json.dump(comp_report, f, indent=2)

    print("Reports successfully exported!")

if __name__ == "__main__":
    main()

