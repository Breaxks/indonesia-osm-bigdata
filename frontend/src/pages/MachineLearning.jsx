import {
  Box,
  Card,
  Chip,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useCallback } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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

const CLASS_COLORS = { Low: tokens.coral, Medium: tokens.amber, High: tokens.teal };

function formatAlgorithmName(value) {
  if (!value) return "--";
  return value.replace(/([a-z0-9])([A-Z])/g, "$1 $2");
}

function ClassChip({ value }) {
  const color = CLASS_COLORS[value] || tokens.textMuted;
  return (
    <Chip
      size="small"
      label={value}
      sx={{ bgcolor: `${color}22`, color, fontWeight: 700 }}
    />
  );
}

export default function MachineLearning() {
  const metrics = useFetch(useCallback(() => api.mlMetrics(), []));
  const importance = useFetch(useCallback(() => api.mlFeatureImportance(), []));
  const predictions = useFetch(useCallback(() => api.mlPredictions(), []));

  const notProcessed = metrics.notProcessed || importance.notProcessed || predictions.notProcessed;
  const anyError = metrics.error || importance.error || predictions.error;
  if (notProcessed) return <DatasetNotProcessedAlert />;
  if (anyError) return <ErrorAlert message={anyError} />;

  const m = metrics.data || {};
  const labels = m.class_labels || [];
  const cm = m.confusion_matrix || [];

  const importanceData = (importance.data || []).map((d) => ({
    feature: d.feature,
    importance: d.importance,
  }));

  const predictionRows = predictions.data || [];

  return (
    <Box>
      <PageHeader
        title="Machine Learning: Accessibility Classification"
        subtitle="Supervised classifier trained to reproduce Low/Medium/High classes derived from the composite accessibility index."
      />

      {/* <Card sx={{ p: 2.5, mb: 2.5, borderLeft: `3px solid ${tokens.amber}` }}>
        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
          Methodology
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {m.methodology ||
            "This classification is derived from a transparent composite accessibility index built " +
              "from normalized road-network metrics (road density, intersection density, major-road ratio, " +
              "network density, average node degree). It is NOT an official government accessibility label -- " +
              "OpenStreetMap provides no such ground truth."}
        </Typography>
        {m.n_provinces_total !== undefined && (
          <Typography variant="caption" sx={{ color: "text.secondary", display: "block", mt: 1 }}>
            Trained on {m.n_provinces_total} province records ({m.n_train} train / {m.n_test} test).
            With a small number of provinces, treat these metrics as diagnostic of the index's internal
            consistency rather than large-sample statistical power.
          </Typography>
        )}
      </Card> */}

      <Grid container spacing={2.5} sx={{ mb: 1 }}>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard
            label="Algorithm"
            value={formatAlgorithmName(m.algorithm)}
            accent="amber"
            loading={metrics.loading}
            valueSx={{ fontSize: "1.35rem", lineHeight: 1.2, overflowWrap: "anywhere" }}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Accuracy" value={m.accuracy !== undefined ? (m.accuracy * 100).toFixed(1) : "--"} suffix="%" accent="teal" loading={metrics.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="F1 (macro)" value={m.f1_macro ?? "--"} accent="coral" loading={metrics.loading} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <KpiCard label="Precision / Recall (macro)" value={`${m.precision_macro ?? "--"} / ${m.recall_macro ?? "--"}`} accent="amber" loading={metrics.loading} />
        </Grid>
      </Grid>

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={6}>
          <ChartPanel title="Confusion Matrix" subtitle="Rows: actual index class, columns: predicted class" accent="teal" loading={metrics.loading} height={260}>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell />
                    {labels.map((l) => (
                      <TableCell key={l} align="center">{l}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cm.map((row, i) => (
                    <TableRow key={labels[i]}>
                      <TableCell sx={{ fontWeight: 700 }}>{labels[i]}</TableCell>
                      {row.map((val, j) => (
                        <TableCell
                          key={j}
                          align="center"
                          sx={{
                            bgcolor: i === j ? "rgba(63,191,174,0.15)" : "transparent",
                            fontWeight: i === j ? 700 : 400,
                          }}
                        >
                          {val}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12} md={6}>
          <ChartPanel title="Feature Importance" subtitle="Which network characteristics explain the classification" accent="amber" loading={importance.loading} height={300}>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={importanceData} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.border} horizontal={false} />
                <XAxis type="number" stroke={tokens.textMuted} fontSize={11} />
                <YAxis type="category" dataKey="feature" stroke={tokens.textMuted} fontSize={10} width={170} />
                <Tooltip contentStyle={{ background: tokens.surfaceAlt, border: `1px solid ${tokens.border}` }} />
                <Bar dataKey="importance" fill={tokens.amber} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </Grid>

        <Grid item xs={12}>
          <ChartPanel title="Province Accessibility Ranking & Predictions" accent="teal" loading={predictions.loading} height={100}>
            <TableContainer sx={{ maxHeight: 480 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell>Province</TableCell>
                    <TableCell align="right">Accessibility Score</TableCell>
                    <TableCell align="center">Index Class</TableCell>
                    <TableCell align="center">Model Predicted Class</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {predictionRows.map((row) => (
                    <TableRow key={row.province} hover>
                      <TableCell>{row.province}</TableCell>
                      <TableCell align="right">{row.accessibility_score?.toFixed(2)}</TableCell>
                      <TableCell align="center"><ClassChip value={row.accessibility_class} /></TableCell>
                      <TableCell align="center"><ClassChip value={row.predicted_class} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </ChartPanel>
        </Grid>
      </Grid>
    </Box>
  );
}
