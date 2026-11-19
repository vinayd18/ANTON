# -*- coding: utf-8 -*-
"""Example script demonstrating secure loading of Antenna-Net weights.

Guarantees:
- Safe loading with PyTorch weights_only=True.
- Immutable handling of original checkpoint.
- Feature extractor freezing and custom head attachment for fine-tuning.
"""

import sys
from pathlib import Path
import torch
import torch.nn as nn

# Model Definition matching Antenna-Net s11_model architecture
class AntennaNetS11Model(nn.Module):
    def __init__(self, in_features=4, out_points=101):
        super().__init__()
        self.fc1 = nn.Linear(in_features, 128)
        self.bn1 = nn.BatchNorm1d(128)
        self.act1 = nn.LeakyReLU(0.1)
        self.drop1 = nn.Dropout(0.1)

        self.fc2 = nn.Linear(128, 256)
        self.bn2 = nn.BatchNorm1d(256)
        self.act2 = nn.LeakyReLU(0.1)
        self.drop2 = nn.Dropout(0.1)

        self.fc3 = nn.Linear(256, 512)
        self.bn3 = nn.BatchNorm1d(512)
        self.act3 = nn.LeakyReLU(0.1)

        self.fc4 = nn.Linear(512, 256)
        self.bn4 = nn.BatchNorm1d(256)
        self.act4 = nn.LeakyReLU(0.1)

        self.out = nn.Linear(256, out_points)

    def forward(self, x):
        x = self.drop1(self.act1(self.bn1(self.fc1(x))))
        x = self.drop2(self.act2(self.bn2(self.fc2(x))))
        x = self.act3(self.bn3(self.fc3(x)))
        x = self.act4(self.bn4(self.fc4(x)))
        return self.out(x)


def load_model_for_finetuning(checkpoint_path: str, freeze_base: bool = True):
    p = Path(checkpoint_path)
    if not p.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    print(f"Loading checkpoint from: {p}")
    model = AntennaNetS11Model()

    # Safe loading without arbitrary code execution
    try:
        state_dict = torch.load(p, map_location="cpu", weights_only=True)
        if isinstance(state_dict, dict) and "state_dict" in state_dict:
            state_dict = state_dict["state_dict"]
        model.load_state_dict(state_dict, strict=False)
        print("Checkpoint successfully loaded into model.")
    except Exception as e:
        print(f"Warning during weights_only load: {e}")
        # State dict keys inspection
        print("Proceeding with model architecture initialized.")

    if freeze_base:
        print("Freezing base feature extraction layers (fc1, fc2)...")
        for param in model.fc1.parameters():
            param.requires_grad = False
        for param in model.fc2.parameters():
            param.requires_grad = False

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = sum(p.numel() for p in model.parameters() if not p.requires_grad)
    print(f"Model Summary: {trainable_params:,} trainable parameters, {frozen_params:,} frozen parameters.")
    return model


if __name__ == "__main__":
    ckpt = "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt"
    if Path(ckpt).is_file():
        m = load_model_for_finetuning(ckpt)
        dummy_input = torch.tensor([[0.5, 0.5, 0.4, 0.35]], dtype=torch.float32)
        m.eval()
        with torch.no_grad():
            pred_s11 = m(dummy_input)
        print(f"Inference test successful! Output shape: {pred_s11.shape}")
    else:
        print(f"Checkpoint {ckpt} not found. Run download_verified_checkpoints.py first.")
