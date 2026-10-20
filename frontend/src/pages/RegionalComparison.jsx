import { Autocomplete, Box, Card, Grid, Stack, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ChartPanel from "../components/ChartPanel.jsx";
import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

const METRICS = [
  { key: "total_length_km", label: "Total road length (km)" },
  { key: "road_density_km_per_km2", label: "Road density (km/km²)" },
  { key: "segment_count", label: "Road segment count" },
  { key: "nodes", label: "Intersections (nodes)" },
  { key: "intersection_density_per_km2", label: "Intersection density (/km²)" },
  { key: "major_road_pct", label: "Major road %" },
  { key: "avg_length_m", label: "Avg segment length (m)" },
  { key: "network_density", label: "Network connectivity (graph density)" },
  { key: "population", label: "Population (BPS)" },
  { key: "road_km_per_1000_people", label: "Road per 1,000 people (km)" },
  { key: "accessibility_score", label: "ML accessibility score (0-100)" },
];

function fmt(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return "--";
  if (typeof v === "number") return Number.isInteger(v) ? v.toLocaleString() : v.toFixed(3);
  return v;
}

export default function RegionalComparison() {
  const provincesRes = useFetch(useCallback(() => api.provinces(), []));
  const [regionA, setRegionA] = useState(null);
  const [regionB, setRegionB] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const provinces = provincesRes.data || [];

  useEffect(() => {
    if (!regionA && provinces.length > 0) setRegionA(provinces[0]);
    if (!regionB && provinces.length > 1) setRegionB(provinces[1]);
  }, [provinces, regionA, regionB]);

  useEffect(() => {
    if (!regionA || !regionB || regionA === regionB) return;
    setLoading(true);
    setError(null);
    api
      .compare(regionA, regionB)
      .then((res) => setCompareData(res))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [regionA, regionB]);

  if (provincesRes.notProcessed) return <DatasetNotProcessedAlert />;
  if (provincesRes.error) return <ErrorAlert message={provincesRes.error} />;

  const a = compareData?.region_a;
  const b = compareData?.region_b;

  const barData = a && b
    ? METRICS.filter((m) => !["accessibility_score"].includes(m.key)).map((m) => ({
        metric: m.label,
        [regionA]: Number(a[m.key]) || 0,
        [regionB]: Number(b[m.key]) || 0,
      }))
    : [];

  // Radar chart needs comparable 0-1-ish scale -- normalize each metric
  // against the max of the two regions being compared.
  const radarData = a && b
    ? METRICS.map((m) => {
        const av = Number(a[m.key]) || 0;
        const bv = Number(b[m.key]) || 0;
        const max = Math.max(av, bv, 1e-9);
        return { metric: m.label.split(" (")[0], [regionA]: (av / max) * 100, [regionB]: (bv / max) * 100 };
      })
    : [];

  return (
    <Box>
      <PageHeader
        title="Regional Comparison"
        subtitle="Compare two provinces across road infrastructure, connectivity, and accessibility metrics."
      />

      <Card sx={{ p: 2, mb: 2.5 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <Autocomplete
              size="small"
              options={provinces}
              value={regionA}
              onChange={(_, v) => setRegionA(v)}
              renderInput={(params) => <TextField {...params} label="Region A" />}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Autocomplete
              size="small"
              options={provinces}
              value={regionB}
              onChange={(_, v) => setRegionB(v)}
              renderInput={(params) => <TextField {...params} label="Region B" />}
            />
          </Grid>
        </Grid>
      </Card>

      {error && <ErrorAlert message={error} />}
      {regionA === regionB && (
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
          Select two different regions to compare.
        </Typography>
      )}

      {a && b && regionA !== regionB && (
        <>
          <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
            {[
              { region: regionA, data: a },
              { region: regionB, data: b },
            ].map(({ region, data }) => (
              <Grid item xs={12} md={6} key={region}>
                <Card sx={{ p: 2.5 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                    {region}
                  </Typography>
                  <Stack spacing={0.75}>
                    {METRICS.map((m) => {
                      const other = data === a ? b : a;
                      const isHigher = Number(data[m.key]) > Number(other[m.key]);
                      return (
                        <Stack key={m.key} direction="row" justifyContent="space-between">
                          <Typography variant="body2" sx={{ color: "text.secondary" }}>
                            {m.label}
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{
                              fontWeight: isHigher ? 700 : 500,
                              color: isHigher ? tokens.teal : "text.primary",
                            }}
                          >
                            {fmt(data[m.key])}
                          </Typography>
                        </Stack>
                      );
                    })}
                    {data.accessibility_class && (
                      <Stack direction="row" justifyContent="space-between" sx={{ pt: 0.5 }}>
                        <Typography variant="body2" sx={{ color: "text.secondary" }}>
                          Accessibility class
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>
                          {data.accessibility_class}
                        </Typography>
                      </Stack>
                    )}
                  </Stack>
                </Card>
              </Grid>
            ))}
          </Grid>

          <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2 }}>
            A highlighted (teal) value is simply higher between the two regions -- higher is not
            automatically "better" for every metric (e.g. a very high average segment length can
            also reflect sparser mapping).
          </Typography>

          <Grid container spacing={2.5}>
            <Grid item xs={12} md={7}>
              <ChartPanel title="Metric Comparison" accent="teal" loading={loading} height={380}>
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={barData} layout="vertical" margin={{ left: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} horizontal={false} />
                    <XAxis type="number" stroke={tokens.textMuted} fontSize={11} />
                    <YAxis type="category" dataKey="metric" stroke={tokens.textMuted} fontSize={10} width={160} />
                    <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey={regionA} fill={tokens.amber} radius={[0, 3, 3, 0]} />
                    <Bar dataKey={regionB} fill={tokens.teal} radius={[0, 3, 3, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartPanel>
            </Grid>
            <Grid item xs={12} md={5}>
              <ChartPanel title="Relative Profile" subtitle="Each metric normalized to the higher of the two regions" accent="amber" loading={loading} height={380}>
                <ResponsiveContainer width="100%" height={360}>
                  <RadarChart data={radarData}>
                    <PolarGrid stroke={tokens.border} />
                    <PolarAngleAxis dataKey="metric" stroke={tokens.textMuted} fontSize={9} />
                    <PolarRadiusAxis stroke={tokens.textMuted} fontSize={9} />
                    <Radar name={regionA} dataKey={regionA} stroke={tokens.amber} fill={tokens.amber} fillOpacity={0.25} />
                    <Radar name={regionB} dataKey={regionB} stroke={tokens.teal} fill={tokens.teal} fillOpacity={0.25} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </ChartPanel>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}
