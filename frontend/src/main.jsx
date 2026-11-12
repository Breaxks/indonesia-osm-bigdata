import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";
import React from "react";
import ReactDOM from "react-dom/client";
import { HashRouter } from "react-router-dom";

import App from "./App.jsx";
import "leaflet/dist/leaflet.css";
import "./theme/leaflet-dark.css";
import theme from "./theme/theme.js";

// HashRouter (URLs like /#/map-explorer) is what makes page refreshes and
// shared links work on GitHub Pages, which has no server-side routing.
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <HashRouter>
        <App />
      </HashRouter>
    </ThemeProvider>
  </React.StrictMode>
);
