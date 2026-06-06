"""
Pairs SoilGrids SOC/Nitrogen labels with Sentinel-2 features to create ML training data.

Reprojects SoilGrids layers onto the Sentinel-2 grid, filters to valid pixels,
converts units, and saves an NPZ file per region.

Output: data/training/{region}/training_{region}.npz with keys:
  X          — (N, 11) float32: B2 B3 B4 B5 B6 B7 B8 B11 B12 NDVI BSI
  y_soc      — (N, 3)  float32: SOC g/kg at [0-5, 5-15, 15-30 cm]
  y_nitrogen — (N, 3)  float32: Nitrogen g/kg at [0-5, 5-15, 15-30 cm]

Unit conversions (per SoilGrids 2.0 spec):
  SOC:      stored in dg/kg  → divide by 10   to get g/kg
  Nitrogen: stored in cg/kg  → divide by 100  to get g/kg
  Nodata:   -32768 in source → masked out
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOC_LAYERS = ["soc_0-5cm_mean", "soc_5-15cm_mean", "soc_15-30cm_mean"]
NITROGEN_LAYERS = ["nitrogen_0-5cm_mean", "nitrogen_5-15cm_mean", "nitrogen_15-30cm_mean"]
SOILGRIDS_NODATA = -32768

REGIONS = ["europe", "africa"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _reproject_to_grid(
    src_path: Path,
    dst_transform,
    dst_width: int,
    dst_height: int,
    dst_crs,
) -> np.ndarray:
    """Read a SoilGrids GeoTIFF and reproject it onto a target grid.

    Args:
        src_path: Path to source Int16 SoilGrids GeoTIFF.
        dst_transform: Affine transform of the target grid.
        dst_width: Pixel width of the target grid.
        dst_height: Pixel height of the target grid.
        dst_crs: CRS of the target grid.

    Returns:
        2-D float32 array shaped (dst_height, dst_width).
        Nodata pixels are set to NaN.
    """
    with rasterio.open(src_path) as src:
        dst = np.empty((dst_height, dst_width), dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=dst,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=SOILGRIDS_NODATA,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return dst


def pair_region(region: str) -> None:
    """Build training NPZ for one region.

    Args:
        region: 'europe' or 'africa'.
    """
    processed = PROJECT_ROOT / "data" / "processed" / region
    training_dir = PROJECT_ROOT / "data" / "training" / region
    training_dir.mkdir(parents=True, exist_ok=True)
    out_path = training_dir / f"training_{region}.npz"

    if out_path.exists():
        log.info("[%s] Already exists — skipping", region)
        return

    s2_path = processed / "sentinel2" / f"sentinel2_{region}.tif"
    log.info("[%s] Loading Sentinel-2 from %s", region, s2_path.relative_to(PROJECT_ROOT))

    with rasterio.open(s2_path) as s2:
        dst_transform = s2.transform
        dst_crs = s2.crs
        dst_height, dst_width = s2.height, s2.width
        s2_data = s2.read().astype(np.float32)   # (11, H, W)

    log.info("[%s] S2 grid: %dx%d  bands=%d", region, dst_height, dst_width, s2_data.shape[0])

    # Valid S2 pixels: all 11 bands finite (NaN = ocean / no data)
    s2_valid = np.all(np.isfinite(s2_data), axis=0)   # (H, W)
    log.info("[%s] Valid S2 pixels: %d / %d", region, s2_valid.sum(), dst_height * dst_width)

    # Reproject and stack SoilGrids layers
    soc_stack = []
    for layer in SOC_LAYERS:
        src_path = processed / "soc" / f"{layer}.tif"
        log.info("[%s]   reprojecting %s ...", region, layer)
        arr = _reproject_to_grid(src_path, dst_transform, dst_width, dst_height, dst_crs)
        arr = arr / 10.0   # dg/kg → g/kg
        soc_stack.append(arr)

    nitrogen_stack = []
    for layer in NITROGEN_LAYERS:
        src_path = processed / "nitrogen" / f"{layer}.tif"
        log.info("[%s]   reprojecting %s ...", region, layer)
        arr = _reproject_to_grid(src_path, dst_transform, dst_width, dst_height, dst_crs)
        arr = arr / 100.0  # cg/kg → g/kg
        nitrogen_stack.append(arr)

    soc_cube = np.stack(soc_stack, axis=0)           # (3, H, W)
    n_cube   = np.stack(nitrogen_stack, axis=0)      # (3, H, W)

    # Valid SoilGrids pixels: no NaN in any depth layer for both SOC and N
    sg_valid = (
        np.all(np.isfinite(soc_cube), axis=0) &
        np.all(np.isfinite(n_cube), axis=0)
    )

    valid = s2_valid & sg_valid
    n_valid = int(valid.sum())
    log.info("[%s] Valid paired pixels: %d", region, n_valid)

    if n_valid == 0:
        raise RuntimeError(
            f"[{region}] No valid paired pixels found. "
            "Check that SoilGrids and Sentinel-2 grids overlap."
        )

    # Extract valid pixels → 2-D arrays (N, bands)
    X          = s2_data[:, valid].T.astype(np.float32)   # (N, 11)
    y_soc      = soc_cube[:, valid].T.astype(np.float32)   # (N, 3)
    y_nitrogen = n_cube[:, valid].T.astype(np.float32)     # (N, 3)

    log.info("[%s] X shape: %s  y_soc: %s  y_nitrogen: %s", region, X.shape, y_soc.shape, y_nitrogen.shape)
    log.info(
        "[%s] SOC range: %.1f – %.1f g/kg  (mean %.1f)",
        region, float(y_soc.min()), float(y_soc.max()), float(y_soc.mean()),
    )
    log.info(
        "[%s] N range:   %.3f – %.3f g/kg  (mean %.3f)",
        region, float(y_nitrogen.min()), float(y_nitrogen.max()), float(y_nitrogen.mean()),
    )

    np.savez_compressed(out_path, X=X, y_soc=y_soc, y_nitrogen=y_nitrogen)
    log.info("[%s] Saved → %s", region, out_path.relative_to(PROJECT_ROOT))


def main() -> None:
    """Pair SoilGrids and Sentinel-2 data for all regions."""
    for region in REGIONS:
        pair_region(region)
    log.info("All done.")


if __name__ == "__main__":
    main()
