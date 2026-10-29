import type { NextConfig } from "next";

/**
 * The browser only ever calls the Next.js origin (relative `/api` URLs). These
 * rewrites proxy to the FastAPI process server-side, which keeps the app working
 * behind preview proxies and avoids CORS in the browser.
 */
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  allowedDevOrigins: ["localhost", "127.0.0.1", "*.e2b.app"],
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*` },
      { source: "/health", destination: `${apiProxyTarget}/health` },
      // Swagger UI + its schema, so "API reference" stays same-origin in the browser.
      { source: "/docs", destination: `${apiProxyTarget}/docs` },
      { source: "/openapi.json", destination: `${apiProxyTarget}/openapi.json` },
    ];
  },
};

export default nextConfig;
