import type { NextConfig } from "next";

// Origin der Backend-API (ohne Pfad). Fallback = alte Railway-Adresse.
const apiOrigin = (() => {
  try {
    return new URL(
      process.env.NEXT_PUBLIC_API_URL ??
        "https://beattrack-production.up.railway.app",
    ).origin;
  } catch {
    return "";
  }
})();

const nextConfig: NextConfig = {
  // Eigenstaendiger Server-Build fuer den Docker-Container auf infra-01.
  output: "standalone",
  eslint: {
    // ESLint runs via `bun lint` — skip during build to avoid
    // Bun workspace hoisting issues with eslint-config-next plugins
    ignoreDuringBuilds: true,
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: https:",
              "font-src 'self'",
              // Die API-Adresse kommt aus der Umgebung, damit der Umzug
              // zwischen Hostern keine Codeaenderung braucht.
              `connect-src 'self' ${apiOrigin}`,
              "frame-src https://widget.deezer.com",
              "frame-ancestors 'none'",
            ].join("; "),
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
