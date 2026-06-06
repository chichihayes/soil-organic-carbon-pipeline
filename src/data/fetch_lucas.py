"""
Prepares LUCAS 2018 Topsoil data for model evaluation.

LUCAS (Land Use/Cover Area frame Survey) is the EU's field soil survey —
~19,000 lab-measured soil samples across Europe with GPS coordinates.
It is the real ground truth we use to validate model accuracy.

HOW TO GET THE DATA (free, requires registration):
  1. Go to: https://esdac.jrc.ec.europa.eu/content/lucas-2018-topsoil-data
  2. Register for a free ESDAC account and request access
  3. Download the ZIP file — it contains LUCAS-SOIL-2018.csv
  4. Place LUCAS-SOIL-2018.csv in:  data/raw/lucas/LUCAS-SOIL-2018.csv
  5. Run this script: python src/data/fetch_lucas.py

This script will:
  - Parse the raw CSV
  - Filter to valid OC (SOC) and N measurements
  - Clip to the Europe bounding box
  - Save a cleaned CSV to data/raw/lucas/lucas_clean.csv

Output columns:
  lat       — GPS latitude (EPSG:4326)
  lon       — GPS longitude (EPSG:4326)
  soc_g_kg  — Organic carbon (g/kg) — matches our model's SOC output
  n_g_kg    — Total nitrogen (g/kg) — matches our model's N output
  point_id  — LUCAS point identifier (for traceability)
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_LUCAS_DIR = PROJECT_ROOT / "data" / "raw" / "lucas"
RAW_CSV = RAW_LUCAS_DIR / "LUCAS-SOIL-2018.csv"
CLEAN_CSV = RAW_LUCAS_DIR / "lucas_clean.csv"

# Europe bounding box (matches CLAUDE.md)
EUROPE_BBOX = {"west": -25.0, "east": 45.0, "south": 34.0, "north": 72.0}

# LUCAS 2018 column names
COL_ID = "POINTID"
COL_LAT = "GPS_LAT"
COL_LON = "GPS_LONG"
COL_LAT_TH = "TH_LAT"    # fallback if GPS coords missing
COL_LON_TH = "TH_LONG"
COL_OC = "OC"             # organic carbon (g/kg) = SOC
COL_N = "N"               # total nitrogen (g/kg)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _check_raw_exists() -> None:
    """Abort with clear instructions if the raw CSV has not been downloaded."""
    if not RAW_CSV.exists():
        log.error("LUCAS raw CSV not found at: %s", RAW_CSV)
        log.error("")
        log.error("To download (free, requires registration):")
        log.error("  1. Visit https://esdac.jrc.ec.europa.eu/content/lucas-2018-topsoil-data")
        log.error("  2. Register for a free ESDAC account and request access")
        log.error("  3. Download the ZIP and extract LUCAS-SOIL-2018.csv")
        log.error("  4. Place it at: %s", RAW_CSV)
        log.error("  5. Re-run this script")
        sys.exit(1)


def process_lucas(raw_path: Path, clean_path: Path) -> pd.DataFrame:
    """Parse and clean the raw LUCAS 2018 CSV.

    Steps:
      - Use GPS coordinates; fall back to theoretical grid points if missing.
      - Drop rows with missing or non-positive OC / N values.
      - Clip to the Europe bounding box.
      - Rename columns to match our pipeline conventions.

    Args:
        raw_path: Path to LUCAS-SOIL-2018.csv.
        clean_path: Output path for the cleaned CSV.

    Returns:
        Cleaned DataFrame with columns [point_id, lat, lon, soc_g_kg, n_g_kg].
    """
    log.info("Loading raw LUCAS CSV: %s", raw_path)
    df = pd.read_csv(raw_path, low_memory=False)
    log.info("  raw rows: %d  columns: %d", len(df), len(df.columns))

    # Use GPS coordinates, fall back to theoretical points
    if COL_LAT in df.columns and COL_LON in df.columns:
        df["lat"] = pd.to_numeric(df[COL_LAT], errors="coerce")
        df["lon"] = pd.to_numeric(df[COL_LON], errors="coerce")
        # Fill missing GPS with theoretical coordinates
        if COL_LAT_TH in df.columns:
            mask = df["lat"].isna()
            df.loc[mask, "lat"] = pd.to_numeric(df.loc[mask, COL_LAT_TH], errors="coerce")
            df.loc[mask, "lon"] = pd.to_numeric(df.loc[mask, COL_LON_TH], errors="coerce")
    elif COL_LAT_TH in df.columns:
        df["lat"] = pd.to_numeric(df[COL_LAT_TH], errors="coerce")
        df["lon"] = pd.to_numeric(df[COL_LON_TH], errors="coerce")
    else:
        raise KeyError(f"No coordinate columns found. Expected {COL_LAT}/{COL_LON} or {COL_LAT_TH}/{COL_LON_TH}.")

    df["soc_g_kg"] = pd.to_numeric(df[COL_OC], errors="coerce")
    df["n_g_kg"]   = pd.to_numeric(df[COL_N],  errors="coerce")
    df["point_id"] = df[COL_ID].astype(str)

    before = len(df)
    df = df.dropna(subset=["lat", "lon", "soc_g_kg", "n_g_kg"])
    df = df[(df["soc_g_kg"] > 0) & (df["n_g_kg"] > 0)]
    log.info("  after dropping missing/invalid values: %d rows (removed %d)", len(df), before - len(df))

    # Clip to Europe bbox
    bbox = EUROPE_BBOX
    df = df[
        (df["lon"] >= bbox["west"]) & (df["lon"] <= bbox["east"]) &
        (df["lat"] >= bbox["south"]) & (df["lat"] <= bbox["north"])
    ]
    log.info("  after clipping to Europe bbox: %d rows", len(df))

    out = df[["point_id", "lat", "lon", "soc_g_kg", "n_g_kg"]].reset_index(drop=True)

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(clean_path, index=False)
    log.info("Saved clean CSV → %s  (%d points)", clean_path.relative_to(PROJECT_ROOT), len(out))

    log.info("SOC: %.1f – %.1f g/kg  (mean %.1f)", out["soc_g_kg"].min(), out["soc_g_kg"].max(), out["soc_g_kg"].mean())
    log.info("N:   %.3f – %.3f g/kg  (mean %.3f)", out["n_g_kg"].min(), out["n_g_kg"].max(), out["n_g_kg"].mean())

    return out


def main() -> None:
    """Check for raw LUCAS CSV and produce cleaned output."""
    _check_raw_exists()

    if CLEAN_CSV.exists():
        log.info("Clean CSV already exists: %s", CLEAN_CSV.relative_to(PROJECT_ROOT))
        log.info("Delete it and re-run to reprocess.")
        return

    process_lucas(RAW_CSV, CLEAN_CSV)


if __name__ == "__main__":
    main()
