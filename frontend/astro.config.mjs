// @ts-check
import { defineConfig } from "astro/config";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  output: "static",
  outDir: resolve(__dirname, "../server/static"),
  base: "/",
  build: {
    assets: "_astro",
    inlineStylesheets: "auto",
  },
  vite: {
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules/@preact/signals-core"))
              return "vendor-signals";
            if (id.includes("node_modules/astro")) return "vendor-astro";
            if (id.includes("node_modules")) return "vendor";
            if (id.includes("components/LogPanel")) return "logpanel";
            if (id.includes("components/PipelineGraph")) return "pipelinegraph";
            if (id.includes("components/OutputManagerCard")) return "outputs";
            if (id.includes("components/InputCard")) return "inputcard";
          },
        },
      },
      assetsInlineLimit: 4096,
    },
  },
  markdown: {
    shikiConfig: {
      theme: "github-dark",
    },
  },
});
