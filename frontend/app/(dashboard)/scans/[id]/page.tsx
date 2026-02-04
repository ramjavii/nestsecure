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

// Mock data for demo
const mockScan: Scan = {
  id: '1',
  name: 'Escaneo Red Interna',
  description: 'Escaneo completo de la red interna 192.168.1.0/24',
  scan_type: 'full',
  status: 'running',
  progress: 67,
  targets: ['192.168.1.0/24'],
  port_range: '1-65535',
  total_hosts_scanned: 254,
  total_hosts_up: 45,
  total_services_found: 128,
  total_vulnerabilities: 23,
  vuln_critical: 2,
  vuln_high: 5,
  vuln_medium: 8,
  vuln_low: 8,
  started_at: new Date(Date.now() - 3600000).toISOString(),
  completed_at: null,
  created_at: new Date(Date.now() - 7200000).toISOString(),
  updated_at: new Date().toISOString(),
};

const mockHosts = [
  { ip: '192.168.1.1', hostname: 'router.local', os: 'RouterOS', ports: [22, 80, 443], status: 'up' },
  { ip: '192.168.1.10', hostname: 'dc01.local', os: 'Windows Server 2019', ports: [53, 88, 389, 636, 3389], status: 'up' },
  { ip: '192.168.1.20', hostname: 'web-prod-01', os: 'Ubuntu 22.04', ports: [22, 80, 443, 8080], status: 'up' },
  { ip: '192.168.1.21', hostname: 'web-prod-02', os: 'Ubuntu 22.04', ports: [22, 80, 443, 8080], status: 'up' },
  { ip: '192.168.1.30', hostname: 'db-master', os: 'CentOS 8', ports: [22, 3306, 33060], status: 'up' },
];

const mockVulns: Partial<Vulnerability>[] = [
  { id: '1', name: 'Apache Log4j RCE', severity: 'critical', cve_id: 'CVE-2021-44228', cvss_score: 10.0, status: 'open' },
  { id: '2', name: 'SQL Injection', severity: 'critical', cve_id: null, cvss_score: 9.8, status: 'open' },
  { id: '3', name: 'OpenSSL Buffer Overflow', severity: 'high', cve_id: 'CVE-2022-3602', cvss_score: 7.5, status: 'open' },
  { id: '4', name: 'XSS Vulnerability', severity: 'medium', cve_id: null, cvss_score: 6.1, status: 'acknowledged' },
  { id: '5', name: 'Weak SSH Ciphers', severity: 'low', cve_id: null, cvss_score: 3.7, status: 'in_progress' },
];

const mockLogs = [
  { time: '10:30:15', level: 'INFO', message: 'Iniciando escaneo de red 192.168.1.0/24' },
  { time: '10:30:16', level: 'INFO', message: 'Descubriendo hosts activos...' },
  { time: '10:31:45', level: 'INFO', message: 'Encontrados 45 hosts activos' },
  { time: '10:31:46', level: 'INFO', message: 'Iniciando escaneo de puertos...' },
  { time: '10:45:23', level: 'INFO', message: 'Escaneo de puertos completado. 128 servicios detectados.' },
  { time: '10:45:24', level: 'INFO', message: 'Iniciando detección de servicios...' },
  { time: '10:52:18', level: 'WARN', message: 'Timeout en host 192.168.1.45 - reintentando...' },
  { time: '10:53:01', level: 'INFO', message: 'Detección de servicios completada.' },
  { time: '10:53:02', level: 'INFO', message: 'Iniciando análisis de vulnerabilidades...' },
  { time: '11:15:34', level: 'CRITICAL', message: 'Vulnerabilidad crítica detectada: CVE-2021-44228 en 192.168.1.20' },
  { time: '11:16:45', level: 'HIGH', message: 'Vulnerabilidad alta detectada: CVE-2022-3602 en 192.168.1.21' },
  { time: '11:30:00', level: 'INFO', message: 'Progreso: 67% completado...' },
];

export default function ScanDetailPage({ params }: ScanDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { data: scan, isLoading } = useScan(id);
  const stopScan = useStopScan();
  const { toast } = useToast();
  const [showStopDialog, setShowStopDialog] = useState(false);
  const [pollingProgress, setPollingProgress] = useState(67);

  // Use mock data for demo
  const displayScan = scan || mockScan;

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
                {mockHosts.length} hosts activos encontrados
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IP</TableHead>
                    <TableHead>Hostname</TableHead>
                    <TableHead>Sistema Operativo</TableHead>
                    <TableHead>Puertos Abiertos</TableHead>
                    <TableHead>Estado</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockHosts.map((host) => (
                    <TableRow key={host.ip}>
                      <TableCell className="font-mono">{host.ip}</TableCell>
                      <TableCell>{host.hostname}</TableCell>
                      <TableCell>{host.os}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {host.ports.slice(0, 4).map((port) => (
                            <code
                              key={port}
                              className="px-1.5 py-0.5 bg-muted rounded text-xs"
                            >
                              {port}
                            </code>
                          ))}
                          {host.ports.length > 4 && (
                            <span className="text-xs text-muted-foreground">
                              +{host.ports.length - 4} más
                            </span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-status-success">
                          <span className="h-1.5 w-1.5 rounded-full bg-status-success" />
                          Activo
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vulnerabilities Tab */}
        <TabsContent value="vulnerabilities">
          <Card>
            <CardHeader>
              <CardTitle>Vulnerabilidades Detectadas</CardTitle>
              <CardDescription>
                {mockVulns.length} vulnerabilidades encontradas en este escaneo
              </CardDescription>
            </CardHeader>
            <CardContent>
              {mockVulns.length === 0 ? (
                <EmptyState
                  icon={AlertTriangle}
                  title="Sin vulnerabilidades"
                  description="No se detectaron vulnerabilidades en este escaneo."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Severidad</TableHead>
                      <TableHead>CVE</TableHead>
                      <TableHead>CVSS</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockVulns.map((vuln) => (
                      <TableRow key={vuln.id}>
                        <TableCell>
                          <Link
                            href={`/vulnerabilities/${vuln.id}`}
                            className="font-medium hover:text-primary transition-colors"
                          >
                            {vuln.name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <SeverityBadge severity={vuln.severity!} size="sm" />
                        </TableCell>
                        <TableCell>
                          {vuln.cve_id ? (
                            <code className="text-sm">{vuln.cve_id}</code>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm font-medium">
                            {vuln.cvss_score?.toFixed(1)}
                          </span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={vuln.status!} size="sm" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
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
                {mockLogs.map((log, index) => (
                  <div key={index} className="flex gap-2">
                    <span className="text-muted-foreground">[{log.time}]</span>
                    <span
                      className={
                        log.level === 'CRITICAL'
                          ? 'text-severity-critical'
                          : log.level === 'HIGH'
                          ? 'text-severity-high'
                          : log.level === 'WARN'
                          ? 'text-severity-medium'
                          : 'text-foreground'
                      }
                    >
                      [{log.level}]
                    </span>
                    <span>{log.message}</span>
                  </div>
                ))}
                {displayScan.status === 'running' && (
                  <div className="flex gap-2 animate-pulse">
                    <span className="text-muted-foreground">[--:--:--]</span>
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
