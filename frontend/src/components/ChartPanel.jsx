import { Card, Skeleton, Stack, Typography } from "@mui/material";

import { tokens } from "../theme/theme.js";

const ACCENTS = { amber: tokens.amber, teal: tokens.teal, coral: tokens.coral };

export default function ChartPanel({ title, subtitle, accent = "amber", loading, height = 320, children }) {
  const accentColor = ACCENTS[accent] || tokens.amber;
  return (
    <Card
      sx={{
        p: 2.5,
        height: "100%",
        position: "relative",
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 3,
          backgroundColor: accentColor,
        },
      }}
    >
      <Stack spacing={0.25} sx={{ mb: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        {subtitle && (
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {subtitle}
          </Typography>
        )}
      </Stack>
      {loading ? (
        <Skeleton variant="rounded" height={height} sx={{ bgcolor: "rgba(255,255,255,0.06)" }} />
      ) : (
        children
      )}
    </Card>
  );
}
