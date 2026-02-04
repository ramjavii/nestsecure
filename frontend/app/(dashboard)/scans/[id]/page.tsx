'use client';

import { useState, useEffect, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow, format } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  ArrowLeft,
  Server,
  Network,
  AlertTriangle,
  Clock,
  Target,
  Download,
  StopCircle,
  RefreshCw,
  Terminal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { PageHeader } from '@/components/shared/page-header';
import { StatCard } from '@/components/shared/stat-card';
import { StatusBadge } from '@/components/shared/status-badge';
import { SeverityBadge } from '@/components/shared/severity-badge';
import { ProgressBar } from '@/components/shared/progress-bar';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import { useScan, useStopScan } from '@/hooks/use-scans';
import { useToast } from '@/hooks/use-toast';
import type { Scan, Vulnerability, Asset } from '@/types';

interface ScanDetailPageProps {
  params: Promise<{ id: string }>;
}

// Empty defaults for production mode
const emptyScan: Scan = {
  id: '',
  name: 'Cargando...',
  description: null,
  scan_type: 'quick',
  status: 'queued',
  progress: 0,
  targets: [],
  port_range: null,
  total_hosts_scanned: 0,
  total_hosts_up: 0,
  total_services_found: 0,
  total_vulnerabilities: 0,
  vuln_critical: 0,
  vuln_high: 0,
  vuln_medium: 0,
  vuln_low: 0,
  started_at: null,
  completed_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export default function ScanDetailPage({ params }: ScanDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { data: scan, isLoading } = useScan(id);
  const stopScan = useStopScan();
  const { toast } = useToast();
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [pollingProgress, setPollingProgress] = useState(0);

  // Use API data with empty defaults
  const displayScan = scan || emptyScan;

  // Simulate polling for running scans
  useEffect(() => {
    if (displayScan.status === 'running') {
      const interval = setInterval(() => {
        setPollingProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            return 100;
          }
          return prev + Math.random() * 2;
        });
      }, 2000);

      return () => clearInterval(interval);
    }
  }, [displayScan.status]);

  const handleStopScan = async () => {
    try {
      await stopScan.mutateAsync(id);
      toast({
        title: 'Escaneo detenido',
        description: 'El escaneo ha sido detenido correctamente.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo detener el escaneo.',
        variant: 'destructive',
      });
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 bg-muted animate-pulse rounded" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const currentProgress = displayScan.status === 'running' ? pollingProgress : displayScan.progress;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver
        </Button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{displayScan.name}</h1>
              <StatusBadge status={displayScan.status} size="lg" />
            </div>
            {displayScan.description && (
              <p className="text-muted-foreground">{displayScan.description}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {displayScan.status === 'running' && (
              <Button
                variant="destructive"
                onClick={() => setShowStopDialog(true)}
              >
                <StopCircle className="mr-2 h-4 w-4" />
                Detener
              </Button>
            )}
            {displayScan.status === 'completed' && (
              <>
                <Button variant="outline">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Re-escanear
                </Button>
                <Button>
                  <Download className="mr-2 h-4 w-4" />
                  Descargar Reporte
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Progress bar for running scans */}
        {(displayScan.status === 'running' || displayScan.status === 'queued') && (
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Progreso del escaneo</span>
                  <span className="font-medium">{Math.round(currentProgress)}%</span>
                </div>
                <ProgressBar
                  value={currentProgress}
                  size="lg"
                  showLabel={false}
                  animated={displayScan.status === 'running'}
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title="Targets"
          value={displayScan.targets.length}
          icon={Target}
          variant="default"
        />
        <StatCard
          title="Hosts Activos"
          value={displayScan.total_hosts_up}
          description={`de ${displayScan.total_hosts_scanned} escaneados`}
          icon={Server}
          variant="info"
        />
        <StatCard
          title="Servicios"
          value={displayScan.total_services_found}
          icon={Network}
          variant="info"
        />
        <StatCard
          title="Vulnerabilidades"
          value={displayScan.total_vulnerabilities}
          description={`${displayScan.vuln_critical} críticas`}
          icon={AlertTriangle}
          variant={displayScan.vuln_critical > 0 ? 'danger' : 'warning'}
        />
        <StatCard
          title="Duración"
          value={
            displayScan.started_at
              ? formatDistanceToNow(new Date(displayScan.started_at), { locale: es })
              : '-'
          }
          icon={Clock}
          variant="default"
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="summary" className="space-y-4">
        <TabsList>
          <TabsTrigger value="summary">Resumen</TabsTrigger>
          <TabsTrigger value="hosts">Hosts</TabsTrigger>
          <TabsTrigger value="vulnerabilities">Vulnerabilidades</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
        </TabsList>

        {/* Summary Tab */}
        <TabsContent value="summary" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Información del Escaneo</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Tipo de escaneo</p>
                    <p className="font-medium capitalize">{displayScan.scan_type.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Rango de puertos</p>
                    <p className="font-medium">{displayScan.port_range || 'Por defecto'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Creado</p>
                    <p className="font-medium">
                      {format(new Date(displayScan.created_at), 'dd/MM/yyyy HH:mm', { locale: es })}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Iniciado</p>
                    <p className="font-medium">
                      {displayScan.started_at
                        ? format(new Date(displayScan.started_at), 'dd/MM/yyyy HH:mm', { locale: es })
                        : '-'}
                    </p>
                  </div>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Targets</p>
                  <div className="flex flex-wrap gap-2">
                    {displayScan.targets.map((target) => (
                      <code
                        key={target}
                        className="px-2 py-1 bg-muted rounded text-sm font-mono"
                      >
                        {target}
                      </code>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Vulnerabilidades por Severidad</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {[
                    { label: 'Críticas', value: displayScan.vuln_critical, color: 'bg-severity-critical' },
                    { label: 'Altas', value: displayScan.vuln_high, color: 'bg-severity-high' },
                    { label: 'Medias', value: displayScan.vuln_medium, color: 'bg-severity-medium' },
                    { label: 'Bajas', value: displayScan.vuln_low, color: 'bg-severity-low' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={`h-3 w-3 rounded-full ${item.color}`} />
                        <span className="text-sm">{item.label}</span>
                      </div>
                      <span className="font-medium">{item.value}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Hosts Tab */}
        <TabsContent value="hosts">
          <Card>
            <CardHeader>
              <CardTitle>Hosts Descubiertos</CardTitle>
              <CardDescription>
                {displayScan.total_hosts_up} hosts activos encontrados
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={Server}
                title="Hosts en desarrollo"
                description="La visualización detallada de hosts estará disponible próximamente. Los hosts descubiertos se muestran en las estadísticas generales."
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vulnerabilities Tab */}
        <TabsContent value="vulnerabilities">
          <Card>
            <CardHeader>
              <CardTitle>Vulnerabilidades Detectadas</CardTitle>
              <CardDescription>
                {displayScan.total_vulnerabilities} vulnerabilidades encontradas en este escaneo
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={AlertTriangle}
                title="Sin vulnerabilidades"
                description="No se detectaron vulnerabilidades en este escaneo o los detalles estarán disponibles al completarse."
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Terminal className="h-5 w-5" />
                Logs del Escaneo
              </CardTitle>
              <CardDescription>
                Registro de actividad en tiempo real
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-background border rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto space-y-1">
                <div className="text-muted-foreground text-center py-8">
                  Los logs en tiempo real estarán disponibles próximamente.
                </div>
                {displayScan.status === 'running' && (
                  <div className="flex gap-2 animate-pulse justify-center">
                    <span className="text-primary">Escaneando...</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Stop Dialog */}
      <ConfirmDialog
        open={showStopDialog}
        onOpenChange={setShowStopDialog}
        title="Detener escaneo"
        description="¿Estás seguro de que deseas detener este escaneo? El progreso actual se guardará pero no podrás reanudar desde este punto."
        confirmLabel="Detener"
        variant="destructive"
        onConfirm={handleStopScan}
      />
    </div>
  );
}
