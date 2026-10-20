import { Autocomplete, Box, Card, Grid, Stack, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CircleMarker, MapContainer, Popup, TileLayer } from "react-leaflet";

import ChartPanel from "../components/ChartPanel.jsx";
import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import KpiCard from "../components/KpiCard.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

export default function GraphAnalytics() {
  const national = useFetch(useCallback(() => api.graphNationalSummary(), []));
  const provinces = useFetch(useCallback(() => api.provinces(), []));

  const [region, setRegion] = useState(null);
  const [regionSummary, setRegionSummary] = useState(null);
  const [centrality, setCentrality] = useState([]);
  const [degreeDist, setDegreeDist] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [loadingRegion, setLoadingRegion] = useState(false);
  const [regionError, setRegionError] = useState(null);

  const provinceOptions = provinces.data || [];

  useEffect(() => {
    if (!region && provinceOptions.length > 0) setRegion(provinceOptions[0]);
  }, [provinceOptions, region]);

  useEffect(() => {
    if (!region) return;
    setLoadingRegion(true);
    setRegionError(null);
    Promise.all([
      api.graphRegionSummary(region),
      api.graphRegionCentrality(region, 10),
      api.graphDegreeDistribution(region),
      api.graphRegionNodes(region, 150),
    ])
      .then(([summary, cent, dist, nodeList]) => {
        setRegionSummary(summary);
        setCentrality(cent);
        setDegreeDist(dist);
        setNodes(nodeList);
      })
      .catch((err) => setRegionError(err.message))
      .finally(() => setLoadingRegion(false));
  }, [region]);

  if (national.notProcessed || provinces.notProcessed) return <DatasetNotProcessedAlert />;
  if (national.error || provinces.error) return <ErrorAlert message={national.error || provinces.error} />;

  const n = national.data || {};
  const mapCenter = nodes.length > 0 ? [nodes[0].lat, nodes[0].lon] : [-2.5, 118];

  return (
    <Box>
      <PageHeader
        title="Graph Analytics"
        subtitle="Intersections as graph nodes, road segments as edges. Computed per-province for computational tractability."
      />

      {n.note && (
        <Card sx={{ p: 2, mb: 2.5, borderLeft: `3px solid ${tokens.teal}` }}>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {n.note}
          </Typography>
        </Card>
      )}

      <Grid container spacing={2.5} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={6} md={2.4}>
          <KpiCard label="Total Nodes" value={(n.total_nodes ?? 0).toLocaleString()} accent="amber" loading={national.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <KpiCard label="Total Edges" value={(n.total_edges ?? 0).toLocaleString()} accent="teal" loading={national.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <KpiCard label="Avg Degree (national)" value={n.avg_degree_national ?? "--"} accent="amber" loading={national.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <KpiCard label="Provinces Analyzed" value={n.provinces_analyzed ?? 0} accent="teal" loading={national.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={2.4}>
          <KpiCard label="Approx. Betweenness" value={n.provinces_with_approximate_betweenness ?? 0} suffix="provinces" accent="coral" loading={national.loading} />
        </Grid>
      </Grid>

      <Card sx={{ p: 2, mb: 2.5 }}>
        <Autocomplete
          size="small"
          sx={{ maxWidth: 320 }}
          options={provinceOptions}
          value={region}
          onChange={(_, v) => setRegion(v)}
          renderInput={(params) => <TextField {...params} label="Province for detailed graph analysis" />}
        />
      </Card>

      {regionError && <ErrorAlert message={regionError} />}

      {regionSummary && (
        <>
          <Grid container spacing={2.5} sx={{ mb: 1 }}>
            <Grid item xs={12} sm={6} md={2.4}>
              <KpiCard label="Nodes" value={(regionSummary.nodes ?? 0).toLocaleString()} accent="amber" loading={loadingRegion} />
            </Grid>
            <Grid item xs={12} sm={6} md={2.4}>
              <KpiCard label="Edges" value={(regionSummary.edges ?? 0).toLocaleString()} accent="teal" loading={loadingRegion} />
            </Grid>
            <Grid item xs={12} sm={6} md={2.4}>
              <KpiCard label="Avg Degree" value={regionSummary.avg_degree ?? "--"} accent="amber" loading={loadingRegion} />
            </Grid>
            <Grid item xs={12} sm={6} md={2.4}>
              <KpiCard label="Connected Components" value={regionSummary.connected_components ?? 0} accent="teal" loading={loadingRegion} />
            </Grid>
            <Grid item xs={12} sm={6} md={2.4}>
              <KpiCard label="Largest Component" value={(regionSummary.largest_component_size ?? 0).toLocaleString()} accent="coral" loading={loadingRegion} />
            </Grid>
          </Grid>

          {regionSummary.betweenness_approximate && (
            <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mb: 2 }}>
              This province's graph exceeds the exact-computation node limit, so betweenness
              centrality below is a k-sampled approximation, not an exact value.
            </Typography>
          )}

          <Grid container spacing={2.5}>
            <Grid item xs={12} md={6}>
              <ChartPanel title="Top 10 Most Important Nodes" subtitle="By betweenness centrality" accent="teal" loading={loadingRegion} height={320}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={centrality} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} horizontal={false} />
                    <XAxis type="number" stroke={tokens.textMuted} fontSize={11} />
                    <YAxis type="category" dataKey="node_id" stroke={tokens.textMuted} fontSize={9} width={110} />
                    <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                    <Bar dataKey="betweenness_centrality" fill={tokens.teal} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartPanel>
            </Grid>

            <Grid item xs={12} md={6}>
              <ChartPanel title="Intersection-Degree Distribution" subtitle="Number of nodes at each degree" accent="amber" loading={loadingRegion} height={320}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={degreeDist}>
                    <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} vertical={false} />
                    <XAxis dataKey="degree" stroke={tokens.textMuted} fontSize={11} label={{ value: "Degree", position: "insideBottom", offset: -4, fill: tokens.textMuted, fontSize: 11 }} />
                    <YAxis stroke={tokens.textMuted} fontSize={12} />
                    <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                    <Bar dataKey="count" fill={tokens.amber} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartPanel>
            </Grid>

            <Grid item xs={12}>
              <ChartPanel title="Important Graph Nodes on the Map" subtitle={`Top nodes by degree centrality in ${region}`} accent="coral" loading={loadingRegion} height={480}>
                <MapContainer center={mapCenter} zoom={9} style={{ height: 460, width: "100%", borderRadius: 6 }}>
                  <TileLayer
  			url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
  			attribution='&copy; OpenStreetMap contributors'
  			className="muted-tiles"
			/>
                  {nodes.map((node) => (
                    <CircleMarker
                      key={node.node_id}
                      center={[node.lat, node.lon]}
                      radius={3 + node.degree_centrality * 40}
                      pathOptions={{ color: tokens.coral, fillColor: tokens.coral, fillOpacity: 0.6 }}
                    >
                      <Popup>
                        Node: {node.node_id}<br />
                        Degree: {node.degree}<br />
                        Degree centrality: {node.degree_centrality}<br />
                        Betweenness: {node.betweenness_centrality}
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>
              </ChartPanel>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}
