// Static-site version of the API layer.
//
// Instead of calling the FastAPI backend, every function reads a JSON file
// from  public/data/  (created by backend/export_static.py). The function
// names and return shapes are the same as before, so no page needs changing.
import axios from "axios";

// import.meta.env.BASE_URL is "/" locally and "/<repo-name>/" on GitHub Pages.
const BASE = (import.meta.env.BASE_URL || "/").replace(/\/?$/, "/");

const client = axios.create({
  baseURL: `${BASE}data/`,
  timeout: 60000,
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error.response?.status;
    return Promise.reject({
      status,
      message:
        status === 404
          ? "Data file not found. Run backend/export_static.py and redeploy."
          : error.message || "Unexpected error",
      notProcessed: false,
    });
  }
);

// Must match slugify() in backend/export_static.py
export const slugify = (name) =>
  String(name).toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "unknown";

const getJson = (path) =>
  client.get(path).then((r) => {
    // The dev server answers a missing file with index.html; treat that as an error.
    if (typeof r.data === "string" && r.data.trim().startsWith("<")) {
      throw { status: 404, message: "Data file not found. Run backend/export_static.py first." };
    }
    return r.data;
  });

// --- Data Explorer: roads are a pre-exported sample, filtered in the browser ---
const roadCache = new Map();
const loadRoads = (key) => {
  if (!roadCache.has(key)) {
    roadCache.set(
      key,
      getJson(`roads/${key}.json`).catch((e) => {
        roadCache.delete(key);
        if (e?.status === 404 && key !== "_top") return []; // province with no roads file
        throw e;
      })
    );
  }
  return roadCache.get(key);
};

const queryRoads = async ({ page = 1, page_size = 50, province, road_type, search } = {}) => {
  let items = await loadRoads(province ? slugify(province) : "_top");
  if (road_type) items = items.filter((r) => r.highway === road_type);
  if (search) {
    const q = search.toLowerCase();
    items = items.filter((r) => String(r.name || "").toLowerCase().includes(q));
  }
  const total_items = items.length;
  const total_pages = Math.max(1, Math.ceil(total_items / page_size));
  const p = Math.min(Math.max(1, page), total_pages);
  return {
    items: items.slice((p - 1) * page_size, p * page_size),
    page: p,
    page_size,
    total_items,
    total_pages,
  };
};

export const api = {
  health: () => Promise.resolve({ status: "ok", dataset_processed: true }),
  pipelineStatus: () => getJson("pipeline_status.json"),

  overview: () => getJson("overview.json"),
  provinces: () => getJson("provinces.json"),
  cities: () => Promise.resolve([]),
  roadTypes: () => getJson("road_types.json"),
  provinceRankings: () => getJson("province_rankings.json"),
  roadTypeDistribution: () => getJson("road_type_distribution.json"),
  topProvincesByDensity: (limit = 10) => getJson("top_density.json").then((d) => d.slice(0, limit)),
  topProvincesByRoadPerCapita: (limit = 10) => getJson("top_per_capita.json").then((d) => d.slice(0, limit)),

  roads: (params) => queryRoads(params),
  road: () => Promise.reject({ status: 404, message: "Single-road lookup is not available in the static version." }),

  regionSummary: (region) => getJson(`regions/${slugify(region)}/summary.json`),
  regionRoads: (region, params) => queryRoads({ ...params, province: region }),
  regionGeojson: (region) => getJson(`geojson/${slugify(region)}.geojson`),
  geojsonManifest: () => getJson("geojson/_manifest.json"),
  compare: (regionA, regionB) =>
    Promise.all([api.regionSummary(regionA), api.regionSummary(regionB)]).then(([a, b]) => ({
      region_a: a,
      region_b: b,
    })),

  mlMetrics: () => getJson("ml/metrics.json"),
  mlFeatureImportance: () => getJson("ml/feature_importance.json"),
  mlPredictions: () => getJson("ml/predictions.json"),

  graphNationalSummary: () => getJson("graph/summary.json"),
  graphAllProvinces: () => getJson("graph/provinces.json"),
  graphRegionSummary: (region) => getJson(`graph/${slugify(region)}/summary.json`),
  graphRegionCentrality: (region, limit = 10) =>
    getJson(`graph/${slugify(region)}/centrality.json`).then((d) => d.slice(0, limit)),
  graphRegionNodes: (region, limit = 200) =>
    getJson(`graph/${slugify(region)}/nodes.json`).then((d) => d.slice(0, limit)),
  graphDegreeDistribution: (region) => getJson(`graph/${slugify(region)}/degree_distribution.json`),
};

export default api;
