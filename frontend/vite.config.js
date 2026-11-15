import { defineConfig, loadEnv } from 'vite';
import { parseApiOrigin } from './src/config.js';

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd(), '');
  const host = process.env.FRONTEND_HOST || environment.FRONTEND_HOST || '127.0.0.1';
  parseApiOrigin(`http://${host.includes(':') ? `[${host}]` : host}:1080`);
  return {
    server: { host, port: 1080, strictPort: true, open: false },
    preview: { host, port: 1080, strictPort: true },
  };
});
