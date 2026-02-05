'use client';

import { cn } from '@/lib/utils';
import { CVESeverity } from '@/types';

interface CVSSBadgeProps {
  score: number | null | undefined;
  severity?: CVESeverity | string | null;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  showLabel?: boolean;
  className?: string;
}

const severityConfig = {
  CRITICAL: {
    bg: 'bg-red-500',
    text: 'text-white',
    border: 'border-red-600',
    label: 'Critical',
  },
  HIGH: {
    bg: 'bg-orange-500',
    text: 'text-white',
    border: 'border-orange-600',
    label: 'High',
  },
  MEDIUM: {
    bg: 'bg-yellow-500',
    text: 'text-black',
    border: 'border-yellow-600',
    label: 'Medium',
  },
  LOW: {
    bg: 'bg-blue-500',
    text: 'text-white',
    border: 'border-blue-600',
    label: 'Low',
  },
  NONE: {
    bg: 'bg-gray-400',
    text: 'text-white',
    border: 'border-gray-500',
    label: 'None',
  },
};

function getSeverityFromScore(score: number | null | undefined): CVESeverity {
  if (score === null || score === undefined) return 'NONE';
  if (score >= 9.0) return 'CRITICAL';
  if (score >= 7.0) return 'HIGH';
  if (score >= 4.0) return 'MEDIUM';
  if (score >= 0.1) return 'LOW';
  return 'NONE';
}

const sizeConfig = {
  sm: {
    badge: 'px-1.5 py-0.5 text-xs',
    score: 'text-xs font-medium',
  },
  md: {
    badge: 'px-2 py-1 text-sm',
    score: 'text-sm font-semibold',
  },
  lg: {
    badge: 'px-3 py-1.5 text-base',
    score: 'text-lg font-bold',
  },
};

export function CVSSBadge({
  score,
  severity,
  size = 'md',
  showScore = true,
  showLabel = true,
  className,
}: CVSSBadgeProps) {
  const effectiveSeverity = (severity?.toUpperCase() as CVESeverity) || getSeverityFromScore(score);
  const config = severityConfig[effectiveSeverity] || severityConfig.NONE;
  const sizeStyles = sizeConfig[size];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border font-medium',
        config.bg,
        config.text,
        config.border,
        sizeStyles.badge,
        className
      )}
    >
      {showScore && score !== null && score !== undefined && (
        <span className={sizeStyles.score}>{score.toFixed(1)}</span>
      )}
      {showLabel && showScore && score !== null && score !== undefined && (
        <span className="opacity-80">|</span>
      )}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

// Standalone severity badge (no score)
interface SeverityBadgeProps {
  severity: CVESeverity | string | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function SeverityBadge({ severity, size = 'md', className }: SeverityBadgeProps) {
  return (
    <CVSSBadge
      score={null}
      severity={severity}
      size={size}
      showScore={false}
      showLabel={true}
      className={className}
    />
  );
}

// Score only display (for tables)
interface CVSSScoreProps {
  score: number | null | undefined;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function CVSSScore({ score, size = 'md', className }: CVSSScoreProps) {
  if (score === null || score === undefined) {
    return (
      <span className={cn('text-muted-foreground', className)}>N/A</span>
    );
  }

  const severity = getSeverityFromScore(score);
  const config = severityConfig[severity];

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded-md font-mono font-bold',
        config.bg,
        config.text,
        sizeConfig[size].badge,
        className
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}

export default CVSSBadge;
