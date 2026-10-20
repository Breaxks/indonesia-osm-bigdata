import { Autocomplete, Box, Card, Chip, Grid, TextField } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useCallback, useEffect, useState } from "react";

import DatasetNotProcessedAlert from "../components/DatasetNotProcessedAlert.jsx";
import ErrorAlert from "../components/ErrorAlert.jsx";
import PageHeader from "../components/PageHeader.jsx";
import useFetch from "../hooks/useFetch.js";
import api from "../services/api.js";
import { tokens } from "../theme/theme.js";

const COLUMNS = [
  { field: "osm_id", headerName: "OSM ID", width: 130 },
  { field: "name", headerName: "Road Name", flex: 1, minWidth: 160 },
  { field: "highway", headerName: "Highway Type", width: 140 },
  {
    field: "length_m",
    headerName: "Length (m)",
    width: 120,
    type: "number",
    valueFormatter: (params) => (params.value != null ? Math.round(params.value).toLocaleString() : "-"),
  },
  { field: "province", headerName: "Province", width: 160 },
  {
    field: "oneway",
    headerName: "One-Way",
    width: 100,
    renderCell: (params) => (
      <Chip
        size="small"
        label={params.value ? "Yes" : "No"}
        sx={{
          bgcolor: params.value ? "rgba(242,169,59,0.15)" : "rgba(133,146,172,0.15)",
          color: params.value ? tokens.amber : tokens.textMuted,
        }}
      />
    ),
  },
  { field: "lanes", headerName: "Lanes", width: 90, type: "number" },
  { field: "surface", headerName: "Surface", width: 120 },
  { field: "maxspeed", headerName: "Max Speed", width: 110, type: "number" },
];

export default function DataExplorer() {
  const provincesRes = useFetch(useCallback(() => api.provinces(), []));
  const roadTypesRes = useFetch(useCallback(() => api.roadTypes(), []));

  const [province, setProvince] = useState(null);
  const [roadType, setRoadType] = useState(null);
  const [search, setSearch] = useState("");
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });
  const [rows, setRows] = useState([]);
  const [rowCount, setRowCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [notProcessed, setNotProcessed] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .roads({
        page: paginationModel.page + 1,
        page_size: paginationModel.pageSize,
        province: province || undefined,
        road_type: roadType || undefined,
        search: search || undefined,
      })
      .then((res) => {
        setRows(res.items.map((r) => ({ id: r.osm_id, ...r })));
        setRowCount(res.total_items);
      })
      .catch((err) => {
        if (err.notProcessed) setNotProcessed(true);
        else setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [paginationModel, province, roadType, search]);

  if (notProcessed || provincesRes.notProcessed) return <DatasetNotProcessedAlert />;
  if (provincesRes.error) return <ErrorAlert message={provincesRes.error} />;

  return (
    <Box>
      <PageHeader
        title="Data Explorer"
        subtitle="Browse processed road records with server-side pagination, sorting, and filtering."
      />

      <Card sx={{ p: 2, mb: 2.5 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={4}>
            <Autocomplete
              size="small"
              options={provincesRes.data || []}
              value={province}
              onChange={(_, v) => {
                setProvince(v);
                setPaginationModel((p) => ({ ...p, page: 0 }));
              }}
              renderInput={(params) => <TextField {...params} label="Province" />}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <Autocomplete
              size="small"
              options={roadTypesRes.data || []}
              value={roadType}
              onChange={(_, v) => {
                setRoadType(v);
                setPaginationModel((p) => ({ ...p, page: 0 }));
              }}
              renderInput={(params) => <TextField {...params} label="Road Type" />}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              size="small"
              fullWidth
              label="Search road name"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPaginationModel((p) => ({ ...p, page: 0 }));
              }}
            />
          </Grid>
        </Grid>
      </Card>

      {error && <ErrorAlert message={error} />}

      <Card sx={{ p: 0 }}>
        <DataGrid
          autoHeight
          rows={rows}
          columns={COLUMNS}
          rowCount={rowCount}
          loading={loading}
          paginationMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[25, 50, 100]}
          disableRowSelectionOnClick
          sx={{
            border: "none",
            "& .MuiDataGrid-columnHeaders": { bgcolor: tokens.surfaceAlt, borderColor: tokens.border },
            "& .MuiDataGrid-cell": { borderColor: tokens.border },
            "& .MuiDataGrid-footerContainer": { borderColor: tokens.border },
          }}
        />
      </Card>
    </Box>
  );
}
