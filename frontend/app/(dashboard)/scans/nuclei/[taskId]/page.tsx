'use client';

/**
 * Nuclei Scan Results Page
 * 
 * Displays real-time status and results of a Nuclei vulnerability scan.
 * Includes progress tracking, severity breakdown, and findings table.
 */

import { use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow, format } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  ArrowLeft,
  Shield,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Clock,
  Target,
  ExternalLink,
  RefreshCw,
  XCircle,
  Info,
  Bug,
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
import { PageHeader } from '@/components/shared/page-header';
import { StatCard } from '@/components/shared/stat-card';
import { SeverityBadge } from '@/components/shared/severity-badge';
import { EmptyState } from '@/components/shared/empty-state';
import { 
  useNucleiScanStatus, 
  useNucleiScanResults,
  useCancelNucleiScan,
  getSeverityColor,
  getScanStatusColor,
  formatScanDuration,
  type NucleiSeveritySummary,
  type NucleiFinding,
} from '@/hooks/use-nuclei';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { useState } from 'react';

interface NucleiResultsPageProps {
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
      return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
    default:
      return <Clock className="h-5 w-5 text-yellow-500" />;
  }
}

// Severity summary badges
function SeveritySummaryCard({ summary }: { summary: NucleiSeveritySummary | null }) {
  if (!summary) return null;
  
  return (
    <div className="grid grid-cols-5 gap-2 p-4 bg-muted/50 rounded-lg">
      <div className="text-center">
        <div className="text-2xl font-bold text-red-500">{summary.critical}</div>
        <div className="text-xs text-muted-foreground">Críticas</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-orange-500">{summary.high}</div>
        <div className="text-xs text-muted-foreground">Altas</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-yellow-500">{summary.medium}</div>
        <div className="text-xs text-muted-foreground">Medias</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-blue-500">{summary.low}</div>
        <div className="text-xs text-muted-foreground">Bajas</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold text-gray-500">{summary.info}</div>
        <div className="text-xs text-muted-foreground">Info</div>
      </div>
    </div>
  );
}

