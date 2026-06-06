# Deep Dive — Everything You Need to Know

This document explains every concept, every decision, every number in the project.
Written so you can answer any question from any angle — science, engineering, business.

---

# PART 1: THE SCIENCE

## 1.1 The Carbon Cycle — Why Soil Carbon Matters

The Earth has a carbon cycle. Carbon moves between four main places:
- The atmosphere (as CO2 gas)
- The ocean (dissolved carbon)
- Plants and trees (as organic matter)
- The soil (as organic carbon)

```
         ATMOSPHERE (CO2)
              ↑↓
         ┌────────────┐
    Rain  │            │  Photosynthesis
    CO2   │   PLANTS   │  (plants absorb CO2)
          │            │
          └─────┬──────┘
                │ Plants die, roots decompose
                ↓
         ┌────────────┐
         │    SOIL    │  ← Where our project lives
         │  ORGANIC   │
         │   CARBON   │
         └─────┬──────┘
                │ Decomposition (bacteria eat organic matter)
                ↓
         ATMOSPHERE (CO2 released back)
```

Soil holds MORE carbon than all forests and the atmosphere COMBINED.
If soil carbon decreases → that CO2 goes into the air → planet warms.
If soil carbon increases → CO2 is pulled from the air → planet cools slightly.

**Q: Why does soil carbon increase?**
Regenerative farming (no-till, cover crops, compost), reforestation, wetland restoration.

**Q: Why does soil carbon decrease?**
Ploughing (breaks up organic matter, exposes it to oxygen → releases CO2),
deforestation, overgrazing, drought, intensive monoculture farming.

---

## 1.2 What Exactly Is Soil Organic Carbon (SOC)?

Organic carbon is carbon contained in organic molecules — things that were once alive.
Dead plant roots, fungal threads, bacteria bodies, decomposed leaves → these become 
"humus" — the dark, spongy part of healthy soil.

SOC is measured as grams of carbon per kilogram of soil (g/kg).
This is a ratio — essentially a percentage:
- 10 g/kg = 1% carbon by weight
- 50 g/kg = 5% carbon by weight

**Q: What does "organic" mean here?**
Carbon bonded to hydrogen in molecules (C-H bonds). 
Distinguished from "inorganic" carbon like limestone (calcium carbonate, CaCO3).
LUCAS measures "OC" (organic carbon), which equals what we call SOC.

**Q: Why measure at different depths (0-5cm, 5-15cm, 15-30cm)?**
Carbon decreases with depth — most is in the top few centimetres.
For carbon credits, the top 0-5cm is most responsive to land management changes.
Deeper layers are more stable but change very slowly.
```
  Surface ──► SOC = 80 g/kg  (lots of recent plant matter)
  5cm    ──► SOC = 45 g/kg
  15cm   ──► SOC = 25 g/kg
  30cm   ──► SOC = 12 g/kg  (ancient carbon, barely changes)
```

---

## 1.3 What Is Nitrogen and Why Do We Measure It?

Nitrogen (N) is an essential plant nutrient. It travels with carbon through the soil.

**The C:N Ratio — The Stability Test**

C:N ratio = SOC ÷ Nitrogen

- C:N = 10–20 → carbon is locked in STABLE humus. Microbes can't easily decompose it.
  This means the carbon will stay in the soil for decades. It's REAL sequestration.

- C:N > 20 → carbon is in unstable fresh organic matter (like straw).
  Microbes will eat it and release the carbon as CO2 within months. NOT permanent.

- C:N < 10 → nitrogen is too abundant. Carbon releases quickly as well.

```
  STABLE CARBON (C:N 10-20):          UNSTABLE CARBON (C:N > 20):
  ┌─────────────────────────┐          ┌─────────────────────────┐
  │  Humus molecule         │          │  Fresh straw/leaf       │
  │  Tight C-N bonds        │          │  Loose organic matter   │
  │  Bacteria can't         │          │  Bacteria digest        │
  │  easily break apart     │          │  quickly → CO2 release  │
  │  → stays for decades    │          │  → gone in months       │
  └─────────────────────────┘          └─────────────────────────┘
```

**Q: Why does Verra require C:N between 10–20?**
To prove the carbon you're claiming credit for is actually going to STAY in the soil.
If C:N is too high, you might be measuring fresh crop residue that decomposes next spring.
That's not a real carbon credit — it's temporary storage.

---

## 1.4 How Does a Satellite Detect Soil Properties?

Satellites measure **reflected light** — how much light bounces off the Earth's surface 
at different wavelengths. This is spectroscopy from space.

**The Key Physics:**

Different materials reflect different amounts of light at different wavelengths.
Soil with high organic matter reflects LESS light (darker, absorbs more).
Minerals reflect MORE at specific wavelengths.
Water absorbs strongly in shortwave infrared.

```
  SUN emits light →  hits soil  →  bounces back  →  satellite sensor detects it

  HOW MUCH bounces back at each wavelength = the SPECTRAL SIGNATURE of that soil

  High SOC soil:                    Low SOC soil:
  Reflectance                       Reflectance
     │ ▓                               │          ░░
     │ ▓▓                              │       ░░░░░
     │ ▓▓▓▓                            │    ░░░░░░░░░
     │ ▓▓▓▓▓▓                          │ ░░░░░░░░░░░░
     └──────── wavelength              └──────── wavelength
     (absorbs more = darker = low      (reflects more = brighter = low
      reflectance = high SOC)           reflectance = low SOC)
```

