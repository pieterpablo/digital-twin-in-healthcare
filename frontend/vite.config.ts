import { defineConfig } from 'vite';

// De frontend gebruikt relatieve /api-URLs, ook bij pixi run frontend.
export default defineConfig({
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } }
});
