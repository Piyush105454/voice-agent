import path from "node:path";
import nextEnv from "@next/env";

// One .env for the whole repo: load ../.env (API keys never reach the browser; only NEXT_PUBLIC_* do).
// forceReload: Next has already loaded (and cached) the empty web/ env by the time this runs.
const dev = process.env.NODE_ENV !== "production";
nextEnv.loadEnvConfig(path.resolve(process.cwd(), ".."), dev, { info() {}, error: console.error }, true);

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  poweredByHeader: false,
  // One public URL serves the dashboard AND the API's public endpoints (all-in-one deployment).
  async rewrites() {
    const api = process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
    return [
      { source: "/bolna/:path*", destination: `${api}/bolna/:path*` },
      { source: "/missed_call", destination: `${api}/missed_call` },
      { source: "/call", destination: `${api}/call` },
      { source: "/web-call/:path*", destination: `${api}/web-call/:path*` },
      { source: "/health", destination: `${api}/health` },
    ];
  },
};
export default nextConfig;
