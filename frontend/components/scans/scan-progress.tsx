'use client';

import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, XCircle, Clock, Pause } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useScanStatus } from '@/hooks/use-scans';
import { cn } from '@/lib/utils';
import type { ScanStatus } from '@/types';

interface ScanProgressProps {
  scanId: string;
  showDetails?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const statusConfig: Record<ScanStatus, {
  label: string;
  color: string;
  bgColor: string;
  icon: React.ComponentType<{ className?: string }>;
}> = {
  pending: {
    label: 'Pendiente',
    color: 'text-gray-500',
    bgColor: 'bg-gray-100 dark:bg-gray-800',
    icon: Clock,
  },
  queued: {
    label: 'En cola',
    color: 'text-blue-500',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    icon: Clock,
  },
  running: {
    label: 'En ejecución',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
    icon: Loader2,
  },
  completed: {
    label: 'Completado',
    color: 'text-green-600',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
    icon: CheckCircle,
  },
  failed: {
    label: 'Fallido',
    color: 'text-red-600',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
    icon: XCircle,
  },
  cancelled: {
    label: 'Cancelado',
    color: 'text-orange-600',
    bgColor: 'bg-orange-100 dark:bg-orange-900/30',
    icon: Pause,
  },
};

export function ScanProgress({ 
  scanId, 
  showDetails = false, 
  size = 'md',
  className 
}: ScanProgressProps) {
  const { data: scan, isLoading, error } = useScanStatus(scanId);
  const [animatedProgress, setAnimatedProgress] = useState(0);

  // Animar el progreso suavemente
  useEffect(() => {
    if (scan?.progress !== undefined) {
      setAnimatedProgress(scan.progress);
    }
  }, [scan?.progress]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Cargando...</span>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <XCircle className="h-4 w-4 text-destructive" />
        <span className="text-sm text-destructive">Error al cargar</span>
      </div>
    );
  }

  const config = statusConfig[scan.status];
  const StatusIcon = config.icon;
  const isActive = ['running', 'pending', 'queued'].includes(scan.status);

  // Tamaños
  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const progressHeight = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className={cn('space-y-2', className)}>
      {/* Status Badge y Progreso */}
      <div className="flex items-center justify-between gap-2">
        <Badge 
          variant="outline" 
          className={cn(config.bgColor, config.color, 'border-0')}
        >
          <StatusIcon 
            className={cn(
              'mr-1 h-3 w-3',
              scan.status === 'running' && 'animate-spin'
            )} 
          />
          {config.label}
        </Badge>
        
        <span className={cn(sizeClasses[size], 'font-medium tabular-nums')}>
          {scan.progress}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <Progress 
          value={animatedProgress} 
          className={cn(
            progressHeight[size],
            'transition-all duration-500 ease-out'
          )}
        />
        
        {/* Shimmer effect for active scans */}
        {isActive && scan.progress < 100 && (
          <div className="absolute inset-0 overflow-hidden rounded-full">
            <div 
              className="absolute inset-y-0 w-1/3 bg-linear-to-r from-transparent via-white/20 to-transparent animate-shimmer"
              style={{
                animation: 'shimmer 1.5s infinite linear',
              }}
            />
          </div>
        )}
      </div>

      {/* Details (opcional) */}
      {showDetails && (
        <div className="space-y-1 animate-in fade-in-0 slide-in-from-top-2 duration-200">
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <div>Hosts escaneados:</div>
            <div className="font-medium text-foreground">
              {scan.total_hosts_up} / {scan.total_hosts_scanned}
            </div>
            
            <div>Servicios encontrados:</div>
            <div className="font-medium text-foreground">
              {scan.total_services_found}
            </div>
            
            <div>Vulnerabilidades:</div>
            <div className="flex gap-1 font-medium">
              {scan.vuln_critical > 0 && (
                <span className="text-red-600">{scan.vuln_critical}C</span>
              )}
              {scan.vuln_high > 0 && (
                <span className="text-orange-600">{scan.vuln_high}H</span>
              )}
              {scan.vuln_medium > 0 && (
                <span className="text-yellow-600">{scan.vuln_medium}M</span>
              )}
              {scan.vuln_low > 0 && (
                <span className="text-blue-600">{scan.vuln_low}L</span>
              )}
              {scan.total_vulnerabilities === 0 && (
                <span className="text-muted-foreground">0</span>
              )}
            </div>
          </div>

          {/* Tiempo estimado (cuando está running) */}
          {scan.status === 'running' && scan.started_at && (
            <div className="text-xs text-muted-foreground">
              <Clock className="mr-1 inline h-3 w-3" />
              En progreso desde{' '}
              {new Date(scan.started_at).toLocaleTimeString('es-ES', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Componente de progreso compacto para usar en listas
 */
export function ScanProgressCompact({ 
  scanId, 
  className 
}: { 
  scanId: string; 
  className?: string;
}) {
  const { data: scan } = useScanStatus(scanId);

  if (!scan) return null;

  const isActive = ['running', 'pending', 'queued'].includes(scan.status);
  const config = statusConfig[scan.status];
  const StatusIcon = config.icon;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <StatusIcon 
        className={cn(
          'h-4 w-4',
          config.color,
          scan.status === 'running' && 'animate-spin'
        )} 
      />
      <div className="flex-1">
        <Progress 
          value={scan.progress} 
          className={cn(
            'h-1.5',
            isActive && 'animate-pulse'
          )}
        />
      </div>
      <span className="text-xs tabular-nums text-muted-foreground">
        {scan.progress}%
      </span>
    </div>
  );
}
