'use client';

/**
 * NESTSECURE - ZAP Scan History Component
 *
 * Componente para mostrar el historial de escaneos ZAP.
 */

import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronRight,
  Shield,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';

// =============================================================================
// TYPES
// =============================================================================

export interface ZapScanRecord {
  id: string;
  task_id: string;
  target_url: string;
  mode: 'quick' | 'standard' | 'full' | 'api' | 'spa' | 'passive';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at: string;
  completed_at?: string;
  alerts_count?: number;
  alerts_summary?: {
    high: number;
    medium: number;
    low: number;
    informational: number;
  };
  duration_seconds?: number;
}

interface ZapScanHistoryProps {
  scans: ZapScanRecord[];
  isLoading?: boolean;
  onViewDetails?: (scanId: string) => void;
  onDelete?: (scanId: string) => void;
  className?: string;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const MODE_LABELS = {
  quick: 'Rápido',
  standard: 'Estándar',
  full: 'Completo',
  api: 'API',
  spa: 'SPA',
  passive: 'Pasivo',
};

const STATUS_CONFIG = {
  pending: {
    label: 'Pendiente',
    icon: Clock,
    className: 'text-muted-foreground',
  },
  running: {
    label: 'En progreso',
    icon: Loader2,
    className: 'text-blue-500',
    animate: true,
  },
  completed: {
    label: 'Completado',
    icon: CheckCircle2,
    className: 'text-green-500',
  },
  failed: {
    label: 'Fallido',
    icon: XCircle,
    className: 'text-destructive',
  },
  cancelled: {
    label: 'Cancelado',
    icon: XCircle,
    className: 'text-muted-foreground',
  },
};

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

function ScanStatusIcon({ status }: { status: ZapScanRecord['status'] }) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <Icon
      className={cn(
        'h-5 w-5',
        config.className,
        config.animate && 'animate-spin'
      )}
    />
  );
}

function AlertsSummaryMini({
  summary,
}: {
  summary: ZapScanRecord['alerts_summary'];
}) {
  if (!summary) return null;

  return (
    <div className="flex gap-1">
      {summary.high > 0 && (
        <Badge variant="destructive" className="h-5 text-xs px-1">
          {summary.high}
        </Badge>
      )}
      {summary.medium > 0 && (
        <Badge className="h-5 text-xs px-1 bg-orange-500">
          {summary.medium}
        </Badge>
      )}
      {summary.low > 0 && (
        <Badge className="h-5 text-xs px-1 bg-yellow-500 text-black">
          {summary.low}
        </Badge>
      )}
      {summary.informational > 0 && (
        <Badge variant="secondary" className="h-5 text-xs px-1">
          {summary.informational}
        </Badge>
      )}
    </div>
  );
}

function ScanCard({
  scan,
  onViewDetails,
  onDelete,
}: {
  scan: ZapScanRecord;
  onViewDetails?: (id: string) => void;
  onDelete?: (id: string) => void;
}) {
  const statusConfig = STATUS_CONFIG[scan.status];
  const timeAgo = formatDistanceToNow(new Date(scan.started_at), {
    addSuffix: true,
    locale: es,
  });

  return (
    <div className="flex items-center gap-4 p-4 border rounded-lg hover:bg-accent/50 transition-colors">
      <ScanStatusIcon status={scan.status} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium truncate" title={scan.target_url}>
            {scan.target_url}
          </span>
          <Badge variant="outline" className="text-xs">
            {MODE_LABELS[scan.mode]}
          </Badge>
        </div>
        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
          <span className={statusConfig.className}>{statusConfig.label}</span>
          <span>{timeAgo}</span>
          {scan.duration_seconds && (
            <span>{Math.round(scan.duration_seconds / 60)} min</span>
          )}
        </div>
      </div>

      {scan.alerts_summary && (
        <AlertsSummaryMini summary={scan.alerts_summary} />
      )}

      <div className="flex items-center gap-1">
        {onViewDetails && scan.status === 'completed' && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewDetails(scan.id)}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        )}
        {onDelete && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(scan.id)}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function ZapScanHistory({
  scans,
  isLoading = false,
  onViewDetails,
  onDelete,
  className,
}: ZapScanHistoryProps) {
  const [filter, setFilter] = useState<'all' | ZapScanRecord['status']>('all');

  const filteredScans =
    filter === 'all' ? scans : scans.filter((s) => s.status === filter);

  // Stats
  const stats = {
    total: scans.length,
    running: scans.filter((s) => s.status === 'running').length,
    completed: scans.filter((s) => s.status === 'completed').length,
    failed: scans.filter((s) => s.status === 'failed').length,
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          Historial de Escaneos
        </CardTitle>
        <CardDescription>
          {stats.total} escaneos · {stats.running} en progreso · {stats.completed}{' '}
          completados
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filter buttons */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
          >
            Todos ({stats.total})
          </Button>
          <Button
            variant={filter === 'running' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('running')}
          >
            En progreso ({stats.running})
          </Button>
          <Button
            variant={filter === 'completed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('completed')}
          >
            Completados ({stats.completed})
          </Button>
          <Button
            variant={filter === 'failed' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('failed')}
          >
            Fallidos ({stats.failed})
          </Button>
        </div>

        {/* Scans list */}
        <ScrollArea className="h-[400px]">
          <div className="space-y-2">
            {isLoading ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2" />
                Cargando historial...
              </div>
            ) : filteredScans.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No hay escaneos{filter !== 'all' ? ' con este filtro' : ''}
              </div>
            ) : (
              filteredScans.map((scan) => (
                <ScanCard
                  key={scan.id}
                  scan={scan}
                  onViewDetails={onViewDetails}
                  onDelete={onDelete}
                />
              ))
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default ZapScanHistory;
