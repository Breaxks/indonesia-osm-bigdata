import MapIcon from "@mui/icons-material/Map";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  Chip,
  FormControlLabel,
  Grid,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import L from "leaflet";
import { useCallback, useEffect, useMemo, useState } from "react";
import { GeoJSON, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";

import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

const MAJOR_TYPES = new Set([
  "motorway", "motorway_link", "trunk", "trunk_link",
  "primary", "primary_link", "secondary", "secondary_link",
]);

const HIGHWAY_COLORS = {
  motorway: "#E2574C", motorway_link: "#E2574C",
  trunk: "#F2A93B", trunk_link: "#F2A93B",
  primary: "#F2C94C", primary_link: "#F2C94C",
  secondary: "#3FBFAE", secondary_link: "#3FBFAE",
  tertiary: "#6FD0C8", tertiary_link: "#6FD0C8",
  residential: "#7C9CF2", service: "#5A6B8C",
  unclassified: "#8592AC", living_street: "#B98BF0",
};

// Shown at the top of the Road Type dropdown so there's an explicit,
// unambiguous way to say "don't filter by type" instead of relying on
// the user knowing to clear the field.
const ALL_ROAD_TYPES = "All road types";

// Zooms/pans the map to fit whatever GeoJSON is currently loaded, so
// picking a province actually flies to that province instead of staying
// zoomed out on the whole country.
function FitBounds({ geojson }) {
  const map = useMap();
  useEffect(() => {
    if (!geojson || !geojson.features || geojson.features.length === 0) return;
    try {
      const layer = L.geoJSON(geojson);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [20, 20] });
      }
    } catch {
      // ignore malformed geometry -- map just stays at its current view
    }
  }, [geojson, map]);
  return null;
}

