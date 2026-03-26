/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "/api",
  },
  async rewrites() {
    const base = (process.env.INTERNAL_API_BASE || "http://localhost:8000").replace(/\/$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${base}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
