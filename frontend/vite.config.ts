import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The CloudGuard demo server (FastAPI) serves /api/* on port 8501. In dev, proxy /api to it so the
// browser makes same-origin calls and no CORS change is needed on the Python server.
// Start the backend first: `.\kit.cmd demo-bg` (or `python -m uvicorn demo.server:app --port 8501`).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.CLOUDGUARD_API ?? "http://127.0.0.1:8501",
        changeOrigin: true,
      },
    },
  },
  build: { outDir: "dist" },
});
