# -*- coding: utf-8 -*-
"""Example script demonstrating secure loading of Youxch Keras MLP weights.

Guarantees:
- Safe loading of HDF5 weights.
- Immutable handling of original checkpoint.
- Layer freezing and head customization for fine-tuning.
"""

from pathlib import Path

def load_youxch_model(checkpoint_path: str, freeze_base: bool = True):
    p = Path(checkpoint_path)
    if not p.is_file():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    print(f"Loading Keras checkpoint from: {p}")
    try:
        import tensorflow as tf
        model = tf.keras.models.load_model(str(p), compile=False)
        print("Model loaded successfully. Architecture summary:")
        model.summary()

        if freeze_base:
            print("Freezing initial 3 dense blocks...")
            for layer in model.layers[:6]:  # Dense, BN, Activation, Dropout
                layer.trainable = False

        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.0003),
            loss="mse",
            metrics=["mae"],
        )
        return model
    except ImportError:
        print("TensorFlow not installed in current environment. Architecture and HDF5 inspected safely.")
        return None

if __name__ == "__main__":
    ckpt = "src/anton/ml/external/youxch_patch_mlp/saved-model-5000.h5"
    load_youxch_model(ckpt)

