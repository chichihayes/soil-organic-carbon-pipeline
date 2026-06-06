"""
Evaluates model predictions against LUCAS 2018 field measurements.

For each LUCAS soil sample point, extracts the model's SOC and Nitrogen
prediction at that GPS location from the prediction GeoTIFF, then computes
R², RMSE, and MAE against the real lab-measured values.

This is the true accuracy metric — not against SoilGrids (ML-predicted),
but against actual soil dug from the ground and analysed in a lab.

Prerequisites:
  1. Run fetch_lucas.py to produce data/raw/lucas/lucas_clean.csv
  2. Run predict.py to produce a SOC/N prediction GeoTIFF

Usage:
  python src/models/evaluate.py --model rf --region europe
  python src/models/evaluate.py --model cnn2d --region europe
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LUCAS_CSV = PROJECT_ROOT / "data" / "raw" / "lucas" / "lucas_clean.csv"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def load_lucas(region: str) -> pd.DataFrame:
    """Load cleaned LUCAS points and clip to the requested region bbox.

    Args:
        region: 'europe' or 'africa'.

    Returns:
        DataFrame with columns [point_id, lat, lon, soc_g_kg, n_g_kg].
    """
    bboxes = {
        "europe": {"west": -25.0, "east": 45.0, "south": 34.0, "north": 72.0},
        "africa": {"west": -20.0, "east": 55.0, "south": -35.0, "north": 38.0},
    }
    if not LUCAS_CSV.exists():
        raise FileNotFoundError(
            f"LUCAS CSV not found at {LUCAS_CSV}. "
            "Run: python src/data/fetch_lucas.py"
        )
    df = pd.read_csv(LUCAS_CSV)
    bbox = bboxes[region]
    df = df[
        (df["lon"] >= bbox["west"]) & (df["lon"] <= bbox["east"]) &
        (df["lat"] >= bbox["south"]) & (df["lat"] <= bbox["north"])
    ].reset_index(drop=True)
    log.info("Loaded %d LUCAS points for %s", len(df), region)
    return df


def sample_predictions(
    map_path: Path,
    lons: np.ndarray,
    lats: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract SOC and N predictions at LUCAS GPS locations from the GeoTIFF.

    Uses rasterio's sample() to read the pixel value at each lon/lat point.
    Points that fall outside the raster or on nodata pixels are returned as NaN.

    Args:
        map_path: Path to 2-band prediction GeoTIFF (band 1=SOC, band 2=N).
        lons: Array of longitudes.
        lats: Array of latitudes.

    Returns:
        pred_soc: (N,) float32 predicted SOC g/kg.
        pred_n:   (N,) float32 predicted N g/kg.
    """
    coords = list(zip(lons, lats))
    with rasterio.open(map_path) as src:
        samples = list(src.sample(coords, indexes=[1, 2]))
        nodata = src.nodata

    arr = np.array(samples, dtype=np.float32)   # (N, 2)
    pred_soc = arr[:, 0]
    pred_n   = arr[:, 1]

    if nodata is not None:
        pred_soc[pred_soc == nodata] = np.nan
        pred_n[pred_n   == nodata]   = np.nan

    # Also mask extreme/implausible values (raster edge artefacts)
    pred_soc[(pred_soc < 0) | (pred_soc > 1000)] = np.nan
    pred_n[(pred_n < 0)   | (pred_n > 100)]      = np.nan

    return pred_soc, pred_n


def evaluate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    label: str,
) -> dict[str, float]:
    """Compute R², RMSE, MAE for one output variable.

    Args:
        y_true: Ground truth values (LUCAS measured).
        y_pred: Model predictions.
        label: Variable name for logging (e.g. 'SOC', 'N').

    Returns:
        Dict with keys r2, rmse, mae.
    """
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    n = int(valid.sum())
    if n < 10:
        log.warning("Only %d valid paired points for %s — results unreliable.", n, label)

    yt = y_true[valid]
    yp = y_pred[valid]

    r2   = r2_score(yt, yp)
    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    mae  = mean_absolute_error(yt, yp)

    log.info(
        "  %-4s  n=%d  R²=%.3f  RMSE=%.3f g/kg  MAE=%.3f g/kg",
        label, n, r2, rmse, mae,
    )
    return {"r2": r2, "rmse": rmse, "mae": mae, "n": n}


