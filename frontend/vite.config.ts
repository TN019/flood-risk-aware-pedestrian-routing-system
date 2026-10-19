import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs separately (uvicorn, port 8000 unless FLOODROUTE_API_URL says
// otherwise); requests to /api are passed to it.
declare const process: { env: Record<string, string | undefined> }; // Node, without @types/node
const API_URL = process.env.FLOODROUTE_API_URL ?? "http://127.0.0.1:8000";

// The API redirects /reference to /reference/ (where the page's index.html is); do the same in
// development, where Vite would otherwise fall back to the app.
const referenceSlash = {
  name: "reference-slash",
  configureServer(server: { middlewares: { use: (fn: (req: any, res: any, next: () => void) => void) => void } }) {
    server.middlewares.use((req, res, next) => {
      const [path, query] = (req.url ?? "").split("?");
      if (path !== "/reference") return next();
      res.statusCode = 307;
      res.setHeader("Location", `/reference/${query ? `?${query}` : ""}`);
      res.end();
    });
  },
};

export default defineConfig({
  plugins: [react(), referenceSlash],
  server: {
    port: 5174,
    proxy: { "/api": API_URL },
  },
  build: {
    // MapLibre is most of the bundle; keep it in its own chunk so app updates do not re-download it.
    chunkSizeWarningLimit: 1100,
    rollupOptions: {
      // Two pages: the app, and /reference (reached only by its address).
      input: { app: "index.html", reference: "reference/index.html" },
      output: { manualChunks: { maplibre: ["maplibre-gl"] } },
    },
  },
  test: { environment: "node" },
} as never);
