"""
Fetches SoilGrids 2.0 SOC and Nitrogen layers via ISRIC WCS API.
Outputs GeoTIFFs to data/processed/{region}/{variable}/
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_WCS_BASE = "https://maps.isric.org/mapserv"
_NATIVE_RES = 0.002083333   # ~250 m in degrees
_SERVER_MAX = 4096           # safe pixel cap per dimension (server OOMs above ~8k for large bboxes)

LAYERS: dict[str, list[str]] = {
    "soc": ["soc_0-5cm_mean", "soc_5-15cm_mean", "soc_15-30cm_mean"],
    "nitrogen": ["nitrogen_0-5cm_mean", "nitrogen_5-15cm_mean", "nitrogen_15-30cm_mean"],
}

REGIONS: dict[str, tuple[float, float, float, float]] = {
    "europe": (-25.0, 34.0, 45.0, 72.0),   # west, south, east, north
    "africa": (-20.0, -35.0, 55.0, 38.0),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _build_url(
    variable: str,
    coverage_id: str,
    bbox: tuple[float, float, float, float],
) -> str:
    """Build an ISRIC WCS 1.0.0 GetCoverage URL for a given layer and bbox.

    Uses square pixels sized by the longest bbox span so both dimensions
    stay within _SERVER_MAX, never finer than the native ~250 m grid.

    Args:
        variable: SoilGrids map name ('soc' or 'nitrogen').
        coverage_id: WCS coverage ID (e.g. 'soc_0-5cm_mean').
        bbox: (west, south, east, north) in EPSG:4326.

    Returns:
        Full WCS GetCoverage request URL.
    """
    west, south, east, north = bbox
    res = max(_NATIVE_RES, max(east - west, north - south) / _SERVER_MAX)
    resx = resy = res
    return (
        f"{_WCS_BASE}?map=/map/{variable}.map"
        f"&SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage"
        f"&COVERAGE={coverage_id}"
        f"&CRS=EPSG:4326"
        f"&BBOX={west},{south},{east},{north}"
        f"&RESX={resx:.9f}&RESY={resy:.9f}"
        f"&FORMAT=GEOTIFF_INT16"
    )


def fetch_coverage(
    variable: str,
    coverage_id: str,
    bbox: tuple[float, float, float, float],
    dst_path: Path,
) -> None:
    """Download one WCS coverage and write it as a GeoTIFF.

    Streams the response to disk so large regions don't blow up memory.
    Raises RuntimeError if the server returns an XML/HTML error body
    instead of a TIFF.

    Args:
        variable: SoilGrids map name ('soc' or 'nitrogen').
        coverage_id: WCS coverage ID (e.g. 'soc_0-5cm_mean').
        bbox: (west, south, east, north) in EPSG:4326.
        dst_path: Output path for the GeoTIFF.
    """
    url = _build_url(variable, coverage_id, bbox)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, 4):
        try:
            with requests.get(url, stream=True, timeout=300) as resp:
                resp.raise_for_status()

                content_type = resp.headers.get("Content-Type", "")
                if "xml" in content_type or "html" in content_type:
                    raise RuntimeError(
                        f"WCS returned an error for {coverage_id}:\n{resp.text[:500]}"
                    )

                bytes_written = 0
                with open(dst_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=1024 * 1024):
                        f.write(chunk)
                        bytes_written += len(chunk)

            log.info("  %.1f MB  →  %s", bytes_written / 1e6, dst_path.relative_to(PROJECT_ROOT))
            return

        except requests.exceptions.HTTPError as exc:
            if attempt == 3:
                raise
            wait = 30 * attempt
            log.warning("  attempt %d failed (%s) — retrying in %ds", attempt, exc, wait)
            time.sleep(wait)


def main() -> None:
    """Fetch all SoilGrids SOC and Nitrogen layers for Europe and Africa."""
    processed_root = PROJECT_ROOT / "data" / "processed"

    jobs: list[tuple[str, str, tuple[float, float, float, float], Path]] = []
    for variable, coverage_ids in LAYERS.items():
        for coverage_id in coverage_ids:
            for region, bbox in REGIONS.items():
                dst_path = processed_root / region / variable / f"{coverage_id}.tif"
                jobs.append((variable, coverage_id, bbox, dst_path))

    log.info(
        "Starting %d fetch jobs (%d layers × %d regions)",
        len(jobs),
        len(jobs) // len(REGIONS),
        len(REGIONS),
    )

    for i, (variable, coverage_id, bbox, dst_path) in enumerate(jobs, 1):
        region = dst_path.parent.parent.name
        if dst_path.exists():
            log.info("[%d/%d] Skipping  %-30s  region=%s (already exists)", i, len(jobs), coverage_id, region)
            continue
        log.info("[%d/%d] Fetching  %-30s  region=%s", i, len(jobs), coverage_id, region)
        fetch_coverage(variable, coverage_id, bbox, dst_path)
        log.info("[%d/%d] Done", i, len(jobs))

    log.info(
        "All done. %d GeoTIFFs written to %s",
        len(jobs),
        processed_root.relative_to(PROJECT_ROOT),
    )


if __name__ == "__main__":
    main()
