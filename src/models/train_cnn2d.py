"""
Trains only the 2D-CNN model. Run this after train.py has completed
XGBoost, RF, and 1D-CNN (scalers and other models already saved).

Usage:
  python src/models/train_cnn2d.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[2]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Import everything from train.py
from train import (
    OUTPUTS, REGIONS, SEED,
    train_2dcnn,
)

def main() -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Device: %s", device)

    x_scaler = joblib.load(OUTPUTS / "x_scaler.pkl")
    y_scaler = joblib.load(OUTPUTS / "y_scaler.pkl")
    log.info("Loaded scalers from outputs/models/")

    train_2dcnn(x_scaler, y_scaler, device)
    log.info("Done.")

if __name__ == "__main__":
    main()
