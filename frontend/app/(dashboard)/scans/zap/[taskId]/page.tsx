'use client';

/**
 * ZAP Scan Results Page
 * 
 * Displays real-time status and results of an OWASP ZAP scan.
 * Includes progress tracking by phase, alerts summary, and detailed alerts table.
 */

import { use, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  ArrowLeft,
  Shield,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Globe,
  ExternalLink,
  XCircle,
  Info,
  Bug,
  Link2,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { PageHeader } from '@/components/shared/page-header';
import { StatCard } from '@/components/shared/stat-card';
import { EmptyState } from '@/components/shared/empty-state';
import { 
  useZapScanStatus, 
  useZapScanResults,
  useCancelZapScan,
  getZapPhaseDisplayName,
  getZapRiskColor,
  type ZapAlert,
  type ZapAlertsSummary,
  type ZapScanProgress,
} from '@/hooks/use-zap';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface ZapResultsPageProps {
  params: Promise<{ taskId: string }>;
}

// Status icon component
function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case 'failed':
    case 'cancelled':
      return <XCircle className="h-5 w-5 text-red-500" />;
    case 'running':
      return <Bug className="h-5 w-5 text-blue-500 animate-spin" />;
    default:
      return <Clock className="h-5 w-5 text-yellow-500" />;
  }
}

