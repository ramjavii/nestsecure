/** @type {import('next').NextConfig} */
const nextConfig = {
  // Habilitar output standalone para Docker
  output: 'standalone',
  
  // TypeScript - ignorar errores de build en desarrollo
  typescript: {
    ignoreBuildErrors: true,
  },
  
  // Imágenes - desoptimizadas para simplicidad
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: 'backend',
      },
    ],
  },
  
  // Turbopack config (Next.js 16+ usa Turbopack por defecto)
  turbopack: {},
  
  // Headers de seguridad y CORS
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, Authorization' },
        ],
      },
    ];
  },
  
  // Rewrites para proxy al backend (solo en desarrollo)
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    // Extraer el host base sin el path
    const backendHost = backendUrl.replace('/api/v1', '');
    
    return [
      // Health check endpoint
      {
        source: '/api/health',
        destination: `${backendHost}/health`,
      },
    ];
  },
};

export default nextConfig;
