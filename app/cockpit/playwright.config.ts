import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: { baseURL: "http://localhost:5174/" },
  webServer: {
    command: "npm run build && npx vite preview --port 5174 --strictPort",
    url: "http://localhost:5174/",
    reuseExistingServer: false,
    timeout: 120_000,
  },
  projects: [
    { name: "1920", use: { viewport: { width: 1920, height: 1080 } } },
    { name: "1280", use: { viewport: { width: 1280, height: 720 } } },
  ],
});