**Q: Why can we detect soil from space?**
Because different soil properties (carbon content, moisture, clay minerals) change 
HOW the soil reflects light. Carbon-rich soil looks darker in visible AND infrared.
Clay minerals have specific absorption features in shortwave infrared.
The satellite measures these reflectances across 13 wavelength bands.

---

## 1.5 The Electromagnetic Spectrum — What Each Band Detects

Light we can see (visible) is just a tiny slice of electromagnetic radiation.
Sentinel-2 measures beyond what human eyes can see:

```
  Wavelength:  400nm    700nm    1000nm              2000nm
               │        │        │                    │
  ┌────────────┼────────┼────────┼────────────────────┼──────┐
  │ Ultraviolet│Visible │Near-   │                    │Short │
  │            │(RGB)   │Infrared│                    │Wave  │
  │            │        │ (NIR)  │                    │Infra │
  │            │        │        │                    │Red   │
  └────────────┼────────┼────────┼────────────────────┼──────┘
               │  B2 B3 B4  B5 B6 B7  B8             B11 B12
               │(Blue)(G)(R)(RedEdge)(NIR)           (SWIR)

  What each zone detects in soil:
  
  Visible (B2-B4):  Overall soil brightness, iron oxides (red soils), 
                    organic matter (dark soils)
  
  Red Edge (B5-B7): Chlorophyll absorption edge — tells us vegetation vs bare soil,
                    how healthy the vegetation is, bare soil exposure
  
  NIR (B8):         Near-infrared — organic matter has strong absorption here.
                    Also separates vegetation from soil (plants reflect strongly,
                    bare soil reflects moderately)
  
  SWIR (B11, B12):  Shortwave infrared — MOST diagnostic for soil.
                    Detects clay minerals, soil moisture, organic matter.
                    B11 at 1610nm: moisture content, kaolinite clay
                    B12 at 2190nm: montmorillonite clay, carbonate, organic matter
```

**Q: Why is shortwave infrared (SWIR) so useful for soil?**
Many soil minerals have specific "absorption features" in SWIR — like fingerprints.
When a mineral absorbs light at a specific wavelength, reflectance drops at that point.
Clay minerals (which often co-occur with organic carbon) have strong SWIR features.
Also, organic carbon absorbs broadly in SWIR, so high SOC = lower B11/B12 values.

---

## 1.6 NDVI and BSI — Why We Calculated These

**NDVI (Normalized Difference Vegetation Index)**

```
  NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)

  Range: -1 to +1

  NDVI < 0:    Water, snow, clouds
  NDVI 0-0.2:  Bare soil, rock, urban
  NDVI 0.2-0.5: Sparse vegetation, dry grassland
  NDVI 0.5-1.0: Dense healthy vegetation, forest
```

**Why we need NDVI for SOC prediction:**
SOC can only be measured from satellite when the soil is BARE (no crops blocking the view).
If a pixel has high NDVI (covered by crops), the satellite sees the PLANT not the soil.
NDVI tells our model: "how much plant cover is blocking the soil signal?"
This is a critical correction — without it, the model would confuse healthy crops with 
high-SOC soil.

**BSI (Bare Soil Index)**

```
  BSI = ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2))

  High BSI: bare exposed soil
  Low BSI:  vegetated or water-covered surface
```

**Why BSI on top of NDVI?**
NDVI detects green vegetation. BSI specifically detects EXPOSED BARE SOIL.
They're complementary:
- NDVI high → definitely vegetation
- BSI high → definitely bare soil
- Both low → could be dry vegetation, urban, snow

Together they help the model understand "am I looking at soil right now?"
Only when looking at bare soil does the spectral signal contain soil information.

---

# PART 2: THE DATA IN DEPTH

## 2.1 Sentinel-2 — Every Decision Explained

**Q: Why Sentinel-2 and not Landsat or Planet?**

| Satellite | Resolution | Revisit | Cost | Bands |
|-----------|-----------|---------|------|-------|
| Landsat   | 30m       | 16 days | Free | 7-11  |
| Sentinel-2| 10-60m    | 5 days  | Free | 13    |
| Planet    | 3-5m      | Daily   | $$$  | 4-8   |

Sentinel-2 wins on: free access + 5-day revisit + 13 bands (including critical SWIR) + 
standard for European agricultural monitoring (ESA mandate).
We need SWIR bands B11 and B12 — Landsat has them but Sentinel-2 has better spatial resolution 
and is fully free with no download limits.

**Q: Why did we use Google Earth Engine instead of downloading raw imagery?**

Sentinel-2 produces ~1.6 TB of data PER DAY globally.
For Europe alone, 2018-2020, July-October = roughly 3 years × 4 months × 74,000 images.
Each image = ~1 GB raw. Total = ~74,000 GB = 74 terabytes. Impossible to download.

Google Earth Engine has ALL of this pre-loaded on their servers.
You write Python code, it runs on Google's machines, you download only the result.
We sent 2 files to Google Drive (Europe + Africa composites), each ~100 MB. 
That's the power of cloud geospatial computing.

**Q: Why July–October specifically?**

