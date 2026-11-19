# -*- coding: utf-8 -*-
import sys

modules = ['torch', 'tensorflow', 'keras', 'h5py', 'sklearn', 'scipy', 'numpy', 'pydantic', 'safetensors', 'onnx']
for mod in modules:
    try:
        m = __import__(mod)
        ver = getattr(m, '__version__', 'installed')
        print(f"{mod}: {ver}")
    except ImportError as e:
        print(f"{mod}: NOT INSTALLED ({e})")
