/// <reference types="astro/client" />

// Global type declaration for .astro files
declare module '*.astro' {
  const component: any;
  export default component;
  export type Astro = typeof component;
}