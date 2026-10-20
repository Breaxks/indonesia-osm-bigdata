import BarChartIcon from "@mui/icons-material/BarChart";
import CompareArrowsIcon from "@mui/icons-material/CompareArrows";
import HubIcon from "@mui/icons-material/Hub";
import InfoOutlineIcon from "@mui/icons-material/InfoOutlined";
import InsightsIcon from "@mui/icons-material/Insights";
import MapIcon from "@mui/icons-material/Map";
import MenuIcon from "@mui/icons-material/Menu";
import RouteIcon from "@mui/icons-material/Route";
import TableRowsIcon from "@mui/icons-material/TableRows";
import DashboardIcon from "@mui/icons-material/SpaceDashboard";
import {
  AppBar,
  Box,
  Chip,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Toolbar,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { tokens } from "../theme/theme.js";

const DRAWER_WIDTH = 248;

const NAV_ITEMS = [
  { label: "Overview", path: "/", icon: <DashboardIcon /> },
  { label: "Map Explorer", path: "/map-explorer", icon: <MapIcon /> },
  { label: "Road Infrastructure", path: "/road-infrastructure", icon: <RouteIcon /> },
  { label: "Regional Comparison", path: "/regional-comparison", icon: <CompareArrowsIcon /> },
  { label: "Machine Learning", path: "/machine-learning", icon: <InsightsIcon /> },
  { label: "Graph Analytics", path: "/graph-analytics", icon: <HubIcon /> },
  { label: "Data Explorer", path: "/data-explorer", icon: <TableRowsIcon /> },
  { label: "About Dataset", path: "/about-dataset", icon: <InfoOutlineIcon /> },
];

function SidebarContent() {
  const location = useLocation();
  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <Toolbar sx={{ px: 2.5 }}>
        <Stack direction="row" spacing={1.2} alignItems="center">
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: "6px",
              backgroundColor: tokens.amber,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <RouteIcon sx={{ color: tokens.ink, fontSize: 20 }} />
          </Box>
          <Box>
            <Typography variant="subtitle2" sx={{ lineHeight: 1.1, fontWeight: 700 }}>
              JalanAnalytics
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              Indonesia OSM
            </Typography>
          </Box>
        </Stack>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1.5, py: 1.5, flexGrow: 1 }}>
        {NAV_ITEMS.map((item) => {
          const active = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              component={NavLink}
              to={item.path}
              sx={{
                borderRadius: 1.5,
                mb: 0.5,
                position: "relative",
                color: active ? "text.primary" : "text.secondary",
                backgroundColor: active ? "rgba(242,169,59,0.10)" : "transparent",
                "&::before": active
                  ? {
                      content: '""',
                      position: "absolute",
                      left: -12,
                      top: 6,
                      bottom: 6,
                      width: 3,
                      borderRadius: 2,
                      backgroundColor: tokens.amber,
                    }
                  : {},
                "&:hover": { backgroundColor: "rgba(255,255,255,0.05)" },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: active ? tokens.amber : "inherit" }}>
                {item.icon}
              </ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{ fontSize: 14, fontWeight: active ? 600 : 500 }}
              />
            </ListItemButton>
          );
        })}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Typography variant="caption" sx={{ color: "text.secondary", display: "block" }}>
          Matthew Christian Hansel Budhiono
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          2702750924
        </Typography>
      </Box>
    </Box>
  );
}

export default function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const isSmall = useMediaQuery("(max-width:900px)");
  const location = useLocation();

  const currentLabel = NAV_ITEMS.find((n) => n.path === location.pathname)?.label || "Dashboard";

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        sx={{ zIndex: (t) => t.zIndex.drawer + 1, ml: { md: `${DRAWER_WIDTH}px` }, width: { md: `calc(100% - ${DRAWER_WIDTH}px)` } }}
      >
        <Toolbar sx={{ display: "flex", justifyContent: "space-between" }}>
          <Stack direction="row" alignItems="center" spacing={1.5}>
            {isSmall && (
              <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ color: "text.primary" }}>
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h6">{currentLabel}</Typography>
          </Stack>
          <Chip
            icon={<BarChartIcon sx={{ fontSize: 16 }} />}
            label="Big Data Analytics"
            size="small"
            sx={{ bgcolor: "rgba(63,191,174,0.12)", color: tokens.teal, fontWeight: 600 }}
          />
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: DRAWER_WIDTH } }}
        >
          <SidebarContent />
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{ display: { xs: "none", md: "block" }, "& .MuiDrawer-paper": { width: DRAWER_WIDTH, boxSizing: "border-box" } }}
          open
        >
          <SidebarContent />
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          bgcolor: "background.default",
          minHeight: "100vh",
        }}
      >
        <Toolbar />
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