def save_report(
    model: str,
    region: str,
    soc_metrics: dict,
    n_metrics: dict,
    lucas_df: pd.DataFrame,
    pred_soc: np.ndarray,
    pred_n: np.ndarray,
) -> Path:
    """Save a CSV with per-point predictions vs ground truth.

    Args:
        model: Model name string.
        region: Region string.
        soc_metrics: Dict from evaluate() for SOC.
        n_metrics: Dict from evaluate() for N.
        lucas_df: LUCAS DataFrame with ground truth.
        pred_soc: Model SOC predictions aligned to lucas_df rows.
        pred_n: Model N predictions aligned to lucas_df rows.

    Returns:
        Path to saved report CSV.
    """
    out_dir = OUTPUTS_DIR / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{model}_{region}_vs_lucas.csv"

    report_df = lucas_df.copy()
    report_df["pred_soc_g_kg"] = pred_soc
    report_df["pred_n_g_kg"]   = pred_n
    report_df["soc_error"]     = pred_soc - report_df["soc_g_kg"]
    report_df["n_error"]       = pred_n   - report_df["n_g_kg"]
    report_df.to_csv(out_path, index=False)

    log.info("Per-point report saved → %s", out_path.relative_to(PROJECT_ROOT))
    return out_path


def main() -> None:
    """Load LUCAS points, sample predictions, compute and report metrics."""
    parser = argparse.ArgumentParser(description="Evaluate model against LUCAS 2018 field data.")
    parser.add_argument("--model",  required=True, choices=["rf", "xgboost", "cnn1d", "cnn2d"],
                        help="Model whose prediction map to evaluate.")
    parser.add_argument("--region", required=True, choices=["europe", "africa"],
                        help="Region to evaluate.")
    args = parser.parse_args()

    map_path = OUTPUTS_DIR / "maps" / args.region / f"{args.model}_soc_n.tif"
    if not map_path.exists():
        raise FileNotFoundError(
            f"Prediction map not found: {map_path}. "
            f"Run: python src/models/predict.py --model {args.model} --region {args.region}"
        )

    lucas_df = load_lucas(args.region)
    if len(lucas_df) == 0:
        log.error("No LUCAS points found for region '%s'. Check bbox and CSV content.", args.region)
        return

    log.info("Sampling predictions from: %s", map_path.relative_to(PROJECT_ROOT))
    pred_soc, pred_n = sample_predictions(
        map_path,
        lucas_df["lon"].values,
        lucas_df["lat"].values,
    )

    matched = int(np.isfinite(pred_soc).sum())
    log.info("%d / %d LUCAS points matched to valid prediction pixels", matched, len(lucas_df))

    log.info("=" * 60)
    log.info("EVALUATION: %s vs LUCAS 2018  [%s]", args.model.upper(), args.region)
    log.info("-" * 60)
    soc_m = evaluate(lucas_df["soc_g_kg"].values, pred_soc, "SOC")
    n_m   = evaluate(lucas_df["n_g_kg"].values,   pred_n,   "N")
    log.info("=" * 60)

    # Certification threshold guidance
    for label, metrics in [("SOC", soc_m), ("N", n_m)]:
        r2 = metrics["r2"]
        status = "PASS" if r2 >= 0.85 else "BELOW TARGET"
        log.info("  %s R²=%.3f — Verra/Gold Standard target ≥0.85: %s", label, r2, status)

    save_report(args.model, args.region, soc_m, n_m, lucas_df, pred_soc, pred_n)


if __name__ == "__main__":
    main()
