"""
Trains 4 models to predict SOC 0-5cm (g/kg) and Nitrogen 0-5cm (g/kg)
from Sentinel-2 spectral features.

Models:
  1. XGBoost       — pixel-wise tabular baseline
  2. Random Forest — pixel-wise comparison
  3. 1D-CNN        — pixel-wise spectral convolution (PyTorch)
  4. 2D-CNN        — 9x9 spatial patch model (PyTorch)

Outputs: outputs/models/{model}.{pkl|pt}  +  outputs/models/{x,y}_scaler.pkl

Usage:
  python src/models/train.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import rasterio
import torch
import torch.nn as nn
from rasterio.warp import Resampling, reproject
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from torch.utils.data import ConcatDataset, DataLoader, Dataset, TensorDataset
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = PROJECT_ROOT / "outputs" / "models"
TRAINING_DIR = PROJECT_ROOT / "data" / "training"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

REGIONS = ["europe", "africa"]
PATCH_HALF = 4           # patch = 2*PATCH_HALF+1 = 9
MAX_TREE_SAMPLES = 500_000
VAL_FRAC = 0.2
EPOCHS_1D = 10
EPOCHS_2D = 5
BATCH_1D = 4096
BATCH_2D = 1024
LR = 1e-3
SEED = 42

np.random.seed(SEED)
torch.manual_seed(SEED)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pixel_data() -> tuple[np.ndarray, np.ndarray]:
    """Load pixel-wise features and targets from all regions.

    Returns:
        X: (N, 11) float32 — Sentinel-2 bands + NDVI + BSI
        Y: (N, 2)  float32 — [SOC_0-5cm g/kg, Nitrogen_0-5cm g/kg]
    """
    X_parts, Y_parts = [], []
    for region in REGIONS:
        data = np.load(TRAINING_DIR / region / f"training_{region}.npz")
        X_parts.append(data["X"])
        Y_parts.append(np.stack([data["y_soc"][:, 0], data["y_nitrogen"][:, 0]], axis=1))
    return np.concatenate(X_parts).astype(np.float32), np.concatenate(Y_parts).astype(np.float32)


def _reproject_to_s2(
    src_path: Path,
    dst_transform,
    dst_width: int,
    dst_height: int,
    dst_crs,
) -> np.ndarray:
    """Reproject a SoilGrids Int16 raster to the Sentinel-2 grid.

    Args:
        src_path: Source SoilGrids GeoTIFF (Int16, nodata=-32768).
        dst_transform: Target affine transform.
        dst_width: Target pixel width.
        dst_height: Target pixel height.
        dst_crs: Target CRS.

    Returns:
        (H, W) float32 array — nodata pixels are NaN.
    """
    dst = np.empty((dst_height, dst_width), dtype=np.float32)
    with rasterio.open(src_path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=-32768,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return dst


def load_rasters_for_patches(
    region: str,
    x_scaler: StandardScaler,
    y_scaler: StandardScaler,
) -> tuple[np.ndarray, np.ndarray]:
    """Load and pre-scale S2 raster and SoilGrids labels for patch extraction.

    Pre-scaling in __init__ rather than __getitem__ avoids per-sample scaler
    overhead during DataLoader iteration.

    Args:
        region: 'europe' or 'africa'.
        x_scaler: Fitted StandardScaler for X (11 features).
        y_scaler: Fitted StandardScaler for Y (2 outputs).

    Returns:
        s2_scaled:     (H, W, 11) float32 — scaled, NaN where invalid.
        labels_scaled: (H, W, 2)  float32 — scaled [SOC, N], NaN where invalid.
    """
    processed = PROCESSED_DIR / region
    s2_path = processed / "sentinel2" / f"sentinel2_{region}.tif"

    log.info("  [%s] loading S2 raster ...", region)
    with rasterio.open(s2_path) as src:
        s2 = src.read().astype(np.float32).transpose(1, 2, 0)  # (H, W, 11)
        tx, crs, H, W = src.transform, src.crs, src.height, src.width

    log.info("  [%s] reprojecting SoilGrids labels ...", region)
    soc = _reproject_to_s2(processed / "soc" / "soc_0-5cm_mean.tif", tx, W, H, crs) / 10.0
    nit = _reproject_to_s2(processed / "nitrogen" / "nitrogen_0-5cm_mean.tif", tx, W, H, crs) / 100.0

    # Scale X — fill NaN with 0 before transform (masked pixels are excluded later)
    s2_flat = s2.reshape(-1, 11)
    nan_rows = ~np.all(np.isfinite(s2_flat), axis=1)
    s2_flat_clean = s2_flat.copy()
    s2_flat_clean[nan_rows] = 0.0
    s2_scaled = x_scaler.transform(s2_flat_clean).astype(np.float32)
    s2_scaled[nan_rows] = np.nan
    s2_scaled = s2_scaled.reshape(H, W, 11)

    # Scale Y
    labels = np.stack([soc.ravel(), nit.ravel()], axis=1)  # (H*W, 2)
    valid_mask = np.all(np.isfinite(labels), axis=1)
    labels_scaled = np.full_like(labels, np.nan)
    if valid_mask.any():
        labels_scaled[valid_mask] = y_scaler.transform(labels[valid_mask])
    labels_scaled = labels_scaled.reshape(H, W, 2).astype(np.float32)

    return s2_scaled, labels_scaled


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def log_metrics(name: str, y_true: np.ndarray, y_pred: np.ndarray) -> None:
    """Log R², RMSE, MAE for SOC and Nitrogen separately.

    Args:
        name: Model name for display.
        y_true: (N, 2) ground truth.
        y_pred: (N, 2) predictions.
    """
    for i, label in enumerate(["SOC", "N"]):
        r2   = r2_score(y_true[:, i], y_pred[:, i])
        rmse = float(np.sqrt(mean_squared_error(y_true[:, i], y_pred[:, i])))
        mae  = mean_absolute_error(y_true[:, i], y_pred[:, i])
        log.info("  %-15s  %-4s  R²=%.3f  RMSE=%.3f g/kg  MAE=%.3f g/kg", name, label, r2, rmse, mae)


# ---------------------------------------------------------------------------
# Tree models
# ---------------------------------------------------------------------------

def train_xgboost(
    X_tr: np.ndarray, Y_tr: np.ndarray,
    X_val: np.ndarray, Y_val: np.ndarray,
) -> None:
    """Train and evaluate XGBoost via MultiOutputRegressor.

    Args:
        X_tr: Training features (N_tr, 11).
        Y_tr: Training targets (N_tr, 2).
        X_val: Validation features.
        Y_val: Validation targets.
    """
    log.info("Training XGBoost (subsample=%d) ...", min(len(X_tr), MAX_TREE_SAMPLES))
    n = min(len(X_tr), MAX_TREE_SAMPLES)
    idx = np.random.choice(len(X_tr), n, replace=False)
    model = MultiOutputRegressor(
        XGBRegressor(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            n_jobs=-1, random_state=SEED, verbosity=0,
        ),
        n_jobs=2,
    )
    model.fit(X_tr[idx], Y_tr[idx])
    log_metrics("XGBoost", Y_val, model.predict(X_val))
    joblib.dump(model, OUTPUTS / "xgboost.pkl")
    log.info("  saved → outputs/models/xgboost.pkl")


def train_rf(
    X_tr: np.ndarray, Y_tr: np.ndarray,
    X_val: np.ndarray, Y_val: np.ndarray,
) -> None:
    """Train and evaluate Random Forest (multi-output natively).

    Args:
        X_tr: Training features.
        Y_tr: Training targets.
        X_val: Validation features.
        Y_val: Validation targets.
    """
    log.info("Training Random Forest (subsample=%d) ...", min(len(X_tr), MAX_TREE_SAMPLES))
    n = min(len(X_tr), MAX_TREE_SAMPLES)
    idx = np.random.choice(len(X_tr), n, replace=False)
    model = RandomForestRegressor(n_estimators=100, n_jobs=-1, random_state=SEED)
    model.fit(X_tr[idx], Y_tr[idx])
    log_metrics("Random Forest", Y_val, model.predict(X_val))
    joblib.dump(model, OUTPUTS / "random_forest.pkl")
    log.info("  saved → outputs/models/random_forest.pkl")


# ---------------------------------------------------------------------------
# 1D-CNN
# ---------------------------------------------------------------------------

class CNN1D(nn.Module):
    """1D convolution over spectral bands for pixel-wise SOC/N regression.

    Treats the 11-band spectrum as a 1D sequence with 1 input channel.
    """

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
        """Args: x (B, 11). Returns: (B, 2)."""
        return self.net(x.unsqueeze(1))   # (B, 11) → (B, 1, 11)


# ---------------------------------------------------------------------------
# 2D-CNN
# ---------------------------------------------------------------------------

class PatchDataset(Dataset):
    """Provides (patch, label) pairs from pre-scaled in-memory rasters.

    Patches are extracted on-the-fly by indexing pre-scaled numpy arrays.
    Pre-scaling in __init__ avoids StandardScaler overhead per sample.
    """

    def __init__(
        self,
        s2_scaled: np.ndarray,      # (H, W, 11) float32 — pre-scaled, NaN=invalid
        labels_scaled: np.ndarray,  # (H, W, 2)  float32 — pre-scaled, NaN=invalid
        half: int = PATCH_HALF,
    ) -> None:
        self.s2 = s2_scaled
        self.labels = labels_scaled
        self.half = half

        H, W = s2_scaled.shape[:2]
        valid = (
            np.all(np.isfinite(s2_scaled), axis=-1) &
            np.all(np.isfinite(labels_scaled), axis=-1)
        )
        # Exclude border pixels where a full patch would exceed the array
        valid[:half, :] = False
        valid[-half:, :] = False
        valid[:, :half] = False
        valid[:, -half:] = False
        rows, cols = np.where(valid)
        self.indices = np.stack([rows, cols], axis=1)   # (N, 2) int32

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        r, c = self.indices[i]
        h = self.half
        patch = self.s2[r - h:r + h + 1, c - h:c + h + 1, :]  # (9, 9, 11)
        patch = np.nan_to_num(patch, nan=0.0)                   # ocean/edge NaNs → 0 (scaled mean)
        patch = np.ascontiguousarray(patch.transpose(2, 0, 1))  # (11, 9, 9)
        label = self.labels[r, c].copy()                        # (2,)
        return torch.from_numpy(patch), torch.from_numpy(label)


class CNN2D(nn.Module):
    """2D spatial-spectral convolution over 9×9 patches for SOC/N regression."""

    def __init__(self, in_channels: int = 11, n_outputs: int = 2) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, kernel_size=3, padding=1),   # 9×9
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),            # 9×9
            nn.ReLU(),
            nn.Conv2d(64, 128, kernel_size=3),                      # 7×7
            nn.ReLU(),
            nn.Conv2d(128, 128, kernel_size=3),                     # 5×5
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, n_outputs),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args: x (B, 11, 9, 9). Returns: (B, 2)."""
        return self.net(x)


