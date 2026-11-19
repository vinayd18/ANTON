# -*- coding: utf-8 -*-
"""Inspect candidate repositories for ANTON Stage 3.0."""
import urllib.request
import urllib.error
import json
import os

REPOS = [
    "Galabavamsi/Antenna-Net",
    "udaykdk/pixelant",
    "METU-SIMPL/Microstrip-Patch",
    "vish1comp/antenna-ai-benchmark",
    "youxch/Inverse-design-of-patch-antennas",
    "JastiTheCoder/ML-patch-antenna-design",
]

def inspect_repo(repo_slug: str):
    base_url = f"https://api.github.com/repos/{repo_slug}"
    req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0 (ANTON-Inspector)"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"=== {repo_slug} === HTTP ERROR: {e.code} {e.reason}")
        return None
    except Exception as e:
        print(f"=== {repo_slug} === ERROR: {e}")
        return None

    lic = data.get("license") or {}
    print(f"=== {repo_slug} ===")
    print(f"  Description: {data.get('description')}")
    print(f"  License: {lic.get('name', 'None')}")
    print(f"  Default Branch: {data.get('default_branch')}")
    print(f"  Stars: {data.get('stargazers_count')}, Forks: {data.get('forks_count')}")
    print(f"  Size KB: {data.get('size')}")

    # Inspect tree contents
    tree_url = f"https://api.github.com/repos/{repo_slug}/git/trees/{data.get('default_branch')}?recursive=1"
    req_tree = urllib.request.Request(tree_url, headers={"User-Agent": "Mozilla/5.0 (ANTON-Inspector)"})
    try:
        with urllib.request.urlopen(req_tree, timeout=12) as resp:
            tree_data = json.loads(resp.read().decode())
            files = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
            print(f"  Total files: {len(files)}")
            checkpoints = [f for f in files if any(f.endswith(ext) for ext in [".pth", ".pt", ".h5", ".hdf5", ".ckpt", ".bin", ".onnx", ".pb", ".pkl", ".joblib", ".weights", ".safetensors"])]
            print(f"  Checkpoint / model weight files ({len(checkpoints)}): {checkpoints[:10]}")
            datasets = [f for f in files if any(f.endswith(ext) for ext in [".csv", ".mat", ".npz", ".npy", ".h5", ".json", ".s1p", ".s2p"])]
            print(f"  Dataset files ({len(datasets)}): {datasets[:10]}")
            scripts = [f for f in files if f.endswith(".py") or f.endswith(".ipynb")]
            print(f"  Code / Notebook files ({len(scripts)}): {scripts[:15]}")
    except Exception as e:
        print(f"  Could not fetch tree: {e}")

    # Inspect releases
    rel_url = f"https://api.github.com/repos/{repo_slug}/releases"
    req_rel = urllib.request.Request(rel_url, headers={"User-Agent": "Mozilla/5.0 (ANTON-Inspector)"})
    try:
        with urllib.request.urlopen(req_rel, timeout=12) as resp:
            rel_data = json.loads(resp.read().decode())
            print(f"  Releases ({len(rel_data)}): {[r.get('tag_name') for r in rel_data]}")
            for r in rel_data:
                assets = r.get("assets", [])
                print(f"    Release {r.get('tag_name')} assets: {[a.get('name') for a in assets]}")
    except Exception as e:
        print(f"  Could not fetch releases: {e}")

    print()
    return data

if __name__ == "__main__":
    for repo in REPOS:
        inspect_repo(repo)

