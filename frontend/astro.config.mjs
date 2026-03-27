// @ts-check
import { defineConfig } from 'astro/config';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default defineConfig({
  output: 'static',
  build: {
    outDir: resolve(__dirname, '../server/static'),
  },
  base: '/',
  markdown: {
    shikiConfig: {
      theme: 'github-dark',
    },
  },
});
