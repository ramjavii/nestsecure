import { NextResponse } from 'next/server';

/**
 * Health Check Endpoint para el frontend
 * Usado por Docker health checks y load balancers
 */
export async function GET() {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const backendHost = backendUrl.replace('/api/v1', '');
  
  let backendStatus = 'unknown';
  let backendHealthy = false;
  
  try {
    // Verificar conexión al backend
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(`${backendHost}/health`, {
      method: 'GET',
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      backendStatus = 'healthy';
      backendHealthy = true;
    } else {
      backendStatus = 'unhealthy';
    }
  } catch (error) {
    backendStatus = 'unreachable';
  }
  
  const healthData = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '0.1.0',
    environment: process.env.NODE_ENV || 'development',
    services: {
      frontend: {
        status: 'healthy',
      },
      backend: {
        status: backendStatus,
        url: backendHost,
      },
    },
    uptime: process.uptime(),
  };
  
  // Si el backend no está disponible, reportar degraded pero no fail
  const overallStatus = backendHealthy ? 200 : 200; // Frontend sigue funcionando
  
  return NextResponse.json(healthData, { status: overallStatus });
}

// Soporte para HEAD requests (algunos health checkers lo usan)
export async function HEAD() {
  return new NextResponse(null, { status: 200 });
}
