# -*- coding: utf-8 -*-
import nbformat as nbf
from pathlib import Path

def create_antennanet_notebook(output_path: str):
    nb = nbf.v4.new_notebook()
    
    cells = [
        nbf.v4.new_markdown_cell(
            "# Antenna-Net Validation & Benchmark Evaluation\n\n"
            "This notebook calculates standardized electromagnetic performance metrics for the fine-tuned or adapted Antenna-Net model.\n\n"
            "### Target Metrics\n"
            "- **MAE** ($S_{11}$ spectral error in dB)\n"
            "- **RMSE** ($S_{11}$ spectral error in dB)\n"
            "- **Resonant Frequency Deviation** ($|\\Delta f_r|$ in MHz and %)\n"
            "- **-10dB Impedance Bandwidth Deviation** ($|\\Delta \\text{BW}|$ in MHz)\n"
            "- **Inference Latency** (ms per antenna design)"
        ),
        nbf.v4.new_code_cell(
            "import sys\n"
            "from pathlib import Path\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n\n"
            "# Add ANTON src to path\n"
            "sys.path.insert(0, str(Path('../../..').resolve()))\n"
            "from anton.ml.registry import AntennaBenchmarkEvaluator, EvaluationSlice"
        ),
        nbf.v4.new_markdown_cell(
            "## 1. Load Ground Truth Validation Dataset\n"
            "Ensure the ground-truth data comes from authentic electromagnetic simulation (e.g. ANSYS HFSS or CST Studio)."
        ),
        nbf.v4.new_code_cell(
            "# Define frequency sweep grid (1.0 to 6.0 GHz, 101 points)\n"
            "freqs_ghz = np.linspace(1.0, 6.0, 101)\n\n"
            "# Placeholder: Load your verified validation data here\n"
            "# Example: val_data = np.load('val_ground_truth.npz')\n"
            "print(f'Frequency grid: {len(freqs_ghz)} points from {freqs_ghz[0]} to {freqs_ghz[-1]} GHz')"
        ),
        nbf.v4.new_markdown_cell(
            "## 2. Model Inference & Evaluation\n"
            "Execute model prediction and compute metrics using ANTON's standardized evaluator."
        ),
        nbf.v4.new_code_cell(
            "# Evaluator calculation examples\n"
            "# y_true = val_data['s11_true_db']\n"
            "# y_pred = model_predictions\n\n"
            "# mae = AntennaBenchmarkEvaluator.calculate_mae(y_true, y_pred)\n"
            "# rmse = AntennaBenchmarkEvaluator.calculate_rmse(y_true, y_pred)\n"
            "# r2 = AntennaBenchmarkEvaluator.calculate_r2(y_true, y_pred)\n"
            "print('Benchmark evaluation cell ready for execution against loaded validation set.')"
        ),
        nbf.v4.new_markdown_cell(
            "## 3. Visualization: S11 Return Loss Curves\n"
            "Compare predicted vs simulated reflection coefficients."
        ),
        nbf.v4.new_code_cell(
            "# Visual inspection template\n"
            "plt.figure(figsize=(10, 5))\n"
            "plt.axhline(-10.0, color='r', linestyle='--', label='-10 dB Threshold')\n"
            "plt.title('Antenna-Net S11 Return Loss: Ground Truth vs Prediction')\n"
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
    create_antennanet_notebook("src/anton/ml/workspaces/antennanet_workspace/evaluation_template.ipynb")
    create_antennanet_notebook("backend/app/ml/workspaces/antennanet_workspace/evaluation_template.ipynb")

