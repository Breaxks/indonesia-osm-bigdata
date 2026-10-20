import AltRouteIcon from "@mui/icons-material/AltRoute";
import GroupsIcon from "@mui/icons-material/Groups";
import HubIcon from "@mui/icons-material/Hub";
import MapIcon from "@mui/icons-material/Map";
import RouteIcon from "@mui/icons-material/Route";
import SignpostIcon from "@mui/icons-material/Signpost";
import SpeedIcon from "@mui/icons-material/Speed";
import { Box, Grid, Stack, Typography, useTheme } from "@mui/material";
import { useCallback } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import ChartPanel from "../components/ChartPanel.jsx";
import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import KpiCard from "../components/KpiCard.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

const PIE_COLORS = [tokens.amber, tokens.teal, tokens.coral, "#7C9CF2", "#B98BF0", "#6FD08C", "#E8912C", "#4C8FE2"];

export default function Overview() {
  const overview = useFetch(useCallback(() => api.overview(), []));
  const roadTypeDist = useFetch(useCallback(() => api.roadTypeDistribution(), []));
  const rankings = useFetch(useCallback(() => api.provinceRankings(), []));
  const density = useFetch(useCallback(() => api.topProvincesByDensity(10), []));

  const notProcessed = overview.notProcessed || roadTypeDist.notProcessed;
  const anyError = overview.error || roadTypeDist.error || rankings.error || density.error;

  if (notProcessed) return <DatasetNotProcessedAlert />;
  if (anyError) return <ErrorAlert message={anyError} />;

  const o = overview.data || {};
  const roadTypeData = (roadTypeDist.data || []).map((d) => ({
    name: d.highway,
    value: Math.round((d.total_length_m || 0) / 1000),
  }));

  const topByLength = (rankings.data?.by_total_length_km || []).slice(0, 10);
  const topByDensity = (density.data || []).slice(0, 10);

  const majorPct = o.major_road_percentage ?? 0;
  const insight1 = topByLength[0]
    ? `${topByLength[0].province} has the longest mapped road network at ${topByLength[0].total_length_km?.toLocaleString()} km.`
    : null;
  const insight2 = `Major roads (motorway/trunk/primary/secondary) make up ${majorPct}% of all mapped segments nationally; the remainder is predominantly local/residential infrastructure.`;

  return (
    <Box>
      <PageHeader
        title="Road Infrastructure Overview"
        subtitle="Executive summary derived from the processed OpenStreetMap Indonesia extract."
      />

      <Grid container spacing={2.5} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Total Road Segments"
            value={(o.total_road_segments ?? 0).toLocaleString()}
            icon={<RouteIcon />}
            accent="amber"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Total Road Length"
            value={(o.total_road_length_km ?? 0).toLocaleString()}
            suffix="km"
            icon={<AltRouteIcon />}
            accent="teal"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Provinces Covered"
            value={o.number_of_provinces ?? 0}
            icon={<MapIcon />}
            accent="amber"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Road Types"
            value={o.number_of_road_types ?? 0}
            icon={<SignpostIcon />}
            accent="teal"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Avg Segment Length"
            value={(o.average_segment_length_m ?? 0).toFixed?.(0) ?? o.average_segment_length_m}
            suffix="m"
            icon={<SpeedIcon />}
            accent="coral"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Major Road Share"
            value={`${majorPct}`}
            suffix="%"
            icon={<SignpostIcon />}
            accent="amber"
            loading={overview.loading}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Avg Accessibility Score"
            value={o.accessibility_score_avg ?? "--"}
            suffix="/100"
            icon={<HubIcon />}
            accent="teal"
            loading={overview.loading}
            // hint="Composite index, see Machine Learning page"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Road per 1,000 People"
            value={o.road_km_per_1000_people_avg ?? "--"}
            suffix="km"
            icon={<GroupsIcon />}
            accent="coral"
            loading={overview.loading}
            hint={
              o.population_matched_provinces
                ? `BPS population data, ${o.population_matched_provinces}/${o.population_total_provinces} provinces matched`
                : "BPS population data (second dataset)"
            }
          />
        </Grid>
      </Grid>

      <Grid container spacing={2.5} sx={{ mt: 0.5 }}>
        <Grid item xs={12} md={5}>
          <ChartPanel
            title="Road Type Distribution"
            subtitle="Share of total mapped road length by highway type (km)"
            accent="amber"
            loading={roadTypeDist.loading}
            height={340}
          >
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={roadTypeData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={2}
                >
                  {roadTypeData.map((entry, idx) => (
                    <Cell key={entry.name} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) => [`${v.toLocaleString()} km`, "Length"]}
                  contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }}
                  itemStyle={{ color: tokens.text }}
                  labelStyle={{ color: tokens.text }}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12} md={7}>
          <ChartPanel
            title="Top 10 Provinces by Road Length"
            subtitle="Total mapped road length (km)"
            accent="teal"
            loading={rankings.loading}
            height={340}
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={topByLength} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} horizontal={false} />
                <XAxis type="number" stroke={tokens.textMuted} fontSize={12} />
                <YAxis
                  type="category"
                  dataKey="province"
                  stroke={tokens.textMuted}
                  fontSize={12}
                  width={110}
                />
                <Tooltip
                  formatter={(v) => [`${v.toLocaleString()} km`, "Length"]}
                  contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }}
                  itemStyle={{ color: tokens.text }}
                  labelStyle={{ color: tokens.text }}
                />
                <Bar dataKey="total_length_km" fill={tokens.teal} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel
            title="Top 10 Provinces by Road Density"
            subtitle="Kilometers of road per square kilometer of province area"
            accent="amber"
            loading={density.loading}
            height={300}
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topByDensity}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="province" stroke={tokens.textMuted} fontSize={11} angle={-20} textAnchor="end" height={70} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="road_density_km_per_km2" fill={tokens.amber} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel title="Road Infrastructure Summary" accent="coral" loading={overview.loading} height={110}>
            <Stack spacing={1}>
              {insight1 && <Typography variant="body2">{insight1}</Typography>}
              <Typography variant="body2">{insight2}</Typography>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                Insights are computed directly from the processed dataset, not generated text.
              </Typography>
            </Stack>
          </ChartPanel>
        </Grid>
      </Grid>
    </Box>
  );
}
