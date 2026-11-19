# -*- coding: utf-8 -*-
import nbformat as nbf
from pathlib import Path

def create_youxch_notebook(output_path: str):
    nb = nbf.v4.new_notebook()
    
    cells = [
        nbf.v4.new_markdown_cell(
            "# Youxch Patch MLP Validation & Benchmark Evaluation\n\n"
            "Calculates standardized electromagnetic prediction metrics for the Youxch Keras MLP model.\n\n"
            "### Target Metrics\n"
            "- **S11 MAE & RMSE** (dB, 2.0 to 3.0 GHz)\n"
            "- **Resonant Frequency Deviation** ($|\\Delta f_r|$ in MHz)\n"
            "- **Gain Prediction Error** ($|\\Delta G|$ in dBi)\n"
            "- **Inference Latency** (ms)"
        ),
        nbf.v4.new_code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n\n"
            "# Add ANTON src to path\n"
            "sys.path.insert(0, str(Path('../../..').resolve()))\n"
            "from anton.ml.registry import AntennaBenchmarkEvaluator"
        ),
        nbf.v4.new_markdown_cell(
            "## 1. Load Ground Truth Data (2.0 to 3.0 GHz)\n"
            "Load authentic full-wave simulation data."
        ),
        nbf.v4.new_code_cell(
            "freqs_ghz = np.linspace(2.0, 3.0, 101)\n"
            "print(f'Frequency range: {freqs_ghz[0]} to {freqs_ghz[-1]} GHz ({len(freqs_ghz)} points)')"
        ),
        nbf.v4.new_markdown_cell(
            "## 2. Model Evaluation & Gain Assessment"
        ),
        nbf.v4.new_code_cell(
            "# Evaluation metrics cell\n"
            "# s11_mae = AntennaBenchmarkEvaluator.calculate_mae(s11_true, s11_pred)\n"
            "# gain_error = np.mean(np.abs(gain_true - gain_pred))\n"
            "print('Ready to evaluate S11 and broadside gain against ground truth.')"
        ),
        nbf.v4.new_code_cell(
            "plt.figure(figsize=(10, 5))\n"
            "plt.axhline(-10.0, color='r', linestyle='--', label='-10 dB Return Loss')\n"
            "plt.title('Youxch MLP S11 Validation: Ground Truth vs Predicted')\n"
            "plt.xlabel('Frequency (GHz)')\n"
            "plt.ylabel('S11 (dB)')\n"
            "plt.grid(True, alpha=0.3)\n"
            "plt.legend()\n"
            "plt.show()"
        )
    ]
    
    nb.cells = cells
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Generated {output_path}")

if __name__ == "__main__":
    create_youxch_notebook("src/anton/ml/workspaces/youxch_workspace/evaluation_template.ipynb")
    create_youxch_notebook("backend/app/ml/workspaces/youxch_workspace/evaluation_template.ipynb")

