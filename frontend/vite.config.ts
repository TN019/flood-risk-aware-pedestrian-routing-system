import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (uvicorn on port 8000); requests to /api are passed to it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  build: {
    // MapLibre is most of the bundle; keep it in its own chunk so app updates do not re-download it.
    chunkSizeWarningLimit: 1100,
    rollupOptions: { output: { manualChunks: { maplibre: ["maplibre-gl"] } } },
  },
  test: { environment: "node" },
} as never);
