from pathlib import Path
import json
from anton.ml.registry import ModelRegistry

reg = ModelRegistry.build_default_catalog()

out_dir = Path("src/anton/ml/reports")
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Export registry catalog JSON
reg.export_registry_json(out_dir / "model_registry_catalog.json")

# 2. Export discovery report JSON
discovery = reg.generate_discovery_report()
with open(out_dir / "model_discovery_report.json", "w", encoding="utf-8") as f:
    json.dump(discovery, f, indent=2)

# 3. Export compatibility report JSON
compatibility = reg.generate_compatibility_report()
with open(out_dir / "model_compatibility_report.json", "w", encoding="utf-8") as f:
    json.dump(compatibility, f, indent=2)

print("Exported updated reports to src/anton/ml/reports/")

