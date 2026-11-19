import torch
import h5py
from pathlib import Path

checkpoints = {
    "s11_model": "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt",
    "best_forward_surrogate": "src/anton/ml/external/galabavamsi_antennanet/best_forward_surrogate.pt",
    "best_pixel_surrogate": "src/anton/ml/external/galabavamsi_antennanet/best_pixel_surrogate.pt",
    "s11_pinn_model": "src/anton/ml/external/galabavamsi_antennanet/s11_pinn_model.pt",
    "hybrid_lorentzian_rnn_best": "src/anton/ml/external/galabavamsi_antennanet/hybrid_lorentzian_rnn_best.pth",
}

for name, path in checkpoints.items():
    print("=" * 60)
    print(name)
    sd = torch.load(path, map_location="cpu", weights_only=False)
    for k, v in sd.items():
        if hasattr(v, "shape"):
            print(f"  {k}: {tuple(v.shape)}")
        else:
            print(f"  {k}: {type(v)}")

print("=" * 60)
print("saved-model-5000.h5")
with h5py.File("src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5", "r") as f:
    for k in f.keys():
        print(f"  Group: {k}")
        grp = f[k]
        if isinstance(grp, h5py.Group):
            for subk in grp.keys():
                subgrp = grp[subk]
                if isinstance(subgrp, h5py.Group):
                    for dset in subgrp.keys():
                        print(f"    {subk}/{dset}: {subgrp[dset].shape}")
                elif isinstance(subgrp, h5py.Dataset):
                    print(f"    {subk}: {subgrp.shape}")
