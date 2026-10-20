"""One-time helper: converts the downloaded province source file into the
fallback boundaries file preprocess.py expects (a 'province' property)."""
import json
from pathlib import Path

src = Path("data/geojson/_raw_province_source.json")
dst = Path("data/geojson/_province_boundaries_fallback.geojson")

data = json.loads(src.read_text(encoding="utf-8"))

for feature in data["features"]:
    props = feature["properties"]
    name = props.get("Propinsi") or props.get("PROVINSI") or props.get("province")
    if name:
        feature["properties"] = {"province": name.title()}

dst.write_text(json.dumps(data), encoding="utf-8")
print(f"Wrote {len(data['features'])} provinces to {dst}")