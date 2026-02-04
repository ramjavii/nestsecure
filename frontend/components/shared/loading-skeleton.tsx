'use client';

import { cn } from '@/lib/utils';
import { Skeleton } from '@/components/ui/skeleton';

interface TableSkeletonProps {
  rows?: number;
  columns?: number;
}

export function TableSkeleton({ rows = 5, columns = 5 }: TableSkeletonProps) {
  return (
    <div className="w-full space-y-3">
      {/* Header */}
      <div className="flex items-center gap-4 py-3 border-b border-border">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex items-center gap-4 py-3">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}

interface CardSkeletonProps {
  hasHeader?: boolean;
  lines?: number;
}

export function CardSkeleton({ hasHeader = true, lines = 3 }: CardSkeletonProps) {
  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4">
      {hasHeader && (
        <div className="flex items-center justify-between">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-8 w-8 rounded-lg" />
        </div>
      )}
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={cn('h-4', i === lines - 1 ? 'w-2/3' : 'w-full')} />
        ))}
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-8 w-24 rounded" />
      </div>
      <div className="h-64 flex items-end justify-between gap-2 pt-4">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton
            key={i}
            className="flex-1"
            style={{ height: `${20 + Math.random() * 80}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <div className="flex items-start justify-between">
        <div className="space-y-3 flex-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-16" />
          <Skeleton className="h-3 w-32" />
        </div>
        <Skeleton className="h-12 w-12 rounded-lg" />
      </div>
    </div>
  );
}
