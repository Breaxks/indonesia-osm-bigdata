# Indonesia Road Infrastructure & Accessibility — Big Data Analytics

A full-stack Big Data analytics project analyzing road infrastructure, network
connectivity, accessibility, and regional differences across Indonesia, built
entirely from an OpenStreetMap (Geofabrik) extract.

- **Backend:** Python, FastAPI, PySpark, GeoPandas, NetworkX, scikit-learn
- **Frontend:** React, Vite, Material UI, React-Leaflet, Recharts
- **No database required.** Processed artifacts are Parquet / JSON / GeoJSON files.

---

## 1. Project Structure

```text
indonesia-osm-bigdata/
├── backend/
│   ├── app/                 # FastAPI application (API, services, config)
│   ├── processing/          # The Big Data pipeline (run this first)
│   ├── data/
│   │   ├── raw/              <- put indonesia-latest.osm.pbf here
│   │   ├── processed/         (generated: roads.parquet, etc.)
│   │   ├── geojson/           (generated: per-province GeoJSON)
│   │   ├── models/             (generated: accessibility_model.pkl)
│   │   └── outputs/            (generated: overview.json, ml_metrics.json, etc.)
│   └── requirements.txt
├── frontend/                # React + MUI dashboard
└── .gitignore
```

---

## 2. Prerequisites

- Python 3.10 or 3.11 (PySpark and GeoPandas are most reliably installed on
  these versions; Python 3.12+ can work but may need newer wheels)
- Java 11 or 17 (required by PySpark — `java -version` should work)
- Node.js 18+
- ~4 GB of free RAM for full national processing (PySpark is configured for
  2 GB driver memory by default; adjust in `processing/aggregate_regions.py`
  if needed)

---

## 3. Backend Setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

- Windows: `venv\Scripts\activate`
- macOS/Linux: `source venv/bin/activate`

Install dependencies:

```bash
pip install -r requirements.txt
```

> **Note on `pyrosm` / `osmium`:** these are the two supported PBF-reading
> backends. `pyrosm` is tried first because it is simpler; if it fails to
> import or errors during extraction, the pipeline automatically falls back
> to a streaming `pyosmium` extractor that uses effectively constant memory.
> You do not need to choose one manually.

### Place the raw dataset

Download `indonesia-latest.osm.pbf` from Geofabrik if you don't already have it:

```text
https://download.geofabrik.de/asia/indonesia-latest.osm.pbf
```

Copy it into:

```text
backend/data/raw/indonesia-latest.osm.pbf
```

The pipeline and API both check for this file and print a clear message
(never a raw stack trace) if it's missing.

### Run the processing pipeline

```bash
# Fast development mode (processes a small Jakarta-area subset in seconds/minutes)
python processing/run_pipeline.py --sample

# Full national processing (processes the entire 1.6GB extract; can take a
# while depending on your machine -- extraction and graph analytics are the
# slowest stages)
python processing/run_pipeline.py --full
```

The pipeline prints progress for all 13 stages, e.g.:

```text
[1/13] Checking raw OSM file...
[2/13] Extracting roads and administrative boundaries...
...
[13/13] Processing complete.
```

Re-run this any time you want to regenerate the processed data (e.g. after
switching from `--sample` to `--full`, or after tuning
`ACCESSIBILITY_WEIGHTS` in `app/config.py`).

### Start the API

```bash
uvicorn app.main:app --reload
```

- API base URL: `http://127.0.0.1:8000`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`
- Health check: `GET /api/health`

If you query the API before running the pipeline, endpoints return an
HTTP 503 with a clear `"Dataset has not been processed yet..."` message
instead of an error or fabricated data.

---

## 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

- Dashboard URL: `http://localhost:5173`
- The Vite dev server proxies `/api/*` requests to `http://127.0.0.1:8000`
  (see `vite.config.js`), so make sure the backend is running first.

---

## 5. Typical First-Run Workflow

```bash
# 1. Place the dataset
cp /path/to/indonesia-latest.osm.pbf backend/data/raw/

# 2. Process it (start with --sample to verify everything works quickly)
cd backend
python processing/run_pipeline.py --sample

# 3. Start the API
uvicorn app.main:app --reload

# 4. In a second terminal, start the frontend
cd frontend
npm install
npm run dev

# 5. Open http://localhost:5173
```

Once you've confirmed the dashboard works end-to-end in sample mode, switch
to full processing:

```bash
python processing/run_pipeline.py --full
# then restart uvicorn so it picks up the new processed files
```

---

## 6. Where Things Are Generated

| File | Produced by | Used by |
|---|---|---|
| `data/processed/roads.parquet` | `preprocess.py` | almost everything |
| `data/processed/province_summary.parquet` | `aggregate_regions.py` (PySpark) | Overview, Road Infrastructure |
| `data/processed/graph_metrics.parquet` | `graph_analysis.py` (NetworkX) | Graph Analytics, ML features |
| `data/processed/region_features.parquet` | `feature_engineering.py` | Regional Comparison, ML |
| `data/processed/accessibility_scores.parquet` | `feature_engineering.py` | Machine Learning, Overview |
| `data/models/accessibility_model.pkl` | `train_ml.py` (scikit-learn) | ML API endpoints |
| `data/geojson/<province>.geojson` | `export_geojson.py` | Map Explorer |
| `data/outputs/*.json` | various stages | API JSON responses |
| `data/outputs/pipeline_status.json` | `run_pipeline.py` | "processed" status shown in UI |

## 7. Re-running Preprocessing / Regenerating Specific Stages

The pipeline is modular — you can import and re-run any single stage from a
Python shell inside `backend/` if you only need to regenerate part of the
output (e.g. after editing `ACCESSIBILITY_WEIGHTS`):

```python
import pandas as pd
from processing.feature_engineering import build_region_features, compute_accessibility_index

roads = pd.read_parquet("data/processed/roads.parquet")
features = build_region_features(boundaries=None)  # boundaries already baked into province col
compute_accessibility_index(features)
```

For a full, guaranteed-consistent regeneration, just re-run
`python processing/run_pipeline.py --full` (or `--sample`).

---

## 8. Methodology Notes

- **Province assignment:** roads are spatially joined to `admin_level=4`
  boundaries extracted from the same PBF (via `pyrosm.get_boundaries`), with
  a bundled fallback GeoJSON path (`data/geojson/_province_boundaries_fallback.geojson`)
  if you supply one. If neither is available, roads are labeled `"Unknown"`
  rather than guessed.
- **Accessibility index:** a transparent, weighted combination of normalized
  road-network metrics (road density, intersection density, major-road
  ratio, network density, average node degree). Weights and Low/Medium/High
  thresholds live in `backend/app/config.py` and are meant to be tuned.
- **Machine learning:** a Random Forest is trained to reproduce the
  index-derived Low/Medium/High classes from the underlying raw features —
  this is explicitly **not** based on any official ground-truth accessibility
  label, since none exists in OpenStreetMap.
- **Graph analytics:** graphs are built per-province (not one national
  graph) because exact betweenness centrality is computationally
  unreasonable at national scale. Provinces with very large graphs use a
  k-sampled approximation, flagged in both the API response and the UI.

## 9. Data Limitations

OpenStreetMap is community-maintained and its completeness varies by
location. Road existence does not imply road quality. OSM alone cannot
measure traffic congestion or real travel demand. The accessibility score
in this project describes road-network structural characteristics only and
is not an official Indonesian government accessibility index. See the
**About Dataset** page in the dashboard for the full list of limitations.
