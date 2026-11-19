# -*- coding: utf-8 -*-
"""Deep inspection of selected candidate repositories."""
import urllib.request
import json
import base64

CANDIDATES = [
    "Galabavamsi/Antenna-Net",
    "youxch/Inverse-design-of-patch-antennas",
    "udaykdk/pixelant",
    "METU-SIMPL/Microstrip-Patch",
    "vish1comp/antenna-ai-benchmark",
    "JastiTheCoder/ML-patch-antenna-design",
    "sharvesh1401/Inverse-design-patch-antenna",
    "becklabs/patch-antenna-tto",
    "DevAbdoTolba/Inverse-Design-of-a-U-Slot-Microstrip-Patch-Antenna",
    "Abinayasree6009/AI-Antenna-Design-Tool",
]

def fetch_readme(repo: str) -> str:
    url = f"https://api.github.com/repos/{repo}/readme"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ANTON-DeepDive)"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
            return content
    except Exception as e:
        return f"Error fetching README: {e}"

def fetch_files_and_sizes(repo: str):
    url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ANTON-DeepDive)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("tree", [])
            blobs = [item for item in items if item.get("type") == "blob"]
            return blobs
    except Exception as e:
        return []

def main():
    details = {}
    for repo in CANDIDATES:
        print(f"=== Fetching {repo} ===")
        blobs = fetch_files_and_sizes(repo)
        readme = fetch_readme(repo)
        
        # Analyze blobs
        checkpoints = []
        datasets = []
        code_files = []
        for b in blobs:
            path = b.get("path", "")
            size = b.get("size", 0)
            if any(path.endswith(ext) for ext in [".pth", ".pt", ".h5", ".hdf5", ".ckpt", ".bin", ".onnx", ".pb", ".pkl", ".joblib", ".weights", ".safetensors"]):
                checkpoints.append({"path": path, "size": size})
            elif any(path.endswith(ext) for ext in [".csv", ".mat", ".npz", ".npy", ".h5", ".json", ".s1p", ".s2p", ".dat"]):
                datasets.append({"path": path, "size": size})
            elif path.endswith(".py") or path.endswith(".ipynb"):
                code_files.append({"path": path, "size": size})
                
        print(f"  Blobs: {len(blobs)}")
        print(f"  Checkpoints ({len(checkpoints)}): {checkpoints}")
        print(f"  Datasets ({len(datasets)}): {[d['path'] for d in datasets[:10]]}")
        print(f"  Code files ({len(code_files)}): {[c['path'] for c in code_files[:10]]}")
        print(f"  README excerpt: {readme[:400].strip()}...\n")
        
        details[repo] = {
            "checkpoints": checkpoints,
            "datasets": datasets,
            "code_files": code_files,
            "readme_head": readme[:1500],
        }

    with open("data/deep_dive_raw.json", "w", encoding="utf-8") as f:
        json.dump(details, f, indent=2)
    print("Saved deep dive raw data to data/deep_dive_raw.json")

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    main()

