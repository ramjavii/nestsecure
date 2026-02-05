/**
 * Nuclei Scanning Hooks
 * 
 * React Query hooks for Nuclei vulnerability scanning operations.
 * Provides hooks for starting scans, monitoring progress, and fetching results.
 */

'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

// =============================================================================
// TYPES
// =============================================================================

export interface NucleiScanParams {
  target: string;
  profile?: string;
  scan_name?: string;
  timeout?: number;
  tags?: string[];
  severities?: string[];
}

export interface NucleiSeveritySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  total: number;
}

export interface NucleiFinding {
  template_id: string;
  template_name: string;
  severity: string;
  host: string;
  matched_at: string;
  ip: string | null;
  timestamp: string | null;
  cve: string | null;
  cvss: number | null;
  cwe_id: string | null;
  description: string | null;
  references: string[] | null;
  extracted: string[] | null;
  matcher_name: string | null;
}

export interface NucleiScanResponse {
  task_id: string;
  scan_id: string;
  status: string;
  target: string;
  profile: string;
  message: string;
}

export interface NucleiScanStatus {
  task_id: string;
  scan_id: string | null;
  status: string;
  target: string;
  profile: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_findings: number | null;
  unique_cves: string[];
  summary: NucleiSeveritySummary | null;
  error_message: string | null;
}

export interface NucleiProfile {
  name: string;
  display_name: string;
  description: string;
  estimated_time: string;
  tags: string[];
  severities: string[];
  templates_count: number | null;
}

export interface NucleiHealth {
  status: string;
  nuclei_installed: boolean;
  nuclei_version: string | null;
  templates_path: string | null;
  templates_count: number | null;
  last_updated: string | null;
}

// =============================================================================
// QUERY KEYS
// =============================================================================

export const nucleiKeys = {
  all: ['nuclei'] as const,
  profiles: () => [...nucleiKeys.all, 'profiles'] as const,
  health: () => [...nucleiKeys.all, 'health'] as const,
  scans: () => [...nucleiKeys.all, 'scans'] as const,
  scan: (taskId: string) => [...nucleiKeys.scans(), taskId] as const,
  scanResults: (taskId: string) => [...nucleiKeys.scan(taskId), 'results'] as const,
};

// =============================================================================
// HOOKS - QUERIES
// =============================================================================

/**
 * Hook to fetch available Nuclei scan profiles
 */