export default function MapExplorer() {
  const manifest = useFetch(useCallback(() => api.geojsonManifest(), []));
  const roadTypesRes = useFetch(useCallback(() => api.roadTypes(), []));

  // Draft = whatever is currently selected in the controls, not yet
  // applied to the map. Applied = what the map is actually showing.
  // Nothing changes on the map until "Show Roads" is clicked, so picking
  // through options doesn't cause the map to flicker/refetch on every click.
  const [draftProvince, setDraftProvince] = useState(null);
  const [draftRoadType, setDraftRoadType] = useState(ALL_ROAD_TYPES);
  const [draftMajorOnly, setDraftMajorOnly] = useState(true);

  const [appliedProvince, setAppliedProvince] = useState(null);
  const [appliedRoadType, setAppliedRoadType] = useState(null);
  const [appliedMajorOnly, setAppliedMajorOnly] = useState(true);

  const [geojson, setGeojson] = useState(null);
  const [loadingGeojson, setLoadingGeojson] = useState(false);
  const [geoError, setGeoError] = useState(null);

  const provinceOptions = useMemo(
    () => (manifest.data || []).map((m) => m.province).sort(),
    [manifest.data]
  );

  const roadTypeOptions = useMemo(
    () => [ALL_ROAD_TYPES, ...(roadTypesRes.data || [])],
    [roadTypesRes.data]
  );

  // On first load, once we know the province list, default both the
  // draft controls and the applied/rendered map to the first province
  // so there's something on screen immediately.
  useEffect(() => {
    if (!draftProvince && provinceOptions.length > 0) {
      setDraftProvince(provinceOptions[0]);
      setAppliedProvince(provinceOptions[0]);
    }
  }, [provinceOptions, draftProvince]);

  useEffect(() => {
    if (!appliedProvince) return;
    setLoadingGeojson(true);
    setGeoError(null);
    api
      .regionGeojson(appliedProvince)
      .then((fc) => setGeojson(fc))
      .catch((err) => setGeoError(err.message))
      .finally(() => setLoadingGeojson(false));
  }, [appliedProvince]);

  const handleShowRoads = () => {
    setAppliedProvince(draftProvince);
    setAppliedRoadType(draftRoadType === ALL_ROAD_TYPES ? null : draftRoadType);
    setAppliedMajorOnly(draftMajorOnly);
  };

  const filteredGeojson = useMemo(() => {
    if (!geojson) return null;
    let features = geojson.features;
    if (appliedRoadType) {
      features = features.filter((f) => f.properties.highway === appliedRoadType);
    }
    if (appliedMajorOnly) {
      features = features.filter((f) => MAJOR_TYPES.has(f.properties.highway));
    }
    return { ...geojson, features };
  }, [geojson, appliedRoadType, appliedMajorOnly]);

  if (manifest.notProcessed) return <DatasetNotProcessedAlert />;
  if (manifest.error) return <ErrorAlert message={manifest.error} />;

  const style = (feature) => ({
    color: HIGHWAY_COLORS[feature.properties.highway] || tokens.textMuted,
    weight: MAJOR_TYPES.has(feature.properties.highway) ? 3 : 1.5,
    opacity: 0.9,
  });

  const onEachFeature = (feature, layer) => {
    const p = feature.properties;
    layer.bindPopup(
      `<div style="font-family:Inter,sans-serif;font-size:13px;min-width:180px">
        <strong>${p.name || "Unnamed road"}</strong><br/>
        OSM ID: ${p.osm_id}<br/>
        Type: ${p.highway}<br/>
        Length: ${Math.round(p.length_m)} m<br/>
        One-way: ${p.oneway ? "Yes" : "No"}<br/>
        Lanes: ${p.lanes ?? "-"}<br/>
        Surface: ${p.surface ?? "-"}<br/>
        Max speed: ${p.maxspeed ?? "-"}
      </div>`
    );
  };

  return (
    <Box>
      <PageHeader
        title="Map Explorer"
        subtitle="Interactive road network map, loaded per-region to keep the browser responsive."
      />

      <Card sx={{ p: 2, mb: 2.5 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} sm={3}>
            <Autocomplete
              size="small"
              options={provinceOptions}
              value={draftProvince}
              onChange={(_, v) => setDraftProvince(v)}
              renderInput={(params) => <TextField {...params} label="Province" />}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <Autocomplete
              size="small"
              options={roadTypeOptions}
              value={draftRoadType}
              onChange={(_, v) => setDraftRoadType(v || ALL_ROAD_TYPES)}
              renderInput={(params) => <TextField {...params} label="Road Type" />}
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <FormControlLabel
              control={<Switch checked={draftMajorOnly} onChange={(e) => setDraftMajorOnly(e.target.checked)} />}
              label="Major roads only"
            />
          </Grid>
          <Grid item xs={12} sm={3}>
            <Stack spacing={0.75} alignItems="center">
              <Button
                fullWidth
                variant="contained"
                startIcon={<MapIcon />}
                onClick={handleShowRoads}
                disabled={!draftProvince || loadingGeojson}
              >
                {loadingGeojson ? "Loading..." : "Show Roads"}
              </Button>
              {filteredGeojson && (
                <Chip
                  size="small"
                  label={`${filteredGeojson.features.length.toLocaleString()} roads`}
                  sx={{ bgcolor: "rgba(63,191,174,0.12)", color: tokens.teal }}
                />
              )}
            </Stack>
          </Grid>
        </Grid>
      </Card>

      {geoError && <ErrorAlert message={geoError} />}

      <Card sx={{ p: 0, overflow: "hidden" }}>
        {loadingGeojson ? (
          <Skeleton variant="rectangular" height={600} sx={{ bgcolor: "rgba(255,255,255,0.06)" }} />
        ) : (
          <MapContainer center={[-2.5, 118]} zoom={5} style={{ height: 600, width: "100%" }}>
            <TileLayer
              url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
              className="muted-tiles"
            />
            {filteredGeojson && (
              <GeoJSON
                key={`${appliedProvince}-${appliedRoadType}-${appliedMajorOnly}`}
                data={filteredGeojson}
                style={style}
                onEachFeature={onEachFeature}
              />
            )}
            <FitBounds geojson={filteredGeojson} />
          </MapContainer>
        )}
      </Card>
      <Typography variant="caption" sx={{ color: "text.secondary", mt: 1, display: "block" }}>
        Geometry is simplified and loaded per-province to avoid rendering the entire national
        network at once. Pick your filters, then click "Show Roads". Click a road segment on the
        map for details.
      </Typography>
    </Box>
  );
}