import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  eslint: {
    // ESLint runs via `bun lint` — skip during build to avoid
    // Bun workspace hoisting issues with eslint-config-next plugins
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