export function useNucleiProfiles() {
  return useQuery({
    queryKey: nucleiKeys.profiles(),
    queryFn: () => api.getNucleiProfiles(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

/**
 * Hook to check Nuclei scanner health
 */
export function useNucleiHealth() {
  return useQuery({
    queryKey: nucleiKeys.health(),
    queryFn: () => api.getNucleiHealth(),
    staleTime: 1000 * 60 * 1, // 1 minute
    retry: 1,
  });
}

/**
 * Hook to get Nuclei scan status
 * Polls every 5 seconds while scan is running
 */
export function useNucleiScanStatus(
  taskId: string | null,
  options?: { enabled?: boolean; refetchInterval?: number }
) {
  return useQuery({
    queryKey: taskId ? nucleiKeys.scan(taskId) : ['nuclei', 'scan', 'none'],
    queryFn: () => api.getNucleiScanStatus(taskId!),
    enabled: !!taskId && (options?.enabled !== false),
    refetchInterval: (query) => {
      // Auto-poll if scan is still running
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return false;
      }
      return options?.refetchInterval ?? 5000; // Poll every 5s
    },
  });
}

/**
 * Hook to get Nuclei scan results
 */
export function useNucleiScanResults(
  taskId: string | null,
  options?: {
    page?: number;
    page_size?: number;
    severity?: string;
    enabled?: boolean;
  }
) {
  return useQuery({
    queryKey: taskId
      ? [...nucleiKeys.scanResults(taskId), options?.page, options?.severity]
      : ['nuclei', 'results', 'none'],
    queryFn: () =>
      api.getNucleiScanResults(taskId!, {
        page: options?.page,
        page_size: options?.page_size,
        severity: options?.severity,
      }),
    enabled: !!taskId && (options?.enabled !== false),
  });
}

// =============================================================================
// HOOKS - MUTATIONS
// =============================================================================

/**
 * Hook to start a Nuclei scan
 */
export function useStartNucleiScan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (params: NucleiScanParams) => api.startNucleiScan(params),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: nucleiKeys.scans() });
      toast({
        title: 'Scan Started',
        description: `Nuclei scan queued with profile "${data.profile}"`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Scan Failed',
        description: error.message || 'Failed to start Nuclei scan',
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for quick Nuclei scan (critical vulns only)
 */
export function useNucleiQuickScan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ target, scanName }: { target: string; scanName?: string }) =>
      api.nucleiQuickScan(target, scanName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: nucleiKeys.scans() });
      toast({
        title: 'Quick Scan Started',
        description: `Scanning ${data.target} for critical vulnerabilities`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Quick Scan Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for CVE-focused Nuclei scan
 */
export function useNucleiCVEScan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({
      target,
      cves,
      scanName,
    }: {
      target: string;
      cves?: string[];
      scanName?: string;
    }) => api.nucleiCVEScan(target, cves, scanName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: nucleiKeys.scans() });
      toast({
        title: 'CVE Scan Started',
        description: `CVE-focused scan started on ${data.target}`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'CVE Scan Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook for web vulnerability Nuclei scan
 */
export function useNucleiWebScan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: ({ target, scanName }: { target: string; scanName?: string }) =>
      api.nucleiWebScan(target, scanName),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: nucleiKeys.scans() });
      toast({
        title: 'Web Scan Started',
        description: `Web vulnerability scan started on ${data.target}`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Web Scan Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

/**
 * Hook to cancel a running Nuclei scan
 */
export function useCancelNucleiScan() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  return useMutation({
    mutationFn: (taskId: string) => api.cancelNucleiScan(taskId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: nucleiKeys.scan(data.task_id) });
      toast({
        title: 'Scan Cancelled',
        description: 'The scan has been cancelled',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Cancel Failed',
        description: error.message,
        variant: 'destructive',
      });
    },
  });
}

// =============================================================================
// UTILITIES
// =============================================================================

/**
 * Get color class for severity badge
 */
export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'bg-red-600 text-white';
    case 'high':
      return 'bg-orange-500 text-white';
    case 'medium':
      return 'bg-yellow-500 text-black';
    case 'low':
      return 'bg-blue-500 text-white';
    case 'info':
    default:
      return 'bg-gray-400 text-white';
  }
}

/**
 * Get color class for scan status badge
 */
export function getScanStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'bg-green-500 text-white';
    case 'running':
      return 'bg-blue-500 text-white';
    case 'queued':
    case 'pending':
      return 'bg-yellow-500 text-black';
    case 'failed':
    case 'error':
      return 'bg-red-500 text-white';
    case 'cancelled':
      return 'bg-gray-500 text-white';
    case 'timeout':
      return 'bg-orange-500 text-white';
    default:
      return 'bg-gray-400 text-white';
  }
}

/**
 * Format scan duration
 */
export function formatScanDuration(
  startedAt: string | null,
  completedAt: string | null
): string {
  if (!startedAt) return 'N/A';
  
  const start = new Date(startedAt);
  const end = completedAt ? new Date(completedAt) : new Date();
  const durationMs = end.getTime() - start.getTime();
  
  const seconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`;
  }
  return `${seconds}s`;
}

/**
 * Get profile display name
 */
export function getProfileDisplayName(profile: string): string {
  const names: Record<string, string> = {
    quick: 'Quick Scan',
    standard: 'Standard Scan',
    full: 'Full Scan',
    cves: 'CVE Detection',
    web: 'Web Vulnerabilities',
    misconfig: 'Misconfigurations',
    exposure: 'Exposures',
    takeover: 'Subdomain Takeover',
    network: 'Network Scan',
    tech_detect: 'Technology Detection',
  };
  return names[profile.toLowerCase()] || profile;
}
