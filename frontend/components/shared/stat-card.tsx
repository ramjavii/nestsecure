'use client';

import { type LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string | number;
  description?: string;
  icon: LucideIcon;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info';
  isLoading?: boolean;
}

const variantStyles = {
  default: 'text-primary bg-primary/10',
  success: 'text-status-success bg-status-success/10',
  warning: 'text-status-warning bg-status-warning/10',
  danger: 'text-severity-critical bg-severity-critical/10',
  info: 'text-status-info bg-status-info/10',
};

export function StatCard({
  title,
  value,
  description,
  icon: Icon,
  trend,
  variant = 'default',
  isLoading,
}: StatCardProps) {
  if (isLoading) {
    return (
      <Card className="overflow-hidden">
        <CardContent className="p-6">
          <div className="flex items-start justify-between">
            <div className="space-y-3 flex-1">
              <div className="h-4 w-24 bg-muted animate-pulse rounded" />
              <div className="h-8 w-16 bg-muted animate-pulse rounded" />
              <div className="h-3 w-32 bg-muted animate-pulse rounded" />
            </div>
            <div className="h-12 w-12 bg-muted animate-pulse rounded-lg" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold tracking-tight">{value}</p>
              {trend && (
                <span
                  className={cn(
                    'text-xs font-medium px-1.5 py-0.5 rounded',
                    trend.isPositive
                      ? 'text-status-success bg-status-success/10'
                      : 'text-severity-critical bg-severity-critical/10'
                  )}
                >
                  {trend.isPositive ? '+' : ''}{trend.value}%
                </span>
              )}
            </div>
            {description && (
              <p className="text-xs text-muted-foreground">{description}</p>
            )}
          </div>
          <div className={cn('p-3 rounded-lg', variantStyles[variant])}>
            <Icon className="h-6 w-6" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
