'use client';

import { cn } from '@/lib/utils';
import type { Criticality } from '@/types';

interface CriticalityBadgeProps {
  criticality: Criticality;
  size?: 'sm' | 'md' | 'lg';
}

const criticalityConfig: Record<Criticality, { label: string; className: string }> = {
  critical: {
    label: 'Crítico',
    className: 'bg-severity-critical/15 text-severity-critical border-severity-critical/30',
  },
  high: {
    label: 'Alto',
    className: 'bg-severity-high/15 text-severity-high border-severity-high/30',
  },
  medium: {
    label: 'Medio',
    className: 'bg-severity-medium/15 text-severity-medium border-severity-medium/30',
  },
  low: {
    label: 'Bajo',
    className: 'bg-severity-low/15 text-severity-low border-severity-low/30',
  },
};

const sizeStyles = {
  sm: 'text-[10px] px-1.5 py-0.5',
  md: 'text-xs px-2 py-1',
  lg: 'text-sm px-3 py-1.5',
};

export function CriticalityBadge({ criticality, size = 'md' }: CriticalityBadgeProps) {
  const config = criticalityConfig[criticality];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 font-medium rounded-md border',
        config.className,
        sizeStyles[size]
      )}
    >
      {config.label}
    </span>
  );
}
