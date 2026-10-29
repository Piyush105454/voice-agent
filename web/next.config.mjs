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
};
export default nextConfig;
