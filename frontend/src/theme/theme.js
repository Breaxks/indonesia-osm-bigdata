import { createTheme } from "@mui/material/styles";

/*
  Design tokens
  -------------
  Subject: a road-network / infrastructure analytics control room.
  Palette:
    ink        #0B1220  page background
    surface    #121B2E  panels
    surfaceAlt #182444  raised panels / sidebar
    border     #223054  hairline dividers
    amber      #F2A93B  primary accent (route markers / signal amber)
    teal       #3FBFAE  secondary accent (connectivity / graph)
    coral      #E2574C  alert / "Low" accessibility
    text       #EDF1F7  primary text
    textMuted  #8592AC  secondary text
  Type: Space Grotesk for headings (geometric, technical), Inter for body
  and data. Panels are flat with 1px hairline borders and a thin top
  accent rule rather than drop shadows + uniform radius.
*/

export const tokens = {
  ink: "#0B1220",
  surface: "#121B2E",
  surfaceAlt: "#182444",
  border: "#223054",
  amber: "#F2A93B",
  teal: "#3FBFAE",
  coral: "#E2574C",
  text: "#EDF1F7",
  textMuted: "#8592AC",
};

const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: tokens.ink,
      paper: tokens.surface,
    },
    primary: { main: tokens.amber, contrastText: "#0B1220" },
    secondary: { main: tokens.teal, contrastText: "#0B1220" },
    error: { main: tokens.coral },
    warning: { main: tokens.amber },
    success: { main: tokens.teal },
    text: {
      primary: tokens.text,
      secondary: tokens.textMuted,
    },
    divider: tokens.border,
  },
  shape: { borderRadius: 6 },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, sans-serif',
    h1: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h2: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h3: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h4: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h5: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600 },
    h6: { fontFamily: '"Space Grotesk", sans-serif', fontWeight: 600, letterSpacing: 0.2 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          border: `1px solid ${tokens.border}`,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.surface,
          borderBottom: `1px solid ${tokens.border}`,
          boxShadow: "none",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: tokens.surfaceAlt,
          borderRight: `1px solid ${tokens.border}`,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: tokens.surface,
          border: `1px solid ${tokens.border}`,
          borderRadius: 8,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 6 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 4, fontWeight: 600 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: tokens.border },
      },
    },
  },
});

export default theme;
