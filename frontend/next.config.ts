import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: "export",
  turbopack: {
    root: __dirname
  }
};

export default nextConfig;
