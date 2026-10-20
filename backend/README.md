# Backend — Indonesia Road Infrastructure API

See the top-level `README.md` for full setup instructions. Quick reference:

```bash
python -m venv venv && source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# place indonesia-latest.osm.pbf into data/raw/, then:
python processing/run_pipeline.py --sample    # or --full

uvicorn app.main:app --reload
```

- Swagger docs: http://127.0.0.1:8000/docs
- Config (paths, accessibility weights/thresholds, graph limits): `app/config.py`
- Pipeline stages: `processing/` (run via `processing/run_pipeline.py`)
- API routers: `app/api/`
- Data access layer: `app/services/`
