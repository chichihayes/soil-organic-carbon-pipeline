"""
Fetches Sentinel-2 L2A Surface Reflectance composites via Google Earth Engine.

Workflow:
  1. Build Jul-Oct median composites (2018-2020, cloud < 10%) for each region.
  2. Export to Google Drive (async — GEE requirement for continental-scale images).
  3. Poll until tasks complete.
  4. Download from Drive to data/processed/{region}/sentinel2/ using stored GEE credentials.

Prerequisites:
  pip install earthengine-api
  earthengine authenticate
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import ee
from ee import oauth as ee_oauth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_GEE_CREDS_FILE = Path.home() / ".config" / "earthengine" / "credentials"


def _gee_config_project() -> str | None:
    """Read the GEE project from the earthengine credentials file."""
    if not _GEE_CREDS_FILE.exists():
        return None
    return json.loads(_GEE_CREDS_FILE.read_text()).get("project")

BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B11", "B12"]
DATE_START = "2018-07-01"
DATE_END = "2020-10-31"
SCALE = 2000          # metres ≈ 0.0183° — matches SoilGrids resolution
MAX_CLOUD_PCT = 10
DRIVE_FOLDER = "soc_carbon_sentinel2"

REGIONS: dict[str, list[float]] = {
    "europe": [-25.0, 34.0, 45.0, 72.0],   # west, south, east, north
    "africa": [-20.0, -35.0, 55.0, 38.0],
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# GEE image building
# ---------------------------------------------------------------------------

def _add_indices(img: ee.Image) -> ee.Image:
    """Add NDVI and BSI bands to a Sentinel-2 image."""
    ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    bsi = img.expression(
        "((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))",
        {
            "B11": img.select("B11"),
            "B4":  img.select("B4"),
            "B8":  img.select("B8"),
            "B2":  img.select("B2"),
        },
    ).rename("BSI")
    return img.addBands([ndvi, bsi])


def build_composite(region_name: str, bbox: list[float]) -> ee.Image:
    """Build a Sentinel-2 median composite for one region.

    Filters to Jul-Oct (bare soil season) across 2018-2020, <10% cloud cover.
    Computes NDVI and BSI per image before taking the median.

    Args:
        region_name: Label used only for logging.
        bbox: [west, south, east, north] in EPSG:4326.

    Returns:
        Median composite ee.Image: bands B2-B12, NDVI, BSI.
    """
    region = ee.Geometry.Rectangle(bbox)
    all_bands = BANDS + ["NDVI", "BSI"]

    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(DATE_START, DATE_END)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PCT))
        .filter(ee.Filter.calendarRange(7, 10, "month"))
        .map(_add_indices)
        .select(all_bands)
    )

    count = collection.size().getInfo()
    log.info("  [%s] %d images pass filters", region_name, count)
    if count == 0:
        raise RuntimeError(
            f"No images found for {region_name}. Check date range, bbox, and cloud filter."
        )

    return collection.median().clip(region).toFloat()


# ---------------------------------------------------------------------------
# GEE export
# ---------------------------------------------------------------------------

def submit_export(
    image: ee.Image,
    region_name: str,
    bbox: list[float],
) -> ee.batch.Task:
    """Submit an async export of one composite to Google Drive.

    Args:
        image: Composite ee.Image to export.
        region_name: Used in Drive file and task names.
        bbox: [west, south, east, north] in EPSG:4326.

    Returns:
        The started GEE batch task.
    """
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=f"sentinel2_{region_name}",
        folder=DRIVE_FOLDER,
        fileNamePrefix=f"sentinel2_{region_name}",
        region=ee.Geometry.Rectangle(bbox),
        scale=SCALE,
        crs="EPSG:4326",
        fileFormat="GeoTIFF",
        maxPixels=int(1e10),
    )
    task.start()
    return task


def monitor_tasks(tasks: dict[str, ee.batch.Task]) -> dict[str, bool]:
    """Poll all GEE tasks every 60 s until each is COMPLETED or FAILED.

    Args:
        tasks: Mapping of region_name → GEE batch task.

    Returns:
        Mapping of region_name → True (completed) / False (failed).
    """
    pending = dict(tasks)
    results: dict[str, bool] = {}

    while pending:
        for region, task in list(pending.items()):
            status = task.status()
            state = status["state"]
            if state == "COMPLETED":
                log.info("  [%s] export complete", region)
                results[region] = True
                del pending[region]
            elif state == "FAILED":
                log.error("  [%s] export FAILED: %s", region, status.get("error_message", "—"))
                results[region] = False
                del pending[region]
            else:
                log.info("  [%s] %s ...", region, state)
        if pending:
            time.sleep(60)

    return results


# ---------------------------------------------------------------------------
# Drive download
# ---------------------------------------------------------------------------

def _drive_service() -> object:
    """Build a Drive API client reusing the stored GEE OAuth credentials.

    Uses the EE OAuth client ID/secret to refresh the token — these are
    the same credentials earthengine authenticate stored.

    Returns:
        Authenticated googleapiclient Resource for Drive v3.
    """
    raw = json.loads(_GEE_CREDS_FILE.read_text())
    creds = Credentials(
        token=None,
        refresh_token=raw["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=ee_oauth.CLIENT_ID,
        client_secret=ee_oauth.CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def _download_file(service: object, file_id: str, dst_path: Path) -> None:
    """Stream a single Drive file to disk with progress logging.

    Args:
        service: Authenticated Drive API Resource.
        file_id: Google Drive file ID.
        dst_path: Local destination path.
    """
    request = service.files().get_media(fileId=file_id)
    with open(dst_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request, chunksize=8 * 1024 * 1024)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            log.info("    %s  %d%%", dst_path.name, int(status.progress() * 100))


def download_from_drive(region_name: str, dst_path: Path) -> None:
    """Download exported GeoTIFF(s) from Drive and save locally.

    GEE may split large exports into tiles. If multiple tiles are found,
    they are mosaicked with rasterio before saving.

    Args:
        region_name: Used to search Drive for files matching the export prefix.
        dst_path: Local path for the final GeoTIFF.
    """
    import rasterio
    from rasterio.merge import merge

    service = _drive_service()
    prefix = f"sentinel2_{region_name}"

    results = service.files().list(
        q=f"name contains '{prefix}' and trashed=false and mimeType='image/tiff'",
        fields="files(id, name)",
        orderBy="name",
    ).execute()
    tiles = results.get("files", [])

    if not tiles:
        raise FileNotFoundError(
            f"No Drive files matching '{prefix}*.tif'. "
            "Confirm the GEE export completed and folder is '{DRIVE_FOLDER}'."
        )

    log.info("  [%s] found %d tile(s) in Drive", region_name, len(tiles))
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if len(tiles) == 1:
        _download_file(service, tiles[0]["id"], dst_path)
        return

    # Multi-tile: download to a temp subfolder, then mosaic
    tmp_dir = dst_path.parent / f"_tmp_{region_name}"
    tmp_dir.mkdir(exist_ok=True)
    tmp_paths: list[Path] = []
    try:
        for tile in tiles:
            tmp_path = tmp_dir / tile["name"]
            _download_file(service, tile["id"], tmp_path)
            tmp_paths.append(tmp_path)

        log.info("  [%s] mosaicking %d tiles ...", region_name, len(tmp_paths))
        datasets = [rasterio.open(p) for p in tmp_paths]
        mosaic, transform = merge(datasets)
        profile = datasets[0].profile.copy()
        profile.update(
            width=mosaic.shape[2],
            height=mosaic.shape[1],
            transform=transform,
            compress="lzw",
        )
        for ds in datasets:
            ds.close()
        with rasterio.open(dst_path, "w", **profile) as out:
            out.write(mosaic)
    finally:
        for p in tmp_paths:
            p.unlink(missing_ok=True)
        if tmp_dir.exists():
            tmp_dir.rmdir()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Build, export, and download Sentinel-2 composites for Europe and Africa."""
    log.info("Initialising Google Earth Engine ...")
    project = os.environ.get("GEE_PROJECT") or _gee_config_project()
    if not project:
        raise RuntimeError(
            "No GEE project found. Either:\n"
            "  earthengine config set project YOUR_PROJECT_ID\n"
            "  or set GEE_PROJECT=YOUR_PROJECT_ID in .env"
        )
    log.info("  project: %s", project)
    ee.Initialize(project=project)

    # Check Drive first — skip export if file already exists there
    service = _drive_service()
    results: dict[str, bool] = {}
    tasks: dict[str, ee.batch.Task] = {}

    for region_name, bbox in REGIONS.items():
        fname = f"sentinel2_{region_name}.tif"
        existing = service.files().list(
            q=f'name="{fname}" and trashed=false',
            fields="files(id)",
        ).execute().get("files", [])

        if existing:
            log.info("[%s] Already in Drive — skipping export", region_name)
            results[region_name] = True
        else:
            log.info("[%s] Building composite ...", region_name)
            composite = build_composite(region_name, bbox)
            log.info("[%s] Submitting export to Drive folder '%s' ...", region_name, DRIVE_FOLDER)
            tasks[region_name] = submit_export(composite, region_name, bbox)
            log.info("[%s] Task submitted", region_name)

    if tasks:
        log.info("Monitoring %d export tasks (polling every 60 s) ...", len(tasks))
        results.update(monitor_tasks(tasks))

    processed_root = PROJECT_ROOT / "data" / "processed"
    for region_name, success in results.items():
        if not success:
            log.error("[%s] Skipping download — export failed", region_name)
            continue
        dst_path = processed_root / region_name / "sentinel2" / f"sentinel2_{region_name}.tif"
        log.info("[%s] Downloading from Drive -> %s ...", region_name, dst_path.relative_to(PROJECT_ROOT))
        download_from_drive(region_name, dst_path)
        log.info("[%s] Done", region_name)

    log.info("All done.")


if __name__ == "__main__":
    main()
