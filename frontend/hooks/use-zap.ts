/**
 * NESTSECURE - ZAP React Query Hooks
 * 
 * Custom hooks for OWASP ZAP integration using TanStack Query.
 * 
 * Provides:
 * - useZapScan: Start ZAP scans
 * - useZapScanStatus: Poll scan status
 * - useZapScanResults: Get scan results
 * - useZapProfiles: List scan profiles
 * - useZapVersion: Check ZAP availability
 * - useZapAlerts: Get current alerts
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  UseQueryOptions,
  UseMutationOptions,
} from '@tanstack/react-query';
import { api } from '@/lib/api';

// =============================================================================
// TYPES
// =============================================================================

export type ZapScanMode = 'quick' | 'standard' | 'full' | 'api' | 'passive' | 'spa';

export type ZapScanStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export type ZapAlertRisk = 'informational' | 'low' | 'medium' | 'high';

export interface ZapScanRequest {
  target_url: string;
  mode?: ZapScanMode;
  asset_id?: string;
  include_patterns?: string[];
  exclude_patterns?: string[];
  timeout?: number;
}

export interface ZapScanResponse {
  task_id: string;
  target_url: string;
  mode: string;
  status: string;
  message: string;
}

export interface ZapScanProgress {
  phase: string;
  spider_progress: number;
  ajax_spider_progress: number;
  active_scan_progress: number;
  passive_scan_pending: number;
  urls_found: number;
  alerts_found: number;
  overall_progress: number;
  elapsed_seconds: number;
}

export interface ZapScanStatusResponse {
  task_id: string;
  status: ZapScanStatus;
  progress?: ZapScanProgress;
  started_at?: string;
  completed_at?: string;
  error?: string;
}

export interface ZapAlert {
  id: string;
  name: string;
  risk: ZapAlertRisk;
  confidence: string;
  url: string;
  method: string;
  param?: string;
  attack?: string;
  evidence?: string;
  description: string;
  solution: string;
  reference?: string;
  cwe_id?: number;
  wasc_id?: number;
  owasp_top_10?: string;
  plugin_id: number;
}

export interface ZapAlertsSummary {
  informational: number;
  low: number;
  medium: number;
  high: number;
  total: number;
}

export interface ZapScanResults {
  task_id: string;
  target_url: string;
  mode: string;
  status: string;
  success: boolean;
  started_at: string;
  completed_at: string;
  duration_seconds: number;
  urls_found: number;
  alerts_count: number;
  alerts_summary: ZapAlertsSummary;
  alerts: ZapAlert[];
  errors: string[];
  spider_scan_id?: string;
  active_scan_id?: string;
  context_name?: string;
}

export interface ZapProfile {
  id: string;
  name: string;
  description: string;
  spider: boolean;
  ajax_spider: boolean;
  active_scan: boolean;
  api_scan: boolean;
  timeout: number;
}

export interface ZapVersion {
  version: string;
  available: boolean;
  host: string;
  port: number;
}

// =============================================================================
// QUERY KEYS
// =============================================================================

export const zapKeys = {
  all: ['zap'] as const,
  version: () => [...zapKeys.all, 'version'] as const,
  profiles: () => [...zapKeys.all, 'profiles'] as const,
  scans: () => [...zapKeys.all, 'scans'] as const,
  scan: (taskId: string) => [...zapKeys.scans(), taskId] as const,
  scanStatus: (taskId: string) => [...zapKeys.scan(taskId), 'status'] as const,
  scanResults: (taskId: string) => [...zapKeys.scan(taskId), 'results'] as const,
  alerts: (baseUrl?: string) => [...zapKeys.all, 'alerts', baseUrl] as const,
  alertsSummary: (baseUrl?: string) => [...zapKeys.all, 'alertsSummary', baseUrl] as const,
};

// =============================================================================
// HOOKS - QUERIES
// =============================================================================

/**
 * Hook to check ZAP version and availability
 */
export function useZapVersion(
  options?: Omit<UseQueryOptions<ZapVersion, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.version(),
    queryFn: () => api.getZapVersion(),
    staleTime: 60 * 1000, // 1 minute
    ...options,
  });
}

/**
 * Hook to get ZAP scan profiles
 */
export function useZapProfiles(
  options?: Omit<UseQueryOptions<{ profiles: ZapProfile[]; total: number }, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.profiles(),
    queryFn: () => api.getZapProfiles(),
    staleTime: 5 * 60 * 1000, // 5 minutes (profiles don't change often)
    ...options,
  });
}

/**
 * Hook to poll ZAP scan status
 * Automatically polls every 3 seconds while scan is running
 */
export function useZapScanStatus(
  taskId: string,
  options?: Omit<UseQueryOptions<ZapScanStatusResponse, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.scanStatus(taskId),
    queryFn: async () => {
      const response = await api.getZapScanStatus(taskId);
      return response as unknown as ZapScanStatusResponse;
    },
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling when scan is completed, failed, or cancelled
      if (data?.status === 'completed' || data?.status === 'failed' || data?.status === 'cancelled') {
        return false;
      }
      // Poll every 3 seconds while running
      return 3000;
    },
    ...options,
  });
}

/**
 * Hook to get ZAP scan results
 */
