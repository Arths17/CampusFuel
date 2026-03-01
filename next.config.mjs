/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizeCss: true,
  },
  async rewrites() {
    return [
      // Route all /api/* calls through the internal Next.js proxy
      // (app/api/proxy/[...path]/route.js) which adds ngrok headers
      // and reads BACKEND_URL at runtime, not build time.
      {
        source: '/api/:path*',
        destination: '/api/proxy/:path*',
      },
    ];
  },
};

export default nextConfig;