// Risk badge component
function RiskBadge({ risk }: { risk: string }) {
  const config: Record<string, { label: string; className: string }> = {
    high: { label: 'Alta', className: 'bg-red-500/20 text-red-400 border-red-500/30' },
    medium: { label: 'Media', className: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
    low: { label: 'Baja', className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
    informational: { label: 'Info', className: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  };
  
  const riskConfig = config[risk] || config.informational;
  
  return (
    <Badge variant="outline" className={riskConfig.className}>
      {riskConfig.label}
    </Badge>
  );
}

// Alerts summary component
function AlertsSummaryCard({ summary }: { summary: ZapAlertsSummary | undefined }) {
  if (!summary) return null;
  
  return (
    <div className="grid grid-cols-4 gap-2 p-4 bg-muted/50 rounded-lg">
      <div className="text-center">
        <div className="text-2xl font-bold text-red-500">{summary.high}</div>
        <div className="text-xs text-muted-foreground">Alta</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-orange-500">{summary.medium}</div>
        <div className="text-xs text-muted-foreground">Media</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-yellow-500">{summary.low}</div>
        <div className="text-xs text-muted-foreground">Baja</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-500">{summary.informational}</div>
        <div className="text-xs text-muted-foreground">Info</div>
      </div>
    </div>
  );
}

// Progress phases component
function ScanProgress({ progress }: { progress: ZapScanProgress | undefined }) {
  if (!progress) return null;

  const phases = [
    { name: 'Spider', value: progress.spider_progress, phase: 'spider' },
    { name: 'Ajax Spider', value: progress.ajax_spider_progress, phase: 'ajax' },
    { name: 'Scan Activo', value: progress.active_scan_progress, phase: 'active' },
  ];

  return (
    <div className="space-y-3">
      {phases.map((p) => (
        <div key={p.phase} className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className={cn(
              'text-muted-foreground',
              progress.phase === p.phase && 'text-foreground font-medium'
            )}>
              {p.name}
            </span>
            <span className="font-medium">{p.value}%</span>
          </div>
          <Progress 
            value={p.value} 
            className={cn(
              'h-2',
              progress.phase === p.phase && 'animate-pulse'
            )} 
          />
        </div>
      ))}
      <div className="flex justify-between text-xs text-muted-foreground pt-2 border-t">
        <span>URLs encontradas: {progress.urls_found}</span>
        <span>Alertas: {progress.alerts_found}</span>
        <span>Pasivo pendiente: {progress.passive_scan_pending}</span>
      </div>
    </div>
  );
}

// Alert detail row component
function AlertRow({ alert }: { alert: ZapAlert }) {
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
        <TableCell>
          <RiskBadge risk={alert.risk} />
        </TableCell>
        <TableCell className="max-w-75">
          <div className="font-medium truncate" title={alert.name}>
            {alert.name}
          </div>
        </TableCell>
        <TableCell>
          <Badge variant="outline" className="text-xs">
            {alert.confidence}
          </Badge>
        </TableCell>
        <TableCell className="font-mono text-xs max-w-50 truncate" title={alert.url}>
          {alert.url}
        </TableCell>
        <TableCell>
          <Badge variant="secondary" className="text-xs">
            {alert.method}
          </Badge>
        </TableCell>
      </TableRow>
      <CollapsibleContent asChild>
        <TableRow className="bg-muted/30">
          <TableCell colSpan={6} className="p-0">
            <div className="p-4 space-y-4">
              {/* Description */}
              <div>
                <h4 className="text-sm font-medium mb-1">Descripción</h4>
                <p className="text-sm text-muted-foreground">{alert.description}</p>
              </div>
              
              {/* Solution */}
              <div>
                <h4 className="text-sm font-medium mb-1">Solución</h4>
                <p className="text-sm text-muted-foreground">{alert.solution}</p>
              </div>

              {/* Technical Details */}
              <div className="grid sm:grid-cols-2 gap-4">
                {alert.param && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Parámetro</h4>
                    <code className="text-xs bg-background px-2 py-1 rounded">{alert.param}</code>
                  </div>
                )}
                {alert.attack && (
                  <div>
                    <h4 className="text-sm font-medium mb-1">Ataque</h4>
                    <code className="text-xs bg-background px-2 py-1 rounded break-all">{alert.attack}</code>
                  </div>
                )}
                {alert.evidence && (
                  <div className="sm:col-span-2">
                    <h4 className="text-sm font-medium mb-1">Evidencia</h4>
                    <code className="text-xs bg-background px-2 py-1 rounded block break-all">{alert.evidence}</code>
                  </div>
                )}
              </div>

              {/* References */}
              <div className="flex flex-wrap gap-2">
                {alert.cwe_id && (
                  <Badge variant="outline" className="text-xs">
                    CWE-{alert.cwe_id}
                  </Badge>
                )}
                {alert.wasc_id && (
                  <Badge variant="outline" className="text-xs">
                    WASC-{alert.wasc_id}
                  </Badge>
                )}
                {alert.owasp_top_10 && (
                  <Badge variant="outline" className="text-xs">
                    {alert.owasp_top_10}
                  </Badge>
                )}
                {alert.reference && (
                  <a 
                    href={alert.reference} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    <ExternalLink className="h-3 w-3" />
                    Referencia
                  </a>
                )}
              </div>
            </div>
          </TableCell>
        </TableRow>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default function ZapResultsPage({ params }: ZapResultsPageProps) {
  const { taskId } = use(params);
  const router = useRouter();
  const { toast } = useToast();
  const [riskFilter, setRiskFilter] = useState<string>('all');

  // Fetch scan status with polling
  const { data: status, isLoading: statusLoading } = useZapScanStatus(taskId);
  
  // Fetch results when scan is completed
  const { data: results, isLoading: resultsLoading } = useZapScanResults(taskId, {
    enabled: status?.status === 'completed',
  });

  // Cancel mutation
  const cancelScan = useCancelZapScan();

  const handleCancelScan = async () => {
    try {
      await cancelScan.mutateAsync(taskId);
      toast({
        title: 'Escaneo cancelado',
        description: 'El escaneo ZAP ha sido cancelado.',
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo cancelar el escaneo.',
        variant: 'destructive',
      });
    }
  };

  const isRunning = status?.status === 'running' || status?.status === 'pending' || status?.status === 'queued';
  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed' || status?.status === 'cancelled';

  // Filter alerts by risk
  const filteredAlerts = results?.alerts?.filter((alert: ZapAlert) => 
    riskFilter === 'all' || alert.risk === riskFilter
  ) || [];

  // Calculate duration
  const duration = results?.started_at && results?.completed_at
    ? `${Math.round(results.duration_seconds / 60)} min`
    : status?.progress?.elapsed_seconds
      ? `${Math.round(status.progress.elapsed_seconds / 60)} min (en progreso)`
      : '-';

  if (statusLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 bg-muted animate-pulse rounded" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

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
              <Globe className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">Scan ZAP</h1>
              <Badge
                variant="outline"
                className={cn(
                  'gap-1',
                  status?.status === 'completed' && 'text-green-500 border-green-500',
                  status?.status === 'running' && 'text-blue-500 border-blue-500',
                  (status?.status === 'failed' || status?.status === 'cancelled') && 'text-red-500 border-red-500'
                )}
              >
                <StatusIcon status={status?.status || 'pending'} />
                {status?.status === 'completed' ? 'Completado' :
                 status?.status === 'running' ? 'En progreso' :
                 status?.status === 'failed' ? 'Fallido' :
                 status?.status === 'cancelled' ? 'Cancelado' : 'Pendiente'}
              </Badge>
            </div>
            <p className="text-muted-foreground font-mono">{results?.target_url || '-'}</p>
          </div>

          <div className="flex items-center gap-2">
            {isRunning && (
              <Button
                variant="destructive"
                onClick={handleCancelScan}
                disabled={cancelScan.isPending}
              >
                <XCircle className="mr-2 h-4 w-4" />
                Cancelar
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Progress for running scans */}
      {isRunning && status?.progress && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Progreso del Escaneo
            </CardTitle>
            <CardDescription>
              Fase actual: {getZapPhaseDisplayName(status.progress.phase)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ScanProgress progress={status.progress} />
          </CardContent>
        </Card>
      )}

      {/* Error message for failed scans */}
      {isFailed && status?.error && (
        <Card className="border-red-500/50 bg-red-500/5">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <p className="font-medium text-red-500">Error en el escaneo</p>
                <p className="text-sm text-muted-foreground mt-1">{status.error}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="URLs Encontradas"
          value={results?.urls_found || status?.progress?.urls_found || 0}
          icon={Link2}
          variant="default"
        />
        <StatCard
          title="Total Alertas"
          value={results?.alerts_count || status?.progress?.alerts_found || 0}
          icon={AlertTriangle}
          variant={results?.alerts_summary?.high ? 'danger' : 'warning'}
        />
        <StatCard
          title="Modo"
          value={results?.mode || 'standard'}
          icon={Shield}
          variant="info"
        />
        <StatCard
          title="Duración"
          value={duration}
          icon={Clock}
          variant="default"
        />
      </div>

      {/* Alerts Summary */}
      {(results?.alerts_summary || isCompleted) && (
        <AlertsSummaryCard summary={results?.alerts_summary} />
      )}

      {/* Errors if any */}
      {results?.errors && results.errors.length > 0 && (
        <Card className="border-yellow-500/50">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Advertencias
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
              {results.errors.map((error: string, i: number) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Alerts Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle>Alertas de Seguridad</CardTitle>
              <CardDescription>
                {filteredAlerts.length} alertas encontradas
              </CardDescription>
            </div>
            <Select value={riskFilter} onValueChange={setRiskFilter}>
              <SelectTrigger className="w-45">
                <SelectValue placeholder="Filtrar riesgo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos los riesgos</SelectItem>
                <SelectItem value="high">Alta</SelectItem>
                <SelectItem value="medium">Media</SelectItem>
                <SelectItem value="low">Baja</SelectItem>
                <SelectItem value="informational">Informativa</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {resultsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 bg-muted animate-pulse rounded" />
              ))}
            </div>
          ) : !isCompleted ? (
            <EmptyState
              icon={Clock}
              title="Esperando resultados"
              description="Los resultados aparecerán aquí cuando el escaneo complete."
            />
          ) : filteredAlerts.length === 0 ? (
            <EmptyState
              icon={CheckCircle2}
              title="Sin alertas"
              description={
                riskFilter === 'all'
                  ? "No se detectaron alertas de seguridad en este escaneo."
                  : `No hay alertas con riesgo ${riskFilter}.`
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10"></TableHead>
                  <TableHead>Riesgo</TableHead>
                  <TableHead>Alerta</TableHead>
                  <TableHead>Confianza</TableHead>
                  <TableHead>URL</TableHead>
                  <TableHead>Método</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAlerts.map((alert: ZapAlert) => (
                  <AlertRow key={alert.id} alert={alert} />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
