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
  },
  markdown: {
    shikiConfig: {
      theme: "github-dark",
    },
  },
});
