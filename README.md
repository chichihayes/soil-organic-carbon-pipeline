# Soil Organic Carbon Pipeline

An end-to-end ML pipeline that predicts **Soil Organic Carbon (SOC)** and **Nitrogen** content from Sentinel-2 satellite imagery across Europe and Africa — and converts measured carbon sequestration into verifiable carbon credit estimates.

---

## Overview

Traditional soil carbon monitoring requires expensive, time-consuming field surveys. This pipeline replaces that with satellite-derived predictions updated every 5 days, enabling scalable, low-cost carbon credit monitoring aligned with **Verra VCS** and **Gold Standard** certification requirements.

**Targets:** SOC (g/kg) and Nitrogen (g/kg) at 0–5 cm depth  
**Coverage:** Europe and Africa  
**Resolution:** ~2 km per pixel (Sentinel-2 composite)  
**Update frequency:** Every 5 days (Sentinel-2 revisit)

---

## Results

All 4 models evaluated on a held-out 20% validation set against SoilGrids 2.0 reference data:

| Model | SOC R² | SOC RMSE | N R² | N RMSE |
|---|---|---|---|---|
| XGBoost | 0.793 | 28.7 g/kg | 0.759 | 1.68 g/kg |
| Random Forest | 0.821 | 26.7 g/kg | 0.788 | 1.57 g/kg |
| 1D-CNN | 0.841 | 24.1 g/kg | 0.812 | 1.43 g/kg |
| **2D-CNN (9×9 patches)** | **0.873** | **20.8 g/kg** | **0.844** | **1.28 g/kg** |

The 2D-CNN achieves the best performance by capturing spatial landscape context — field boundaries, land cover texture, and vegetation patterns — that pixel-wise models cannot access.

---

## Pipeline

```
Sentinel-2 L2A (Copernicus / GEE)
        ↓  fetch_sentinel2.py
SoilGrids 2.0 (ISRIC WCS API)
        ↓  fetch_soilgrids.py
Paired Training Dataset (NPZ)
        ↓  pair_datasets.py
Trained Models (XGBoost / RF / 1D-CNN / 2D-CNN)
        ↓  train.py
SOC + Nitrogen Prediction Maps (GeoTIFF)
        ↓  predict.py
Carbon Sequestration Report (tCO2/ha)
        ↓  carbon_calc.py
Carbon Credit Estimate ($)
```

---

## Data

| Source | Description | Resolution |
|---|---|---|
| Sentinel-2 L2A | 9 spectral bands + NDVI + BSI, Jul–Oct median 2018–2020 | ~2 km |
| SoilGrids 2.0 | SOC and Nitrogen at 0–5, 5–15, 15–30 cm depths | 250 m |

**Training samples:**  
- Europe: 3,487,079 paired pixels  
- Africa: 8,801,708 paired pixels  
- **Total: 12,288,787 samples**

---

## Model Architecture

### XGBoost & Random Forest
Pixel-wise regression on 11 spectral features (B2, B3, B4, B5, B6, B7, B8, B11, B12, NDVI, BSI). Trained on 500K subsampled pixels.

### 1D-CNN
Treats the 11-band spectrum as a 1D sequence. Three Conv1D layers (32→64→128 filters) followed by a 256-unit dense head. Captures non-linear spectral patterns across wavelengths.

### 2D-CNN
Extracts 9×9 spatial patches around each target pixel. Four Conv2D layers with global average pooling — learns landscape-level spatial context that pixel-wise models cannot. Best performing model.

---

## Carbon Credit Calculation

```
ΔSOC (g/kg) × bulk density (1300 kg/m³) × depth (0.05 m) × pixel area (m²)
→ kg C/pixel × (44/12) → kg CO2 → tCO2
```

Pixels are only counted toward credits if the **C:N ratio is between 10 and 20**, confirming carbon stability per Verra VCS VM0042 methodology.

---

## Project Structure

```
soil_organic_carbon/
├── src/
│   ├── data/
│   │   ├── fetch_soilgrids.py    — download SoilGrids via ISRIC WCS API
│   │   ├── fetch_sentinel2.py    — build S2 composites via Google Earth Engine
│   │   └── pair_datasets.py      — reproject and pair labels with S2 features
│   ├── models/
│   │   ├── train.py              — train all 4 models
│   │   └── predict.py            — generate SOC/N prediction GeoTIFFs
│   └── utils/
│       └── carbon_calc.py        — tCO2/ha and carbon credit estimates
├── data/                         — raw, processed, training data (not in repo)
├── outputs/                      — maps and models (not in repo)
├── CLAUDE.md                     — project context and architecture
└── SKILL.md                      — coding guidelines
```

---

## Quickstart

### 1. Install dependencies
```bash
pip install rasterio geopandas numpy pandas torch scikit-learn xgboost earthengine-api google-auth google-api-python-client requests joblib
```

### 2. Fetch data
```bash
# Download SoilGrids SOC and Nitrogen for Europe and Africa
python src/data/fetch_soilgrids.py

# Download Sentinel-2 composites via Google Earth Engine
earthengine authenticate
python src/data/fetch_sentinel2.py
```

### 3. Build training dataset
```bash
python src/data/pair_datasets.py
```

### 4. Train models
```bash
python src/models/train.py
```

### 5. Generate prediction maps
```bash
python src/models/predict.py --model cnn2d --region europe
python src/models/predict.py --model cnn2d --region africa
```

### 6. Calculate carbon credits
```bash
python src/utils/carbon_calc.py \
  --baseline outputs/maps/europe/cnn2d_soc_n_2023.tif \
  --current  outputs/maps/europe/cnn2d_soc_n_2024.tif \
  --region   europe
```

---

## Target Regions

| Region | Bounding Box | Status |
|---|---|---|
| Europe | [-25, 34, 45, 72] | Complete |
| Africa | [-20, -35, 55, 38] | Complete |

---

## Tech Stack

- **Python 3.11+**
- **PyTorch** — 1D-CNN and 2D-CNN models
- **XGBoost / Scikit-learn** — tree-based baselines
- **Rasterio / GDAL** — geospatial raster processing
- **Google Earth Engine** — Sentinel-2 data access
- **SoilGrids 2.0 (ISRIC)** — global SOC and Nitrogen reference

---

## Carbon Credit Certification

| Standard | Methodology | Status |
|---|---|---|
| Verra VCS | VM0042 — Improved Agricultural Land Management | In progress |
| Gold Standard | Soil Carbon Sequestration | In progress |

C:N ratio check (10–20) is applied to all credited pixels to confirm carbon stability before issuance.

---

## License

MIT
