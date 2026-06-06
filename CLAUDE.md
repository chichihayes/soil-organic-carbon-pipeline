# SOC Carbon Credit Monitoring Project

## Project Overview
This project builds an ML pipeline to predict Soil Organic Carbon (SOC) 
and Nitrogen content from Sentinel-2 satellite imagery for Europe and Africa. 
The end goal is carbon credit monitoring and issuance at scale.

## Business Goal
- Predict SOC (g/kg) and Nitrogen (g/kg) from satellite imagery
- Detect SOC change over time to quantify carbon sequestration
- Convert sequestration data into verifiable carbon credits (Verra/Gold Standard)
- Target markets: Europe (immediate), Africa (expansion)

## Tech Stack
- Python 3.11+
- GDAL / Rasterio — geospatial data processing
- GeoPandas — vector data handling
- NumPy / Pandas / SciPy — data manipulation
- PyTorch — deep learning models
- Scikit-learn / XGBoost — baseline ML models
- Sentinel-2 via Copernicus / Google Earth Engine — satellite imagery
- QGIS — visual inspection of rasters

## Data
### Raw Data (data/raw/)
- SoilGrids 2.0 (ISRIC, 2020) — global ML-predicted SOC and Nitrogen
  - SOC layers: 0-5cm, 5-15cm, 15-30cm (mean, VRT format)
  - Nitrogen layers: 0-5cm, 5-15cm, 15-30cm (mean, VRT format)
  - Units: SOC in dg/kg (divide by 10 for g/kg), Nitrogen in cg/kg
  - Resolution: 250m per pixel, global coverage
- Sentinel-2 L2A — 13 multispectral bands at 10m resolution
  - Source: Copernicus Open Access Hub / Google Earth Engine
  - Update frequency: every 5 days

### Key Facts
- SoilGrids is the BASELINE — it is not current ground truth
- Sentinel-2 is the LIVE layer — updated every 5 days
- ML model learns SOC/N patterns from SoilGrids + Sentinel-2 pairing
- Once trained, model runs on current Sentinel-2 to produce current SOC estimates

## Target Regions
- Europe: bbox [-25, 34, 45, 72] (west, south, east, north)
- Africa: bbox [-20, -35, 55, 38]

## ML Approach
- Input: Sentinel-2 bands (B02, B03, B04, B05, B06, B07, B08, B11, B12) + spectral indices (NDVI, BSI)
- Output: SOC (g/kg), Nitrogen (g/kg) per pixel
- Models: XGBoost (baseline), 1D-CNN (primary), Random Forest (comparison)
- Validation: R², RMSE, MAE against held-out LUCAS 2022 ground truth

## Carbon Credit Pipeline
- SOC map Year 1 = baseline
- SOC map Year 2 = current
- Difference = sequestration (tCO2/ha)
- Certification: Verra VCS / Gold Standard
- C:N ratio must be 10–20 to confirm carbon stability

## Folder Structure
```
soil_organic_carbon/
├── data/
│   ├── raw/soilgrids/soc/ and /nitrogen/
│   ├── raw/sentinel2/europe/ and /africa/
│   ├── processed/europe/ and /africa/
│   └── training/europe/ and /africa/
├── notebooks/          — exploration and experiments
├── src/
│   ├── data/           — clip, fetch, pair scripts
│   ├── models/         — train, predict, evaluate
│   └── utils/          — carbon calculations, visualization
├── outputs/            — maps, models, reports
└── tests/
```

## Coding Standards
- Python type annotations on all functions
- Docstrings on every function and class
- Unit tests for all data processing functions
- No hardcoded paths — use config or .env
- All file paths relative to project root

## Current Stage
Setting up project structure and clipping SoilGrids VRT files to 
Europe and Africa regions before pairing with Sentinel-2 imagery.
