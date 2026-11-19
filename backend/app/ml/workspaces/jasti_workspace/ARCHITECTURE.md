# Jasti ML Patch Antenna Architecture Specification

## Overview
- **Model ID**: `jasti_rf_surrogate`
- **Source Repository**: `https://github.com/JastiTheCoder/ML-patch-antenna-design`
- **License**: MIT License
- **Framework**: Scikit-Learn / DEAP (Python)
- **Primary Capabilities**: Resonant frequency ($f_r$) prediction, -10dB Bandwidth ($BW$) prediction, Genetic Algorithm antenna optimization for 2.45 GHz ISM band.

---

## 1. Model Pipeline
- **Algorithm**: Random Forest Regressor (`sklearn.ensemble.RandomForestRegressor`)
- **Estimators**: 200 Decision Trees
- **Max Depth**: 15
- **Criterion**: Squared Error (MSE)
- **Optimizer**: Distributed Evolutionary Algorithms in Python (DEAP) Genetic Algorithm
  - Population size: 100
  - Generations: 50
  - Mutation probability: 0.2
  - Crossover probability: 0.7

---

## 2. Adaptation to ANTON Canonical Rectangular Patch
- Fast inference latency (< 1.5 ms on CPU).
- Maps directly to ANTON's `rectangular_patch` parameters $[W, L, h, \varepsilon_r]$.
- Provides instantaneous initial geometry estimates for subsequent HFSS notebook generation.