export function useZapScanResults(
  taskId: string,
  options?: Omit<UseQueryOptions<ZapScanResults, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.scanResults(taskId),
    queryFn: async () => {
      const response = await api.getZapScanResults(taskId);
      return response as unknown as ZapScanResults;
    },
    enabled: !!taskId,
    staleTime: 60 * 1000, // Results don't change after completion
    ...options,
  });
}

/**
 * Hook to get current ZAP alerts
 */
export function useZapAlerts(
  params?: {
    base_url?: string;
    risk?: number;
    start?: number;
    count?: number;
  },
  options?: Omit<UseQueryOptions<ZapAlert[], Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.alerts(params?.base_url),
    queryFn: async () => {
      const response = await api.getZapAlerts(params);
      return response as unknown as ZapAlert[];
    },
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
}

/**
 * Hook to get ZAP alerts summary
 */
export function useZapAlertsSummary(
  baseUrl?: string,
  options?: Omit<UseQueryOptions<ZapAlertsSummary, Error>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: zapKeys.alertsSummary(baseUrl),
    queryFn: () => api.getZapAlertsSummary(baseUrl),
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
}

// =============================================================================
// HOOKS - MUTATIONS
// =============================================================================

/**
 * Hook to start a ZAP scan
 */
export function useZapScan(
  options?: UseMutationOptions<ZapScanResponse, Error, ZapScanRequest>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: ZapScanRequest) => api.startZapScan(params),
    onSuccess: () => {
      // Invalidate alerts when new scan starts
      queryClient.invalidateQueries({ queryKey: zapKeys.alerts() });
    },
    ...options,
  });
}

/**
 * Hook for quick ZAP scan (Spider + Passive)
 */
export function useZapQuickScan(
  options?: UseMutationOptions<ZapScanResponse, Error, { targetUrl: string; assetId?: string }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ targetUrl, assetId }) => api.zapQuickScan(targetUrl, assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: zapKeys.alerts() });
    },
    ...options,
  });
}

/**
 * Hook for full ZAP scan
 */
export function useZapFullScan(
  options?: UseMutationOptions<ZapScanResponse, Error, { targetUrl: string; assetId?: string }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ targetUrl, assetId }) => api.zapFullScan(targetUrl, assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: zapKeys.alerts() });
    },
    ...options,
  });
}

/**
 * Hook for ZAP API scan
 */
export function useZapApiScan(
  options?: UseMutationOptions<ZapScanResponse, Error, { targetUrl: string; openapiUrl?: string; assetId?: string }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ targetUrl, openapiUrl, assetId }) => api.zapApiScan(targetUrl, openapiUrl, assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: zapKeys.alerts() });
    },
    ...options,
  });
}

/**
 * Hook for ZAP SPA scan
 */
export function useZapSpaScan(
  options?: UseMutationOptions<ZapScanResponse, Error, { targetUrl: string; assetId?: string }>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ targetUrl, assetId }) => api.zapSpaScan(targetUrl, assetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: zapKeys.alerts() });
    },
    ...options,
  });
}

/**
 * Hook to cancel a ZAP scan
 */
export function useCancelZapScan(
  options?: UseMutationOptions<void, Error, string>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (taskId: string) => api.cancelZapScan(taskId),
    onSuccess: (_, taskId) => {
      // Update scan status
      queryClient.invalidateQueries({ queryKey: zapKeys.scanStatus(taskId) });
    },
    ...options,
  });
}

/**
 * Hook to clear ZAP session
 */
export function useClearZapSession(
  options?: UseMutationOptions<void, Error, void>
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.clearZapSession(),
    onSuccess: () => {
      // Invalidate all ZAP queries
      queryClient.invalidateQueries({ queryKey: zapKeys.all });
    },
    ...options,
  });
}

// =============================================================================
// UTILITY HOOKS
// =============================================================================

/**
 * Hook to check if ZAP is available
 */
export function useZapAvailable() {
  const { data, isLoading, error } = useZapVersion();
  
  return {
    isAvailable: data?.available ?? false,
    version: data?.version,
    isLoading,
    error,
  };
}

/**
 * Hook to get a specific profile by ID
 */
export function useZapProfile(profileId: string) {
  const { data, isLoading } = useZapProfiles();
  
  const profile = data?.profiles.find((p) => p.id === profileId);
  
  return {
    profile,
    isLoading,
  };
}

/**
 * Hook to format scan duration
 */
export function useFormatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${minutes}m ${secs}s`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}

/**
 * Get risk color for alerts
 */
export function getZapRiskColor(risk: ZapAlertRisk): string {
  switch (risk) {
    case 'high':
      return 'text-red-600 bg-red-100';
    case 'medium':
      return 'text-orange-600 bg-orange-100';
    case 'low':
      return 'text-yellow-600 bg-yellow-100';
    case 'informational':
    default:
      return 'text-blue-600 bg-blue-100';
  }
}

/**
 * Get phase display name
 */
export function getZapPhaseDisplayName(phase: string): string {
  const phases: Record<string, string> = {
    initializing: 'Inicializando',
    connecting: 'Conectando',
    preparing: 'Preparando',
    spider: 'Spider (Descubrimiento)',
    ajax_spider: 'Ajax Spider (SPA)',
    passive_scan: 'Escaneo Pasivo',
    active_scan: 'Escaneo Activo',
    collecting: 'Recolectando Resultados',
    completed: 'Completado',
  };
  return phases[phase] || phase;
}
