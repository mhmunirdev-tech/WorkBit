import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: process.cwd(),
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  async rewrites() {
    const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
    if (!configuredApiUrl) return [];

    const backendOrigin = configuredApiUrl
      .replace(/\/+$/, "")
      .replace(/\/api\/v1$/i, "");

    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendOrigin}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