export default function NucleiResultsPage({ params }: NucleiResultsPageProps) {
  const { taskId } = use(params);
  const router = useRouter();
  const { toast } = useToast();
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [page, setPage] = useState(1);

  // Fetch scan status with polling
  const { data: status, isLoading: statusLoading } = useNucleiScanStatus(taskId);
  
  // Fetch results (only when scan is completed or running)
  const { data: resultsData, isLoading: resultsLoading } = useNucleiScanResults(
    taskId,
    {
      severity: severityFilter !== 'all' ? severityFilter : undefined,
      page,
      page_size: 50,
      enabled: status?.status === 'completed' || status?.status === 'running',
    }
  );

  // Cancel mutation
  const cancelScan = useCancelNucleiScan();

  const handleCancelScan = async () => {
    try {
      await cancelScan.mutateAsync(taskId);
      toast({
        title: 'Escaneo cancelado',
        description: 'El escaneo Nuclei ha sido cancelado.',
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

  // Calculate duration
  const duration = status?.started_at && status?.completed_at
    ? formatScanDuration(status.started_at, status.completed_at)
    : status?.started_at
      ? `${formatDistanceToNow(new Date(status.started_at), { locale: es })} (en progreso)`
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
              <Bug className="h-6 w-6 text-primary" />
              <h1 className="text-2xl font-bold">Scan Nuclei</h1>
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
            <p className="text-muted-foreground font-mono">{status?.target}</p>
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
      {isRunning && (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">
                  Escaneando vulnerabilidades...
                </span>
                <span className="font-medium">
                  {status?.total_findings || 0} hallazgos encontrados
                </span>
              </div>
              <Progress value={undefined} className="animate-pulse" />
              <p className="text-xs text-muted-foreground">
                Perfil: {status?.profile || 'default'} | 
                Iniciado: {status?.started_at 
                  ? formatDistanceToNow(new Date(status.started_at), { addSuffix: true, locale: es })
                  : 'Pendiente'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error message for failed scans */}
      {isFailed && status?.error_message && (
        <Card className="border-red-500/50 bg-red-500/5">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 mt-0.5" />
              <div>
                <p className="font-medium text-red-500">Error en el escaneo</p>
                <p className="text-sm text-muted-foreground mt-1">{status.error_message}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Target"
          value={status?.target?.split('/')[2] || status?.target || '-'}
          icon={Target}
          variant="default"
        />
        <StatCard
          title="Total Hallazgos"
          value={status?.total_findings || 0}
          icon={AlertTriangle}
          variant={status?.summary?.critical ? 'danger' : 'warning'}
        />
        <StatCard
          title="CVEs Únicos"
          value={status?.unique_cves?.length || 0}
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

      {/* Severity Summary */}
      {status?.summary && (
        <SeveritySummaryCard summary={status.summary} />
      )}

      {/* CVEs Found */}
      {status?.unique_cves && status.unique_cves.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">CVEs Detectados</CardTitle>
            <CardDescription>
              {status.unique_cves.length} CVEs únicos encontrados
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {status.unique_cves.map((cve) => (
                <Link key={cve} href={`/cve?search=${cve}`}>
                  <Badge variant="outline" className="font-mono hover:bg-primary/10 cursor-pointer">
                    {cve}
                  </Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <CardTitle>Hallazgos</CardTitle>
              <CardDescription>
                {resultsData?.total_findings || 0} vulnerabilidades detectadas
              </CardDescription>
            </div>
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-45">
                <SelectValue placeholder="Filtrar severidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las severidades</SelectItem>
                <SelectItem value="critical">Crítica</SelectItem>
                <SelectItem value="high">Alta</SelectItem>
                <SelectItem value="medium">Media</SelectItem>
                <SelectItem value="low">Baja</SelectItem>
                <SelectItem value="info">Informativa</SelectItem>
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
          ) : !resultsData?.findings || resultsData.findings.length === 0 ? (
            <EmptyState
              icon={isCompleted ? CheckCircle2 : AlertTriangle}
              title={isCompleted ? "Sin vulnerabilidades" : "Esperando resultados"}
              description={
                isCompleted 
                  ? "No se detectaron vulnerabilidades en este escaneo."
                  : "Los resultados aparecerán aquí cuando el escaneo progrese."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Severidad</TableHead>
                  <TableHead>Template</TableHead>
                  <TableHead>Nombre</TableHead>
                  <TableHead>CVE</TableHead>
                  <TableHead>URL Afectada</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resultsData.findings.map((finding: NucleiFinding, index: number) => (
                  <TableRow key={`${finding.template_id}-${index}`}>
                    <TableCell>
                      <SeverityBadge 
                        severity={finding.severity as 'critical' | 'high' | 'medium' | 'low' | 'info'} 
                        size="sm" 
                      />
                    </TableCell>
                    <TableCell>
                      <code className="text-xs bg-muted px-1 py-0.5 rounded">
                        {finding.template_id}
                      </code>
                    </TableCell>
                    <TableCell className="max-w-75">
                      <div className="truncate font-medium" title={finding.template_name}>
                        {finding.template_name}
                      </div>
                      {finding.description && (
                        <p className="text-xs text-muted-foreground truncate" title={finding.description}>
                          {finding.description}
                        </p>
                      )}
                    </TableCell>
                    <TableCell>
                      {finding.cve ? (
                        <Link href={`/cve?search=${finding.cve}`}>
                          <Badge variant="outline" className="font-mono text-xs hover:bg-primary/10">
                            {finding.cve}
                          </Badge>
                        </Link>
                      ) : (
                        <span className="text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="max-w-50 truncate font-mono text-xs" title={finding.matched_at}>
                        {finding.matched_at}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {resultsData && (resultsData.total_findings || 0) > 50 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                Anterior
              </Button>
              <span className="text-sm text-muted-foreground">
                Página {page} de {resultsData.total_pages || 1}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => p + 1)}
                disabled={page >= (resultsData.total_pages || 1)}
              >
                Siguiente
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
