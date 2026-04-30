import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Server Components by default per app/ router; no special opt-in needed.
  experimental: {
    typedRoutes: true,
  },
};

export default nextConfig;