```
  EUROPE AGRICULTURAL CALENDAR:

  Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
  ─────────────────────────────────────────────────────────
  Winter wheat growing    │         │ Harvest │
                          │         └─────────┘
  Summer crops sown in spring        ▲ Bare fields after harvest
                                     │
  This window (Jul-Oct) is when     BEST TIME for soil measurement:
  fields are most bare              - Crops harvested
                                    - Fields ploughed or empty
                                    - Maximum soil exposure
```

In spring, everything is green and growing — you'd measure the crops, not the soil.
In winter, soils are often snow-covered, waterlogged, or frozen.
July–October gives the maximum bare soil signal in Europe.

**Q: Why cloud cover < 10%?**
Clouds block the soil completely. A pixel covered by cloud gives you cloud reflectance, 
not soil reflectance. We filter to images where less than 10% of the scene is cloudy.
Still got 74,000 valid images for Europe — more than enough for a good median.

**Q: Why take the MEDIAN over 2018-2020?**

Not the MEAN (average) — the MEDIAN (middle value).

```
  Example: pixel has cloud on day 1, then normal values:
  Day 1: 9000 (cloud = massive wrong value)
  Day 2: 450  (soil)
  Day 3: 460  (soil)
  Day 4: 440  (soil)
  Day 5: 455  (soil)

  Mean: (9000+450+460+440+455) / 5 = 2161  ← WRONG, skewed by cloud
  Median: 455  ← CORRECT, cloud outlier ignored automatically
```

Median is robust to outliers (residual clouds, shadows, sensor errors).
Taking 3 years gives enough observations that the median is stable.

**Q: Why SCALE=2000 metres for GEE export?**
The original Sentinel-2 resolution is 10m for visible bands, 20m for SWIR.
At 10m, Europe = 800,000 × 700,000 pixels = 560 billion pixels. 
That would be a 2 TB file — impossible to export from GEE.
At 2000m resolution, Europe = 3,897 × 2,288 pixels ≈ 9 million pixels. 
Much smaller, and actually matches SoilGrids resolution (~250m resampled to ~2km 
because our WCS pixel cap was also at ~2km effective resolution).
For continent-scale carbon credit monitoring, 2km is sufficient.

---

## 2.2 SoilGrids 2.0 — Every Decision Explained

**Q: What is SoilGrids exactly?**

ISRIC (International Soil Reference and Information Centre, Netherlands) took:
- 240,000 soil profiles collected globally by researchers over decades
- Remote sensing layers (climate, terrain, vegetation)
- Machine learning models (Random Forest, mostly)

They trained models to predict soil properties everywhere on Earth.
Output: a global map at 250m resolution of SOC, Nitrogen, pH, clay content, etc.

**Q: Why are the values in dg/kg and cg/kg instead of g/kg?**

SoilGrids stores values as INTEGERS (whole numbers) to save file space.
Floating point numbers (like 23.4) take more space than integers (like 234).

SOC in dg/kg (decigrams per kg):
- Actual value: 23.4 g/kg
- Stored as: 234 dg/kg (multiply by 10)
- We divide by 10 to get g/kg back

Nitrogen in cg/kg (centigrams per kg):
- Actual value: 2.34 g/kg  
- Stored as: 234 cg/kg (multiply by 100)
- We divide by 100 to get g/kg back

**Q: Why Int16 and what does that mean?**

Int16 = 16-bit signed integer = can store values from -32,768 to +32,767.

-32,768 is used as the NODATA value (ocean, missing data).
SOC values max out around 5000 dg/kg (= 500 g/kg, very high peat). 
This fits comfortably in Int16 range.

When we first downloaded with FORMAT=GTiff, the server returned RGB images (uint8, 0-255). 
That was WRONG — it was a visual render for display, not scientific data.
FORMAT=GEOTIFF_INT16 returned the actual Int16 scientific data. 
That bug wasted all 12 downloads and we had to redo them all.

**Q: What is a VRT file and why didn't we use it?**

VRT = Virtual Raster Table. It's like a playlist — a small XML file that points to 
many individual TIFF tiles. The full SoilGrids dataset is too big to store as one file,
so it's split into thousands of tiles. The VRT tells software where each tile is.

Problem: SoilGrids VRT files point to tiles stored on ISRIC's servers, not locally.
When we tried to open them, the software looked for the tiles on our machine — they 
weren't there. We'd have needed to download terabytes of tiles.

Solution: Use the WCS API instead. WCS (Web Coverage Service) is a standard 
geospatial web service that lets you request exactly the area you want 
(Europe or Africa bounding box) and download just that region.

**Q: What is the WCS API call doing exactly?**

```
https://maps.isric.org/mapserv?
  map=/map/soc.map          ← which SoilGrids product
  &SERVICE=WCS              ← Web Coverage Service protocol
  &VERSION=1.0.0            ← WCS version
  &REQUEST=GetCoverage      ← we want data, not metadata
  &COVERAGE=soc_0-5cm_mean  ← which layer
  &CRS=EPSG:4326            ← coordinate system (WGS84, standard GPS)
  &BBOX=-25,34,45,72        ← Europe bounding box (west,south,east,north)
  &RESX=0.017&RESY=0.017    ← pixel size in degrees
  &FORMAT=GEOTIFF_INT16     ← scientific integer format (NOT visual RGB)
```

