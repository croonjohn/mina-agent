import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://mina-verse8.duckdns.org/api/:path*",
      },
    ];
  },
};

export default nextConfig;
