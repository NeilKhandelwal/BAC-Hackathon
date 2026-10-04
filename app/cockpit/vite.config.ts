import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the built files open from any static host or folder.
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
