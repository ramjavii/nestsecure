'use client';

import { cn } from '@/lib/utils';
import type { ScanStatus, AssetStatus, VulnStatus } from '@/types';

type Status = ScanStatus | AssetStatus | VulnStatus;

interface StatusBadgeProps {
  status: Status;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
}

const statusConfig: Record<string, { label: string; className: string; dotClassName?: string }> = {
  // Scan statuses
  pending: {
    label: 'Pendiente',
    className: 'bg-muted text-muted-foreground border-muted-foreground/30',
  },
  queued: {
    label: 'En cola',
    className: 'bg-status-info/15 text-status-info border-status-info/30',
  },
  running: {
    label: 'En ejecución',
    className: 'bg-status-warning/15 text-status-warning border-status-warning/30',
    dotClassName: 'animate-pulse',
  },
  completed: {
    label: 'Completado',
    className: 'bg-status-success/15 text-status-success border-status-success/30',
  },
  failed: {
    label: 'Fallido',
    className: 'bg-severity-critical/15 text-severity-critical border-severity-critical/30',
  },
  cancelled: {
    label: 'Cancelado',
    className: 'bg-muted text-muted-foreground border-muted-foreground/30',
  },
  // Asset statuses
  active: {
    label: 'Activo',
    className: 'bg-status-success/15 text-status-success border-status-success/30',
  },
  inactive: {
    label: 'Inactivo',
    className: 'bg-muted text-muted-foreground border-muted-foreground/30',
  },
  maintenance: {
    label: 'Mantenimiento',
    className: 'bg-status-warning/15 text-status-warning border-status-warning/30',
  },
  // Vulnerability statuses
  open: {
    label: 'Abierta',
    className: 'bg-severity-critical/15 text-severity-critical border-severity-critical/30',
  },
  acknowledged: {
    label: 'Reconocida',
    className: 'bg-status-warning/15 text-status-warning border-status-warning/30',
  },
  in_progress: {
    label: 'En progreso',
    className: 'bg-status-info/15 text-status-info border-status-info/30',
  },
  fixed: {
    label: 'Corregida',
    className: 'bg-status-success/15 text-status-success border-status-success/30',
  },
  false_positive: {
    label: 'Falso positivo',
    className: 'bg-muted text-muted-foreground border-muted-foreground/30',
  },
};

const sizeStyles = {
  sm: 'text-[10px] px-1.5 py-0.5',
  md: 'text-xs px-2 py-1',
  lg: 'text-sm px-3 py-1.5',
};

export function StatusBadge({ status, size = 'md', animated }: StatusBadgeProps) {
  const config = statusConfig[status] || { label: status, className: 'bg-muted text-muted-foreground' };

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-md border',
        config.className,
        sizeStyles[size]
      )}
    >
      <span
        className={cn(
          'rounded-full bg-current',
          size === 'sm' ? 'h-1.5 w-1.5' : size === 'md' ? 'h-2 w-2' : 'h-2.5 w-2.5',
          (animated || config.dotClassName) && config.dotClassName
        )}
      />
      {config.label}
    </span>
  );
}
