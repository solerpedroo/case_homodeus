/**
 * EN: Next.js config — standalone output for Docker, strict mode, optional
 *     rewrite proxy /api/* → FastAPI (when same-origin desired).
 * PT: Config Next.js — output standalone para Docker, strict mode, proxy
 *     opcional /api/* → FastAPI.
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  experimental: {
    serverActions: { bodySizeLimit: "2mb" },
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};

export default nextConfig;
