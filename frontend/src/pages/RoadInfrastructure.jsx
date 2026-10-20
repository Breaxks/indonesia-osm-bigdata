import { Box, Card, Grid, Stack, Typography } from "@mui/material";
import { useCallback, useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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

export default function RoadInfrastructure() {
  const overview = useFetch(useCallback(() => api.overview(), []));
  const roadTypeDist = useFetch(useCallback(() => api.roadTypeDistribution(), []));
  const rankings = useFetch(useCallback(() => api.provinceRankings(), []));
  const density = useFetch(useCallback(() => api.topProvincesByDensity(15), []));
  const perCapita = useFetch(useCallback(() => api.topProvincesByRoadPerCapita(15), []));

  const notProcessed = overview.notProcessed || roadTypeDist.notProcessed;
  const anyError = overview.error || roadTypeDist.error || rankings.error || density.error;
  if (notProcessed) return <DatasetNotProcessedAlert />;
  if (anyError) return <ErrorAlert message={anyError} />;

  const o = overview.data || {};
  const roadTypeData = roadTypeDist.data || [];
  const lengthByType = roadTypeData.map((d) => ({
    highway: d.highway,
    length_km: Math.round((d.total_length_m || 0) / 1000),
  }));
  const countByType = roadTypeData.map((d) => ({
    highway: d.highway,
    count: d.segment_count,
  }));
  const avgLenByType = roadTypeData.map((d) => ({
    highway: d.highway,
    avg_m: Math.round(d.avg_length_m || 0),
  }));

  const topByLength = (rankings.data?.by_total_length_km || []);
  const topByDensity = density.data || [];

  const majorPct = o.major_road_percentage ?? 0;
  const localPct = (100 - majorPct).toFixed(1);
  const ratioData = [
    { name: "Major roads", value: majorPct },
    { name: "Local roads", value: 100 - majorPct },
  ];

  return (
    <Box>
      <PageHeader
        title="Road Infrastructure"
        subtitle="Detailed infrastructure metrics derived from the processed road network."
      />

      <Grid container spacing={2.5} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Total Road Length" value={(o.total_road_length_km ?? 0).toLocaleString()} suffix="km" accent="teal" loading={overview.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Road Segments" value={(o.total_road_segments ?? 0).toLocaleString()} accent="amber" loading={overview.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Avg Segment Length" value={(o.average_segment_length_m ?? 0).toFixed?.(0)} suffix="m" accent="coral" loading={overview.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Major Road %" value={majorPct} suffix="%" accent="amber" loading={overview.loading} />
        </Grid>
      </Grid>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={7}>
          <ChartPanel title="Road Length by Highway Type" subtitle="Total km per type" accent="teal" loading={roadTypeDist.loading} height={320}>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={lengthByType}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="highway" stroke={tokens.textMuted} fontSize={11} angle={-25} textAnchor="end" height={70} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="length_km" fill={tokens.teal} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12} md={5}>
          <ChartPanel title="Major vs Local Road Ratio" accent="coral" loading={overview.loading} height={320}>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={ratioData} dataKey="value" nameKey="name" innerRadius={70} outerRadius={110} paddingAngle={3}>
                  <Cell fill={tokens.amber} />
                  <Cell fill={tokens.coral} />
                </Pie>
                <Tooltip formatter={(v) => `${v.toFixed(1)}%`} contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
              </PieChart>
            </ResponsiveContainer>
            <Typography variant="caption" sx={{ color: "text.secondary", display: "block", textAlign: "center", mt: -2 }}>
              {majorPct}% major &middot; {localPct}% local
            </Typography>
          </ChartPanel>
        </Grid>

        <Grid item xs={12} md={6}>
          <ChartPanel title="Road Count by Highway Type" subtitle="Number of segments per type" accent="amber" loading={roadTypeDist.loading} height={300}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={countByType}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="highway" stroke={tokens.textMuted} fontSize={11} angle={-25} textAnchor="end" height={70} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="count" fill={tokens.amber} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12} md={6}>
          <ChartPanel title="Average Segment Length by Type" subtitle="Meters per type" accent="teal" loading={roadTypeDist.loading} height={300}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={avgLenByType}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="highway" stroke={tokens.textMuted} fontSize={11} angle={-25} textAnchor="end" height={70} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="avg_m" fill={tokens.coral} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel title="Road Length by Province" subtitle="All provinces in the processed dataset" accent="teal" loading={rankings.loading} height={340}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={topByLength} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} horizontal={false} />
                <XAxis type="number" stroke={tokens.textMuted} fontSize={12} />
                <YAxis type="category" dataKey="province" stroke={tokens.textMuted} fontSize={12} width={110} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="total_length_km" fill={tokens.teal} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel title="Road Density by Province" subtitle="km of road per km² of province area" accent="amber" loading={density.loading} height={340}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={topByDensity}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="province" stroke={tokens.textMuted} fontSize={11} angle={-25} textAnchor="end" height={80} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="road_density_km_per_km2" fill={tokens.amber} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel
            title="Road Length per Capita by Province"
            subtitle="km of road per 1,000 people (BPS population, second dataset) -- reframes density around who actually uses the network, not just land area"
            accent="coral"
            loading={perCapita.loading}
            height={340}
          >
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={perCapita.data || []}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                <XAxis dataKey="province" stroke={tokens.textMuted} fontSize={11} angle={-25} textAnchor="end" height={80} />
                <YAxis stroke={tokens.textMuted} fontSize={12} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="road_km_per_1000_people" fill={tokens.coral} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>
      </Grid>
    </Box>
  );
}
