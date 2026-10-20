import {
  Box,
  Card,
  Chip,
  Grid,
  Link,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import { useCallback } from "react";

import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

const LIMITATIONS = [
  "OpenStreetMap is community-maintained: coverage and tag completeness vary by location.",
  "The presence of a road in OSM does not imply anything about its physical quality or condition.",
  "OSM alone cannot measure traffic congestion.",
  "OSM alone cannot measure actual travel demand.",
  "The accessibility score reflects road-network structural characteristics only -- it is not an official Indonesian government accessibility index.",
  "Regions identified as lower-accessibility are candidates for further assessment, not a claim that infrastructure investment is definitively required there.",
];

export default function AboutDataset() {
  const status = useFetch(useCallback(() => api.pipelineStatus(), []));
  const overview = useFetch(useCallback(() => api.overview(), []));

  const s = status.data || {};
  const o = overview.data || {};

  return (
    <Box>
      <PageHeader title="About This Dataset" subtitle="Source, processing status, and known limitations." />

      <Grid container spacing={2.5}>
        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Dataset
            </Typography>
            <List dense disablePadding>
              <ListItem disableGutters>
                <ListItemText primary="Name" secondary="OpenStreetMap Indonesia (road network extract)" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText primary="Raw file" secondary="backend/data/raw/indonesia-latest.osm.pbf" />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary="Source"
                  secondary={
                    <Link
                      href="https://download.geofabrik.de/asia/indonesia-latest.osm.pbf"
                      target="_blank"
                      rel="noreferrer"
                      sx={{ color: tokens.teal }}
                    >
                      Geofabrik Indonesia extract
                    </Link>
                  }
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary="What is OpenStreetMap?"
                  secondary="A free, editable map of the world built and maintained by a global community of volunteer contributors."
                />
              </ListItem>
            </List>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2.5, height: "100%" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Processing Status
            </Typography>
            {status.loading ? (
              <Typography variant="body2" sx={{ color: "text.secondary" }}>Loading...</Typography>
            ) : status.notProcessed || !s.processed ? (
              <DatasetNotProcessedAlert />
            ) : (
              <List dense disablePadding>
                <ListItem disableGutters>
                  <ListItemText
                    primary="Status"
                    secondary={
                      <Chip
                        size="small"
                        label={s.mode === "sample" ? "SAMPLE / DEV MODE" : "Processed (Full)"}
                        sx={{
                          bgcolor: s.mode === "sample" ? "rgba(226,87,76,0.15)" : "rgba(63,191,174,0.15)",
                          color: s.mode === "sample" ? tokens.coral : tokens.teal,
                          fontWeight: 700,
                          mt: 0.5,
                        }}
                      />
                    }
                  />
                </ListItem>
                <ListItem disableGutters>
                  <ListItemText primary="Processed at (UTC)" secondary={s.processed_at_utc || "--"} />
                </ListItem>
                <ListItem disableGutters>
                  <ListItemText primary="Processing time" secondary={s.elapsed_seconds ? `${s.elapsed_seconds}s` : "--"} />
                </ListItem>
                <ListItem disableGutters>
                  <ListItemText primary="Raw file size" secondary={s.raw_file_size_mb ? `${s.raw_file_size_mb} MB` : "--"} />
                </ListItem>
                <ListItem disableGutters>
                  <ListItemText
                    primary="Extracted road records"
                    secondary={(s.road_records_extracted ?? o.total_road_segments ?? 0).toLocaleString()}
                  />
                </ListItem>
                <ListItem disableGutters>
                  <ListItemText primary="Provinces detected" secondary={s.provinces_detected ?? o.number_of_provinces ?? "--"} />
                </ListItem>
                {s.note && (
                  <ListItem disableGutters>
                    <ListItemText
                      primary="Note"
                      secondary={<Typography variant="body2" sx={{ color: tokens.coral, fontWeight: 600 }}>{s.note}</Typography>}
                    />
                  </ListItem>
                )}
              </List>
            )}
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Second Dataset: Population (BPS)
            </Typography>
            <List dense disablePadding>
              <ListItem disableGutters>
                <ListItemText
                  primary="Source"
                  secondary={
                    <Link href="https://www.bps.go.id/" target="_blank" rel="noreferrer" sx={{ color: tokens.teal }}>
                      Badan Pusat Statistik (BPS) -- Statistics Indonesia
                    </Link>
                  }
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary="What it adds"
                  secondary="Province-level population figures, joined against the OSM road network to compute road length per 1,000 people -- reframing accessibility around population served, not just land area."
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary="Join limitation"
                  secondary="Province boundaries used for the OSM road network come from a community-maintained source that predates Indonesia's 2022 Papua province split (into 6 provinces). One province (formerly 'Irian Jaya Timur') has no safe modern equivalent and is shown with population unavailable rather than a guessed value."
                />
              </ListItem>
            </List>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card sx={{ p: 2.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1.5 }}>
              Data Limitations
            </Typography>
            <Stack spacing={1}>
              {LIMITATIONS.map((text) => (
                <Typography key={text} variant="body2" sx={{ color: "text.secondary" }}>
                  &bull; {text}
                </Typography>
              ))}
            </Stack>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
