import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 30000,
});

// Normalizes errors so components can read `.status` and `.message`
// consistently, including our backend's 503 "not processed yet" shape.
client.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    return Promise.reject({
      status,
      message: detail || error.message || "Unexpected error",
      notProcessed: status === 503,
    });
  }
);

export const api = {
  health: () => client.get("/health").then((r) => r.data),
  pipelineStatus: () => client.get("/pipeline-status").then((r) => r.data),

  overview: () => client.get("/overview").then((r) => r.data),
  provinces: () => client.get("/provinces").then((r) => r.data),
  cities: () => client.get("/cities").then((r) => r.data),
  roadTypes: () => client.get("/road-types").then((r) => r.data),
  provinceRankings: () => client.get("/province-rankings").then((r) => r.data),
  roadTypeDistribution: () => client.get("/road-type-distribution").then((r) => r.data),
    topProvincesByDensity: (limit = 10) =>
    client.get("/top-provinces-by-density", { params: { limit } }).then((r) => r.data),
  topProvincesByRoadPerCapita: (limit = 10) =>
    client.get("/top-provinces-by-road-per-capita", { params: { limit } }).then((r) => r.data),

  roads: (params) => client.get("/roads", { params }).then((r) => r.data),
  road: (osmId) => client.get(`/roads/${osmId}`).then((r) => r.data),

  regionSummary: (region) => client.get(`/regions/${encodeURIComponent(region)}/summary`).then((r) => r.data),
  regionRoads: (region, params) =>
    client.get(`/regions/${encodeURIComponent(region)}/roads`, { params }).then((r) => r.data),
  regionGeojson: (region) =>
    client.get(`/regions/${encodeURIComponent(region)}/geojson`).then((r) => r.data),
  geojsonManifest: () => client.get("/geojson-manifest").then((r) => r.data),
  compare: (regionA, regionB) =>
    client.get("/compare", { params: { region_a: regionA, region_b: regionB } }).then((r) => r.data),

  mlMetrics: () => client.get("/ml/metrics").then((r) => r.data),
  mlFeatureImportance: () => client.get("/ml/feature-importance").then((r) => r.data),
  mlPredictions: () => client.get("/ml/predictions").then((r) => r.data),

  graphNationalSummary: () => client.get("/graph/summary").then((r) => r.data),
  graphAllProvinces: () => client.get("/graph/provinces").then((r) => r.data),
  graphRegionSummary: (region) => client.get(`/graph/${encodeURIComponent(region)}/summary`).then((r) => r.data),
  graphRegionCentrality: (region, limit = 10) =>
    client.get(`/graph/${encodeURIComponent(region)}/centrality`, { params: { limit } }).then((r) => r.data),
  graphRegionNodes: (region, limit = 200) =>
    client.get(`/graph/${encodeURIComponent(region)}/nodes`, { params: { limit } }).then((r) => r.data),
  graphDegreeDistribution: (region) =>
    client.get(`/graph/${encodeURIComponent(region)}/degree-distribution`).then((r) => r.data),
};

export default api;
