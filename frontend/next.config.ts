import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "i.etsystatic.com",
      },
      {
        protocol: "https",
        hostname: "i.etsy-cdn.com",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/static/:path*",
        destination: "http://127.0.0.1:8000/static/:path*",
      },
      {
        source: "/assets/:path*",
        destination: "http://127.0.0.1:8000/assets/:path*",
      },
    ];
  },
};

export default nextConfig;
