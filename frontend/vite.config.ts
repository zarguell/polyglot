import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { resolve } from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/login": "http://localhost:8000",
      "/auth": "http://localhost:8000",
      "/logout": "http://localhost:8000",
      "/healthz": "http://localhost:8000",
      "/readyz": "http://localhost:8000",
    },
  },
  build: {
    outDir: resolve(__dirname, "..", "app", "static", "react"),
    emptyOutDir: true,
  },
});
