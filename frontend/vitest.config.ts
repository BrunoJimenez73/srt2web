import { defineConfig } from "vitest/config";
import path from "path";

export default defineConfig({
  root: path.resolve(__dirname),
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.ts"],
    cache: {
      dir: path.resolve(__dirname, "node_modules/.vitest"),
    },
  },
  deps: {
    cacheDir: path.resolve(__dirname, "node_modules/.vite"),
  },
});
