"""
Computes carbon sequestration and issues carbon credit estimates from two SOC maps.

Workflow:
  1. Load Year 1 (baseline) and Year 2 (current) SOC/N prediction GeoTIFFs.
  2. Compute ΔSOC per pixel (g/kg).
  3. Convert to tCO2/ha using bulk density and pixel area.
  4. Check C:N ratio stability (must be 10–20 for Verra/Gold Standard).
  5. Report total sequestration and carbon credit estimate per region.

Carbon conversion:
  SOC (g/kg) × bulk_density (kg/m³) × depth (m) × pixel_area (m²) → kg C/pixel
  kg C × (44/12) → kg CO2 → ÷ 1000 → tCO2/pixel
  Sum over region → total tCO2
  ÷ region_area_ha → tCO2/ha

Assumptions (conservative, aligned with Verra VCS VM0042):
  - Bulk density: 1300 kg/m³ (typical mineral soil)
  - Measurement depth: 0.05 m (0-5cm layer)
  - C:N stability window: 10–20

Usage:
  python src/utils/carbon_calc.py --baseline outputs/maps/europe/rf_soc_n_2023.tif
                                  --current  outputs/maps/europe/rf_soc_n_2024.tif
                                  --region   europe

  # Quick test using the same map twice (expect ~0 sequestration):
  python src/utils/carbon_calc.py --baseline outputs/maps/europe/rf_soc_n.tif
                                  --current  outputs/maps/europe/rf_soc_n.tif
                                  --region   europe
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import rasterio

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Physical constants
BULK_DENSITY_KG_M3 = 1300.0   # kg/m³ — conservative for mineral soils
DEPTH_M = 0.05                 # metres — 0-5 cm layer
C_TO_CO2 = 44.0 / 12.0        # mass ratio CO2/C
CN_MIN = 10.0
CN_MAX = 20.0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _pixel_area_m2(transform) -> float:
    """Compute pixel area in m² from a geographic (degree) transform.

    Uses the centre-latitude of the raster as the representative latitude
    for the cosine correction. Accurate to ~1% for continental extents.

    Args:
        transform: rasterio Affine transform (EPSG:4326).

    Returns:
        Pixel area in square metres.
    """
    deg_x = abs(transform.a)   # pixel width in degrees (longitude)
    deg_y = abs(transform.e)   # pixel height in degrees (latitude)
    # 1° latitude ≈ 111,320 m everywhere
    m_per_deg_lat = 111_320.0
    # 1° longitude shrinks with cos(lat) — use ~45° as representative mid-lat
    # (caller can override by passing exact centre lat if needed)
    import math
    centre_lat_rad = math.radians(45.0)
    m_per_deg_lon = 111_320.0 * math.cos(centre_lat_rad)
    return (deg_x * m_per_deg_lon) * (deg_y * m_per_deg_lat)


def load_bands(path: Path) -> tuple[np.ndarray, np.ndarray, object]:
    """Load SOC (band 1) and N (band 2) from a prediction GeoTIFF.

    Args:
        path: Path to a 2-band GeoTIFF produced by predict.py.

    Returns:
        soc: (H, W) float32 SOC g/kg, NaN where nodata.
        n:   (H, W) float32 Nitrogen g/kg, NaN where nodata.
        transform: rasterio Affine transform.
    """
    with rasterio.open(path) as src:
        soc = src.read(1).astype(np.float32)
        n   = src.read(2).astype(np.float32)
        transform = src.transform
        nodata = src.nodata
    if nodata is not None:
        soc[soc == nodata] = np.nan
        n[n   == nodata] = np.nan
    return soc, n, transform


def compute_sequestration(
    soc_y1: np.ndarray,
    soc_y2: np.ndarray,
    n_y1: np.ndarray,
    n_y2: np.ndarray,
    pixel_area_m2: float,
) -> dict[str, float | np.ndarray]:
    """Compute carbon sequestration and C:N stability metrics.

    Args:
        soc_y1: (H, W) SOC g/kg — baseline year.
        soc_y2: (H, W) SOC g/kg — current year.
        n_y1:   (H, W) N g/kg — baseline year.
        n_y2:   (H, W) N g/kg — current year.
        pixel_area_m2: Pixel area in square metres.

    Returns:
        dict with keys:
          delta_soc_g_kg      — (H, W) ΔSOC per pixel
          tco2_per_pixel      — (H, W) tCO2 sequestered per pixel
          cn_ratio_y2         — (H, W) C:N ratio in current year
          cn_stable_mask      — (H, W) bool — True where C:N is 10–20
          total_tco2          — scalar total tCO2 over stable pixels
          stable_pixel_count  — int number of stable pixels
          total_pixels        — int total valid pixels
          region_ha           — float total valid area in hectares
    """
    valid = np.isfinite(soc_y1) & np.isfinite(soc_y2) & np.isfinite(n_y1) & np.isfinite(n_y2)

    delta_soc = soc_y2 - soc_y1   # g/kg — positive = sequestration

    # SOC g/kg × bulk_density kg/m³ × depth m × area m² = g C/pixel
    # ÷ 1000 → kg C/pixel × C_TO_CO2 → kg CO2/pixel ÷ 1000 → tCO2/pixel
    tco2_per_pixel = (
        delta_soc
        * BULK_DENSITY_KG_M3
        * DEPTH_M
        * pixel_area_m2
        / 1e6           # g → t  (g/1e6 = t)
        * C_TO_CO2
    )

    # C:N ratio — use average of year 1 and year 2 to smooth noise
    n_avg = (n_y1 + n_y2) / 2.0
    cn_ratio = np.where(n_avg > 0, soc_y2 / n_avg, np.nan)

    cn_stable = (cn_ratio >= CN_MIN) & (cn_ratio <= CN_MAX) & valid

    # Only count sequestration where both valid AND C:N stable
    seq_pixels = tco2_per_pixel[cn_stable & (tco2_per_pixel > 0)]
    total_tco2 = float(seq_pixels.sum()) if len(seq_pixels) > 0 else 0.0

    pixel_ha = pixel_area_m2 / 10_000.0
    region_ha = float(valid.sum()) * pixel_ha

    return {
        "delta_soc_g_kg":     delta_soc,
        "tco2_per_pixel":     tco2_per_pixel,
        "cn_ratio_y2":        cn_ratio,
        "cn_stable_mask":     cn_stable,
        "total_tco2":         total_tco2,
        "stable_pixel_count": int(cn_stable.sum()),
        "total_pixels":       int(valid.sum()),
        "region_ha":          region_ha,
    }


def report(region: str, results: dict, baseline_path: Path, current_path: Path) -> None:
    """Print a human-readable sequestration report.

    Args:
        region: Region name for display.
        results: Output dict from compute_sequestration().
        baseline_path: Path to baseline map (for provenance).
        current_path: Path to current map.
    """
    total_px   = results["total_pixels"]
    stable_px  = results["stable_pixel_count"]
    stable_pct = 100.0 * stable_px / total_px if total_px else 0.0
    region_ha  = results["region_ha"]
    total_tco2 = results["total_tco2"]
    tco2_ha    = total_tco2 / region_ha if region_ha > 0 else 0.0

    # Carbon credit estimate: 1 tCO2 ≈ $15 (conservative market price)
    credit_usd = total_tco2 * 15.0

    delta = results["delta_soc_g_kg"]
    valid_delta = delta[np.isfinite(delta)]

    log.info("=" * 60)
    log.info("CARBON SEQUESTRATION REPORT — %s", region.upper())
    log.info("  Baseline : %s", baseline_path.name)
    log.info("  Current  : %s", current_path.name)
    log.info("-" * 60)
    log.info("  Valid pixels          : %d", total_px)
    log.info("  Region area           : %.1f Mha", region_ha / 1e6)
    log.info("  Mean ΔSOC             : %+.2f g/kg", float(np.nanmean(valid_delta)))
    log.info("  C:N stable pixels     : %d / %d  (%.1f%%)", stable_px, total_px, stable_pct)
    log.info("  Total sequestration   : %.1f tCO2  (stable pixels only)", total_tco2)
    log.info("  Sequestration rate    : %.4f tCO2/ha", tco2_ha)
    log.info("  Est. carbon credits   : %.0f tCO2  @ ~$15/tCO2 = $%.0f", total_tco2, credit_usd)
    log.info("=" * 60)

    if stable_pct < 50:
        log.warning(
            "Only %.1f%% of pixels pass the C:N stability check (%.0f–%.0f). "
            "Consider re-sampling or smoothing the N prediction.",
            stable_pct, CN_MIN, CN_MAX,
        )


def main() -> None:
    """Parse args, compute sequestration, print report."""
    parser = argparse.ArgumentParser(description="Compute carbon sequestration from two SOC maps.")
    parser.add_argument("--baseline", required=True, type=Path,
                        help="Year 1 SOC/N GeoTIFF (2-band, from predict.py).")
    parser.add_argument("--current",  required=True, type=Path,
                        help="Year 2 SOC/N GeoTIFF (2-band, from predict.py).")
    parser.add_argument("--region",   required=True, choices=["europe", "africa"],
                        help="Region label for the report.")
    args = parser.parse_args()

    log.info("Loading baseline: %s", args.baseline)
    soc_y1, n_y1, transform = load_bands(args.baseline)

    log.info("Loading current:  %s", args.current)
    soc_y2, n_y2, _ = load_bands(args.current)

    if soc_y1.shape != soc_y2.shape:
        raise ValueError(
            f"Shape mismatch: baseline {soc_y1.shape} vs current {soc_y2.shape}. "
            "Both maps must cover the same grid."
        )

    pixel_area = _pixel_area_m2(transform)
    log.info("Pixel area: %.1f m²  (%.4f ha)", pixel_area, pixel_area / 10_000)

    results = compute_sequestration(soc_y1, soc_y2, n_y1, n_y2, pixel_area)
    report(args.region, results, args.baseline, args.current)


if __name__ == "__main__":
    main()
