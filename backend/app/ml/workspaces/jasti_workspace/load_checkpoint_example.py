# -*- coding: utf-8 -*-
"""Example script demonstrating loading and training of Jasti RF surrogate."""

from sklearn.ensemble import RandomForestRegressor
import numpy as np

def train_and_export_surrogate(X_train: np.ndarray, y_train: np.ndarray, export_path: str = "rf_surrogate.joblib"):
    print(f"Training RandomForestRegressor on {len(X_train)} samples...")
    rf = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=4,
        random_state=42,
    )
    rf.fit(X_train, y_train)
    print("Training complete. Feature importances:")
    param_names = ["width", "length", "height", "dielectric_constant"]
    for name, imp in zip(param_names, rf.feature_importances_):
        print(f"  {name}: {imp:.4f}")
    return rf

if __name__ == "__main__":
    # Test synthetic features for syntax verification
    X = np.random.uniform([20, 20, 0.8, 2.0], [50, 50, 2.5, 4.5], size=(20, 4))
    y = np.random.uniform([2.0, 30.0], [3.0, 70.0], size=(20, 2))
    rf = train_and_export_surrogate(X, y)
    print("Script executed successfully.")
