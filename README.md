# Indonesia Road Infrastructure & Accessibility: Big Data Analytics

A full-stack Big Data project that analyzes road infrastructure, network
connectivity and accessibility across Indonesian provinces. It combines two
independent datasets:

| Dataset | Source | Format | What it provides |
|---|---|---|---|
| **OpenStreetMap Indonesia** | [Geofabrik](https://download.geofabrik.de/asia/indonesia.html) | `.osm.pbf` (~1.6 GB, ~5 million road segments) | Road network geometry and attributes |
| **Population by province (2026)** | [BPS, Statistics Indonesia](https://www.bps.go.id/id/statistics-table/3/V1ZSbFRUY3lTbFpEYTNsVWNGcDZjek53YkhsNFFUMDkjMyMwMDAw/jumlah-penduduk--laju-pertumbuhan-penduduk--distribusi-persentase-penduduk--kepadatan-penduduk--rasio-jenis-kelamin-penduduk-menurut-provinsi.html?year=2026) | CSV (38 provinces) | Population, growth rate, density, sex ratio |

Joining the two lets the project measure accessibility relative to the people
served, for example **road length per 1,000 people**, and not only road
density per square kilometre.

- **Backend:** Python 3.11, FastAPI, PySpark, GeoPandas, NetworkX, scikit-learn, PyOsmium
- **Frontend:** React, Vite, Material UI, React-Leaflet, Recharts
- **No database.** Processed data is stored as Parquet, JSON and GeoJSON files.

---

## 1. Project structure

```text
indonesia-osm-bigdata/
├── backend/
│   ├── app/                      # FastAPI application (API, services, config)
│   ├── processing/               # The big data pipeline
│   │   ├── extract_osm.py        # PBF extraction (PyOsmium, streaming)
│   │   ├── preprocess.py         # Cleaning, geodesic length, province join
│   │   ├── aggregate_regions.py  # PySpark aggregation
│   │   ├── graph_analysis.py     # NetworkX graph analytics (checkpointed)
│   │   ├── feature_engineering.py# Region features + accessibility index
│   │   ├── demographic_join.py   # BPS population join (second dataset)
│   │   ├── train_ml.py           # Random Forest classification
│   │   ├── export_geojson.py     # Per-province GeoJSON for the map
│   │   └── run_pipeline.py       # Runs all stages
│   ├── prepare_boundaries.py     # One-off: converts the province boundary source
│   ├── data/
│   │   ├── raw/                  # Put indonesia-latest.osm.pbf here
│   │   │   └── population_bps_2026.csv   # BPS population data (included in repo)
│   │   ├── geojson/              # Province boundary file (included) + generated files
│   │   ├── processed/            # Generated: Parquet files, graph checkpoints
│   │   ├── models/               # Generated: accessibility_model.pkl
│   │   └── outputs/              # Generated: JSON summaries
│   └── requirements.txt
├── frontend/                     # React + Material UI dashboard
└── .gitignore
```

The raw `.osm.pbf` file is **not** in the repository because of its size.
Everything else needed to run the pipeline is, including the BPS CSV and the
province boundary file.

---

## 2. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | **3.11** | Python 3.14 has no prebuilt wheels for pandas and the geospatial packages, and `pip install` fails there |
| Java | **17** | Required by PySpark. Check with `java -version` |
| Node.js | 18 or newer | For the frontend |
| RAM | 16 GB recommended | Full national run was tested on 16 GB |

On Windows, after installing Python, Java or Node, close all terminals and
fully restart VS Code. Terminals only see new PATH entries after a restart.

---

## 3. Backend setup

The commands below are for Windows PowerShell. Run them one per line (older
PowerShell does not support `&&`).

```powershell
cd backend
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If activation is blocked by the execution policy, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

On macOS/Linux, use `python3.11 -m venv venv` and `source venv/bin/activate`.

Always check that your prompt starts with `(venv)` before running any
`python` command. Without it, you are using the system Python, which does not
have the packages installed.

### Get the OSM data

Download `indonesia-latest.osm.pbf` from Geofabrik:

```text
https://download.geofabrik.de/asia/indonesia-latest.osm.pbf
```

Geofabrik downloads can be slow from some regions. A multi-connection
downloader such as `aria2c` helps. Geofabrik may also name the file with a
date, such as `indonesia-260918.osm.pbf`. Rename it so the file is exactly:

```text
backend/data/raw/indonesia-latest.osm.pbf
```

### Population data (BPS)

`backend/data/raw/population_bps_2026.csv` is already in the repository. It is
the BPS table *Penduduk, Laju Pertumbuhan Penduduk, Distribusi Persentase
Penduduk, Kepadatan Penduduk, Rasio Jenis Kelamin Penduduk Menurut Provinsi*
(2026). To use a newer table, export it from bps.go.id as CSV and keep the same
column names, or update `BPS_COLUMN_MAP` in `processing/demographic_join.py`.

### Province boundaries

PyOsmium streams the PBF and does not extract administrative boundaries. Roads
are assigned to provinces with a spatial join against
`backend/data/geojson/_province_boundaries_fallback.geojson`, which is included
in the repository. See [Known limitations](#8-known-limitations) for what this
means for province names.

---

## 4. Run the pipeline

```powershell
# Quick development run: small Jakarta-area subset
python processing\run_pipeline.py --sample

# Full national run
python processing\run_pipeline.py --full

# Re-run only the later stages, reusing the existing roads.parquet
python processing\run_pipeline.py --resume
```

The pipeline has 13 stages and prints progress for each one:

| Stages | What happens |
|---|---|
| 1-2 | Validate the PBF file and extract the road network |
| 3-6 | Clean records, compute geodesic length, join roads to provinces, save Parquet |
| 7 | PySpark aggregation by province and road type |
| 8 | NetworkX graph analytics per province (nodes, edges, degree, components, centrality) |
| 9 | Region features, then **BPS population join** and per-capita metrics |
| 10 | Accessibility score and Low / Medium / High class |
| 11 | Random Forest training and evaluation |
| 12 | Simplified GeoJSON for the map |
| 13 | Write pipeline status |

Reference timings from a full run on an Intel Core i5-13420H with 16 GB RAM:
extraction about 5 minutes, preprocessing about 5 minutes, PySpark aggregation
about 10 seconds, **graph analytics about 66 minutes**, GeoJSON export about 2 minutes.

### Resuming and checkpoints

Stage 8 saves each province's result to `backend/data/processed/graph_checkpoints/`
as soon as that province finishes. If the run is interrupted, run it again and
finished provinces are loaded from disk instead of recomputed. Only the
province that was in progress is redone. Delete the folder to force a full
recompute.

`--resume` skips stages 1-6 when `backend/data/processed/roads.parquet` exists.
Use a full `--full` run only when the raw PBF or the extraction/preprocessing code changes.

### Run the API

```powershell
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger docs: `http://127.0.0.1:8000/docs`
- Before the pipeline has run, endpoints return HTTP 503 with a message saying the dataset has not been processed. They never return placeholder data.

Restart `uvicorn` after re-running the pipeline so it loads the new files.

---

## 5. Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api/*` to `http://127.0.0.1:8000`,
so the backend must be running.

### Dashboard pages

| Page | Content |
|---|---|
| Overview | National KPIs, road type distribution, top provinces by length and density, **road km per 1,000 people** |
| Map Explorer | Per-province road map with road type filters. Major roads are always kept complete; minor roads are sampled for large provinces |
| Road Infrastructure | Road length and count by type and province, density, **road length per capita by province** |
| Regional Comparison | Side-by-side comparison of two provinces, including **population and road km per 1,000 people** |
| Machine Learning | Metrics, confusion matrix, feature importance (includes **population density**), province ranking |
| Graph Analytics | Per-province graph summary, most important intersections, degree distribution |
| Data Explorer | Server-side paginated road records |
| About Dataset | Sources, processing status, limitations, **BPS population dataset notes** |

---

## 6. Methodology

- **Accessibility index.** A weighted combination of min-max normalized
  metrics: road density, intersection density, major-road ratio, network
  density and average node degree. The weights and the Low (0-39) / Medium
  (40-69) / High (70-100) thresholds are in `backend/app/config.py`.
- **Population join.** `demographic_join.py` merges BPS population into the
  region features and adds `road_km_per_1000_people`. Province names are
  matched case-insensitively, with an explicit mapping
  (`PROVINCE_NAME_MAP_TO_BPS` in `config.py`) for names that differ between the
  boundary source and BPS. Provinces with no safe match get `null` population
  instead of a guessed value.
- **Machine learning.** A Random Forest is trained to reproduce the
  index-derived classes from the underlying features, which now include
  `population_density_bps`. This is not supervised learning against an
  official label, because no official accessibility label exists in OpenStreetMap.
- **Graph analytics.** One graph per province. Exact betweenness centrality is
  too expensive at this scale, so provinces above 3,000 nodes use a sampled
  approximation (k = 500). This is flagged in the API and the UI. The top 20
  nodes per province are stored.

### Main generated files

| File | Produced by |
|---|---|
| `data/processed/roads.parquet`, `nodes.parquet` | `preprocess.py` |
| `data/processed/province_summary.parquet` | `aggregate_regions.py` (PySpark) |
| `data/processed/graph_metrics.parquet`, `graph_node_centrality.parquet` | `graph_analysis.py` |
| `data/processed/region_features.parquet`, `demographics.parquet` | `feature_engineering.py`, `demographic_join.py` |
| `data/processed/accessibility_scores.parquet`, `ml_predictions.parquet` | `feature_engineering.py`, `train_ml.py` |
| `data/models/accessibility_model.pkl` | `train_ml.py` |
| `data/geojson/<province>.geojson` | `export_geojson.py` |
| `data/outputs/*.json` | various stages |

---

## 7. Data sources and attribution

- Road data: © OpenStreetMap contributors, available under the
  [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
  Extract provided by Geofabrik.
- Population data: Badan Pusat Statistik (BPS), Statistics Indonesia.
- Province boundaries: a community GeoJSON from the
  [superpikar/indonesia-geojson](https://github.com/superpikar/indonesia-geojson)
  repository, converted with `prepare_boundaries.py`. Check that repository's
  terms before redistributing the file outside this project.
- Map tiles: OpenStreetMap standard tiles with a CSS filter to mute their colours.

---

## 8. Known limitations

- **Province boundaries are outdated.** The boundary source has 32 provinces
  and predates Indonesia's 2022 Papua split (BPS lists 38 provinces). It also
  uses old names such as `Irian Jaya Barat`, `Irian Jaya Tengah` and
  `Irian Jaya Timur`, has no Kepulauan Riau, Sulawesi Barat or Kalimantan
  Utara polygons, and contains the typo `Probanten` for Banten.
- **Population join covers 31 of 32 provinces.** `Irian Jaya Timur` has no
  safe modern BPS equivalent and shows population as unavailable. Roads in
  provinces that have no polygon are assigned to a neighbouring province, so
  per-province totals for those areas are approximate.
- **Class imbalance in the ML task.** The accessibility index gives about 30
  Low, 1 Medium and 1 High province. With so few provinces and such imbalance,
  accuracy is not a reliable measure. Use macro F1 and treat the per-class
  results as illustrative.
- **OpenStreetMap is community-maintained.** Completeness varies by region,
  road existence does not imply road quality, and OSM alone cannot measure
  congestion or travel demand.
- **The accessibility score is not an official index.** It describes road
  network structure relative to area and population. Low-scoring provinces
  are candidates for further assessment, not proof that infrastructure is needed.
- **Batch processing.** Data comes from one static snapshot of each source.
  Geofabrik also publishes incremental `.osc` diffs, which could be used to
  update the data without reprocessing everything.
- **Spark runs in local mode** on a single machine, not on a cluster.
- **Pipeline status label.** After `--resume`, `data/outputs/pipeline_status.json`
  keeps the mode recorded by the last full pipeline run. If that run was a
  `--sample` run, the About Dataset page keeps showing "sample mode" even
  though the data is the full dataset.

---

## 9. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Unable to find a usable engine ... pyarrow` | The venv is not active. The prompt must start with `(venv)` |
| `pip install` fails building pandas | Wrong Python version. Use Python 3.11 |
| `java` not recognized, or PySpark fails to start | Install Java 17 and restart the terminal and VS Code |
| `Raw OSM file not found` | The file must be named exactly `indonesia-latest.osm.pbf` and sit in `backend/data/raw/` |
| Dashboard says the dataset has not been processed | Run the pipeline, then restart `uvicorn` |
| Map shows an "API key required" watermark | The basemap URL points at CARTO tiles. Use the OpenStreetMap tile URL in the map pages |