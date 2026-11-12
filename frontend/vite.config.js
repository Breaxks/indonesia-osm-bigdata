import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  // On GitHub Pages the site lives at /<repo-name>/ ; the deploy workflow sets
  // VITE_BASE for you. Locally it stays "/".
  base: process.env.VITE_BASE || "/",
  plugins: [react()],
  server: {
    port: 5173,
  },
});
