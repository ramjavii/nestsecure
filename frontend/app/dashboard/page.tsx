'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { api } from '@/lib/api';
import { Server, Radar, AlertTriangle, Shield, Activity, Clock } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';
import { cn } from '@/lib/utils';

interface DashboardStats {
  assets: { total: number; active: number };
  services: { total: number; open: number };
  vulnerabilities: { critical: number; high: number; medium: number; low: number };
  risk: { average_score: number; assets_at_risk: number };
}

export default function DashboardPage() {
  const router = useRouter();
  const { accessToken, user, setUser, logout } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth and fetch data
  useEffect(() => {
    const init = async () => {
      if (!accessToken) {
        router.push('/login');
        return;
      }

      try {
        // Verificar autenticación si no hay user
        if (!user) {
          const userData = await api.getMe();
          setUser(userData);
        }

        // Cargar stats del dashboard
        try {
          const dashboardStats = await api.getDashboardStats();
          setStats(dashboardStats);
        } catch (e) {
          console.error('Error loading stats:', e);
        }

        setIsInitialized(true);
        setLoading(false);
      } catch {
        logout();
        router.push('/login');
      }
    };

    init();
  }, [accessToken, user, setUser, logout, router]);

  // Handle responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setSidebarCollapsed(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-muted-foreground">Cargando dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <div className="hidden lg:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Topbar */}
      <Topbar
        onMenuClick={() => {}}
        sidebarCollapsed={sidebarCollapsed}
      />

      {/* Main content */}
      <main
        className={cn(
          'pt-16 min-h-screen transition-all duration-300',
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
        )}
      >
        <div className="p-4 lg:p-6 space-y-6">
          {/* Header */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Bienvenido, {user?.full_name || 'Usuario'}. Resumen de seguridad de tu infraestructura.
            </p>
          </div>

          {/* Stats Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Assets</CardTitle>
                <Server className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.assets?.total || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {stats?.assets?.active || 0} activos
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Servicios</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats?.services?.total || 0}</div>
                <p className="text-xs text-muted-foreground">
                  {stats?.services?.open || 0} abiertos
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Vulnerabilidades</CardTitle>
                <AlertTriangle className="h-4 w-4 text-destructive" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-destructive">
                  {(stats?.vulnerabilities?.critical || 0) + (stats?.vulnerabilities?.high || 0)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats?.vulnerabilities?.critical || 0} críticas, {stats?.vulnerabilities?.high || 0} altas
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Riesgo Promedio</CardTitle>
                <Shield className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {(stats?.risk?.average_score || 0).toFixed(1)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats?.risk?.assets_at_risk || 0} assets en riesgo
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Acciones Rápidas</CardTitle>
              <CardDescription>Tareas frecuentes de seguridad</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <button 
                onClick={() => router.push('/scans')}
                className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-accent transition-colors"
              >
                <Radar className="h-5 w-5 text-primary" />
                <div className="text-left">
                  <p className="font-medium">Nuevo Escaneo</p>
                  <p className="text-sm text-muted-foreground">Iniciar scan de vulnerabilidades</p>
                </div>
              </button>
              
              <button 
                onClick={() => router.push('/assets')}
                className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-accent transition-colors"
              >
                <Server className="h-5 w-5 text-primary" />
                <div className="text-left">
                  <p className="font-medium">Agregar Asset</p>
                  <p className="text-sm text-muted-foreground">Registrar nuevo activo</p>
                </div>
              </button>
              
              <button 
                onClick={() => router.push('/vulnerabilities')}
                className="flex items-center gap-3 p-4 rounded-lg border border-border hover:bg-accent transition-colors"
              >
                <AlertTriangle className="h-5 w-5 text-primary" />
                <div className="text-left">
                  <p className="font-medium">Ver Vulnerabilidades</p>
                  <p className="text-sm text-muted-foreground">Revisar hallazgos pendientes</p>
                </div>
              </button>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Actividad Reciente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground text-center py-8">
                No hay actividad reciente para mostrar.
              </p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
