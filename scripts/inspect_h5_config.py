import h5py
import json

h5_path = "src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5"
with h5py.File(h5_path, "r") as f:
    print("Attrs keys:", list(f.attrs.keys()))
    if "model_config" in f.attrs:
        mc = f.attrs["model_config"]
        if isinstance(mc, bytes):
            mc = mc.decode("utf-8")
        cfg = json.loads(mc)
        print("Model Config:")
        print(json.dumps(cfg, indent=2)[:2000])
    if "training_config" in f.attrs:
        tc = f.attrs["training_config"]
        if isinstance(tc, bytes):
            tc = tc.decode("utf-8")
        print("Training Config:")
        print(tc[:500])

