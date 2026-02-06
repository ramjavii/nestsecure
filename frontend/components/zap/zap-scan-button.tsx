'use client';

/**
 * NESTSECURE - ZAP Scan Button Component
 *
 * Componente para iniciar y monitorear escaneos OWASP ZAP.
 * 
 * Features:
 * - Selector de modo de escaneo (Quick, Standard, Full, API, SPA)
 * - Barra de progreso con fases
 * - Resumen de alertas al completar
 * - Cancelación de escaneos en progreso
 */

import { useState, useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Play,
  Square,
  Shield,
  Bug,
  Globe,
  Code,
  Smartphone,
  XCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useZapScan,
  useZapScanStatus,
  useZapScanResults,
  useCancelZapScan,
  useZapAvailable,
  useZapProfiles,
  getZapPhaseDisplayName,
  getZapRiskColor,
  type ZapScanMode,
  type ZapScanProgress,
  type ZapAlertsSummary,
} from '@/hooks/use-zap';

// =============================================================================
// TYPES
// =============================================================================

interface ZapScanButtonProps {
  /** Target URL to scan (optional, can be entered by user) */
  defaultUrl?: string;
  /** Asset ID to associate with scan */
  assetId?: string;
  /** Default scan mode */
  defaultMode?: ZapScanMode;
  /** Show mode selector */
  showModeSelector?: boolean;
  /** Compact mode (button only) */
  compact?: boolean;
  /** Callback when scan completes */
  onComplete?: (taskId: string, success: boolean) => void;
  /** Callback when scan fails */
  onError?: (error: Error) => void;
  /** Additional class names */
  className?: string;
}

interface ScanModeOption {
  value: ZapScanMode;
  label: string;
  description: string;
  icon: React.ReactNode;
  duration: string;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const SCAN_MODES: ScanModeOption[] = [
  {
    value: 'quick',
    label: 'Rápido',
    description: 'Spider + Pasivo (5 min)',
    icon: <Play className="h-4 w-4" />,
    duration: '~5 minutos',
  },
  {
    value: 'standard',
    label: 'Estándar',
    description: 'Spider + Pasivo + Activo',
    icon: <Shield className="h-4 w-4" />,
    duration: '~30 minutos',
  },
  {
    value: 'full',
    label: 'Completo',
    description: 'Spider + Ajax + Activo',
    icon: <Bug className="h-4 w-4" />,
    duration: '~1 hora',
  },
  {
    value: 'api',
    label: 'API',
    description: 'REST/GraphQL APIs',
    icon: <Code className="h-4 w-4" />,
    duration: '~30 minutos',
  },
  {
    value: 'spa',
    label: 'SPA',
    description: 'Single Page Apps',
    icon: <Smartphone className="h-4 w-4" />,
    duration: '~40 minutos',
  },
  {
    value: 'passive',
    label: 'Pasivo',
    description: 'Solo análisis pasivo',
    icon: <Globe className="h-4 w-4" />,
    duration: '~10 minutos',
  },
];

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

function AlertsSummaryBadges({ summary }: { summary: ZapAlertsSummary }) {
  return (
    <div className="flex gap-2 flex-wrap">
      {summary.high > 0 && (
        <Badge variant="destructive">{summary.high} Alta</Badge>
      )}
      {summary.medium > 0 && (
        <Badge className="bg-orange-500">{summary.medium} Media</Badge>
      )}
      {summary.low > 0 && (
        <Badge className="bg-yellow-500 text-black">{summary.low} Baja</Badge>
      )}
      {summary.informational > 0 && (
        <Badge variant="secondary">{summary.informational} Info</Badge>
      )}
    </div>
  );
}

function ScanProgress({ progress }: { progress: ZapScanProgress }) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">
          {getZapPhaseDisplayName(progress.phase)}
        </span>
        <span className="font-medium">{progress.overall_progress}%</span>
      </div>
      <Progress value={progress.overall_progress} className="h-2" />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{progress.urls_found} URLs encontradas</span>
        <span>{progress.alerts_found} alertas</span>
      </div>
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function ZapScanButton({
  defaultUrl = '',
  assetId,
  defaultMode = 'standard',
  showModeSelector = true,
  compact = false,
  onComplete,
  onError,
  className,
}: ZapScanButtonProps) {
  // State
  const [targetUrl, setTargetUrl] = useState(defaultUrl);
  const [mode, setMode] = useState<ZapScanMode>(defaultMode);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Hooks
  const { isAvailable, isLoading: checkingZap } = useZapAvailable();
  const scanMutation = useZapScan();
  const cancelMutation = useCancelZapScan();
  const { data: statusData, isLoading: statusLoading } = useZapScanStatus(taskId || '');
  const { data: resultsData } = useZapScanResults(
    taskId && statusData?.status === 'completed' ? taskId : ''
  );

  // Derived state
  const isScanning = taskId !== null && statusData?.status === 'running';
  const isPending = taskId !== null && (statusData?.status === 'pending' || statusData?.status === 'queued');
  const isCompleted = statusData?.status === 'completed';
  const isFailed = statusData?.status === 'failed';
  const progress = statusData?.progress;

  // Handle completion
  useEffect(() => {
    if (isCompleted && taskId) {
      setShowResults(true);
      onComplete?.(taskId, true);
    } else if (isFailed && taskId) {
      onError?.(new Error(statusData?.error || 'Scan failed'));
    }
  }, [isCompleted, isFailed, taskId, statusData?.error, onComplete, onError]);

  // Handlers
  const handleStartScan = useCallback(async () => {
    if (!targetUrl.trim()) {
      return;
    }

    try {
      const result = await scanMutation.mutateAsync({
        target_url: targetUrl.trim(),
        mode,
        asset_id: assetId,
      });
      setTaskId(result.task_id);
      setShowResults(false);
    } catch (error) {
      onError?.(error as Error);
    }
  }, [targetUrl, mode, assetId, scanMutation, onError]);

  const handleCancel = useCallback(async () => {
    if (taskId) {
      try {
        await cancelMutation.mutateAsync(taskId);
        setTaskId(null);
      } catch (error) {
        console.error('Failed to cancel scan:', error);
      }
    }
  }, [taskId, cancelMutation]);

  const handleReset = useCallback(() => {
    setTaskId(null);
    setShowResults(false);
  }, []);

  // Compact mode - just a button
  if (compact) {
    return (
      <Button
        onClick={handleStartScan}
        disabled={!isAvailable || isScanning || isPending || !targetUrl}
        className={className}
      >
        {isScanning || isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Escaneando...
          </>
        ) : (
          <>
            <Shield className="mr-2 h-4 w-4" />
            ZAP Scan
          </>
        )}
      </Button>
    );
  }

