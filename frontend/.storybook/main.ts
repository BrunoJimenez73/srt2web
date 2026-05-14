/** @type { import('@storybook/web-components-vite').StorybookConfig } */
const config = {
  stories: ["../src/components/**/*.stories.@(js|ts)"],
  addons: ["@storybook/addon-essentials"],
  framework: {
    name: "@storybook/web-components-vite",
    options: {},
  },
  core: {
    builder: "@storybook/builder-vite",
  },
};
export default config;
