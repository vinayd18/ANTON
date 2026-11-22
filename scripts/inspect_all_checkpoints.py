import hashlib
import torch
import h5py
from pathlib import Path

def get_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(131072):
            h.update(chunk)
    return h.hexdigest()

torch_files = [
    "src/anton/ml/external/galabavamsi_antennanet/s11_model.pt",
    "src/anton/ml/external/galabavamsi_antennanet/best_forward_surrogate.pt",
    "src/anton/ml/external/galabavamsi_antennanet/best_pixel_surrogate.pt",
    "src/anton/ml/external/galabavamsi_antennanet/s11_pinn_model.pt",
    "src/anton/ml/external/galabavamsi_antennanet/hybrid_lorentzian_rnn_best.pth",
]

for tf in torch_files:
    p = Path(tf)
    print("=" * 60)
    print(f"FILE: {p.name} ({p.stat().st_size} bytes)")
    print(f"SHA-256: {get_sha256(p)}")
    try:
        data = torch.load(p, map_location="cpu", weights_only=False)
        print("Loaded successfully. Type:", type(data))
        if isinstance(data, dict):
            print("Keys:", list(data.keys())[:10])
            for k in list(data.keys())[:10]:
                v = data[k]
                if hasattr(v, "shape"):
                    print(f"  {k}: shape {v.shape}, dtype {v.dtype}")
                elif isinstance(v, dict):
                    print(f"  {k}: dict with {len(v)} subkeys")
                else:
                    print(f"  {k}: {type(v)}")
        elif hasattr(data, "state_dict"):
            print("Module state_dict keys:")
            sd = data.state_dict()
            for k in list(sd.keys())[:10]:
                print(f"  {k}: shape {sd[k].shape}, dtype {sd[k].dtype}")
    except Exception as e:
        print(f"Load Error: {type(e).__name__}: {e}")

h5_file = Path("src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5")
print("=" * 60)
print(f"FILE: {h5_file.name} ({h5_file.stat().st_size} bytes)")
print(f"SHA-256: {get_sha256(h5_file)}")
try:
    with h5py.File(h5_file, "r") as f:
        print("HDF5 Root keys:", list(f.keys()))
        print("HDF5 Root attrs:", list(f.attrs.keys()))
        if "model_weights" in f:
            print("model_weights keys:", list(f["model_weights"].keys()))
        def visitor(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(f"  Dataset {name}: shape {obj.shape}, dtype {obj.dtype}")
        print("Structure sample:")
        f.visititems(visitor)
except Exception as e:
    print(f"HDF5 Load Error: {type(e).__name__}: {e}")

