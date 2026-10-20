import { Box, Card, Skeleton, Stack, Typography } from "@mui/material";

import { tokens } from "../theme/theme.js";

const ACCENTS = {
  amber: tokens.amber,
  teal: tokens.teal,
  coral: tokens.coral,
};

export default function KpiCard({ label, value, suffix, icon, accent = "amber", loading, hint, valueSx }) {
  const accentColor = ACCENTS[accent] || tokens.amber;

  return (
    <Card
      sx={{
        p: 2.5,
        height: "100%",
        position: "relative",
        overflow: "hidden",
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
      <Stack spacing={1}>
        <Stack direction="row" alignItems="center" justifyContent="space-between">
          <Typography variant="overline" sx={{ color: "text.secondary", letterSpacing: 0.4 }}>
            {label}
          </Typography>
          {icon && (
            <Box sx={{ color: accentColor, display: "flex", opacity: 0.85 }}>{icon}</Box>
          )}
        </Stack>
        {loading ? (
          <Skeleton variant="text" width="70%" height={44} sx={{ bgcolor: "rgba(255,255,255,0.08)" }} />
        ) : (
          <Typography variant="h4" sx={{ fontVariantNumeric: "tabular-nums", ...valueSx }}>
            {value}
            {suffix && (
              <Typography component="span" variant="body2" sx={{ color: "text.secondary", ml: 0.5 }}>
                {suffix}
              </Typography>
            )}
          </Typography>
        )}
        {hint && (
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {hint}
          </Typography>
        )}
      </Stack>
    </Card>
  );
}
