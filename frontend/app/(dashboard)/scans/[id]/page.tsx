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
  ChevronDown,
  ChevronRight,
  Shield,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { PageHeader } from '@/components/shared/page-header';
import { StatCard } from '@/components/shared/stat-card';
import { StatusBadge } from '@/components/shared/status-badge';
import { SeverityBadge } from '@/components/shared/severity-badge';
import { ProgressBar } from '@/components/shared/progress-bar';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import { useScan, useStopScan, useScanResults, useScanHosts, useScanLogs } from '@/hooks/use-scans';
import { useToast } from '@/hooks/use-toast';
import type { Scan, Vulnerability, Asset, ScanHost, ScanLogEntry } from '@/types';
import { cn } from '@/lib/utils';

interface ScanDetailPageProps {
  params: Promise<{ id: string }>;
}

// Empty defaults for production mode
const emptyScan: Scan = {
  id: '',
  name: 'Cargando...',
  description: undefined,
  scan_type: 'discovery',
  status: 'queued',
  progress: 0,
  targets: [],
  port_range: undefined,
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

// Helper function to map severity class to display
function getSeverityFromClass(severityClass: string): 'critical' | 'high' | 'medium' | 'low' | 'info' {
  const mapping: Record<string, 'critical' | 'high' | 'medium' | 'low' | 'info'> = {
    critical: 'critical',
    high: 'high',
    medium: 'medium',
    low: 'low',
    info: 'info',
  };
  return mapping[severityClass] || 'info';
}

// Log level icon component
function LogLevelIcon({ level }: { level: string }) {
  switch (level) {
    case 'error':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'warning':
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    case 'success':
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case 'debug':
      return <Terminal className="h-4 w-4 text-gray-400" />;
    default:
      return <Info className="h-4 w-4 text-blue-500" />;
  }
}

// Host row component with expandable services
function HostRow({ host }: { host: ScanHost }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <TableRow className="cursor-pointer hover:bg-muted/50">
        <TableCell>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="p-0 h-auto">
              {isOpen ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
        </TableCell>
        <TableCell className="font-mono font-medium">{host.ip_address}</TableCell>
        <TableCell>{host.hostname || '-'}</TableCell>
        <TableCell>{host.operating_system || 'Desconocido'}</TableCell>
        <TableCell>
          <Badge variant="secondary">{host.services_count}</Badge>
        </TableCell>
        <TableCell>
          <div className="flex items-center gap-2">
            <span className="font-medium">{host.vulnerabilities_count}</span>
            {host.vuln_critical > 0 && (
              <Badge variant="destructive" className="text-xs">
                {host.vuln_critical} críticas
              </Badge>
            )}
            {host.vuln_high > 0 && (
              <Badge className="bg-orange-500 text-xs">
                {host.vuln_high} altas
              </Badge>
            )}
          </div>
        </TableCell>
        <TableCell>
          <StatusBadge status={host.status} />
        </TableCell>
      </TableRow>
      <CollapsibleContent asChild>
        <TableRow className="bg-muted/30">
          <TableCell colSpan={7} className="p-0">
            <div className="p-4 space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Network className="h-4 w-4" />
                Servicios Detectados ({host.services.length})
              </h4>
              {host.services.length > 0 ? (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {host.services.map((service) => (
                    <div
                      key={service.id}
                      className="flex items-center gap-3 p-3 rounded-md bg-background border group"
                    >
                      <div className={cn(
                        "h-2 w-2 rounded-full shrink-0",
                        service.state === 'open' ? 'bg-green-500' :
                        service.state === 'filtered' ? 'bg-yellow-500' : 'bg-red-500'
                      )} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-medium">
                            {service.port}/{service.protocol}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {service.state}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground truncate">
                          {service.service_name || 'Desconocido'}
                          {service.version && ` (${service.version})`}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No se detectaron servicios en este host
                </p>
              )}
            </div>
          </TableCell>
        </TableRow>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default function ScanDetailPage({ params }: ScanDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { data: scan, isLoading, refetch: refetchScan } = useScan(id);
  const stopScan = useStopScan();
  const { toast } = useToast();
  const [showStopDialog, setShowStopDialog] = useState(false);

  // Use API data with empty defaults
  const displayScan = scan || emptyScan;

  // Fetch results, hosts, and logs with polling based on scan status
  const { data: resultsData, isLoading: loadingResults, refetch: refetchResults } = useScanResults(id, displayScan.status);
  const { data: hostsData, isLoading: loadingHosts } = useScanHosts(id, displayScan.status);
  const { data: logsData, isLoading: loadingLogs } = useScanLogs(id, displayScan.status);

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

  const currentProgress = displayScan.progress;

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

          <div className="flex flex-wrap items-center gap-2">
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
                  <span className="text-muted-foreground">
                    {logsData?.current_phase || 'Preparando escaneo...'}
                  </span>
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
          value={hostsData?.total_hosts || displayScan.total_hosts_up}
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
          value={resultsData?.total_vulnerabilities || displayScan.total_vulnerabilities}
          description={`${resultsData?.summary?.critical || displayScan.vuln_critical} críticas`}
          icon={AlertTriangle}
          variant={displayScan.vuln_critical > 0 ? 'danger' : 'warning'}
        />
        <StatCard
          title="Duración"
          value={
            displayScan.duration_seconds
              ? `${Math.floor(displayScan.duration_seconds / 60)}m ${displayScan.duration_seconds % 60}s`
              : displayScan.started_at && displayScan.status === 'running'
              ? formatDistanceToNow(new Date(displayScan.started_at), { locale: es })
              : displayScan.started_at && displayScan.completed_at
              ? `${Math.floor((new Date(displayScan.completed_at).getTime() - new Date(displayScan.started_at).getTime()) / 60000)}m`
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
          <TabsTrigger value="hosts">
            Hosts
            {hostsData?.total_hosts ? (
              <Badge variant="secondary" className="ml-2">
                {hostsData.total_hosts}
              </Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="vulnerabilities">
            Vulnerabilidades
            {resultsData?.total_vulnerabilities ? (
              <Badge variant="secondary" className="ml-2">
                {resultsData.total_vulnerabilities}
              </Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="logs">
            Logs
            {logsData?.logs?.length ? (
              <Badge variant="secondary" className="ml-2">
                {logsData.logs.length}
              </Badge>
            ) : null}
          </TabsTrigger>
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
                    { label: 'Críticas', value: resultsData?.summary?.critical ?? displayScan.vuln_critical, color: 'bg-red-500' },
                    { label: 'Altas', value: resultsData?.summary?.high ?? displayScan.vuln_high, color: 'bg-orange-500' },
                    { label: 'Medias', value: resultsData?.summary?.medium ?? displayScan.vuln_medium, color: 'bg-yellow-500' },
                    { label: 'Bajas', value: resultsData?.summary?.low ?? displayScan.vuln_low, color: 'bg-blue-500' },
                    { label: 'Info', value: resultsData?.summary?.info ?? 0, color: 'bg-gray-400' },
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
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                Hosts Descubiertos
              </CardTitle>
              <CardDescription>
                {hostsData?.total_hosts || 0} hosts encontrados en este escaneo
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingHosts ? (
                <TableSkeleton columns={5} rows={5} />
              ) : hostsData?.hosts && hostsData.hosts.length > 0 ? (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {hostsData.hosts.map((host) => (
                    <Link
                      key={host.id}
                      href={`/assets/${host.id}`}
                      className="group block"
                    >
                      <div className="p-4 rounded-lg border bg-card hover:bg-muted/50 hover:border-primary/50 transition-all">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center">
                              <Server className="h-4 w-4 text-primary" />
                            </div>
                            <div>
                              <p className="font-mono font-medium text-sm">{host.ip_address}</p>
                              <p className="text-xs text-muted-foreground">
                                {host.hostname || 'Sin hostname'}
                              </p>
                            </div>
                          </div>
                          <StatusBadge status={host.status} size="sm" />
                        </div>
                        
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Network className="h-3.5 w-3.5" />
                            <span>{host.services_count} servicios</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-muted-foreground">
                            <Shield className="h-3.5 w-3.5" />
                            <span>{host.vulnerabilities_count} vulns</span>
                          </div>
                        </div>
                        
                        {(host.vuln_critical > 0 || host.vuln_high > 0) && (
                          <div className="flex gap-1.5 mt-2 pt-2 border-t">
                            {host.vuln_critical > 0 && (
                              <Badge variant="destructive" className="text-xs px-1.5 py-0">
                                {host.vuln_critical} críticas
                              </Badge>
                            )}
                            {host.vuln_high > 0 && (
                              <Badge className="bg-orange-500 hover:bg-orange-600 text-xs px-1.5 py-0">
                                {host.vuln_high} altas
                              </Badge>
                            )}
                          </div>
                        )}
                        
                        {host.operating_system && (
                          <p className="text-xs text-muted-foreground mt-2 truncate">
                            {host.operating_system}
                          </p>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={Server}
                  title="Sin hosts descubiertos"
                  description={
                    displayScan.status === 'running' || displayScan.status === 'queued'
                      ? 'El escaneo está en progreso. Los hosts aparecerán aquí cuando sean descubiertos.'
                      : 'No se encontraron hosts activos en los targets especificados.'
                  }
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vulnerabilities Tab */}
        <TabsContent value="vulnerabilities">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Vulnerabilidades Detectadas
              </CardTitle>
              <CardDescription>
                {resultsData?.total_vulnerabilities || 0} vulnerabilidades encontradas
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingResults ? (
                <TableSkeleton columns={6} rows={5} />
              ) : resultsData?.vulnerabilities && resultsData.vulnerabilities.length > 0 ? (
                <div className="rounded-md border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-24">Severidad</TableHead>
                        <TableHead>Nombre</TableHead>
                        <TableHead>CVE</TableHead>
                        <TableHead>Host</TableHead>
                        <TableHead>Puerto</TableHead>
                        <TableHead className="text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {resultsData.vulnerabilities.map((vuln) => (
                        <TableRow key={vuln.id}>
                          <TableCell>
                            <SeverityBadge severity={getSeverityFromClass(vuln.severity_class)} />
                          </TableCell>
                          <TableCell>
                            <div className="max-w-md">
                              <p className="font-medium truncate">{vuln.name}</p>
                              {(vuln as any).affected_count > 1 && (
                                <p className="text-xs text-muted-foreground">
                                  Afecta a {(vuln as any).affected_count} hosts
                                </p>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            {vuln.cve_ids.length > 0 ? (
                              <div className="flex flex-wrap gap-1">
                                {vuln.cve_ids.slice(0, 2).map((cve) => (
                                  <Badge key={cve} variant="outline" className="text-xs font-mono">
                                    {cve}
                                  </Badge>
                                ))}
                                {vuln.cve_ids.length > 2 && (
                                  <Badge variant="secondary" className="text-xs">
                                    +{vuln.cve_ids.length - 2}
                                  </Badge>
                                )}
                              </div>
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </TableCell>
                          <TableCell className="font-mono text-sm">{vuln.host || '-'}</TableCell>
                          <TableCell>
                            {vuln.port ? (
                              <Badge variant="secondary">{vuln.port}</Badge>
                            ) : (
                              '-'
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" asChild>
                              <Link href={`/vulnerabilities/${vuln.id}`}>
                                <ExternalLink className="h-4 w-4" />
                              </Link>
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : (
                <EmptyState
                  icon={Shield}
                  title="Sin vulnerabilidades detectadas"
                  description={
                    displayScan.status === 'running' || displayScan.status === 'queued'
                      ? 'El escaneo está en progreso. Las vulnerabilidades aparecerán aquí cuando sean detectadas.'
                      : 'No se detectaron vulnerabilidades en este escaneo. ¡Buen trabajo!'
                  }
                />
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
                Registro de actividad {displayScan.status === 'running' ? 'en tiempo real' : 'del escaneo'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingLogs ? (
                <div className="space-y-2">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-8 bg-muted animate-pulse rounded" />
                  ))}
                </div>
              ) : logsData?.logs && logsData.logs.length > 0 ? (
                <div className="bg-zinc-950 rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto space-y-2">
                  {logsData.logs.map((log, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-3 py-1 border-b border-zinc-800 last:border-0"
                    >
                      <LogLevelIcon level={log.level} />
                      <span className="text-zinc-500 text-xs whitespace-nowrap">
                        {log.timestamp ? format(new Date(log.timestamp), 'HH:mm:ss', { locale: es }) : '--:--:--'}
                      </span>
                      <span className={cn(
                        "flex-1",
                        log.level === 'error' && 'text-red-400',
                        log.level === 'warning' && 'text-yellow-400',
                        log.level === 'success' && 'text-green-400',
                        log.level === 'debug' && 'text-zinc-500',
                        log.level === 'info' && 'text-zinc-300',
                      )}>
                        {log.message}
                      </span>
                    </div>
                  ))}
                  {displayScan.status === 'running' && (
                    <div className="flex items-center gap-2 pt-2 text-primary animate-pulse">
                      <div className="h-2 w-2 rounded-full bg-primary animate-ping" />
                      <span>Escaneando...</span>
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState
                  icon={Terminal}
                  title="Sin logs disponibles"
                  description={
                    displayScan.status === 'queued'
                      ? 'Los logs aparecerán cuando el escaneo comience.'
                      : 'No hay logs registrados para este escaneo.'
                  }
                />
              )}
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
