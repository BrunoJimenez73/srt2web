/// <reference types="astro/client" />

// Global type declaration for .astro files
declare module "*.astro" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const component: any;
  export default component;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export type Astro = any;
}