  // Full mode - card with all options
  return (
    <Card className={cn('w-full max-w-md', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-primary" />
          OWASP ZAP Scan
        </CardTitle>
        <CardDescription>
          Escaneo de vulnerabilidades web DAST
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* ZAP availability check */}
        {checkingZap ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Verificando ZAP...
          </div>
        ) : !isAvailable ? (
          <div className="flex items-center gap-2 text-destructive">
            <XCircle className="h-4 w-4" />
            ZAP no está disponible
          </div>
        ) : null}

        {/* URL Input */}
        <div className="space-y-2">
          <Label htmlFor="target-url">URL Objetivo</Label>
          <Input
            id="target-url"
            type="url"
            placeholder="http://target.local:8080"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            disabled={isScanning || isPending}
          />
        </div>

        {/* Mode Selector */}
        {showModeSelector && (
          <div className="space-y-2">
            <Label>Modo de Escaneo</Label>
            <Select
              value={mode}
              onValueChange={(value) => setMode(value as ZapScanMode)}
              disabled={isScanning || isPending}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCAN_MODES.map((scanMode) => (
                  <SelectItem key={scanMode.value} value={scanMode.value}>
                    <div className="flex items-center gap-2">
                      {scanMode.icon}
                      <span>{scanMode.label}</span>
                      <span className="text-xs text-muted-foreground">
                        ({scanMode.duration})
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Progress */}
        {(isScanning || isPending) && progress && (
          <ScanProgress progress={progress} />
        )}

        {/* Results Summary */}
        {showResults && resultsData && (
          <div className="space-y-3 p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              {resultsData.success ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-destructive" />
              )}
              <span className="font-medium">
                {resultsData.success ? 'Escaneo completado' : 'Escaneo fallido'}
              </span>
            </div>

            {resultsData.success && (
              <>
                <div className="text-sm text-muted-foreground">
                  {resultsData.urls_found} URLs · {resultsData.alerts_count} alertas ·{' '}
                  {Math.round(resultsData.duration_seconds / 60)} min
                </div>
                <AlertsSummaryBadges summary={resultsData.alerts_summary} />
              </>
            )}

            {resultsData.errors.length > 0 && (
              <div className="text-sm text-destructive">
                {resultsData.errors[0]}
              </div>
            )}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex gap-2">
        {isScanning || isPending ? (
          <Button
            variant="destructive"
            onClick={handleCancel}
            disabled={cancelMutation.isPending}
            className="w-full"
          >
            {cancelMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Square className="mr-2 h-4 w-4" />
            )}
            Cancelar
          </Button>
        ) : showResults ? (
          <Button onClick={handleReset} variant="outline" className="w-full">
            Nuevo Escaneo
          </Button>
        ) : (
          <Button
            onClick={handleStartScan}
            disabled={!isAvailable || !targetUrl.trim() || scanMutation.isPending}
            className="w-full"
          >
            {scanMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Iniciar Escaneo
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}

export default ZapScanButton;
