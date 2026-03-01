/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizeCss: true,
  },
  allowedDevOrigins: ["10.125.175.84", "localhost"],
  turbopack: {
    root: ".",
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL;

    if (backendUrl) {
      // On Vercel: route through the server-side proxy which injects ngrok header
      // Exclude /api/proxy/* itself to avoid infinite loop
      return [
        {
          source: "/api/:path((?!proxy).*)",
          destination: "/api/proxy/:path*",
        },
      ];
    }

    // Local dev: proxy directly to localhost:8000
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;

