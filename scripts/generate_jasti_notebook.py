# -*- coding: utf-8 -*-
import nbformat as nbf
from pathlib import Path

def create_jasti_notebook(output_path: str):
    nb = nbf.v4.new_notebook()
    
    cells = [
        nbf.v4.new_markdown_cell(
            "# Jasti RF Surrogate Validation & Evaluation\n\n"
            "Calculates prediction accuracy for resonant frequency and bandwidth estimates."
        ),
        nbf.v4.new_code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n\n"
            "sys.path.insert(0, str(Path('../../..').resolve()))\n"
            "from anton.ml.registry import AntennaBenchmarkEvaluator"
        ),
        nbf.v4.new_markdown_cell(
            "## 1. Metric Calculations\n"
            "Assess R2 score and MAE on held-out test data."
        ),
        nbf.v4.new_code_cell(
            "# Evaluator calculation examples\n"
            "# r2_freq = AntennaBenchmarkEvaluator.calculate_r2(fr_true, fr_pred)\n"
            "# mae_freq = AntennaBenchmarkEvaluator.calculate_mae(fr_true, fr_pred)\n"
            "print('Jasti RF benchmark evaluation template ready.')"
        )
    ]
    
    nb.cells = cells
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Generated {output_path}")

if __name__ == "__main__":
    create_jasti_notebook("src/anton/ml/workspaces/jasti_workspace/evaluation_template.ipynb")
    create_jasti_notebook("backend/app/ml/workspaces/jasti_workspace/evaluation_template.ipynb")