# ---------------------------------------------------------------------------
# Generic NN training loop
# ---------------------------------------------------------------------------

def _nn_train_eval(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Train with MSE+Adam, return (y_true_scaled, y_pred_scaled) on val set.

    Args:
        model: PyTorch model.
        train_loader: Training DataLoader.
        val_loader: Validation DataLoader.
        device: Compute device.
        epochs: Number of training epochs.

    Returns:
        y_true: (N_val, 2) ground truth in normalized space.
        y_pred: (N_val, 2) predictions in normalized space.
    """
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    criterion = nn.MSELoss()
    model.to(device)
    log_every = max(1, epochs // 5)

    for epoch in range(1, epochs + 1):
        model.train()
        t_loss = 0.0
        for Xb, Yb in train_loader:
            Xb, Yb = Xb.to(device), Yb.to(device)
            optimizer.zero_grad()
            loss = criterion(model(Xb), Yb)
            loss.backward()
            optimizer.step()
            t_loss += loss.item() * len(Xb)

        if epoch % log_every == 0 or epoch == epochs:
            model.eval()
            v_loss = 0.0
            with torch.no_grad():
                for Xb, Yb in val_loader:
                    v_loss += criterion(model(Xb.to(device)), Yb.to(device)).item() * len(Xb)
            log.info(
                "  epoch %2d/%d  train_loss=%.4f  val_loss=%.4f",
                epoch, epochs,
                t_loss / len(train_loader.dataset),
                v_loss / len(val_loader.dataset),
            )

    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for Xb, Yb in val_loader:
            preds.append(model(Xb.to(device)).cpu().numpy())
            trues.append(Yb.numpy())
    return np.concatenate(trues), np.concatenate(preds)


# ---------------------------------------------------------------------------
# NN training wrappers
# ---------------------------------------------------------------------------

def train_1dcnn(
    X_tr: np.ndarray, Y_tr: np.ndarray,
    X_val: np.ndarray, Y_val: np.ndarray,
    x_scaler: StandardScaler,
    y_scaler: StandardScaler,
    device: torch.device,
) -> None:
    """Train 1D-CNN and report metrics in original (g/kg) scale.

    Args:
        X_tr: (N_tr, 11) training features.
        Y_tr: (N_tr, 2) training targets.
        X_val: Validation features.
        Y_val: Validation targets (original scale).
        x_scaler: Fitted X scaler.
        y_scaler: Fitted Y scaler.
        device: Compute device.
    """
    log.info("Training 1D-CNN (%d train, %d val) ...", len(X_tr), len(X_val))
    Xtr_s = x_scaler.transform(X_tr).astype(np.float32)
    Ytr_s = y_scaler.transform(Y_tr).astype(np.float32)
    Xvl_s = x_scaler.transform(X_val).astype(np.float32)
    Yvl_s = y_scaler.transform(Y_val).astype(np.float32)

    tr_dl = DataLoader(
        TensorDataset(torch.from_numpy(Xtr_s), torch.from_numpy(Ytr_s)),
        batch_size=BATCH_1D, shuffle=True, num_workers=0,
    )
    vl_dl = DataLoader(
        TensorDataset(torch.from_numpy(Xvl_s), torch.from_numpy(Yvl_s)),
        batch_size=BATCH_1D * 2, shuffle=False, num_workers=0,
    )

    model = CNN1D()
    y_true_s, y_pred_s = _nn_train_eval(model, tr_dl, vl_dl, device, EPOCHS_1D)
    log_metrics("1D-CNN", y_scaler.inverse_transform(y_true_s), y_scaler.inverse_transform(y_pred_s))

    torch.save(model.state_dict(), OUTPUTS / "cnn1d.pt")
    log.info("  saved → outputs/models/cnn1d.pt")


def train_2dcnn(
    x_scaler: StandardScaler,
    y_scaler: StandardScaler,
    device: torch.device,
) -> None:
    """Train 2D-CNN on spatial patches and report metrics in original (g/kg) scale.

    Args:
        x_scaler: Fitted X scaler (applied to raster pixels).
        y_scaler: Fitted Y scaler (applied to label rasters).
        device: Compute device.
    """
    log.info("Building 2D-CNN patch datasets ...")
    patch_datasets = []
    for region in REGIONS:
        s2_scaled, labels_scaled = load_rasters_for_patches(region, x_scaler, y_scaler)
        ds = PatchDataset(s2_scaled, labels_scaled)
        log.info("  [%s] %d valid patches", region, len(ds))
        patch_datasets.append(ds)

    full_ds = ConcatDataset(patch_datasets)
    n_val = int(len(full_ds) * VAL_FRAC)
    n_tr = len(full_ds) - n_val
    tr_ds, vl_ds = torch.utils.data.random_split(
        full_ds, [n_tr, n_val], generator=torch.Generator().manual_seed(SEED),
    )
    log.info("Training 2D-CNN (%d train, %d val) ...", n_tr, n_val)

    tr_dl = DataLoader(tr_ds, batch_size=BATCH_2D, shuffle=True,  num_workers=0)
    vl_dl = DataLoader(vl_ds, batch_size=BATCH_2D * 2, shuffle=False, num_workers=0)

    model = CNN2D()
    y_true_s, y_pred_s = _nn_train_eval(model, tr_dl, vl_dl, device, EPOCHS_2D)
    log_metrics("2D-CNN", y_scaler.inverse_transform(y_true_s), y_scaler.inverse_transform(y_pred_s))

    torch.save(model.state_dict(), OUTPUTS / "cnn2d.pt")
    log.info("  saved → outputs/models/cnn2d.pt")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Train all 4 models and save to outputs/models/."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Device: %s", device)

    log.info("Loading pixel data ...")
    X, Y = load_pixel_data()
    log.info("  total: %d samples  X=%s  Y=%s", len(X), X.shape, Y.shape)

    X_tr, X_val, Y_tr, Y_val = train_test_split(X, Y, test_size=VAL_FRAC, random_state=SEED)
    log.info("  train=%d  val=%d", len(X_tr), len(X_val))

    x_scaler = StandardScaler().fit(X_tr)
    y_scaler = StandardScaler().fit(Y_tr)
    joblib.dump(x_scaler, OUTPUTS / "x_scaler.pkl")
    joblib.dump(y_scaler, OUTPUTS / "y_scaler.pkl")

    train_xgboost(X_tr, Y_tr, X_val, Y_val)
    train_rf(X_tr, Y_tr, X_val, Y_val)
    train_1dcnn(X_tr, Y_tr, X_val, Y_val, x_scaler, y_scaler, device)

    # Free pixel arrays before loading rasters for 2D-CNN
    del X, X_tr, X_val, Y_tr, Y_val

    train_2dcnn(x_scaler, y_scaler, device)

    log.info("All models trained. Outputs in outputs/models/")


if __name__ == "__main__":
    main()
