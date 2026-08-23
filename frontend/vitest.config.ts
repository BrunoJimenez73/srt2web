import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  root: path.resolve(__dirname),
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.ts"],
    exclude: ["e2e/**", "node_modules/**"],
    cache: {
      dir: path.resolve(__dirname, "node_modules/.vitest"),
    },
    coverage: {
      provider: "v8",
      reportsDirectory: "./coverage",
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 70,
      },
    },
  },
  deps: {
    cacheDir: path.resolve(__dirname, "node_modules/.vite"),
  },
});