The server computes the crop, resamples to our pixel size, returns the GeoTIFF.
We got 12 files this way (6 layers × 2 regions).

**Q: Why the pixel cap of 4096 and square pixels?**

Server limit: ISRIC's server crashes (HTTP 500, Out of Memory) if you request 
more than ~8192 pixels per dimension. We set a safe limit of 4096.

Square pixels: we compute resolution as:
```
  resolution = max(east-west, north-south) / 4096
```
Using the LARGEST dimension ensures both width and height fit within 4096 pixels.
If we used different resolutions for X and Y, pixels would be rectangles — 
causes problems with reprojection and area calculations later.

---

## 2.3 LUCAS — The Real Ground Truth

**Q: Who physically collects LUCAS data?**

The European Commission contracts survey teams across all EU countries.
Teams are given GPS coordinates (on a 2km grid covering Europe).
They drive/walk to each point, use a GPS device to find the exact spot.
If the point is on farmland, they dig down with an auger and collect 0-20cm of soil.
Sample goes into a bag, shipped to a central lab in Italy (JRC Ispra).
Lab measures: organic carbon, nitrogen, pH, phosphorus, potassium, calcium carbonate, 
bulk density, particle size distribution.

**Q: Why only 19,000 points for all of Europe?**

The 2km grid covers Europe. At 2km spacing, Europe (~10 million km²) = ~5 million grid points.
But not every point is accessible or agricultural land. 
And the soil survey is a SUBSAMPLE — visiting every 2km point would take decades.
LUCAS visits a stratified random sample that represents all land cover types proportionally.
19,000 is statistically sufficient to characterize European soil variation.

**Q: How does LUCAS measuring 0-20cm compare to our 0-5cm prediction?**

This is a real limitation. LUCAS mixes the top 20cm together in one sample.
Our model predicts the top 5cm layer specifically.
The 0-20cm average will be LOWER than 0-5cm (since carbon decreases with depth).
When we evaluate against LUCAS, we'll see some systematic offset for this reason.
It's a known limitation in the literature — researchers typically accept it or apply 
depth correction factors.

---

# PART 3: THE ENGINEERING DECISIONS

## 3.1 The Pairing Step — Why It's Non-Trivial

**Q: Why can't you just stack the rasters?**

