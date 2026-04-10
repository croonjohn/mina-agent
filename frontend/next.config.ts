import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "https://pam-venice-recommend-transportation.trycloudflare.com/api/:path*",
      },
    ];
  },
};

export default nextConfig;
