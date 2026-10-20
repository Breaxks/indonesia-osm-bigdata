import { Alert, AlertTitle, Box } from "@mui/material";

export default function ErrorAlert({ message }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
      <Alert severity="error" sx={{ maxWidth: 620 }}>
        <AlertTitle>Something went wrong</AlertTitle>
        {message || "Unable to load data from the API."}
      </Alert>
    </Box>
  );
}
