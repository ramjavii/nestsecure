'use client';

import { cn } from '@/lib/utils';
import type { Severity } from '@/types';

interface SeverityBadgeProps {
  severity: Severity;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const severityConfig: Record<Severity, { label: string; className: string }> = {
  critical: {
    label: 'Crítica',
    className: 'bg-severity-critical/15 text-severity-critical border-severity-critical/30',
  },
  high: {
    label: 'Alta',
    className: 'bg-severity-high/15 text-severity-high border-severity-high/30',
  },
  medium: {
    label: 'Media',
    className: 'bg-severity-medium/15 text-severity-medium border-severity-medium/30',
  },
  low: {
    label: 'Baja',
    className: 'bg-severity-low/15 text-severity-low border-severity-low/30',
  },
  info: {
    label: 'Info',
    className: 'bg-severity-info/15 text-severity-info border-severity-info/30',
  },
};

const sizeStyles = {
  sm: 'text-[10px] px-1.5 py-0.5',
  md: 'text-xs px-2 py-1',
  lg: 'text-sm px-3 py-1.5',
};

export function SeverityBadge({ severity, size = 'md', showLabel = true }: SeverityBadgeProps) {
  const config = severityConfig[severity];

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
          'rounded-full',
          size === 'sm' ? 'h-1.5 w-1.5' : size === 'md' ? 'h-2 w-2' : 'h-2.5 w-2.5',
          severity === 'critical' && 'bg-severity-critical animate-pulse',
          severity === 'high' && 'bg-severity-high',
          severity === 'medium' && 'bg-severity-medium',
          severity === 'low' && 'bg-severity-low',
          severity === 'info' && 'bg-severity-info'
        )}
      />
      {showLabel && config.label}
    </span>
  );
}
