import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Konfigurasi untuk deployment production ke Vercel
  // NEXT_PUBLIC_API_URL di-set via environment variable Vercel

  // Security headers untuk production
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "X-XSS-Protection",
            value: "1; mode=block",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
        ],
      },
    ];
  },

  // Standalone output untuk Vercel deployment
  output: "standalone",
};

export default nextConfig;
