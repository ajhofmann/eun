/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_PAGES_MODE?: string;
  readonly VITE_DEMO_BASE?: string;
  readonly VITE_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
