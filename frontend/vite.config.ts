import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (uvicorn, port 8000 unless FLOODROUTE_API_URL says
// otherwise); requests to /api are passed to it.
declare const process: { env: Record<string, string | undefined> }; // Node, without @types/node
const API_URL = process.env.FLOODROUTE_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { "/api": API_URL },
  },
  build: {
    // MapLibre is most of the bundle; keep it in its own chunk so app updates do not re-download it.
    chunkSizeWarningLimit: 1100,
    rollupOptions: { output: { manualChunks: { maplibre: ["maplibre-gl"] } } },
  },
  test: { environment: "node" },
} as never);
