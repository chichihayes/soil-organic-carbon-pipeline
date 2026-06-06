"""
Generates SOC and Nitrogen prediction maps from a trained model + Sentinel-2 imagery.

Produces a 2-band GeoTIFF (band 1 = SOC 0-5cm g/kg, band 2 = N 0-5cm g/kg)
at the Sentinel-2 raster's native resolution and extent.

Supported models: rf, xgboost, cnn1d, cnn2d

Usage:
  python src/models/predict.py --model rf --region europe
  python src/models/predict.py --model xgboost --region africa
  python src/models/predict.py --model cnn1d --region europe
  python src/models/predict.py --model cnn2d --region europe
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import rasterio
import torch
import torch.nn as nn
from rasterio.transform import Affine

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = PROJECT_ROOT / "outputs"
MODELS_DIR = OUTPUTS / "models"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

PATCH_HALF = 4       # must match train.py
PRED_BATCH = 8192    # pixels per inference batch (memory vs speed tradeoff)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model definitions (must match train.py architectures exactly)
# ---------------------------------------------------------------------------

class CNN1D(nn.Module):
    """1D spectral CNN — mirrors train.py CNN1D."""

    def __init__(self, n_features: int = 11, n_outputs: int = 2) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Flatten(),
            nn.Linear(128 * n_features, 256),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(256, n_outputs),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x.unsqueeze(1))


class CNN2D(nn.Module):
    """2D spatial-patch CNN — mirrors train.py CNN2D."""

    def __init__(self, in_channels: int = 11, n_outputs: int = 2) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3),
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, n_outputs),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def load_model(model_name: str, device: torch.device):
    """Load a trained model from outputs/models/.

    Args:
        model_name: One of 'rf', 'xgboost', 'cnn1d', 'cnn2d'.
        device: Torch device for CNN models.

    Returns:
        Loaded model object (sklearn or nn.Module).
    """
    if model_name == "rf":
        path = MODELS_DIR / "random_forest.pkl"
        log.info("Loading Random Forest from %s", path.name)
        return joblib.load(path)

    if model_name == "xgboost":
        path = MODELS_DIR / "xgboost.pkl"
        log.info("Loading XGBoost from %s", path.name)
        return joblib.load(path)

    if model_name == "cnn1d":
        path = MODELS_DIR / "cnn1d.pt"
        log.info("Loading 1D-CNN from %s", path.name)
        model = CNN1D()
        model.load_state_dict(torch.load(path, map_location=device))
        model.to(device).eval()
        return model

    if model_name == "cnn2d":
        path = MODELS_DIR / "cnn2d.pt"
        log.info("Loading 2D-CNN from %s", path.name)
        model = CNN2D()
        model.load_state_dict(torch.load(path, map_location=device))
        model.to(device).eval()
        return model

    raise ValueError(f"Unknown model '{model_name}'. Choose: rf, xgboost, cnn1d, cnn2d")


# ---------------------------------------------------------------------------
# Pixel-wise prediction (RF, XGBoost, 1D-CNN)
# ---------------------------------------------------------------------------

def predict_pixelwise(
    model_name: str,
    model,
    s2: np.ndarray,
    device: torch.device,
    x_scaler=None,
    y_scaler=None,
) -> np.ndarray:
    """Predict SOC and N for every valid pixel in a Sentinel-2 raster.

    Args:
        model_name: Model type string.
        model: Fitted model.
        s2: (H, W, 11) float32 Sentinel-2 array, NaN where invalid.
        device: Torch device (CNN only).
        x_scaler: Fitted StandardScaler for X (CNN only).
        y_scaler: Fitted StandardScaler for Y (CNN only).

    Returns:
        (H, W, 2) float32 array — [SOC g/kg, N g/kg], NaN where no prediction.
    """
    H, W = s2.shape[:2]
    valid = np.all(np.isfinite(s2), axis=-1)   # (H, W)
    X_flat = s2.reshape(-1, 11)                 # (H*W, 11)
    valid_flat = valid.ravel()

    X_valid = X_flat[valid_flat]
    log.info("  predicting %d valid pixels ...", len(X_valid))

    if model_name in ("rf", "xgboost"):
        preds = model.predict(X_valid).astype(np.float32)   # (N, 2)

    else:  # cnn1d
        X_scaled = x_scaler.transform(X_valid).astype(np.float32)
        preds_s = []
        with torch.no_grad():
            for i in range(0, len(X_scaled), PRED_BATCH):
                Xb = torch.from_numpy(X_scaled[i:i + PRED_BATCH]).to(device)
                preds_s.append(model(Xb).cpu().numpy())
        preds_s = np.concatenate(preds_s)
        preds = y_scaler.inverse_transform(preds_s).astype(np.float32)

    out_flat = np.full((H * W, 2), np.nan, dtype=np.float32)
    out_flat[valid_flat] = preds
    return out_flat.reshape(H, W, 2)


# ---------------------------------------------------------------------------
# Patch-based prediction (2D-CNN)
# ---------------------------------------------------------------------------

def predict_patches(
    model,
    s2: np.ndarray,
    device: torch.device,
    x_scaler,
    y_scaler,
) -> np.ndarray:
    """Predict SOC and N using 9×9 spatial patches (2D-CNN only).

    Border pixels (PATCH_HALF wide) remain NaN — negligible at continental scale.

    Args:
        model: Loaded CNN2D model in eval mode.
        s2: (H, W, 11) float32, NaN where invalid.
        device: Torch device.
        x_scaler: Fitted X StandardScaler.
        y_scaler: Fitted Y StandardScaler.

    Returns:
        (H, W, 2) float32 SOC/N map.
    """
    H, W = s2.shape[:2]
    h = PATCH_HALF

    # Pre-scale S2 raster
    s2_flat = s2.reshape(-1, 11)
    nan_rows = ~np.all(np.isfinite(s2_flat), axis=1)
    s2_clean = s2_flat.copy()
    s2_clean[nan_rows] = 0.0
    s2_scaled_flat = x_scaler.transform(s2_clean).astype(np.float32)
    s2_scaled_flat[nan_rows] = np.nan
    s2_scaled = s2_scaled_flat.reshape(H, W, 11)

    # Valid pixels (not NaN, not on border)
    valid = np.all(np.isfinite(s2), axis=-1)
    valid[:h, :] = False
    valid[-h:, :] = False
    valid[:, :h] = False
    valid[:, -h:] = False
    rows, cols = np.where(valid)
    log.info("  predicting %d patch pixels ...", len(rows))

    row_offsets = np.arange(-h, h + 1)   # (9,)
    col_offsets = np.arange(-h, h + 1)   # (9,)

    out_flat = np.full((H * W, 2), np.nan, dtype=np.float32)

    with torch.no_grad():
        for start in range(0, len(rows), PRED_BATCH):
            end = min(start + PRED_BATCH, len(rows))
            br = rows[start:end]
            bc = cols[start:end]

            # Vectorised patch extraction: (B, 9, 9, 11) → (B, 11, 9, 9)
            patch_r = br[:, None, None] + row_offsets[None, :, None]  # (B, 9, 9)
            patch_c = bc[:, None, None] + col_offsets[None, None, :]  # (B, 9, 9)
            patches = s2_scaled[patch_r, patch_c, :]                  # (B, 9, 9, 11)
            patches = np.ascontiguousarray(patches.transpose(0, 3, 1, 2))  # (B, 11, 9, 9)

            preds_s = model(torch.from_numpy(patches).to(device)).cpu().numpy()
            preds = y_scaler.inverse_transform(preds_s).astype(np.float32)

            linear_idx = br * W + bc
            out_flat[linear_idx] = preds

    return out_flat.reshape(H, W, 2)


# ---------------------------------------------------------------------------
# Save output map
# ---------------------------------------------------------------------------

def save_map(
    soc_n: np.ndarray,
    profile: dict,
    region: str,
    model_name: str,
) -> Path:
    """Write a 2-band SOC/N GeoTIFF to outputs/maps/{region}/.

    Band 1 = SOC 0-5cm (g/kg), Band 2 = N 0-5cm (g/kg).

    Args:
        soc_n: (H, W, 2) float32 prediction map.
        profile: rasterio profile from the source S2 raster.
        region: 'europe' or 'africa'.
        model_name: Used in output filename.

    Returns:
        Path to written file.
    """
    out_dir = OUTPUTS / "maps" / region
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{model_name}_soc_n.tif"

    profile.update(
        count=2,
        dtype="float32",
        nodata=np.nan,
        compress="lzw",
    )
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(soc_n[:, :, 0], 1)
        dst.write(soc_n[:, :, 1], 2)
        dst.update_tags(1, name="SOC_0-5cm_g_per_kg")
        dst.update_tags(2, name="Nitrogen_0-5cm_g_per_kg")

    log.info("Saved → %s", out_path.relative_to(PROJECT_ROOT))
    return out_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Parse args, load model, predict, save map."""
    parser = argparse.ArgumentParser(description="Generate SOC/N prediction map.")
    parser.add_argument("--model", required=True, choices=["rf", "xgboost", "cnn1d", "cnn2d"],
                        help="Trained model to use.")
    parser.add_argument("--region", required=True, choices=["europe", "africa"],
                        help="Target region.")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Model=%s  Region=%s  Device=%s", args.model, args.region, device)

    model = load_model(args.model, device)

    x_scaler = joblib.load(MODELS_DIR / "x_scaler.pkl") if args.model in ("cnn1d", "cnn2d") else None
    y_scaler = joblib.load(MODELS_DIR / "y_scaler.pkl") if args.model in ("cnn1d", "cnn2d") else None

    s2_path = PROCESSED_DIR / args.region / "sentinel2" / f"sentinel2_{args.region}.tif"
    log.info("Loading Sentinel-2: %s", s2_path.relative_to(PROJECT_ROOT))
    with rasterio.open(s2_path) as src:
        s2 = src.read().astype(np.float32).transpose(1, 2, 0)  # (H, W, 11)
        profile = src.profile.copy()

    log.info("S2 grid: %dx%d  bands=%d", s2.shape[0], s2.shape[1], s2.shape[2])

    if args.model == "cnn2d":
        soc_n = predict_patches(model, s2, device, x_scaler, y_scaler)
    else:
        soc_n = predict_pixelwise(args.model, model, s2, device, x_scaler, y_scaler)

    log.info(
        "SOC: %.1f – %.1f g/kg (mean %.1f) | N: %.3f – %.3f g/kg (mean %.3f)",
        float(np.nanmin(soc_n[:, :, 0])), float(np.nanmax(soc_n[:, :, 0])), float(np.nanmean(soc_n[:, :, 0])),
        float(np.nanmin(soc_n[:, :, 1])), float(np.nanmax(soc_n[:, :, 1])), float(np.nanmean(soc_n[:, :, 1])),
    )

    save_map(soc_n, profile, args.region, args.model)


if __name__ == "__main__":
    main()
