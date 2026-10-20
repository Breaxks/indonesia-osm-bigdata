import TerrainIcon from "@mui/icons-material/Terrain";
import { Alert, AlertTitle, Box, Typography } from "@mui/material";

export default function DatasetNotProcessedAlert() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
      <Alert
        severity="warning"
        icon={<TerrainIcon />}
        sx={{ maxWidth: 620, border: "1px solid", borderColor: "warning.main" }}
      >
        <AlertTitle>Dataset has not been processed yet</AlertTitle>
        <Typography variant="body2" sx={{ mb: 1 }}>
          Run the processing pipeline first, then restart the API.
        </Typography>
        <Box
          component="pre"
          sx={{
            bgcolor: "background.default",
            p: 1.5,
            borderRadius: 1,
            fontSize: 13,
            overflowX: "auto",
          }}
        >
          {`cd backend
python processing/run_pipeline.py --sample   # fast dev mode
# or
python processing/run_pipeline.py --full     # full national dataset`}
        </Box>
      </Alert>
    </Box>
  );
}
