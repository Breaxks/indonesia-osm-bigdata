import { Box, Typography } from "@mui/material";

export default function NotFound() {
  return (
    <Box sx={{ textAlign: "center", py: 10 }}>
      <Typography variant="h3">404</Typography>
      <Typography variant="body1" sx={{ color: "text.secondary" }}>
        Page not found.
      </Typography>
    </Box>
  );
}
