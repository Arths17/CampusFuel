/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    optimizeCss: true,
  },
  async rewrites() {
    const rawBackendUrl = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const backendUrlWithProtocol = /^https?:\/\//i.test(rawBackendUrl)
      ? rawBackendUrl
      : `https://${rawBackendUrl}`;
    const backendUrl = backendUrlWithProtocol.replace(/\/+$/, '');
    return [
      {
        source: '/api/login',
        destination: `${backendUrl}/login`,
      },
      {
        source: '/api/signup',
        destination: `${backendUrl}/api/signup`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