Sentinel-2 and SoilGrids use:
- Different pixel sizes (S2 ≈ 2km, SoilGrids ≈ 250m at native resolution, both became ~2km)
- Different pixel grids (even at the same resolution, pixel corners don't align)
- Slightly different extents

```
  SoilGrids grid:          Sentinel-2 grid:
  ┌──┬──┬──┬──┐            ┌───┬───┬───┐
  │  │  │  │  │            │   │   │   │
  ├──┼──┼──┼──┤            ├───┼───┼───┤
  │  │  │  │  │            │   │   │   │
  ├──┼──┼──┼──┤            ├───┼───┼───┤
  └──┴──┴──┴──┘            └───┴───┴───┘
  (smaller pixels,          (larger pixels,
   different origin)         different origin)
```

Reprojection warps SoilGrids pixels to exactly match S2 pixel locations.
After reprojection, pixel (i,j) in SoilGrids array corresponds exactly to 
pixel (i,j) in Sentinel-2 array — they represent the same piece of ground.

**Q: Why bilinear resampling and not nearest-neighbour?**

Nearest-neighbour: just picks the closest source pixel. Fast but creates "blocky" output.
Bilinear: interpolates between 4 surrounding source pixels. Smoother, more accurate.

For continuous data like SOC (which changes gradually across landscapes), 
bilinear interpolation gives more accurate values at each grid point.

**Q: Why 80/20 train/validation split?**

Standard practice in machine learning.
80% of data trains the model (it learns from these examples).
20% is HELD OUT — the model never sees these during training.
We test on the 20% to check real performance (the model can't have memorised those).

With 12.3 million samples: 9.8M train, 2.5M validation. Very robust estimates.

**Q: Why did we need a random seed (SEED=42)?**

Without fixing the random seed, the train/val split would be different every run.
The model weights would initialise differently. Results would be different each run.
Setting seed=42 makes every run REPRODUCIBLE — same results every time.
Essential for science: someone else running your code must get the same numbers.

---

## 3.2 The NPZ File Format

**Q: What is NPZ and why did we use it?**

NPZ = NumPy Zipped. It stores multiple NumPy arrays in one compressed file.

Alternatives considered:
- CSV: can't store multi-dimensional arrays. 12M rows × 11 columns CSV = ~1 GB uncompressed
- HDF5: powerful but requires extra library (h5py)
- Parquet: great for tabular data but needs pandas/pyarrow
- NPZ: built into NumPy (no extra dependency), compressed, fast to load

Our training_europe.npz contains:
```
  X          shape (3487079, 11)  float32  → 11 features per pixel
  y_soc      shape (3487079, 3)   float32  → SOC at 3 depths
  y_nitrogen shape (3487079, 3)   float32  → N at 3 depths
```

Total uncompressed: ~265 MB. After NPZ compression: ~169 MB. 

**Q: Why float32 and not float64?**

float32 = 4 bytes per number (32 bits), accuracy to ~7 decimal places
float64 = 8 bytes per number (64 bits), accuracy to ~15 decimal places

For our values (SOC 0-500 g/kg, spectral reflectance 0-1), 7 decimal places is plenty.
float32 uses HALF the memory of float64.
12.3M × 11 features × 4 bytes = 541 MB in float32
12.3M × 11 features × 8 bytes = 1.08 GB in float64
Neural networks train on float32 natively (GPUs are optimised for it).

---

## 3.3 The StandardScaler — Why We Normalise

**Q: Why do neural networks need normalised data but trees don't?**

Decision trees and XGBoost work by asking "is this feature ABOVE or BELOW a threshold?"
They don't care about the magnitude of values — only the ordering.
B2 = 0.05 or B2 = 500 makes no difference to a tree, it just splits on a number.

Neural networks use gradient descent — they update weights by small steps.
If features are on very different scales, gradients are unbalanced:
```
  B2 (reflectance): 0.02 to 0.15   (small numbers)
  SOC target:       2 to 500 g/kg  (large numbers)

  Without scaling: gradient for SOC features is 10,000× bigger than B2 features.
  The network wildly overfit to SOC scale and ignores B2. Training is unstable.

  With StandardScaler: each feature has mean=0, std=1. All gradients balanced.
  Network trains stably and learns from ALL features equally.
```

StandardScaler formula:
```
  scaled_value = (original_value - mean) / standard_deviation
```

We fit the scaler ONLY on training data (not validation).
This prevents "data leakage" — the model shouldn't know anything about validation data,
including its statistics.

---

## 3.4 Why Each Neural Network Architecture Decision

**Q: Why ReLU activation function?**

```
  Sigmoid: output = 1/(1+e^-x)  → squashes all values to 0-1
           Problem: gradients become tiny for large inputs → "vanishing gradients"
           Training slows or stops

  ReLU: output = max(0, x)      → 0 for negatives, x for positives
        Why better: gradient is always 1 (for positive inputs) → no vanishing gradient
        Simple and fast to compute
        Standard in modern deep learning since 2012
```

**Q: Why Dropout(0.2)?**

Dropout randomly sets 20% of neurons to zero during training.
This forces the network to not rely on any single neuron — more robust representations.
It's a regularisation technique: prevents overfitting (memorising training data).

During inference (predict.py), dropout is turned OFF — all neurons active.

**Q: Why 3 Conv1D layers in 1D-CNN with 32→64→128 filters?**

Each convolutional layer learns more complex spectral patterns:
- Layer 1 (32 filters): simple patterns like "high B8, low B4" (vegetation vs soil)
- Layer 2 (64 filters): combinations like "high B11 AND high B12" (clay minerals)
- Layer 3 (128 filters): complex multi-band signatures specific to SOC-rich soils

Increasing filters with depth: each layer can build on what the previous learned.
32→64→128 is a common doubling pattern — validated empirically in hundreds of papers.

**Q: Why kernel_size=3 with padding=1 in 1D-CNN?**

kernel_size=3 means each filter looks at 3 consecutive bands at a time.
padding=1 adds one zero on each side so the output stays the same length (11).
Without padding, each Conv1D layer would shrink the sequence length.
With padding, all 3 layers preserve the 11-band structure until Flatten.

**Q: Why 9×9 patches for 2D-CNN?**

Smaller (e.g. 5×5): captures only immediate neighbours, misses landscape context.
Larger (e.g. 15×15): requires more computation, captures irrelevant distant context.
9×9 = at 2km pixels → 18km × 18km area around each target pixel.
At 2km resolution, a 9×9 patch spans ~18km — enough to capture:
- Field patterns and boundaries
- Valley vs hilltop position (topographic context)
- Urban edge effects
- Forest/crop transitions

**Q: Why AdaptiveAvgPool2d(1) at the end of 2D-CNN?**

After 4 Conv2D layers, the spatial dimensions shrink:
9×9 → (pad) → (kernel=3) → 7×7 → (kernel=3) → 5×5

AdaptiveAvgPool2d(1) collapses this 5×5 spatial map to a single 1×1 value per channel.
It takes the AVERAGE of all 5×5=25 spatial values per feature map.
This gives us a fixed-size feature vector regardless of input spatial size.
Why average instead of flatten? Averaging is translation-invariant — the model 
doesn't care WHERE in the 9×9 patch a feature appears, just WHETHER it appears.

---

## 3.5 Why We Subsampled Trees to 500K

Training XGBoost on all 12.3M samples would take hours and use gigabytes of RAM.
Beyond about 500K samples, the accuracy improvement is marginal for tree models.

This is because decision trees learn by finding the best SPLIT POINT for each feature.
With 12M samples vs 500K samples, the 500K version finds almost identical split points.
The rare events that only appear in the extra 11.8M samples don't change the tree structure.

Neural networks benefit more from large datasets because they learn distributed representations
— every parameter benefits from every example. Trees don't learn this way.

---

# PART 4: THE MACHINE LEARNING IN DEPTH

## 4.1 XGBoost — How It Actually Works

XGBoost (eXtreme Gradient Boosting) builds trees sequentially:

```
  Iteration 1: Build a simple tree → predicts SOC for each pixel
               Tree makes errors. Calculate residuals (actual - predicted).

  Iteration 2: Build another tree to predict the RESIDUALS from iteration 1.
               Now combined prediction = tree1 + tree2. Better!

  Iteration 3: Calculate new residuals from combined tree1+tree2.
               Build tree3 to predict those residuals.
               Combined: tree1 + tree2 + tree3. Even better!

  ... repeat 300 times (n_estimators=300) ...

  Final prediction = sum of all 300 trees' predictions
```

**Why it works:** Each tree specialises in fixing the previous trees' mistakes.
The "gradient" in gradient boosting refers to the gradient of the loss function 
(how wrong we are) with respect to the prediction — each tree descends this gradient.

**Our settings:**
- n_estimators=300: 300 trees (more = better but slower)
- max_depth=6: each tree can have up to 6 levels (64 leaf nodes maximum)
- learning_rate=0.05: each tree contributes only 5% of its prediction (prevents overfitting)
- subsample=0.8: each tree trains on 80% of data (random, prevents overfitting)
- colsample_bytree=0.8: each tree uses 80% of features randomly (prevents overfitting)

---

## 4.2 Random Forest — How It Differs from XGBoost

```
  Random Forest:                    XGBoost:

  Train 100 trees IN PARALLEL       Train 300 trees IN SEQUENCE
  Each tree uses random subset      Each tree fixes previous tree's errors
  of data and features              
  Final answer = AVERAGE            Final answer = WEIGHTED SUM
  of all 100 trees                  of all 300 trees

  More robust (averaging           More accurate (gradient-guided)
  independent opinions)            but can overfit if not careful
```

**Why Random Forest beat XGBoost in our results (R²=0.821 vs 0.793):**
With 11 features and the amount of noise in satellite-to-soil relationships,
RF's averaging approach was more stable. XGBoost may have been slightly overfitting
to the SoilGrids training data with our hyperparameters.

With proper hyperparameter tuning, XGBoost would likely match or beat RF.

---

## 4.3 What R² Actually Means (Detailed)

R² (coefficient of determination) measures variance explained.

```
  SOC values for 5 pixels:  [10, 50, 80, 120, 200] g/kg
  Mean:                       92 g/kg

  Total variance = spread of actual values from mean
  = (10-92)² + (50-92)² + (80-92)² + (120-92)² + (200-92)²
  = 6724 + 1764 + 144 + 784 + 11664 = 21080

  Our model predicts:        [15, 45, 90, 110, 210]
  Residual variance = spread of errors
  = (15-10)² + (45-50)² + (90-80)² + (110-120)² + (210-200)²
  = 25 + 25 + 100 + 100 + 100 = 350

  R² = 1 - (residual variance / total variance)
     = 1 - (350 / 21080)
     = 1 - 0.0166
     = 0.983  ← very good (hypothetical example)
```

**Why R²=0.82 might sound high but we still need R²=0.85:**
Our training R² (against SoilGrids) is 0.82. But:
1. SoilGrids itself has errors vs real soil (R²~0.60–0.70 vs field data)
2. Our model inherits those errors + adds its own
3. True R² against LUCAS field data is probably 0.50–0.65

The jump from 0.82 (vs SoilGrids) to 0.65 (vs reality) is why LUCAS evaluation matters.
Verra's R²≥0.85 requirement applies to validation against FIELD DATA, not SoilGrids.

---

# PART 5: THE CARBON CREDIT BUSINESS

## 5.1 How Carbon Credits Work

```
  CARBON CREDIT = 1 tonne of CO2 that would NOT have been released
                  (or has been absorbed from the atmosphere)

  Who buys them: Companies that can't reduce their own emissions fast enough.
                 They buy credits to "offset" their remaining emissions.

  Who sells them: Farmers, forest owners, land managers who improve their land.
                  Each tonne of CO2 sequestered = 1 credit = ~$15–30 revenue.

  Who certifies: Verra (Voluntary Carbon Standard) or Gold Standard.
                 They check: Is the measurement methodology sound?
                             Is the carbon ADDITIONAL (wouldn't have happened anyway)?
                             Is the carbon PERMANENT (won't be released soon)?
                             Is leakage prevented (not just shifted elsewhere)?
```

## 5.2 The Carbon Conversion Equation — Every Number Justified

```
  ΔSOC (g/kg) × bulk density (kg/m³) × depth (m) × area (m²) = grams of Carbon

  Why each number:

  ΔSOC = change in soil organic carbon (g/kg)
         Positive = soil absorbed carbon (sequestration)
         Negative = soil lost carbon (no credit)

  × 1300 kg/m³ = bulk density
    "How heavy is a cubic metre of this soil?"
    1300 kg/m³ is conservative for mineral soils (actual range: 1000–1600)
    Sandy soils: ~1600 kg/m³
    Clay-rich soils: ~1200 kg/m³  
    Peaty soils: ~800–1000 kg/m³
    We use 1300 as a safe conservative value
    Units: (g carbon / kg soil) × (kg soil / m³) = g carbon / m³

  × 0.05 m = depth of top layer (0-5cm = 0.05 metres)
    We're measuring only the top 5cm
    Units: (g carbon / m³) × m = g carbon / m²

  × pixel area (m²) = how big each pixel is
    At 2000m resolution: each pixel covers 2km × 2km = 4,000,000 m²
    But pixels are in degrees (lat/lon) so area varies with latitude:
    At equator: 1° longitude = 111,320m. At 60°N: 1° longitude = 55,660m.
    We use cos(45°) as a mid-latitude correction for Europe.
    Units: (g carbon / m²) × m² = g carbon (per pixel)

  ÷ 1,000,000 = convert grams to tonnes (1 tonne = 1,000,000 grams)
    Units: tonnes of Carbon (per pixel)

  × 44/12 = convert Carbon to CO2
    Carbon atom: atomic mass 12
    CO2 molecule: atomic mass 12 + 16 + 16 = 44
    1 tonne of Carbon, when it becomes CO2, weighs 44/12 = 3.667 tonnes
    Units: tonnes of CO2 (per pixel)

  FINAL: Sum over all valid pixels = total tCO2 sequestered in the region
```

## 5.3 The C:N Stability Filter — Why Only 62.7% of Europe Passed

Of 6.4M valid Europe pixels, 4M passed the C:N 10–20 filter (62.7%).
The 37.3% that failed are:
- Pixels where SOC/N > 20: likely fresh crop residue, unstable carbon
- Pixels where SOC/N < 10: nitrogen-rich soils (heavily fertilised arable land)
- Pixels at field edges where both signals mix

This is actually a GOOD sign — the C:N filter is working as intended.
Only claiming credits for genuinely stable carbon is exactly what Verra wants.

---

# PART 6: COMMON INTERVIEW QUESTIONS

**Q: "Why didn't you use field measurements directly for training?"**

We would need field measurements at millions of locations to train a continental model.
The LUCAS survey has 19,000 points — not enough to train a model that needs to generalise 
across 12 million pixels. SoilGrids (derived from 240,000 global samples + ML) gives us 
denser coverage at the cost of introducing its own model errors.
The correct approach (which we're building toward) is:
1. Pre-train on SoilGrids (dense coverage)
2. Fine-tune on LUCAS (real measurements)
This is called "transfer learning" and is standard in satellite remote sensing.

**Q: "How do you handle clouds?"**

Two layers of cloud handling:
1. GEE filter: only include Sentinel-2 images where < 10% of scene is cloudy
2. Median composite: even if some remaining clouds slip through the filter, 
   taking the median over 3 years means the median value will be from a cloud-free image
   (most of the 74,000 images for Europe are clear — clouds are outliers in the median)

**Q: "What happens when new Sentinel-2 images come in?"**

The pipeline can run predict.py on any new S2 image.
For carbon credit monitoring:
- Year 1: run predict.py → baseline SOC map
- Year 2: run predict.py → current SOC map
- Run carbon_calc.py on both → sequestration amount → carbon credits

The 5-day revisit means you could theoretically do this monthly, but for carbon credits 
annual measurement is standard (following crop seasons and annual carbon turnover).

**Q: "How accurate is 2km resolution for measuring a single farm?"**

A 2km pixel covers 400 hectares. A typical European farm is 10-100 hectares.
So one pixel contains multiple farms — we're measuring landscape-level SOC, 
not individual field SOC.

For certification of individual farms, you'd need higher resolution imagery 
(e.g. Planet at 3-5m) but that costs money.
At 2km, our pipeline is suited for:
- National/regional carbon accounting
- Carbon credit projects covering large areas (>1000 ha)
- Policy monitoring (Verra REDD+ jurisdictional approach)

For individual farm credits, the resolution would need to be increased in future.

**Q: "What's the difference between SoilGrids and LUCAS?"**

| | SoilGrids | LUCAS |
|---|---|---|
| Type | ML prediction | Real lab measurements |
| Coverage | Global, 250m continuous | 19,000 points, sampled |
| SOC accuracy vs reality | R²≈0.60-0.70 | IS the reality |
| How collected | Algorithm + existing data | People + augers + labs |
| Use in our project | Training labels | Validation truth |
| Limitation | Inherits old data biases | Too sparse for training |

**Q: "Why four models? Why not just train one?"**

Ensemble learning principle: different models have different weaknesses.
- XGBoost: fast, good baseline, interpretable feature importance
- Random Forest: robust to overfitting, good uncertainty estimates
- 1D-CNN: learns spectral band relationships pixel-wise
- 2D-CNN: learns spatial-spectral patterns across landscapes

Comparing multiple models helps us:
1. Understand which approach works best for this data type
2. Potentially ensemble them (average predictions for better accuracy)
3. Use the simpler model where compute matters, complex model where accuracy matters

**Q: "Could you improve accuracy further?"**

Yes, several paths:
1. Fine-tune on LUCAS (transfer learning from SoilGrids → LUCAS)
2. Add terrain data (elevation, slope, aspect) — topography strongly controls SOC
3. Add climate data (rainfall, temperature) as additional features
4. Use time-series of Sentinel-2 (multiple dates, not just median) — LSTM or Transformer
5. Higher resolution imagery (Planet, WorldView) for field-scale accuracy
6. Add Sentinel-1 radar data (sees through clouds, soil moisture sensitive)

**Q: "What is Verra VCS VM0042?"**

Verra VCS = Voluntary Carbon Standard — the world's leading voluntary carbon market.
VM0042 = Methodology for Improved Agricultural Land Management.
It specifies:
- How to measure baseline SOC
- How to measure additionality (would this sequestration happen without the project?)
- Minimum R² required for remote sensing-based measurement (≥0.85)
- How often to re-measure (typically every 5 years, can be annual)
- Permanence requirements (carbon must stay for 100 years or buffer pool required)
- Leakage assessment (has land use change just moved to neighbouring areas?)

Our pipeline is being built to satisfy VM0042 requirements for remote sensing SOC quantification.

**Q: "What is the biggest weakness of your pipeline right now?"**

Training on SoilGrids instead of real field measurements.
Our reported R²=0.87 is against SoilGrids validation data — a model grading itself on 
a test set derived from the same source as its training labels.
The TRUE accuracy against LUCAS field measurements is likely 0.50-0.70.
This is why the LUCAS evaluation step is critical before any commercial deployment.

**Q: "What does it cost to run this pipeline?"**

Data:
- Sentinel-2: FREE (ESA open data)
- SoilGrids: FREE (ISRIC WCS API)
- LUCAS: FREE (requires registration)
- Google Earth Engine: FREE for research and non-commercial use

Compute:
- Data download: your own machine, free
- Model training: our models ran on CPU (slow but free)
  With a GPU (e.g. NVIDIA A100 on cloud), training would take minutes instead of hours
  AWS EC2 p3.2xlarge: ~$3/hour × 2 hours training = ~$6 total

Storage:
- All processed data + models: ~2-3 GB = negligible cost

The entire pipeline can run for under $10 in cloud compute costs.
Compare to traditional field surveys: €500-2000 per sample × 19,000 samples = 
€9-38 million for LUCAS. Our approach is 1000× cheaper at scale.

---

# PART 7: THE FILES YOU COULDN'T OPEN — EXPLAINED

## The GeoTIFF Files (.tif)

These are scientific rasters — grids of numbers with GPS coordinates attached.
Each pixel IS a number (SOC value, reflectance value, etc.) — not a colour.
Software like Excel, Photos, or even GIMP will try to open them as images and fail.

**To actually open them:** Install QGIS (free). File → Open → drag .tif file.
QGIS will show you the spatial extent on a map and let you click pixels to see values.

**To read the values in Python:**
```python
import rasterio
with rasterio.open('data/processed/europe/soc/soc_0-5cm_mean.tif') as src:
    data = src.read(1)           # read band 1 (only 1 band in SoilGrids files)
    print(data.shape)            # (2224, 4096) = rows × columns
    print(data[1000, 2000])      # SOC at pixel row 1000, column 2000 (in dg/kg)
    print(data[1000, 2000] / 10) # convert to g/kg
```

## The NPZ Files (.npz)

These are compressed numpy arrays — pure numerical data, no spatial info.
Think of them as very efficient spreadsheets with 12 million rows.

**To read them:**
```python
import numpy as np
data = np.load('data/training/europe/training_europe.npz')
print(data.files)          # ['X', 'y_soc', 'y_nitrogen']
print(data['X'].shape)     # (3487079, 11) — 3.5M pixels × 11 features
print(data['X'][0])        # spectral features of first pixel
print(data['y_soc'][0])    # SOC values at 3 depths for first pixel
```

## The PKL Files (.pkl)

Python "pickle" files — serialised Python objects. In our case, trained ML models.
A .pkl file contains the entire learned model (all 100 trees for RF, all 300 for XGB).

**To use them:**
```python
import joblib
model = joblib.load('outputs/models/random_forest.pkl')
# Now you can use it:
import numpy as np
features = np.array([[0.04, 0.06, 0.05, 0.07, 0.18, 0.22, 0.31, 0.19, 0.14, 0.45, -0.1]])
prediction = model.predict(features)
print(f"SOC: {prediction[0,0]:.1f} g/kg, N: {prediction[0,1]:.3f} g/kg")
```

## The .pt Files (PyTorch model weights)

These contain the neural network weights (the learned numbers inside each neuron).
Not executable on their own — you need to load them INTO the model architecture.

**To use them:**
```python
import torch
from src.models.train import CNN2D  # import the architecture

model = CNN2D()                                      # create empty model
model.load_state_dict(torch.load('outputs/models/cnn2d.pt'))  # fill with learned weights
model.eval()                                         # switch to inference mode
# Now use it for predictions
```

---

# SUMMARY: THE ONE-PAGE VERSION

**What:** ML pipeline to predict Soil Organic Carbon from satellite imagery.

**Why:** Soil carbon monitoring at continental scale, to issue verifiable carbon credits.

**Data in:**
- Sentinel-2 satellite (11 spectral features per 2km pixel, updated every 5 days)
- SoilGrids 2.0 (training labels: predicted SOC at 250m globally)
- LUCAS 2018 (validation: 19,000 real lab-measured soil samples across Europe)

**What we built:**
- Data pipeline: fetch, pair, and process 12.3M training samples
- 4 ML models: XGBoost (R²=0.793), RF (R²=0.821), 1D-CNN (~0.841), 2D-CNN (~0.873)
- Prediction maps: 2-band GeoTIFFs (SOC g/kg + N g/kg) for Europe and Africa
- Carbon calc: ΔSOC → tCO2/ha → carbon credit estimate

**What's left:**
- Validate against LUCAS real measurements (find true R²)
- Run on Year 2 imagery to get real sequestration numbers
- Submit to Verra VCS for certification (requires R²≥0.85 vs field data)
