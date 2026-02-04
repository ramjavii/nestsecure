'use client';

import { cn } from '@/lib/utils';

interface ProgressBarProps {
  value: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  variant?: 'default' | 'success' | 'warning' | 'danger';
  animated?: boolean;
}

const variantStyles = {
  default: 'bg-primary',
  success: 'bg-status-success',
  warning: 'bg-status-warning',
  danger: 'bg-severity-critical',
};

const sizeStyles = {
  sm: 'h-1',
  md: 'h-2',
  lg: 'h-3',
};

export function ProgressBar({
  value,
  max = 100,
  size = 'md',
  showLabel = true,
  variant = 'default',
  animated,
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100);

  return (
    <div className="flex items-center gap-2 w-full">
      <div className={cn('flex-1 bg-muted rounded-full overflow-hidden', sizeStyles[size])}>
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            variantStyles[variant],
            animated && 'animate-pulse'
          )}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs font-medium text-muted-foreground min-w-[3ch] text-right">
          {Math.round(percentage)}%
        </span>
      )}
    </div>
  );
}
